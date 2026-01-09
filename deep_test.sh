#!/bin/bash
SECRET="test_secret_key_change_in_production"
URL="http://localhost:8000"

echo "🔥 1. API HEALTH CHECK..."
curl -s "$URL/health" | jq .

echo -e "\n🔥 2. WEBHOOK INJECTION (10 orders)..."
for i in {1..10}; do
   KID="kwork-test-$RANDOM"
   echo "Injecting $KID..."
   curl -s -X POST "$URL/webhook" \
     -H "Content-Type: application/json" \
     -H "X-Token: $SECRET" \
     -d "{\"kworkid\":\"$KID\",\"topic\":\"Write a short poem about Firehorse iteration $i\"}" | jq .
done

echo -e "\n🔥 3. WORKER LOGS (Real-time processing)..."
timeout 10s docker logs -f firehorse-v3-worker-1

echo -e "\n🔥 4. DATABASE VALIDATION..."
docker exec firehorse-v3-postgres-1 psql -U postgres -d firehorse -c "
SELECT count(*) as total_orders FROM orders;
SELECT sourceid, status, createdat FROM orders ORDER BY createdat DESC LIMIT 5;
"

echo -e "\n✅ TEST COMPLETE!"
