"""
Advanced error handling and resilience system for Firehorse.
Features:
- Circuit breaker pattern for external APIs
- Exponential backoff with jitter
- Retry logic with configurable strategies
- Graceful degradation
- Comprehensive error classification
"""

import asyncio
import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorCategory(Enum):
    """Categories of errors for different handling strategies"""
    NETWORK = "network"           # Connection issues, timeouts
    API = "api"                   # API errors (4xx, 5xx)
    DATABASE = "database"         # Database connection/query errors
    VALIDATION = "validation"     # Input validation errors
    BUSINESS = "business"         # Business logic errors
    EXTERNAL = "external"         # Third-party service errors
    UNKNOWN = "unknown"           # Unclassified errors


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit open, failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_categories: List[ErrorCategory] = None
    
    def __post_init__(self):
        if self.retry_on_categories is None:
            self.retry_on_categories = [
                ErrorCategory.NETWORK,
                ErrorCategory.API,
                ErrorCategory.DATABASE,
                ErrorCategory.EXTERNAL,
                ErrorCategory.UNKNOWN,  # Retry unknown errors by default
            ]


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    reset_timeout: float = 60.0  # seconds
    half_open_max_requests: int = 3
    half_open_timeout: float = 30.0  # seconds


class ErrorClassifier:
    """Classify errors for appropriate handling"""
    
    @staticmethod
    def classify_error(error: Exception) -> ErrorCategory:
        """Classify exception into error category"""
        error_str = str(error).lower()
        
        # Check exception types first
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK
        
        # Database errors (check before network since "connection" appears in both)
        db_keywords = [
            "database", "sql", "postgres", "transaction", "constraint",
            "deadlock", "connection pool", "query timeout", "pg_"
        ]
        if any(keyword in error_str for keyword in db_keywords):
            return ErrorCategory.DATABASE
        
        # Network errors
        network_keywords = [
            "timeout", "network", "socket", "refused",
            "reset", "unreachable", "dns", "ssl", "tls", "connection refused"
        ]
        if any(keyword in error_str for keyword in network_keywords):
            return ErrorCategory.NETWORK
        
        # API errors
        api_keywords = ["api", "http", "status", "response", "request", "4", "5"]
        if any(keyword in error_str for keyword in api_keywords):
            return ErrorCategory.API
        
        # Validation errors
        validation_keywords = ["validation", "invalid", "missing", "required", "value"]
        if any(keyword in error_str for keyword in validation_keywords):
            return ErrorCategory.VALIDATION
        
        return ErrorCategory.UNKNOWN
    
    @staticmethod
    def should_retry(error: Exception, config: RetryConfig) -> bool:
        """Determine if error should be retried"""
        category = ErrorClassifier.classify_error(error)
        return category in config.retry_on_categories


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_attempts = 0
        self.half_open_start: Optional[datetime] = None
        
    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        now = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            return True
        
        elif self.state == CircuitState.OPEN:
            # Check if reset timeout has passed
            if self.last_failure_time and \
               (now - self.last_failure_time).total_seconds() >= self.config.reset_timeout:
                logger.info(f"Circuit {self.name}: transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.half_open_start = now
                self.half_open_attempts = 0
                return True
            return False
        
        elif self.state == CircuitState.HALF_OPEN:
            # Check half-open timeout
            if self.half_open_start and \
               (now - self.half_open_start).total_seconds() >= self.config.half_open_timeout:
                logger.info(f"Circuit {self.name}: HALF_OPEN timeout, transitioning to OPEN")
                self.state = CircuitState.OPEN
                return False
            
            # Limit number of attempts in half-open state
            if self.half_open_attempts >= self.config.half_open_max_requests:
                return False
            
            return True
        
        return False
    
    def on_success(self):
        """Handle successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit {self.name}: HALF_OPEN success, transitioning to CLOSED")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            self.half_open_attempts = 0
            self.half_open_start = None
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def on_failure(self, error: Exception):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit {self.name}: HALF_OPEN failure, transitioning to OPEN")
            self.state = CircuitState.OPEN
            self.half_open_attempts = 0
            self.half_open_start = None
        
        elif self.state == CircuitState.CLOSED and \
             self.failure_count >= self.config.failure_threshold:
            logger.warning(f"Circuit {self.name}: failure threshold reached, transitioning to OPEN")
            self.state = CircuitState.OPEN
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get current circuit state information"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "half_open_attempts": self.half_open_attempts,
            "half_open_start": self.half_open_start.isoformat() if self.half_open_start else None,
        }


class RetryManager:
    """Manage retry logic with exponential backoff"""
    
    @staticmethod
    def calculate_delay(
        attempt: int,
        base_delay: float,
        max_delay: float,
        exponential_base: float,
        jitter: bool = True
    ) -> float:
        """Calculate delay for retry attempt"""
        delay = min(
            max_delay,
            base_delay * (exponential_base ** (attempt - 1))
        )
        
        if jitter:
            # Add random jitter (±20%)
            jitter_amount = delay * 0.2
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.1, delay)  # Ensure positive delay
        
        return delay
    
    @staticmethod
    async def execute_with_retry(
        func: Callable[..., T],
        config: RetryConfig = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        *args,
        **kwargs
    ) -> T:
        """Execute function with retry logic"""
        config = config or RetryConfig()
        last_error = None
        
        for attempt in range(1, config.max_retries + 2):  # +1 for initial attempt
            try:
                # Check circuit breaker if provided
                if circuit_breaker and not circuit_breaker.can_execute():
                    raise Exception(f"Circuit {circuit_breaker.name} is OPEN")
                
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Update circuit breaker on success
                if circuit_breaker:
                    circuit_breaker.on_success()
                
                return result
                
            except Exception as e:
                last_error = e
                
                # Update circuit breaker on failure
                if circuit_breaker:
                    circuit_breaker.on_failure(e)
                
                # Check if we should retry
                if attempt == config.max_retries + 1:
                    logger.error(f"All {config.max_retries} retry attempts failed")
                    break
                
                if not ErrorClassifier.should_retry(e, config):
                    logger.warning(f"Non-retryable error: {e}")
                    break
                
                # Calculate and wait for retry delay
                delay = RetryManager.calculate_delay(
                    attempt,
                    config.base_delay,
                    config.max_delay,
                    config.exponential_base,
                    config.jitter
                )
                
                logger.warning(
                    f"Attempt {attempt} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                await asyncio.sleep(delay)
        
        # If we get here, all retries failed
        if last_error:
            raise last_error
        else:
            raise Exception("Retry failed without capturing error")


class GracefulDegradation:
    """Implement graceful degradation patterns"""
    
    @staticmethod
    async def with_fallback(
        primary_func: Callable[..., T],
        fallback_func: Callable[..., T],
        fallback_condition: Optional[Callable[[Exception], bool]] = None,
        *args,
        **kwargs
    ) -> T:
        """Execute primary function with fallback"""
        try:
            if asyncio.iscoroutinefunction(primary_func):
                return await primary_func(*args, **kwargs)
            else:
                return primary_func(*args, **kwargs)
        except Exception as e:
            if fallback_condition and not fallback_condition(e):
                raise
            
            logger.warning(f"Primary function failed, using fallback: {e}")
            
            if asyncio.iscoroutinefunction(fallback_func):
                return await fallback_func(*args, **kwargs)
            else:
                return fallback_func(*args, **kwargs)
    
    @staticmethod
    async def with_cache_fallback(
        func: Callable[..., T],
        cache_key: str,
        cache_ttl: int = 300,  # 5 minutes
        *args,
        **kwargs
    ) -> T:
        """Execute function with cache fallback"""
        # This is a simplified version - in production, you'd use Redis or similar
        # For now, we'll just log the pattern
        logger.info(f"Cache fallback pattern for key: {cache_key}, TTL: {cache_ttl}s")
        
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Function failed, would use cache if available: {e}")
            raise


class ErrorMetrics:
    """Track error metrics for monitoring"""
    
    def __init__(self):
        self.metrics = {
            "total_errors": 0,
            "error_by_category": {category.value: 0 for category in ErrorCategory},
            "error_by_service": {},
            "circuit_breaker_state": {},
            "retry_success_rate": 0.0,
            "last_error_time": None,
        }
    
    def record_error(self, error: Exception, service: str = "unknown"):
        """Record error metrics"""
        self.metrics["total_errors"] += 1
        
        category = ErrorClassifier.classify_error(error)
        self.metrics["error_by_category"][category.value] += 1
        
        if service not in self.metrics["error_by_service"]:
            self.metrics["error_by_service"][service] = 0
        self.metrics["error_by_service"][service] += 1
        
        self.metrics["last_error_time"] = datetime.now().isoformat()
    
    def record_circuit_state(self, circuit_name: str, state: CircuitState):
        """Record circuit breaker state"""
        self.metrics["circuit_breaker_state"][circuit_name] = state.value
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics.copy()


# Global instances
error_metrics = ErrorMetrics()
circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
    """Get or create circuit breaker instance"""
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(name, config)
    return circuit_breakers[name]


async def resilient_call(
    func: Callable[..., T],
    service_name: str,
    retry_config: RetryConfig = None,
    circuit_breaker_config: CircuitBreakerConfig = None,
    use_circuit_breaker: bool = True,
    *args,
    **kwargs
) -> T:
    """
    Make a resilient call with retry and circuit breaker.
    
    Args:
        func: Function to call
        service_name: Name of the service (for circuit breaker and metrics)
        retry_config: Retry configuration
        circuit_breaker_config: Circuit breaker configuration
        use_circuit_breaker: Whether to use circuit breaker
        *args, **kwargs: Arguments to pass to function
    
    Returns:
        Function result
    
    Raises:
        Exception: If all retries fail
    """
    circuit_breaker = None
    if use_circuit_breaker:
        circuit_breaker = get_circuit_breaker(service_name, circuit_breaker_config)
    
    try:
        result = await RetryManager.execute_with_retry(
            func,
            retry_config,
            circuit_breaker,
            *args,
            **kwargs
        )
        
        # Record circuit breaker state
        if circuit_breaker:
            error_metrics.record_circuit_state(
                service_name,
                circuit_breaker.state
            )
        
        return result
        
    except Exception as e:
        # Record error metrics
        error_metrics.record_error(e, service_name)
        
        # Re-raise the error
        raise


# Convenience functions for common use cases
async def resilient_api_call(
    func: Callable[..., T],
    service_name: str,
    *args,
    **kwargs
) -> T:
    """Make resilient API call with optimized settings"""
    retry_config = RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True,
    )
    
    circuit_config = CircuitBreakerConfig(
        failure_threshold=5,
        reset_timeout=60.0,
        half_open_max_requests=2,
        half_open_timeout=30.0,
    )
    
    return await resilient_call(
        func,
        service_name,
        retry_config,
        circuit_config,
        True,
        *args,
        **kwargs
    )


async def resilient_database_call(
    func: Callable[..., T],
    *args,
    **kwargs
) -> T:
    """Make resilient database call with optimized settings"""
    retry_config = RetryConfig(
        max_retries=2,
        base_delay=0.5,
        max_delay=5.0,
        exponential_base=1.5,
        jitter=True,
    )
    
    return await resilient_call(
        func,
        "database",
        retry_config,
        None,  # Don't use circuit breaker for database
        False,
        *args,
        **kwargs
    )


# Example usage patterns
async def example_usage():
    """Example of how to use the error handling system"""
    
    # Example 1: Simple retry
    async def call_external_api():
        # Your API call here
        pass
    
    try:
        result = await resilient_api_call(
            call_external_api,
            "deepseek_api"
        )
    except Exception as e:
        logger.error(f"API call failed after retries: {e}")
    
    # Example 2: With fallback
    async def primary_service():
        # Primary service call
        pass
    
    async def fallback_service():
        # Fallback service call
        pass
    
    result = await GracefulDegradation.with_fallback(
        primary_service,
        fallback_service
    )
    
    # Example 3: Get metrics
    metrics = error_metrics.get_metrics()
    logger.info(f"Error metrics: {metrics}")
