#!/usr/bin/env python3
"""
Deploy fixed fh_ingress RPC function to Supabase
"""

import os
import httpx
import asyncio
import sys
from pathlib import Path

# Load environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Missing Supabase credentials in environment variables")
    print(f"SUPABASE_URL: {'Set' if SUPABASE_URL else 'Missing'}")
    print(f"SUPABASE_SERVICE_ROLE_KEY: {'Set' if SUPABASE_SERVICE_ROLE_KEY else 'Missing'}")
    sys.exit(1)

# Headers for Supabase REST API
headers = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}

async def execute_sql(sql: str) -> dict:
    """Execute SQL via Supabase REST API"""
    url = f"{SUPABASE_URL}/rest/v1/rpc/execute_sql"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                headers=headers,
                json={"query": sql},
                timeout=30.0
            )
            
            if response.status_code == 200:
                print("✅ SQL executed successfully")
                return response.json()
            else:
                print(f"❌ SQL execution failed: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return None
                
        except Exception as e:
            print(f"❌ Error executing SQL: {e}")
            return None

async def test_fh_ingress():
    """Test the fh_ingress function"""
    url = f"{SUPABASE_URL}/rest/v1/rpc/fh_ingress"
    
    test_data = {
        "p_kwork_order_id": 987654321,
        "p_title": "Test after deployment"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                headers=headers,
                json=test_data,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ fh_ingress test successful")
                print(f"Result: {result}")
                return result
            else:
                print(f"❌ fh_ingress test failed: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return None
                
        except Exception as e:
            print(f"❌ Error testing fh_ingress: {e}")
            return None

async def main():
    """Main deployment function"""
    print("🚀 Deploying fixed fh_ingress RPC function to Supabase")
    print(f"Supabase URL: {SUPABASE_URL}")
    
    # Read SQL from file
    sql_file = Path("fix_fh_ingress_final.sql")
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        sys.exit(1)
    
    sql_content = sql_file.read_text()
    print(f"📄 Read SQL from {sql_file} ({len(sql_content)} chars)")
    
    # Execute SQL
    print("⚡ Executing SQL...")
    result = await execute_sql(sql_content)
    
    if result is None:
        print("❌ Deployment failed")
        sys.exit(1)
    
    # Test the function
    print("\n🧪 Testing fh_ingress function...")
    test_result = await test_fh_ingress()
    
    if test_result and len(test_result) > 0:
        print(f"🎉 SUCCESS: fh_ingress function is working!")
        print(f"   Order ID: {test_result[0].get('orderid')}")
        print(f"   Created: {test_result[0].get('created')}")
        
        # Verify the order was actually created
        order_id = test_result[0].get('orderid')
        if order_id:
            # Check if order exists in fh_orders
            check_url = f"{SUPABASE_URL}/rest/v1/fh_orders?id=eq.{order_id}"
            async with httpx.AsyncClient() as client:
                check_response = await client.get(
                    check_url,
                    headers=headers,
                    timeout=10.0
                )
                if check_response.status_code == 200:
                    orders = check_response.json()
                    if orders and len(orders) > 0:
                        print(f"✅ Verified: Order {order_id} exists in fh_orders table")
                        print(f"   Source ID: {orders[0].get('source_id')}")
                        print(f"   Topic: {orders[0].get('topic')}")
                        print(f"   Status: {orders[0].get('status')}")
                    else:
                        print(f"⚠️ Warning: Order {order_id} not found in fh_orders table")
    else:
        print("❌ fh_ingress test failed - function may not be working correctly")
        sys.exit(1)
    
    print("\n✅ Deployment completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
