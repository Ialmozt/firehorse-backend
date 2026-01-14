#!/usr/bin/env python3
"""
Обновление Grafana dashboard для отображения Kwork статистики
"""

import os
import json
import logging
import requests
from typing import Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GrafanaDashboardUpdater:
    """Класс для обновления Grafana dashboard"""
    
    def __init__(self, grafana_url: str = "http://localhost:3000"):
        self.grafana_url = grafana_url
        self.api_url = f"{grafana_url}/api"
        
        # Получаем credentials из .env
        from dotenv import load_dotenv
        load_dotenv('/srv/firehorse-backend/.env')
        
        self.username = os.getenv('GRAFANA_USER', 'admin')
        self.password = os.getenv('GRAFANA_PASSWORD', 'admin')
        
        # Получаем API key или создаем сессию
        self.session = self.create_session()
    
    def create_session(self):
        """Создание сессии с аутентификацией"""
        session = requests.Session()
        
        # Попробуем использовать basic auth
        session.auth = (self.username, self.password)
        
        # Проверим подключение
        try:
            response = session.get(f"{self.api_url}/health")
            if response.status_code == 200:
                logger.info("✅ Успешное подключение к Grafana API")
                return session
            else:
                logger.warning(f"⚠️  Basic auth не сработал, статус: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️  Ошибка подключения к Grafana: {e}")
        
        # Попробуем получить API key
        try:
            api_key = self.get_or_create_api_key()
            if api_key:
                session.headers.update({
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                })
                logger.info("✅ Используется API key для Grafana")
                return session
        except Exception as e:
            logger.error(f"❌ Ошибка получения API key: {e}")
        
        return session
    
    def get_or_create_api_key(self) -> str:
        """Получение или создание API key для Grafana"""
        # Проверим существующие ключи
        try:
            response = self.session.get(f"{self.api_url}/auth/keys")
            if response.status_code == 200:
                keys = response.json()
                for key in keys:
                    if key.get('name') == 'firehorse-auto':
                        logger.info(f"✅ Найден существующий API key: {key['id']}")
                        return key['key']
        except:
            pass
        
        # Создаем новый ключ
        key_data = {
            "name": "firehorse-auto",
            "role": "Admin",
            "secondsToLive": 86400 * 365  # 1 год
        }
        
        try:
            response = self.session.post(f"{self.api_url}/auth/keys", json=key_data)
            if response.status_code == 200:
                key_info = response.json()
                logger.info(f"✅ Создан новый API key: {key_info['id']}")
                return key_info['key']
        except Exception as e:
            logger.error(f"❌ Ошибка создания API key: {e}")
        
        return None
    
    def create_kwork_dashboard(self) -> Dict[str, Any]:
        """Создание dashboard для Kwork статистики"""
        dashboard = {
            "dashboard": {
                "id": None,
                "uid": "firehorse-kwork",
                "title": "Firehorse Kwork Revenue",
                "tags": ["firehorse", "kwork", "revenue"],
                "timezone": "browser",
                "schemaVersion": 36,
                "version": 0,
                "refresh": "30s",
                "panels": [
                    # Панель 1: Количество заказов за 24 часа
                    {
                        "id": 1,
                        "title": "Заказы за 24 часа",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                        "targets": [
                            {
                                "datasource": {"type": "postgres", "uid": "postgres"},
                                "rawSql": """
                                SELECT COUNT(*) as count 
                                FROM fh_orders 
                                WHERE created_at > now() - interval '24 hours'
                                """,
                                "format": "table",
                                "refId": "A"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "mappings": [],
                                "thresholds": {
                                    "mode": "absolute",
                                    "steps": [
                                        {"color": "red", "value": None},
                                        {"color": "green", "value": 5}
                                    ]
                                },
                                "unit": "short"
                            }
                        },
                        "options": {
                            "reduceOptions": {"values": False, "calcs": ["lastNotNull"]},
                            "orientation": "auto",
                            "textMode": "auto"
                        }
                    },
                    # Панель 2: Выручка за 24 часа
                    {
                        "id": 2,
                        "title": "Выручка за 24 часа",
                        "type": "stat",
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                        "targets": [
                            {
                                "datasource": {"type": "postgres", "uid": "postgres"},
                                "rawSql": """
                                SELECT COALESCE(SUM(
                                    CASE 
                                        WHEN price ~ '\\d+\\s*₽' THEN CAST(REGEXP_REPLACE(price, '[^\\d]', '', 'g') AS INTEGER)
                                        WHEN price ~ '\\$\\d+' THEN CAST(REGEXP_REPLACE(price, '[^\\d]', '', 'g') AS INTEGER) * 100
                                        ELSE 0
                                    END
                                ), 0) as revenue
                                FROM fh_orders 
                                WHERE created_at > now() - interval '24 hours'
                                AND status = 'completed'
                                """,
                                "format": "table",
                                "refId": "A"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "mappings": [],
                                "thresholds": {
                                    "mode": "absolute",
                                    "steps": [
                                        {"color": "red", "value": None},
                                        {"color": "orange", "value": 5000},
                                        {"color": "green", "value": 10000}
                                    ]
                                },
                                "unit": "currencyRUB"
                            }
                        }
                    },
                    # Панель 3: Заказы по категориям Kwork
                    {
                        "id": 3,
                        "title": "Заказы по категориям Kwork",
                        "type": "barchart",
                        "gridPos": {"h": 10, "w": 24, "x": 0, "y": 8},
                        "targets": [
                            {
                                "datasource": {"type": "postgres", "uid": "postgres"},
                                "rawSql": """
                                SELECT 
                                    CASE category
                                        WHEN '41' THEN 'Скрипты и боты'
                                        WHEN '33' THEN 'Копирайтинг'
                                        WHEN '109' THEN 'SEO'
                                        WHEN '3' THEN 'Дизайн'
                                        WHEN '10' THEN 'Аудио'
                                        ELSE 'Другое'
                                    END as category_name,
                                    COUNT(*) as order_count
                                FROM fh_orders 
                                WHERE created_at > now() - interval '7 days'
                                GROUP BY category
                                ORDER BY order_count DESC
                                """,
                                "format": "table",
                                "refId": "A"
                            }
                        ],
                        "options": {
                            "orientation": "auto",
                            "showLegend": True,
                            "tooltip": {"mode": "single"}
                        }
                    },
                    # Панель 4: Статусы заказов
                    {
                        "id": 4,
                        "title": "Статусы заказов",
                        "type": "piechart",
                        "gridPos": {"h": 10, "w": 12, "x": 0, "y": 18},
                        "targets": [
                            {
                                "datasource": {"type": "postgres", "uid": "postgres"},
                                "rawSql": """
                                SELECT 
                                    status,
                                    COUNT(*) as count
                                FROM fh_orders 
                                WHERE created_at > now() - interval '24 hours'
                                GROUP BY status
                                """,
                                "format": "table",
                                "refId": "A"
                            }
                        ],
                        "options": {
                            "pieType": "pie",
                            "displayLabels": ["name", "percent"],
                            "legend": {"showLegend": True, "values": True}
                        }
                    },
                    # Панель 5: Активность Kwork API
                    {
                        "id": 5,
                        "title": "Активность Kwork API (последний час)",
                        "type": "table",
                        "gridPos": {"h": 10, "w": 12, "x": 12, "y": 18},
                        "targets": [
                            {
                                "datasource": {"type": "postgres", "uid": "postgres"},
                                "rawSql": """
                                SELECT 
                                    request_type,
                                    COUNT(*) as requests,
                                    AVG(response_time_ms) as avg_response_ms,
                                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
                                FROM kwork_api_requests 
                                WHERE timestamp > now() - interval '1 hour'
                                GROUP BY request_type
                                ORDER BY requests DESC
                                """,
                                "format": "table",
                                "refId": "A"
                            }
                        ]
                    }
                ],
                "time": {"from": "now-24h", "to": "now"},
                "timepicker": {
                    "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"],
                    "time_options": ["5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"]
                }
            },
            "folderUid": "firehorse",
            "overwrite": True,
            "message": "Auto-created by Firehorse Kwork integration"
        }
        
        return dashboard
    
    def create_or_update_dashboard(self):
        """Создание или обновление dashboard в Grafana"""
        dashboard_data = self.create_kwork_dashboard()
        
        try:
            # Проверим, существует ли уже dashboard
            response = self.session.get(f"{self.api_url}/dashboards/uid/firehorse-kwork")
            
            if response.status_code == 200:
                # Dashboard существует, обновляем
                existing = response.json()
                dashboard_data['dashboard']['id'] = existing['dashboard']['id']
                dashboard_data['dashboard']['version'] = existing['dashboard']['version'] + 1
                
                logger.info("📊 Обновление существующего dashboard...")
                response = self.session.post(f"{self.api_url}/dashboards/db", json=dashboard_data)
                
                if response.status_code == 200:
                    logger.info("✅ Dashboard успешно обновлен")
                    return True
                else:
                    logger.error(f"❌ Ошибка обновления dashboard: {response.status_code} - {response.text}")
                    return False
            else:
                # Dashboard не существует, создаем новый
                logger.info("📊 Создание нового dashboard...")
                response = self.session.post(f"{self.api_url}/dashboards/db", json=dashboard_data)
                
                if response.status_code == 200:
                    logger.info("✅ Dashboard успешно создан")
                    return True
                else:
                    logger.error(f"❌ Ошибка создания dashboard: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при работе с dashboard: {e}")
            return False
    
    def test_connection(self):
        """Тестирование подключения к Grafana"""
        try:
            response = self.session.get(f"{self.api_url}/health")
            if response.status_code == 200:
                logger.info("✅ Подключение к Grafana успешно")
                return True
            else:
                logger.error(f"❌ Ошибка подключения: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Grafana: {e}")
            return False
    
    def setup_complete(self):
        """Полная настройка Grafana dashboard"""
        logger.info("🚀 Начало настройки Grafana dashboard для Kwork...")
        
        # 1. Тестирование подключения
        logger.info("1. Тестирование подключения к Grafana...")
        if not self.test_connection():
            logger.error("❌ Не удалось подключиться к Grafana")
            return False
        
        # 2. Создание/обновление dashboard
        logger.info("2. Создание/обновление dashboard...")
        if not self.create_or_update_dashboard():
            logger.error("❌ Не удалось создать/обновить dashboard")
            return False
        
        # 3. Получение ссылки на dashboard
        dashboard_url = f"{self.grafana_url}/d/firehorse-kwork/firehorse-kwork-revenue"
        logger.info(f"3. Dashboard доступен по ссылке: {dashboard_url}")
        
        logger.info("✅ Настройка Grafana dashboard завершена!")
        return True

def main():
    """Основная функция"""
    updater = GrafanaDashboardUpdater()
    
    if updater.setup_complete():
        print("\n" + "="*60)
        print("🎉 GRAFANA DASHBOARD НАСТРОЕН УСПЕШНО!")
        print("="*60)
        print("\n📊 Доступные дашборды:")
        print(f"   1. Kwork Revenue: http://localhost:3000/d/firehorse-kwork/firehorse-kwork-revenue")
        print(f"   2. Основной: http://localhost:3000/d/firehorse-main/firehorse-main")
        print("\n📈 Метрики которые теперь отслеживаются:")
        print("   • Заказы за 24 часа")
        print("   • Выручка за 24 часа (автоконвертация ₽/$)")
        print("   • Распределение по категориям Kwork")
        print("   • Статусы заказов (pie chart)")
        print("   • Активность Kwork API")
        print("\n🔄 Автообновление: каждые 30 секунд")
        print("="*60)
    else:
        print("\n❌ Настройка Grafana dashboard не удалась")
        print("Проверьте:")
        print("  1. Запущен ли Grafana: docker-compose ps | grep grafana")
        print("  2. Доступен ли порт 3000: curl -I http://localhost:3000")
        print("  3. Правильные ли credentials в .env (GRAFANA_USER, GRAFANA_PASSWORD)")

if __name__ == "__main__":
    main()
