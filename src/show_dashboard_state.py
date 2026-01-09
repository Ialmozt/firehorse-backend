"""Show what user would see in dashboard"""
import requests
from datetime import datetime

# Get all orders from Supabase
try:
    response = requests.get(
        "https://yommcknuizxkwpmpvlmp.supabase.co/rest/v1/orders?order=created_at.desc",
        headers={
            "apikey": "sb_publishable_MT63ZGqyQYMOc-IlzQBcYA_W4UVRyKc",
            "Content-Type": "application/json"
        }
    )
    
    if response.status_code == 200:
        orders = response.json()
    else:
        print(f"Error fetching orders: {response.status_code}")
        print(response.text)
        orders = []
except Exception as e:
    print(f"Error: {e}")
    orders = []

# Print dashboard view
print("\n" + "="*100)
print("📊 DASHBOARD - ORDERS FROM KWORK")
print("="*100 + "\n")

print(f"📈 Total Orders: {len(orders)}")
print(f"📅 Last Updated: {datetime.now().isoformat()}\n")

# Show recent Kwork orders
print("="*100)
print("🎯 RECENT KWORK ORDERS (Last 10)")
print("="*100 + "\n")

# Filter today's test orders (kwork_order_id starting with 1767965)
recent_orders = [o for o in orders if str(o['kwork_order_id']).startswith('1767965')]

if recent_orders:
    print("✅ TODAY'S TEST ORDERS (from test script):")
    for i, order in enumerate(recent_orders[:10], 1):
        created_at = order['created_at'].replace('T', ' ')[:19]
        print(f"  {i}. 📋 ID: {order['id']} | Kwork: {order['kwork_order_id']}")
        print(f"     Title: {order['title'][:60]}...")
        print(f"     Status: {order['status']} | Created: {created_at}")
        print()
else:
    print("No recent Kwork orders found")

# Show summary
print("="*100)
print("📊 SUMMARY")
print("="*100 + "\n")

status_counts = {}
for order in orders:
    status = order['status']
    status_counts[status] = status_counts.get(status, 0) + 1

print("Status Distribution:")
for status, count in status_counts.items():
    print(f"  {status}: {count} orders")

# Count today's orders
today = datetime.now().date().isoformat()
today_orders = [o for o in orders if o['created_at'].startswith(today)]
print(f"\n📅 Today's Orders ({today}): {len(today_orders)}")

# Show API health
print("\n" + "="*100)
print("🏥 API HEALTH CHECK")
print("="*100 + "\n")

try:
    health_response = requests.get("http://localhost:8000/health", timeout=5)
    if health_response.status_code == 200:
        health_data = health_response.json()
        print(f"✅ API Status: {health_data.get('status', 'unknown')}")
        print(f"✅ Database: {health_data.get('database', 'unknown')}")
        print(f"✅ Version: {health_data.get('version', 'unknown')}")
    else:
        print(f"⚠️ API Health Check Failed: {health_response.status_code}")
except Exception as e:
    print(f"⚠️ API Health Check Error: {e}")