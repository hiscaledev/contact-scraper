"""LinkedIn-only CSV processing service for background jobs with concurrent scraping."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd

from app.core.config import get_settings
from app.core.database import (
    create_job,
    increment_job_progress,
    update_job_status,
)
from app.services.linkedin_service import scrape_linkedin_only
from app.services.storage_service import (
    download_csv_from_storage,
    upload_csv_to_storage,
)
from app.services.worker_service import submit_csv_job

settings = get_settings()


def process_linkedin_csv_background(
    job_id: int, input_path: str, original_filename: str, website_column: str
) -> None:
    """
    Process CSV file for LinkedIn-only scraping in the background with concurrent requests.

    Args:
        job_id: Unique job identifier (integer primary key)
        input_path: Storage path to the input CSV
        original_filename: Original filename of the uploaded CSV
        website_column: Name of the column containing website URLs
    """
    try:
        # Update status to processing
        print(f"[LinkedIn Job {job_id}] Starting CSV processing")
        update_job_status(job_id, status="processing")

        # Download CSV from Supabase storage
        print(f"[LinkedIn Job {job_id}] Downloading CSV from storage: {input_path}")
        csv_content = download_csv_from_storage(input_path)
        if not csv_content:
            print(f"[LinkedIn Job {job_id}] Failed to download CSV from storage")
            update_job_status(
                job_id, status="failed", error="Failed to download CSV from storage"
            )
            return

        print(f"[LinkedIn Job {job_id}] CSV downloaded successfully")
        # Read CSV
        df = pd.read_csv(pd.io.common.BytesIO(csv_content))
        print(
            f"[LinkedIn Job {job_id}] CSV loaded: {len(df)} rows, {len(df.columns)} columns"
        )

        # Validate website column exists
        if website_column not in df.columns:
            print(f"[LinkedIn Job {job_id}] Error: Column '{website_column}' not found")
            update_job_status(
                job_id,
                status="failed",
                error=f"Column '{website_column}' not found in CSV. Available columns: {', '.join(df.columns)}",
            )
            return

        print(f"[LinkedIn Job {job_id}] Adding LinkedIn result columns to CSV")
        # Add LinkedIn-specific result columns (only 2 columns)
        df["company_linkedin"] = ""
        df["personal_linkedin"] = ""
        df["scrape_status"] = ""

        # Add error column only in debug mode
        if settings.debug:
            df["error"] = ""

        # Get concurrent workers setting (default 10)
        concurrent_workers = getattr(settings, "csv_concurrent_workers", 10)
        print(
            f"[LinkedIn Job {job_id}] Processing {len(df)} rows with {concurrent_workers} concurrent workers"
        )

        def process_single_row(index, website):
            """Process a single row and return the results."""
            if pd.isna(website) or not str(website).strip():
                return {
                    "index": index,
                    "scrape_status": "skipped",
                    "error": "Empty website URL",
                    "failed": True,
                }

            try:
                print(f"[LinkedIn Job {job_id}] Processing row {index + 1}: {website}")
                result = scrape_linkedin_only(str(website).strip())

                row_data = {
                    "index": index,
                    "scrape_status": result.status,
                    "company_linkedin": result.company_linkedin
                    if hasattr(result, "company_linkedin")
                    else [],
                    "personal_linkedin": result.personal_linkedin
                    if hasattr(result, "personal_linkedin")
                    else [],
                    "error": result.error if hasattr(result, "error") else None,
                    "failed": False,
                }

                print(
                    f"[LinkedIn Job {job_id}] Row {index + 1} processed successfully: {result.status}"
                )
                return row_data

            except Exception as e:
                print(f"[LinkedIn Job {job_id}] Error processing row {index + 1}: {e}")
                return {
                    "index": index,
                    "scrape_status": "error",
                    "error": str(e),
                    "failed": True,
                }

        # Process rows concurrently
        with ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            # Submit all tasks
            future_to_row = {
                executor.submit(process_single_row, index, row[website_column]): index
                for index, row in df.iterrows()
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_row):
                try:
                    row_data = future.result()
                    index = row_data["index"]

                    # Update DataFrame with results
                    df.at[index, "scrape_status"] = row_data.get(
                        "scrape_status", "error"
                    )

                    # Store LinkedIn URLs in 2 columns (comma-separated if multiple)
                    if "company_linkedin" in row_data and row_data["company_linkedin"]:
                        company_urls = row_data["company_linkedin"]
                        df.at[index, "company_linkedin"] = ", ".join(company_urls)

                    if (
                        "personal_linkedin" in row_data
                        and row_data["personal_linkedin"]
                    ):
                        personal_urls = row_data["personal_linkedin"]
                        df.at[index, "personal_linkedin"] = ", ".join(personal_urls)

                    # Store error only in debug mode
                    if settings.debug and row_data.get("error"):
                        df.at[index, "error"] = row_data["error"]

                    # Update progress
                    increment_job_progress(job_id, failed=row_data.get("failed", False))

                except Exception as e:
                    print(
                        f"[LinkedIn Job {job_id}] Error processing future result: {e}"
                    )
                    index = future_to_row[future]
                    df.at[index, "scrape_status"] = "error"
                    if settings.debug:
                        df.at[index, "error"] = str(e)
                    increment_job_progress(job_id, failed=True)

        print(f"[LinkedIn Job {job_id}] All rows processed, saving output CSV")
        # Save processed CSV to bytes
        output_buffer = pd.io.common.BytesIO()
        df.to_csv(output_buffer, index=False)
        output_content = output_buffer.getvalue()

        # Upload processed CSV to Supabase storage
        print(f"[LinkedIn Job {job_id}] Uploading processed CSV to storage")
        output_path = upload_csv_to_storage(
            job_id, output_content, original_filename, is_output=True
        )

        if output_path:
            print(
                f"[LinkedIn Job {job_id}] Output CSV uploaded to storage: {output_path}"
            )
            print(f"[LinkedIn Job {job_id}] Job completed successfully")
            # Mark as completed and store output path
            update_job_status(job_id, status="completed", output_path=output_path)
        else:
            print(f"[LinkedIn Job {job_id}] Failed to upload output CSV")
            update_job_status(
                job_id,
                status="failed",
                error="Failed to upload processed CSV to storage",
            )

    except Exception as e:
        print(f"[LinkedIn Job {job_id}] Fatal error: {e}")
        update_job_status(job_id, status="failed", error=str(e))


def start_linkedin_csv_processing(
    csv_content: bytes, original_filename: str, website_column: str = "website"
) -> Optional[int]:
    """
    Start processing a CSV file for LinkedIn-only scraping in a background worker.

    Args:
        csv_content: CSV file content as bytes
        original_filename: Original filename of the uploaded CSV
        website_column: Name of the column containing website URLs

    Returns:
        The job ID (integer) if successful, None otherwise
    """
    print(f"[LinkedIn CSV Upload] Processing file: {original_filename}")
    # Read CSV to get row count first
    df = pd.read_csv(pd.io.common.BytesIO(csv_content))
    total_rows = len(df)
    print(f"[LinkedIn CSV Upload] CSV contains {total_rows} rows")

    # Create job in database first to get the auto-generated ID
    print(f"[LinkedIn CSV Upload] Creating job in database")
    job_id = create_job(total_rows, None, original_filename)

    if not job_id:
        print(f"[LinkedIn CSV Upload] Failed to create job in database")
        return None

    print(f"[LinkedIn CSV Upload] Job created with ID: {job_id}")

    # Upload CSV to Supabase storage with the job ID
    print(f"[LinkedIn CSV Upload] Uploading CSV to storage")
    input_path = upload_csv_to_storage(
        job_id, csv_content, original_filename, is_output=False
    )

    if not input_path:
        print(f"[LinkedIn Job {job_id}] Failed to upload CSV to storage")
        update_job_status(
            job_id, status="failed", error="Failed to upload CSV to storage"
        )
        return None

    print(f"[LinkedIn Job {job_id}] CSV uploaded to storage: {input_path}")

    # Update job with input path
    update_job_status(job_id, input_path=input_path)

    # Submit job to worker pool (max 2 concurrent jobs)
    print(f"[LinkedIn Job {job_id}] Submitting to worker pool")
    submit_csv_job(
        process_linkedin_csv_background,
        job_id,
        input_path,
        original_filename,
        website_column,
    )

    print(f"[LinkedIn Job {job_id}] Job queued successfully for {total_rows} rows")
    return job_id
