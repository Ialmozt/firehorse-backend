"""
CORS middleware для Firehorse MVP.
Настраивает CORS политики для фронтенда.
"""

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import os

def setup_cors(app: FastAPI):
    """
    Настройка CORS middleware для приложения.
    
    Разрешает запросы только с указанных доменов.
    По умолчанию разрешает все домены для разработки.
    """
    
    # Получаем список разрешенных доменов из переменных окружения
    allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "*")
    
    if allowed_origins_str == "*":
        # Разрешаем все домены (для разработки)
        allowed_origins = ["*"]
    else:
        # Разрешаем только указанные домены
        allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]
    
    # Настройка CORS middleware
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
        ],
        expose_headers=[
            "Content-Length",
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        max_age=600,  # 10 минут кэширования preflight запросов
    )
    
    return app
