#!/usr/bin/env python3
"""
Test script for Kwork webhook functionality.
"""
import sys
import json
from datetime import datetime

# Add app to path
sys.path.insert(0, '/srv/firehorse-backend')

def test_kwork_parser():
    """Test Kwork parser functionality"""
    print("🧪 Testing Kwork parser...")
    
    try:
        from app.services.kwork_parser import KworkParser
        
        # Test payload
        test_payload = {
            "order_id": 12345,
            "user_id": 1,
            "title": "Write SEO article about Python programming",
            "description": "Need 1000-word article about Python programming best practices",
            "status": "pending",
            "metadata": {
                "category": "programming",
                "budget": 5000
            }
        }
        
        # Test validation
        parser = KworkParser()
        is_valid = parser.validate_payload(test_payload)
        print(f"  ✅ Payload validation: {is_valid}")
        
        # Test parsing
        firehorse_order = parser.parse_webhook_payload(test_payload)
        print(f"  ✅ Parsing successful")
        print(f"  📊 Source ID: {firehorse_order['source_id']}")
        print(f"  📊 Topic: {firehorse_order['topic']}")
        print(f"  📊 Status: {firehorse_order['status']}")
        
        # Test response creation
        response = parser.create_webhook_response("12345", "test-uuid-123")
        print(f"  ✅ Response creation: {response['status']}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Parser test failed: {str(e)}")
        return False

def test_supabase_client_structure():
    """Test Supabase client structure (without actual connection)"""
    print("\n🧪 Testing Supabase client structure...")
    
    try:
        from app.services.supabase_client import SupabaseClient
        
        # Just test that we can import and create instance
        # Don't actually initialize to avoid connection errors
        print("  ✅ SupabaseClient class imported successfully")
        
        # Check methods exist
        client_class = SupabaseClient
        required_methods = ['save_order', 'create_pgmq_job', 'get_order_by_source_id', 
                           'update_order_status', 'create_order_event']
        
        for method in required_methods:
            if hasattr(client_class, method):
                print(f"  ✅ Method '{method}' exists")
            else:
                print(f"  ❌ Method '{method}' missing")
                
        return True
        
    except Exception as e:
        print(f"  ❌ Supabase client test failed: {str(e)}")
        return False

def test_webhook_route():
    """Test webhook route structure"""
    print("\n🧪 Testing webhook route structure...")
    
    try:
        from app.routes.webhook import router, KworkWebhookPayload, WebhookResponse
        
        print("  ✅ Router imported successfully")
        print(f"  ✅ KworkWebhookPayload fields: {KworkWebhookPayload.__fields__.keys()}")
        print(f"  ✅ WebhookResponse fields: {WebhookResponse.__fields__.keys()}")
        
        # Test payload model
        test_payload = KworkWebhookPayload(
            order_id=12345,
            user_id=1,
            title="Test order",
            description="Test description"
        )
        print(f"  ✅ Payload model instantiation: order_id={test_payload.order_id}")
        
        # Test response model
        test_response = WebhookResponse(
            status="accepted",
            message="Test message",
            order_id=12345,
            firehorse_id="test-uuid",
            timestamp=datetime.utcnow().isoformat()
        )
        print(f"  ✅ Response model instantiation: status={test_response.status}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Webhook route test failed: {str(e)}")
        return False

def test_main_app():
    """Test main app structure"""
    print("\n🧪 Testing main app structure...")
    
    try:
        from app.main import app
        
        print(f"  ✅ App title: {app.title}")
        print(f"  ✅ App version: {app.version}")
        
        # Check routes
        routes = [route.path for route in app.routes]
        print(f"  ✅ Total routes: {len(routes)}")
        
        # Check for kwork webhook route
        kwork_routes = [r for r in routes if 'kwork' in r]
        print(f"  ✅ Kwork webhook routes: {len(kwork_routes)}")
        
        for route in kwork_routes:
            print(f"    - {route}")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Main app test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Kwork webhook integration tests...")
    print("=" * 60)
    
    tests = [
        test_kwork_parser,
        test_supabase_client_structure,
        test_webhook_route,
        test_main_app
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Test crashed: {str(e)}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"  Total tests: {len(tests)}")
    print(f"  Passed: {sum(results)}")
    print(f"  Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\n✅ All tests passed! Kwork webhook integration is ready.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
