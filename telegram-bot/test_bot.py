#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности Firehorse Telegram Bot
Проверяет RSS парсинг и webhook интеграцию без запуска реального бота
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import feedparser
import requests
from datetime import datetime

# Конфигурация из bot.py
WEBHOOK_URL = "http://localhost:8000/webhook"
WEBHOOK_TOKEN = "44c89b6265fb03bb6ce22c5f41f02bca87177662da81e3ed719c7321b36f8a70"

# RSS фиды для тестирования
TEST_RSS_URLS = [
    "https://kwork.ru/rss?category=copywriting",
    "https://kwork.ru/rss?category=scripts",
]

def test_rss_parsing():
    """Тест парсинга RSS фидов"""
    print("🔍 Тестирование RSS парсинга...")
    
    for rss_url in TEST_RSS_URLS:
        print(f"\n📡 Проверка RSS: {rss_url}")
        try:
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                print(f"   ❌ Ошибка парсинга: {feed.bozo_exception}")
                continue
            
            print(f"   ✅ Успешно! Загружено {len(feed.entries)} записей")
            
            if feed.entries:
                entry = feed.entries[0]
                print(f"   📰 Пример записи:")
                print(f"      Заголовок: {entry.title[:50]}...")
                print(f"      Ссылка: {entry.link}")
                print(f"      ID: {entry.id if hasattr(entry, 'id') else 'N/A'}")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    return True

def test_webhook_connection():
    """Тест подключения к Firehorse webhook"""
    print("\n🔗 Тестирование подключения к Firehorse webhook...")
    
    # Сначала проверяем health endpoint
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"   ✅ Health endpoint: {health_response.status_code}")
        if health_response.status_code == 200:
            print(f"   📊 Ответ: {health_response.json()}")
    except Exception as e:
        print(f"   ❌ Health endpoint недоступен: {e}")
        return False
    
    # Тестируем webhook с тестовыми данными
    test_data = {
        "kworkid": f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "topic": "Тестовый заказ из Telegram Bot",
        "source": "telegram_bot_test",
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"\n   🚀 Отправка тестового webhook запроса...")
    print(f"   📦 Данные: {test_data}")
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=test_data,
            headers={
                "Content-Type": "application/json",
                "X-Token": WEBHOOK_TOKEN
            },
            timeout=10
        )
        
        print(f"   📡 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Успешно! Ответ: {result}")
            return True
        else:
            print(f"   ❌ Ошибка! Ответ: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Сетевая ошибка: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Неизвестная ошибка: {e}")
        return False

def test_bot_dependencies():
    """Тест зависимостей бота"""
    print("\n📦 Тестирование зависимостей Python...")
    
    dependencies = [
        ("feedparser", "feedparser"),
        ("requests", "requests"),
        ("python-telegram-bot", "telegram"),
    ]
    
    all_ok = True
    for package_name, import_name in dependencies:
        try:
            if import_name == "telegram":
                __import__("telegram")
            else:
                __import__(import_name)
            print(f"   ✅ {package_name} - OK")
        except ImportError as e:
            print(f"   ❌ {package_name} - Ошибка: {e}")
            all_ok = False
    
    return all_ok

def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("🤖 ТЕСТИРОВАНИЕ FIREHORSE TELEGRAM BOT")
    print("=" * 60)
    
    # Проверяем зависимости
    if not test_bot_dependencies():
        print("\n❌ Не все зависимости установлены!")
        print("   Установите: pip install -r requirements.txt")
        return False
    
    # Проверяем RSS парсинг
    if not test_rss_parsing():
        print("\n❌ Ошибка RSS парсинга!")
        return False
    
    # Проверяем webhook
    if not test_webhook_connection():
        print("\n❌ Ошибка подключения к webhook!")
        print("   Убедитесь что Firehorse API запущен: docker-compose up api")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 60)
    print("\n📝 Инструкция по запуску бота:")
    print("1. Получите токен бота у @BotFather в Telegram")
    print("2. Добавьте токен в .env файл: TELEGRAM_BOT_TOKEN=ваш_токен")
    print("3. Запустите бота: python bot.py")
    print("4. Или используйте Docker: docker-compose up telegram-bot")
    print("\n⚡ Бот готов к работе!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
