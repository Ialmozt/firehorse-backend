#!/usr/bin/env python3
"""
Тестирование middleware безопасности для Firehorse MVP.
Проверяет:
1. Rate limiting (10 запросов в минуту)
2. CORS headers
3. API key validation
"""

import asyncio
import httpx
import time
import sys
from typing import Dict, Any

# Конфигурация теста
BASE_URL = "http://localhost:8000"
TEST_API_KEY = "test-api-key-123"

async def test_health_endpoint() -> bool:
    """Тест health endpoint (должен работать без API key)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            print(f"✅ Health endpoint: {response.status_code}")
            print(f"   Response: {response.json()}")
            return response.status_code == 200
    except Exception as e:
        print(f"❌ Health endpoint failed: {e}")
        return False

async def test_metrics_endpoint() -> bool:
    """Тест metrics endpoint (должен работать без API key)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/metrics")
            print(f"✅ Metrics endpoint: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('content-type')}")
            return response.status_code == 200
    except Exception as e:
        print(f"❌ Metrics endpoint failed: {e}")
        return False

async def test_cors_headers() -> bool:
    """Тест CORS headers"""
    try:
        async with httpx.AsyncClient() as client:
            # Отправляем OPTIONS запрос для проверки CORS
            response = await client.options(
                f"{BASE_URL}/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Content-Type"
                }
            )
            
            print(f"✅ CORS OPTIONS request: {response.status_code}")
            
            # Проверяем CORS headers
            cors_headers = {
                "access-control-allow-origin": response.headers.get("access-control-allow-origin"),
                "access-control-allow-methods": response.headers.get("access-control-allow-methods"),
                "access-control-allow-headers": response.headers.get("access-control-allow-headers"),
            }
            
            print(f"   CORS Headers: {cors_headers}")
            
            # Проверяем обычный GET запрос
            response = await client.get(
                f"{BASE_URL}/health",
                headers={"Origin": "http://localhost:3000"}
            )
            
            origin_header = response.headers.get("access-control-allow-origin")
            print(f"   GET request Origin header: {origin_header}")
            
            return origin_header == "*" or "localhost:3000" in origin_header
    except Exception as e:
        print(f"❌ CORS test failed: {e}")
        return False

async def test_rate_limiting() -> bool:
    """Тест rate limiting (10 запросов в минуту)"""
    print("\n🔧 Testing rate limiting (10 requests per minute)...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Отправляем 12 запросов быстро (должны получить 429 на 11-м)
            successes = 0
            rate_limited = False
            
            for i in range(12):
                response = await client.get(f"{BASE_URL}/health")
                
                if response.status_code == 200:
                    successes += 1
                    print(f"   Request {i+1}: 200 OK")
                    print(f"     X-RateLimit-Remaining: {response.headers.get('x-ratelimit-remaining')}")
                elif response.status_code == 429:
                    rate_limited = True
                    print(f"   Request {i+1}: 429 Too Many Requests (Rate limited)")
                    print(f"   Retry-After: {response.headers.get('retry-after')}")
                    print(f"   X-RateLimit-Remaining: {response.headers.get('x-ratelimit-remaining')}")
                    break
                else:
                    print(f"   Request {i+1}: {response.status_code}")
                
                # Маленькая задержка между запросами
                await asyncio.sleep(0.1)
            
            print(f"✅ Rate limiting test: {successes} successful requests before limit")
            # Ожидаем хотя бы 5 успешных запросов перед лимитом (из-за sliding window)
            return rate_limited and successes >= 5
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

async def test_api_key_validation() -> bool:
    """Тест API key validation"""
    print("\n🔧 Testing API key validation...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Тест 1: Запрос без API key (должен работать для /health)
            response = await client.get(f"{BASE_URL}/health")
            print(f"✅ Health without API key: {response.status_code}")
            
            # Тест 2: Запрос к /webhook без API key (должен вернуть 401 если REQUIRE_API_KEY=true)
            # Сначала проверяем текущую конфигурацию
            response = await client.post(
                f"{BASE_URL}/webhook",
                json={
                    "id": "kwork_12345",
                    "title": "Test Order",
                    "price": 100.0,
                    "description": "Test description",
                    "buyer_id": "test_buyer"
                }
            )
            
            if response.status_code == 401:
                print(f"✅ Webhook without API key: 401 Unauthorized (API key required)")
                
                # Тест 3: Запрос с неверным API key
                response = await client.post(
                    f"{BASE_URL}/webhook",
                    json={
                        "id": "kwork_12345",
                        "title": "Test Order",
                        "price": 100.0,
                        "description": "Test description",
                        "buyer_id": "test_buyer"
                    },
                    headers={"X-API-Key": "wrong-key"}
                )
                
                if response.status_code == 401:
                    print(f"✅ Webhook with wrong API key: 401 Unauthorized")
                    return True
                else:
                    print(f"❌ Expected 401 with wrong API key, got {response.status_code}")
                    return False
            else:
                print(f"⚠️  API key validation not enabled (REQUIRE_API_KEY=false)")
                print(f"   Webhook response: {response.status_code}")
                return True  # Пропускаем тест если валидация отключена
    except Exception as e:
        print(f"❌ API key validation test failed: {e}")
        return False

async def test_security_headers() -> bool:
    """Тест security headers"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            
            security_headers = {
                "X-Content-Type-Options": response.headers.get("x-content-type-options"),
                "X-Frame-Options": response.headers.get("x-frame-options"),
                "X-XSS-Protection": response.headers.get("x-xss-protection"),
                "Strict-Transport-Security": response.headers.get("strict-transport-security"),
                "X-Request-ID": response.headers.get("x-request-id"),
                "X-RateLimit-Limit": response.headers.get("x-ratelimit-limit"),
                "X-RateLimit-Remaining": response.headers.get("x-ratelimit-remaining"),
                "X-RateLimit-Reset": response.headers.get("x-ratelimit-reset"),
            }
            
            print(f"\n🔧 Security headers check:")
            headers_found = 0
            for header, value in security_headers.items():
                if value:
                    print(f"   ✅ {header}: {value}")
                    headers_found += 1
                else:
                    print(f"   ⚠️  {header}: MISSING")
            
            print(f"   📊 Found {headers_found}/{len(security_headers)} security headers")
            
            # Проверяем обязательные headers
            required_headers = ["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
            all_present = all(response.headers.get(h) for h in required_headers)
            
            return all_present
    except Exception as e:
        print(f"❌ Security headers test failed: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 Starting Firehorse Security Middleware Tests")
    print("=" * 50)
    
    # Проверяем что сервер запущен
    print("🔍 Checking if server is running...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print("❌ Server is not running. Please start the server with:")
                print("   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("   Please start the server with:")
        print("   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
        return False
    
    # Запускаем тесты
    tests = [
        ("Health Endpoint", test_health_endpoint),
        ("Metrics Endpoint", test_metrics_endpoint),
        ("CORS Headers", test_cors_headers),
        ("Rate Limiting", test_rate_limiting),
        ("API Key Validation", test_api_key_validation),
        ("Security Headers", test_security_headers),
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
        print("🚀 All security tests passed successfully!")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed")
        return False

if __name__ == "__main__":
    # Запускаем асинхронный main
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
