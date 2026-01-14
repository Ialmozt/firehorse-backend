# 🤖 Firehorse Telegram Bot

Автоматическое создание заказов в Firehorse через RSS Kwork с помощью Telegram бота.

## 📋 Функциональность

- 📡 Парсинг RSS фидов Kwork (копирайтинг, скрипты, дизайн, SEO, аудио)
- 🔔 Отображение последних заказов в Telegram
- ➕ Inline кнопка "Firehorse" для мгновенного создания заказа
- 🔗 Интеграция с Firehorse webhook API
- 📊 Логирование и мониторинг

## 🚀 Быстрый старт

### 1. Получение токена бота

1. Откройте Telegram и найдите [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен (например: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Настройка окружения

Добавьте токен в файл `.env` в корне проекта:

```bash
TELEGRAM_BOT_TOKEN=ваш_токен_здесь
```

### 3. Запуск бота

#### Вариант A: Запуск через Python (разработка)

```bash
cd /srv/firehorse-backend/telegram-bot
pip install -r requirements.txt
python bot.py
```

#### Вариант B: Запуск через Docker Compose (production)

```bash
cd /srv/firehorse-backend
docker-compose up -d telegram-bot
```

#### Вариант C: Запуск как systemd сервис

```bash
sudo cp telegram-bot/firehorse-telegram.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable firehorse-telegram
sudo systemctl start firehorse-telegram
```

## 📡 Настройка RSS фидов

Бот поддерживает несколько категорий Kwork. Настройки находятся в `bot.py`:

```python
KWORK_RSS_FEEDS = {
    'copywriting': 'https://kwork.ru/rss?category=copywriting',
    'scripts': 'https://kwork.ru/rss?category=scripts',
    'design': 'https://kwork.ru/rss?category=design',
    'seo': 'https://kwork.ru/rss?category=seo',
    'audio': 'https://kwork.ru/rss?category=audio',
}
```

## 💬 Команды бота

- `/start` - Приветственное сообщение
- `/help` - Помощь и инструкции
- `/feeds` - Список доступных RSS фидов
- `/kwork` - Загрузить последние заказы с Kwork

## 🔧 Тестирование

Для проверки функциональности без запуска бота:

```bash
cd telegram-bot
python test_bot.py
```

Тест проверяет:
- 📦 Зависимости Python
- 📡 RSS парсинг Kwork
- 🔗 Подключение к Firehorse webhook

## 🐳 Docker

### Сборка образа

```bash
cd telegram-bot
docker build -t firehorse-telegram-bot .
```

### Запуск контейнера

```bash
docker run -d \
  --name firehorse-telegram-bot \
  --env-file ../.env \
  -v /var/log/firehorse-telegram.log:/var/log/firehorse-telegram.log \
  firehorse-telegram-bot
```

## 📊 Мониторинг

### Логи

Логи бота сохраняются в `/var/log/firehorse-telegram.log`

Просмотр логов:

```bash
# Docker
docker logs -f firehorse-telegram-bot

# Systemd
sudo journalctl -u firehorse-telegram -f

# Файл логов
tail -f /var/log/firehorse-telegram.log
```

### Графана

Мониторинг заказов доступен в Grafana: http://localhost:3000

## 🔒 Безопасность

- Токен бота хранится в `.env` файле (никогда не коммитьте его!)
- Webhook запросы защищены токеном `INGRESS_SECRET`
- Бот использует HTTPS для всех внешних запросов

## 🚨 Устранение неполадок

### Бот не запускается

1. Проверьте токен: `grep TELEGRAM_BOT_TOKEN .env`
2. Проверьте зависимости: `python test_bot.py`
3. Проверьте логи: `docker logs firehorse-telegram-bot`

### RSS не загружается

1. Проверьте интернет-соединение
2. Проверьте URL RSS фида в браузере
3. Проверьте логи на наличие ошибок парсинга

### Webhook не работает

1. Проверьте что Firehorse API запущен: `docker-compose ps api`
2. Проверьте health endpoint: `curl http://localhost:8000/health`
3. Проверьте токен INGRESS_SECRET в `.env`

## 📁 Структура проекта

```
telegram-bot/
├── bot.py              # Основной код бота
├── test_bot.py         # Тестовый скрипт
├── requirements.txt    # Зависимости Python
├── Dockerfile         # Конфигурация Docker
├── README.md          # Эта документация
└── firehorse-telegram.service  # Systemd сервис
```

## 🔄 Интеграция с Firehorse

Бот отправляет заказы в Firehorse через webhook:

```json
{
  "kworkid": "уникальный_id_заказа",
  "topic": "Название заказа",
  "source": "telegram_bot",
  "timestamp": "2026-01-14T07:48:45.603365"
}
```

Firehorse обрабатывает заказ и возвращает:
- `orderid` - уникальный ID заказа в системе
- `status` - статус обработки
- `message` - детали обработки

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `/var/log/firehorse-telegram.log`
2. Проверьте статус сервисов: `docker-compose ps`
3. Запустите тест: `python test_bot.py`

## 📄 Лицензия

Проект является частью Firehorse MVP. Используйте для автоматизации вашего бизнеса на Kwork!
