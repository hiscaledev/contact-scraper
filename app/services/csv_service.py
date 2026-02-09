"""CSV processing service for background jobs."""
import pandas as pd
import threading
from pathlib import Path
from typing import Optional
from app.services.contact_service import scrape_website
from app.core.database import (
    create_job,
    update_job_status,
    increment_job_progress
)


# Storage directory for CSV files
STORAGE_DIR = Path("storage/csv")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_csv_path(job_id: str, processed: bool = False) -> Path:
    """
    Get the file path for a CSV file.
    
    Args:
        job_id: Unique job identifier
        processed: Whether this is the processed output file
        
    Returns:
        Path to the CSV file
    """
    suffix = "_processed" if processed else ""
    return STORAGE_DIR / f"{job_id}{suffix}.csv"


def process_csv_background(job_id: str, csv_path: Path, website_column: str) -> None:
    """
    Process CSV file in the background.
    
    Args:
        job_id: Unique job identifier
        csv_path: Path to the uploaded CSV file
        website_column: Name of the column containing website URLs
    """
    try:
        # Update status to processing
        update_job_status(job_id, status="processing")
        
        # Read CSV
        df = pd.read_csv(csv_path)
        
        # Validate website column exists
        if website_column not in df.columns:
            update_job_status(
                job_id,
                status="failed",
                error=f"Column '{website_column}' not found in CSV. Available columns: {', '.join(df.columns)}"
            )
            return
        
        # Add result columns if they don't exist
        if "scrape_status" not in df.columns:
            df["scrape_status"] = ""
        if "emails" not in df.columns:
            df["emails"] = ""
        if "phones" not in df.columns:
            df["phones"] = ""
        if "error" not in df.columns:
            df["error"] = ""
        
        # Process each row
        for index, row in df.iterrows():
            website = row[website_column]
            
            if pd.isna(website) or not str(website).strip():
                df.at[index, "scrape_status"] = "skipped"
                df.at[index, "error"] = "Empty website URL"
                increment_job_progress(job_id, failed=True)
                continue
            
            try:
                print(f"[Job {job_id}] Processing row {index + 1}: {website}")
                result = scrape_website(str(website).strip())
                
                # Store results
                df.at[index, "scrape_status"] = result.status
                
                if hasattr(result, 'emails') and result.emails:
                    df.at[index, "emails"] = ", ".join(result.emails)
                
                if hasattr(result, 'phones') and result.phones:
                    df.at[index, "phones"] = ", ".join(result.phones)
                
                if hasattr(result, 'error'):
                    df.at[index, "error"] = result.error
                
                increment_job_progress(job_id, failed=False)
                
            except Exception as e:
                print(f"[Job {job_id}] Error processing row {index + 1}: {e}")
                df.at[index, "scrape_status"] = "error"
                df.at[index, "error"] = str(e)
                increment_job_progress(job_id, failed=True)
        
        # Save processed CSV
        output_path = get_csv_path(job_id, processed=True)
        df.to_csv(output_path, index=False)
        print(f"[Job {job_id}] Completed. Output saved to {output_path}")
        
        # Mark as completed
        update_job_status(job_id, status="completed")
        
    except Exception as e:
        print(f"[Job {job_id}] Fatal error: {e}")
        update_job_status(job_id, status="failed", error=str(e))


def start_csv_processing(
    job_id: str,
    csv_content: bytes,
    website_column: str = "website"
) -> None:
    """
    Start processing a CSV file in a background thread.
    
    Args:
        job_id: Unique job identifier
        csv_content: CSV file content as bytes
        website_column: Name of the column containing website URLs
    """
    # Save uploaded file
    csv_path = get_csv_path(job_id, processed=False)
    csv_path.write_bytes(csv_content)
    
    # Read CSV to get row count
    df = pd.read_csv(csv_path)
    total_rows = len(df)
    
    # Create job in Redis
    create_job(job_id, total_rows)
    
    # Start background processing
    thread = threading.Thread(
        target=process_csv_background,
        args=(job_id, csv_path, website_column),
        daemon=True
    )
    thread.start()
    
    print(f"[Job {job_id}] Started background processing for {total_rows} rows")
