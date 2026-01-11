import re

with open('src/main.py', 'r') as f:
    content = f.read()

# Replace check_db_connection function to use ANON key for health check
new_check_db_connection = '''async def check_db_connection():
    """Check if Supabase is accessible"""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return False

    try:
        # Use ANON key for health check (it works)
        health_headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        if SUPABASE_ANON_KEY and SUPABASE_ANON_KEY.startswith('ey'):
            health_headers["Authorization"] = f"Bearer {SUPABASE_ANON_KEY}"
        
        async with get_http_client() as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/orders",
                headers=health_headers,
                params={"select": "id", "limit": 1}
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(
            "database_connection_failed",
            extra={
                "error": str(e),
                "supabase_url": SUPABASE_URL[:50] + "..." if SUPABASE_URL and len(SUPABASE_URL) > 50 else SUPABASE_URL
            }
        )
        return False'''

# Find and replace the function
pattern = r'async def check_db_connection\(\):.*?return False'
content = re.sub(pattern, new_check_db_connection, content, flags=re.DOTALL)

with open('src/main.py', 'w') as f:
    f.write(content)

print("Fixed check_db_connection function")
