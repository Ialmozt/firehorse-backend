import asyncio
import logging
import os
import sys
sys.path.insert(0, 'src')

# Temporarily break the Supabase URL to simulate network failure
original_url = os.environ.get('SUPABASE_URL')
os.environ['SUPABASE_URL'] = 'http://invalid-url:9999'

from src.main import insert_order

logging.basicConfig(level=logging.INFO)

async def test():
    data = {"id": "999", "title": "Network Test", "price": 100}
    try:
        result = await insert_order(data)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Expected error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
    
# Restore original URL
if original_url:
    os.environ['SUPABASE_URL'] = original_url