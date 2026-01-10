from fastapi import APIRouter, HTTPException, Request, Header, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import hmac
import hashlib
import json
from app.config import settings
from app.services.supabase_client import SupabaseClient
from app.services.kwork_parser import KworkParser, validate_kwork_payload

logger = logging.getLogger(__name__)
router = APIRouter()

class KworkWebhookPayload(BaseModel):
    """Payload from Kwork webhook"""
    order_id: int
    user_id: int
    title: str
    description: Optional[str] = ""
    status: Optional[str] = "pending"
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "order_id": 12345,
                "user_id": 1,
                "title": "Write SEO article about Python",
                "description": "Need 1000-word article about Python programming",
                "status": "pending",
                "metadata": {
                    "category": "programming",
                    "budget": 5000,
                    "deadline": "2026-01-15"
                }
            }
        }

class WebhookResponse(BaseModel):
    """Response from webhook"""
    status: str
    message: str
    order_id: int
    firehorse_id: Optional[str] = None
    timestamp: str

def verify_kwork_signature(payload: str, signature: str) -> bool:
    """Verify Kwork webhook signature"""
    if not settings.KWORK_WEBHOOK_SECRET:
        logger.warning("KWORK_WEBHOOK_SECRET not set, skipping signature verification")
        return True
        
    expected_signature = hmac.new(
        settings.KWORK_WEBHOOK_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

@router.post("/webhook/kwork", response_model=WebhookResponse, status_code=status.HTTP_202_ACCEPTED)
async def kwork_webhook(
    payload: KworkWebhookPayload,
    x_kwork_signature: Optional[str] = Header(None),
    request: Request = None
):
    """
    Handle Kwork webhook.
    
    Accepts JSON from Kwork, parses it, saves to Supabase orders table,
    and creates PGMQ job in queue_orders.
    
    Returns 202 Accepted with order_id.
    """
    # Verify signature (skip in debug mode)
    if not settings.DEBUG and settings.KWORK_WEBHOOK_SECRET:
        if not x_kwork_signature:
            logger.warning("Missing Kwork signature header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Kwork-Signature header"
            )

        body = await request.body()
        if not verify_kwork_signature(body.decode(), x_kwork_signature):
            logger.warning(f"Invalid signature for order {payload.order_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

    try:
        logger.info(f"📩 Received Kwork webhook for order {payload.order_id}")
        
        # Convert Pydantic model to dict for validation
        payload_dict = payload.dict()
        
        # Validate payload structure
        if not validate_kwork_payload(payload_dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload structure"
            )
        
        # Parse Kwork payload to Firehorse format
        parser = KworkParser()
        firehorse_order = parser.parse_webhook_payload(payload_dict)
        
        # Initialize Supabase client
        supabase = SupabaseClient()
        
        # 1. Save to Supabase orders table
        saved_order = supabase.save_order(firehorse_order)
        firehorse_id = saved_order.get("firehorse_id")
        logger.info(f"✅ Order saved to database: {firehorse_order['source_id']} (UUID: {firehorse_id})")
        
        # 2. Create audit event
        supabase.create_order_event(
            order_uuid=firehorse_id,
            stage="webhook_received",
            level="INFO",
            message=f"Kwork order {payload.order_id} received via webhook",
            meta={"kwork_payload": payload_dict}
        )
        
        # 3. Create PGMQ job in queue_orders
        pgmq_result = supabase.create_pgmq_job(saved_order)
        if pgmq_result.get("success", False):
            logger.info(f"✅ PGMQ job created for order: {firehorse_order['source_id']}")
            
            # Update order status to processing
            supabase.update_order_status(firehorse_id, "processing")
            
            # Create processing event
            supabase.create_order_event(
                order_uuid=firehorse_id,
                stage="job_queued",
                level="INFO",
                message=f"Job queued in PGMQ for processing",
                meta={"pgmq_result": pgmq_result}
            )
        else:
            logger.warning(f"⚠️ PGMQ job creation had issues: {pgmq_result.get('message')}")
            
            # Create warning event
            supabase.create_order_event(
                order_uuid=firehorse_id,
                stage="job_queue_warning",
                level="WARN",
                message=f"PGMQ job creation had issues: {pgmq_result.get('message')}",
                meta={"pgmq_result": pgmq_result}
            )
        
        # Create response
        response = parser.create_webhook_response(
            order_id=str(payload.order_id),
            firehorse_order_id=firehorse_id
        )
        
        logger.info(f"✅ Webhook processing complete for order {payload.order_id}")
        return WebhookResponse(**response)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {str(e)}", exc_info=True)
        
        # Try to create error event if we have firehorse_id
        try:
            if 'firehorse_id' in locals():
                supabase.create_order_event(
                    order_uuid=firehorse_id,
                    stage="webhook_error",
                    level="ERROR",
                    message=f"Error processing webhook: {str(e)}",
                    meta={"error": str(e)}
                )
        except:
            pass  # Ignore errors in error handling
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)[:100]}"
        )

@router.get("/webhook/kwork/test")
async def test_kwork_webhook():
    """Test Kwork webhook endpoint (development only)"""
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test endpoint not available in production"
        )

    return {
        "status": "ok",
        "message": "Kwork webhook endpoint is working",
        "endpoint": "/api/webhook/kwork",
        "method": "POST",
        "example_payload": {
            "order_id": 12345,
            "user_id": 1,
            "title": "Test order",
            "description": "Test description",
            "status": "pending"
        }
    }

@router.post("/webhook/kwork/simulate")
async def simulate_kwork_webhook(payload: KworkWebhookPayload):
    """
    Simulate Kwork webhook (development only).
    
    Useful for testing without actual Kwork webhook.
    """
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation endpoint not available in production"
        )
    
    # Call the actual webhook handler
    from . import kwork_webhook
    return await kwork_webhook(payload, None, None)
