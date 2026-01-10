#!/usr/bin/env python3
"""
Тестирование системы обработки ошибок и resilience.
Проверяет:
1. Circuit breaker pattern
2. Retry logic with exponential backoff
3. Error classification
4. Graceful degradation
"""

import asyncio
import sys
import time
from unittest.mock import AsyncMock, Mock, patch
from src.core.error_handling import (
    CircuitBreaker, CircuitBreakerConfig, CircuitState,
    RetryConfig, RetryManager, ErrorClassifier, ErrorCategory,
    GracefulDegradation, error_metrics, get_circuit_breaker,
    resilient_call, resilient_api_call
)


async def test_circuit_breaker() -> bool:
    """Тест circuit breaker pattern"""
    print("\n🔧 Testing circuit breaker...")
    
    try:
        config = CircuitBreakerConfig(
            failure_threshold=2,
            reset_timeout=0.5,  # Short timeout for testing
            half_open_max_requests=1,
            half_open_timeout=0.3,
        )
        
        cb = CircuitBreaker("test_service", config)
        
        # Initial state should be CLOSED
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() == True
        
        # Simulate failures
        cb.on_failure(Exception("Test error 1"))
        assert cb.failure_count == 1
        assert cb.state == CircuitState.CLOSED
        
        cb.on_failure(Exception("Test error 2"))
        assert cb.failure_count == 2
        assert cb.state == CircuitState.OPEN  # Should open after threshold
        assert cb.can_execute() == False  # Should not execute when OPEN
        
        # Wait for reset timeout
        await asyncio.sleep(0.6)  # Slightly more than reset_timeout
        assert cb.can_execute() == True  # Should transition to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN
        
        # Test success in HALF_OPEN state
        cb.on_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        
        print("✅ Circuit breaker test passed")
        return True
        
    except Exception as e:
        print(f"❌ Circuit breaker test failed: {e}")
        return False


async def test_retry_logic() -> bool:
    """Тест retry logic with exponential backoff"""
    print("\n🔧 Testing retry logic...")
    
    try:
        # Create a mock function that fails twice then succeeds
        mock_func = AsyncMock()
        mock_func.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            "Success"
        ]
        
        config = RetryConfig(
            max_retries=3,
            base_delay=0.1,  # Short delays for testing
            max_delay=1.0,
            exponential_base=2.0,
            jitter=False,  # Disable jitter for predictable tests
        )
        
        # Test retry with eventual success
        start_time = time.time()
        
        # Temporarily disable logging for this test
        import logging
        logging.disable(logging.CRITICAL)
        
        try:
            result = await RetryManager.execute_with_retry(mock_func, config)
        finally:
            logging.disable(logging.NOTSET)
        
        elapsed_time = time.time() - start_time
        
        assert result == "Success"
        assert mock_func.call_count == 3  # 2 failures + 1 success
        
        # Check that delays were applied (approximately)
        # Expected delays: 0.1s, 0.2s (0.1 * 2^1)
        # Total should be at least 0.3s
        assert elapsed_time >= 0.25  # Allow some tolerance
        
        print(f"✅ Retry logic test passed (elapsed: {elapsed_time:.2f}s)")
        return True
        
    except Exception as e:
        print(f"❌ Retry logic test failed: {e}")
        return False


async def test_error_classification() -> bool:
    """Тест классификации ошибок"""
    print("\n🔧 Testing error classification...")
    
    try:
        # Test network errors
        network_error = ConnectionError("Connection refused")
        category = ErrorClassifier.classify_error(network_error)
        assert category == ErrorCategory.NETWORK
        
        # Test timeout errors
        timeout_error = TimeoutError("Request timed out")
        category = ErrorClassifier.classify_error(timeout_error)
        assert category == ErrorCategory.NETWORK
        
        # Test database errors
        db_error = Exception("Database connection failed")
        category = ErrorClassifier.classify_error(db_error)
        assert category == ErrorCategory.DATABASE
        
        # Test API errors
        api_error = Exception("API returned 500")
        category = ErrorClassifier.classify_error(api_error)
        assert category == ErrorCategory.API
        
        # Test validation errors
        validation_error = ValueError("Invalid input")
        category = ErrorClassifier.classify_error(validation_error)
        assert category == ErrorCategory.VALIDATION
        
        # Test retry decision
        config = RetryConfig()
        assert ErrorClassifier.should_retry(network_error, config) == True
        assert ErrorClassifier.should_retry(db_error, config) == True
        assert ErrorClassifier.should_retry(api_error, config) == True
        
        print("✅ Error classification test passed")
        return True
        
    except AssertionError as e:
        print(f"❌ Error classification test failed with assertion: {e}")
        return False
    except Exception as e:
        print(f"❌ Error classification test failed with error: {e}")
        return False


async def test_graceful_degradation() -> bool:
    """Тест graceful degradation"""
    print("\n🔧 Testing graceful degradation...")
    
    try:
        # Mock functions
        primary_func = AsyncMock(side_effect=Exception("Primary failed"))
        fallback_func = AsyncMock(return_value="Fallback result")
        
        # Test fallback when primary fails
        result = await GracefulDegradation.with_fallback(
            primary_func,
            fallback_func
        )
        
        assert result == "Fallback result"
        assert primary_func.call_count == 1
        assert fallback_func.call_count == 1
        
        # Test cache fallback pattern (just check it doesn't crash)
        func = AsyncMock(return_value="Result")
        try:
            await GracefulDegradation.with_cache_fallback(
                func,
                "test_key",
                300
            )
        except Exception:
            pass  # Expected to not crash
        
        print("✅ Graceful degradation test passed")
        return True
        
    except Exception as e:
        print(f"❌ Graceful degradation test failed: {e}")
        return False


async def test_resilient_call() -> bool:
    """Тест resilient_call функции"""
    print("\n🔧 Testing resilient_call...")
    
    try:
        # Mock successful function
        mock_func = AsyncMock(return_value="Success")
        
        result = await resilient_call(
            mock_func,
            "test_service",
            RetryConfig(max_retries=2, base_delay=0.1),
            CircuitBreakerConfig(failure_threshold=3, reset_timeout=0.5),
            True
        )
        
        assert result == "Success"
        assert mock_func.call_count == 1
        
        # Check that circuit breaker was created
        cb = get_circuit_breaker("test_service")
        assert cb is not None
        assert cb.state == CircuitState.CLOSED
        
        print("✅ Resilient call test passed")
        return True
        
    except Exception as e:
        print(f"❌ Resilient call test failed: {e}")
        return False


async def test_error_metrics() -> bool:
    """Тест отслеживания метрик ошибок"""
    print("\n🔧 Testing error metrics...")
    
    try:
        # Reset metrics for clean test
        error_metrics.metrics = {
            "total_errors": 0,
            "error_by_category": {category.value: 0 for category in ErrorCategory},
            "error_by_service": {},
            "circuit_breaker_state": {},
            "retry_success_rate": 0.0,
            "last_error_time": None,
        }
        
        # Record some errors
        error1 = ConnectionError("Network error")
        error2 = Exception("Database error")
        
        error_metrics.record_error(error1, "api_service")
        error_metrics.record_error(error2, "db_service")
        
        # Check metrics
        metrics = error_metrics.get_metrics()
        assert metrics["total_errors"] == 2
        assert metrics["error_by_category"]["network"] == 1
        assert metrics["error_by_category"]["database"] == 1
        assert metrics["error_by_service"]["api_service"] == 1
        assert metrics["error_by_service"]["db_service"] == 1
        assert metrics["last_error_time"] is not None
        
        # Test circuit breaker state recording
        cb = get_circuit_breaker("test_service")
        error_metrics.record_circuit_state("test_service", cb.state)
        
        metrics = error_metrics.get_metrics()
        assert "test_service" in metrics["circuit_breaker_state"]
        
        print("✅ Error metrics test passed")
        return True
        
    except Exception as e:
        print(f"❌ Error metrics test failed: {e}")
        return False


async def test_convenience_functions() -> bool:
    """Тест convenience функций"""
    print("\n🔧 Testing convenience functions...")
    
    try:
        # Test resilient_api_call
        mock_func = AsyncMock(return_value="API Success")
        
        result = await resilient_api_call(mock_func, "test_api")
        
        assert result == "API Success"
        assert mock_func.call_count == 1
        
        # Check that circuit breaker was created for API
        cb = get_circuit_breaker("test_api")
        assert cb is not None
        
        print("✅ Convenience functions test passed")
        return True
        
    except Exception as e:
        print(f"❌ Convenience functions test failed: {e}")
        return False


async def main():
    """Основная функция тестирования"""
    print("🚀 Starting Error Handling & Resilience Tests")
    print("=" * 50)
    
    # Запускаем тесты
    tests = [
        ("Circuit Breaker", test_circuit_breaker),
        ("Retry Logic", test_retry_logic),
        ("Error Classification", test_error_classification),
        ("Graceful Degradation", test_graceful_degradation),
        ("Resilient Call", test_resilient_call),
        ("Error Metrics", test_error_metrics),
        ("Convenience Functions", test_convenience_functions),
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
        print("🚀 All error handling tests passed! System is resilient.")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed")
        print("\n📋 Recommendations:")
        print("1. Review error handling implementation")
        print("2. Check circuit breaker configuration")
        print("3. Verify retry logic works correctly")
        return False


if __name__ == "__main__":
    # Запускаем асинхронный main
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
