# Contact Scraper API

An API service that scrapes websites to extract contact information (emails, phone numbers, and LinkedIn URLs), validates data using OpenAI, caches results in Redis, and supports batch CSV processing with Supabase-backed job tracking and storage.

## Index

- [Features](#features)
- [Installation Guide](#installation-guide)
- [Env files](#env-files)
- [Project structure](#project-structure)
- [Architecture](#architecture)
- [API overview](#api-overview)
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

- GET `/` — Health check
- GET `/scrap` — Scrape a website for contacts
  - Query params: `website` (required), `validate_linkedin` (optional, default `false`)
  - Header: `X-API-Key` if `API_KEYS` configured
- POST `/csv/upload-csv` — Upload CSV for batch scraping
  - Form fields: `file` (CSV), `website_column` (default `website`)
  - Returns `job_id` and initial stats
- GET `/csv/job/{job_id}` — Job status
- GET `/csv/download/{job_id}` — Signed URL for processed CSV
- GET `/csv/jobs` — Paginated job list (optional `status`, `limit` filters)

## Common troubleshooting

- Missing API key
  - Symptom: 401/403 errors
  - Fix: Set `API_KEYS` in `.env` and pass `X-API-Key` header; or leave `API_KEYS` empty in dev

- Redis host mismatch
  - Symptom: Cache errors / connection refused
  - Fix: In Docker set `REDIS_HOST=redis`; locally use `REDIS_HOST=localhost`

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
