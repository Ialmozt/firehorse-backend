#!/usr/bin/env python3
"""
Firehorse Telegram Bot
Автоматическое создание заказов через RSS Kwork
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import feedparser
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv('/srv/firehorse-backend/.env')

# Конфигурация
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
WEBHOOK_URL = os.getenv('FIREHORSE_WEBHOOK_URL', 'http://localhost:8000/webhook')
WEBHOOK_TOKEN = os.getenv('INGRESS_SECRET', '44c89b6265fb03bb6ce22c5f41f02bca87177662da81e3ed719c7321b36f8a70')

# RSS фиды Kwork (можно настроить под разные категории)
KWORK_RSS_FEEDS = {
    'copywriting': 'https://kwork.ru/rss?category=copywriting',
    'scripts': 'https://kwork.ru/rss?category=scripts',
    'design': 'https://kwork.ru/rss?category=design',
    'seo': 'https://kwork.ru/rss?category=seo',
    'audio': 'https://kwork.ru/rss?category=audio',
}

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('/var/log/firehorse-telegram.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "🤖 Я *Firehorse Bot* - автоматизирую создание заказов из Kwork.\n\n"
        "📋 *Доступные команды:*\n"
        "/start - это сообщение\n"
        "/kwork - показать последние заказы с Kwork\n"
        "/help - помощь\n"
        "/feeds - список RSS фидов\n\n"
        "⚡ Просто отправь мне RSS ссылку или используй /kwork для автоматической загрузки!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = (
        "🆘 *Помощь по Firehorse Bot*\n\n"
        "1. Используй /kwork чтобы увидеть последние заказы с Kwork\n"
        "2. Нажми кнопку '➕ Firehorse' под любым заказом чтобы автоматически создать заказ в системе\n"
        "3. Бот отправит заказ в Firehorse и уведомит о результате\n\n"
        "🔧 *Настройка:*\n"
        "Измени RSS фиды в настройках бота для своей ниши\n\n"
        "📊 *Мониторинг:*\n"
        "Следи за обработкой заказов в Grafana: http://localhost:3000"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def feeds_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /feeds - показать доступные RSS фиды"""
    feeds_text = "📡 *Доступные RSS фиды Kwork:*\n\n"
    for category, url in KWORK_RSS_FEEDS.items():
        feeds_text += f"• *{category}*: `{url}`\n"
    
    feeds_text += "\nИспользуй /kwork для загрузки заказов из фидов."
    await update.message.reply_text(feeds_text, parse_mode='Markdown')


async def kwork_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /kwork - загрузить заказы из RSS Kwork"""
    await update.message.reply_text("🔄 Загружаю последние заказы с Kwork...")
    
    try:
        # Используем первый фид (можно расширить для выбора категории)
        rss_url = list(KWORK_RSS_FEEDS.values())[0]
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            await update.message.reply_text("❌ Не удалось загрузить заказы. Проверь RSS фид.")
            return
        
        loaded_count = 0
        for entry in feed.entries[:10]:  # Ограничиваем 10 заказами
            # Создаем inline кнопку для каждого заказа
            keyboard = [[
                InlineKeyboardButton("➕ Firehorse", callback_data=f"order:{entry.id}:{entry.title[:50]}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Формируем сообщение
            message_text = (
                f"💰 *{entry.title}*\n\n"
                f"🔗 {entry.link}\n"
                f"📅 {entry.published if hasattr(entry, 'published') else 'Дата не указана'}\n"
                f"📝 {entry.summary[:200] if hasattr(entry, 'summary') else 'Описание отсутствует'}..."
            )
            
            try:
                await update.message.reply_text(
                    message_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                loaded_count += 1
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения: {e}")
                continue
        
        await update.message.reply_text(
            f"✅ Загружено {loaded_count} заказов. Нажми '➕ Firehorse' под любым заказом чтобы создать заказ в системе."
        )
        
    except Exception as e:
        logger.error(f"Ошибка загрузки RSS: {e}")
        await update.message.reply_text(f"❌ Ошибка загрузки заказов: {str(e)[:200]}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на inline кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("order:"):
        # Парсим данные из callback_data
        _, kwork_id, topic = query.data.split(":", 2)
        
        await query.edit_message_text("⚡ Создаю заказ в Firehorse...")
        
        try:
            # Отправляем запрос в Firehorse webhook
            response = requests.post(
                WEBHOOK_URL,
                json={
                    "kworkid": kwork_id,
                    "topic": topic,
                    "source": "telegram_bot",
                    "timestamp": datetime.now().isoformat()
                },
                headers={
                    "Content-Type": "application/json",
                    "X-Token": WEBHOOK_TOKEN
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                success_text = (
                    f"✅ *Заказ создан успешно!*\n\n"
                    f"📋 ID заказа: `{result.get('orderid', 'N/A')}`\n"
                    f"📊 Статус: {result.get('status', 'N/A')}\n"
                    f"💬 Сообщение: {result.get('message', 'N/A')}\n\n"
                    f"🔍 Мониторь прогресс в Grafana: http://localhost:3000"
                )
                await query.edit_message_text(success_text, parse_mode='Markdown')
                
                # Логируем успешное создание
                logger.info(f"Заказ создан: kwork_id={kwork_id}, order_id={result.get('orderid')}")
                
            else:
                error_text = (
                    f"❌ *Ошибка создания заказа*\n\n"
                    f"Код ошибки: {response.status_code}\n"
                    f"Ответ: {response.text[:200]}"
                )
                await query.edit_message_text(error_text, parse_mode='Markdown')
                logger.error(f"Ошибка webhook: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            error_text = f"❌ *Сетевая ошибка:* {str(e)[:200]}"
            await query.edit_message_text(error_text, parse_mode='Markdown')
            logger.error(f"Сетевая ошибка: {e}")
        except Exception as e:
            error_text = f"❌ *Неизвестная ошибка:* {str(e)[:200]}"
            await query.edit_message_text(error_text, parse_mode='Markdown')
            logger.error(f"Неизвестная ошибка: {e}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления {update}: {context.error}")
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка при обработке запроса. Попробуйте еще раз."
            )
        except:
            pass


def main() -> None:
    """Основная функция запуска бота"""
    if TOKEN == 'YOUR_BOT_TOKEN_HERE':
        logger.error("Токен бота не установлен! Установи TELEGRAM_BOT_TOKEN в .env файле.")
        print("❌ ОШИБКА: Токен бота не установлен!")
        print("📝 Инструкция по получению токена:")
        print("1. Откройте Telegram и найдите @BotFather")
        print("2. Создайте нового бота с помощью команды /newbot")
        print("3. Скопируйте полученный токен")
        print("4. Добавьте в .env файл: TELEGRAM_BOT_TOKEN=ваш_токен")
        return
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("feeds", feeds_command))
    application.add_handler(CommandHandler("kwork", kwork_command))
    
    # Регистрируем обработчик inline кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Запуск Firehorse Telegram Bot...")
    print("🤖 Firehorse Telegram Bot запускается...")
    print(f"📡 Webhook URL: {WEBHOOK_URL}")
    print("⚡ Используйте /start в Telegram для начала работы")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
