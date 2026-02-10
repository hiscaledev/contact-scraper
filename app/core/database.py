"""Database operations: Redis for caching, Supabase for job tracking."""
from supabase import create_client, Client
import redis
import json
from typing import Optional
from datetime import datetime
from app.core.config import get_settings


settings = get_settings()

# Create Redis client for caching
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    password=settings.redis_password if settings.redis_password else None,
    decode_responses=True  # Automatically decode responses to strings
)

# Create Supabase client for job tracking
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)


def ensure_tables_exist():
    """
    Ensure required database tables exist in Supabase.
    Table: scraping.contact_scraper_jobs should be created in 'scraping' schema.
    """
    try:
        # Check if contact_scraper_jobs table exists in scraping schema
        # If not, run the SQL script in supabase_schema.sql
        print("[Supabase] Database tables ready in 'scraping' schema")
    except Exception as e:
        print(f"[!] Error ensuring tables exist: {e}")


# ============================================================================
# Contact Cache Operations (Redis)
# ============================================================================

def get_contact_from_cache(website: str) -> Optional[dict]:
    """
    Retrieve existing contact info for a website from Redis cache.
    
    Args:
        website: The normalized website URL
        
    Returns:
        Contact information dict if found, None otherwise
    """
    try:
        data = redis_client.get(f"contact:{website}")
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"[!] Error retrieving from Redis: {e}")
        return None


def save_contact_to_cache(
    website: str, 
    emails: list[str], 
    phones: list[str],
    linkedin_urls: dict[str, list[str]] = None
) -> None:
    """
    Save contact info to Redis cache with TTL.
    
    Args:
        website: Website URL (used as key)
        emails: List of email addresses
        phones: List of phone numbers
        linkedin_urls: Dictionary with 'company' and 'personal' LinkedIn URLs
    """
    doc = {
        "website": website,
        "emails": emails if emails else [],
        "phones": phones if phones else [],
        "linkedin_urls": linkedin_urls if linkedin_urls else {"company": [], "personal": []},
    }
    try:
        # Use setex to set value with TTL from config
        redis_client.setex(
            f"contact:{website}",
            settings.cache_ttl,  # TTL in seconds from config
            json.dumps(doc)
        )
        print(f"[Redis] Saved contact info for {website} (TTL: {settings.cache_ttl}s)")
    except Exception as e:
        print(f"[!] Error saving to Redis: {e}")


def clear_cache(website: str) -> bool:
    """
    Clear cached contact info for a specific website.
    
    Args:
        website: The website URL to clear from cache
        
    Returns:
        True if deleted, False otherwise
    """
    try:
        result = redis_client.delete(f"contact:{website}")
        return result > 0
    except Exception as e:
        print(f"[!] Error clearing cache: {e}")
        return False


# ============================================================================
# Job Tracking Operations (Supabase - scraping schema)
# ============================================================================

def create_job(
    total_rows: int,
    input_path: str,
    original_filename: str
) -> Optional[int]:
    """
    Create a new background job in Supabase (scraping.contact_scraper_jobs table).
    
    Args:
        total_rows: Total number of rows to process
        input_path: Storage path to input CSV
        original_filename: Original filename of uploaded CSV
        
    Returns:
        The auto-generated job ID (integer) if successful, None otherwise
    """
    try:
        job_data = {
            "status": "queued",
            "total_rows": total_rows,
            "processed_rows": 0,
            "failed_rows": 0,
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "error": None,
            "input_path": input_path,
            "output_path": None,
            "original_filename": original_filename
        }
        
        response = supabase.schema("scraping").table("contact_scraper_jobs").insert(job_data).execute()
        job_id = response.data[0]["id"] if response.data else None
        print(f"[Supabase] Created job {job_id}")
        return job_id
    except Exception as e:
        print(f"[!] Error creating job: {e}")
        return None


def get_job_status(job_id: int) -> Optional[dict]:
    """
    Get the status of a background job from Supabase.
    
    Args:
        job_id: Unique job identifier (integer primary key)
        
    Returns:
        Job status dict if found, None otherwise
    """
    try:
        response = supabase.schema("scraping").table("contact_scraper_jobs").select("*").eq("id", job_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"[!] Error retrieving job status: {e}")
        return None


def get_all_jobs(status: Optional[str] = None, limit: int = 50) -> list[dict]:
    """
    Get all jobs with optional status filter.
    
    Args:
        status: Optional status filter (queued, processing, completed, failed)
        limit: Maximum number of jobs to return
        
    Returns:
        List of job dicts
    """
    try:
        query = supabase.schema("scraping").table("contact_scraper_jobs").select("*")
        
        # Filter by status if provided
        if status:
            query = query.eq("status", status)
        
        # Order by creation date (newest first) and limit
        query = query.order("created_at", desc=True).limit(limit)
        
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[!] Error retrieving jobs: {e}")
        return []


def update_job_status(
    job_id: int,
    status: Optional[str] = None,
    processed_rows: Optional[int] = None,
    failed_rows: Optional[int] = None,
    error: Optional[str] = None,
    output_path: Optional[str] = None,
    input_path: Optional[str] = None
) -> None:
    """
    Update a job's status in Supabase.
    
    Args:
        job_id: Unique job identifier (integer primary key)
        status: New status (queued, processing, completed, failed)
        processed_rows: Number of rows processed
        failed_rows: Number of rows that failed
        error: Error message if any
        output_path: Storage path to output CSV
        input_path: Storage path to input CSV
    """
    try:
        update_data = {}
        
        if status:
            update_data["status"] = status
            if status in ["completed", "failed"]:
                update_data["completed_at"] = datetime.now().isoformat()
        
        if processed_rows is not None:
            update_data["processed_rows"] = processed_rows
        
        if failed_rows is not None:
            update_data["failed_rows"] = failed_rows
            
        if error:
            update_data["error"] = error
        
        if output_path:
            update_data["output_path"] = output_path
        
        if input_path:
            update_data["input_path"] = input_path
        
        if update_data:
            supabase.schema("scraping").table("contact_scraper_jobs").update(update_data).eq("id", job_id).execute()
            print(f"[Supabase] Updated job {job_id}: {update_data}")
    except Exception as e:
        print(f"[!] Error updating job status: {e}")


def increment_job_progress(job_id: int, failed: bool = False) -> None:
    """
    Increment the progress counters for a job.
    
    Args:
        job_id: Unique job identifier (integer primary key)
        failed: Whether this row failed processing
    """
    try:
        job_data = get_job_status(job_id)
        if not job_data:
            return
        
        processed_rows = job_data["processed_rows"] + 1
        failed_rows = job_data["failed_rows"] + (1 if failed else 0)
        
        update_data = {
            "processed_rows": processed_rows,
            "failed_rows": failed_rows
        }
        
        # Auto-complete when all rows processed
        if processed_rows >= job_data["total_rows"]:
            update_data["status"] = "completed"
            update_data["completed_at"] = datetime.now().isoformat()
        
        supabase.schema("scraping").table("contact_scraper_jobs").update(update_data).eq("id", job_id).execute()
    except Exception as e:
        print(f"[!] Error incrementing job progress: {e}")


# Initialize tables on module load
ensure_tables_exist()



