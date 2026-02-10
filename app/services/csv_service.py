"""CSV processing service for background jobs."""
import pandas as pd
import json
from pathlib import Path
from typing import Optional
from app.services.contact_service import scrape_website
from app.core.database import (
    create_job,
    update_job_status,
    increment_job_progress,
    get_job_status
)
from app.services.storage_service import (
    upload_csv_to_storage,
    download_csv_from_storage
)
from app.services.worker_service import submit_csv_job
from app.core.config import get_settings

settings = get_settings()


def process_csv_background(
    job_id: int,
    input_path: str,
    original_filename: str,
    website_column: str
) -> None:
    """
    Process CSV file in the background.
    
    Args:
        job_id: Unique job identifier (integer primary key)
        input_path: Storage path to the input CSV
        original_filename: Original filename of the uploaded CSV
        website_column: Name of the column containing website URLs
    """
    try:
        # Update status to processing
        print(f"[Job {job_id}] Starting CSV processing")
        update_job_status(job_id, status="processing")
        
        # Download CSV from Supabase storage
        print(f"[Job {job_id}] Downloading CSV from storage: {input_path}")
        csv_content = download_csv_from_storage(input_path)
        if not csv_content:
            print(f"[Job {job_id}] Failed to download CSV from storage")
            update_job_status(
                job_id,
                status="failed",
                error="Failed to download CSV from storage"
            )
            return
        
        print(f"[Job {job_id}] CSV downloaded successfully")
        # Read CSV
        df = pd.read_csv(pd.io.common.BytesIO(csv_content))
        print(f"[Job {job_id}] CSV loaded: {len(df)} rows, {len(df.columns)} columns")
        
        # Validate website column exists
        if website_column not in df.columns:
            print(f"[Job {job_id}] Error: Column '{website_column}' not found")
            update_job_status(
                job_id,
                status="failed",
                error=f"Column '{website_column}' not found in CSV. Available columns: {', '.join(df.columns)}"
            )
            return
        
        print(f"[Job {job_id}] Adding result columns to CSV")
        # Add result columns
        df["scrape_status"] = ""
        df["raw_json_response"] = ""
        df["email1"] = ""
        df["email2"] = ""
        df["email3"] = ""
        df["phone1"] = ""
        df["phone2"] = ""
        df["phone3"] = ""
        df["company_linkedin_url"] = ""
        df["personal_linkedin_url"] = ""
        
        # Add error column only in debug mode
        if settings.debug:
            df["error"] = ""
        
        # Process each row
        for index, row in df.iterrows():
            website = row[website_column]
            
            if pd.isna(website) or not str(website).strip():
                df.at[index, "scrape_status"] = "skipped"
                if settings.debug:
                    df.at[index, "error"] = "Empty website URL"
                increment_job_progress(job_id, failed=True)
                continue
            
            try:
                print(f"[Job {job_id}] Processing row {index + 1}: {website}")
                result = scrape_website(str(website).strip())
                
                # Convert result to dict for JSON storage
                result_dict = result.model_dump()
                
                # Store raw JSON response
                df.at[index, "raw_json_response"] = json.dumps(result_dict)
                df.at[index, "scrape_status"] = result.status
                
                # Store emails in separate columns
                if hasattr(result, 'emails') and result.emails:
                    for i, email in enumerate(result.emails[:3]):  # Max 3 emails
                        df.at[index, f"email{i+1}"] = email
                
                # Store phones in separate columns
                if hasattr(result, 'phones') and result.phones:
                    for i, phone in enumerate(result.phones[:3]):  # Max 3 phones
                        df.at[index, f"phone{i+1}"] = phone
                
                # Store LinkedIn URLs
                if hasattr(result, 'linkedin_urls') and result.linkedin_urls:
                    company_urls = result.linkedin_urls.get("company", [])
                    personal_urls = result.linkedin_urls.get("personal", [])
                    
                    # Store first company URL in dedicated column
                    if company_urls:
                        df.at[index, "company_linkedin_url"] = company_urls[0]
                    
                    # Store all personal URLs in personal_linkedin_url column
                    if personal_urls:
                        df.at[index, "personal_linkedin_url"] = ", ".join(personal_urls)
                
                # Store error only in debug mode
                if settings.debug and hasattr(result, 'error'):
                    df.at[index, "error"] = result.error
                
                increment_job_progress(job_id, failed=False)
                print(f"[Job {job_id}] Row {index + 1} processed successfully: {result.status}")
                
            except Exception as e:
                print(f"[Job {job_id}] Error processing row {index + 1}: {e}")
                df.at[index, "scrape_status"] = "error"
                if settings.debug:
                    df.at[index, "error"] = str(e)
                increment_job_progress(job_id, failed=True)
        
        print(f"[Job {job_id}] All rows processed, saving output CSV")
        # Save processed CSV to bytes
        output_buffer = pd.io.common.BytesIO()
        df.to_csv(output_buffer, index=False)
        output_content = output_buffer.getvalue()
        
        # Upload processed CSV to Supabase storage
        print(f"[Job {job_id}] Uploading processed CSV to storage")
        output_path = upload_csv_to_storage(
            job_id,
            output_content,
            original_filename,
            is_output=True
        )
        
        if output_path:
            print(f"[Job {job_id}] Output CSV uploaded to storage: {output_path}")
            print(f"[Job {job_id}] Job completed successfully")
            # Mark as completed and store output path
            update_job_status(job_id, status="completed", output_path=output_path)
        else:
            print(f"[Job {job_id}] Failed to upload output CSV")
            update_job_status(
                job_id,
                status="failed",
                error="Failed to upload processed CSV to storage"
            )
        
    except Exception as e:
        print(f"[Job {job_id}] Fatal error: {e}")
        update_job_status(job_id, status="failed", error=str(e))


def start_csv_processing(
    csv_content: bytes,
    original_filename: str,
    website_column: str = "website"
) -> Optional[int]:
    """
    Start processing a CSV file in a background worker.
    
    Args:
        csv_content: CSV file content as bytes
        original_filename: Original filename of the uploaded CSV
        website_column: Name of the column containing website URLs
        
    Returns:
        The job ID (integer) if successful, None otherwise
    """
    print(f"[CSV Upload] Processing file: {original_filename}")
    # Read CSV to get row count first
    df = pd.read_csv(pd.io.common.BytesIO(csv_content))
    total_rows = len(df)
    print(f"[CSV Upload] CSV contains {total_rows} rows")
    
    # Create job in database first to get the auto-generated ID
    print(f"[CSV Upload] Creating job in database")
    job_id = create_job(total_rows, None, original_filename)
    
    if not job_id:
        print(f"[CSV Upload] Failed to create job in database")
        return None
    
    print(f"[CSV Upload] Job created with ID: {job_id}")
    
    # Upload CSV to Supabase storage with the job ID
    print(f"[CSV Upload] Uploading CSV to storage")
    input_path = upload_csv_to_storage(
        job_id,
        csv_content,
        original_filename,
        is_output=False
    )
    
    if not input_path:
        print(f"[Job {job_id}] Failed to upload CSV to storage")
        update_job_status(job_id, status="failed", error="Failed to upload CSV to storage")
        return None
    
    print(f"[Job {job_id}] CSV uploaded to storage: {input_path}")
    
    # Update job with input path
    update_job_status(job_id, input_path=input_path)
    
    # Submit job to worker pool (max 2 concurrent jobs)
    print(f"[Job {job_id}] Submitting to worker pool")
    submit_csv_job(
        process_csv_background,
        job_id,
        input_path,
        original_filename,
        website_column
    )
    
    print(f"[Job {job_id}] Job queued successfully for {total_rows} rows")
    return job_id
