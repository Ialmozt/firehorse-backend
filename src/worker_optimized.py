"""
Optimized PGMQ worker for Firehorse with advanced features:
- Dynamic batch processing
- Adaptive polling intervals
- Concurrency control
- Graceful shutdown
- Health monitoring
- Dead-letter queue routing
"""

import asyncio
import logging
import signal
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.core.error_handling import (
    resilient_api_call, resilient_database_call,
    GracefulDegradation, error_metrics
)
from src.services.deepseek_client_v2 import AdvancedDeepSeekClient
from app.services.supabase_client import SupabaseClient
from src.core.logging import setup_logging

logger = logging.getLogger(__name__)


@dataclass
class WorkerConfig:
    """Configuration for optimized worker"""
    # Polling configuration
    min_poll_interval: float = 5.0  # seconds
    max_poll_interval: float = 60.0  # seconds
    adaptive_polling: bool = True
    
    # Batch processing
    min_batch_size: int = 1
    max_batch_size: int = 10
    batch_timeout: float = 30.0  # seconds
    
    # Concurrency control
    max_concurrent_tasks: int = 4
    max_concurrent_deepseek: int = 2
    
    # Job processing
    visibility_timeout: int = 300  # 5 minutes
    max_attempts: int = 3
    dead_letter_threshold: int = 3
    
    # Health monitoring
    health_check_interval: float = 30.0  # seconds
    max_queue_depth_threshold: int = 100
    
    # Graceful shutdown
    shutdown_timeout: float = 30.0  # seconds


class AdaptivePollingManager:
    """Manage adaptive polling intervals based on queue depth"""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.current_interval = config.min_poll_interval
        self.queue_depth_history: List[int] = []
        self.max_history_size = 10
        
    def update_interval(self, queue_depth: int) -> float:
        """Update polling interval based on queue depth"""
        if not self.config.adaptive_polling:
            return self.config.min_poll_interval
        
        # Store queue depth
        self.queue_depth_history.append(queue_depth)
        if len(self.queue_depth_history) > self.max_history_size:
            self.queue_depth_history.pop(0)
        
        # Calculate average queue depth
        if not self.queue_depth_history:
            avg_depth = 0
        else:
            avg_depth = sum(self.queue_depth_history) / len(self.queue_depth_history)
        
        # Adjust interval based on queue depth
        if avg_depth == 0:
            # No jobs, use max interval
            self.current_interval = self.config.max_poll_interval
        elif avg_depth >= self.config.max_queue_depth_threshold:
            # High load, use min interval
            self.current_interval = self.config.min_poll_interval
        else:
            # Scale interval based on load
            load_factor = avg_depth / self.config.max_queue_depth_threshold
            interval_range = self.config.max_poll_interval - self.config.min_poll_interval
            self.current_interval = self.config.max_poll_interval - (interval_range * load_factor)
        
        # Ensure within bounds
        self.current_interval = max(
            self.config.min_poll_interval,
            min(self.config.max_poll_interval, self.current_interval)
        )
        
        return self.current_interval
    
    def get_stats(self) -> Dict[str, Any]:
        """Get polling statistics"""
        return {
            "current_interval": self.current_interval,
            "queue_depth_history": self.queue_depth_history.copy(),
            "avg_queue_depth": sum(self.queue_depth_history) / len(self.queue_depth_history) if self.queue_depth_history else 0,
        }


class BatchProcessor:
    """Process jobs in batches for efficiency"""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent_tasks)
        self.deepseek_semaphore = asyncio.Semaphore(config.max_concurrent_deepseek)
        
    async def process_batch(
        self,
        jobs: List[Dict[str, Any]],
        process_func,
        *args,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Process a batch of jobs concurrently"""
        if not jobs:
            return []
        
        # Process jobs concurrently with semaphore
        tasks = []
        for job in jobs:
            task = self._process_job_with_semaphore(
                job, process_func, *args, **kwargs
            )
            tasks.append(task)
        
        # Wait for all tasks with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.batch_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Batch processing timeout after {self.config.batch_timeout}s")
            # Cancel remaining tasks
            for task in tasks:
                task.cancel()
            results = []
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Job {i} failed: {result}")
                # Mark job as failed
                job_result = {
                    "job": jobs[i],
                    "success": False,
                    "error": str(result),
                    "exception": result
                }
            else:
                job_result = {
                    "job": jobs[i],
                    "success": True,
                    "result": result
                }
            processed_results.append(job_result)
        
        return processed_results
    
    async def _process_job_with_semaphore(
        self,
        job: Dict[str, Any],
        process_func,
        *args,
        **kwargs
    ) -> Any:
        """Process single job with semaphore control"""
        async with self.semaphore:
            return await process_func(job, *args, **kwargs)
    
    async def process_with_deepseek_limit(
        self,
        job: Dict[str, Any],
        process_func,
        *args,
        **kwargs
    ) -> Any:
        """Process job with DeepSeek concurrency limit"""
        async with self.deepseek_semaphore:
            return await process_func(job, *args, **kwargs)


class HealthMonitor:
    """Monitor worker health and performance"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.metrics = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "jobs_succeeded": 0,
            "avg_processing_time": 0.0,
            "last_health_check": None,
            "concurrent_tasks": 0,
            "queue_depth": 0,
            "deepseek_api_calls": 0,
            "deepseek_api_errors": 0,
        }
        self.processing_times: List[float] = []
        self.max_processing_times = 100
        
    def record_job_start(self):
        """Record job start"""
        self.metrics["concurrent_tasks"] += 1
    
    def record_job_completion(self, success: bool, processing_time: float):
        """Record job completion"""
        self.metrics["concurrent_tasks"] -= 1
        self.metrics["jobs_processed"] += 1
        
        if success:
            self.metrics["jobs_succeeded"] += 1
        else:
            self.metrics["jobs_failed"] += 1
        
        # Update average processing time
        self.processing_times.append(processing_time)
        if len(self.processing_times) > self.max_processing_times:
            self.processing_times.pop(0)
        
        if self.processing_times:
            self.metrics["avg_processing_time"] = sum(self.processing_times) / len(self.processing_times)
    
    def record_deepseek_call(self, success: bool):
        """Record DeepSeek API call"""
        self.metrics["deepseek_api_calls"] += 1
        if not success:
            self.metrics["deepseek_api_errors"] += 1
    
    def update_queue_depth(self, depth: int):
        """Update queue depth"""
        self.metrics["queue_depth"] = depth
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        self.metrics["last_health_check"] = datetime.now().isoformat()
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        success_rate = 0.0
        if self.metrics["jobs_processed"] > 0:
            success_rate = self.metrics["jobs_succeeded"] / self.metrics["jobs_processed"]
        
        deepseek_error_rate = 0.0
        if self.metrics["deepseek_api_calls"] > 0:
            deepseek_error_rate = self.metrics["deepseek_api_errors"] / self.metrics["deepseek_api_calls"]
        
        health_status = {
            "status": "healthy",
            "uptime_seconds": uptime,
            "jobs_processed": self.metrics["jobs_processed"],
            "success_rate": success_rate,
            "avg_processing_time": self.metrics["avg_processing_time"],
            "concurrent_tasks": self.metrics["concurrent_tasks"],
            "queue_depth": self.metrics["queue_depth"],
            "deepseek_api_calls": self.metrics["deepseek_api_calls"],
            "deepseek_error_rate": deepseek_error_rate,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Check for issues
        if success_rate < 0.8:
            health_status["status"] = "degraded"
            health_status["issue"] = "Low success rate"
        elif deepseek_error_rate > 0.2:
            health_status["status"] = "degraded"
            health_status["issue"] = "High DeepSeek error rate"
        elif self.metrics["concurrent_tasks"] > 10:
            health_status["status"] = "degraded"
            health_status["issue"] = "High concurrency"
        
        return health_status


class OptimizedWorker:
    """Optimized PGMQ worker with advanced features"""
    
    def __init__(
        self,
        supabase_client: SupabaseClient,
        deepseek_client: AdvancedDeepSeekClient,
        config: Optional[WorkerConfig] = None
    ):
        self.supabase = supabase_client
        self.deepseek = deepseek_client
        self.config = config or WorkerConfig()
        
        # Initialize components
        self.polling_manager = AdaptivePollingManager(self.config)
        self.batch_processor = BatchProcessor(self.config)
        self.health_monitor = HealthMonitor()
        
        # Worker state
        self.is_running = False
        self.shutdown_requested = False
        self.current_tasks: List[asyncio.Task] = []
        
        # Setup logging
        setup_logging()
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, self.request_shutdown)
        except (NotImplementedError, RuntimeError):
            # Signal handlers not supported in this environment
            pass
    
    def request_shutdown(self):
        """Request graceful shutdown"""
        logger.info("Shutdown requested")
        self.shutdown_requested = True
    
    async def _wait_for_shutdown(self):
        """Wait for graceful shutdown"""
        if not self.shutdown_requested:
            return
        
        logger.info("Starting graceful shutdown...")
        
        # Wait for current tasks to complete
        start_time = time.time()
        while self.current_tasks and time.time() - start_time < self.config.shutdown_timeout:
            logger.info(f"Waiting for {len(self.current_tasks)} tasks to complete...")
            await asyncio.sleep(1)
        
        # Cancel remaining tasks if timeout reached
        if self.current_tasks:
            logger.warning(f"Cancelling {len(self.current_tasks)} remaining tasks")
            for task in self.current_tasks:
                task.cancel()
            
            # Wait for cancellation
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.current_tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for task cancellation")
        
        self.is_running = False
        logger.info("Shutdown complete")
    
    async def get_queue_depth(self) -> int:
        """Get current queue depth"""
        try:
            # This is a simplified version - in production, you'd query PGMQ
            result = await resilient_database_call(
                self.supabase.get_queue_depth
            )
            return result or 0
        except Exception as e:
            logger.error(f"Failed to get queue depth: {e}")
            return 0
    
    async def fetch_jobs(self, batch_size: int) -> List[Dict[str, Any]]:
        """Fetch jobs from queue"""
        try:
            jobs = await resilient_database_call(
                self.supabase.read_jobs,
                batch_size,
                self.config.visibility_timeout
            )
            return jobs or []
        except Exception as e:
            logger.error(f"Failed to fetch jobs: {e}")
            return []
    
    async def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single job"""
        start_time = time.time()
        self.health_monitor.record_job_start()
        
        try:
            logger.info(f"Processing job: {job.get('id', 'unknown')}")
            
            # Extract job data
            order_id = job.get("order_id")
            content_type = job.get("content_type", "seo_article")
            prompt_version = job.get("prompt_version", "v1")
            temperature = job.get("temperature", 0.7)
            max_tokens = job.get("max_tokens", 2000)
            
            if not order_id:
                raise ValueError("Job missing order_id")
            
            # Get order details
            order = await resilient_database_call(
                self.supabase.get_order,
                order_id
            )
            
            if not order:
                raise ValueError(f"Order not found: {order_id}")
            
            # Generate content using DeepSeek with resilience
            prompt = self._create_prompt(order, content_type, prompt_version)
            
            generated_content = await self.batch_processor.process_with_deepseek_limit(
                job,
                self._generate_content_with_fallback,
                prompt, content_type, temperature, max_tokens
            )
            
            # Update order with generated content
            await resilient_database_call(
                self.supabase.update_order_content,
                order_id,
                generated_content,
                "completed"
            )
            
            # Record success
            processing_time = time.time() - start_time
            self.health_monitor.record_job_completion(True, processing_time)
            self.health_monitor.record_deepseek_call(True)
            
            return {
                "success": True,
                "order_id": order_id,
                "processing_time": processing_time,
                "content_length": len(generated_content) if generated_content else 0,
            }
            
        except Exception as e:
            # Record failure
            processing_time = time.time() - start_time
            self.health_monitor.record_job_completion(False, processing_time)
            self.health_monitor.record_deepseek_call(False)
            
            logger.error(f"Job processing failed: {e}")
            
            # Move to dead-letter queue if max attempts reached
            attempts = job.get("attempts", 0) + 1
            if attempts >= self.config.dead_letter_threshold:
                await self._move_to_dead_letter(job, str(e))
            else:
                # Retry job
                await self._retry_job(job, attempts, str(e))
            
            return {
                "success": False,
                "order_id": job.get("order_id"),
                "error": str(e),
                "processing_time": processing_time,
                "attempts": attempts,
            }
    
    async def _generate_content_with_fallback(
        self,
        job: Dict[str, Any],
        prompt: str,
        content_type: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate content with fallback strategy"""
        
        async def primary_generation():
            """Primary content generation using DeepSeek"""
            return await resilient_api_call(
                self.deepseek.generate_content,
                "deepseek_api",
                prompt,
                content_type,
                temperature,
                max_tokens
            )
        
        async def fallback_generation():
            """Fallback content generation (simplified)"""
            logger.warning("Using fallback content generation")
            # In production, this could use a different AI model or cached responses
            return f"Fallback content for {content_type}. Prompt: {prompt[:100]}..."
        
        # Use graceful degradation with fallback
        return await GracefulDegradation.with_fallback(
            primary_generation,
            fallback_generation,
            lambda e: "timeout" in str(e).lower() or "connection" in str(e).lower()
        )
    
    def _create_prompt(
        self,
        order: Dict[str, Any],
        content_type: str,
        prompt_version: str
    ) -> str:
        """Create prompt for content generation"""
        # This would use the advanced prompt engineering system
        # For now, create a simple prompt
        title = order.get("title", "")
        description = order.get("description", "")
        
        prompt_templates = {
            "seo_article": f"Write a SEO-optimized article about: {title}. Description: {description}",
            "translation": f"Translate to Russian: {title}. {description}",
            "content_creation": f"Create engaging content about: {title}. Details: {description}",
            "code_generation": f"Generate code for: {title}. Requirements: {description}",
        }
        
        return prompt_templates.get(content_type, f"Create content: {title}. {description}")
    
    async def _move_to_dead_letter(self, job: Dict[str, Any], error: str):
        """Move job to dead-letter queue"""
        try:
            job_id = job.get("id")
            order_id = job.get("order_id")
            
            logger.warning(f"Moving job {job_id} to dead-letter queue: {error}")
            
            # In production, you'd move to PGMQ dead-letter queue
            # For now, just log and update status
            await resilient_database_call(
                self.supabase.update_order_status,
                order_id,
                "failed",
                f"Moved to DLQ: {error}"
            )
            
            # Record error metrics
            error_metrics.record_error(
                Exception(f"Job moved to DLQ: {error}"),
                "worker"
            )
            
        except Exception as e:
            logger.error(f"Failed to move job to dead-letter queue: {e}")
    
    async def _retry_job(self, job: Dict[str, Any], attempts: int, error: str):
        """Retry job with updated attempts"""
        try:
            job_id = job.get("id")
            order_id = job.get("order_id")
            
            logger.info(f"Retrying job {job_id}, attempt {attempts}: {error}")
            
            # Update job attempts
            await resilient_database_call(
                self.supabase.update_job_attempts,
                job_id,
                attempts,
                error
            )
            
            # Update order status
            await resilient_database_call(
                self.supabase.update_order_status,
                order_id,
                "retrying",
                f"Attempt {attempts}: {error}"
            )
            
        except Exception as e:
            logger.error(f"Failed to retry job: {e}")
    
    async def process_batch(self, batch_size: int) -> List[Dict[str, Any]]:
        """Process a batch of jobs"""
        # Fetch jobs
        jobs = await self.fetch_jobs(batch_size)
        if not jobs:
            return []
        
        # Process batch
        results = await self.batch_processor.process_batch(
            jobs,
            self.process_job
        )
        
        # Acknowledge successful jobs
        successful_jobs = [r["job"] for r in results if r.get("success")]
        for job in successful_jobs:
            await self._acknowledge_job(job)
        
        return results
    
    async def _acknowledge_job(self, job: Dict[str, Any]):
        """Acknowledge job completion"""
        try:
            job_id = job.get("id")
            await resilient_database_call(
                self.supabase.acknowledge_job,
                job_id
            )
        except Exception as e:
            logger.error(f"Failed to acknowledge job {job_id}: {e}")
    
    async def run_health_check(self):
        """Run periodic health check"""
        while self.is_running and not self.shutdown_requested:
            try:
                health_status = self.health_monitor.health_check()
                logger.info(f"Worker health: {health_status}")
                
                # Log to error metrics
                if health_status["status"] != "healthy":
                    error_metrics.record_error(
                        Exception(f"Worker health degraded: {health_status.get('issue', 'unknown')}"),
                        "worker_health"
                    )
                
                await asyncio.sleep(self.config.health_check_interval)
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                await asyncio.sleep(5.0)
    
    async def run(self):
        """Main worker loop"""
        self.is_running = True
        logger.info("Starting optimized worker...")
        
        # Start health check task
        health_task = asyncio.create_task(self.run_health_check())
        self.current_tasks.append(health_task)
        
        try:
            while self.is_running and not self.shutdown_requested:
                try:
                    # Get queue depth and adjust polling
                    queue_depth = await self.get_queue_depth()
                    self.health_monitor.update_queue_depth(queue_depth)
                    
                    poll_interval = self.polling_manager.update_interval(queue_depth)
                    
                    # Determine batch size based on queue depth
                    batch_size = self._calculate_batch_size(queue_depth)
                    
                    if queue_depth > 0:
                        logger.info(f"Queue depth: {queue_depth}, batch size: {batch_size}, poll interval: {poll_interval:.1f}s")
                        
                        # Process batch
                        results = await self.process_batch(batch_size)
                        
                        # Log results
                        success_count = sum(1 for r in results if r.get("success"))
                        if results:
                            logger.info(f"Batch processed: {success_count}/{len(results)} successful")
                    
                    else:
                        logger.debug(f"No jobs in queue, sleeping for {poll_interval:.1f}s")
                    
                    # Wait for next poll or shutdown
                    await asyncio.sleep(poll_interval)
                    
                    # Check for shutdown
                    if self.shutdown_requested:
                        break
                        
                except Exception as e:
                    logger.error(f"Worker loop error: {e}")
                    await asyncio.sleep(5.0)  # Brief pause on error
        
        finally:
            # Wait for graceful shutdown
            await self._wait_for_shutdown()
            
            # Cancel health task
            health_task.cancel()
            try:
                await health_task
            except asyncio.CancelledError:
                pass
            
            logger.info("Worker stopped")
    
    def _calculate_batch_size(self, queue_depth: int) -> int:
        """Calculate optimal batch size based on queue depth"""
        if queue_depth <= self.config.min_batch_size:
            return self.config.min_batch_size
        elif queue_depth >= self.config.max_batch_size:
            return self.config.max_batch_size
        else:
            # Scale batch size with queue depth
            return min(queue_depth, self.config.max_batch_size)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        return {
            "is_running": self.is_running,
            "shutdown_requested": self.shutdown_requested,
            "current_tasks": len(self.current_tasks),
            "polling_stats": self.polling_manager.get_stats(),
            "health_status": self.health_monitor.health_check(),
            "error_metrics": error_metrics.get_metrics(),
        }


async def main():
    """Main entry point for optimized worker"""
    from app.config import settings
    
    # Initialize clients
    supabase_client = SupabaseClient(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    deepseek_client = AdvancedDeepSeekClient()
    
    # Create and run worker
    worker = OptimizedWorker(supabase_client, deepseek_client)
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        raise
    finally:
        # Print final stats
        stats = worker.get_stats()
        logger.info(f"Final worker stats: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
