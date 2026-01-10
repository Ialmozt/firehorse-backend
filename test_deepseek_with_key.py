#!/usr/bin/env python3
"""
Тест DeepSeek API с API Key через X-Ray VPN
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")
print(f"API Key: {API_KEY[:20] if API_KEY else 'NOT FOUND'}...")

if not API_KEY:
    print("❌ DEEPSEEK_API_KEY не установлен!")
    exit(1)

# HTTP proxy
HTTP_PROXY = "http://127.0.0.1:7890"

print("\n🔐 Тест DeepSeek API через X-Ray VPN (7890)")
print("=" * 50)

try:
    with httpx.Client(
        proxies=HTTP_PROXY,
        timeout=30.0,
        verify=False
    ) as client:
        
        # TEST 1: Chat completions
        print("\n[TEST 1] Chat Completions")
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Ты помощник для написания SEO статей"},
                {"role": "user", "content": "Напиши короткую SEO статью (100 слов) про Python"}
            ],
            "temperature": 0.7,
            "max_tokens": 150
        }
        
        print(f"📡 Отправляю запрос...")
        response = client.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=payload,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')
            print(f"\n✅ УСПЕХ! DeepSeek ответил:")
            print("=" * 50)
            print(content)
            print("=" * 50)
            print(f"\n✅ VPN + API Key работают! Production ready!")
        else:
            print(f"❌ Ошибка {response.status_code}:")
            print(response.text)

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
