# n8n Integration Guide for Contact Scraper API

## Problem: n8n HTTP Node Spinning Endlessly

If you're experiencing issues where the n8n HTTP Request node spins indefinitely when calling the `/scrap` endpoint (even though curl and Python work fine), this guide will help you resolve it.

## Root Cause

The issue occurs because n8n's HTTP client doesn't properly detect when the response is complete in certain scenarios, particularly when:

1. The API is behind a reverse proxy (Traefik)
2. HTTP keep-alive connections are used
3. The response doesn't explicitly signal connection closure

## Solutions Implemented

### 1. Connection: Close Header (Primary Fix)

We added a middleware that explicitly sets `Connection: close` header on all responses:

```python
# In main.py
class ResponseCleanupMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Connection"] = "close"
        return response
```

This ensures n8n knows when the response is complete and can close the connection.

### 2. Uvicorn Timeout Settings

Updated Docker CMD to include keep-alive timeout:

```dockerfile
CMD ["python", "-m", "uvicorn", "main:app", 
     "--host", "0.0.0.0", 
     "--port", "8000", 
     "--proxy-headers", 
     "--forwarded-allow-ips", "*", 
     "--timeout-keep-alive", "5",
     "--limit-concurrency", "100"]
```

### 3. Explicit JSONResponse

Changed the `/scrap` endpoint to return explicit `JSONResponse` with proper headers:

```python
return JSONResponse(
    content=result.model_dump(),
    headers={
        "Content-Type": "application/json; charset=utf-8",
        "Connection": "close",
    },
)
```

## Recommended n8n Configuration

Use the following configuration in your n8n HTTP Request node:

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
          "name": "validate_linkedin",
          "value": "false"
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
      "timeout": 60000
    }
  },
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2
}
```

### Key Settings:

- **`timeout: 60000`** - 60 seconds (scraping + AI takes 10-30 seconds typically)
- **HTTP Method**: GET
- **Required Header**: `X-API-Key` with your API key
- **Query Parameters**: `website` (required), `validate_linkedin` (optional, default: false)

## Response Format

### Success Response:
```json
{
  "website": "http://example.com",
  "emails": ["contact@example.com", "info@example.com"],
  "phones": ["+1-555-0100"],
  "linkedin_urls": {
    "company": ["https://linkedin.com/company/example"],
    "personal": ["https://linkedin.com/in/john-doe"]
  },
  "status": "success"
}
```

### Error Response:
```json
{
  "website": "http://example.com",
  "error": "Failed to fetch homepage",
  "status": "error"
}
```

### No Contacts Found:
```json
{
  "website": "http://example.com",
  "emails": [],
  "phones": [],
  "linkedin_urls": {
    "company": [],
    "personal": []
  },
  "status": "no_contacts_found"
}
```

## Testing the Fix

### 1. Test with curl (should work):
```bash
curl -X GET "https://scraper.hiscale.ai/scrap?website=example.com" \
  -H "X-API-Key: your-api-key-here" \
  -v
```

### 2. Test with n8n:
- Create a new workflow
- Add HTTP Request node
- Configure as shown above
- Execute the node
- Should complete successfully without spinning

### 3. Check response headers:
Look for these headers in the response:
- `Connection: close`
- `Content-Type: application/json; charset=utf-8`

## Performance Expectations

| Scenario | Expected Time |
|----------|---------------|
| Cached result | < 1 second |
| Simple website (no contact page) | 5-15 seconds |
| Complex website (with contact page) | 15-30 seconds |
| Slow website or AI delays | 30-60 seconds |

## Troubleshooting

### Issue: Still spinning after fixes
**Solution**: 
1. Ensure you've rebuilt and restarted the Docker containers:
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```
2. Clear n8n cache: Settings → Reset
3. Increase timeout to 90 seconds if dealing with very slow websites

### Issue: Timeout after 60 seconds
**Solution**: 
- This is expected for very slow websites
- Increase timeout in n8n or optimize by disabling LinkedIn validation
- Check if the website is blocking scraping (some sites have rate limits)

### Issue: Empty results but status is "success"
**Solution**:
- Website might have no public contact info
- Try enabling `validate_linkedin=true` to get more aggressive scraping
- Check logs: `docker compose logs -f app`

### Issue: "Failed to fetch homepage" error
**Solution**:
- Website might be down or blocking requests
- Try accessing the website manually in browser
- Some websites block non-browser user agents

## Advanced: Debugging with Logs

Enable debug mode to see detailed logs:

1. Set in `.env`:
```env
DEBUG=True
```

2. Restart containers:
```bash
docker compose restart app
```

3. Watch logs in real-time:
```bash
docker compose logs -f app
```

You'll see detailed output like:
```
[Cache] Checking cache for http://example.com
[Scraper] Fetching homepage: http://example.com
[Scraper] Found 2 email(s), 1 phone(s)
[AI] Sending 15 link(s) to find contact page
[AI] Contact page found: http://example.com/contact
[AI] Validation complete: 2 valid email(s)
[Cache] Saving to cache with TTL: 86400s
```

## API Rate Limits

To prevent overload, consider:
- Using Redis cache (24-hour TTL by default)
- Limiting concurrent n8n workflow executions
- Monitoring OpenAI API usage (2 calls per scrape)

## Support

If issues persist after applying these fixes:
1. Check Docker logs: `docker compose logs app`
2. Verify API is accessible: `curl https://scraper.hiscale.ai/`
3. Test with Postman/Insomnia to isolate n8n-specific issues
4. Check Traefik routing if using custom domain

---

**Last Updated**: 2024-01-20  
**API Version**: 1.0.0  
**Tested with n8n**: v1.0+