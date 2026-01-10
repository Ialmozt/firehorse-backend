"""
Prometheus metrics for Firehorse monitoring.
"""

import time
from typing import Dict, Any, Optional
from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, multiprocess
)
from prometheus_client.exposition import MetricsHandler
import logging

logger = logging.getLogger(__name__)

# Global registry
_registry = CollectorRegistry()

# Order processing metrics
ORDER_PROCESSING_TIME = Histogram(
    'firehorse_order_processing_seconds',
    'Time to process an order',
    ['status', 'content_type'],
    registry=_registry
)

ORDER_PROCESSING_COUNT = Counter(
    'firehorse_orders_processed_total',
    'Total number of orders processed',
    ['status', 'content_type'],
    registry=_registry
)

# DeepSeek API metrics
DEEPSEEK_TOKENS_USED = Counter(
    'firehorse_deepseek_tokens_used_total',
    'Total DeepSeek tokens used',
    ['task_type', 'version'],
    registry=_registry
)

DEEPSEEK_API_CALLS = Counter(
    'firehorse_deepseek_api_calls_total',
    'Total DeepSeek API calls',
    ['status'],
    registry=_registry
)

DEEPSEEK_API_LATENCY = Histogram(
    'firehorse_deepseek_api_latency_seconds',
    'DeepSeek API call latency',
    ['task_type'],
    registry=_registry
)

# Queue metrics
QUEUE_DEPTH = Gauge(
    'firehorse_queue_depth',
    'Current queue depth',
    ['queue_name'],
    registry=_registry
)

QUEUE_PROCESSING_RATE = Gauge(
    'firehorse_queue_processing_rate',
    'Queue processing rate (jobs/second)',
    ['queue_name'],
    registry=_registry
)

# Worker metrics
WORKER_CONCURRENT_TASKS = Gauge(
    'firehorse_worker_concurrent_tasks',
    'Number of concurrent tasks being processed',
    ['worker_id'],
    registry=_registry
)

WORKER_HEALTH = Gauge(
    'firehorse_worker_health',
    'Worker health status (1=healthy, 0=unhealthy)',
    ['worker_id'],
    registry=_registry
)

# API metrics
API_REQUESTS = Counter(
    'firehorse_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status'],
    registry=_registry
)

API_LATENCY = Histogram(
    'firehorse_api_latency_seconds',
    'API request latency',
    ['method', 'endpoint'],
    registry=_registry
)

# Error metrics
ERROR_COUNT = Counter(
    'firehorse_errors_total',
    'Total errors',
    ['error_type', 'component'],
    registry=_registry
)

# System metrics
SYSTEM_MEMORY_USAGE = Gauge(
    'firehorse_system_memory_usage_bytes',
    'System memory usage',
    registry=_registry
)

SYSTEM_CPU_USAGE = Gauge(
    'firehorse_system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=_registry
)


def setup_metrics():
    """Setup metrics system"""
    logger.info("Setting up Prometheus metrics")
    # In production, you might want to use multiprocess mode
    # multiprocess.MultiProcessCollector(_registry)
    return _registry


def record_order_processing_time(
    processing_time: float,
    status: str = "completed",
    content_type: str = "seo_article"
):
    """Record order processing time"""
    ORDER_PROCESSING_TIME.labels(
        status=status,
        content_type=content_type
    ).observe(processing_time)
    
    ORDER_PROCESSING_COUNT.labels(
        status=status,
        content_type=content_type
    ).inc()


def record_deepseek_tokens_used(
    tokens: int,
    task_type: str = "content_creation",
    version: str = "v1"
):
    """Record DeepSeek tokens used"""
    DEEPSEEK_TOKENS_USED.labels(
        task_type=task_type,
        version=version
    ).inc(tokens)


def record_deepseek_api_call(
    success: bool,
    latency: float,
    task_type: str = "content_creation"
):
    """Record DeepSeek API call"""
    status = "success" if success else "error"
    DEEPSEEK_API_CALLS.labels(status=status).inc()
    DEEPSEEK_API_LATENCY.labels(task_type=task_type).observe(latency)


def record_queue_depth(queue_name: str, depth: int):
    """Record queue depth"""
    QUEUE_DEPTH.labels(queue_name=queue_name).set(depth)


def record_queue_processing_rate(queue_name: str, rate: float):
    """Record queue processing rate"""
    QUEUE_PROCESSING_RATE.labels(queue_name=queue_name).set(rate)


def record_worker_concurrent_tasks(worker_id: str, count: int):
    """Record worker concurrent tasks"""
    WORKER_CONCURRENT_TASKS.labels(worker_id=worker_id).set(count)


def record_worker_health(worker_id: str, healthy: bool):
    """Record worker health"""
    value = 1 if healthy else 0
    WORKER_HEALTH.labels(worker_id=worker_id).set(value)


def record_api_request(
    method: str,
    endpoint: str,
    status_code: int,
    latency: float
):
    """Record API request"""
    status = f"{status_code}"
    API_REQUESTS.labels(
        method=method,
        endpoint=endpoint,
        status=status
    ).inc()
    
    API_LATENCY.labels(
        method=method,
        endpoint=endpoint
    ).observe(latency)


def record_error(error_type: str, component: str):
    """Record error"""
    ERROR_COUNT.labels(
        error_type=error_type,
        component=component
    ).inc()


def record_system_metrics(memory_bytes: int, cpu_percent: float):
    """Record system metrics"""
    SYSTEM_MEMORY_USAGE.set(memory_bytes)
    SYSTEM_CPU_USAGE.set(cpu_percent)


def get_metrics_summary() -> Dict[str, Any]:
    """Get metrics summary"""
    # This is a simplified version - in production, you'd query Prometheus
    # or use the metrics registry to get current values
    
    # For now, return a placeholder summary
    # In a real implementation, you would query the metrics registry
    summary = {
        "orders_processed": {
            "total": 0,
            "by_status": {},
            "by_content_type": {}
        },
        "deepseek_usage": {
            "total_tokens": 0,
            "api_calls": 0,
            "success_rate": 0.0
        },
        "queue_metrics": {
            "depth": {},
            "processing_rate": {}
        },
        "worker_metrics": {
            "concurrent_tasks": {},
            "health": {}
        },
        "api_metrics": {
            "total_requests": 0,
            "error_rate": 0.0
        },
        "error_metrics": {
            "total_errors": 0,
            "by_type": {},
            "by_component": {}
        }
    }
    
    return summary


def get_metrics_registry():
    """Get metrics registry"""
    return _registry


def generate_metrics_response():
    """Generate metrics response for Prometheus scraping"""
    return generate_latest(_registry), CONTENT_TYPE_LATEST


class MetricsMiddleware:
    """Middleware for recording API metrics"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        start_time = time.time()
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        
        # Skip metrics endpoint
        if path == "/metrics":
            return await self.app(scope, receive, send)
        
        async def send_wrapper(message):
            if message.get("type") == "http.response.start":
                status_code = message.get("status", 200)
                latency = time.time() - start_time
                
                # Record metrics
                record_api_request(
                    method=method,
                    endpoint=path,
                    status_code=status_code,
                    latency=latency
                )
                
                if status_code >= 400:
                    record_error(
                        error_type=f"http_{status_code}",
                        component="api"
                    )
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Record error
            record_error(
                error_type=type(e).__name__,
                component="api"
            )
            raise
