"""
CORS middleware for Firehorse MVP.
Configures CORS policies for frontend access.
"""

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import os

def setup_cors(app: FastAPI) -> FastAPI:
    """
    Configure CORS middleware for the application.
    
    Allows requests only from specified domains.
    Defaults to allowing all domains for development.
    
    Returns:
        FastAPI: The configured application
    """
    
    # Get allowed origins from environment variables
    allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "*")
    
    if allowed_origins_str == "*":
        # Allow all domains (for development)
        allowed_origins = ["*"]
    else:
        # Allow only specified domains
        allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]
    
    # Configure CORS middleware with security best practices
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Request-ID",
            "Accept",
            "Origin",
            "User-Agent",
            "Cache-Control",
            "X-Requested-With",
            "X-Forwarded-For",
            "X-Real-IP",
        ],
        expose_headers=[
            "Content-Length",
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
        ],
        max_age=600,  # 10 minutes cache for preflight requests
    )
    
    return app
