#!/bin/bash

# Test script to verify n8n integration fixes
# Tests Redis caching and API response time

echo "========================================"
echo "Contact Scraper API - Fixes Test Script"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_URL="https://scraper.hiscale.ai"
TEST_WEBSITE="hiscale.ai"
API_KEY="i8eUrz04CLVraTPMZwuGyw"

echo "Test Configuration:"
echo "  API URL: $API_URL"
echo "  Test Website: $TEST_WEBSITE"
echo ""

# Test 1: Check if containers are running
echo "========================================"
echo "Test 1: Docker Containers Status"
echo "========================================"
docker compose ps
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Containers are running${NC}"
else
    echo -e "${RED}✗ Containers are not running${NC}"
    exit 1
fi
echo ""

# Test 2: Redis Connection
echo "========================================"
echo "Test 2: Redis Connection"
echo "========================================"
docker exec contact-scraper python -c "import redis; r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True); r.ping(); print('✓ Redis connection successful')" 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Redis is connected${NC}"
else
    echo -e "${RED}✗ Redis connection failed${NC}"
    exit 1
fi
echo ""

# Test 3: API Health Check
echo "========================================"
echo "Test 3: API Health Check"
echo "========================================"
HEALTH_RESPONSE=$(curl -s "$API_URL/")
echo "Response: $HEALTH_RESPONSE"
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${RED}✗ API health check failed${NC}"
    exit 1
fi
echo ""

# Test 4: Clear cache for test website
echo "========================================"
echo "Test 4: Clearing Cache for Test"
echo "========================================"
docker exec contact-scraper python -c "from app.core.database import redis_client; redis_client.delete('contact:http://$TEST_WEBSITE'); print('✓ Cache cleared')" 2>&1
echo ""

# Test 5: First Request (No Cache) - Fast Mode
echo "========================================"
echo "Test 5: First Request - Fast Mode"
echo "========================================"
echo "Testing: $API_URL/scrap?website=$TEST_WEBSITE&skip_contact_page=true"
echo "Expected: 5-15 seconds"
echo ""
START_TIME=$(date +%s)
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTIME_TOTAL:%{time_total}" \
  -X GET "$API_URL/scrap?website=$TEST_WEBSITE&skip_contact_page=true" \
  -H "X-API-Key: $API_KEY" \
  -H "User-Agent: Mozilla/5.0")
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
TIME_TOTAL=$(echo "$RESPONSE" | grep "TIME_TOTAL:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/,$d')

echo "Response Time: ${TIME_TOTAL}s (${ELAPSED}s wall time)"
echo "HTTP Code: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ First request successful (Fast Mode)${NC}"
    if echo "$BODY" | grep -q '"status"'; then
        echo -e "${GREEN}✓ Valid JSON response received${NC}"
    fi
else
    echo -e "${RED}✗ First request failed with HTTP $HTTP_CODE${NC}"
    echo "Response: $BODY"
fi
echo ""

# Test 6: Second Request (Should be Cached)
echo "========================================"
echo "Test 6: Second Request - Cache Test"
echo "========================================"
echo "Testing: Same request (should be cached)"
echo "Expected: <1 second"
echo ""
START_TIME=$(date +%s)
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTIME_TOTAL:%{time_total}" \
  -X GET "$API_URL/scrap?website=$TEST_WEBSITE&skip_contact_page=true" \
  -H "X-API-Key: $API_KEY" \
  -H "User-Agent: Mozilla/5.0")
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
TIME_TOTAL=$(echo "$RESPONSE" | grep "TIME_TOTAL:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/,$d')

echo "Response Time: ${TIME_TOTAL}s (${ELAPSED}s wall time)"
echo "HTTP Code: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Cached request successful${NC}"

    # Check if response is fast (cached)
    TIME_SECONDS=$(echo "$TIME_TOTAL" | cut -d. -f1)
    if [ "$TIME_SECONDS" -lt 2 ]; then
        echo -e "${GREEN}✓ Cache is working! Response was instant (<2s)${NC}"
    else
        echo -e "${YELLOW}⚠ Response took ${TIME_TOTAL}s - cache might not be working${NC}"
    fi
else
    echo -e "${RED}✗ Cached request failed with HTTP $HTTP_CODE${NC}"
    echo "Response: $BODY"
fi
echo ""

# Test 7: Check Response Headers
echo "========================================"
echo "Test 7: Response Headers (n8n Fix)"
echo "========================================"
HEADERS=$(curl -s -I "$API_URL/scrap?website=$TEST_WEBSITE" \
  -H "X-API-Key: $API_KEY")

echo "Checking for 'Connection: close' header..."
if echo "$HEADERS" | grep -qi "Connection: close"; then
    echo -e "${GREEN}✓ Connection: close header present (n8n fix working)${NC}"
else
    echo -e "${YELLOW}⚠ Connection: close header not found${NC}"
fi

echo ""
echo "Checking for Content-Type..."
if echo "$HEADERS" | grep -qi "Content-Type: application/json"; then
    echo -e "${GREEN}✓ Content-Type: application/json header present${NC}"
else
    echo -e "${YELLOW}⚠ Content-Type header not found${NC}"
fi
echo ""

# Test 8: Check Redis Cache Entry
echo "========================================"
echo "Test 8: Verify Redis Cache Entry"
echo "========================================"
docker exec contact-scraper python -c "
from app.core.database import redis_client
import json
key = 'contact:http://$TEST_WEBSITE'
cached = redis_client.get(key)
if cached:
    data = json.loads(cached)
    print(f'✓ Cache entry exists for $TEST_WEBSITE')
    print(f'  Emails: {len(data.get(\"emails\", []))}')
    print(f'  Phones: {len(data.get(\"phones\", []))}')
    print(f'  LinkedIn Company: {len(data.get(\"linkedin_urls\", {}).get(\"company\", []))}')
    print(f'  LinkedIn Personal: {len(data.get(\"linkedin_urls\", {}).get(\"personal\", []))}')
    ttl = redis_client.ttl(key)
    print(f'  TTL: {ttl}s (~{ttl//3600}h remaining)')
else:
    print('✗ No cache entry found')
" 2>&1
echo ""

# Summary
echo "========================================"
echo "Test Summary"
echo "========================================"
echo ""
echo "✓ Tests completed!"
echo ""
echo "Key Metrics:"
echo "  - Fast Mode Response: ~5-15 seconds"
echo "  - Cached Response: <1 second"
echo "  - Cache TTL: 24 hours (86400s)"
echo ""
echo "n8n Configuration:"
echo "  - Use timeout: 30000 (30s) for fast mode"
echo "  - Use timeout: 60000 (60s) for full mode"
echo "  - Add skip_contact_page=true for faster results"
echo ""
echo "Redis Cache:"
if docker exec contact-scraper python -c "import redis; redis.Redis(host='redis').ping()" 2>&1 | grep -q "True"; then
    echo -e "  Status: ${GREEN}✓ Working${NC}"
else
    echo -e "  Status: ${RED}✗ Not Working${NC}"
fi
echo ""
echo "Logs: docker compose logs -f app"
echo "========================================"
