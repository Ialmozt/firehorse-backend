#!/usr/bin/env python3
"""
Упрощенный скрипт для автоматических ответов на Kwork
(Альтернатива pykwork для Python 3.12)
"""

import os
import logging
import time
import random
from typing import Dict, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KworkAutoReply:
    """Класс для автоматических ответов на Kwork проекты"""
    
    # Шаблоны ответов для разных категорий
    REPLY_TEMPLATES = {
        41: [  # Скрипты и боты
            "Готов выполнить ваш проект по созданию скрипта/бота! Имею опыт в Python, AI интеграциях и автоматизации процессов. Срок: 1-3 дня, качество гарантирую.",
            "Специализируюсь на разработке ИИ скриптов и ботов. Выполню ваш проект быстро и качественно. Использую современные технологии: Python, FastAPI, ML модели.",
            "Могу разработать эффективный скрипт/бот для вашей задачи. Опыт в автоматизации, парсинге, интеграциях с API. Работаю оперативно, тестирую каждый этап."
        ],
        33: [  # Копирайтинг
            "Напишу качественный текст для вашего проекта! Специализируюсь на ИИ-тематике, технических текстах, SEO-оптимизации. Уникальность 100%, сроки соблюдаю.",
            "Профессиональный копирайтинг с использованием ИИ-инструментов для максимальной эффективности. Тексты продающие, информативные, оптимизированные под поиск.",
            "Создам контент для вашего проекта: статьи, описания, посты. Использую DeepSeek для анализа и генерации, затем human editing для качества."
        ],
        109: [  # SEO
            "Проведу SEO-оптимизацию вашего проекта. Анализ ключевых слов, технический аудит, контент-стратегия. Повышение позиций в поиске гарантирую.",
            "SEO специалист с опытом в ИИ-проектах. Оптимизирую сайты под поисковые системы, работаю с семантическим ядром, улучшаю поведенческие факторы.",
            "Комплексное SEO: от анализа конкурентов до реализации. Использую современные инструменты и ИИ для анализа данных и прогнозирования результатов."
        ]
    }
    
    def __init__(self):
        self.last_reply_time = {}
    
    def generate_reply(self, project: Dict) -> Optional[str]:
        """Генерация ответа на проект"""
        category = project.get('category_id', 41)
        
        # Проверяем, не отвечали ли уже на этот проект
        project_id = project.get('id')
        if project_id in self.last_reply_time:
            # Проверяем временной интервал (не чаще чем раз в час на один проект)
            if time.time() - self.last_reply_time[project_id] < 3600:
                logger.info(f"Уже отвечали на проект {project_id} недавно, пропускаем")
                return None
        
        # Выбираем шаблон ответа
        templates = self.REPLY_TEMPLATES.get(category, self.REPLY_TEMPLATES[41])
        reply_template = random.choice(templates)
        
        # Персонализируем ответ
        title = project.get('title', '')
        price = project.get('price', '')
        
        reply = f"{reply_template}\n\n"
        reply += f"По вашему проекту '{title[:50]}...' "
        
        if price and price != "Цена не указана":
            reply += f"с бюджетом {price} "
        
        reply += "готов предложить решение. Можем обсудить детали в чате!"
        
        # Добавляем контактную информацию
        reply += "\n\n📞 Telegram: @FirehorseKworkBot"
        reply += "\n⏱️ Время ответа: в течение 30 минут"
        reply += "\n✅ Гарантия качества"
        
        # Запоминаем время ответа
        if project_id:
            self.last_reply_time[project_id] = time.time()
        
        return reply
    
    def simulate_auto_reply(self, project: Dict) -> bool:
        """Симуляция автоматического ответа (в реальности нужно API Kwork)"""
        reply = self.generate_reply(project)
        
        if not reply:
            logger.info(f"Пропускаем проект {project.get('id')}")
            return False
        
        logger.info(f"Генерируем ответ для проекта {project.get('id')}:")
        logger.info(f"Заголовок: {project.get('title')}")
        logger.info(f"Ответ: {reply[:100]}...")
        
        # В реальном приложении здесь был бы вызов API Kwork для отправки ответа
        # Например: await kwork_api.send_reply(project_id, reply)
        
        # Для демонстрации просто логируем
        logger.info(f"✅ Ответ готов для отправки на проект {project.get('id')}")
        
        # Сохраняем в лог-файл для отслеживания
        self.log_reply(project, reply)
        
        return True
    
    def log_reply(self, project: Dict, reply: str):
        """Логирование ответов в файл"""
        log_dir = "/var/log/firehorse"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "kwork_replies.log")
        
        log_entry = {
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'project_id': project.get('id'),
            'project_title': project.get('title'),
            'category': project.get('category_id'),
            'price': project.get('price'),
            'reply': reply
        }
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Ошибка при логировании: {e}")
    
    def process_projects(self, projects: list):
        """Обработка списка проектов"""
        successful_replies = 0
        
        for project in projects:
            try:
                success = self.simulate_auto_reply(project)
                if success:
                    successful_replies += 1
                
                # Пауза между ответами (чтобы не спамить)
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                logger.error(f"Ошибка при обработке проекта {project.get('id')}: {e}")
        
        logger.info(f"Успешно обработано {successful_replies}/{len(projects)} проектов")
        return successful_replies

def main():
    """Основная функция для тестирования"""
    auto_reply = KworkAutoReply()
    
    # Тестовые проекты
    test_projects = [
        {
            'id': 'test-001',
            'title': 'Нужен скрипт для автоматизации парсинга данных',
            'category_id': 41,
            'price': '2000₽'
        },
        {
            'id': 'test-002',
            'title': 'Требуется статья про ИИ в бизнесе',
            'category_id': 33,
            'price': '1500₽'
        },
        {
            'id': 'test-003',
            'title': 'SEO оптимизация сайта',
            'category_id': 109,
            'price': '3000₽'
        }
    ]
    
    logger.info("Тестирование автоматических ответов на Kwork...")
    auto_reply.process_projects(test_projects)
    logger.info("Тестирование завершено")

if __name__ == "__main__":
    main()
