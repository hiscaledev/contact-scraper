# LinkedIn-Only Endpoints Summary

## Quick Overview

Two new super-fast endpoints for extracting LinkedIn URLs without AI processing.

---

## ✨ New Endpoints

### 1. Single Website: `GET /scrap-linkedin`

**Fast LinkedIn extraction from homepage only**

```bash
curl "https://scraper.hiscale.ai/scrap-linkedin?website=example.com" \
  -H "X-API-Key: your-api-key"
```

**Response Time:** 2-5 seconds (vs 10-30 seconds for full scraping)

**Response:**
```json
{
  "website": "http://example.com",
  "emails": [],
  "phones": [],
  "linkedin_urls": {
    "company": ["https://linkedin.com/company/example"],
    "personal": ["https://linkedin.com/in/john-doe"]
  },
  "status": "success"
}
```

---

### 2. Batch CSV: `POST /csv/upload-linkedin-csv`

**Bulk LinkedIn extraction from CSV**

```bash
curl -X POST "https://scraper.hiscale.ai/csv/upload-linkedin-csv" \
  -H "X-API-Key: your-api-key" \
  -F "file=@websites.csv" \
  -F "website_column=website"
```

**Response:**
```json
{
  "job_id": "123",
  "message": "CSV uploaded successfully. LinkedIn-only processing queued.",
  "total_rows": 100,
  "status": "queued"
}
```

**Output CSV Columns:**
- `company_linkedin_url_1`, `company_linkedin_url_2`, `company_linkedin_url_3`
- `personal_linkedin_url_1`, `personal_linkedin_url_2`, `personal_linkedin_url_3`
- `scrape_status`, `raw_json_response`

---

## 🚀 n8n Configuration (Recommended)

### For Single Website Scraping

```json
{
  "parameters": {
    "method": "GET",
    "url": "https://scraper.hiscale.ai/scrap-linkedin",
    "queryParameters": {
      "parameters": [
        {
          "name": "website",
          "value": "={{ $json.website }}"
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
      "timeout": 15000
    }
  }
}
```

**Key Settings:**
- ✅ Timeout: **15000ms (15 seconds)** - sufficient for LinkedIn-only
- ✅ No `skip_contact_page` parameter needed
- ✅ Perfect for high-volume n8n workflows

---

## 📊 Performance Comparison

| Endpoint | Response Time | AI Used | Returns | Best For |
|----------|---------------|---------|---------|----------|
| `/scrap-linkedin` ⚡ | **2-5 seconds** | ❌ No | LinkedIn only | **n8n workflows** |
| `/scrap?skip_contact_page=true` | 5-15 seconds | ✅ Yes | All contacts | Need emails/phones too |
| `/scrap` (full) | 10-30 seconds | ✅ Yes | All contacts | Most complete data |

---

## 🎯 Why Use LinkedIn-Only?

### Benefits:
- ⚡ **4-6x faster** than full contact scraping
- 💰 **No OpenAI credits** used (no AI processing)
- ⏱️ **Lower timeout** needed in n8n (15s vs 60s)
- 🎯 **Focused** - only returns what you need
- 📦 **Same caching** - 24-hour TTL

### Perfect For:
- Lead generation (company pages)
- Employee finder (personal profiles)
- Bulk LinkedIn enrichment
- High-volume n8n workflows
- When you only need LinkedIn URLs

---

## 🔄 How It Works

### LinkedIn-Only Flow:
```
1. Normalize URL → 2. Check Redis Cache → 3. Scrape Homepage → 
4. Extract LinkedIn URLs → 5. Cache & Return
```

**No AI, no contact page detection, no validation = FAST!**

### Full Contact Flow (for comparison):
```
1. Normalize URL → 2. Check Redis Cache → 3. Scrape Homepage → 
4. AI finds Contact Page → 5. Scrape Contact Page → 
6. AI validates contacts → 7. Cache & Return
```

---

## 💡 Use Cases

### 1. B2B Lead Generation
```bash
# Get company LinkedIn for outreach
curl "https://scraper.hiscale.ai/scrap-linkedin?website=techcorp.com" \
  -H "X-API-Key: key"

# Result: company LinkedIn page for cold outreach
```

### 2. People Finder
```bash
# Find employee profiles
curl "https://scraper.hiscale.ai/scrap-linkedin?website=startup.io" \
  -H "X-API-Key: key"

# Result: founder, CTO, team LinkedIn profiles
```

### 3. Bulk Enrichment
```bash
# Process 1000 companies
curl -X POST "https://scraper.hiscale.ai/csv/upload-linkedin-csv" \
  -F "file=@companies.csv"

# Processing time: 1000 rows × 3 seconds = ~50 minutes
```

---

## 📝 CSV Input Example

**Input CSV:**
```csv
website,company_name
example.com,Example Corp
acme.org,Acme Inc
startup.io,Tech Startup
```

**Output CSV:**
```csv
website,company_name,scrape_status,company_linkedin_url_1,personal_linkedin_url_1,personal_linkedin_url_2
example.com,Example Corp,success,https://linkedin.com/company/example,https://linkedin.com/in/ceo,https://linkedin.com/in/cto
acme.org,Acme Inc,success,https://linkedin.com/company/acme,https://linkedin.com/in/founder,
startup.io,Tech Startup,no_contacts_found,,,
```

---

## ⚙️ Configuration

No special configuration needed! Uses same:
- Redis caching (24-hour TTL)
- API key authentication
- Supabase job tracking
- Worker pool (2 concurrent jobs)

---

## 🐛 Troubleshooting

### n8n Timeout
```
Error: timeout of 15000ms exceeded
```
**Solution:** Increase to 30000ms for slow websites

### No LinkedIn URLs Found
```json
{"status": "no_contacts_found"}
```
**Reason:** Homepage doesn't contain LinkedIn URLs (common for some sites)

### Cache Not Working
**Solution:** Check Redis connection:
```bash
docker exec contact-scraper python -c "import redis; redis.Redis(host='redis').ping()"
```

---

## 📚 Full Documentation

- **Complete guide:** `LINKEDIN_SCRAPING.md`
- **Main README:** `README.md`
- **n8n integration:** `N8N_INTEGRATION.md`
- **Fixes summary:** `FIXES_SUMMARY.md`

---

## 🚦 Quick Start

### 1. Test Single Website
```bash
curl "https://scraper.hiscale.ai/scrap-linkedin?website=hiscale.ai" \
  -H "X-API-Key: i8eUrz04CLVraTPMZwuGyw"
```

### 2. Use in n8n
- Add HTTP Request node
- URL: `https://scraper.hiscale.ai/scrap-linkedin`
- Add query param: `website`
- Add header: `X-API-Key`
- Set timeout: `15000`

### 3. Process CSV
```bash
curl -X POST "https://scraper.hiscale.ai/csv/upload-linkedin-csv" \
  -H "X-API-Key: your-key" \
  -F "file=@websites.csv"
```

---

## ✅ Summary

**Created 2 new endpoints:**
1. `GET /scrap-linkedin` - Single website LinkedIn scraping (2-5 seconds)
2. `POST /csv/upload-linkedin-csv` - Batch LinkedIn scraping from CSV

**Key advantages:**
- 4-6x faster than full scraping
- No AI processing required
- Perfect for n8n workflows
- Same 24-hour caching

**Recommended for:**
- High-volume LinkedIn extraction
- n8n automation workflows
- When you don't need emails/phones
- Lead generation and enrichment

---

**Status:** ✅ Deployed and Ready  
**Last Updated:** 2024-01-20  
**API Version:** 1.0.0