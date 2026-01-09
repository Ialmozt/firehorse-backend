"""
Middleware для distributed tracing и observability.
Каждый запрос получает уникальный request_id для трассировки.
"""

import uuid
import time
import json
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

logger = logging.getLogger("src.middleware")


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Добавляет distributed tracing каждому запросу.
    
    Features:
    - Генерирует уникальный request_id для каждого запроса
    - Измеряет время обработки запроса
    - Логирует все запросы/ответы в структурированном формате
    - Пропагирует request_id в логи
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Генерируем уникальный request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Начало обработки
        start_time = time.time()
        
        # Логируем входящий запрос
        logger.info(
            json.dumps({
                "event": "request_start",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
                "timestamp": time.time(),
            })
        )
        
        try:
            # Обрабатываем запрос
            response = await call_next(request)
            
            # Добавляем request_id в headers ответа
            response.headers["X-Request-ID"] = request_id
            
            # Измеряем время обработки
            process_time = time.time() - start_time
            
            # Логируем успешный ответ
            logger.info(
                json.dumps({
                    "event": "request_complete",
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(process_time * 1000, 2),
                    "timestamp": time.time(),
                })
            )
            
            return response
            
        except Exception as e:
            # Измеряем время до ошибки
            process_time = time.time() - start_time
            
            # Логируем ошибку
            logger.error(
                json.dumps({
                    "event": "request_error",
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": round(process_time * 1000, 2),
                    "timestamp": time.time(),
                })
            )
            
            raise


class LoggingContextFilter(logging.Filter):
    """
    Добавляет request_id в контекст логирования.
    """
    
    def filter(self, record):
        # Пытаемся получить request_id из контекста
        # (будет добавлено в следующем task'е через contextvars)
        record.request_id = getattr(record, 'request_id', 'no-request-id')
        return True