# src/core/logging.py
import json
import logging
import sys
from datetime import datetime
from contextvars import ContextVar
from typing import Any, Dict
import uuid

# Context variable to store request_id across async calls
request_id_context: ContextVar[str] = ContextVar('request_id', default='')

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing and structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": request_id_context.get(),
        }
        
        # Add extra fields from record
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            log_data["exception"] = {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "message": str(exc_value) if exc_value else "",
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data, ensure_ascii=False)

def setup_logging(level=logging.INFO):
    """Configure JSON logging for entire application"""
    
    # Remove default handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    
    # Create JSON formatter
    json_formatter = JSONFormatter()
    
    # Console handler (stdout for Docker)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    console_handler.setLevel(level)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    root_logger.setLevel(level)
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """Get logger instance with JSON formatting"""
    return logging.getLogger(name)

def generate_request_id() -> str:
    """Generate unique request ID"""
    return str(uuid.uuid4())

def set_request_id(request_id: str) -> None:
    """Set request_id in context for current request"""
    request_id_context.set(request_id)

def get_request_id() -> str:
    """Get current request_id from context"""
    return request_id_context.get()