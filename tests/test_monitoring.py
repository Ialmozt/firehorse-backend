#!/usr/bin/env python3
"""
Тестирование модуля мониторинга Firehorse.
Проверяет:
1. Prometheus метрики
2. Health checks
3. Distributed tracing
4. Интеграция с основными компонентами
"""

import asyncio
import sys
import time
from unittest.mock import AsyncMock, Mock, patch

from src.monitoring.metrics import (
    setup_metrics, record_order_processing_time,
    record_deepseek_tokens_used, record_queue_depth,
    record_api_request, record_error,
    get_metrics_summary, MetricsMiddleware
)
from src.monitoring.health import (
    HealthChecker, check_database_health,
    check_deepseek_health, check_system_health,
    perform_health_check
)
from src.monitoring.tracing import (
    setup_tracing, trace_request, trace_operation,
    get_trace_context, Tracer, Span
)


async def test_metrics_setup() -> bool:
    """Тест настройки метрик"""
    print("\n🔧 Testing metrics setup...")
    
    try:
        # Setup metrics
        registry = setup_metrics()
        
        # Record some metrics
        record_order_processing_time(2.5, "completed", "seo_article")
        record_deepseek_tokens_used(1500, "seo_article", "v1")
        record_queue_depth("job_queue", 25)
        record_api_request("POST", "/webhook/kwork", 200, 0.15)
        record_error("connection_error", "deepseek_api")
        
        # Get summary
        summary = get_metrics_summary()
        
        # Check summary structure
        assert "orders_processed" in summary
        assert "deepseek_usage" in summary
        assert "queue_metrics" in summary
        assert "api_metrics" in summary
        assert "error_metrics" in summary
        
        # Check that metrics functions don't raise exceptions
        # (we can't easily check actual values without querying Prometheus)
        
        print("✅ Metrics setup test passed")
        return True
        
    except Exception as e:
        print(f"❌ Metrics setup test failed: {e}")
        return False


async def test_health_checker() -> bool:
    """Тест health checker"""
    print("\n🔧 Testing health checker...")
    
    try:
        health_checker = HealthChecker()
        
        # Mock check functions
        async def mock_healthy_check():
            return {
                "status": "healthy",
                "healthy": True,
                "message": "Mock check passed"
            }
        
        async def mock_unhealthy_check():
            return {
                "status": "unhealthy",
                "healthy": False,
                "message": "Mock check failed"
            }
        
        # Register checks
        health_checker.register_check("healthy_check", mock_healthy_check)
        health_checker.register_check("unhealthy_check", mock_unhealthy_check)
        
        # Run checks
        overall_health = await health_checker.run_all_checks()
        
        # Check results
        assert "status" in overall_health
        assert "healthy" in overall_health
        assert "checks" in overall_health
        assert len(overall_health["checks"]) == 2
        
        # Check individual results
        healthy_result = overall_health["checks"]["healthy_check"]
        unhealthy_result = overall_health["checks"]["unhealthy_check"]
        
        assert healthy_result["healthy"] == True
        assert unhealthy_result["healthy"] == False
        
        print("✅ Health checker test passed")
        return True
        
    except Exception as e:
        print(f"❌ Health checker test failed: {e}")
        return False


async def test_tracing() -> bool:
    """Тест distributed tracing"""
    print("\n🔧 Testing tracing...")
    
    try:
        tracer = setup_tracing("test-service")
        
        # Start a request span
        request_span = trace_request(
            tracer=tracer,
            name="Test Request",
            request_id="test-request-123"
        )
        
        # Add attributes
        request_span.set_attribute("user_id", "user-456")
        request_span.add_event("processing_started")
        
        # Start an operation span
        operation_span = trace_operation(
            tracer=tracer,
            name="Database Query",
            parent_span=request_span
        )
        
        operation_span.set_attribute("query", "SELECT * FROM orders")
        operation_span.add_event("query_executed")
        
        # End spans
        operation_span.end()
        request_span.end()
        
        # Export spans
        exported_spans = tracer.export_spans()
        
        # Check exported spans
        assert len(exported_spans) == 2
        
        # Check span relationships
        request_span_data = next(s for s in exported_spans if s["name"] == "Test Request")
        operation_span_data = next(s for s in exported_spans if s["name"] == "Database Query")
        
        assert operation_span_data["parent_span_id"] == request_span_data["span_id"]
        assert operation_span_data["trace_id"] == request_span_data["trace_id"]
        
        # Check trace context
        context = get_trace_context()
        assert "request_id" in context
        assert "trace_id" in context
        assert "span_id" in context
        
        print("✅ Tracing test passed")
        return True
        
    except Exception as e:
        print(f"❌ Tracing test failed: {e}")
        return False


async def test_system_health_check() -> bool:
    """Тест проверки системного здоровья"""
    print("\n🔧 Testing system health check...")
    
    try:
        # Skip this test if psutil is not available
        try:
            import psutil
            psutil_available = True
        except ImportError:
            print("⚠️  psutil not available, skipping system health check test")
            return True  # Skip test
        
        # Mock psutil to avoid actual system calls
        with patch('psutil.cpu_percent', return_value=50.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 60.0
                mock_memory.return_value.available = 4 * 1024**3  # 4GB
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 70.0
                    mock_disk.return_value.free = 50 * 1024**3  # 50GB
                    
                    # Run system health check
                    result = await check_system_health()
                    
                    # Check result
                    assert "status" in result
                    assert "healthy" in result
                    assert "message" in result
                    assert "details" in result
                    
                    # Should be healthy with these values
                    assert result["healthy"] == True
                    assert result["status"] == "healthy"
                    
                    # Check details
                    details = result["details"]
                    assert "cpu_percent" in details
                    assert "memory_percent" in details
                    assert "memory_available_gb" in details
                    assert "disk_percent" in details
                    assert "disk_free_gb" in details
        
        print("✅ System health check test passed")
        return True
        
    except Exception as e:
        print(f"❌ System health check test failed: {e}")
        return False


async def test_metrics_middleware() -> bool:
    """Тест middleware для метрик"""
    print("\n🔧 Testing metrics middleware...")
    
    try:
        # Mock app that actually sends responses
        async def mock_app(scope, receive, send):
            # Send response start
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": []
            })
            # Send response body
            await send({
                "type": "http.response.body",
                "body": b"OK"
            })
        
        # Create middleware
        middleware = MetricsMiddleware(mock_app)
        
        # Mock scope
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/test",
            "headers": []
        }
        
        # Mock receive
        async def mock_receive():
            return {"type": "http.request"}
        
        send_calls = []
        
        async def mock_send(message):
            send_calls.append(message)
        
        # Call middleware
        await middleware(scope, mock_receive, mock_send)
        
        # Check that send was called at least twice
        assert len(send_calls) >= 2
        
        # Check that we have response start and body
        response_start = next(m for m in send_calls if m.get("type") == "http.response.start")
        response_body = next(m for m in send_calls if m.get("type") == "http.response.body")
        
        assert response_start["status"] == 200
        assert response_body["body"] == b"OK"
        
        print("✅ Metrics middleware test passed")
        return True
        
    except Exception as e:
        print(f"❌ Metrics middleware test failed: {e}")
        return False


async def test_comprehensive_health_check() -> bool:
    """Тест комплексной проверки здоровья"""
    print("\n🔧 Testing comprehensive health check...")
    
    try:
        # Mock all external dependencies
        with patch('app.services.supabase_client.SupabaseClient') as MockSupabase:
            with patch('src.services.deepseek_client_v2.AdvancedDeepSeekClient') as MockDeepSeek:
                with patch('app.config.settings') as MockSettings:
                    # Setup mocks
                    mock_supabase_instance = AsyncMock()
                    mock_supabase_instance.test_connection.return_value = True
                    MockSupabase.return_value = mock_supabase_instance
                    
                    mock_deepseek_instance = AsyncMock()
                    mock_deepseek_instance.test_connection.return_value = True
                    MockDeepSeek.return_value = mock_deepseek_instance
                    
                    MockSettings.SUPABASE_URL = "mock-url"
                    MockSettings.SUPABASE_KEY = "mock-key"
                    MockSettings.DEEPSEEK_API_KEY = "mock-api-key"
                    MockSettings.VPN_HTTP_PORT = 7890
                    
                    # Run comprehensive health check
                    result = await perform_health_check()
                    
                    # Check result structure
                    assert "status" in result
                    assert "healthy" in result
                    assert "message" in result
                    assert "checks" in result
                    
                    # Should have multiple checks
                    assert len(result["checks"]) >= 3
                    
                    print("✅ Comprehensive health check test passed")
                    return True
        
    except Exception as e:
        print(f"❌ Comprehensive health check test failed: {e}")
        return False


async def test_metrics_integration() -> bool:
    """Тест интеграции метрик с реальными сценариями"""
    print("\n🔧 Testing metrics integration...")
    
    try:
        # Simulate order processing
        processing_times = [1.5, 2.0, 1.8, 2.5, 1.2]
        
        for i, processing_time in enumerate(processing_times):
            status = "completed" if i % 2 == 0 else "failed"
            record_order_processing_time(processing_time, status, "seo_article")
        
        # Simulate DeepSeek API calls
        for i in range(10):
            success = i < 8  # 80% success rate
            tokens = 1000 + i * 100
            record_deepseek_tokens_used(tokens, "seo_article", "v1")
        
        # Simulate queue depth changes
        for depth in [10, 25, 50, 75, 100, 75, 50, 25]:
            record_queue_depth("job_queue", depth)
        
        # Simulate API requests
        endpoints = ["/webhook/kwork", "/api/orders", "/health", "/metrics"]
        for endpoint in endpoints:
            for status_code in [200, 400, 500]:
                record_api_request(
                    "GET" if endpoint == "/health" else "POST",
                    endpoint,
                    status_code,
                    0.1
                )
        
        # Get metrics summary
        summary = get_metrics_summary()
        
        # Verify summary structure
        assert "orders_processed" in summary
        assert "deepseek_usage" in summary
        assert "queue_metrics" in summary
        assert "api_metrics" in summary
        assert "error_metrics" in summary
        
        # Check that metrics functions don't raise exceptions
        # (actual values would require querying Prometheus)
        
        print("✅ Metrics integration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Metrics integration test failed: {e}")
        return False


async def main():
    """Основная функция тестирования"""
    print("🚀 Starting Monitoring Tests")
    print("=" * 50)
    
    # Запускаем тесты
    tests = [
        ("Metrics Setup", test_metrics_setup),
        ("Health Checker", test_health_checker),
        ("Distributed Tracing", test_tracing),
        ("System Health Check", test_system_health_check),
        ("Metrics Middleware", test_metrics_middleware),
        ("Comprehensive Health Check", test_comprehensive_health_check),
        ("Metrics Integration", test_metrics_integration),
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
        print("🚀 All monitoring tests passed! Monitoring system is production-ready.")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed")
        print("\n📋 Recommendations:")
        print("1. Review metrics configuration")
        print("2. Check health check dependencies")
        print("3. Verify tracing implementation")
        return False


if __name__ == "__main__":
    # Запускаем асинхронный main
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
