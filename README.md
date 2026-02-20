# Contact Scraper API

An API service that scrapes websites to extract contact information (emails, phone numbers, and LinkedIn URLs), validates data using OpenAI, caches results in Redis, and supports batch CSV processing with Supabase-backed job tracking and storage.

## Index

- [Features](#features)
- [Installation Guide](#installation-guide)
- [Env files](#env-files)
- [Project structure](#project-structure)
- [Architecture](#architecture)
- [API overview](#api-overview)
- [n8n Integration](#n8n-integration)
- [Common troubleshooting](#common-troubleshooting)
- [Notes](#notes)

## Features

- FastAPI-based REST API with interactive docs at `/docs`
- Health check endpoint to verify server status
- Website contact scraping: emails, phones, LinkedIn (company and personal)
- AI-assisted contact validation via OpenAI (optional LinkedIn validation)
- URL normalization and robust HTML parsing using BeautifulSoup
- Caching with Redis to avoid repeated scraping and speed up responses
- CSV upload endpoint for batch processing with background worker pool
- Supabase integration for job tracking (Postgres) and file storage
- Signed download URLs for processed CSV results
- API key authentication via `X-API-Key` header (can be disabled in dev)
- CORS enabled for easy integration with frontends
- Docker-first deployment with `docker-compose`

## Installation Guide

You can run this project with Docker (recommended) or locally using Python.

### 1) Prerequisites

- Docker and Docker Compose
- Supabase project (URL + service role key)
- OpenAI API key

### 2) Configure environment

- Copy `.env.example` to `.env`
- Fill in required values (see Env files section below)
- For Docker, set `REDIS_HOST=redis`

Optional: run the setup helper to validate your environment and build images.

```bash
bash setup.sh
```

### 3) Set up Supabase

- In your Supabase project, ensure a schema named `scraping` exists
- Run the SQL in `schema/supabase_schema.sql` (tables and indexes for jobs)
- Create a private storage bucket named `contact-scraper`

### 4) Start the stack

```bash
# Start Redis and the API
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

API will be available at:

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### Local development (without Docker)

```bash
# Install uv (Python manager from Astral)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Ensure Redis is running locally
docker run -d -p 6379:6379 redis:8.4.0-alpine

# Set in .env for local dev
# REDIS_HOST=localhost

# Run the app with live reload
uv run uvicorn main:app --reload
```

## Env files

Environment variables are loaded from `.env` (see `app/core/config.py`). The project includes `.env.example` with defaults and guidance.

Key variables:

- API_KEYS: Comma-separated list of allowed API keys; empty disables auth (dev only)
- OPENAI_API_KEY: Your OpenAI API key
- OPENAI_MODEL: Model for validation (default: `gpt-4.1-mini`)
- REDIS_HOST: Redis host (`redis` in Docker, `localhost` locally)
- REDIS_PORT: Redis port (default: 6379)
- REDIS_DB: Redis DB index (default: 0)
- REDIS_PASSWORD: Redis password (optional)
- SUPABASE_URL: Your Supabase project URL
- SUPABASE_KEY: Supabase service role key (not anon key)
- SUPABASE_BUCKET: Storage bucket name (default: `contact-scraper`)
- DEBUG: Enables verbose logging and adds an `error` column in CSV output
- MAX_WORKERS: Max concurrent CSV jobs in worker pool (default: 2)
- CSV_CONCURRENT_WORKERS: Concurrent website scraping within each CSV job (default: 10)
- CACHE_TTL: Cache TTL seconds for website results (default: 86400)

## Project structure

```
contact-scraper/
├─ Dockerfile
├─ docker-compose.yml
├─ main.py                  # FastAPI app entrypoint
├─ pyproject.toml           # Python project deps
├─ setup.sh                 # Setup helper script
├─ uv.lock                  # uv dependency lockfile
├─ .env                     # Environment config (user-defined)
├─ .env.example             # Example environment template
├─ schema/
│  └─ supabase_schema.sql   # Supabase schema for jobs
└─ app/
   ├─ __init__.py
   ├─ api/
   │  ├─ __init__.py
   │  ├─ router.py          # Combines route modules
   │  └─ routes/
   │     ├─ __init__.py
   │     ├─ contact.py      # Health and website scraping endpoints
   │     └─ csv.py          # CSV upload, job status, download endpoints
   ├─ core/
   │  ├─ __init__.py
   │  ├─ auth.py            # API key verification via X-API-Key
   │  ├─ config.py          # Pydantic settings loaded from .env
   │  └─ database.py        # Redis cache + Supabase job tracking
   ├─ schemas/
   │  ├─ __init__.py
   │  ├─ contact.py         # Pydantic models for contact responses
   │  └─ csv.py             # Pydantic models for CSV job responses
   └─ services/
      ├─ __init__.py
      ├─ ai_service.py      # OpenAI-powered validation and contact page detection
      ├─ contact_service.py # Main scraping and validation logic with caching
      ├─ csv_service.py     # Background CSV processing orchestration
      ├─ scraper_utils.py   # Requests/HTML parsing, email/phone/link extraction
      ├─ storage_service.py # Supabase storage upload/download/signed URLs
      └─ worker_service.py  # Threaded worker pool for job concurrency
```

## Architecture

At a glance, the system combines FastAPI for HTTP endpoints, Redis for caching, Supabase for job tracking and file storage, and OpenAI for optional AI-assisted validation.

- FastAPI app (`main.py`)
  - Wires CORS, reads settings, and mounts routes via `app/api/router.py`.
  - Routes:
    - `contact.py` → health check and single-website scrape (`GET /scrap`).
    - `csv.py` → CSV upload and job operations.

- Authentication (`app/core/auth.py`)
  - Verifies `X-API-Key` against `API_KEYS` from env.
  - If `API_KEYS` is empty, auth is effectively disabled (development only).

- Configuration (`app/core/config.py`)
  - Pydantic Settings loads `.env` into a typed `Settings` object.
  - Centralizes Redis, OpenAI, Supabase, cache TTL, and worker settings.

- Contact scraping flow (`app/services/contact_service.py`)
  1. Normalize URL and check Redis cache (`app/core/database.py`).
  2. Fetch homepage (`scraper_utils.fetch_page`) and extract emails, phones, and LinkedIn URLs (`scraper_utils.extract_*`).
  3. Use OpenAI to pick a likely contact page (`ai_service.find_contact_page`); scrape it if found and merge results.
  4. Optionally validate extracted data with OpenAI (`ai_service.validate_contacts`).
  5. Save validated results to Redis with TTL and return.

- CSV batch pipeline (`app/services/csv_service.py`)
  - Upload (`POST /csv/upload-csv`):
    1. Read CSV to count rows; create a job row in Supabase (`database.create_job`).
    2. Upload the CSV to Supabase Storage (`storage_service.upload_csv_to_storage`).
    3. Queue background processing via a thread-based worker pool (`worker_service.submit_csv_job`).
  - Worker execution (`process_csv_background`):
    1. Download input CSV from storage.
    2. Iterate rows; for each website call `scrape_website`.
    3. Record raw JSON, normalized output columns, and (in debug) per-row error.
    4. Upload the result CSV to storage; update job status to completed.
  - Status and download:
    - `GET /csv/job/{job_id}` reads job progress from Supabase.
    - `GET /csv/download/{job_id}` returns a signed URL via `storage_service.get_public_url`.

- Persistence and cache (`app/core/database.py` + `storage_service.py`)
  - Redis stores website contact results under `contact:{normalized_url}` with TTL (`CACHE_TTL`).
  - Supabase Postgres table `scraping.contact_scraper_jobs` tracks job metadata and progress.
  - Supabase Storage keeps input/output CSVs under `jobs/{job_id}/...`.

- Worker pool (`app/services/worker_service.py`)
  - A lightweight thread dispatcher limits concurrency to `MAX_WORKERS`.
  - Jobs are queued and executed without blocking the API.

- Deployment (`docker-compose.yml`)
  - `redis` service for caching.
  - `app` service builds from `Dockerfile`, mounts code, and exposes port 8000.
  - `.env` provides runtime configuration to the container.

## API overview

### Contact Scraping Endpoints

- GET `/` — Health check
- GET `/scrap` — Scrape a website for full contacts (emails, phones, LinkedIn)
  - Query params: 
    - `website` (required)
    - `validate_linkedin` (optional, default `false`)
    - `skip_contact_page` (optional, default `false`) - Skip AI contact page detection for faster results
  - Header: `X-API-Key` if `API_KEYS` configured
  - **Average response time: 5-15 seconds** (with `skip_contact_page=true`), **10-30 seconds** (full scan)
- GET `/scrap-linkedin` — **NEW** Scrape LinkedIn URLs only (fast, no AI)
  - Query params: `website` (required)
  - Header: `X-API-Key` if `API_KEYS` configured
  - **Average response time: 2-5 seconds** (homepage only, no AI validation)
  - Returns only `company_linkedin` and `personal_linkedin` arrays
  - **Uses separate cache** from full contact scraping (cache key: `linkedin:{url}`)

### CSV Batch Processing Endpoints

- POST `/csv/upload-csv` — Upload CSV for batch full contact scraping
  - Form fields: `file` (CSV), `website_column` (default `website`)
  - Returns `job_id` and initial stats
  - Output: emails, phones, LinkedIn URLs
  - **Processing:** 10 concurrent requests per job (configurable via `CSV_CONCURRENT_WORKERS`)
- POST `/csv/upload-linkedin-csv` — **NEW** Upload CSV for batch LinkedIn-only scraping
  - Form fields: `file` (CSV), `website_column` (default `website`)
  - Returns `job_id` and initial stats
  - Output: **Only 2 new columns**: `company_linkedin` and `personal_linkedin` (comma-separated if multiple)
  - **Much faster**: 2-5 seconds per row (vs 10-30 seconds for full scraping)
  - **Processing:** 10 concurrent requests per job (configurable via `CSV_CONCURRENT_WORKERS`)
- GET `/csv/job/{job_id}` — Job status
- GET `/csv/download/{job_id}` — Signed URL for processed CSV
- GET `/csv/jobs` — Paginated job list (optional `status`, `limit` filters)

## n8n Integration

### LinkedIn-Only Endpoint (Recommended for n8n)

For fastest results with n8n, use the `/scrap-linkedin` endpoint:

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
          "value": "example.com"
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
  }
}
```

**Benefits:**
- **Response time: 2-5 seconds** (much faster than full scraping)
- Only 15-second timeout needed
- No AI processing (instant results)
- Returns only `company_linkedin` and `personal_linkedin` arrays (cleaner response)
- **Separate cache** (won't interfere with full contact scraping)
- Perfect for high-volume scraping in n8n workflows

### Full Contact Scraping Configuration

When using the `/scrap` endpoint with n8n HTTP Request node, **you must increase the timeout** as the scraping process involves multiple AI calls and website fetches.

#### Recommended n8n Configuration

```json
{
  "parameters": {
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
      "timeout": 60000,
      "redirect": {
        "followRedirects": true,
        "maxRedirects": 5
      }
    }
  }
}
```

**Key settings:**

- **`timeout: 60000`** (60 seconds) - Required for AI processing (can use 30000ms if `skip_contact_page=true`)
- **`skip_contact_page: true`** - Recommended for n8n to get faster results (5-15 seconds vs 10-30 seconds)
- Default 10-second timeout will cause timeout errors
- The endpoint typically responds in:
  - **5-15 seconds** with `skip_contact_page=true` (fast mode - homepage only)
  - **10-30 seconds** with full contact page detection (more comprehensive)

### Endpoint Comparison for n8n

| Endpoint | Response Time | AI Used | Cache | Returns | Best For |
|----------|---------------|---------|-------|---------|----------|
| `/scrap-linkedin` | 2-5 seconds | ❌ No | Separate (`linkedin:*`) | LinkedIn URLs only | **Recommended for n8n** - High-volume workflows |
| `/scrap?skip_contact_page=true` | 5-15 seconds | ✅ Yes (validation) | Shared (`contact:*`) | Emails, phones, LinkedIn | Need all contact types quickly |
| `/scrap` (full) | 10-30 seconds | ✅ Yes (detection + validation) | Shared (`contact:*`) | Emails, phones, LinkedIn (comprehensive) | Most complete data |

### CSV Batch Processing for LinkedIn

Use `/csv/upload-linkedin-csv` for batch LinkedIn scraping:

```bash
# Upload CSV with website column
curl -X POST "https://scraper.hiscale.ai/csv/upload-linkedin-csv" \
  -H "X-API-Key: your-api-key-here" \
  -F "file=@websites.csv" \
  -F "website_column=website"

# Response: {"job_id": "123", "message": "LinkedIn-only processing queued", "total_rows": 100}

# Check status
curl "https://scraper.hiscale.ai/csv/job/123" \
  -H "X-API-Key: your-api-key-here"

# Download results when completed
curl "https://scraper.hiscale.ai/csv/download/123" \
  -H "X-API-Key: your-api-key-here"
```

**Output CSV columns:**
- `company_linkedin` - Comma-separated list of company LinkedIn URLs
- `personal_linkedin` - Comma-separated list of personal LinkedIn URLs
- `scrape_status` (success, error, no_contacts_found, skipped)
- `error` (only in DEBUG mode)

**Performance:**
- **10 concurrent requests** within each CSV job (default)
- Example: 100 rows with 10 concurrent workers = ~30-50 seconds (vs 5-8 minutes sequential)
- Configurable via `CSV_CONCURRENT_WORKERS` environment variable

## Common troubleshooting

- **LinkedIn-only scraping returns empty, but full scraping works**
  - Reason: `/scrap-linkedin` and `/scrap` use **separate caches**
  - LinkedIn-only cache key: `linkedin:{url}`
  - Full contact cache key: `contact:{url}`
  - This is intentional to prevent cache conflicts
  - If you scrape LinkedIn-only first, then full scraping will still work correctly

- **n8n HTTP node spinning endlessly or timing out**
  - Symptom: Request never completes in n8n, or times out with "timeout exceeded" error
  - **Fix 1**: Add `skip_contact_page=true` query parameter for faster results (5-15 seconds)
  - **Fix 2**: Increase timeout to `60000` (60 seconds) in n8n options, or `30000` (30 seconds) if using `skip_contact_page=true`
  - **Fix 3**: Ensure Redis is properly connected (check `docker compose logs app` for Redis errors)
  - Technical: The API includes `Connection: close` header to ensure proper response completion
  - Reason: Full scraping involves multiple HTTP requests + 2 OpenAI API calls (~10-30 seconds total)

- Missing API key
  - Symptom: 401/403 errors
  - Fix: Set `API_KEYS` in `.env` and pass `X-API-Key` header; or leave `API_KEYS` empty in dev

- Redis connection errors / Cache not working
  - Symptom: `Error connecting to redis` in logs, repeated scraping takes same time as first request
  - Fix 1: Ensure Redis and app are on the same Docker network (both should be on `hiscale` network)
  - Fix 2: In Docker set `REDIS_HOST=redis`; locally use `REDIS_HOST=localhost`
  - Fix 3: Check both containers are running: `docker compose ps`
  - Fix 4: Test Redis connection: `docker exec contact-scraper python -c "import redis; redis.Redis(host='redis').ping()"`

- Supabase credentials or bucket issues
  - Symptom: Job creation/storage fails; 500 errors on upload/download
  - Fix: Set `SUPABASE_URL` and `SUPABASE_KEY` (service role). Create the `contact-scraper` bucket (private). Run `schema/supabase_schema.sql`.

- OpenAI errors or empty validation
  - Symptom: No validated contacts; logs show OpenAI exceptions
  - Fix: Ensure `OPENAI_API_KEY` is valid and model name exists; check network egress and rate limits

- CSV column not found
  - Symptom: Job fails with "Column 'website' not found"
  - Fix: Ensure your CSV has the `website` column or set `website_column` accordingly when uploading

- No contacts found
  - Symptom: Status `no_contacts_found`
  - Fix: Verify the given domain is correct; content may be sparse, or pages block scraping; try enabling `validate_linkedin` for better URL signals

- Port conflicts / service won’t start
  - Symptom: `uvicorn` fails to bind 8000 or Redis port
  - Fix: Change ports in `docker-compose.yml` or stop the conflicting service

- Local vs Docker URLs
  - Note: Internally, the scraper normalizes URLs to `http://` for consistency; most sites redirect to https automatically.

## Notes

- Authentication is enforced if `API_KEYS` is set; otherwise requests are allowed (development convenience).
- Caching reduces repeated work; you can clear or adjust TTL via Redis settings.
- The worker pool defaults to `MAX_WORKERS=2` to avoid overload; adjust carefully.

---

Made with FastAPI, Redis, Supabase, and OpenAI.
