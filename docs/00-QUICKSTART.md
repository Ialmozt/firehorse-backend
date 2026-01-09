🚀 Firehorse MVP - Quick Start (5 minutes)

⚡ Prerequisites
- SOCKS5 proxy running at 127.0.0.1:7891
- Supabase credentials: postgres / bkOFQ9jiln6JE82v

📋 Quick Steps

1. Copy .env template
```bash
cp .env.example .env
# Edit .env and set REAL password
```

2. Deploy schema
```bash
PGPASSWORD="bkOFQ9jiln6JE82v" proxychains psql \
-h db.yommcknuизxkwpmpvlmp.supabase.co \
-U postgres -d postgres \
-f schema.sql
```

3. Launch Docker
```bash
docker-compose up -d
sleep 5
curl http://localhost:8000/health
```

✅ Success
You should see PostgreSQL version in health response.

📖 Next Steps
- Read docs/01-DEPLOYMENT.md for manual setup
- Read docs/02-CLINE-AUTO.md for automated setup