#!/usr/bin/env python3
"""
Kwork RSS парсер для Firehorse
Парсит новые проекты с Kwork каждые 15 минут
Категория 41: Скрипты и боты (ИИ ниша)
"""

import asyncio
import os
import logging
import json
import time
from datetime import datetime
import feedparser
import aiohttp
from typing import List, Dict, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KworkRSSParser:
    """Парсер RSS ленты Kwork"""
    
    # RSS URL для разных категорий Kwork
    RSS_URLS = {
        41: "https://kwork.ru/rss?c=41",  # Скрипты и боты
        33: "https://kwork.ru/rss?c=33",  # Копирайтинг
        109: "https://kwork.ru/rss?c=109",  # SEO
        3: "https://kwork.ru/rss?c=3",  # Дизайн
        10: "https://kwork.ru/rss?c=10",  # Аудио
    }
    
    def __init__(self, webhook_url: str = "http://localhost:8000/webhook"):
        self.webhook_url = webhook_url
        self.seen_projects = set()  # Для отслеживания уже обработанных проектов
        self.session = None
        
    async def init_session(self):
        """Инициализация aiohttp сессии"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def parse_rss_feed(self, category: int = 41) -> List[Dict]:
        """Парсинг RSS ленты для указанной категории"""
        url = self.RSS_URLS.get(category, self.RSS_URLS[41])
        logger.info(f"Парсинг RSS ленты: {url}")
        
        try:
            feed = feedparser.parse(url)
            projects = []
            
            for entry in feed.entries[:10]:  # Берем последние 10 проектов
                project = {
                    'id': entry.get('id', '').split('/')[-1],
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'description': entry.get('description', ''),
                    'published': entry.get('published', ''),
                    'price': self._extract_price(entry.get('description', '')),
                    'category_id': category,
                    'category_name': self._get_category_name(category)
                }
                
                # Проверяем, не обрабатывали ли уже этот проект
                project_key = f"{category}_{project['id']}"
                if project_key not in self.seen_projects:
                    projects.append(project)
                    self.seen_projects.add(project_key)
                    logger.info(f"Найден новый проект: {project['title'][:50]}...")
            
            logger.info(f"Найдено {len(projects)} новых проектов в категории {category}")
            return projects
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге RSS: {e}")
            return []
    
    def _extract_price(self, description: str) -> str:
        """Извлечение цены из описания"""
        import re
        price_pattern = r'(\d+[\s]*₽|\$\d+)'
        match = re.search(price_pattern, description)
        return match.group(0) if match else "Цена не указана"
    
    def _get_category_name(self, category_id: int) -> str:
        """Получение названия категории по ID"""
        categories = {
            41: "Скрипты и боты",
            33: "Копирайтинг",
            109: "SEO",
            3: "Дизайн",
            10: "Аудио"
        }
        return categories.get(category_id, "Другое")
    
    async def send_to_firehorse(self, project: Dict) -> bool:
        """Отправка проекта в Firehorse через webhook"""
        await self.init_session()
        
        # Получаем токен из .env
        token = os.getenv('INGRESS_SECRET', '44c89b6265fb03bb6ce22c5f41f02bca87177662da81e3ed719c7321b36f8a70')
        
        payload = {
            'kworkid': f"kwork-{project['id']}",
            'topic': project['title'],
            'category': str(project['category_id']),
            'price': project['price'],
            'link': project['link'],
            'source': 'kwork_rss'
        }
        
        headers = {
            'Content-Type': 'application/json',
            'X-Token': token
        }
        
        try:
            async with self.session.post(self.webhook_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Проект отправлен в Firehorse: {project['id']}, orderid: {data.get('orderid')}")
                    return True
                else:
                    logger.error(f"Ошибка отправки: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка при отправке в Firehorse: {e}")
            return False
    
    async def process_category(self, category: int = 41, limit: int = 5):
        """Обработка проектов в категории"""
        projects = self.parse_rss_feed(category)
        
        if not projects:
            logger.info(f"Нет новых проектов в категории {category}")
            return
        
        # Ограничиваем количество обрабатываемых проектов
        projects_to_process = projects[:limit]
        
        logger.info(f"Обработка {len(projects_to_process)} проектов в категории {category}")
        
        success_count = 0
        for project in projects_to_process:
            success = await self.send_to_firehorse(project)
            if success:
                success_count += 1
                # Небольшая задержка между запросами
                await asyncio.sleep(1)
        
        logger.info(f"Успешно обработано {success_count}/{len(projects_to_process)} проектов")
    
    async def run_continuous(self, interval_minutes: int = 15):
        """Непрерывный запуск парсера с заданным интервалом"""
        logger.info(f"Запуск Kwork RSS парсера с интервалом {interval_minutes} минут")
        
        while True:
            try:
                logger.info("Начало цикла парсинга")
                
                # Обрабатываем все категории
                categories = [41, 33, 109, 3, 10]  # Основные категории
                
                for category in categories:
                    await self.process_category(category, limit=3)  # По 3 проекта из каждой категории
                    await asyncio.sleep(2)  # Пауза между категориями
                
                logger.info(f"Цикл парсинга завершен. Ожидание {interval_minutes} минут...")
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке

async def main():
    """Основная функция"""
    parser = KworkRSSParser()
    
    try:
        # Тестовый запуск - обработка одной категории
        logger.info("Тестовый запуск Kwork RSS парсера...")
        await parser.process_category(41, limit=2)
        
        # Или запуск непрерывного парсинга
        # await parser.run_continuous(interval_minutes=15)
        
    finally:
        await parser.close_session()

if __name__ == "__main__":
    asyncio.run(main())
