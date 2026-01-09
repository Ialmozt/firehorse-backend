# src/core/resilience.py
import asyncio
import functools
import logging
from typing import Callable, Any
import httpx

logger = logging.getLogger(__name__)

class RetryConfig:
    """Exponential backoff configuration"""
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 8.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

def classify_error(error: Exception) -> tuple[str, bool]:
    """
    Classify error and determine if retry should happen
    Returns: (error_type, should_retry)
    """
    if isinstance(error, httpx.TimeoutException):
        return ("timeout", True)
    elif isinstance(error, httpx.ConnectError):
        return ("connection", True)
    elif isinstance(error, httpx.NetworkError):
        return ("network", True)
    elif isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        if 500 <= status < 600:
            return ("server_error", True)
        else:
            return ("client_error", False)
    elif isinstance(error, ConnectionError):
        return ("connection", True)
    elif isinstance(error, TimeoutError):
        return ("timeout", True)
    elif isinstance(error, OSError):
        # Network-related OS errors (e.g., ECONNREFUSED)
        return ("os_error", True)
    else:
        return ("unknown", False)

def retry_with_backoff(config: RetryConfig = None):
    """
    Decorator for exponential backoff retry logic
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    logger.info(f"Attempt {attempt + 1}/{config.max_retries + 1} for {func.__name__}")
                    result = await func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"Success after {attempt} retries for {func.__name__}")
                    return result
                except Exception as e:
                    error_type, should_retry = classify_error(e)
                    last_error = e
                    
                    if not should_retry or attempt == config.max_retries:
                        logger.error(f"Failed after {attempt + 1} attempts: {error_type} - {str(e)}")
                        raise
                    
                    # Exponential backoff
                    delay = min(config.base_delay * (2 ** attempt), config.max_delay)
                    logger.warning(f"Retry {error_type}, waiting {delay}s before attempt {attempt + 2}")
                    await asyncio.sleep(delay)
            
            raise last_error
        
        return wrapper
    return decorator

# Create default retry config for Supabase operations
supabase_retry_config = RetryConfig(max_retries=3, base_delay=1.0, max_delay=8.0)