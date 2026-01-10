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
    Simple in-memory rate limiter using fixed window algorithm
    Limit: 10 requests per minute per IP (как указано в задаче)
    """
    
    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed for this IP"""
        current_time = time.time()
        window_start = current_time - 60.0  # 1 minute window
        
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
        return True

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
        self.rate_limiter = rate_limiter or RateLimiter(requests_per_minute=10)
    
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
            logger.warning(
                "rate_limit_exceeded",
                extra={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "limit": self.rate_limiter.requests_per_minute,
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "message": f"Rate limit: {self.rate_limiter.requests_per_minute} requests per minute",
                    "request_id": request_id,
                },
                headers={"Retry-After": "60"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Request-ID"] = request_id
        
        # Add CORS headers (will be overridden by CORS middleware if present)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
        
        return response
