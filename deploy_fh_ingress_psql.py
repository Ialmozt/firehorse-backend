#!/usr/bin/env python3
"""
Deploy fixed fh_ingress RPC function to Supabase using psql
"""

import os
import subprocess
import sys
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

def execute_sql_via_psql(sql_content: str, env_vars: dict):
    """Execute SQL via psql command"""
    # Get database credentials
    db_host = env_vars.get('DATABASE_HOST', 'aws-0-eu-west-1.pooler.supabase.com')
    db_port = env_vars.get('DATABASE_PORT', '5432')
    db_name = env_vars.get('DATABASE_NAME', 'postgres')
    db_user = env_vars.get('DATABASE_USER', 'postgres.yommcknuizxkwpmpvlmp')
    db_password = env_vars.get('DATABASE_PASSWORD', 'bkOFQ9jiln6JE82v')
    
    # Build connection string
    conn_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require"
    
    print(f"🔗 Connecting to: {db_host}:{db_port}")
    print(f"📊 Database: {db_name}")
    print(f"👤 User: {db_user}")
    
    try:
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password
        
        cmd = ['psql', conn_str, '-c', sql_content]
        print(f"⚡ Executing SQL via psql...")
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=30)
        
        print("📋 STDOUT:", result.stdout)
        if result.stderr:
            print("⚠️ STDERR:", result.stderr)
        print("🔢 Return code:", result.returncode)
        
        if result.returncode == 0:
            print("✅ SQL executed successfully!")
            return True
        else:
            print("❌ SQL execution failed")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_fh_ingress_via_curl(env_vars: dict):
    """Test the fh_ingress function via curl"""
    supabase_url = env_vars.get('SUPABASE_URL')
    supabase_anon_key = env_vars.get('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_anon_key:
        print("❌ Missing Supabase URL or ANON key")
        return False
    
    # Test with a unique order ID to avoid conflicts
    import time
    test_order_id = int(time.time()) % 1000000000
    test_title = f"Test Order {test_order_id}"
    
    print(f"\n🧪 Testing fh_ingress function...")
    print(f"   Test order ID: {test_order_id}")
    print(f"   Test title: {test_title}")
    
    # Build curl command
    curl_cmd = [
        'curl', '-s', '-X', 'POST',
        f'{supabase_url}/rest/v1/rpc/fh_ingress',
        '-H', f'apikey: {supabase_anon_key}',
        '-H', f'Authorization: Bearer {supabase_anon_key}',
        '-H', 'Content-Type: application/json',
        '-d', f'{{"p_kwork_order_id": {test_order_id}, "p_title": "{test_title}"}}'
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"📥 Response: {result.stdout}")
            
            # Parse JSON response
            import json
            try:
                response_data = json.loads(result.stdout)
                if isinstance(response_data, list) and len(response_data) > 0:
                    order_id = response_data[0].get('orderid')
                    created = response_data[0].get('created', False)
                    
                    print(f"✅ fh_ingress test successful!")
                    print(f"   Order ID: {order_id}")
                    print(f"   Created: {created}")
                    
                    # Verify the order was actually created
                    if order_id:
                        verify_cmd = [
                            'curl', '-s', '-X', 'GET',
                            f'{supabase_url}/rest/v1/fh_orders?id=eq.{order_id}',
                            '-H', f'apikey: {supabase_anon_key}',
                            '-H', f'Authorization: Bearer {supabase_anon_key}'
                        ]
                        
                        verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=10)
                        if verify_result.returncode == 0:
                            try:
                                orders = json.loads(verify_result.stdout)
                                if orders and len(orders) > 0:
                                    print(f"✅ Verified: Order {order_id} exists in fh_orders table")
                                    print(f"   Source ID: {orders[0].get('source_id')}")
                                    print(f"   Topic: {orders[0].get('topic')}")
                                    print(f"   Status: {orders[0].get('status')}")
                                    return True
                                else:
                                    print(f"⚠️ Warning: Order {order_id} not found in fh_orders table")
                                    return False
                            except json.JSONDecodeError:
                                print(f"❌ Failed to parse verification response")
                                return False
                    return True
                else:
                    print(f"❌ fh_ingress returned empty array or invalid format")
                    return False
            except json.JSONDecodeError:
                print(f"❌ Failed to parse JSON response")
                return False
        else:
            print(f"❌ curl command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing fh_ingress: {e}")
        return False

def main():
    """Main deployment function"""
    print("🚀 Deploying fixed fh_ingress RPC function to Supabase")
    
    # Load environment variables
    env_vars = load_env_vars()
    
    # Read SQL from file
    sql_file = Path("fix_fh_ingress_final.sql")
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        sys.exit(1)
    
    sql_content = sql_file.read_text()
    print(f"📄 Read SQL from {sql_file} ({len(sql_content)} chars)")
    
    # Execute SQL via psql
    success = execute_sql_via_psql(sql_content, env_vars)
    
    if not success:
        print("❌ Deployment failed")
        sys.exit(1)
    
    # Test the function
    test_success = test_fh_ingress_via_curl(env_vars)
    
    if test_success:
        print("\n🎉 SUCCESS: fh_ingress function is working correctly!")
        print("   The RPC function now returns proper data instead of empty array.")
    else:
        print("\n⚠️ WARNING: fh_ingress test failed or returned unexpected results")
        print("   The function may need further debugging.")
        sys.exit(1)
    
    print("\n✅ Deployment completed successfully!")

if __name__ == "__main__":
    main()
