"""
Prometheus metrics для мониторинга системы.
Отслеживает: requests, errors, latency, queue depth, API calls.
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
import time


# ═══════════════════════════════════════════════════════════════════════════
# REQUEST METRICS
# ═══════════════════════════════════════════════════════════════════════════

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed'
)


# ═══════════════════════════════════════════════════════════════════════════
# ERROR METRICS
# ═══════════════════════════════════════════════════════════════════════════

http_request_errors_total = Counter(
    'http_request_errors_total',
    'Total HTTP request errors',
    ['method', 'endpoint', 'error_type']
)

http_request_exceptions_total = Counter(
    'http_request_exceptions_total',
    'Total unhandled exceptions',
    ['exception_type', 'endpoint']
)


# ═══════════════════════════════════════════════════════════════════════════
# QUEUE METRICS
# ═══════════════════════════════════════════════════════════════════════════

queue_depth = Gauge(
    'queue_depth',
    'Number of pending jobs in queue'
)

queue_processing_time = Histogram(
    'queue_processing_time_seconds',
    'Time to process a queue job in seconds',
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

queue_errors_total = Counter(
    'queue_errors_total',
    'Total queue processing errors',
    ['error_type', 'queue_name']
)

queue_dead_letter_total = Counter(
    'queue_dead_letter_total',
    'Jobs moved to dead letter queue',
    ['reason']
)


# ═══════════════════════════════════════════════════════════════════════════
# API CALL METRICS (DeepSeek, Kwork, etc)
# ═══════════════════════════════════════════════════════════════════════════

external_api_calls_total = Counter(
    'external_api_calls_total',
    'Total external API calls',
    ['api_name', 'endpoint', 'status_code']
)

external_api_duration_seconds = Histogram(
    'external_api_duration_seconds',
    'External API call latency in seconds',
    ['api_name', 'endpoint'],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120)
)

external_api_errors_total = Counter(
    'external_api_errors_total',
    'Total external API errors',
    ['api_name', 'error_type']
)

external_api_retries_total = Counter(
    'external_api_retries_total',
    'External API retry attempts',
    ['api_name', 'retry_count']
)


# ═══════════════════════════════════════════════════════════════════════════
# BUSINESS METRICS
# ═══════════════════════════════════════════════════════════════════════════

orders_created_total = Counter(
    'orders_created_total',
    'Total orders created'
)

orders_completed_total = Counter(
    'orders_completed_total',
    'Total orders completed successfully'
)

orders_failed_total = Counter(
    'orders_failed_total',
    'Total orders failed',
    ['reason']
)

article_generation_time = Histogram(
    'article_generation_time_seconds',
    'Time to generate an article in seconds',
    buckets=(5, 10, 30, 60, 120, 300, 600)
)

article_word_count = Histogram(
    'article_word_count',
    'Generated article word count',
    buckets=(100, 500, 1000, 2000, 5000, 10000)
)


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE METRICS
# ═══════════════════════════════════════════════════════════════════════════

db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size'
)

db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['query_type', 'table_name']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query latency in seconds',
    ['query_type'],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
)

db_errors_total = Counter(
    'db_errors_total',
    'Total database errors',
    ['error_type']
)


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM HEALTH METRICS
# ═══════════════════════════════════════════════════════════════════════════

system_uptime_seconds = Gauge(
    'system_uptime_seconds',
    'System uptime in seconds'
)

last_error_timestamp = Gauge(
    'last_error_timestamp',
    'Timestamp of last error',
    ['error_type']
)

active_workers = Gauge(
    'active_workers',
    'Number of active worker processes'
)

cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits'
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses'
)


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def get_metrics_text():
    """Generate Prometheus metrics in text format."""
    return generate_latest()


def get_metrics_content_type():
    """Get the correct content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST