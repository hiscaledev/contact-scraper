"""Supabase storage service for managing file uploads and downloads."""
from supabase import create_client, Client
from app.core.config import get_settings
from typing import Optional
from pathlib import Path
import io


settings = get_settings()

# Initialize Supabase client
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)


def ensure_bucket_exists() -> bool:
    """
    Ensure the Supabase storage bucket exists.
    
    Returns:
        True if bucket exists or was created, False otherwise
    """
    try:
        # Try to get bucket info
        buckets = supabase.storage.list_buckets()
        bucket_names = [bucket.name for bucket in buckets]
        
        if settings.supabase_bucket not in bucket_names:
            # Create bucket if it doesn't exist
            supabase.storage.create_bucket(
                settings.supabase_bucket,
                options={"public": False}
            )
            print(f"[Supabase] Created bucket: {settings.supabase_bucket}")
        
        return True
    except Exception as e:
        print(f"[!] Error ensuring bucket exists: {e}")
        return False


def upload_csv_to_storage(
    job_id: int,
    csv_content: bytes,
    original_filename: str,
    is_output: bool = False
) -> Optional[str]:
    """
    Upload CSV file to Supabase storage.
    
    Args:
        job_id: Unique job identifier (integer primary key)
        csv_content: CSV file content as bytes
        original_filename: Original filename of the CSV
        is_output: Whether this is an output file (processed)
        
    Returns:
        Storage path if successful, None otherwise
    """
    try:
        ensure_bucket_exists()
        
        # Determine storage path
        folder = "output" if is_output else "input"
        filename = f"{Path(original_filename).stem}_output.csv" if is_output else original_filename
        storage_path = f"jobs/{job_id}/{folder}/{filename}"
        
        # Upload to Supabase storage
        response = supabase.storage.from_(settings.supabase_bucket).upload(
            path=storage_path,
            file=csv_content,
            file_options={"content-type": "text/csv", "upsert": "true"}
        )
        
        print(f"[Supabase] Uploaded file to: {storage_path}")
        return storage_path
        
    except Exception as e:
        print(f"[!] Error uploading to Supabase storage: {e}")
        return None


def download_csv_from_storage(storage_path: str) -> Optional[bytes]:
    """
    Download CSV file from Supabase storage.
    
    Args:
        storage_path: Path to the file in Supabase storage
        
    Returns:
        File content as bytes if successful, None otherwise
    """
    try:
        response = supabase.storage.from_(settings.supabase_bucket).download(storage_path)
        print(f"[Supabase] Downloaded file from: {storage_path}")
        return response
        
    except Exception as e:
        print(f"[!] Error downloading from Supabase storage: {e}")
        return None


def get_public_url(storage_path: str) -> Optional[str]:
    """
    Get a signed URL for downloading a file.
    
    Args:
        storage_path: Path to the file in Supabase storage
        
    Returns:
        Signed URL if successful, None otherwise
    """
    try:
        # Create signed URL that expires in 1 hour (3600 seconds)
        response = supabase.storage.from_(settings.supabase_bucket).create_signed_url(
            storage_path,
            3600
        )
        
        return response.get("signedURL")
        
    except Exception as e:
        print(f"[!] Error creating signed URL: {e}")
        return None


def delete_file(storage_path: str) -> bool:
    """
    Delete a file from Supabase storage.
    
    Args:
        storage_path: Path to the file in Supabase storage
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        supabase.storage.from_(settings.supabase_bucket).remove([storage_path])
        print(f"[Supabase] Deleted file: {storage_path}")
        return True
        
    except Exception as e:
        print(f"[!] Error deleting from Supabase storage: {e}")
        return False


def list_job_files(job_id: int) -> list[str]:
    """
    List all files for a specific job.
    
    Args:
        job_id: Unique job identifier (integer primary key)
        
    Returns:
        List of file paths
    """
    try:
        response = supabase.storage.from_(settings.supabase_bucket).list(f"jobs/{job_id}")
        return [file.get("name") for file in response]
        
    except Exception as e:
        print(f"[!] Error listing job files: {e}")
        return []
