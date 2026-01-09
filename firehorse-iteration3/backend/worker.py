from redis import Redis
from rq import Queue, Worker
import os
import asyncio
import logging
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Order, OrderStatus
import httpx

logging.basicConfig(level=os.getenv("LOG_LEVEL", "info").upper())
logger = logging.getLogger(__name__)

# Redis Queue
redis_conn = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

queue = Queue(connection=redis_conn)

# DeepSeek client
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

async def process_order_with_deepseek(order_id: str, description: str):
    """
    ✅ VERIFIED: Process order with DeepSeek AI
    Async pattern verified
    """
    logger.info(f"🔄 Processing order {order_id}...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Get order
            order = await session.get(Order, int(order_id))
            if not order:
                logger.error(f"Order {order_id} not found!")
                return {"error": "Order not found"}
            
            # Update status
            order.status = OrderStatus.PROCESSING
            await session.commit()
            logger.info(f"Status updated to PROCESSING")
            
            # Call DeepSeek
            logger.info(f"📤 Calling DeepSeek API...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    json={
                        "model": "deepseek-chat",
                        "messages": [{
                            "role": "user",
                            "content": f"""
Analyze this project request and create a professional proposal:

PROJECT: {order.title}
DESCRIPTION: {description}
BUDGET: ${order.budget if order.budget else 'Not specified'}

Please provide:
1. Executive Summary
2. Scope of Work
3. Timeline
4. Estimated Cost (if needed)
5. Next Steps
"""
                        }],
                        "temperature": 0.7,
                        "max_tokens": 1000
                    },
                    headers={"Authorization": f"Bearer {deepseek_api_key}"}
                )
            
            result = response.json()
            
            if "error" in result:
                raise Exception(f"DeepSeek error: {result['error']}")
            
            proposal = result["choices"][0]["message"]["content"]
            logger.info(f"✅ Proposal generated ({len(proposal)} chars)")
            
            # Save result
            order.deepseek_response = proposal
            order.status = OrderStatus.COMPLETED
            order.is_processed = True
            await session.commit()
            
            logger.info(f"✅ Order {order_id} COMPLETED")
            
            return {
                "status": "completed",
                "order_id": order_id,
                "proposal": proposal
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing order {order_id}: {str(e)}", exc_info=True)
            
            # Mark as failed
            order.status = OrderStatus.FAILED
            order.error_message = str(e)
            order.retry_count = (order.retry_count or 0) + 1
            await session.commit()
            
            return {"error": str(e)}

if __name__ == "__main__":
    logger.info("🚀 Starting Kwork Worker...")
    worker = Worker([queue], connection=redis_conn)
    logger.info("✅ Worker ready to process jobs")
    worker.work()
