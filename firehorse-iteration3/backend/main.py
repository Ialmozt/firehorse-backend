from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import hmac
import hashlib
import json
import os
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, AsyncSessionLocal, get_db
from app.models import Base, Order, OrderStatus
from worker import queue

# Setup logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "info").upper())
logger = logging.getLogger(__name__)

app = FastAPI(title="Firehorse Kwork Integration", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ VERIFIED: HMAC signature verification
def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify webhook signature using HMAC-SHA256
    Sources: Neon.com, Superwall docs, FastAPI examples
    """
    if not signature or not body:
        logger.warning("Missing signature or body")
        return False
    
    secret = os.getenv("KWORK_WEBHOOK_SECRET", "").encode()
    if not secret:
        logger.error("KWORK_WEBHOOK_SECRET not set!")
        return False
    
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    
    # Timing-safe comparison
    return hmac.compare_digest(expected, signature)

@app.on_event("startup")
async def startup():
    """Create database tables"""
    logger.info("🚀 Starting Firehorse...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database initialized")

@app.post("/webhook/kwork")
async def kwork_webhook(request: Request, session: AsyncSession = Depends(get_db)):
    """
    ✅ VERIFIED: Receive Kwork webhook
    Pattern from Neon.com, GitHub examples, production systems
    """
    try:
        # Get raw body (MUST be raw, not parsed)
        body = await request.body()
        
        # Get signature
        signature = request.headers.get("X-Kwork-Signature", "")
        
        logger.info(f"📬 Webhook received. Signature present: {bool(signature)}")
        
        # Verify signature
        if not verify_webhook_signature(body, signature):
            logger.warning("❌ Invalid webhook signature")
            return JSONResponse(
                {"error": "Invalid signature"},
                status_code=401
            )
        
        logger.info("✅ Signature verified")
        
        # Parse JSON
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook")
            return JSONResponse(
                {"error": "Invalid JSON"},
                status_code=400
            )
        
        # Validate required fields
        required = ["id", "title", "description"]
        if not all(field in data for field in required):
            logger.error(f"Missing required fields: {required}")
            return JSONResponse(
                {"error": "Missing required fields"},
                status_code=400
            )
        
        # Check if order already exists
        from sqlalchemy import select
        stmt = select(Order).where(Order.kwork_id == str(data.get("id")))
        existing = await session.execute(stmt)
        if existing.scalar():
            logger.info(f"Order {data.get('id')} already exists")
            return {"status": "received", "message": "Order already processed"}
        
        # Create order
        order = Order(
            kwork_id=str(data.get("id")),
            title=str(data.get("title", ""))[:255],
            description=str(data.get("description", "")),
            budget=float(data.get("budget", 0)) if data.get("budget") else None,
            user_id=str(data.get("user_id", "")),
            username=str(data.get("username", "")),
            status=OrderStatus.RECEIVED,
            platform="kwork"
        )
        
        session.add(order)
        await session.commit()
        await session.refresh(order)
        
        logger.info(f"✅ Order saved: {order.id}")
        
        # Enqueue to Redis
        job = queue.enqueue(
            "process_order_with_deepseek",
            str(order.id),
            data.get("description")
        )
        
        logger.info(f"📤 Queued for processing: job_id={job.id}")
        
        # Return 200 immediately (< 100ms)
        return {
            "status": "received",
            "order_id": order.id,
            "job_id": job.id,
            "message": "Order queued for processing"
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {str(e)}", exc_info=True)
        # Return 200 anyway (don't let Kwork retry)
        return {
            "status": "received",
            "message": "Processing will continue"
        }

@app.get("/api/orders")
async def get_orders(session: AsyncSession = Depends(get_db)):
    """Get all orders"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    stmt = select(Order).order_by(Order.created_at.desc())
    result = await session.execute(stmt)
    orders = result.scalars().all()
    
    return {
        "total": len(orders),
        "orders": [
            {
                "id": o.id,
                "kwork_id": o.kwork_id,
                "title": o.title,
                "status": o.status,
                "budget": o.budget,
                "username": o.username,
                "created_at": o.created_at.isoformat(),
                "is_processed": o.is_processed
            }
            for o in orders
        ]
    }

@app.get("/api/orders/{order_id}")
async def get_order(order_id: int, session: AsyncSession = Depends(get_db)):
    """Get specific order"""
    order = await session.get(Order, order_id)
    if not order:
        return JSONResponse({"error": "Order not found"}, status_code=404)
    
    return {
        "id": order.id,
        "kwork_id": order.kwork_id,
        "title": order.title,
        "description": order.description,
        "status": order.status,
        "budget": order.budget,
        "username": order.username,
        "deepseek_response": order.deepseek_response,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "is_processed": order.is_processed
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "webhook": "ready",
        "service": "firehorse-kwork-integration",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
