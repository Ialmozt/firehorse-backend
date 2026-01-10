"""
PGMQ Worker for Firehorse - processes jobs from queue_orders.
"""
import asyncio
import logging
import time
from typing import Dict, Any, Optional
import asyncpg
from app.config import settings
from app.services.supabase_client import SupabaseClient
from src.services.deepseek_client import DeepSeekClient

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PGMQWorker:
    """Worker that polls PGMQ queue and processes jobs"""
    
    def __init__(self):
        self.supabase = SupabaseClient()
        self.deepseek = DeepSeekClient()
        self.db_pool: Optional[asyncpg.Pool] = None
        self.running = False
        
        # Configuration
        self.poll_interval = 5  # seconds between polls
        self.max_retries = 3
        self.visibility_timeout = 300  # 5 minutes
        
    async def connect_to_database(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            # Build connection string from environment
            conn_info = {
                "host": settings.DATABASE_HOST or "db.yommcknuizxkwpmpvlmp.supabase.co",
                "port": settings.DATABASE_PORT or "5432",
                "database": settings.DATABASE_NAME or "postgres",
                "user": settings.DATABASE_USER or "postgres",
                "password": settings.DATABASE_PASSWORD or "bkOFQ9jiln6JE82v",
            }
            
            # Create connection pool
            self.db_pool = await asyncpg.create_pool(
                host=conn_info["host"],
                port=conn_info["port"],
                database=conn_info["database"],
                user=conn_info["user"],
                password=conn_info["password"],
                min_size=1,
                max_size=5
            )
            
            logger.info("✅ Connected to PostgreSQL database")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def poll_job_queue(self) -> Optional[Dict[str, Any]]:
        """
        Poll job_queue for next available job.
        
        Returns:
            Job data if available, None otherwise
        """
        if not self.db_pool:
            logger.error("❌ Database not connected")
            return None
        
        try:
            async with self.db_pool.acquire() as conn:
                # Use PGMQ's read function with visibility timeout
                query = """
                SELECT * FROM pgmq.read(
                    'job_queue',
                    1,  -- number of messages
                    $1   -- visibility timeout in seconds
                );
                """
                
                result = await conn.fetch(query, self.visibility_timeout)
                
                if result and len(result) > 0:
                    job = dict(result[0])
                    logger.info(f"📥 Received job: {job.get('msg_id')}")
                    return job
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Error polling job queue: {str(e)}")
            return None
    
    async def process_job(self, job: Dict[str, Any]) -> bool:
        """
        Process a single job from the queue.
        
        Args:
            job: Job data from PGMQ
            
        Returns:
            True if successful, False otherwise
        """
        job_id = job.get("msg_id")
        message = job.get("message", {})
        
        try:
            logger.info(f"🔧 Processing job {job_id}")
            
            # Extract order information
            order_id = message.get("order_id")
            source_id = message.get("source_id")
            topic = message.get("topic", "general")
            
            if not order_id:
                logger.error(f"❌ Job {job_id} missing order_id")
                await self.move_to_dlq(job_id, "Missing order_id")
                return False
            
            # Get order details from Supabase
            order = await self.get_order_details(order_id)
            if not order:
                logger.error(f"❌ Order {order_id} not found")
                await self.move_to_dlq(job_id, f"Order {order_id} not found")
                return False
            
            # Update order status to processing
            await self.supabase.update_order_status(order_id, "processing")
            await self.supabase.create_order_event(
                order_id, "worker_started", "INFO", f"Worker started processing job {job_id}"
            )
            
            # Generate content with DeepSeek
            prompt = self.build_prompt(order)
            logger.info(f"🤖 Generating content for order {order_id}, topic: {topic}")
            
            result = await self.deepseek.generate_content(prompt, topic)
            
            if result["success"]:
                # Update order with generated content
                await self.supabase.update_order_with_content(
                    order_id,
                    result["content"],
                    result.get("usage", {})
                )
                
                # Create success event
                await self.supabase.create_order_event(
                    order_id, "content_generated", "INFO",
                    f"Content generated successfully ({len(result['content'])} chars)",
                    {"model": result.get("model"), "usage": result.get("usage")}
                )
                
                logger.info(f"✅ Job {job_id} completed successfully")
                await self.acknowledge_job(job_id)
                return True
            else:
                # Handle failure
                error_msg = result.get("error", "Unknown error")
                logger.error(f"❌ DeepSeek failed for job {job_id}: {error_msg}")
                
                # Update order with error
                await self.supabase.update_order_status(
                    order_id, "failed", error_msg
                )
                
                # Create error event
                await self.supabase.create_order_event(
                    order_id, "content_generation_failed", "ERROR",
                    f"DeepSeek API error: {error_msg}"
                )
                
                # Move to DLQ after max retries
                attempts = order.get("attempts", 0) + 1
                if attempts >= self.max_retries:
                    await self.move_to_dlq(job_id, f"Max retries exceeded: {error_msg}")
                else:
                    await self.reject_job(job_id)
                
                return False
                
        except Exception as e:
            logger.error(f"❌ Error processing job {job_id}: {str(e)}", exc_info=True)
            
            # Try to update order status
            try:
                if 'order_id' in locals():
                    await self.supabase.update_order_status(
                        order_id, "failed", f"Worker error: {str(e)}"
                    )
            except:
                pass
            
            await self.move_to_dlq(job_id, f"Worker exception: {str(e)}")
            return False
    
    async def get_order_details(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order details from Supabase"""
        try:
            # Use existing Supabase client method
            order = self.supabase.get_order_by_source_id(f"kwork_{order_id}")
            if not order:
                # Try direct UUID lookup
                order = self.supabase.get_order_by_source_id(order_id)
            return order
        except Exception as e:
            logger.error(f"❌ Error getting order details: {str(e)}")
            return None
    
    def build_prompt(self, order: Dict[str, Any]) -> str:
        """Build prompt for DeepSeek from order data"""
        title = order.get("title", "")
        description = order.get("description", "")
        metrics = order.get("metrics", {})
        
        # Extract additional info from metrics
        kwork_title = metrics.get("title", "")
        kwork_description = metrics.get("description", "")
        
        # Build comprehensive prompt
        prompt_parts = []
        
        if title:
            prompt_parts.append(f"Title: {title}")
        elif kwork_title:
            prompt_parts.append(f"Original Title: {kwork_title}")
        
        if description:
            prompt_parts.append(f"Description: {description}")
        elif kwork_description:
            prompt_parts.append(f"Original Description: {kwork_description}")
        
        # Add topic context
        topic = order.get("topic", "general")
        prompt_parts.append(f"Content Type: {topic}")
        
        return "\n\n".join(prompt_parts)
    
    async def acknowledge_job(self, job_id: int) -> bool:
        """Acknowledge (delete) job from queue after successful processing"""
        if not self.db_pool:
            return False
        
        try:
            async with self.db_pool.acquire() as conn:
                query = "SELECT * FROM pgmq.delete('job_queue', $1);"
                await conn.execute(query, job_id)
                logger.debug(f"✅ Acknowledged job {job_id}")
                return True
        except Exception as e:
            logger.error(f"❌ Error acknowledging job {job_id}: {str(e)}")
            return False
    
    async def reject_job(self, job_id: int) -> bool:
        """Reject job (make it visible again) for retry"""
        if not self.db_pool:
            return False
        
        try:
            async with self.db_pool.acquire() as conn:
                query = "SELECT * FROM pgmq.set_vt('job_queue', $1, 0);"
                await conn.execute(query, job_id)
                logger.debug(f"🔄 Rejected job {job_id} for retry")
                return True
        except Exception as e:
            logger.error(f"❌ Error rejecting job {job_id}: {str(e)}")
            return False
    
    async def move_to_dlq(self, job_id: int, reason: str) -> bool:
        """Move job to dead letter queue"""
        if not self.db_pool:
            return False
        
        try:
            async with self.db_pool.acquire() as conn:
                # First archive to DLQ
                query = """
                SELECT * FROM pgmq.send(
                    'dlq_job_queue',
                    jsonb_build_object(
                        'original_job_id', $1,
                        'reason', $2,
                        'moved_at', now()
                    )
                );
                """
                await conn.execute(query, job_id, reason)
                
                # Then delete from main queue
                await self.acknowledge_job(job_id)
                
                logger.warning(f"⚠️ Moved job {job_id} to DLQ: {reason}")
                return True
        except Exception as e:
            logger.error(f"❌ Error moving job {job_id} to DLQ: {str(e)}")
            return False
    
    async def run(self):
        """Main worker loop"""
        logger.info("🚀 Starting PGMQ Worker...")
        
        # Connect to database
        if not await self.connect_to_database():
            logger.error("❌ Failed to connect to database, exiting")
            return
        
        # Test DeepSeek connection
        if not await self.deepseek.test_connection():
            logger.warning("⚠️ DeepSeek connection test failed, but continuing...")
        
        self.running = True
        logger.info(f"✅ Worker started, polling every {self.poll_interval} seconds")
        
        try:
            while self.running:
                try:
                    # Poll for jobs
                    job = await self.poll_job_queue()
                    
                    if job:
                        # Process the job
                        await self.process_job(job)
                    else:
                        # No jobs available, wait before polling again
                        await asyncio.sleep(self.poll_interval)
                        
                except asyncio.CancelledError:
                    logger.info("🛑 Worker cancelled")
                    break
                except Exception as e:
                    logger.error(f"❌ Error in worker loop: {str(e)}", exc_info=True)
                    await asyncio.sleep(self.poll_interval * 2)  # Backoff on error
                    
        except KeyboardInterrupt:
            logger.info("🛑 Worker stopped by user")
        finally:
            self.running = False
            if self.db_pool:
                await self.db_pool.close()
            logger.info("🛑 Worker shutdown complete")
    
    async def stop(self):
        """Stop the worker"""
        self.running = False
        logger.info("🛑 Stopping worker...")


async def main():
    """Main entry point"""
    worker = PGMQWorker()
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        await worker.stop()
    except Exception as e:
        logger.error(f"❌ Fatal worker error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
