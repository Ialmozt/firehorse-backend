# src/middleware/security.py
import time
from collections import defaultdict
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from src.core.logging import get_logger, get_request_id

logger = get_logger(__name__)

class RateLimiter:
    """
    Simple in-memory rate limiter using fixed window algorithm
    Limit: 10 requests per second per IP
    """
    
    def __init__(self, requests_per_second: int = 10):
        self.requests_per_second = requests_per_second
        self.requests: Dict[str, List[float]] = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed for this IP"""
        current_time = time.time()
        window_start = current_time - 1.0
        
        # Get requests for this IP in current window
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove old requests outside window
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > window_start
        ]
        
        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.requests_per_second:
            return False
        
        # Add current request
        self.requests[client_ip].append(current_time)
        return True

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware to:
    1. Rate limit by IP
    2. Add security headers
    3. Log security events
    """
    
    def __init__(self, app, rate_limiter: RateLimiter = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter(requests_per_second=10)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = get_request_id()
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip):
            logger.warning(
                "rate_limit_exceeded",
                extra={
                    "request_id": request_id,
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "limit": self.rate_limiter.requests_per_second,
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "message": f"Rate limit: {self.rate_limiter.requests_per_second} requests per second",
                    "request_id": request_id,
                },
                headers={"Retry-After": "1"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Request-ID"] = request_id
        
        return response