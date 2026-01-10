import logging
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

    def save_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save order to Supabase orders table.
        
        Args:
            order_data: Parsed order data from KworkParser
            
        Returns:
            Dict with saved order data including UUID
        """
        try:
            # Generate UUID for the order
            order_uuid = str(uuid.uuid4())
            
            # Prepare data for orders table
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
            logger.info(f"✅ Order saved to Supabase: {order_data['source_id']} (UUID: {order_uuid})")
            
            # Return saved data with UUID
            saved_data = response.data[0] if response.data else data
            saved_data["firehorse_id"] = order_uuid
            return saved_data
            
        except Exception as e:
            logger.error(f"❌ Error saving order: {str(e)}")
            raise

    def create_pgmq_job(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create PGMQ job in job_queue.
        
        Args:
            order_data: Order data including UUID
            
        Returns:
            Dict with job creation result
        """
        try:
            # Prepare job message for PGMQ
            job_message = {
                "order_id": order_data.get("firehorse_id"),
                "source_id": order_data.get("source_id"),
                "topic": order_data.get("topic"),
                "status": "queued",
                "created_at": datetime.utcnow().isoformat(),
                "metadata": order_data.get("metrics", {})
            }
            
            # Execute PGMQ send function
            # Note: This assumes the fh_ingress function exists in the database
            response = self.db.rpc(
                "fh_ingress",
                {
                    "source_id": order_data["source_id"],
                    "topic": order_data["topic"]
                }
            ).execute()
            
            logger.info(f"✅ PGMQ job created for order: {order_data['source_id']}")
            return {
                "success": True,
                "message": "Job queued in PGMQ",
                "order_id": order_data.get("firehorse_id"),
                "pgmq_result": response.data if hasattr(response, 'data') else response
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating PGMQ job: {str(e)}")
            
            # Fallback: Try direct SQL if RPC fails
            try:
                logger.warning("⚠️ Trying fallback PGMQ method...")
                # This would require raw SQL execution, which we can't do directly here
                # For now, log the error and continue
                return {
                    "success": False,
                    "message": f"PGMQ job creation failed: {str(e)}",
                    "fallback_used": True
                }
            except Exception as fallback_error:
                logger.error(f"❌ Fallback also failed: {str(fallback_error)}")
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
                update_data["attempts"] = self.db.table("orders").select("attempts").eq("id", order_uuid).execute().data[0]["attempts"] + 1
            
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
        """
        Update order with generated content and metrics.
        
        Args:
            order_uuid: Order UUID
            content: Generated content from DeepSeek
            usage_metrics: API usage metrics
            
        Returns:
            Updated order data
        """
        try:
            update_data = {
                "final_text": content,
                "status": "completed",
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Add usage metrics to existing metrics
            if usage_metrics:
                # Get current metrics
                current_order = self.db.table("orders").select("metrics").eq("id", order_uuid).execute()
                if current_order.data:
                    current_metrics = current_order.data[0].get("metrics", {})
                    # Merge usage metrics
                    current_metrics["deepseek_usage"] = usage_metrics
                    update_data["metrics"] = current_metrics
            
            response = self.db.table("orders").update(update_data).eq("id", order_uuid).execute()
            logger.info(f"✅ Order {order_uuid} updated with content ({len(content)} chars)")
            return response.data[0] if response.data else update_data
        except Exception as e:
            logger.error(f"❌ Error updating order with content: {str(e)}")
            raise
