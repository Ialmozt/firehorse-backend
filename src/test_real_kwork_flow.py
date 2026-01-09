"""
Simulate real Kwork webhook and verify complete flow:
webhook → validation → logging → database insert
"""
import asyncio
import httpx
import json
from datetime import datetime

# Real test tasks that would come from Kwork
TEST_TASKS = [
    {
        "id": f"kwork_{datetime.now().timestamp()}",
        "title": "Разработать мобильное приложение iOS на Swift",
        "price": 5000,
        "description": "Нужно разработать iOS приложение для управления проектами",
        "buyer_id": "kwork_buyer_001"
    },
    {
        "id": f"kwork_{datetime.now().timestamp() + 1}",
        "title": "Дизайн логотипа для стартапа",
        "price": 500,
        "description": "Креативный логотип для IT компании",
        "buyer_id": "kwork_buyer_002"
    },
    {
        "id": f"kwork_{datetime.now().timestamp() + 2}",
        "title": "Написать статью о машинном обучении",
        "price": 2000,
        "description": "Статья 5000 слов про AI/ML",
        "buyer_id": "kwork_buyer_003"
    },
]

async def send_webhook(task: dict) -> dict:
    """Send task as webhook, return response"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/webhook",
                json=task,
                timeout=10
            )
            
            return {
                "status_code": response.status_code,
                "request_id": response.headers.get("X-Request-ID"),
                "response": response.json(),
                "task_id": task["id"],
                "task_title": task["title"],
                "success": response.status_code == 200
            }
        except Exception as e:
            return {
                "status_code": 0,
                "error": str(e),
                "task_id": task["id"],
                "success": False
            }

async def main():
    """Send all test tasks and show results"""
    print("\n" + "="*80)
    print("🎬 REAL KWORK TASKS → DATABASE FLOW")
    print("="*80 + "\n")
    
    print("📤 Sending 3 real Kwork tasks to API...\n")
    
    results = []
    for i, task in enumerate(TEST_TASKS, 1):
        print(f"Task {i}: {task['title'][:50]}...")
        result = await send_webhook(task)
        results.append(result)
        print(f"  Status: {result['status_code']}")
        print(f"  Request ID: {result['request_id']}")
        print(f"  Success: {'✅' if result['success'] else '❌'}\n")
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in results if r['success'])
    print(f"\nTotal tasks sent: {len(results)}")
    print(f"Successfully inserted: {successful}")
    print(f"Failed: {len(results) - successful}")
    
    print("\n" + "="*80)
    print("📋 DETAILED RESULTS")
    print("="*80 + "\n")
    
    for result in results:
        print(f"Task ID: {result['task_id']}")
        print(f"Status: {result['status_code']}")
        print(f"Request ID: {result.get('request_id', 'N/A')}")
        if result['success']:
            print(f"Response: {result['response']}")
        else:
            print(f"Error: {result.get('error', 'Unknown')}")
        print()

if __name__ == "__main__":
    asyncio.run(main())