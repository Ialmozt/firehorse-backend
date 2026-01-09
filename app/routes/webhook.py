from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional
import logging
import hmac
import hashlib
from app.config import settings
from app.services.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)
router = APIRouter()

class KworkWebhookPayload(BaseModel):
    """Payload from Kwork webhook"""
    order_id: int
    user_id: int
    title: str
    description: str
    status: str = "pending"

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 12345,
                "user_id": 1,
                "title": "Write SEO article",
                "description": "Need 1000-word article about Python",
                "status": "pending"
            }
        }

class WebhookResponse(BaseModel):
    """Response from webhook"""
    status: str
    message: str
    order_id: int

def verify_kwork_signature(payload: str, signature: str) -> bool:
    """Verify Kwork webhook signature"""
    expected_signature = hmac.new(
        settings.KWORK_WEBHOOK_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

@router.post("/webhook", response_model=WebhookResponse)
async def kwork_webhook(
    payload: KworkWebhookPayload,
    x_kwork_signature: Optional[str] = Header(None),
    request: Request = None
):
    """Handle Kwork webhook"""

    # Verify signature (development: skip for testing)
    if not settings.DEBUG:
        if not x_kwork_signature:
            logger.warning("Missing Kwork signature header")
            raise HTTPException(status_code=401, detail="Missing X-Kwork-Signature header")

        body = await request.body()
        if not verify_kwork_signature(body.decode(), x_kwork_signature):
            logger.warning(f"Invalid signature for order {payload.order_id}")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        logger.info(f"📩 Received webhook for order {payload.order_id}")

        # Initialize Supabase (singleton)
        supabase = SupabaseClient()
        
        # 1. Save to Supabase orders table
        supabase.save_order(payload)
        logger.info(f"✅ Order {payload.order_id} saved to database")
        
        # 2. Queue job in Supabase
        supabase.queue_job(payload.order_id)
        logger.info(f"✅ Job queued for order {payload.order_id}")

        return WebhookResponse(
            status="accepted",
            message=f"Order {payload.order_id} received and queued",
            order_id=payload.order_id
        )

    except Exception as e:
        logger.error(f"❌ Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/webhook/test")
async def test_webhook():
    """Test webhook endpoint (development only)"""
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="Test endpoint not available in production")

    return {
        "status": "ok",
        "message": "Webhook endpoint is working",
        "webhook_url": "/api/webhook"
    }
