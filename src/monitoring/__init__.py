"""
Monitoring and observability module for Firehorse.
Provides:
- Prometheus metrics
- Structured logging
- Health checks
- Tracing
"""

from .metrics import (
    setup_metrics, 
    record_order_processing_time,
    record_deepseek_tokens_used,
    record_queue_depth,
    record_error,
    get_metrics_summary
)
from .health import (
    HealthChecker,
    check_database_health,
    check_deepseek_health,
    check_vpn_health,
    perform_health_check
)
from .tracing import (
    setup_tracing,
    trace_request,
    trace_operation,
    get_trace_context
)

__all__ = [
    # Metrics
    'setup_metrics',
    'record_order_processing_time',
    'record_deepseek_tokens_used',
    'record_queue_depth',
    'record_error',
    'get_metrics_summary',
    
    # Health
    'HealthChecker',
    'check_database_health',
    'check_deepseek_health',
    'check_vpn_health',
    'perform_health_check',
    
    # Tracing
    'setup_tracing',
    'trace_request',
    'trace_operation',
    'get_trace_context',
]
