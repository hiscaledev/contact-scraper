"""CSV processing API routes."""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
from app.schemas.csv import CSVUploadResponse, JobStatus, JobError
from app.services.csv_service import start_csv_processing, get_csv_path
from app.core.database import get_job_status
from app.core.auth import verify_api_key
from typing import Optional


router = APIRouter()


@router.post(
    "/upload-csv",
    response_model=CSVUploadResponse,
    tags=["CSV Processing"],
    summary="Upload CSV file for batch contact scraping",
    description="Upload a CSV file with website URLs to scrape contacts in batch"
)
async def upload_csv(
    file: UploadFile = File(..., description="CSV file containing website URLs"),
    website_column: str = Form(
        default="website",
        description="Name of the column containing website URLs"
    ),
    api_key: str = Depends(verify_api_key)
):
    """
    Upload a CSV file for batch processing.
    
    The CSV file must contain a column with website URLs (default: 'website').
    Processing happens in the background, and you can track progress using the job_id.
    
    Args:
        file: CSV file to upload
        website_column: Name of the column containing website URLs
        api_key: API key for authentication
        
    Returns:
        CSVUploadResponse with job_id for tracking
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV file"
        )
    
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Read file content
        content = await file.read()
        
        # Start background processing
        start_csv_processing(job_id, content, website_column)
        
        # Get initial job status to get total rows
        job_data = get_job_status(job_id)
        total_rows = job_data.get("total_rows", 0) if job_data else 0
        
        return CSVUploadResponse(
            job_id=job_id,
            message="CSV uploaded successfully. Processing started.",
            total_rows=total_rows,
            status="queued"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing CSV: {str(e)}"
        )


@router.get(
    "/job/{job_id}",
    response_model=JobStatus,
    tags=["CSV Processing"],
    summary="Get job status",
    description="Check the status and progress of a CSV processing job"
)
async def get_job(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get the status of a background job.
    
    Args:
        job_id: Unique job identifier from upload response
        api_key: API key for authentication
        
    Returns:
        JobStatus with progress and completion information
    """
    job_data = get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found or expired"
        )
    
    # Calculate progress percentage
    total = job_data.get("total_rows", 0)
    processed = job_data.get("processed_rows", 0)
    progress = (processed / total * 100) if total > 0 else 0
    
    # Add download URL if completed
    download_url = None
    if job_data.get("status") == "completed":
        download_url = f"/csv/download/{job_id}"
    
    return JobStatus(
        job_id=job_data["job_id"],
        status=job_data["status"],
        total_rows=total,
        processed_rows=processed,
        failed_rows=job_data.get("failed_rows", 0),
        progress_percentage=round(progress, 2),
        created_at=job_data.get("created_at"),
        completed_at=job_data.get("completed_at"),
        error=job_data.get("error"),
        download_url=download_url
    )


@router.get(
    "/download/{job_id}",
    tags=["CSV Processing"],
    summary="Download processed CSV",
    description="Download the processed CSV file with contact information"
)
async def download_csv(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Download the processed CSV file.
    
    Args:
        job_id: Unique job identifier
        api_key: API key for authentication
        
    Returns:
        CSV file with scraped contact information
    """
    # Check if job exists and is completed
    job_data = get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found or expired"
        )
    
    if job_data.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job_data.get('status')}"
        )
    
    # Get file path
    output_path = get_csv_path(job_id, processed=True)
    
    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Processed file not found"
        )
    
    return FileResponse(
        path=output_path,
        media_type="text/csv",
        filename=f"contacts_{job_id}.csv"
    )
