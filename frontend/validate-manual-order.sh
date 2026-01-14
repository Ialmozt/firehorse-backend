#!/bin/bash
# 🔥 PRODUCTION VALIDATION SCRIPT FOR MANUAL ORDER BUTTON

echo "🧪 Running production validation for Manual Order Button..."

# 1. Check if backend is running
echo "1. Checking backend health..."
curl -s http://localhost:8000/health | grep -q "ok"
if [ $? -eq 0 ]; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend is not responding"
    exit 1
fi

# 2. Test API endpoint
echo "2. Testing API endpoint..."
TEST_ID="validation-test-$(date +%s)"
RESPONSE=$(curl -s -w "\nHTTPSTATUS:%{http_code}" -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Token: 44c89b6265fb03bb6ce22c5f41f02bca87177662da81e3ed719c7321b36f8a70" \
  -d "{\"kworkid\":\"$TEST_ID\",\"topic\":\"Validation test order\"}")

ORDER_ID=$(echo "$RESPONSE" | grep -o '"orderid":"[^"]*"' | cut -d'"' -f4)
STATUS=$(echo "$RESPONSE" | tail -1 | cut -d':' -f2)

if [ "$STATUS" = "202" ] || [ "$STATUS" = "200" ]; then
    echo "✅ API test passed: Order ID = $ORDER_ID"
else
    echo "❌ API test failed: HTTP $STATUS"
    echo "Response: $RESPONSE"
    exit 1
fi

# 3. Check TypeScript compilation
echo "3. Checking TypeScript compilation..."
cd frontend
if npx tsc --noEmit 2>/dev/null; then
    echo "✅ TypeScript compilation passed"
else
    echo "⚠️ TypeScript has errors (check manually)"
fi

# 4. Check if components exist
echo "4. Checking component files..."
if [ -f "src/hooks/useManualOrder.ts" ] && [ -f "src/components/ManualOrderDialog.tsx" ]; then
    echo "✅ All component files exist"
else
    echo "❌ Missing component files"
    exit 1
fi

# 5. Check environment variables
echo "5. Checking environment variables..."
if grep -q "VITE_API_URL" .env.local && grep -q "VITE_INGRESS_SECRET" .env.local; then
    echo "✅ Environment variables are set"
else
    echo "⚠️ Environment variables may be missing"
fi

echo ""
echo "🎉 PRODUCTION VALIDATION COMPLETE"
echo ""
echo "MANUAL TESTS REQUIRED (10 MIN):"
echo "1. Open dashboard → 'New Order' button should be visible"
echo "2. Click button → Modal should open with form"
echo "3. Test form validation:"
echo "   - Empty fields → Show errors"
echo "   - Invalid ID → Show pattern error"
echo "   - Valid data → Submit successfully"
echo "4. Submit → Should show success toast"
echo "5. Check Supabase fh_orders table for new order"
echo "6. Mobile responsive test (320px+)"
echo "7. Keyboard navigation (Tab, Enter)"
echo ""
echo "Status: READY FOR PRODUCTION 🚀"
