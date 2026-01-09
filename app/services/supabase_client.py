import logging
from supabase import create_client
from app.config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

class SupabaseClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        try:
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            self.db = self.client
            self._initialized = True
            logger.info("✅ Supabase client initialized")
        except Exception as e:
            logger.error(f"❌ Supabase init error: {str(e)}")
            raise

    def save_order(self, payload):
        """Save order to Supabase (sync)"""
        try:
            data = {
                "order_id": payload.order_id,
                "user_id": payload.user_id,
                "title": payload.title,
                "description": payload.description,
                "status": payload.status,
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = self.db.table("orders").insert(data).execute()
            logger.info(f"✅ Order {payload.order_id} saved to Supabase")
            return response.data
        except Exception as e:
            logger.error(f"❌ Error saving order: {str(e)}")
            raise

    def queue_job(self, order_id: int):
        """Queue job in Supabase (sync)"""
        try:
            job_data = {
                "order_id": order_id,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = self.db.table("jobs").insert(job_data).execute()
            logger.info(f"✅ Job queued for order {order_id}")
            return response.data
        except Exception as e:
            logger.error(f"❌ Error queueing job: {str(e)}")
            raise

    def get_order(self, order_id: int):
        """Get order from Supabase"""
        try:
            response = self.db.table("orders").select("*").eq("order_id", order_id).execute()
            logger.info(f"✅ Retrieved order {order_id}")
            return response.data
        except Exception as e:
            logger.error(f"❌ Error getting order: {str(e)}")
            raise

    def update_order_status(self, order_id: int, status: str):
        """Update order status"""
        try:
            response = self.db.table("orders").update(
                {"status": status, "updated_at": datetime.utcnow().isoformat()}
            ).eq("order_id", order_id).execute()
            logger.info(f"✅ Order {order_id} status updated to {status}")
            return response.data
        except Exception as e:
            logger.error(f"❌ Error updating order status: {str(e)}")
            raise
