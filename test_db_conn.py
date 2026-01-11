import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

async def test_connection(headers, key_name):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/orders",
                headers=headers,
                params={"select": "id", "limit": 1}
            )
            print(f"{key_name}: Status {response.status_code}")
            if response.status_code == 200:
                print(f"  Success: {response.text[:50]}")
                return True
            else:
                print(f"  Error: {response.text[:100]}")
                return False
    except Exception as e:
        print(f"{key_name}: Exception: {str(e)[:100]}")
        return False

async def main():
    print("Testing Supabase REST API connection...")
    
    # Test with ANON key
    headers_anon = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    if SUPABASE_ANON_KEY and SUPABASE_ANON_KEY.startswith('ey'):
        headers_anon["Authorization"] = f"Bearer {SUPABASE_ANON_KEY}"
    
    # Test with SERVICE_ROLE key  
    headers_service = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    if SUPABASE_SERVICE_ROLE_KEY and SUPABASE_SERVICE_ROLE_KEY.startswith('ey'):
        headers_service["Authorization"] = f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"
    
    print(f"\nSUPABASE_URL: {SUPABASE_URL}")
    print(f"ANON Key starts with: {SUPABASE_ANON_KEY[:20] if SUPABASE_ANON_KEY else 'None'}")
    print(f"SERVICE_ROLE Key starts with: {SUPABASE_SERVICE_ROLE_KEY[:20] if SUPABASE_SERVICE_ROLE_KEY else 'None'}")
    
    result_anon = await test_connection(headers_anon, "ANON_KEY")
    result_service = await test_connection(headers_service, "SERVICE_ROLE_KEY")
    
    print(f"\nResults: ANON_KEY={'✓' if result_anon else '✗'}, SERVICE_ROLE_KEY={'✓' if result_service else '✗'}")

if __name__ == "__main__":
    asyncio.run(main())
