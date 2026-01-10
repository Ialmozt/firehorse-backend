#!/usr/bin/env python3
"""
Быстрый тест безопасности для Firehorse MVP.
Проверяет основные security features.
"""

import httpx
import asyncio
import time

BASE_URL = "http://localhost:8000"

async def test_security_headers():
    """Тест security headers"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        
        security_headers = {
            "X-Content-Type-Options": response.headers.get("x-content-type-options"),
            "X-Frame-Options": response.headers.get("x-frame-options"),
            "X-XSS-Protection": response.headers.get("x-xss-protection"),
            "Strict-Transport-Security": response.headers.get("strict-transport-security"),
            "X-Request-ID": response.headers.get("x-request-id"),
        }
        
        print("🔒 Security Headers Check:")
        for header, value in security_headers.items():
            if value:
                print(f"   ✅ {header}: {value}")
            else:
                print(f"   ❌ {header}: MISSING")
        
        # Проверяем обязательные headers
        required = ["X-Content-Type-Options", "X-Frame-Options", "X-Request-ID"]
        all_present = all(response.headers.get(h.lower()) for h in required)
        
        return all_present

async def test_cors():
    """Тест CORS"""
    async with httpx.AsyncClient() as client:
        # Проверяем OPTIONS запрос
        response = await client.options(
            f"{BASE_URL}/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        print("\n🌐 CORS Check:")
        print(f"   OPTIONS Status: {response.status_code}")
        
        origin = response.headers.get("access-control-allow-origin")
        if origin == "*" or "localhost:3000" in origin:
            print(f"   ✅ CORS Origin: {origin}")
            return True
        else:
            print(f"   ❌ CORS Origin: {origin}")
            return False

async def test_rate_limit_info():
    """Тест информации о rate limit (без превышения лимита)"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        
        print("\n⏱️ Rate Limit Headers Check:")
        rate_headers = {
            "X-RateLimit-Limit": response.headers.get("x-ratelimit-limit"),
            "X-RateLimit-Remaining": response.headers.get("x-ratelimit-remaining"),
            "X-RateLimit-Reset": response.headers.get("x-ratelimit-reset"),
        }
        
        for header, value in rate_headers.items():
            if value:
                print(f"   ✅ {header}: {value}")
            else:
                print(f"   ❌ {header}: MISSING")
        
        # Проверяем что headers присутствуют
        return all(rate_headers.values())

async def test_api_endpoints():
    """Тест доступности API endpoints"""
    async with httpx.AsyncClient() as client:
        endpoints = [
            ("/health", "GET"),
            ("/metrics", "GET"),
        ]
        
        print("\n🔗 API Endpoints Check:")
        all_ok = True
        
        for endpoint, method in endpoints:
            try:
                if method == "GET":
                    response = await client.get(f"{BASE_URL}{endpoint}")
                elif method == "POST":
                    response = await client.post(f"{BASE_URL}{endpoint}")
                
                if response.status_code == 200:
                    print(f"   ✅ {method} {endpoint}: 200 OK")
                else:
                    print(f"   ⚠️  {method} {endpoint}: {response.status_code}")
                    all_ok = False
            except Exception as e:
                print(f"   ❌ {method} {endpoint}: ERROR - {e}")
                all_ok = False
        
        return all_ok

async def main():
    """Основная функция тестирования"""
    print("🚀 Firehorse Security Quick Test")
    print("=" * 50)
    
    tests = [
        ("Security Headers", test_security_headers),
        ("CORS", test_cors),
        ("Rate Limit Info", test_rate_limit_info),
        ("API Endpoints", test_api_endpoints),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Вывод результатов
    print(f"\n{'='*50}")
    print("📊 SECURITY TEST RESULTS")
    print(f"{'='*50}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🔒 Security configuration is working correctly!")
        return True
    else:
        print(f"⚠️  {total - passed} security tests need attention")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
