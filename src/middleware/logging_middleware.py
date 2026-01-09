# src/middleware/logging_middleware.py
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from src.core.logging import generate_request_id, set_request_id, get_request_id

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to:
    1. Generate unique request_id for each request
    2. Log request details (method, path, headers)
    3. Log response details (status, duration)
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Use existing request_id from TracingMiddleware if available
        if hasattr(request.state, 'request_id'):
            request_id = request.state.request_id
        else:
            request_id = generate_request_id()
        
        set_request_id(request_id)
        
        # Log request received
        logger.info(
            "http_request_received",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown",
            }
        )
        
        # Measure request duration
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log successful response
            logger.info(
                "http_response_sent",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "path": request.url.path,
                }
            )
            
            return response
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            logger.error(
                "http_request_failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                    "path": request.url.path,
                },
                exc_info=True
            )
            
            raise