# LinkedIn-Only Scraping Guide

Fast LinkedIn URL extraction without AI validation or contact page detection.

## Overview

The LinkedIn-only endpoints provide the **fastest way to extract LinkedIn URLs** from websites:
- **2-5 seconds per request** (vs 10-30 seconds for full contact scraping)
- No AI processing required
- Homepage scraping only
- Perfect for high-volume workflows and n8n integrations

## Endpoints

### 1. Single Website LinkedIn Scraping

**Endpoint:** `GET /scrap-linkedin`

Extract LinkedIn URLs from a single website's homepage.

#### Request

```bash
curl -X GET "https://scraper.hiscale.ai/scrap-linkedin?website=example.com" \
  -H "X-API-Key: your-api-key-here"
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `website` | string | Yes | Website URL to scrape |

#### Response (Success)

```json
{
  "website": "http://example.com",
  "company_linkedin": [
    "https://linkedin.com/company/example-corp"
  ],
  "personal_linkedin": [
    "https://linkedin.com/in/john-doe",
    "https://linkedin.com/in/jane-smith"
  ],
  "status": "success"
}
```

#### Response (No LinkedIn URLs Found)

```json
{
  "website": "http://example.com",
  "company_linkedin": [],
  "personal_linkedin": [],
  "status": "no_contacts_found"
}
```

#### Response (Error)

```json
{
  "website": "http://example.com",
  "error": "Failed to fetch homepage",
  "status": "error"
}
```

### 2. Batch CSV LinkedIn Scraping

**Endpoint:** `POST /csv/upload-linkedin-csv`

Process multiple websites from a CSV file.

#### Request

```bash
curl -X POST "https://scraper.hiscale.ai/csv/upload-linkedin-csv" \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@websites.csv" \
  -F "website_column=website"
```

#### Form Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | file | Yes | - | CSV file with website URLs |
| `website_column` | string | No | `website` | Column name containing URLs |

#### Input CSV Format

```csv
website,company_name
example.com,Example Corp
acme.org,Acme Inc
techstartup.io,Tech Startup
```

#### Response

```json
{
  "job_id": "123",
  "message": "CSV uploaded successfully. LinkedIn-only processing queued.",
  "total_rows": 3,
  "status": "queued"
}
```

#### Output CSV Format

The processed CSV includes these additional columns:

| Column | Description |
|--------|-------------|
| `company_linkedin` | Comma-separated list of company LinkedIn URLs |
| `personal_linkedin` | Comma-separated list of personal LinkedIn URLs |
| `scrape_status` | success, error, no_contacts_found, or skipped |
| `error` | Error message (only in DEBUG mode) |

**Example Output CSV:**

```csv
website,company_name,company_linkedin,personal_linkedin,scrape_status
example.com,Example Corp,https://linkedin.com/company/example-corp,"https://linkedin.com/in/john-doe, https://linkedin.com/in/jane-smith",success
acme.org,Acme Inc,https://linkedin.com/company/acme,https://linkedin.com/in/acme-ceo,success
techstartup.io,Tech Startup,,,no_contacts_found
```

## n8n Integration

### Single Website Scraping in n8n

**HTTP Request Node Configuration:**

```json
{
  "parameters": {
    "method": "GET",
    "url": "https://scraper.hiscale.ai/scrap-linkedin",
    "sendQuery": true,
    "queryParameters": {
      "parameters": [
        {
          "name": "website",
          "value": "={{ $json.website }}"
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
      "timeout": 15000
    }
  },
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.2
}
```

**Key Settings:**
- **Timeout:** 15000ms (15 seconds) - sufficient for LinkedIn-only scraping
- **Method:** GET
- **Response:** JSON with `linkedin_urls` object

### CSV Upload in n8n

**HTTP Request Node Configuration:**

```json
{
  "parameters": {
    "method": "POST",
    "url": "https://scraper.hiscale.ai/csv/upload-linkedin-csv",
    "sendBody": true,
    "bodyParameters": {
      "parameters": []
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
  }
}
```

### Example n8n Workflow

```
1. Read CSV/Spreadsheet Node
   ↓
2. Split In Batches (10 items)
   ↓
3. HTTP Request: /scrap-linkedin
   - Timeout: 15000
   - Extract: website from input
   ↓
4. Set Node: Format LinkedIn URLs
   ↓
5. Google Sheets: Update Results
```

## Performance Metrics

### Single Website Scraping

| Metric | Value |
|--------|-------|
| Average response time | 2-5 seconds |
| Cached response time | <1 second |
| Cache TTL | 24 hours (86400 seconds) |
| Max LinkedIn URLs per response | Unlimited (all found on homepage) |
| LinkedIn URLs in CSV | All URLs (comma-separated if multiple) |

### Batch CSV Processing

| Metric | Value |
|--------|-------|
| Processing speed | 2-5 seconds per row |
| Concurrent jobs | 2 (configurable via MAX_WORKERS) |
| Concurrent scraping per job | 10 websites (configurable via CSV_CONCURRENT_WORKERS) |
| Job tracking | Real-time via `/csv/job/{job_id}` |

### Comparison with Full Contact Scraping

| Feature | LinkedIn-Only | Full Contact Scraping |
|---------|---------------|----------------------|
| Response time | 2-5 seconds | 10-30 seconds |
| AI processing | ❌ None | ✅ 2 AI calls |
| Contact page detection | ❌ No | ✅ Yes |
| Emails extracted | ❌ No | ✅ Yes |
| Phones extracted | ❌ No | ✅ Yes |
| LinkedIn URLs | ✅ Yes | ✅ Yes |
| Cache key | `linkedin:*` | `contact:*` |
| Best for n8n | ✅ Yes | ⚠️ Requires 60s timeout |

## Caching

LinkedIn-only requests are cached using the same mechanism as full contact scraping:

- **Cache Key:** `linkedin:http://example.com` (separate from full contact scraping)
- **Cache TTL:** 24 hours (86400 seconds)
- **Cache Storage:** Redis
- **Cache Behavior:** 
  - First request: 2-5 seconds (scraping)
  - Subsequent requests: <1 second (from cache)
  - Cache is **separate** from `/scrap` endpoint cache

**Note:** LinkedIn-only and full contact scraping use different cache keys to prevent conflicts:
- `/scrap-linkedin` → `linkedin:{url}`
- `/scrap` → `contact:{url}`

This means you can call `/scrap-linkedin` first, then `/scrap` later, and both will work correctly without cache interference.

## Use Cases

### 1. Lead Generation

Extract LinkedIn company pages for B2B outreach:

```bash
# Get company LinkedIn
curl "https://scraper.hiscale.ai/scrap-linkedin?website=techcorp.com" \
  -H "X-API-Key: your-api-key"

# Response
{
  "company_linkedin": ["https://linkedin.com/company/techcorp"],
  "personal_linkedin": []
}
```

### 2. People Finder

Find employee LinkedIn profiles from company websites:

```bash
# Get personal LinkedIn profiles
curl "https://scraper.hiscale.ai/scrap-linkedin?website=startup.io" \
  -H "X-API-Key: your-api-key"

# Response
{
  "company_linkedin": [],
  "personal_linkedin": [
    "https://linkedin.com/in/founder",
    "https://linkedin.com/in/cto"
  ]
}
```

### 3. Bulk LinkedIn Enrichment

Process CSV with 1000+ companies:

```bash
# Upload CSV
curl -X POST "https://scraper.hiscale.ai/csv/upload-linkedin-csv" \
  -H "X-API-Key: your-api-key" \
  -F "file=@companies.csv"

# Response: job_id = 456

# Check progress
curl "https://scraper.hiscale.ai/csv/job/456" \
  -H "X-API-Key: your-api-key"

# Download when complete
curl "https://scraper.hiscale.ai/csv/download/456" \
  -H "X-API-Key: your-api-key"
```

**Processing Time:** 1000 rows × 3 seconds = ~50 minutes (with 2 concurrent workers)

## Error Handling

### Common Errors

#### 1. Website Not Found

```json
{
  "website": "http://nonexistent.com",
  "error": "Failed to fetch homepage",
  "status": "error"
}
```

**Solution:** Verify the website URL is correct and accessible.

#### 2. No LinkedIn URLs Found

```json
{
  "website": "http://example.com",
  "company_linkedin": [],
  "personal_linkedin": [],
  "status": "no_contacts_found"
}
```

**Reason:** The website's homepage doesn't contain any LinkedIn URLs.

#### 3. Timeout Error (n8n)

```
AxiosError: timeout of 15000ms exceeded
```

**Solution:** Increase timeout to 30000ms (30 seconds) for slower websites.

#### 4. Invalid API Key

```json
{
  "detail": "Invalid API key"
}
```

**Solution:** Check the `X-API-Key` header value.

## Best Practices

### 1. Use Appropriate Timeouts

```json
{
  "options": {
    "timeout": 15000  // LinkedIn-only
  }
}
```

- **LinkedIn-only:** 15 seconds (sufficient for 95% of requests)
- **Slow websites:** 30 seconds
- **Cached requests:** 5 seconds

### 2. Batch Processing

For 100+ websites, use CSV upload instead of individual requests:

```bash
# Instead of 100 individual requests
for website in websites.txt; do
  curl "https://scraper.hiscale.ai/scrap-linkedin?website=$website"
done

# Use CSV upload (much more efficient)
curl -X POST "https://scraper.hiscale.ai/csv/upload-linkedin-csv" \
  -F "file=@websites.csv"
```

### 3. Cache Awareness

Check cache status to avoid redundant scraping:

```bash
# First request: 2-5 seconds
curl "https://scraper.hiscale.ai/scrap-linkedin?website=example.com"

# Second request (within 24h): <1 second (cached)
curl "https://scraper.hiscale.ai/scrap-linkedin?website=example.com"
```

### 4. Error Recovery in n8n

Add error handling in n8n workflows:

```
HTTP Request Node
  ↓
IF Node (check status)
  ↓ success
  Process LinkedIn URLs
  ↓ error/no_contacts_found
  Log to error sheet / Retry later
```

## Rate Limits

### Recommended Limits

- **Single requests:** No hard limit, but respect server capacity
- **CSV batch:** Max 2 concurrent jobs (configurable)
- **OpenAI API:** Not used in LinkedIn-only mode (no rate limits)
- **Redis cache:** No limits

### Optimization Tips

1. **Use caching:** Avoid re-scraping within 24 hours
2. **Batch wisely:** Group websites into CSVs of 100-500 rows
3. **Concurrent workers:** Increase `MAX_WORKERS` in .env for faster CSV processing

## Monitoring

### Check Job Status

```bash
# Get job progress
curl "https://scraper.hiscale.ai/csv/job/123" \
  -H "X-API-Key: your-api-key"

# Response
{
  "job_id": "123",
  "status": "processing",
  "total_rows": 100,
  "processed_rows": 45,
  "failed_rows": 2,
  "progress_percentage": 45.0
}
```

### View Logs

```bash
# Watch real-time logs
docker compose logs -f app | grep "LinkedIn"

# Example output
[LinkedIn Scraper] Fetching homepage: http://example.com
[LinkedIn Scraper] Found 1 company LinkedIn URL(s), 2 personal LinkedIn URL(s)
[Cache] Saving LinkedIn URLs to cache for http://example.com
```

## API Response Schema

### ContactInfo (LinkedIn-Only)

```json
{
  "website": "string",              // Normalized URL
  "company_linkedin": ["string"],   // Company LinkedIn URLs
  "personal_linkedin": ["string"],  // Personal LinkedIn URLs
  "status": "string"                // success, no_contacts_found, error
}
```

### ContactErrorResponse

```json
{
  "website": "string",
  "error": "string",
  "status": "error"
}
```

**Note:** The LinkedIn-only endpoint returns a simplified response format without `emails` and `phones` fields for cleaner integration.

## Troubleshooting

### Issue: Slow Response Times

**Symptom:** Requests taking longer than 10 seconds

**Solutions:**
1. Check website availability: `curl -I http://example.com`
2. Verify Redis is connected: `docker exec contact-scraper python -c "import redis; redis.Redis(host='redis').ping()"`
3. Use caching for repeated requests
4. Increase `request_timeout` in .env if websites are consistently slow

### Issue: Missing LinkedIn URLs

**Symptom:** `status: "no_contacts_found"` but website has LinkedIn links

**Possible Causes:**
1. LinkedIn URLs are loaded via JavaScript (not in initial HTML)
2. LinkedIn URLs are in iframes or external widgets
3. LinkedIn links use redirects or URL shorteners

**Solution:** This endpoint only extracts LinkedIn URLs from the initial HTML. JavaScript-rendered content is not captured.

### Issue: LinkedIn-Only Returns Empty, Full Scraping Works

**Symptom:** `/scrap-linkedin` returns no results, but `/scrap` finds contacts

**Reason:** These endpoints use **separate caches**:
- `/scrap-linkedin` → cache key: `linkedin:{url}` 
- `/scrap` → cache key: `contact:{url}`

This is intentional to prevent cache conflicts. If you call `/scrap-linkedin` first (which saves only LinkedIn data), then call `/scrap`, it will still scrape emails and phones correctly.

### Issue: CSV Job Stuck

**Symptom:** Job status remains "processing" for too long

**Solutions:**
1. Check logs: `docker compose logs -f app`
2. Verify worker pool is running: Check for `[WorkerPool] Initialized` in logs
3. Restart app: `docker compose restart app`
4. Check Supabase connection for job tracking

### Issue: Cache Not Working

**Symptom:** Repeated requests always take 2-5 seconds

**Solution:**
1. Verify Redis connection: See Redis troubleshooting in main README
2. Check cache TTL: `docker exec contact-scraper-redis redis-cli TTL contact:http://example.com`
3. Ensure Redis and app are on same network

## FAQs

**Q: Why use LinkedIn-only instead of full contact scraping?**

A: LinkedIn-only is 4-6x faster (2-5s vs 10-30s) and doesn't use OpenAI credits. Perfect when you only need LinkedIn URLs.

**Q: Can I get more than 3 LinkedIn URLs per type in CSV?**

A: The API extracts all LinkedIn URLs found, but the CSV output limits to 3 per type. Use `raw_json_response` column for the full list.

**Q: Does this work with LinkedIn Sales Navigator URLs?**

**A: Yes, it extracts any LinkedIn URL pattern including Sales Navigator, company pages, personal profiles, etc.

**Q: Are the results cached?**

**A: Yes, all results are cached for 24 hours. LinkedIn-only uses a separate cache (`linkedin:*`) from full scraping (`contact:*`).

**Q: Can I use this for commercial purposes?**

A: Yes, subject to your API key terms and LinkedIn's terms of service for accessing publicly available information.

**Q: What's the difference between company and personal LinkedIn URLs?**

A: 
- **Company:** `linkedin.com/company/*` - Official company pages
- **Personal:** `linkedin.com/in/*` - Individual profile pages

---

## Examples

### Python

```python
import requests

API_KEY = "your-api-key-here"
API_URL = "https://scraper.hiscale.ai"

# Single website
response = requests.get(
    f"{API_URL}/scrap-linkedin",
    params={"website": "example.com"},
    headers={"X-API-Key": API_KEY}
)

data = response.json()
print(f"Company: {data['company_linkedin']}")
print(f"People: {data['personal_linkedin']}")

# CSV upload
with open("websites.csv", "rb") as f:
    response = requests.post(
        f"{API_URL}/csv/upload-linkedin-csv",
        headers={"X-API-Key": API_KEY},
        files={"file": f},
        data={"website_column": "website"}
    )

job_id = response.json()["job_id"]
print(f"Job ID: {job_id}")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

const API_KEY = 'your-api-key-here';
const API_URL = 'https://scraper.hiscale.ai';

// Single website
async function scrapeLinkedIn(website) {
  const response = await axios.get(`${API_URL}/scrap-linkedin`, {
    params: { website },
    headers: { 'X-API-Key': API_KEY }
  });
  
  return response.data.linkedin_urls;
}

scrapeLinkedIn('example.com').then(data => {
  console.log('Company:', data.company_linkedin);
  console.log('People:', data.personal_linkedin);
});
```

### cURL

```bash
# Single request
curl "https://scraper.hiscale.ai/scrap-linkedin?website=example.com" \
  -H "X-API-Key: your-api-key"

# CSV upload
curl -X POST "https://scraper.hiscale.ai/csv/upload-linkedin-csv" \
  -H "X-API-Key: your-api-key" \
  -F "file=@websites.csv" \
  -F "website_column=website"

# Check job status
curl "https://scraper.hiscale.ai/csv/job/123" \
  -H "X-API-Key: your-api-key"

# Download results
curl "https://scraper.hiscale.ai/csv/download/123" \
  -H "X-API-Key: your-api-key"
```

---

**Last Updated:** 2024-01-20  
**API Version:** 1.0.0  
**Support:** See main README.md for troubleshooting