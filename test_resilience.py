import asyncio
import logging
import sys
sys.path.insert(0, 'src')

from core.resilience import retry_with_backoff, supabase_retry_config

logging.basicConfig(level=logging.INFO)

class MockError(Exception):
    pass

counter = 0

@retry_with_backoff(supabase_retry_config)
async def failing_function():
    global counter
    counter += 1
    if counter < 3:
        raise ConnectionError("Simulated connection error")
    return "success"

async def test():
    try:
        result = await failing_function()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed with: {e}")

if __name__ == "__main__":
    asyncio.run(test())