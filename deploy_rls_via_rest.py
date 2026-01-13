#!/usr/bin/env python3
"""
Deploy RLS policies to Supabase using REST API workaround
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def load_env_vars():
    """Load environment variables from .env file"""
    env_vars = {}
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env file not found")
        sys.exit(1)
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    return env_vars

def test_rls_status(env_vars):
    """Test current RLS status by trying to access data with anon key"""
    supabase_url = env_vars.get('SUPABASE_URL')
    supabase_anon_key = env_vars.get('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_anon_key:
        print("❌ Missing Supabase URL or ANON key")
        return False
    
    print("🧪 Testing current RLS status...")
    
    # Try to read from fh_orders with anon key
    curl_cmd = [
        'curl', '-s', '-X', 'GET',
        f'{supabase_url}/rest/v1/fh_orders?select=count',
        '-H', f'apikey: {supabase_anon_key}',
        '-H', f'Authorization: Bearer {supabase_anon_key}'
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"📥 Response: {result.stdout}")
            
            try:
                data = json.loads(result.stdout)
                if isinstance(data, list) and len(data) > 0:
                    count = data[0].get('count', 0)
                    print(f"✅ ANON key can access fh_orders: {count} rows")
                    print("   This suggests RLS is either disabled or has permissive policies")
                    return True
            except json.JSONDecodeError:
                print(f"❌ Failed to parse JSON response")
                return False
        else:
            print(f"❌ curl command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing RLS status: {e}")
        return False

def deploy_rls_alternative(env_vars):
    """
    Alternative approach: Since we can't execute SQL directly,
    we'll update the application to work with current RLS status
    and document the manual steps needed.
    """
    print("\n🚀 Alternative RLS deployment approach")
    print("=" * 50)
    
    supabase_url = env_vars.get('SUPABASE_URL')
    
    print("\n📋 MANUAL STEPS REQUIRED for RLS deployment:")
    print("=" * 50)
    print("""
Since direct SQL execution to Supabase is blocked, you need to:

1. **Login to Supabase Dashboard:**
   - Go to: https://supabase.com/dashboard
   - Select your project: yommcknuizxkwpmpvlmp

2. **Open SQL Editor:**
   - In left sidebar, click "SQL Editor"
   - Click "New query"

3. **Execute RLS SQL:**
   - Copy the content from 'enable_rls_policies.sql'
   - Paste into SQL Editor
   - Click "Run" or press Ctrl+Enter (Cmd+Enter on Mac)

4. **Verify RLS is enabled:**
   - Go to "Table Editor" → "fh_orders" table
   - Check "RLS" column shows "Enabled"
   - Check "Policies" tab shows 2 policies

5. **Test the configuration:**
   - Backend (service_role key) should still work
   - Frontend (anon key) should get permission errors
   - Update frontend to use authenticated requests if needed
""")
    
    print(f"\n🔗 Direct links:")
    print(f"   - SQL Editor: {supabase_url}/project/default/sql")
    print(f"   - Table Editor (fh_orders): {supabase_url}/project/default/editor")
    
    print("\n📁 SQL file location:")
    print(f"   - Local: {Path('enable_rls_policies.sql').absolute()}")
    
    return True

def create_rls_readme():
    """Create README file with RLS deployment instructions"""
    readme_content = """# RLS (Row Level Security) Deployment Guide

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
curl -X POST https://yommcknuizxkwpmpvlmp.supabase.co/rest/v1/rpc/execute_sql \\
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \\
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \\
  -H "Content-Type: application/json" \\
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
   curl -X GET https://yommcknuizxkwpmpvlmp.supabase.co/rest/v1/fh_orders \\
     -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \\
     -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
   # Should return data
   ```

2. **Test frontend (anon key):**
   ```bash
   curl -X GET https://yommcknuizxkwpmpvlmp.supabase.co/rest/v1/fh_orders \\
     -H "apikey: $SUPABASE_ANON_KEY" \\
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
"""
    
    with open('RLS_DEPLOYMENT_GUIDE.md', 'w') as f:
        f.write(readme_content)
    
    print(f"📘 Created RLS deployment guide: RLS_DEPLOYMENT_GUIDE.md")
    return True

def main():
    """Main deployment function"""
    print("🔐 RLS (Row Level Security) Deployment for Firehorse")
    print("=" * 50)
    
    # Load environment variables
    env_vars = load_env_vars()
    
    # Test current RLS status
    test_rls_status(env_vars)
    
    # Deploy using alternative approach
    deploy_rls_alternative(env_vars)
    
    # Create documentation
    create_rls_readme()
    
    print("\n✅ RLS deployment preparation complete!")
    print("\n📋 Next steps:")
    print("   1. Manually execute SQL in Supabase Dashboard")
    print("   2. Test backend functionality")
    print("   3. Update frontend authentication if needed")
    print("   4. Monitor for any permission errors")
    
    print("\n⚠️  IMPORTANT: For MVP, you may choose to keep RLS disabled")
    print("   and enable it later when implementing proper authentication.")

if __name__ == "__main__":
    main()
