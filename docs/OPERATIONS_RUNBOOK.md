# Firehorse Backend - Operations Runbook
## Руководство по эксплуатации и устранению неисправностей

**Версия:** v1.0  
**Дата:** 2026-01-10  
**Статус:** ✅ Production Ready

## 📋 Быстрые команды

### Статус системы
```bash
# Проверка статуса всех сервисов
docker-compose ps

# Просмотр логов
docker-compose logs -f
docker-compose logs -f api
docker-compose logs -f worker

# Проверка health
curl http://localhost:8000/health
curl http://localhost:8000/health/deep

# Проверка метрик
curl http://localhost:8000/metrics | head -20
```

### Управление сервисами
```bash
# Запуск всех сервисов
docker-compose up -d

# Остановка всех сервисов
docker-compose down

# Перезапуск конкретного сервиса
docker-compose restart api
docker-compose restart worker

# Масштабирование worker
docker-compose up -d --scale worker=3
```

## 🚨 Аварийные ситуации

### 1. Сервис не отвечает (Health check failed)

**Симптомы:**
- `curl http://localhost:8000/health` возвращает не 200
- Логи показывают ошибки
- Метрики не обновляются

**Действия:**
```bash
# 1. Проверка логов
docker-compose logs --tail=100 api

# 2. Проверка ресурсов
docker stats
free -h
df -h

# 3. Перезапуск сервиса
docker-compose restart api

# 4. Если не помогает - полный перезапуск
docker-compose down
docker-compose up -d

# 5. Проверка после перезапуска
sleep 10
curl -f http://localhost:8000/health
```

**Распространенные причины:**
- Закончилась память
- Проблемы с сетью
- Проблемы с базой данных
- Истекли API ключи

### 2. База данных недоступна

**Симптомы:**
- Ошибки подключения в логах
- Health check показывает database: disconnected
- Worker не может обрабатывать задачи

**Действия:**
```bash
# 1. Проверка подключения к Supabase
psql -h db.supabase.co -p 5432 -U postgres -d postgres -c "SELECT 1"

# 2. Проверка статуса Supabase
curl https://status.supabase.com/api/v2/status.json | jq .

# 3. Временное отключение worker
docker-compose stop worker

# 4. Включение режима деградации
export DATABASE_CONNECTION_TIMEOUT=5

# 5. Оповещение команды
# (отправить сообщение в Slack/Telegram)
```

### 3. DeepSeek API недоступен

**Симптомы:**
- Ошибки в логах worker
- Задачи не обрабатываются
- Метрики показывают 0 успешных запросов

**Действия:**
```bash
# 1. Проверка API ключа
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  https://api.deepseek.com/v1/models

# 2. Проверка лимитов
# (перейти на platform.deepseek.com)

# 3. Включение fallback режима
export USE_FALLBACK_CONTENT=true

# 4. Остановка новых задач
# (можно временно остановить прием webhook)
```

### 4. Высокая загрузка CPU/памяти

**Симптомы:**
- Медленные ответы
- Ошибки timeout
- Docker stats показывает высокую утилизацию

**Действия:**
```bash
# 1. Определение проблемного процесса
docker stats
top

# 2. Увеличение ресурсов
# Редактировать docker-compose.yml:
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

# 3. Перезапуск с новыми ресурсами
docker-compose down
docker-compose up -d

# 4. Оптимизация настроек
# Увеличить интервалы polling
# Уменьшить batch size
```

### 5. Очередь переполнена

**Симптомы:**
- Много задач в очереди
- Долгое время обработки
- Health check показывает high queue depth

**Действия:**
```bash
# 1. Проверка глубины очереди
curl http://localhost:8000/health/deep | jq '.checks.queue'

# 2. Увеличение количества worker
docker-compose up -d --scale worker=3

# 3. Увеличение batch size
export WORKER_MAX_BATCH_SIZE=20

# 4. Очистка старых задач
# (если есть stuck задачи)
```

## 🔧 Регулярное обслуживание

### Ежедневные проверки
```bash
#!/bin/bash
# scripts/daily-check.sh

echo "=== Daily Health Check ==="
echo "Time: $(date)"

# 1. Health endpoints
echo "1. Health check:"
curl -s http://localhost:8000/health | jq .

# 2. Queue status
echo "2. Queue status:"
curl -s http://localhost:8000/health/deep | jq '.checks.queue'

# 3. Resource usage
echo "3. Resource usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 4. Log errors (last 24h)
echo "4. Recent errors:"
docker-compose logs --since 24h api | grep -i error | tail -10

# 5. Backup status
echo "5. Backup status:"
ls -la /backups/ | tail -5
```

### Еженедельные задачи
1. **Rotate logs:**
```bash
# Архивирование старых логов
find ./logs -name "*.log" -mtime +7 -exec gzip {} \;
find ./logs -name "*.gz" -mtime +30 -delete
```

2. **Cleanup Docker:**
```bash
# Очистка неиспользуемых образов
docker system prune -f

# Очистка volumes
docker volume prune -f
```

3. **Проверка обновлений:**
```bash
# Проверка обновлений безопасности
apt-get update
apt-get upgrade --dry-run

# Проверка обновлений Docker образов
docker-compose pull --dry-run
```

### Ежемесячные задачи
1. **Rotate API keys:**
   - Сгенерировать новые ключи DeepSeek
   - Обновить .env файл
   - Перезапустить сервисы

2. **Review metrics:**
   - Анализ трендов использования
   - Оптимизация параметров
   - Настройка алертов

3. **Security audit:**
   - Проверка логов на подозрительную активность
   - Обновление SSL сертификатов
   - Проверка firewall правил

## 📊 Мониторинг и алерты

### Ключевые метрики для мониторинга
```yaml
# Prometheus алерты (alert.rules)
groups:
  - name: firehorse_alerts
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(firehorse_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          
      # Queue depth critical
      - alert: HighQueueDepth
        expr: firehorse_queue_depth{queue_name="job_queue"} > 100
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Queue depth exceeded 100"
          
      # API latency high
      - alert: HighAPILatency
        expr: histogram_quantile(0.95, rate(firehorse_api_latency_seconds_bucket[5m])) > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "API latency above 5 seconds"
          
      # Worker unhealthy
      - alert: WorkerUnhealthy
        expr: firehorse_worker_health < 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Worker is unhealthy"
```

### Настройка алертов
1. **Email алерты:**
```yaml
# alertmanager.yml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'email-alerts'

receivers:
  - name: 'email-alerts'
    email_configs:
      - to: 'ops@your-company.com'
        from: 'alerts@firehorse.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@firehorse.com'
        auth_password: 'password'
```

2. **Slack алерты:**
```yaml
receivers:
  - name: 'slack-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/XXX/YYY/ZZZ'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.summary }}'
```

3. **Telegram алерты:**
```bash
#!/bin/bash
# scripts/send-telegram-alert.sh
TELEGRAM_BOT_TOKEN="your-bot-token"
CHAT_ID="your-chat-id"

curl -X POST \
  https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage \
  -d "chat_id=$CHAT_ID" \
  -d "text=$ALERT_MESSAGE"
```

## 🔄 Процедуры обновления

### Минорное обновление (патч)
```bash
# 1. Backup текущего состояния
./scripts/backup.sh

# 2. Получение обновлений
git pull origin main

# 3. Запуск тестов
python -m pytest tests/ -v

# 4. Обновление
docker-compose build --no-cache
docker-compose up -d --build

# 5. Проверка
sleep 30
curl -f http://localhost:8000/health
```

### Мажорное обновление (версия)
```bash
# 1. Уведомление пользователей
# (плановые работы)

# 2. Backup всего
./scripts/full-backup.sh

# 3. Остановка приема новых задач
# (временно отключить webhook)

# 4. Ожидание обработки очереди
while [ "$(curl -s http://localhost:8000/health/deep | jq '.checks.queue.details.queue_depth')" -gt 0 ]; do
  echo "Waiting for queue to empty..."
  sleep 10
done

# 5. Обновление
git checkout v2.0.0
docker-compose down
docker-compose up -d --build

# 6. Проверка
./scripts/smoke-test.sh

# 7. Включение приема задач
```

### Откат обновления
```bash
# 1. Остановка сервисов
docker-compose down

# 2. Откат кода
git checkout v1.0.0

# 3. Восстановление backup если нужно
psql -h db.supabase.co -U postgres -d postgres < backup_20260110.sql

# 4. Запуск старой версии
docker-compose up -d

# 5. Проверка
curl -f http://localhost:8000/health
```

## 🗄️ Backup и восстановление

### Полный backup
```bash
#!/bin/bash
# scripts/full-backup.sh
BACKUP_DIR="/backups/full_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "Starting full backup..."

# 1. Backup базы данных
echo "Backing up database..."
pg_dump -h db.supabase.co -U postgres -d postgres | gzip > $BACKUP_DIR/database.sql.gz

# 2. Backup файлов конфигурации
echo "Backing up configuration..."
tar -czf $BACKUP_DIR/config.tar.gz \
  .env \
  docker-compose.yml \
  prometheus.yml \
  grafana/

# 3. Backup логов
echo "Backing up logs..."
tar -czf $BACKUP_DIR/logs.tar.gz logs/

# 4. Backup Docker volumes
echo "Backing up Docker volumes..."
docker run --rm \
  -v firehorse_prometheus_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar -czf /backup/prometheus_data.tar.gz -C /data .

# 5. Создание manifest
echo "Creating manifest..."
cat > $BACKUP_DIR/manifest.json << EOF
{
  "timestamp": "$(date -Iseconds)",
  "components": {
    "database": "present",
    "config": "present",
    "logs": "present",
    "volumes": "present"
  },
  "size": "$(du -sh $BACKUP_DIR | cut -f1)"
}
EOF

echo "Backup completed: $BACKUP_DIR"
```

### Восстановление из backup
```bash
#!/bin/bash
# scripts/restore.sh
BACKUP_DIR="/backups/full_20260110_120000"

echo "Starting restore from $BACKUP_DIR..."

# 1. Остановка сервисов
docker-compose down

# 2. Восстановление базы данных
echo "Restoring database..."
gunzip -c $BACKUP_DIR/database.sql.gz | psql -h db.supabase.co -U postgres -d postgres

# 3. Восстановление конфигурации
echo "Restoring configuration..."
tar -xzf $BACKUP_DIR/config.tar.gz -C /

# 4. Восстановление Docker volumes
echo "Restoring Docker volumes..."
docker run --rm \
  -v firehorse_prometheus_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar -xzf /backup/prometheus_data.tar.gz -C /data

# 5. Запуск сервисов
docker-compose up -d

echo "Restore completed"
```

## 📈 Производительность и оптимизация

### Оптимизация базы данных
```sql
-- Проверка медленных запросов
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Проверка индексов
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public';

-- Оптимизация
VACUUM ANALYZE;
REINDEX DATABASE postgres;
```

### Оптимизация worker
```bash
# Настройка параметров в .env
WORKER_CONCURRENCY=4           # Количество одновременных задач
WORKER_POLL_INTERVAL=5         # Интервал опроса очереди (сек)
WORKER_MAX_BATCH_SIZE=10       # Максимальный размер батча
WORKER_HEALTH_CHECK_INTERVAL=30 # Интервал health check (сек)
```

### Мониторинг производительности
```bash
# Утилизация CPU
docker stats --format "table {{.Name}}\t{{.CPUPerc}}"

# Использование памяти
free -h
docker stats --format "table {{.Name}}\t{{.MemUsage}}"

# Дисковый ввод/вывод
iostat -x 1

# Сетевая активность
iftop -i eth0
```

## 🔐 Безопасность

### Регулярные проверки безопасности
1. **Проверка уязвимостей:**
```bash
# Сканирование образов Docker
docker scan firehorse-api

# Проверка зависимостей
pip-audit
npm audit
```

2. **Аудит логов:**
```bash
# Поиск подозрительной активности
grep -i "failed\|error\|unauthorized\|forbidden" logs/app.log

# Проверка попыток brute force
grep "429" logs/access.log | wc -l
```

3. **Обновление зависимостей:**
```bash
# Обновление Python пакетов
pip list --outdated
pip install --upgrade -r requirements.txt

# Пересборка образов
docker-compose build --no-cache
```

### Инциденты безопасности
**Процедура реагирования:**
1. **Изоляция:** Остановить затронутые сервисы
2. **Анализ:** Собрать логи и метрики
3. **Устранение:** Применить исправления
4. **Восстановление:** Запустить очищенные сервисы
5. **Отчет:** Документировать инцидент

## 📞 Контакты и эскалация

### Команда поддержки
- **Primary On-call:** +7 (XXX) XXX-XX-XX
- **Secondary On-call:** +7 (XXX) XXX-XX-XX
- **Manager:** +7 (XXX) XXX-XX-XX
- **Security Team:** security@your-company.com

### Эскала
