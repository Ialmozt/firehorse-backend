# src/middleware/security.py
import time
import os
from collections import defaultdict
from typing import Dict, List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from src.core.logging import get_logger, get_request_id

logger = get_logger(__name__)

# API Key configuration
API_KEYS = os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"

class RateLimiter:
    """
    Advanced rate limiter using sliding window algorithm
    Limit: 10 requests per minute per IP (как указано в задаче)
    """
    
    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.lock = defaultdict(lambda: False)
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed for this IP using sliding window"""
        current_time = time.time()
        window_start = current_time - 60.0  # 1 minute sliding window
        
        # Get requests for this IP in current window
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove old requests outside window
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > window_start
        ]
        
        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return False
        
        # Add current request
        self.requests[client_ip].append(current_time)
        
        # Clean up old IPs to prevent memory leak
        if len(self.requests) > 1000:  # Keep only 1000 IPs in memory
            oldest_ip = min(self.requests.keys(), key=lambda ip: self.requests[ip][-1] if self.requests[ip] else 0)
            del self.requests[oldest_ip]
        
        return True
    
    def get_remaining_requests(self, client_ip: str) -> int:
        """Get remaining requests for this IP in current window"""
        current_time = time.time()
        window_start = current_time - 60.0
        
        if client_ip not in self.requests:
            return self.requests_per_minute
        
        # Count requests in window
        requests_in_window = [
            req_time for req_time in self.requests[client_ip]
            if req_time > window_start
        ]
        
        return max(0, self.requests_per_minute - len(requests_in_window))

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware to:
    1. Rate limit by IP (10 requests per minute)
    2. Add security headers
    3. Validate API keys (header X-API-Key)
    4. Log security events
    """
    
    def __init__(self, app, rate_limiter: RateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter(requests_per_minute=60)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = get_request_id()
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip API key validation for health and metrics endpoints
        skip_api_key_paths = ["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]
        if request.url.path not in skip_api_key_paths:
            # Validate API key if required
            if REQUIRE_API_KEY:
                api_key = request.headers.get("X-API-Key")
                if not api_key or api_key not in API_KEYS:
                    logger.warning(
                        "invalid_api_key",
                        extra={
                            "request_id": request_id,
                            "client_ip": client_ip,
                            "path": request.url.path,
                            "provided_key": api_key[:10] + "..." if api_key and len(api_key) > 10 else api_key,
                        }
                    )
                    
                    return JSONResponse(
                        status_code=401,
                        content={
                            "error": "Unauthorized",
                            "message": "Invalid or missing API key",
                            "request_id": request_id,
                        }
                    )
        
        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip):
            remaining = self.rate_limiter.get_remaining_requests(client_ip)
            reset_time = int(time.time() + 60)  # Reset in 60 seconds
            
            logger.warning(
                "rate_limit_exceeded",
                extra={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "limit": self.rate_limiter.requests_per_minute,
                    "remaining": remaining,
                    "reset_time": reset_time
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "message": f"Rate limit: {self.rate_limiter.requests_per_minute} requests per minute",
                    "request_id": request_id,
                    "retry_after": 60
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_minute),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Always add security headers (override if needed)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Request-ID"] = request_id
        
        # Add rate limit headers
        remaining = self.rate_limiter.get_remaining_requests(client_ip)
        reset_time = int(time.time() + 60)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
