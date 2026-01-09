# ARCHITECTURAL DECISIONS - Firehorse SaaS Project
**Last Updated:** 2026-01-09T18:09:06Z  
**Total Decisions:** 6 (as referenced in CONTEXT_INJECTION.md)

## 📋 DECISION LOG

### #D001: Async/Await for All I/O Operations
**Date:** 2026-01-09  
**Status:** IMPLEMENTED  
**Rationale:** 
- Modern Python async/await provides better performance for I/O-bound operations
- FastAPI is built on async/await, leveraging Starlette's async capabilities
- Supabase REST API calls are network I/O, perfect for async
- Better resource utilization with connection pooling
**Implementation Location:** 
- `src/main.py` - All endpoint functions are async
- `src/core/resilience.py` - Retry decorator supports async functions
- Database operations use httpx.AsyncClient
**Code Reference:** 
```python
# src/main.py lines 79, 103
async def health_check():
async def webhook(request: Request):
```
**Impact:** All I/O operations non-blocking, better scalability

### #D002: Type Hints Mandatory for All Functions
**Date:** 2026-01-09  
**Status:** IMPLEMENTED  
**Rationale:**
- Improved code readability and maintainability
- Better IDE support (autocomplete, error detection)
- Early bug detection with mypy or pyright
- Self-documenting code
- Required for Pydantic model validation
**Implementation Location:**
- All Python files in the project
- Function signatures include parameter and return type hints
- Pydantic models with explicit field types
**Code Reference:**
```python
# src/main.py line 79
async def health_check() -> HealthResponse:

# src/models.py (when created)
class WebhookPayload(BaseModel):
    id: int
    title: str
```
**Impact:** Better code quality, fewer runtime type errors

### #D003: Structured JSON Logging (Not Human Text)
**Date:** 2026-01-09  
**Status:** PARTIALLY IMPLEMENTED  
**Rationale:**
- Machine-readable logs for automated processing
- Integration with log aggregators (ELK stack, Datadog, etc.)
- Consistent field structure for filtering and searching
- Request ID correlation across distributed systems
- Better performance with bulk log processing
**Implementation Location:**
- `src/core/logging.py` - JSON formatter implementation
- `src/middleware/logging_middleware.py` - Request ID tracking
- ContextVar for request context propagation
**Code Reference:** (To be implemented)
```python
# JSON log format
{
  "timestamp": "2026-01-09T18:09:06Z",
  "level": "INFO",
  "request_id": "uuid-here",
  "message": "webhook received",
  "order_id": "kwork_12345"
}
```
**Impact:** Production-ready observability, easier debugging

### #D004: Request ID Tracking for Complete Request Journey
**Date:** 2026-01-09  
**Status:** PARTIALLY IMPLEMENTED  
**Rationale:**
- Trace single request across entire system
- Correlate logs from different components
- Essential for debugging in distributed systems
- Required for SLA monitoring and performance analysis
- Standard practice in microservices architecture
**Implementation Location:**
- `src/middleware/logging_middleware.py` - Generate and propagate request ID
- `src/core/logging.py` - Include request_id in all log entries
- Response headers include X-Request-ID
**Code Reference:** (To be implemented)
```python
# Middleware generates request ID
request_id = str(uuid.uuid4())
request_id_var.set(request_id)

# All logs include request_id
logger.info("message", extra={"request_id": request_id})
```
**Impact:** Complete request tracing, faster incident resolution

### #D005: Rate Limiting - 10 Requests/Second per IP
**Date:** 2026-01-09  
**Status:** PARTIALLY IMPLEMENTED  
**Rationale:**
- Protect API from abuse and DoS attacks
- Ensure fair usage among clients
- Prevent resource exhaustion
- Standard API best practice
- Configurable for different environments
**Implementation Location:**
- `src/middleware/security.py` - Rate limiting middleware
- Fixed window algorithm (simpler than token bucket for MVP)
- IP-based tracking (with X-Forwarded-For support)
**Code Reference:** (To be implemented)
```python
# Rate limiting logic
if len(request_times) >= 10:
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
```
**Impact:** API protection, predictable performance

### #D006: Retry Strategy - Exponential Backoff (1s → 2s → 4s → 8s)
**Date:** 2026-01-09  
**Status:** PARTIALLY IMPLEMENTED  
**Rationale:**
- Handle transient network failures gracefully
- Avoid overwhelming failed services with immediate retries
- Standard pattern for distributed systems resilience
- Configurable max retries (3) and max wait (8s)
- Error classification to determine retry eligibility
**Implementation Location:**
- `src/core/resilience.py` - @retry_with_backoff decorator
- Error classifier function (5xx retry, 4xx fail-fast)
- Applied to webhook endpoint for Supabase calls
**Code Reference:** (To be implemented)
```python
@retry_with_backoff(max_retries=3, base_delay=1.0)
async def webhook(request: Request):
    # Will retry on network errors with 1s, 2s, 4s delays
```
**Impact:** Improved reliability, automatic failure recovery

## 🎯 DECISION FRAMEWORK

### Decision Making Process
1. **Identify Need:** What problem are we solving?
2. **Research Options:** What are the possible solutions?
3. **Evaluate Tradeoffs:** Pros and cons of each option
4. **Make Decision:** Choose based on project constraints
5. **Document:** Record decision here with rationale
6. **Implement:** Code the decision
7. **Review:** Periodically reassess decisions

### Decision Categories
- **ARCHITECTURAL:** System design, technology choices
- **IMPLEMENTATION:** Coding patterns, library choices  
- **OPERATIONAL:** Deployment, monitoring, scaling
- **SECURITY:** Authentication, authorization, protection

### Decision Authority
- **Cline AI:** Autonomous decisions within project constraints
- **User:** Final approval for major architectural changes
- **Framework:** Follow established patterns from CLINE_MASTER_RULES

## 🔄 DECISION HISTORY

### 2026-01-09: Foundation Decisions
1. **#D001:** Async/await pattern established
2. **#D002:** Type hints mandated
3. **#D003:** JSON logging chosen over text logging
4. **#D004:** Request ID tracking required
5. **#D005:** Rate limiting strategy defined
6. **#D006:** Retry strategy with exponential backoff

### Upcoming Decisions (To Be Made)
- **#D007:** Database connection pooling strategy
- **#D008:** Error monitoring and alerting approach
- **#D009:** Deployment strategy (Docker, VPS, etc.)
- **#D010:** Monitoring and metrics collection

## 📊 DECISION COMPLIANCE

### Current Compliance Status
```
#D001: Async/Await          ✅ 100% COMPLIANT
#D002: Type Hints           ✅ 100% COMPLIANT  
#D003: JSON Logging         🟡 50% COMPLIANT
#D004: Request ID Tracking  🟡 50% COMPLIANT
#D005: Rate Limiting       🟡 50% COMPLIANT
#D006: Retry Strategy      🟡 50% COMPLIANT
```

### Verification Method
- Code review of implementation
- Automated tests validating decision compliance
- Manual testing of features
- Documentation in code comments

## 🚨 DECISION REVIEW SCHEDULE

### Quarterly Reviews
- **Next Review:** 2026-04-09
- **Scope:** Re-evaluate all decisions for relevance
- **Criteria:** 
  - Still solving the right problem?
  - Better alternatives available?
  - Performance impact acceptable?
  - Maintenance burden reasonable?

### Trigger-Based Reviews
Review decisions when:
- Technology stack changes
- Performance requirements change
- Security requirements evolve
- Team size or expertise changes
- Cost constraints change

---

**Last Updated:** 2026-01-09T18:09:06Z  
**Next Decision ID:** #D007  
**Decision Framework:** CLINE_MASTER_RULES v4.0 compliant