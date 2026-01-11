import logging
import httpx
from supabase import create_client
from app.config import settings
from datetime import datetime
import uuid
from typing import Dict, Any, Optional

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
            # Create httpx client with SOCKS5 proxy if configured
            if settings.USE_PROXY and settings.proxy_url:
                logger.info(f"🔗 Using {settings.PROXY_TYPE} proxy: {settings.proxy_url}")
                
                # For SOCKS5 proxy, we need to use httpx with PySocks support
                if settings.PROXY_TYPE == "socks5":
                    # httpx supports SOCKS5 via PySocks
                    http_client = httpx.Client(
                        proxies=settings.proxy_url,
                        timeout=30.0
                    )
                else:
                    # For HTTP proxy
                    http_client = httpx.Client(
                        proxies=settings.proxy_url,
                        timeout=30.0
                    )
            else:
                logger.info("🔗 Direct connection (no proxy)")
                http_client = httpx.Client(timeout=30.0)
            
            # Create Supabase client with proxy
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY,
                http_client=http_client
            )
            self.db = self.client
            self._initialized = True
            logger.info("✅ Supabase client initialized with proxy support")
            
        except Exception as e:
            logger.error(f"❌ Supabase init error: {str(e)}")
            raise

    def save_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save order to Supabase orders table"""
        try:
            order_uuid = str(uuid.uuid4())
            data = {
                "id": order_uuid,
                "source_id": order_data["source_id"],
                "topic": order_data["topic"],
                "status": order_data["status"],
                "attempts": order_data["attempts"],
                "final_text": order_data["final_text"],
                "metrics": order_data["metrics"],
                "last_error": order_data["last_error"],
                "created_at": order_data["created_at"],
                "updated_at": order_data["updated_at"]
            }

            response = self.db.table("orders").insert(data).execute()
            logger.info(f"✅ Order saved: {order_data['source_id']} (UUID: {order_uuid})")
            saved_data = response.data[0] if response.data else data
            saved_data["firehorse_id"] = order_uuid
            return saved_data

        except Exception as e:
            logger.error(f"❌ Error saving order: {str(e)}")
            raise

    def get_order_by_source_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get order from Supabase by source_id"""
        try:
            response = self.db.table("orders").select("*").eq("source_id", source_id).execute()
            if response.data:
                logger.info(f"✅ Retrieved order: {source_id}")
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"❌ Error getting order: {str(e)}")
            raise

    def update_order_status(self, order_uuid: str, status: str, error_message: Optional[str] = None) -> Dict[str, Any]:
        """Update order status"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }

            if error_message:
                update_data["last_error"] = error_message

            response = self.db.table("orders").update(update_data).eq("id", order_uuid).execute()
            logger.info(f"✅ Order {order_uuid} status updated to {status}")
            return response.data[0] if response.data else update_data
        except Exception as e:
            logger.error(f"❌ Error updating order status: {str(e)}")
            raise

    def create_order_event(self, order_uuid: str, stage: str, level: str, message: str, meta: Optional[Dict] = None) -> Dict[str, Any]:
        """Create audit event for order"""
        try:
            event_data = {
                "order_id": order_uuid,
                "stage": stage,
                "level": level,
                "message": message,
                "meta": meta or {},
                "created_at": datetime.utcnow().isoformat()
            }

            response = self.db.table("order_events").insert(event_data).execute()
            logger.info(f"✅ Order event created: {stage} - {level}")
            return response.data[0] if response.data else event_data
        except Exception as e:
            logger.error(f"❌ Error creating order event: {str(e)}")
            raise

    def update_order_with_content(self, order_uuid: str, content: str, usage_metrics: Optional[Dict] = None) -> Dict[str, Any]:
        """Update order with generated content"""
        try:
            update_data = {
                "final_text": content,
                "status": "completed",
                "updated_at": datetime.utcnow().isoformat()
            }

            if usage_metrics:
                current_order = self.db.table("orders").select("metrics").eq("id", order_uuid).execute()
                if current_order.data:
                    current_metrics = current_order.data[0].get("metrics", {})
                    current_metrics["deepseek_usage"] = usage_metrics
                    update_data["metrics"] = current_metrics

            response = self.db.table("orders").update(update_data).eq("id", order_uuid).execute()
            logger.info(f"✅ Order {order_uuid} updated with content ({len(content)} chars)")
            return response.data[0] if response.data else update_data
        except Exception as e:
            logger.error(f"❌ Error updating order with content: {str(e)}")
            raise
