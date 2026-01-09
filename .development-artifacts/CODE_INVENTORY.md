# CODE INVENTORY - Firehorse SaaS Project
**Last Updated:** 2026-01-09T18:18:12Z  
**Project:** Firehorse MVP (Kwork content automation)  
**Status:** 70% complete, moving to production

## 📁 PROJECT STRUCTURE

### Root Directory (`/srv/firehorse-backend`)
```
├── .development-artifacts/          # Development memory system
├── src/                            # Source code
├── docs/                           # Documentation
├── docker-compose.yml              # Docker orchestration
├── Dockerfile                      # Container definition
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables (local)
├── .env.example                    # Environment template
├── .gitignore                      # Git ignore rules
├── schema.sql                      # Database schema
├── schema_fixed.sql                # Fixed schema (idempotent)
├── phase1_verification_report.md   # Phase 1 report
├── test_resilience.py              # Resilience test
├── test_network_failure.py         # Network failure test
├── deploy_via_rest.py              # REST deployment script
└── README.md                       # Project overview
```

## 📦 SOURCE CODE (`src/`)

### Core Modules (`src/core/`)
```
├── resilience.py                   # Retry logic with exponential backoff
├── logging.py                      # JSON logging with request context
```

### Middleware (`src/middleware/`)
```
├── logging_middleware.py           # Request ID tracking middleware
├── security.py                     # Rate limiting & security headers
```

### Models (`src/`)
```
├── models.py                       # Pydantic data models
```

### Application (`src/`)
```
├── main.py                         # FastAPI application (webhook handler)
├── test_real_kwork_flow.py         # Integration test with real data
└── show_dashboard_state.py         # Database state viewer
```

## 🗄️ DATABASE SCHEMA

### Tables
```sql
-- orders table (main Kwork orders)
CREATE TABLE IF NOT EXISTS public.orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  kwork_order_id BIGINT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'queued',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- order_events table (audit trail)
CREATE TABLE IF NOT EXISTS public.order_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES public.orders(id),
  stage TEXT NOT NULL,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Indexes
```sql
CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_source_id ON public.orders(kwork_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON public.orders(created_at);
CREATE INDEX IF NOT EXISTS idx_order_events_order_id ON public.order_events(order_id);
CREATE INDEX IF NOT EXISTS idx_order_events_level ON public.order_events(level);
CREATE INDEX IF NOT EXISTS idx_order_events_created_at ON public.order_events(created_at);
```

### RPC Functions
```sql
-- fh_event: Log order events
CREATE OR REPLACE FUNCTION fh_event(order_id UUID, stage TEXT, level TEXT, message TEXT)
RETURNS UUID AS $$

-- fh_ingress: Process incoming Kwork orders
CREATE OR REPLACE FUNCTION fh_ingress(source_id TEXT, topic TEXT)
RETURNS TABLE(order_id UUID, created BOOLEAN) AS $$

-- fh_read_job: Read next job from queue
CREATE OR REPLACE FUNCTION fh_read_job(queue_name TEXT DEFAULT 'job_queue')
RETURNS TABLE(msg_id BIGINT, vt TIMESTAMP, message JSONB) AS $$

-- fh_ack_job: Acknowledge job completion
CREATE OR REPLACE FUNCTION fh_ack_job(queue_name TEXT, msg_id BIGINT)
RETURNS BOOLEAN AS $$

-- fh_fail_job: Mark job as failed
CREATE OR REPLACE FUNCTION fh_fail_job(queue_name TEXT, msg_id BIGINT)
RETURNS BOOLEAN AS $$
```

### RLS Policies
```sql
-- orders table policies
CREATE POLICY orders_service_role ON public.orders
  USING (true) WITH CHECK (true);

CREATE POLICY orders_auth_read ON public.orders
  FOR SELECT USING (auth.role() = 'authenticated');

-- order_events table policies  
CREATE POLICY order_events_service_role ON public.order_events
  USING (true) WITH CHECK (true);

CREATE POLICY order_events_auth_read ON public.order_events
  FOR SELECT USING (auth.role() = 'authenticated');
```

## 🔧 DEPENDENCIES

### Python Packages (`requirements.txt`)
```
fastapi==0.104.1           # Web framework
uvicorn==0.24.0            # ASGI server
psycopg2-binary==2.9.9     # PostgreSQL adapter
pydantic==2.5.0            # Data validation
python-dotenv==1.0.0       # Environment variables
pysocks==1.7.1             # SOCKS proxy support
httpx==0.24.0              # Async HTTP client
supabase==2.0.1            # Supabase client
```

### System Requirements
- Python 3.11+
- PostgreSQL 15+ (Supabase)
- Docker & docker-compose (optional)

## 🚀 DEPLOYMENT CONFIGURATION

### Environment Variables (`.env`)
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Application Settings
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# Security
RATE_LIMIT_REQUESTS_PER_SECOND=10
```

### Docker Compose (`docker-compose.yml`)
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
    volumes:
      - .:/app
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📊 CODE METRICS

### File Statistics
```
Total Files: 15
Total Lines: ~1,200
Python Files: 10
SQL Files: 2
Markdown Files: 8
Configuration Files: 4
```

### Code Quality Indicators
```
✅ Async/await used consistently
✅ Type hints applied to all functions
✅ Pydantic models for data validation
✅ JSON logging with request context
✅ Error handling with retry logic
✅ Security middleware (rate limiting)
✅ Database operations parameterized
✅ Environment variables properly loaded
```

### Test Coverage
```
Unit Tests: 2 files (test_resilience.py, test_network_failure.py)
Integration Tests: 1 file (test_real_kwork_flow.py)
Test Coverage: ~40% (estimated)
```

## 🔄 DEVELOPMENT WORKFLOW

### Git Branches
```
main           - Production (protected)
feature/*      - Feature development
bugfix/*       - Bug fixes
release/*      - Release preparation
```

### Commit Convention
```
✅ SCHEMA: [description] - Database schema changes
✅ FEAT: [description] - New features
✅ FIX: [description] - Bug fixes
✅ TEST: [description] - Test additions/modifications
✅ DOCS: [description] - Documentation updates
✅ REFACTOR: [description] - Code refactoring
```

### Code Review Checklist
- [ ] Async functions properly await I/O
- [ ] Type hints present for all parameters/returns
- [ ] Error handling with specific exceptions
- [ ] No credentials in logs or code
- [ ] SQL queries parameterized
- [ ] Logging at appropriate levels
- [ ] Tests cover edge cases
- [ ] Documentation updated

## 🎯 KEY IMPLEMENTATIONS

### 1. Resilience System (`src/core/resilience.py`)
- Exponential backoff retry decorator
- Configurable retry attempts (default: 4)
- Configurable backoff factors (default: 1s, 2s, 4s, 8s)
- Error classification for auto-recovery
- Supabase-specific retry configuration

### 2. Logging System (`src/core/logging.py`)
- JSON-formatted structured logs
- Request ID tracking via ContextVar
- Correlation across async operations
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Context-aware logging (order_id, request_id, etc.)

### 3. Security Middleware (`src/middleware/security.py`)
- Rate limiting (10 requests/second per IP)
- Security headers (XSS protection, HSTS, etc.)
- Request ID injection
- Connection timeout handling

### 4. Data Models (`src/models.py`)
- Pydantic validation for Kwork orders
- Injection prevention in title/description
- Price validation (0.01 - 1,000,000)
- Example schemas for documentation

### 5. Webhook Handler (`src/main.py`)
- FastAPI application with async endpoints
- Pydantic validation at endpoint level
- Database operations with retry logic
- Health check endpoint
- Proper error responses

## 📈 PROGRESS TRACKING

### Completed Features (✅)
- Database schema deployed to Supabase
- Core resilience system implemented
- Structured logging with request context
- Security middleware (rate limiting)
- Pydantic data models
- Webhook endpoint with validation
- Docker configuration
- Development artifact system

### In Progress Features (🟡)
- Integration testing with real Kwork data
- Performance optimization
- Monitoring setup

### Planned Features (⬜)
- DeepSeek R1 integration for content generation
- Worker service for async processing
- Dashboard for order management
- Advanced analytics
- Email notifications
- Payment integration

## 🔗 RELATED DOCUMENTS

### Development Artifacts
- `CONTEXT_INJECTION.md` - Current project status
- `DEVELOPMENT_STATE.md` - Progress tracking
- `decisions.md` - Architectural decisions
- `ACTIVE_TASKS.md` - Current work items

### Documentation
- `docs/00-QUICKSTART.md` - Getting started guide
- `docs/01-DEPLOYMENT.md` - Deployment instructions
- `docs/02-CLINE-AUTO.md` - Cline automation guide
- `docs/03-CLINE-PROMPT.txt` - Cline prompt template

### Reports
- `phase1_verification_report.md` - Phase 1 completion report

---

**Maintained by:** Cline AI  
**Last Inventory Update:** 2026-01-09T18:18:12Z  
**Next Inventory Update:** After major code changes  
**Status:** ACTIVE - Development in progress