#!/bin/bash
# Test script for Kwork webhook using curl

echo "🚀 Testing Kwork webhook with curl..."
echo "=========================================="

# Set API URL (assuming FastAPI is running locally)
API_URL="http://localhost:8000/api/webhook/kwork"

# Test 1: Check if endpoint exists
echo "1. Testing endpoint availability..."
curl -s -X GET "http://localhost:8000/api/webhook/kwork/test" | jq . 2>/dev/null || echo "  ⚠️  Test endpoint not available (might need DEBUG mode)"

# Test 2: Send test webhook payload
echo -e "\n2. Sending test webhook payload..."
TEST_PAYLOAD='{
  "order_id": 99999,
  "user_id": 42,
  "title": "Test webhook order",
  "description": "This is a test order from curl",
  "status": "pending",
  "metadata": {
    "test": true,
    "source": "curl_test"
  }
}'

echo "Payload:"
echo "$TEST_PAYLOAD" | jq .

echo -e "\nSending to $API_URL ..."
curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "X-Kwork-Signature: test-signature-ignore-in-debug" \
  -d "$TEST_PAYLOAD" \
  -w "\nStatus: %{http_code}\n" \
  --max-time 10

# Test 3: Check API info endpoint
echo -e "\n3. Checking API info..."
curl -s "http://localhost:8000/api/info" | jq . 2>/dev/null || echo "  ⚠️  Could not fetch API info"

echo -e "\n=========================================="
echo "✅ Test script completed!"
echo ""
echo "To run the webhook manually:"
echo "curl -X POST http://localhost:8000/api/webhook/kwork \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"order_id\": 12345, \"user_id\": 1, \"title\": \"Test\", \"description\": \"Test\"}'"
echo ""
echo "Note: Make sure FastAPI is running first:"
echo "  cd /srv/firehorse-backend && uvicorn app.main:app --reload"
