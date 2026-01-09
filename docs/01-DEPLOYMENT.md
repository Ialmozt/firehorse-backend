📚 Complete Deployment Guide

## Architecture
- PostgreSQL: Supabase (IPv6 via SOCKS5 proxy)
- API: FastAPI on port 8000
- Queue: PGMQ (PostgreSQL Message Queue)
- Container: Docker Compose

## Files Reference
All project files are in `/srv/firehorse-backend/`:

- `schema.sql` - Database schema (single source of truth)
- `requirements.txt` - Python dependencies
- `src/main.py` - FastAPI application
- `Dockerfile` - Container spec
- `docker-compose.yml` - Orchestration

## Step-by-Step

### Step 1: Setup Environment
```bash
cp .env.example .env
# Edit .env: set real DATABASE_PASSWORD
chmod 600 .env
echo ".env" >> .gitignore
```

### Step 2: Deploy Database Schema
```bash
PGPASSWORD="your_password_here" proxychains psql \
-h db.yommcknuизxkwpmpvlmp.supabase.co \
-U postgres -d postgres \
-f schema.sql
```

### Step 3: Start Containers
```bash
cd /srv/firehorse-backend
set -a
source .env
set +a
docker-compose up -d
sleep 5
docker-compose logs api
```

### Step 4: Test
```bash
# Health check
curl http://localhost:8000/health

# Webhook test
curl -X POST http://localhost:8000/webhook \
-H "Content-Type: application/json" \
-d '{"source_id": "test123", "topic": "article"}'
```

## ✅ Checklist
- [ ] .env configured
- [ ] Schema deployed
- [ ] Docker running
- [ ] Health endpoint works
- [ ] Webhook creates orders

## Production Notes
- Change password in Supabase Dashboard
- Use GitHub Secrets for CI/CD
- DO NOT commit .env file