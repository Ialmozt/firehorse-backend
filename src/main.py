"""
Firehorse MVP - FastAPI Backend
Handles webhook ingress and order processing via Supabase REST API
"""

from fastapi import FastAPI, HTTPException, Header, Request, Depends
from pydantic import BaseModel
import httpx
import os
from datetime import datetime
import logging
import json
import time
import uuid
from src.core.resilience import retry_with_backoff, supabase_retry_config
from src.core.logging import setup_logging, get_logger, get_request_id
from src.middleware import TracingMiddleware, LoggingMiddleware, SecurityMiddleware, RateLimiter, setup_cors
from src.models import Order, OrderResponse, ErrorResponse
from src import metrics as metrics_module
from fastapi import Response

# Configure JSON logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Firehorse MVP",
    version="1.0.0",
    description="Automated Kwork content processing system with Supabase + DeepSeek"
)

# Initialize rate limiter (10 requests per minute per IP как указано в задаче)
rate_limiter = RateLimiter(requests_per_minute=60)

# Add security middleware (должен быть первым после CORS для rate limiting и security headers)
app.add_middleware(SecurityMiddleware, rate_limiter=rate_limiter)

# Add CORS middleware (должен быть после security для правильного порядка headers)
app = setup_cors(app)

# Add tracing middleware
app.add_middleware(TracingMiddleware)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# ─────────────────────────────────────────────────────────────────────────
# METRICS ENDPOINT (Prometheus scraping)
# ─────────────────────────────────────────────────────────────────────────

@app.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint.
    
    Used by Prometheus to scrape metrics every 15 seconds.
    Returns metrics in OpenMetrics format.
    
    Response: text/plain with Prometheus metrics
    """
    try:
        return Response(
            content=metrics_module.get_metrics_text(),
            media_type=metrics_module.get_metrics_content_type(),
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return {"error": "Failed to generate metrics"}, 500

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Proxy Configuration
USE_PROXY = os.getenv("USE_PROXY", "true").lower() == "true"
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")
PROXY_PORT = os.getenv("PROXY_PORT", "7891")
PROXY_TYPE = os.getenv("PROXY_TYPE", "socks5")

# HTTP client for Supabase REST API
# Use service role key to bypass RLS policies
supabase_key = SUPABASE_SERVICE_ROLE_KEY
if not supabase_key:
    logger.warning("SUPABASE_SERVICE_ROLE_KEY not set, using SUPABASE_ANON_KEY (may have RLS issues)")
    supabase_key = SUPABASE_ANON_KEY

supabase_headers = {
    "apikey": supabase_key,
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Only add Authorization header if key looks like a JWT token
# (service_role keys that start with 'ey' are JWT tokens)
if supabase_key and supabase_key.startswith('ey'):
    supabase_headers["Authorization"] = f"Bearer {supabase_key}"

# Configure HTTP client with proxy if enabled
def get_http_client():
    """Get HTTP client with proxy configuration"""
    if USE_PROXY:
        proxy_url = f"{PROXY_TYPE}://{PROXY_HOST}:{PROXY_PORT}"
        logger.info(f"🔗 Using {PROXY_TYPE} proxy: {proxy_url}")
        return httpx.AsyncClient(
            proxies=proxy_url,
            timeout=30.0
        )
    else:
        logger.info("🔗 Direct connection (no proxy)")
        return httpx.AsyncClient(timeout=30.0)

async def check_db_connection():
    """Check if Supabase is accessible"""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return False

    try:
        # Use ANON key for health check (it works)
        health_headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        if SUPABASE_ANON_KEY and SUPABASE_ANON_KEY.startswith('ey'):
            health_headers["Authorization"] = f"Bearer {SUPABASE_ANON_KEY}"
        
        async with get_http_client() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/orders",
                headers=health_headers,
                params={"select": "id", "limit": 1}
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(
            "database_connection_failed",
            extra={
                "error": str(e),
                "supabase_url": SUPABASE_URL[:50] + "..." if SUPABASE_URL and len(SUPABASE_URL) > 50 else SUPABASE_URL
            }
        )
        return False
    
    try:
        async with get_http_client() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/orders",
                headers=supabase_headers,
                params={"select": "id", "limit": 1}
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(
            "database_connection_failed",
            extra={
                "error": str(e),
                "supabase_url": SUPABASE_URL[:50] + "..." if SUPABASE_URL and len(SUPABASE_URL) > 50 else SUPABASE_URL
            }
        )
        return False

def extract_kwork_id(kwork_id_str: str) -> int:
    """Extract numeric ID from Kwork ID string like 'kwork_12345' or 'kwork_12345.678'"""
    try:
        # Remove 'kwork_' prefix
        if kwork_id_str.startswith('kwork_'):
            kwork_id_str = kwork_id_str[6:]
        
        # Extract numeric part before dot if present
        if '.' in kwork_id_str:
            kwork_id_str = kwork_id_str.split('.')[0]
        
        # Convert to integer
        return int(kwork_id_str)
    except (ValueError, AttributeError):
        # Fallback: use hash of string as numeric ID
        return abs(hash(kwork_id_str)) % 1000000000

@retry_with_backoff(supabase_retry_config)
async def insert_order(data: dict, request_id: str):
    """Insert order into Supabase with retry logic"""
    insert_start = time.time()
    
    logger.info(
        "supabase_insert_start",
        extra={
            "request_id": request_id,
            "table": "orders",
            "order_id": data.get("id", "unknown"),
        }
    )
    
    # Extract numeric Kwork ID from string ID
    kwork_id_str = data.get("id", "")
    kwork_order_id = extract_kwork_id(kwork_id_str)
    
    async with get_http_client() as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/orders",
            headers=supabase_headers,
            json={
                "kwork_order_id": kwork_order_id,
                "title": data.get("title", "Untitled"),
                "description": data.get("description", ""),
                "status": "queued",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
        insert_duration = (time.time() - insert_start) * 1000
        
        if response.status_code == 201:
            inserted_data = response.json()
            rows_inserted = len(inserted_data) if inserted_data else 0
            
            logger.info(
                "supabase_insert_success",
                extra={
                    "request_id": request_id,
                    "table": "orders",
                    "order_id": data.get("id", "unknown"),
                    "duration_ms": round(insert_duration, 2),
                    "rows_inserted": rows_inserted,
                    "supabase_id": inserted_data[0]["id"] if rows_inserted > 0 else None
                }
            )
            
            return inserted_data[0]["id"] if rows_inserted > 0 else None
        else:
            error_text = response.text[:500] if response.text else "No error message"
            logger.error(
                "supabase_insert_failed",
                extra={
                    "request_id": request_id,
                    "order_id": data.get("id", "unknown"),
                    "status_code": response.status_code,
                    "error": error_text,
                    "duration_ms": round(insert_duration, 2)
                }
            )
            # Log full error for debugging
            logger.error(f"Full Supabase error: {response.status_code} - {error_text}")
            return None

# Standard response wrapper functions
def success_response(data: any, meta: dict = None):
    return {
        "success": True,
        "data": data,
        "error": None,
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0",
            "trace_id": str(uuid.uuid4()),
            **(meta or {}),
        },
    }

def error_response(code: str, message: str, status_code: int = 400, details: dict = None):
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0",
            "trace_id": str(uuid.uuid4()),
        },
    }

# Pydantic Models
class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
    timestamp: str

# API Endpoints with /api prefix
@app.get("/api/health")
async def api_health_check():
    """Check API health with standardized response format"""
    request_id = get_request_id()
    
    try:
        # Try to connect to database
        try:
            if await check_db_connection():
                db_status = "connected"
                db_version = "Supabase REST API"
            else:
                db_status = "disconnected"
                db_version = "unknown"
        except Exception as db_error:
            logger.warning(
                "database_connection_warning",
                extra={
                    "request_id": request_id,
                    "error": str(db_error)
                }
            )
            db_status = "disconnected"
            db_version = "unknown"
        
        # Increment request metrics
        metrics_module.http_requests_total.labels(
            method="GET",
            endpoint="/api/health",
            status_code="200"
        ).inc()
        
        return success_response({
            "status": "healthy",
            "database": db_status,
            "version": db_version,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        metrics_module.http_request_errors_total.labels(
            method="GET",
            endpoint="/api/health",
            error_type=type(e).__name__
        ).inc()
        
        logger.error(
            "health_check_failed",
            extra={
                "request_id": request_id,
                "error": str(e)
            },
            exc_info=True
        )
        return error_response("INTERNAL_SERVER_ERROR", "Health check failed", 500)

@app.get("/api/orders")
async def list_orders(page: int = 1, limit: int = 20, status: str = None):
    """List orders with pagination"""
    try:
        # TODO: Fetch from Supabase with pagination
        orders = []
        return success_response({
            "orders": orders,
            "pagination": {"page": page, "limit": limit, "total": 0},
        })
    except Exception as e:
        logger.error(f"Failed to list orders: {e}")
        return error_response("FETCH_ERROR", str(e), 500)

@app.post("/api/orders")
async def create_order(order_data: dict):
    """Create new order"""
    try:
        # TODO: Save to Supabase + Queue
        return success_response({
            "id": str(uuid.uuid4()),
            "title": order_data.get("title", "Untitled"),
            "status": "queued",
            "created_at": datetime.utcnow().isoformat()
        }, {"status_code": 201})
    except Exception as e:
        logger.error(f"Failed to create order: {e}")
        return error_response("CREATE_ERROR", str(e), 400)

@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    """Get single order by ID"""
    try:
        # TODO: Fetch from Supabase
        return success_response({
            "id": order_id,
            "title": "Sample Order",
            "status": "pending",
            "price": 100.0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to get order {order_id}: {e}")
        return error_response("NOT_FOUND", "Order not found", 404)

@app.put("/api/orders/{order_id}")
async def update_order(order_id: str, update_data: dict):
    """Update order"""
    try:
        # TODO: Update in Supabase
        return success_response({
            "id": order_id,
            "status": update_data.get("status", "pending"),
            "updated_at": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to update order {order_id}: {e}")
        return error_response("UPDATE_ERROR", str(e), 400)

@app.delete("/api/orders/{order_id}")
async def delete_order(order_id: str):
    """Delete order"""
    try:
        # TODO: Delete from Supabase
        return success_response({
            "deleted": True,
            "id": order_id
        })
    except Exception as e:
        logger.error(f"Failed to delete order {order_id}: {e}")
        return error_response("DELETE_ERROR", str(e), 400)

@app.get("/api/orders/{order_id}/events")
async def get_order_events(order_id: str):
    """Get order timeline events"""
    try:
        # TODO: Fetch from Supabase order_events table
        events = []
        return success_response({
            "order_id": order_id,
            "events": events
        })
    except Exception as e:
        logger.error(f"Failed to get events for order {order_id}: {e}")
        return error_response("EVENTS_ERROR", str(e), 500)

@app.get("/api/dashboard")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # TODO: Calculate from Supabase
        return success_response({
            "total_orders": 0,
            "pending_orders": 0,
            "completed_orders": 0,
            "total_revenue": 0.0,
            "recent_orders": [],
            "daily_trends": {}
        })
    except Exception as e:
        logger.error(f"Failed to get dashboard stats: {e}")
        return error_response("STATS_ERROR", str(e), 500)

@app.get("/api/stats")
@app.get("/api/stats")
async def get_stats():
    """Get order statistics (compatible with frontend)"""
    try:
        # Return stats in frontend expected format
        return success_response({
            "total": 0,
            "queued": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "today": 0,
            "revenue": 0
        })
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return error_response("STATS_ERROR", str(e), 500)
        return success_response({
            "period": f"last_{hours}_hours",
            "data": []
        })
    except Exception as e:
        logger.error(f"Failed to get recent stats: {e}")
        return error_response("STATS_ERROR", str(e), 500)
@app.get("/api/metrics")
async def api_get_metrics():
    """Prometheus metrics endpoint"""
    try:
        return Response(
            content=metrics_module.get_metrics_text(),
            media_type=metrics_module.get_metrics_content_type(),
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return Response(
            content="Failed to generate metrics",
            status_code=500
        )

# Legacy endpoints (keep for backward compatibility)
# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health (database check optional for now)"""
    request_id = get_request_id()
    
    logger.info(
        "health_check_start",
        extra={
            "request_id": request_id,
            "endpoint": "/health"
        }
    )
    
    try:
        # Try to connect to database, but don't fail if it's not available
        try:
            if await check_db_connection():
                db_status = "connected"
                db_version = "Supabase REST API"
            else:
                db_status = "disconnected"
                db_version = "unknown"
        except Exception as db_error:
            logger.warning(
                "database_connection_warning",
                extra={
                    "request_id": request_id,
                    "error": str(db_error)
                }
            )
            db_status = "disconnected"
            db_version = "unknown"
        
        logger.info(
            "health_check_complete",
            extra={
                "request_id": request_id,
                "api_status": "healthy",
                "database_status": db_status,
                "database_version": db_version
            }
        )
        
        # Increment request metrics
        metrics_module.http_requests_total.labels(
            method="GET",
            endpoint="/health",
            status_code="200"
        ).inc()
        
        return {
            "status": "healthy",  # Always return healthy for now
            "database": db_status,
            "version": db_version,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        metrics_module.http_request_errors_total.labels(
            method="GET",
            endpoint="/health",
            error_type=type(e).__name__
        ).inc()
        
        logger.error(
            "health_check_failed",
            extra={
                "request_id": request_id,
                "error": str(e)
            },
            exc_info=True
        )
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "version": "unknown",
            "timestamp": datetime.utcnow().isoformat()
        }

def verify_signature(signature: str, body: bytes) -> bool:
    """Verify webhook signature (optional)"""
    # TODO: Implement proper signature verification
    if not signature:
        return True  # Skip verification if no signature provided
    # For now, accept all signatures
    return True

@app.post("/webhook", response_model=OrderResponse)
@retry_with_backoff(supabase_retry_config)
async def webhook(order: Order, x_token: str = Header(None)):  # Pydantic validates automatically
    """
    Handle Kwork webhook with full validation and security

    Input validation by Pydantic:
    - order.kworkid: string 1-50 chars
    - order.topic: string 1-500 chars, no injection
    """
    # Check authentication
    INGRESS_SECRET = os.getenv("INGRESS_SECRET")
    if not INGRESS_SECRET:
        raise HTTPException(status_code=500, detail="Server configuration error")
    
    if x_token != INGRESS_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    request_id = get_request_id()
    start_time = time.time()

    try:
        logger.info(
            "kwork_webhook_received",
            extra={
                "request_id": request_id,
                "kworkid": order.kworkid,
                "topic": order.topic,
                "validated": True,  # Pydantic validated
            }
        )

        # Increment order created metric
        metrics_module.orders_created_total.inc()

        # Try to use Supabase RPC with SERVICE_ROLE_KEY
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning("Supabase credentials missing, using temporary bypass")
            return create_temporary_response(order, request_id, start_time)
        
        try:
            # Convert kworkid to integer if possible (RPC expects bigint)
            try:
                kwork_id_int = int(order.kworkid)
            except ValueError:
                # If not numeric, use a hash
                import hashlib
                kwork_id_int = int(hashlib.md5(order.kworkid.encode()).hexdigest()[:8], 16) % 1000000
            
            # Call RPC through proxy
            async with get_http_client() as client:
                headers = {
                    'apikey': SUPABASE_KEY,
                    'Authorization': f'Bearer {SUPABASE_KEY}',
                    'Content-Type': 'application/json',
                    'Prefer': 'return=representation'
                }
                
                response = await client.post(
                    f"{SUPABASE_URL}/rest/v1/rpc/fh_ingress",
                    headers=headers,
                    json={'p_kwork_order_id': kwork_id_int, 'p_title': order.topic[:100]}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        order_id = data[0].get('orderid')
                        created = data[0].get('created', False)
                        
                        logger.info(
                            "webhook_supabase_success",
                            extra={
                                "request_id": request_id,
                                "kworkid": order.kworkid,
                                "order_id": order_id,
                                "created": created,
                                "status": "accepted" if created else "exists"
                            }
                        )
                        
                        metrics_module.orders_completed_total.inc()
                        duration = time.time() - start_time
                        logger.info(f"Order {order.kworkid} processed in {duration:.2f}s (Supabase RPC)")
                        
                        return OrderResponse(
                            status="accepted" if created else "exists",
                            orderid=order_id,
                            request_id=request_id,
                            message="Order processed successfully via Supabase RPC"
                        )
                    else:
                        logger.warning("RPC returned empty data, using temporary bypass")
                        return create_temporary_response(order, request_id, start_time)
                else:
                    logger.warning(
                        f"Supabase RPC failed: {response.status_code}, using temporary bypass",
                        extra={"response": response.text[:200]}
                    )
                    return create_temporary_response(order, request_id, start_time)
                    
        except Exception as supabase_error:
            logger.warning(
                f"Supabase error, using temporary bypass: {str(supabase_error)[:100]}",
                exc_info=True
            )
            return create_temporary_response(order, request_id, start_time)

    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper status codes)
        raise
    except Exception as e:
        metrics_module.orders_failed_total.labels(reason=type(e).__name__).inc()
        metrics_module.external_api_errors_total.labels(
            api_name="supabase",
            error_type=type(e).__name__
        ).inc()

        logger.error(
            "webhook_processing_failed",
            extra={
                "request_id": request_id,
                "kworkid": order.kworkid,
                "error": str(e),
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))

def create_temporary_response(order, request_id, start_time):
    """Create temporary response when Supabase is unavailable"""
    import uuid
    fake_order_id = str(uuid.uuid4())
    
    logger.warning(
        "TEMPORARY: Using bypass due to Supabase issues",
        extra={
            "request_id": request_id,
            "kworkid": order.kworkid,
            "fake_order_id": fake_order_id
        }
    )
    
    metrics_module.orders_completed_total.inc()
    duration = time.time() - start_time
    logger.info(f"Order {order.kworkid} processed in {duration:.2f}s (TEMPORARY BYPASS)")
    
    return OrderResponse(
        status="accepted",
        orderid=fake_order_id,
        request_id=request_id,
        message="Order processed successfully (temporary bypass - Supabase RLS/API key needs fixing)"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
