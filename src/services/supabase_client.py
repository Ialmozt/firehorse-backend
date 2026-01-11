"""
Simple Supabase client for Firehorse worker.
Provides basic database operations for job processing.
"""

import logging
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Simple Supabase client for database operations"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url.rstrip('/')
        self.supabase_key = supabase_key
        self.headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
    async def get_queue_depth(self) -> int:
        """Get current queue depth from PGMQ"""
        try:
            # Simplified implementation
            # In production, this would query PGMQ queue
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/orders",
                    params={"status": "eq.queued"},
                    headers=self.headers
                )
                response.raise_for_status()
                orders = response.json()
                return len(orders)
        except Exception as e:
            logger.error(f"Failed to get queue depth: {e}")
            return 0
    
    async def read_jobs(self, batch_size: int, visibility_timeout: int) -> List[Dict[str, Any]]:
        """Read jobs from PGMQ queue"""
        try:
            # Simplified implementation
            # In production, this would use PGMQ's read function
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/orders",
                    params={
                        "status": "eq.queued",
                        "limit": batch_size,
                        "order": "created_at.asc"
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                orders = response.json()
                
                # Convert to job format
                jobs = []
                for order in orders:
                    jobs.append({
                        "id": order.get("id"),
                        "order_id": order.get("id"),
                        "content_type": order.get("content_type", "seo_article"),
                        "prompt_version": order.get("prompt_version", "v1"),
                        "temperature": order.get("temperature", 0.7),
                        "max_tokens": order.get("max_tokens", 2000),
                        "attempts": order.get("attempts", 0),
                        "created_at": order.get("created_at")
                    })
                
                return jobs
        except Exception as e:
            logger.error(f"Failed to read jobs: {e}")
            return []
    
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order details"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/orders",
                    params={"id": f"eq.{order_id}"},
                    headers=self.headers
                )
                response.raise_for_status()
                orders = response.json()
                return orders[0] if orders else None
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None
    
    async def update_order_content(self, order_id: str, content: str, status: str) -> bool:
        """Update order with generated content"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.supabase_url}/rest/v1/orders",
                    params={"id": f"eq.{order_id}"},
                    json={
                        "content": content,
                        "status": status,
                        "updated_at": "now()"
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to update order {order_id}: {e}")
            return False
    
    async def update_order_status(self, order_id: str, status: str, error_message: str = None) -> bool:
        """Update order status"""
        try:
            update_data = {
                "status": status,
                "updated_at": "now()"
            }
            if error_message:
                update_data["error_message"] = error_message
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.supabase_url}/rest/v1/orders",
                    params={"id": f"eq.{order_id}"},
                    json=update_data,
                    headers=self.headers
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to update order status {order_id}: {e}")
            return False
    
    async def update_job_attempts(self, job_id: str, attempts: int, error: str) -> bool:
        """Update job attempts (for retry logic)"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.supabase_url}/rest/v1/orders",
                    params={"id": f"eq.{job_id}"},
                    json={
                        "attempts": attempts,
                        "error_message": error,
                        "updated_at": "now()"
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to update job attempts {job_id}: {e}")
            return False
    
    async def acknowledge_job(self, job_id: str) -> bool:
        """Acknowledge job completion"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.supabase_url}/rest/v1/orders",
                    params={"id": f"eq.{job_id}"},
                    json={
                        "status": "completed",
                        "updated_at": "now()"
                    },
                    headers=self.headers
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to acknowledge job {job_id}: {e}")
            return False
