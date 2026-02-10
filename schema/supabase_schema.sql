-- Contact Scraper Database Schema for Supabase
-- Note: The "scraping" schema must already exist in your Supabase database

-- ============================================================================
-- Contact Scraper Jobs Table (in scraping schema)
-- ============================================================================
-- IMPORTANT: If you already have this table with a job_id column, drop it first:
-- DROP TABLE IF EXISTS scraping.contact_scraper_jobs CASCADE;

CREATE TABLE IF NOT EXISTS scraping.contact_scraper_jobs (
    id BIGSERIAL PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    total_rows INTEGER NOT NULL DEFAULT 0,
    processed_rows INTEGER NOT NULL DEFAULT 0,
    failed_rows INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error TEXT,
    input_path TEXT,
    output_path TEXT,
    original_filename TEXT
);

-- Index for faster job lookups
CREATE INDEX IF NOT EXISTS idx_contact_scraper_jobs_status ON scraping.contact_scraper_jobs(status);
CREATE INDEX IF NOT EXISTS idx_contact_scraper_jobs_created_at ON scraping.contact_scraper_jobs(created_at DESC);

-- ============================================================================
-- Row Level Security (RLS) - Optional but recommended
-- ============================================================================
-- Enable RLS on jobs table
ALTER TABLE scraping.contact_scraper_jobs ENABLE ROW LEVEL SECURITY;

-- Create policy for service role (allows all operations)
CREATE POLICY "Enable all access for service role on jobs" ON scraping.contact_scraper_jobs
    FOR ALL USING (true);

-- ============================================================================
-- Storage Bucket Setup (Run this via Supabase Dashboard or API)
-- ============================================================================
-- Note: Storage buckets should be created via Supabase Dashboard or API
-- Bucket name: contact-scraper
-- Public: false
-- File size limit: 50MB (adjust as needed)
-- Allowed MIME types: text/csv
