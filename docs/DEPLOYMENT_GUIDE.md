# Firehorse Backend - Deployment Guide
## Production Deployment Instructions

**Версия:** v1.0  
**Дата:** 2026-01-10  
**Статус:** ✅ Production Ready

## 📋 Предварительные требования

### 1. Системные требования
- **OS:** Ubuntu 22.04+ / Debian 11+ / RHEL 8+
- **RAM:** 4GB минимум, 8GB рекомендуется
- **CPU:** 2+ ядра
- **Storage:** 20GB свободного места
- **Network:** Статический IP, открытые порты 80/443

### 2. Необходимые инструменты
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    docker.io \
    docker-compose \
    git \
    curl \
    jq \
    python3 \
    python3-pip \
    postgresql-client

# CentOS/RHEL
sudo yum install -y \
    docker \
    docker-compose \
    git \
    curl \
    jq \
    python3 \
    postgresql

# Проверка версий
docker --version          # >= 20.10
docker-compose --version  # >= 1.29
python3 --version         # >= 3.9
```

### 3. Аккаунты и API ключи
- [ ] **Supabase:** Создать проект, получить URL и SERVICE_ROLE_KEY
- [ ] **DeepSeek:** Получить API ключ на platform.deepseek.com
- [ ] **GitHub:** Access token для private репозиториев
- [ ] **VPN:** X-Ray proxy конфигурация (опционально)

## 🚀 Быстрый старт (5 минут)

### Шаг 1: Клонирование репозитория
```bash
git clone https://github.com/Ialmozt/firehorse-backend.git
cd firehorse-backend
```

### Шаг 2: Настройка окружения
```bash
# Копирование шаблона
cp .env.example .env

# Редактирование .env файла
nano .env
```

### Шаг 3: Заполнение .env файла
```env
# ====================
# SUPABASE CONFIGURATION
# ====================
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key-here
SUPABASE_ANON_KEY=your-anon-key-here

# ====================
# DEEPSEEK CONFIGURATION
# ====================
DEEPSEEK_API_KEY=your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# ====================
# VPN CONFIGURATION (Optional)
# ====================
VPN_HTTP_PORT=7890
VPN_SOCKS5_PORT=7891
USE_VPN=false

# ====================
# SECURITY CONFIGURATION
# ====================
REQUIRE_API_KEY=false
API_KEY_HEADER=X-API-Key
RATE_LIMIT_PER_MINUTE=10
CORS_ORIGINS=http://localhost:3000,https://your-frontend.com

# ====================
# APPLICATION CONFIGURATION
# ====================
LOG_LEVEL=INFO
WORKER_CONCURRENCY=4
WORKER_POLL_INTERVAL=5
WORKER_MAX_BATCH_SIZE=10
WORKER_HEALTH_CHECK_INTERVAL=30

# ====================
# DATABASE CONFIGURATION
# ====================
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_STATEMENT_TIMEOUT=30000

# ====================
# MONITORING CONFIGURATION
# ====================
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
HEALTH_CHECK_PORT=8080
```

### Шаг 4: Запуск Docker Compose
```bash
# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f
```

### Шаг 5: Проверка работоспособности
```bash
# Проверка health endpoint
curl http://localhost:8000/health

# Проверка metrics endpoint
curl http://localhost:8000/metrics

# Проверка webhook endpoint
curl -X POST http://localhost:8000/webhook/kwork \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

## 🐳 Docker Deployment

### Docker Compose Configuration
```yaml
# docker-compose.yml (основные сервисы)
version: '3.8'

services:
  # FastAPI приложение
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Worker для обработки очередей
  worker:
    build: .
    command: python -m src.worker_optimized
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    depends_on:
      - api

  # Prometheus для мониторинга
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  # Grafana для дашбордов
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание пользователя для безопасности
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск приложения
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🗄️ База данных (Supabase)

### 1. Создание проекта Supabase
1. Перейти на [supabase.com](https://supabase.com)
2. Создать новый проект
3. Запомнить:
   - **Project URL:** `https://[project-ref].supabase.co`
   - **API Key:** Service Role Key (не анонимный)

### 2. Развертывание схемы
```bash
# Использование psql
psql -h db.supabase.co -p 5432 -U postgres -d postgres -f schema_final.sql

# Или через REST API
python deploy_via_rest.py
```

### 3. Проверка схемы
```sql
-- Проверка таблиц
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' ORDER BY table_name;

-- Проверка RLS политик
SELECT tablename, policyname, permissive, roles, cmd 
FROM pg_policies WHERE schemaname = 'public';

-- Проверка функций
SELECT proname FROM pg_proc WHERE proname LIKE 'fh_%';
```

## 🔐 Безопасность

### 1. Настройка firewall
```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw enable

# Проверка
sudo ufw status
```

### 2. SSL/TLS сертификаты (Let's Encrypt)
```bash
# Установка certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d your-domain.com

# Автоматическое обновление
sudo certbot renew --dry-run
```

### 3. Настройка Nginx как reverse proxy
```nginx
# /etc/nginx/sites-available/firehorse
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /metrics {
        # Только для внутреннего мониторинга
        allow 127.0.0.1;
        allow 10.0.0.0/8;
        deny all;
        proxy_pass http://localhost:8000;
    }
}
```

## 📊 Мониторинг и логирование

### 1. Prometheus метрики
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'firehorse'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 2. Grafana дашборды
1. Открыть http://localhost:3000
2. Логин: admin / admin
3. Добавить Prometheus как datasource
4. Импортировать дашборд из `grafana/dashboards/firehorse-main.json`

### 3. Логирование
```bash
# Просмотр логов
docker-compose logs -f api
docker-compose logs -f worker

# Логи в файл
tail -f logs/app.log

# Структурированные логи (JSON)
cat logs/app.log | jq .
```

## 🔄 Обновление

### 1. Обновление кода
```bash
# Получение обновлений
git pull origin main

# Пересборка образов
docker-compose build --no-cache

# Перезапуск сервисов
docker-compose down
docker-compose up -d --build

# Проверка
docker-compose ps
curl http://localhost:8000/health
```

### 2. Миграции базы данных
```bash
# Создание backup
pg_dump -h db.supabase.co -U postgres -d postgres > backup_$(date +%Y%m%d).sql

# Применение миграций
psql -h db.supabase.co -U postgres -d postgres -f migrations/migration_001.sql
```

### 3. Откат
```bash
# Откат к предыдущей версии
git checkout v1.0.0
docker-compose down
docker-compose up -d --build
```

## 🚨 Аварийное восстановление

### 1. База данных недоступна
```bash
# Проверка подключения
psql -h db.supabase.co -p 5432 -U postgres -d postgres -c "SELECT 1"

# Временное отключение worker
docker-compose stop worker

# Включение режима деградации
export DATABASE_CONNECTION_TIMEOUT=5
```

### 2. DeepSeek API недоступен
```bash
# Проверка API
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  https://api.deepseek.com/v1/models

# Включение fallback режима
export USE_FALLBACK_CONTENT=true
```

### 3. Восстановление из backup
```bash
# Восстановление базы данных
psql -h db.supabase.co -U postgres -d postgres < backup_20260110.sql

# Восстановление файлов
tar -xzf backup_20260110.tar.gz -C /
```

## 📈 Масштабирование

### 1. Горизонтальное масштабирование
```bash
# Увеличение количества worker
docker-compose up -d --scale worker=3

# Увеличение количества API инстансов
docker-compose up -d --scale api=2

# Настройка load balancer
# (добавить в nginx конфигурацию)
upstream firehorse_api {
    server api1:8000;
    server api2:8000;
    server api3:8000;
}
```

### 2. Вертикальное масштабирование
```yaml
# docker-compose.yml с ограничениями ресурсов
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 3. Мониторинг нагрузки
```bash
# Проверка использования ресурсов
docker stats

# Проверка очереди
curl http://localhost:8000/health/deep | jq '.checks.queue'

# Автоматическое масштабирование
# (использовать docker swarm или kubernetes)
```

## 🛠️ Утилиты и скрипты

### 1. Скрипт backup
```bash
#!/bin/bash
# scripts/backup.sh
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup базы данных
pg_dump -h db.supabase.co -U postgres -d postgres | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup файлов
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /app

# Ротация backup (хранить 7 дней)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
```

### 2. Скрипт мониторинга
```bash
#!/bin/bash
# scripts/health-check.sh
HEALTH_URL="http://localhost:8000/health"

response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$response" -ne 200 ]; then
    echo "Health check failed: $response"
    # Отправка алерта
    curl -X POST https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage \
      -d "chat_id=$CHAT_ID" \
      -d "text=Firehorse health check failed: $response"
    exit 1
fi

echo "Health check passed: $response"
```

### 3. Скрипт деплоя
```bash
#!/bin/bash
# scripts/deploy.sh
set -e

echo "🚀 Starting deployment..."

# Pull latest code
git pull origin main

# Run tests
python -m pytest tests/ -v

# Build and deploy
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Wait for health check
sleep 10
curl -f http://localhost:8000/health

echo "✅ Deployment completed successfully!"
```

## 📞 Поддержка и устранение неисправ
