# Fixes Summary - Contact Scraper API n8n Integration

## Date: 2024-01-20

## Issues Fixed

### 1. ✅ n8n HTTP Node Spinning Endlessly / Timeout Errors

**Problem**: 
- n8n HTTP Request node was spinning indefinitely or timing out after 30 seconds
- API worked perfectly with curl and Python requests
- Error: `AxiosError: timeout of 30000ms exceeded`

**Root Causes Identified**:
1. **Missing Connection: close header** - n8n couldn't detect response completion
2. **Timeout too short** - 30 seconds insufficient for AI processing (takes 10-30s)
3. **Redis network isolation** - App and Redis on different Docker networks
4. **No fast mode option** - Always ran full AI contact page detection

**Solutions Implemented**:

#### A. Response Completion Headers (Primary Fix)
Added middleware to ensure n8n detects response completion:

```python
# In main.py
class ResponseCleanupMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Connection"] = "close"
        return response

app.add_middleware(ResponseCleanupMiddleware)
```

Also updated `/scrap` endpoint to return explicit JSONResponse:
```python
return JSONResponse(
    content=result.model_dump(),
    headers={
        "Content-Type": "application/json; charset=utf-8",
        "Connection": "close",
    },
)
```

#### B. Uvicorn Configuration
Updated Dockerfile CMD with proper timeout settings:
```dockerfile
CMD ["python", "-m", "uvicorn", "main:app", 
     "--host", "0.0.0.0", 
     "--port", "8000", 
     "--proxy-headers", 
     "--forwarded-allow-ips", "*", 
     "--timeout-keep-alive", "5",
     "--limit-concurrency", "100"]
```

#### C. Fast Mode Parameter
Added `skip_contact_page` parameter to bypass AI contact page detection:
- **Fast mode** (`skip_contact_page=true`): 5-15 seconds
- **Full mode** (default): 10-30 seconds

```python
def scrape_website(
    website: str, 
    validate_linkedin: bool = False, 
    skip_contact_page: bool = False  # NEW
) -> Union[ContactInfo, ContactErrorResponse]:
```

---

### 2. ✅ Redis Caching Not Working

**Problem**:
- Repeated requests took same time as first request
- Cache was not being hit
- Logs showed: `Error -3 connecting to redis:6379. Temporary failure in name resolution`

**Root Cause**:
- **Network isolation**: Redis container was on `contact-scraper_default` network
- App container was on `hiscale` network (Traefik network)
- Containers couldn't communicate

**Solution**:
Added Redis to the `hiscale` network in docker-compose.yml:

```yaml
services:
  redis:
    image: redis:8.4.0-alpine
    networks:
      - hiscale  # Added this line
    # ... rest of config

  app:
    # ... config
    networks:
      - hiscale
```

**Verification**:
```bash
# Test Redis connection
docker exec contact-scraper python -c "import redis; r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True); r.ping(); print('Redis connected successfully!')"
# Output: Redis connected successfully!
```

**Cache Performance**:
- First request: 10-30 seconds (full scraping + AI)
- Cached request: <1 second (instant response from Redis)
- Default TTL: 86400 seconds (24 hours)

---

## Deployment Steps

### 1. Stop Current Services
```bash
docker compose down
```

### 2. Create Hiscale Network (if not exists)
```bash
docker network create hiscale
```

### 3. Rebuild Containers
```bash
docker compose build --no-cache
```

### 4. Start Services
```bash
docker compose up -d
```

### 5. Verify Services
```bash
# Check containers are running
docker compose ps

# Check Redis connection
docker exec contact-scraper python -c "import redis; redis.Redis(host='redis', port=6379).ping(); print('✓ Redis OK')"

# Check logs
docker compose logs -f app
```

---

## Updated n8n Configuration

### Recommended Setup (Fast Mode)

```json
{
  "parameters": {
    "method": "GET",
    "url": "https://scraper.hiscale.ai/scrap",
    "sendQuery": true,
    "queryParameters": {
      "parameters": [
        {
          "name": "website",
          "value": "example.com"
        },
        {
          "name": "skip_contact_page",
          "value": "true"
        }
      ]
    },
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "X-API-Key",
          "value": "your-api-key-here"
        }
      ]
    },
    "options": {
      "timeout": 30000
    }
  },
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2
}
```

### Full Mode (More Comprehensive)

```json
{
  "parameters": {
    "url": "https://scraper.hiscale.ai/scrap",
    "queryParameters": {
      "parameters": [
        {
          "name": "website",
          "value": "example.com"
        },
        {
          "name": "skip_contact_page",
          "value": "false"
        }
      ]
    },
    "headerParameters": {
      "parameters": [
        {
          "name": "X-API-Key",
          "value": "your-api-key-here"
        }
      ]
    },
    "options": {
      "timeout": 60000
    }
  }
}
```

---

## Performance Comparison

| Mode | Response Time | AI Calls | Completeness |
|------|---------------|----------|--------------|
| **Fast** (`skip_contact_page=true`) | 5-15 seconds | 1 (validation only) | Homepage only |
| **Full** (default) | 10-30 seconds | 2 (detection + validation) | Homepage + contact page |
| **Cached** (any mode) | <1 second | 0 | Previous result |

---

## Query Parameters Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `website` | string | **required** | Website URL to scrape |
| `validate_linkedin` | boolean | `false` | Use AI to validate LinkedIn URLs |
| `skip_contact_page` | boolean | `false` | Skip AI contact page detection (faster) |

---

## Testing Checklist

- [x] Redis connection working
- [x] Caching functional (second request < 1s)
- [x] n8n request completes without spinning
- [x] Fast mode (`skip_contact_page=true`) responds in 5-15s
- [x] Full mode responds in 10-30s with 60s timeout
- [x] curl/Python requests still work
- [x] `Connection: close` header present in responses
- [x] Both containers on same network
- [x] API accessible via Traefik (scraper.hiscale.ai)

---

## Files Modified

1. **main.py** - Added `ResponseCleanupMiddleware`
2. **app/api/routes/contact.py** - Added `skip_contact_page` parameter, explicit JSONResponse
3. **app/services/contact_service.py** - Implemented skip_contact_page logic
4. **app/core/config.py** - Added timeout configurations
5. **docker-compose.yml** - Fixed Redis network configuration
6. **Dockerfile** - Updated uvicorn command with timeouts
7. **README.md** - Updated n8n integration guide
8. **N8N_INTEGRATION.md** - Created comprehensive n8n guide

---

## Before vs After

### Before
```
n8n Request → API (10-30s) → Spinning endlessly or timeout
Repeat Request → Full scraping again (10-30s)
Redis: ❌ Not connected
n8n: ❌ Hangs/times out
```

### After
```
n8n Request → API (5-15s with fast mode) → ✅ Success
Repeat Request → Redis cache (<1s) → ✅ Instant
Redis: ✅ Connected on hiscale network
n8n: ✅ Works perfectly with proper timeout
```

---

## Recommended Usage Pattern

### For n8n Workflows

1. **High-volume scraping**: Use `skip_contact_page=true` with 30s timeout
2. **Comprehensive data**: Use default mode with 60s timeout
3. **Repeated lookups**: Rely on Redis cache (24h TTL)
4. **Time-sensitive**: Always use `skip_contact_page=true`

### Example n8n Workflow
```
Trigger → HTTP Request (Fast Mode) → Process Results → Save to DB
         ↓
         skip_contact_page=true
         timeout=30000
```

---

## Monitoring

### Check API Health
```bash
curl https://scraper.hiscale.ai/
# Expected: {"status":"healthy","message":"Contact Scraper API is running"}
```

### Monitor Redis Cache
```bash
docker exec contact-scraper-redis redis-cli
> KEYS contact:*
> TTL contact:http://example.com
```

### Watch Logs in Real-time
```bash
docker compose logs -f app | grep -E "\[Cache\]|\[Scraper\]|\[AI\]"
```

---

## Support & Troubleshooting

### Issue: Still timing out
**Solution**: Increase timeout to 90000 (90s) or use `skip_contact_page=true`

### Issue: Cache not working
**Solution**: 
```bash
docker compose logs app | grep Redis
# Should NOT show connection errors
```

### Issue: Empty results
**Solution**: Enable DEBUG mode in .env and check logs

### Issue: API not accessible
**Solution**: Check Traefik routing and DNS resolution

---

## Future Improvements

- [ ] Add response streaming for large CSV jobs
- [ ] Implement rate limiting per API key
- [ ] Add Prometheus metrics for monitoring
- [ ] Support webhook callbacks for n8n
- [ ] Add batch endpoint for n8n (multiple websites in one call)
- [ ] Implement circuit breaker for OpenAI calls

---

**Status**: ✅ All issues resolved and tested  
**Next Steps**: Monitor production logs for any edge cases  
**Contact**: Check README.md for API documentation