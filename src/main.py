"""
Firehorse MVP - FastAPI Backend
Handles webhook ingress and order processing via Supabase REST API
"""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import httpx
import os
from datetime import datetime
import logging
import json
import time
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
rate_limiter = RateLimiter(requests_per_minute=10)

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
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# HTTP client for Supabase REST API
# Use service key to bypass RLS policies
supabase_key = SUPABASE_SERVICE_KEY
if not supabase_key:
    logger.warning("SUPABASE_SERVICE_KEY not set, using SUPABASE_ANON_KEY (may have RLS issues)")
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

async def check_db_connection():
    """Check if Supabase is accessible"""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return False
    
    try:
        async with httpx.AsyncClient() as client:
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
    
    async with httpx.AsyncClient(timeout=30.0) as client:
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
            logger.error(
                "supabase_insert_failed",
                extra={
                    "request_id": request_id,
                    "order_id": data.get("id", "unknown"),
                    "status_code": response.status_code,
                    "error": response.text[:200] if response.text else "No error message",
                    "duration_ms": round(insert_duration, 2)
                }
            )
            return None

# Pydantic Models
class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
    timestamp: str

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
async def webhook(order: Order):  # Pydantic validates automatically
    """
    Handle Kwork webhook with full validation and security
    
    Input validation by Pydantic:
    - order.id: string 1-50 chars, no injection
    - order.title: string 1-500 chars, no injection
    - order.price: float 0.01-1000000
    """
    request_id = get_request_id()
    start_time = time.time()
    
    try:
        logger.info(
            "kwork_webhook_received",
            extra={
                "request_id": request_id,
                "order_id": order.id,
                "title": order.title,
                "price": order.price,
                "validated": True,  # Pydantic validated
            }
        )
        
        # Increment order created metric
        metrics_module.orders_created_total.inc()
        
        # Prepare data for insertion
        data = {
            "id": order.id,
            "title": order.title,
            "price": order.price,
            "description": order.description or "",
            "buyer_id": order.buyer_id
        }
        
        # Insert into database using Supabase REST API
        order_id = await insert_order(data, request_id)
        
        if not order_id:
            logger.error(
                "webhook_insert_failed",
                extra={
                    "request_id": request_id,
                    "order_id": order.id,
                    "error": "Failed to insert order into Supabase"
                }
            )
            raise HTTPException(status_code=500, detail="Failed to insert order")
        
        # Log successful response
        logger.info(
            "webhook_response_success",
            extra={
                "request_id": request_id,
                "order_id": order.id,
                "supabase_id": order_id,
                "status": "inserted",
            }
        )
        
        # At success, log metrics
        metrics_module.orders_completed_total.inc()
        duration = time.time() - start_time
        logger.info(f"Order {order.id} processed in {duration:.2f}s")
        
        return OrderResponse(
            status="success",
            order_id=order.id,
            request_id=request_id,
            message="Order processed successfully"
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper status codes)
        raise
    except Exception as e:
        metrics_module.orders_failed_total.labels(reason=type(e).__name__).inc()
        metrics_module.external_api_errors_total.labels(
            api_name="deepseek",
            error_type=type(e).__name__
        ).inc()
        
        logger.error(
            "webhook_processing_failed",
            extra={
                "request_id": request_id,
                "order_id": order.id,
                "error": str(e),
            },
            exc_info=True
        )
        raise HTTPException(status_code=400, detail="Invalid request")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
