
===== **CLINE FIREHORSE ADAPTIVE PRODUCTION WORKFLOW v9.0 ULTIMATE** =====
**2026 Prompt Engineering: ToT + CoVeT + Reflexion + Memory Bank + Atomic Phases** [web:223][web:190][web:180][web:191][web:228]

🎯 **ULTIMATE OBJECTIVE**: 
**Adaptive self-improving workflow** — анализирует текущее состояние, фиксирует прогресс, разбивает на атомарные блоки с **mandatory verification gates**, **запоминает контекст** в Memory Bank, переходит только при 100% success. **Никогда не ломает рабочее**.

**MEMORY BANK INTEGRATION** (Cline feature [web:180]):
- **.clinerules/memory/project-state.md** — текущее состояние
- **.clinerules/memory/known-issues.md** — проблемы + решения
- **.clinerules/memory/completed-phases.md** — успешные блоки

---

## **<CONTEXT MEMORY> Current Firehorse State** (2026-01-13 13:36)
```
✅ Backend: /srv/firehorse-backend/ (firehorse-api Up+healthy, src/main.py)
✅ Supabase: yommcknuizxkwpmpvlmp.co (fh_orders/fh_order_events, RLS DISABLED)
✅ Keys: Anon+Service Role VALID (.env updated)
✅ Xray VPN: 127.0.0.1:7890/7891 (DeepSeek bypass)
✅ Schema: fh_orders(source_id TEXT UNIQUE, topic TEXT, status TEXT) — EMPTY
✅ Health: /health 200 OK (observability logs)
✅ Missing: RPC fh_ingress(p_kwork_order_id BIGINT, p_title TEXT)
✅ Pydantic: src/main.py → kwork_order_id:int, title:str (verify)
✅ Docker: /srv/firehorse-backend/docker-compose.yml (firehorse-api)
✅ Progress: 92% → Target 100%
```

**TREND**: RLS fixed, keys valid, API healthy. **Blocker: RPC missing**.

---

## **<TREE-OF-THOUGHT> Adaptive Hypotheses** (Dynamic, Confidence-based)
```
H1: RPC fh_ingress absent (9.8/10) → CREATE + TEST
H2: Pydantic mismatch src/main.py (4.2/10) → Schema introspect + fix
H3: Worker untested (2.1/10) → pgmq jobqueue verify
H4: Frontend integration (1.5/10) → /api/webhook React Query
```

**PRIORITY**: Highest confidence → Test → Fix → Verify → Memory Update.

---

## **<ATOMIC PHASES> Block-Verified Workflow** (No Skip Allowed)

### **PHASE 0: MEMORY SYNCHRONIZATION** (Context Load)
```
1. READ .clinerules/memory/project-state.md → Current status
2. READ .clinerules/memory/known-issues.md → Past fixes
3. UPDATE memory with conversation context
<VERIFY>: Memory consistent? → PASS
╔══════════════════════╗
║ PHASE 0: SYNC ✅     ║
╚══════════════════════╝
```

### **PHASE 1: CURRENT STATE AUDIT** (5 Commands, Raw Output)
```
cd /srv/firehorse-backend
docker compose ps  # api Up+healthy?
curl -v http://127.0.0.1:8000/health  # 200?
cat .env | grep SUPABASE  # Keys present?
curl --proxy http://127.0.0.1:7890 "https://yommcknuizxkwpmpvlmp.supabase.co/rest/v1/fh_orders?limit=1" -H "apikey: ANON_KEY"  # Tables accessible?
curl --proxy http://127.0.0.1:7890 -X POST "https://yommcknuizxkwpmpvlmp.supabase.co/rpc/fh_ingress" -H "apikey: SERVICE_KEY" -d '{}'  # RPC status?
```
**<GATE>**: All 200/Up? → PASS → Phase 2. **FAIL → Report + Halt**.

### **PHASE 2: RPC fh_ingress IMPLEMENT** (Supabase SQL Editor)
```
Dashboard → SQL Editor → New Query → EXECUTE BLOCK:

-- PRODUCTION fh_ingress (fh_orders schema match)
CREATE OR REPLACE FUNCTION fh_ingress(p_kwork_order_id BIGINT, p_title TEXT)
RETURNS TABLE(order_id UUID, created BOOLEAN) AS $$
DECLARE vid UUID; vcreated BOOLEAN := false;
BEGIN
  INSERT INTO fh_orders(source_id, topic, status) 
  VALUES(p_kwork_order_id::TEXT, p_title, 'queued')
  ON CONFLICT(source_id) DO NOTHING RETURNING id INTO vid;
  IF NOT FOUND THEN 
    SELECT id INTO vid FROM fh_orders WHERE source_id = p_kwork_order_id::TEXT;
  ELSE vcreated := true; 
  END IF;
  RETURN QUERY SELECT COALESCE(vid, '00000000-0000-0000-0000-000000000000'::UUID), vcreated;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- VERIFY IMMEDIATELY
SELECT * FROM fh_ingress(999999, 'Phase2 Test');
```
**<GATE>**: `[{"order_id":"uuid","created":true}]`? → **UPDATE memory/completed-phases.md** → PASS.

### **PHASE 3: BACKEND INTEGRATION** (Pydantic + Restart)
```
1. VERIFY Pydantic: curl -X POST http://127.0.0.1:8000/webhook -H "X-Token: TOKEN" -d '{}' -v  # Schema?
2. docker compose restart api
3. sleep 3; curl http://127.0.0.1:8000/health  # Healthy?
```
**<GATE>**: Health 200 + No Pydantic errors? → PASS.

### **PHASE 4: E2E WEBHOOK** (Critical Path)
```
TOKEN=$(grep -i ingress .env | cut -d= -f2- | tr -d ' 
')
curl -v -X POST http://127.0.0.1:8000/webhook   -H "X-Token: $TOKEN" -d '{"kwork_order_id":444444,"title":"E2E Phase4"}'
```
**<GATE>**: `200 {"status":"accepted","order_id":"uuid"}`? → PASS.

### **PHASE 5: DB + QUEUE VERIFY** (Xray)
```
curl --proxy http://127.0.0.1:7890   "https://yommcknuizxkwpmpvlmp.supabase.co/rest/v1/fh_orders?source_id=eq.444444"   -H "apikey: SERVICE_KEY"
curl --proxy http://127.0.0.1:7890   "https://yommcknuizxkwpmpvlmp.supabase.co/rpc/pgmq_read?queue_name=jobqueue"   -H "apikey: SERVICE_KEY" -d '{"count":1}'
```
**<GATE>**: Record exists? → **Memory Bank Update** → Phase 6.

### **PHASE 6: WORKER + DEEPSEEK** (AI Pipeline)
```
docker compose logs worker --tail 20  # Processing?
curl --proxy http://127.0.0.1:7890   "https://yommcknuizxkwpmpvlmp.supabase.co/rest/v1/fh_orders?status=eq.completed&limit=1"   -H "apikey: SERVICE_KEY"
```
**<GATE>**: AI complete? → PASS.

### **PHASE 7: PRODUCTION HARDEN + MEMORY FREEZE**
```
git add .
git commit -m "feat: firehorse production v1.0 $(date)"
echo "🎉 ALL PHASES COMPLETE → PRODUCTION LIVE!" >> .clinerules/memory/completed-phases.md
```

---

## **<SELF-IMPROVEMENT> Reflexion + Memory Bank**
```
**REFLECT**: What worked? What to improve for v9.1?
**MEMORY UPDATE**:
- project-state.md: "Webhook E2E 100%, Worker pending"
- known-solutions.md: "RLS → DISABLE for dev; RPC → SECURITY DEFINER"
**GATEKEEPER**: No phase skipped. 100% verification.
```

**EXECUTE PHASE 1 → Block-by-Block → PRODUCTION!** 🔥

===== END ULTIMATE WORKFLOW =====
    