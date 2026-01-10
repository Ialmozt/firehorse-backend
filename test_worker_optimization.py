#!/usr/bin/env python3
"""
Тестирование оптимизированного воркера.
Проверяет:
1. Adaptive polling intervals
2. Batch processing
3. Concurrency control
4. Health monitoring
5. Graceful shutdown
"""

import asyncio
import sys
import time
from unittest.mock import AsyncMock, Mock, patch
from src.worker_optimized import (
    WorkerConfig, AdaptivePollingManager, BatchProcessor,
    HealthMonitor, OptimizedWorker
)


async def test_adaptive_polling() -> bool:
    """Тест адаптивного polling интервалов"""
    print("\n🔧 Testing adaptive polling...")
    
    try:
        config = WorkerConfig(
            min_poll_interval=5.0,
            max_poll_interval=60.0,
            adaptive_polling=True,
            max_queue_depth_threshold=100
        )
        
        # Test 1: Empty queue
        polling_manager = AdaptivePollingManager(config)
        for _ in range(5):
            interval = polling_manager.update_interval(0)
        
        # After multiple empty queue updates, should use max interval
        if interval != config.max_poll_interval:
            print(f"❌ Empty queue test failed: got {interval}, expected {config.max_poll_interval}")
            return False
        
        # Test 2: High load
        polling_manager = AdaptivePollingManager(config)
        for _ in range(5):
            interval = polling_manager.update_interval(150)
        
        # After multiple high load updates, should use min interval
        if interval != config.min_poll_interval:
            print(f"❌ High load test failed: got {interval}, expected {config.min_poll_interval}")
            return False
        
        # Test 3: Medium load
        polling_manager = AdaptivePollingManager(config)
        interval = polling_manager.update_interval(50)
        if not (config.min_poll_interval <= interval <= config.max_poll_interval):
            print(f"❌ Medium load test failed: {interval} not in range [{config.min_poll_interval}, {config.max_poll_interval}]")
            return False
        
        # Test stats
        stats = polling_manager.get_stats()
        if "current_interval" not in stats:
            print("❌ Stats missing current_interval")
            return False
        if "queue_depth_history" not in stats:
            print("❌ Stats missing queue_depth_history")
            return False
        
        print("✅ Adaptive polling test passed")
        return True
        
    except Exception as e:
        print(f"❌ Adaptive polling test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_batch_processing() -> bool:
    """Тест batch processing"""
    print("\n🔧 Testing batch processing...")
    
    try:
        config = WorkerConfig(
            min_batch_size=1,
            max_batch_size=10,
            batch_timeout=0.5,
            max_concurrent_tasks=2
        )
        
        batch_processor = BatchProcessor(config)
        
        # Mock jobs
        jobs = [
            {"id": 1, "data": "job1"},
            {"id": 2, "data": "job2"},
            {"id": 3, "data": "job3"},
        ]
        
        # Mock processing function
        async def mock_process(job):
            await asyncio.sleep(0.1)
            return f"processed_{job['id']}"
        
        # Process batch
        start_time = time.time()
        results = await batch_processor.process_batch(jobs, mock_process)
        elapsed_time = time.time() - start_time
        
        assert len(results) == 3
        
        # Check that concurrency was limited (should take ~0.2s for 3 jobs with 2 concurrent)
        assert elapsed_time >= 0.15  # At least 0.1s per batch of 2
        
        # Check results
        for result in results:
            assert "job" in result
            assert "success" in result
            if result["success"]:
                assert "result" in result
            else:
                assert "error" in result
        
        print(f"✅ Batch processing test passed (elapsed: {elapsed_time:.2f}s)")
        return True
        
    except Exception as e:
        print(f"❌ Batch processing test failed: {e}")
        return False


async def test_health_monitoring() -> bool:
    """Тест health monitoring"""
    print("\n🔧 Testing health monitoring...")
    
    try:
        health_monitor = HealthMonitor()
        
        # Record some jobs
        health_monitor.record_job_start()
        health_monitor.record_job_completion(True, 1.5)
        
        health_monitor.record_job_start()
        health_monitor.record_job_completion(False, 2.0)
        
        # Record DeepSeek calls
        health_monitor.record_deepseek_call(True)
        health_monitor.record_deepseek_call(False)
        
        # Update queue depth
        health_monitor.update_queue_depth(25)
        
        # Get health status
        health_status = health_monitor.health_check()
        
        # Check metrics
        assert health_status["jobs_processed"] == 2
        assert health_status["success_rate"] == 0.5
        assert health_status["queue_depth"] == 25
        assert health_status["deepseek_api_calls"] == 2
        assert health_status["deepseek_error_rate"] == 0.5
        assert "status" in health_status
        assert "timestamp" in health_status
        
        # Test degraded health
        for _ in range(10):
            health_monitor.record_job_start()
            health_monitor.record_job_completion(False, 1.0)
        
        health_status = health_monitor.health_check()
        if health_status["success_rate"] < 0.8:
            assert health_status["status"] == "degraded"
        
        print("✅ Health monitoring test passed")
        return True
        
    except Exception as e:
        print(f"❌ Health monitoring test failed: {e}")
        return False


async def test_worker_initialization() -> bool:
    """Тест инициализации воркера"""
    print("\n🔧 Testing worker initialization...")
    
    try:
        # Mock clients
        mock_supabase = Mock()
        mock_deepseek = Mock()
        
        # Create worker
        worker = OptimizedWorker(mock_supabase, mock_deepseek)
        
        # Check initialization
        assert worker.supabase == mock_supabase
        assert worker.deepseek == mock_deepseek
        assert worker.is_running == False
        assert worker.shutdown_requested == False
        assert len(worker.current_tasks) == 0
        
        # Check components
        assert isinstance(worker.polling_manager, AdaptivePollingManager)
        assert isinstance(worker.batch_processor, BatchProcessor)
        assert isinstance(worker.health_monitor, HealthMonitor)
        
        # Test shutdown request
        worker.request_shutdown()
        assert worker.shutdown_requested == True
        
        print("✅ Worker initialization test passed")
        return True
        
    except Exception as e:
        print(f"❌ Worker initialization test failed: {e}")
        return False


async def test_batch_size_calculation() -> bool:
    """Тест расчета batch size"""
    print("\n🔧 Testing batch size calculation...")
    
    try:
        config = WorkerConfig(
            min_batch_size=1,
            max_batch_size=10
        )
        
        worker = OptimizedWorker(Mock(), Mock(), config)
        
        # Test with low queue depth
        batch_size = worker._calculate_batch_size(0)
        assert batch_size == config.min_batch_size
        
        # Test with medium queue depth
        batch_size = worker._calculate_batch_size(5)
        assert batch_size == 5
        
        # Test with high queue depth
        batch_size = worker._calculate_batch_size(15)
        assert batch_size == config.max_batch_size
        
        # Test edge cases
        batch_size = worker._calculate_batch_size(1)
        assert batch_size == 1
        
        batch_size = worker._calculate_batch_size(10)
        assert batch_size == 10
        
        print("✅ Batch size calculation test passed")
        return True
        
    except Exception as e:
        print(f"❌ Batch size calculation test failed: {e}")
        return False


async def test_graceful_shutdown() -> bool:
    """Тест graceful shutdown"""
    print("\n🔧 Testing graceful shutdown...")
    
    try:
        config = WorkerConfig(
            shutdown_timeout=1.0  # Short timeout for testing
        )
        
        worker = OptimizedWorker(Mock(), Mock(), config)
        
        # Add some mock tasks
        async def mock_task():
            await asyncio.sleep(0.5)
            return "done"
        
        task1 = asyncio.create_task(mock_task())
        task2 = asyncio.create_task(mock_task())
        worker.current_tasks = [task1, task2]
        
        # Request shutdown
        worker.request_shutdown()
        
        # Wait for shutdown
        start_time = time.time()
        await worker._wait_for_shutdown()
        elapsed_time = time.time() - start_time
        
        # Should complete within timeout
        assert elapsed_time <= config.shutdown_timeout + 0.5  # Allow some buffer
        
        # Worker should be stopped
        assert worker.is_running == False
        
        print(f"✅ Graceful shutdown test passed (elapsed: {elapsed_time:.2f}s)")
        return True
        
    except Exception as e:
        print(f"❌ Graceful shutdown test failed: {e}")
        return False


async def test_concurrency_control() -> bool:
    """Тест контроля concurrency"""
    print("\n🔧 Testing concurrency control...")
    
    try:
        config = WorkerConfig(
            max_concurrent_tasks=2,
            max_concurrent_deepseek=1
        )
        
        batch_processor = BatchProcessor(config)
        
        # Track concurrent executions
        concurrent_tasks = 0
        max_concurrent = 0
        task_lock = asyncio.Lock()
        
        async def track_concurrent(job):
            nonlocal concurrent_tasks, max_concurrent
            async with task_lock:
                concurrent_tasks += 1
                max_concurrent = max(max_concurrent, concurrent_tasks)
            
            await asyncio.sleep(0.1)
            
            async with task_lock:
                concurrent_tasks -= 1
            
            return f"processed_{job['id']}"
        
        # Create jobs
        jobs = [{"id": i} for i in range(5)]
        
        # Process with concurrency control
        results = await batch_processor.process_batch(jobs, track_concurrent)
        
        # Check that concurrency was limited
        assert max_concurrent <= config.max_concurrent_tasks
        
        # Test DeepSeek concurrency limit
        deepseek_concurrent = 0
        max_deepseek_concurrent = 0
        deepseek_lock = asyncio.Lock()
        
        async def track_deepseek_concurrent(job):
            nonlocal deepseek_concurrent, max_deepseek_concurrent
            async with deepseek_lock:
                deepseek_concurrent += 1
                max_deepseek_concurrent = max(max_deepseek_concurrent, deepseek_concurrent)
            
            await asyncio.sleep(0.1)
            
            async with deepseek_lock:
                deepseek_concurrent -= 1
            
            return f"deepseek_{job['id']}"
        
        # Process with DeepSeek limit
        tasks = []
        for job in jobs[:3]:
            task = batch_processor.process_with_deepseek_limit(
                job, track_deepseek_concurrent
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Check DeepSeek concurrency was limited
        assert max_deepseek_concurrent <= config.max_concurrent_deepseek
        
        print("✅ Concurrency control test passed")
        return True
        
    except Exception as e:
        print(f"❌ Concurrency control test failed: {e}")
        return False


async def main():
    """Основная функция тестирования"""
    print("🚀 Starting Worker Optimization Tests")
    print("=" * 50)
    
    # Запускаем тесты
    tests = [
        ("Adaptive Polling", test_adaptive_polling),
        ("Batch Processing", test_batch_processing),
        ("Health Monitoring", test_health_monitoring),
        ("Worker Initialization", test_worker_initialization),
        ("Batch Size Calculation", test_batch_size_calculation),
        ("Graceful Shutdown", test_graceful_shutdown),
        ("Concurrency Control", test_concurrency_control),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 Testing: {test_name}")
        print(f"{'='*50}")
        
        try:
            success = await test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Вывод результатов
    print(f"\n{'='*50}")
    print("📊 TEST RESULTS")
    print(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🚀 All worker optimization tests passed! Worker is production-ready.")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed")
        print("\n📋 Recommendations:")
        print("1. Review worker configuration")
        print("2. Check concurrency limits")
        print("3. Verify graceful shutdown logic")
        return False


if __name__ == "__main__":
    # Запускаем асинхронный main
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
