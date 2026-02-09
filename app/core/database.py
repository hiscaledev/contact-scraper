"""Redis database connection and operations."""
import redis
import json
from typing import Optional
from datetime import datetime
from app.core.config import get_settings


settings = get_settings()

# Create Redis client
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True  # Automatically decode responses to strings
)


# ============================================================================
# Contact Cache Operations
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


def save_contact_to_cache(website: str, emails: list[str], phones: list[str]) -> None:
    """
    Save contact info to Redis cache.
    
    Args:
        website: Website URL (used as key)
        emails: List of email addresses
        phones: List of phone numbers
    """
    doc = {
        "website": website,
        "emails": emails if emails else [],
        "phones": phones if phones else [],
    }
    try:
        redis_client.set(f"contact:{website}", json.dumps(doc))
        print(f"[Redis] Saved contact info for {website}")
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
# Job Tracking Operations
# ============================================================================

def create_job(job_id: str, total_rows: int) -> None:
    """
    Create a new background job in Redis.
    
    Args:
        job_id: Unique job identifier
        total_rows: Total number of rows to process
    """
    job_data = {
        "job_id": job_id,
        "status": "queued",
        "total_rows": total_rows,
        "processed_rows": 0,
        "failed_rows": 0,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None
    }
    try:
        redis_client.set(f"job:{job_id}", json.dumps(job_data))
        # Set expiration to 24 hours
        redis_client.expire(f"job:{job_id}", 86400)
        print(f"[Redis] Created job {job_id}")
    except Exception as e:
        print(f"[!] Error creating job: {e}")


def get_job_status(job_id: str) -> Optional[dict]:
    """
    Get the status of a background job.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        Job status dict if found, None otherwise
    """
    try:
        data = redis_client.get(f"job:{job_id}")
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"[!] Error retrieving job status: {e}")
        return None


def update_job_status(
    job_id: str,
    status: Optional[str] = None,
    processed_rows: Optional[int] = None,
    failed_rows: Optional[int] = None,
    error: Optional[str] = None
) -> None:
    """
    Update a job's status in Redis.
    
    Args:
        job_id: Unique job identifier
        status: New status (queued, processing, completed, failed)
        processed_rows: Number of rows processed
        failed_rows: Number of rows that failed
        error: Error message if any
    """
    try:
        job_data = get_job_status(job_id)
        if not job_data:
            print(f"[!] Job {job_id} not found")
            return
        
        if status:
            job_data["status"] = status
            if status in ["completed", "failed"]:
                job_data["completed_at"] = datetime.now().isoformat()
        
        if processed_rows is not None:
            job_data["processed_rows"] = processed_rows
        
        if failed_rows is not None:
            job_data["failed_rows"] = failed_rows
            
        if error:
            job_data["error"] = error
        
        redis_client.set(f"job:{job_id}", json.dumps(job_data))
        print(f"[Redis] Updated job {job_id}: status={status}, processed={processed_rows}")
    except Exception as e:
        print(f"[!] Error updating job status: {e}")


def increment_job_progress(job_id: str, failed: bool = False) -> None:
    """
    Increment the progress counters for a job.
    
    Args:
        job_id: Unique job identifier
        failed: Whether this row failed processing
    """
    try:
        job_data = get_job_status(job_id)
        if not job_data:
            return
        
        job_data["processed_rows"] += 1
        if failed:
            job_data["failed_rows"] += 1
        
        # Auto-complete when all rows processed
        if job_data["processed_rows"] >= job_data["total_rows"]:
            job_data["status"] = "completed"
            job_data["completed_at"] = datetime.now().isoformat()
        
        redis_client.set(f"job:{job_id}", json.dumps(job_data))
    except Exception as e:
        print(f"[!] Error incrementing job progress: {e}")

