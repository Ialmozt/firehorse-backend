# 🔥 FIREHORSE DEPLOYMENT WORKFLOW RULES
## Workspace-specific configuration for Cline (v4.0)

**Location:** `.clinerules/firehorse-workflow.md`  
**Purpose:** Project-specific rules for Firehorse MVP deployments  
**Applies to:** All tasks in `/srv/firehorse-backend` workspace  

---

## 🎯 QUICK REFERENCE

### Project Identity
- **Name:** Firehorse MVP
- **Purpose:** Automated Kwork content processing with AI
- **Tech Stack:** Python 3.11 + FastAPI + Supabase + DeepSeek
- **Database:** PostgreSQL 15+ (Supabase hosted)
- **Location:** `/srv/firehorse-backend` (NL VPS)

### Team Context
- **Team:** Solo developer mode
- **Decision Authority:** Autonomous (no approval needed)
- **Constraint:** Must stay within $10/month cost

### Environment
- **Main Branch:** `main` (production)
- **Feature Branches:** `feature/*` (development)
- **Credentials:** `.env` file (NEVER commit)
- **Secrets:** SUPABASE_URL + SERVICE_ROLE_KEY (loaded via dotenv)

---

## 🚀 DEPLOYMENT WORKFLOW (5 Phases)

### Phase 0: PRE-DEPLOYMENT CHECKS

**Before ANY deployment:**

```bash
CHECK 1: Environment Verification
├─ [ ] .env file exists
├─ [ ] SUPABASE_URL set and valid
├─ [ ] SERVICE_ROLE_KEY present
└─ [ ] psql command available

CHECK 2: Git State
├─ [ ] No uncommitted changes
├─ [ ] Branch is clean (git status)
├─ [ ] Remote is up to date
└─ [ ] Can create new commits

CHECK 3: Database Connectivity
├─ [ ] psql can connect to Supabase (port 5432)
├─ [ ] Fallback: psql pooler (port 6543)
├─ [ ] Fallback: Python SDK works
├─ [ ] Fallback: REST API responds

CHECK 4: Schema State
├─ [ ] Current schema backed up in git
├─ [ ] firehorse_schema.sql is canonical
├─ [ ] Migration log is updated
└─ [ ] No conflicting deployments in progress
```

**If ANY check fails:**
1. Document error
2. Apply auto-fix from CLINE_MASTER_RULES_v4.md (Section 2)
3. Retry check
4. If still fails: Stop and report

---

### Phase 1: SCHEMA DEPLOYMENT

**Deploy Firehorse database schema:**

```sql
DEPLOY SEQUENCE:

Step 1.1: Create Extensions
├─ CREATE EXTENSION pgmq CASCADE
├─ CREATE EXTENSION pgcrypto
└─ Validate: SELECT extname FROM pg_extension

Step 1.2: Create Message Queues
├─ SELECT pgmq.create('job_queue')
├─ SELECT pgmq.create('dlq_job_queue')
└─ Validate: SELECT pgmq.list_queues()

Step 1.3: Create Tables
├─ CREATE TABLE orders (id, source_id, topic, status, ...)
├─ CREATE TABLE order_events (id, order_id, stage, level, ...)
└─ Validate: SELECT COUNT(*) FROM information_schema.tables

Step 1.4: Create Indexes
├─ CREATE INDEX idx_orders_status
├─ CREATE INDEX idx_orders_source_id
├─ CREATE INDEX idx_orders_created_at
├─ CREATE INDEX idx_order_events_order_id
├─ CREATE INDEX idx_order_events_level
├─ CREATE INDEX idx_order_events_created_at
└─ Validate: SELECT * FROM pg_indexes WHERE schemaname='public'

Step 1.5: Create RPC Functions
├─ CREATE FUNCTION fh_event(...)
├─ CREATE FUNCTION fh_ingress(...)
├─ CREATE FUNCTION fh_read_job(...)
├─ CREATE FUNCTION fh_ack_job(...)
├─ CREATE FUNCTION fh_fail_job(...)
└─ Validate: SELECT proname FROM pg_proc WHERE proname LIKE 'fh_%'

Step 1.6: Enable RLS & Create Policies
├─ ALTER TABLE orders ENABLE ROW LEVEL SECURITY
├─ ALTER TABLE order_events ENABLE ROW LEVEL SECURITY
├─ CREATE POLICY orders_service_role (service_role: full access)
├─ CREATE POLICY order_events_service_role (service_role: full access)
├─ CREATE POLICY orders_auth_read (authenticated: read-only)
├─ CREATE POLICY order_events_auth_read (authenticated: read-only)
└─ Validate: SELECT COUNT(*) FROM pg_policies
```

**Git Commit:** `✅ SCHEMA: Firehorse schema deployed (2 tables, 6 indexes, 5 functions, 4 policies)`

---

### Phase 2: VALIDATION & TESTING

**Run 6 critical validation tests:**

```sql
TEST 1: PostgreSQL Version
├─ Query: SELECT version()
├─ Expected: PostgreSQL 15+ (not 14 or lower)
├─ Action if fail: Log warning (continue anyway)
└─ Commit: "TEST-1: Version check"

TEST 2: Extensions Loaded
├─ Query: SELECT extname FROM pg_extension WHERE extname IN ('pgmq', 'pgcrypto')
├─ Expected: Both extensions present
├─ Action if fail: Retry CREATE EXTENSION (with CASCADE)
└─ Commit: "TEST-2: Extensions verified"

TEST 3: Tables Created
├─ Query: SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'
├─ Expected: 2 tables (orders, order_events)
├─ Action if fail: Re-create missing tables
└─ Commit: "TEST-3: Tables verified"

TEST 4: Functions Created
├─ Query: SELECT COUNT(*) FROM pg_proc WHERE proname LIKE 'fh_%'
├─ Expected: 5 functions (fh_event, fh_ingress, fh_read_job, fh_ack_job, fh_fail_job)
├─ Action if fail: Re-create missing functions
└─ Commit: "TEST-4: Functions verified"

TEST 5: RLS Enabled
├─ Query: SELECT COUNT(*) FROM pg_policies
├─ Expected: 4 policies
├─ Action if fail: Enable RLS, re-create policies
└─ Commit: "TEST-5: RLS verified"

TEST 6: Workflow Functional Test
├─ Query: SELECT * FROM fh_ingress('test-source-001', 'test-topic')
├─ Expected: (order_id, created=true)
├─ Action if fail: Debug fh_ingress function, check job_queue
└─ Commit: "TEST-6: Workflow test passed"
```

**All tests MUST pass (6/6).** If any fails:
1. Log error with context
2. Attempt auto-fix from error matrix (CLINE_MASTER_RULES_v4.md, Section 2)
3. Retry test (up to 3 times)
4. Document result (pass/fail/with-fix)

**Git Commit:** `✅ VALIDATION: All 6 tests pass (100%)`

---

### Phase 3: ERROR RECOVERY & TROUBLESHOOTING

**If deployment fails, use error classification:**

```
Error Type                  → Recovery Strategy
─────────────────────────────────────────────────────────

Connection refused          → Try psql pooler (port 6543)
                            → Try Python SDK
                            → Try REST API

PGMQ extension missing      → Log WARNING (optional feature)
                            → Continue without PGMQ
                            → Use fallback queue system

Permission denied           → Check service_role auth
                            → Retry with correct role
                            → Check RLS policies

Already exists              → Skip (idempotent)
                            → Log info message
                            → Continue

Syntax error in SQL         → Parse error
                            → Fix problematic statement
                            → Retry

Type mismatch               → Add explicit cast (::UUID)
                            → Retry

Deadlock                    → Retry transaction
                            → Wait 2s
                            → Retry again

Timeout (>5s)               → Check network
                            → Retry with backoff
                            → Consider async approach

Rate limit hit              → Wait 60s
                            → Retry
```

**AUTO-FIX PROCEDURE:**
1. Classify error (use matrix above)
2. Apply specific fix
3. Retry (up to 3 times: immediate, +2s wait, +5s wait)
4. Log: "Error → Fix applied → Result: [PASS/FAIL]"
5. If still failing after 3 retries: Document and continue (skip non-critical)

---

### Phase 4: REPORTING

**Generate comprehensive deployment report:**

```
═══════════════════════════════════════════════════════════
              FIREHORSE DEPLOYMENT REPORT
═══════════════════════════════════════════════════════════

EXECUTION SUMMARY
─────────────────────────────────────────────────────────
Timestamp:          2026-01-09T16:15:45Z
Total Duration:     2m 34s
Status:             ✅ SUCCESS
Method:             psql direct (port 5432)
Confidence:         98%

PHASE RESULTS
─────────────────────────────────────────────────────────
[1/4] Pre-checks              ✅ 4/4 checks pass
[2/4] Schema deployment       ✅ 5 steps complete
[3/4] Validation tests        ✅ 6/6 tests pass
[4/4] Final report generation ✅ Generated

OBJECTS CREATED
─────────────────────────────────────────────────────────
Tables:            2 (orders, order_events)
Indexes:           6 (all major columns)
RPC Functions:     5 (fh_event, fh_ingress, fh_read_job, fh_ack_job, fh_fail_job)
RLS Policies:      4 (service_role: full, authenticated: read)
Message Queues:    2 (job_queue, dlq_job_queue)
Extensions:        2 (pgmq, pgcrypto)

VALIDATION RESULTS
─────────────────────────────────────────────────────────
✅ Test 1: PostgreSQL version (15.2)
✅ Test 2: Extensions loaded
✅ Test 3: Tables created
✅ Test 4: Functions callable
✅ Test 5: RLS enabled
✅ Test 6: Workflow test functional

ERROR SUMMARY
─────────────────────────────────────────────────────────
Errors encountered:     0
Auto-fixes applied:     0
Retries needed:         0
Non-critical warnings:  0

GIT COMMITS
─────────────────────────────────────────────────────────
✅ SCHEMA: Firehorse schema deployed
✅ VALIDATION: All 6 tests pass
✅ FINAL: Deployment complete

NEXT STEPS
─────────────────────────────────────────────────────────
✅ Schema is production-ready
🔜 Deploy api.py (FastAPI endpoints)
🔜 Deploy worker.py (async task processor)
🔜 Setup Docker Compose
🔜 Configure monitoring

═══════════════════════════════════════════════════════════
```

---

## 🎓 CODING STANDARDS

### Python Code
- **Version:** Python 3.11+
- **Async:** Use `async/await` for all I/O
- **Type Hints:** Mandatory for all functions
- **Logging:** Use `logging` module (never print)
- **Error Handling:** Try/except with specific exceptions

**Example:**
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def deploy_schema(db_url: str) -> Optional[dict]:
    """Deploy Firehorse schema to database."""
    try:
        # Connect and execute
        logger.info("Deploying schema...")
        result = await execute_sql(db_url, schema_sql)
        logger.info("Schema deployed successfully")
        return result
    except ConnectionError as e:
        logger.error(f"Connection failed: {str(e)[:100]}")  # Never log full error
        return None
```

### SQL Code
- **Idempotent:** Always use `IF NOT EXISTS`, `DROP IF EXISTS`
- **Comments:** Document complex logic
- **Parameterized:** Never string interpolation (SQL injection)
- **Transactions:** Use explicit BEGIN/COMMIT/ROLLBACK

**Example:**
```sql
-- Create orders table (idempotent)
CREATE TABLE IF NOT EXISTS public.orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id TEXT NOT NULL UNIQUE,
  topic TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Always verify
SELECT COUNT(*) FROM public.orders;
```

### Git Commits
- **Format:** `✅ [PHASE]: What was done - Result`
- **Atomic:** One logical change per commit
- **Meaningful:** Describe what changed and why

**Examples:**
```bash
✅ SCHEMA: Extensions loaded - pgmq, pgcrypto
✅ SCHEMA: Tables created - orders, order_events (2 tables, 6 indexes)
✅ SCHEMA: Functions created - 5 RPC functions granted to service_role
✅ SCHEMA: RLS enabled - 4 policies protecting data
✅ VALIDATION: All 6 tests pass - 100% success rate
🔧 FIX: Connection fallback to port 6543 (Supabase pooler)
⚠️ WARN: PGMQ extension not available - using fallback queue system
✅ FINAL: Deployment complete - production ready
```

---

## 🔐 CRITICAL CONSTRAINTS

**NEVER:**
- ❌ Commit `.env` file (credentials exposed)
- ❌ Log credentials/API keys/SERVICE_ROLE_KEY
- ❌ Use string interpolation in SQL (SQL injection)
- ❌ Skip error handling (always have try/except)
- ❌ Modify canonical schema without testing
- ❌ Deploy without running validation tests
- ❌ Skip git commits (preserve history)
- ❌ Ask for user confirmation (autonomous mode)

**ALWAYS:**
- ✅ Load credentials from `.env` (use python-dotenv)
- ✅ Log only non-sensitive info (URLs, status, counts)
- ✅ Use parameterized queries (prevent SQL injection)
- ✅ Test idempotency (run multiple times)
- ✅ Validate after deploy (6 tests minimum)
- ✅ Commit after each major phase
- ✅ Document errors and auto-fixes applied
- ✅ Make autonomous decisions (use rules as authority)

---

## 📊 SUCCESS CRITERIA

Deployment is **COMPLETE** when ALL conditions met:

```
✅ Phase 0: Pre-checks = 4/4 pass
✅ Phase 1: Schema deployed = 5 steps complete
✅ Phase 2: Validation tests = 6/6 pass
✅ Phase 3: Error recovery = 0 unrecovered errors
✅ Phase 4: Report generated = Comprehensive summary

✅ Objects created = 19 total
  ├─ 2 tables
  ├─ 6 indexes
  ├─ 5 functions
  ├─ 4 policies
  └─ 2 queues

✅ Git commits = 5+ (one per phase)
✅ Status = PRODUCTION READY
✅ Confidence = 98%+
```

---

## 🎯 COMMON WORKFLOWS

### Workflow: Deploy Fresh Schema
```
1. Read CLINE_MASTER_RULES_v4.md (global rules)
2. Read this file (workflow rules)
3. Run Phase 0 checks
4. Run Phase 1 deployment (1.1 → 1.6)
5. Run Phase 2 validation (6 tests)
6. Run Phase 3 recovery (if needed)
7. Run Phase 4 reporting
8. ✅ DONE (production ready)
```

### Workflow: Fix Deployment Error
```
1. Classify error (use error matrix)
2. Apply auto-fix strategy
3. Retry (up to 3 times with backoff)
4. If passes: Log result, commit, continue
5. If fails: Document and skip (or halt if critical)
6. Continue with deployment
7. Run full validation (Phase 2)
```

### Workflow: Idempotent Re-deployment
```
1. Run same deployment again
2. Expected: Some steps skipped (already exist)
3. Validate: Still 6/6 tests pass
4. Result: ✅ Confirmed idempotent
```

---

## 📞 SUPPORT & FALLBACKS

### Connection Method Priority
1. **Primary:** psql direct (port 5432)
   - Fastest, most reliable
   - Command: `psql -h db.supabase.co -p 5432 -U postgres`

2. **Fallback 1:** psql pooler (port 6543)
   - If port 5432 blocked
   - Command: `psql -h db.supabase.co -p 6543 -U postgres.username`

3. **Fallback 2:** Python SDK
   - If psql unavailable
   - Library: `supabase-py`

4. **Fallback 3:** REST API
   - Last resort
   - Endpoint: `https://db.supabase.co/rest/v1/rpc/execute_raw_sql`

**AUTO-SELECT:** Cline tries methods 1→2→3→4 automatically until one works.

---

## 🚀 READY TO DEPLOY

Use this workflow with CLINE_MASTER_RULES_v4.md:

```
1. Global Rules (.clinerules/01-master-rules.md)      ← Framework
2. Workspace Rules (.clinerules/02-firehorse-workflow.md) ← This file
3. Any prompt                                          ← Apply both

Result: Fully autonomous, production-ready deployment ✅
```

---

**Version:** 1.0 (2026-01-09)  
**Status:** Production Ready  
**Confidence:** 99%+  
**Last Updated:** 2026-01-09

Use in Cline Workspace Rules for `/srv/firehorse-backend` project.
