"""
Distributed tracing for Firehorse.
"""

import uuid
import time
import logging
from typing import Dict, Any, Optional, List
from contextvars import ContextVar
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Context variables for tracing
_request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
_trace_id: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
_span_id: ContextVar[Optional[str]] = ContextVar('span_id', default=None)
_parent_span_id: ContextVar[Optional[str]] = ContextVar('parent_span_id', default=None)


class Span:
    """Represents a span in a trace"""
    
    def __init__(
        self,
        name: str,
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.attributes = attributes or {}
        self.events: List[Dict[str, Any]] = []
        self.status = "unset"
        self.status_message: Optional[str] = None
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the span"""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        })
    
    def set_attribute(self, key: str, value: Any):
        """Set a span attribute"""
        self.attributes[key] = value
    
    def set_status(self, status: str, message: Optional[str] = None):
        """Set span status"""
        self.status = status
        self.status_message = message
    
    def end(self):
        """End the span"""
        self.end_time = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.end_time - self.start_time if self.end_time else None,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status,
            "status_message": self.status_message
        }


class Tracer:
    """Distributed tracer"""
    
    def __init__(self, service_name: str = "firehorse"):
        self.service_name = service_name
        self.spans: Dict[str, Span] = {}
    
    def start_span(
        self,
        name: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """Start a new span"""
        trace_id = get_trace_id() or self._generate_id()
        span_id = self._generate_id()
        
        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            attributes=attributes
        )
        
        # Store span
        self.spans[span_id] = span
        
        # Update context
        _trace_id.set(trace_id)
        _span_id.set(span_id)
        if parent_span_id:
            _parent_span_id.set(parent_span_id)
        
        return span
    
    def get_span(self, span_id: str) -> Optional[Span]:
        """Get span by ID"""
        return self.spans.get(span_id)
    
    def end_span(self, span_id: str):
        """End a span"""
        span = self.spans.get(span_id)
        if span:
            span.end()
    
    def export_spans(self) -> List[Dict[str, Any]]:
        """Export all spans"""
        return [span.to_dict() for span in self.spans.values() if span.end_time]
    
    def clear_completed_spans(self):
        """Clear completed spans"""
        completed_ids = [span_id for span_id, span in self.spans.items() if span.end_time]
        for span_id in completed_ids:
            del self.spans[span_id]
    
    def _generate_id(self) -> str:
        """Generate a unique ID"""
        return str(uuid.uuid4())


def setup_tracing(service_name: str = "firehorse") -> Tracer:
    """Setup tracing system"""
    logger.info(f"Setting up tracing for service: {service_name}")
    return Tracer(service_name)


def trace_request(
    tracer: Tracer,
    name: str,
    request_id: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
) -> Span:
    """Start tracing a request"""
    if request_id:
        _request_id.set(request_id)
    else:
        _request_id.set(tracer._generate_id())
    
    span = tracer.start_span(
        name=name,
        attributes=attributes
    )
    
    # Add request ID to span attributes
    span.set_attribute("request_id", get_request_id())
    span.set_attribute("service", tracer.service_name)
    span.set_attribute("start_time", datetime.now().isoformat())
    
    return span


def trace_operation(
    tracer: Tracer,
    name: str,
    parent_span: Optional[Span] = None,
    attributes: Optional[Dict[str, Any]] = None
) -> Span:
    """Trace an operation"""
    parent_span_id = parent_span.span_id if parent_span else get_span_id()
    
    span = tracer.start_span(
        name=name,
        parent_span_id=parent_span_id,
        attributes=attributes
    )
    
    # Add operation context
    span.set_attribute("operation", name)
    span.set_attribute("trace_id", span.trace_id)
    
    return span


def get_trace_context() -> Dict[str, Optional[str]]:
    """Get current trace context"""
    return {
        "request_id": get_request_id(),
        "trace_id": get_trace_id(),
        "span_id": get_span_id(),
        "parent_span_id": get_parent_span_id()
    }


def get_request_id() -> Optional[str]:
    """Get current request ID"""
    return _request_id.get()


def get_trace_id() -> Optional[str]:
    """Get current trace ID"""
    return _trace_id.get()


def get_span_id() -> Optional[str]:
    """Get current span ID"""
    return _span_id.get()


def get_parent_span_id() -> Optional[str]:
    """Get parent span ID"""
    return _parent_span_id.get()


def set_trace_context(
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    parent_span_id: Optional[str] = None
):
    """Set trace context"""
    if request_id:
        _request_id.set(request_id)
    if trace_id:
        _trace_id.set(trace_id)
    if span_id:
        _span_id.set(span_id)
    if parent_span_id:
        _parent_span_id.set(parent_span_id)


class TracingMiddleware:
    """Middleware for distributed tracing"""
    
    def __init__(self, app, tracer: Tracer):
        self.app = app
        self.tracer = tracer
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        # Extract headers
        headers = dict(scope.get("headers", []))
        
        # Get or generate trace context from headers
        request_id = self._get_header(headers, "x-request-id")
        trace_id = self._get_header(headers, "x-trace-id")
        span_id = self._get_header(headers, "x-span-id")
        parent_span_id = self._get_header(headers, "x-parent-span-id")
        
        # Set trace context
        set_trace_context(
            request_id=request_id,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
        
        # Start request span
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        span_name = f"{method} {path}"
        
        span_attributes = {
            "http.method": method,
            "http.path": path,
            "http.scheme": scope.get("scheme", "http"),
            "http.host": self._get_header(headers, "host"),
            "http.user_agent": self._get_header(headers, "user-agent"),
        }
        
        span = trace_request(
            tracer=self.tracer,
            name=span_name,
            request_id=request_id,
            attributes=span_attributes
        )
        
        async def send_wrapper(message):
            if message.get("type") == "http.response.start":
                status_code = message.get("status", 200)
                
                # Update span with response info
                span.set_attribute("http.status_code", status_code)
                span.set_status("ok" if status_code < 400 else "error")
                
                # End span
                span.end()
                
                # Add trace headers to response
                headers = message.get("headers", [])
                headers.extend([
                    (b"x-request-id", get_request_id().encode()),
                    (b"x-trace-id", get_trace_id().encode()),
                    (b"x-span-id", get_span_id().encode()),
                ])
                message["headers"] = headers
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Record error in span
            span.set_status("error", str(e))
            span.end()
            raise
    
    def _get_header(self, headers: Dict[bytes, bytes], name: str) -> Optional[str]:
        """Get header value"""
        key = name.lower().encode()
        for header_key, header_value in headers.items():
            if header_key.lower() == key:
                return header_value.decode()
        return None


def log_with_trace(
    logger: logging.Logger,
    level: int,
    message: str,
    extra: Optional[Dict[str, Any]] = None
):
    """Log with trace context"""
    trace_context = get_trace_context()
    
    log_extra = {
        "request_id": trace_context["request_id"],
        "trace_id": trace_context["trace_id"],
        "span_id": trace_context["span_id"],
    }
    
    if extra:
        log_extra.update(extra)
    
    logger.log(level, message, extra=log_extra)


# Global tracer instance
_global_tracer: Optional[Tracer] = None


def get_global_tracer() -> Tracer:
    """Get global tracer instance"""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = setup_tracing()
    return _global_tracer


def init_tracing(service_name: str = "firehorse") -> Tracer:
    """Initialize global tracing"""
    global _global_tracer
    _global_tracer = setup_tracing(service_name)
    return _global_tracer
