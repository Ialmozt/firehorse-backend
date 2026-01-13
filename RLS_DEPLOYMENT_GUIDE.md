# RLS (Row Level Security) Deployment Guide

## Current Status
- **RLS Status:** Disabled (for MVP simplicity)
- **Security Risk:** Tables are publicly readable/writable with anon key
- **Recommendation:** Enable RLS for production security

## Deployment Instructions

### Method 1: Supabase Dashboard (Recommended)
1. Login to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select project: `yommcknuizxkwpmpvlmp`
3. Go to **SQL Editor** → **New query**
4. Copy content from `enable_rls_policies.sql`
5. Paste and execute (Ctrl+Enter / Cmd+Enter)
6. Verify in **Table Editor** that RLS is enabled

### Method 2: psql command line (If credentials work)
```bash
# Set environment variables
export PGPASSWORD="your_database_password"

# Execute SQL
psql "postgresql://postgres.yommcknuizxkwpmpvlmp@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require" -f enable_rls_policies.sql
```

### Method 3: REST API (If execute_sql function exists)
```bash
# This requires the execute_sql RPC function to be created in Supabase
curl -X POST https://yommcknuizxkwpmpvlmp.supabase.co/rest/v1/rpc/execute_sql \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "ALTER TABLE fh_orders ENABLE ROW LEVEL SECURITY;"}'
```

## Policy Configuration
The SQL script creates the following policies:

### fh_orders table
1. **Service role full access** - Backend (FastAPI) can do everything
2. **Authenticated users read-only** - Frontend can read data

### fh_order_events table
1. **Service role full access** - Backend (FastAPI) can do everything
2. **Authenticated users read-only** - Frontend can read data

## Impact on Application

### Backend (FastAPI)
- ✅ No changes needed (uses service_role key)
- ✅ Full access to all tables
- ✅ Webhook processing continues to work

### Frontend (React)
- ❌ May break if using anon key (no access with RLS)
- ✅ Will work if using authenticated requests
- ✅ Temporary workaround: Keep RLS disabled for MVP

## Testing
After enabling RLS:

1. **Test backend:**
   ```bash
   curl -X GET https://yommcknuizxkwpmpvlmp.supabase.co/rest/v1/fh_orders \
     -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
     -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
   # Should return data
   ```

2. **Test frontend (anon key):**
   ```bash
   curl -X GET https://yommcknuizxkwpmpvlmp.supabase.co/rest/v1/fh_orders \
     -H "apikey: $SUPABASE_ANON_KEY" \
     -H "Authorization: Bearer $SUPABASE_ANON_KEY"
   # Should return permission error or empty array
   ```

## Rollback
If RLS causes issues, disable it:
```sql
ALTER TABLE fh_orders DISABLE ROW LEVEL SECURITY;
ALTER TABLE fh_order_events DISABLE ROW LEVEL SECURITY;
```

## Security Considerations
1. **MVP Phase:** RLS disabled for simplicity
2. **Production:** RLS must be enabled
3. **Data Exposure:** Without RLS, anyone with anon key can read/write data
4. **Authentication:** Frontend should use proper authentication for production

## Files
- `enable_rls_policies.sql` - SQL script to enable RLS and create policies
- `deploy_rls_via_rest.py` - Deployment script (alternative methods)
- This file: `RLS_DEPLOYMENT_GUIDE.md`
