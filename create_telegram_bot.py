#!/usr/bin/env python3
"""
Скрипт для создания Telegram бота через BotFather
Предоставляет инструкции для ручного создания бота
"""

import os
import sys

def print_instructions():
    """Печать инструкций по созданию бота"""
    print("=" * 60)
    print("🤖 СОЗДАНИЕ TELEGRAM БОТА ДЛЯ FIREHORSE")
    print("=" * 60)
    print("\n📱 ИНСТРУКЦИЯ ПО СОЗДАНИЮ БОТА:")
    print("\n1. 📲 Откройте Telegram на любом устройстве")
    print("2. 🔍 Найдите @BotFather (официальный бот для создания ботов)")
    print("3. 💬 Начните диалог с @BotFather")
    print("4. 📝 Отправьте команду: /newbot")
    print("5. 🏷️  Введите имя бота: Firehorse Kwork Auto")
    print("6. 🔤 Введите username бота: FirehorseKworkBot")
    print("   (должен заканчиваться на 'bot' или 'Bot')")
    print("7. 🔑 BotFather предоставит токен доступа")
    print("\n📋 ПРИМЕР ТОКЕНА: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    print("\n8. 💾 Скопируйте токен и выполните команду ниже:")
    print("\n   echo 'TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН' >> /srv/firehorse-backend/.env")
    print("\n9. 🚀 Запустите бота:")
    print("   cd /srv/firehorse-backend && docker-compose up -d telegram-bot")
    print("\n" + "=" * 60)
    print("✅ ПОСЛЕ СОЗДАНИЯ БОТА:")
    print("=" * 60)
    print("\n🔗 Ссылка на вашего бота: https://t.me/FirehorseKworkBot")
    print("\n💬 Команды для тестирования:")
    print("   /start - приветственное сообщение")
    print("   /help - помощь по использованию")
    print("   /kwork - загрузить последние заказы с Kwork")
    print("   /feeds - список RSS фидов")
    print("\n⚡ Нажмите '➕ Firehorse' под любым заказом для создания заказа!")
    print("\n📊 Мониторинг: http://localhost:3000 (Grafana)")

def check_current_token():
    """Проверка текущего токена в .env"""
    env_file = "/srv/firehorse-backend/.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            content = f.read()
            if 'TELEGRAM_BOT_TOKEN' in content:
                for line in content.split('\n'):
                    if line.startswith('TELEGRAM_BOT_TOKEN='):
                        token = line.split('=', 1)[1]
                        if token != 'YOUR_BOT_TOKEN_HERE':
                            print(f"\n🔍 Найден токен в .env: {token[:10]}...")
                            return True
    print("\n❌ Токен бота не найден или установлен placeholder")
    return False

def update_env_with_token(token):
    """Обновление .env файла с новым токеном"""
    env_file = "/srv/firehorse-backend/.env"
    
    # Читаем текущий файл
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            lines = f.readlines()
    
    # Удаляем старый TELEGRAM_BOT_TOKEN
    new_lines = []
    for line in lines:
        if not line.startswith('TELEGRAM_BOT_TOKEN='):
            new_lines.append(line)
    
    # Добавляем новый токен
    new_lines.append(f'TELEGRAM_BOT_TOKEN={token}\n')
    
    # Записываем обратно
    with open(env_file, 'w') as f:
        f.writelines(new_lines)
    
    print(f"\n✅ Токен добавлен в {env_file}")
    print(f"🔒 Токен: {token[:10]}... (первые 10 символов)")

def main():
    """Основная функция"""
    
    print_instructions()
    
    # Проверяем текущий токен
    if check_current_token():
        print("\n✅ Токен уже настроен. Можно запускать бота:")
        print("   cd /srv/firehorse-backend && docker-compose up -d telegram-bot")
        return
    
    # Если токена нет, предлагаем ввести его
    print("\n" + "=" * 60)
    print("📝 ВВОД ТОКЕНА ВРУЧНУЮ")
    print("=" * 60)
    
    try:
        token = input("\nВведите токен от BotFather (или нажмите Enter для пропуска): ").strip()
        
        if token:
            update_env_with_token(token)
            print("\n🚀 Теперь можно запустить бота:")
            print("   cd /srv/firehorse-backend && docker-compose up -d telegram-bot")
        else:
            print("\n⚠️  Токен не введен. Добавьте его позже в .env файл")
            print("   Команда для добавления:")
            print("   echo 'TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН' >> /srv/firehorse-backend/.env")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Ввод отменен. Добавьте токен позже.")
        print("   Инструкции выше остаются актуальными.")

if __name__ == "__main__":
    main()
