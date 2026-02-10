"""CSV processing API routes."""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from app.schemas.csv import CSVUploadResponse, JobStatus, JobError
from app.services.csv_service import start_csv_processing
from app.core.database import get_job_status, get_all_jobs
from app.services.storage_service import get_public_url
from app.core.auth import verify_api_key
from typing import Optional, List


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
    Processing happens in the background with max 2 concurrent jobs.
    Files are stored in Supabase storage.
    
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
        # Read file content
        content = await file.read()
        
        # Start background processing with worker pool (returns integer job ID)
        job_id = start_csv_processing(content, file.filename, website_column)
        
        if not job_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to create job"
            )
        
        # Get initial job status to get total rows
        job_data = get_job_status(job_id)
        total_rows = job_data.get("total_rows", 0) if job_data else 0
        
        return CSVUploadResponse(
            job_id=str(job_id),  # Convert to string for API response
            message="CSV uploaded successfully. Processing queued.",
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
    job_id: int,
    api_key: str = Depends(verify_api_key)
):
    """
    Get the status of a background job.
    
    Args:
        job_id: Unique job identifier (integer) from upload response
        api_key: API key for authentication
        
    Returns:
        JobStatus with progress and completion information
    """
    job_data = get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
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
        job_id=str(job_data["id"]),  # Convert integer ID to string for response
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
    summary="Get download URL for processed CSV",
    description="Get a signed URL to download the processed CSV file with contact information"
)
async def download_csv(
    job_id: int,
    api_key: str = Depends(verify_api_key)
):
    """
    Get a signed URL to download the processed CSV file from Supabase storage.
    
    Args:
        job_id: Unique job identifier (integer)
        api_key: API key for authentication
        
    Returns:
        JSON with signed URL that expires in 1 hour
    """
    # Check if job exists and is completed
    job_data = get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    if job_data.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job_data.get('status')}"
        )
    
    # Get output path from job data
    output_path = job_data.get("output_path")
    if not output_path:
        raise HTTPException(
            status_code=404,
            detail="Output file path not found in job data"
        )
    
    # Get signed URL from Supabase storage
    signed_url = get_public_url(output_path)
    
    if not signed_url:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate download URL"
        )
    
    return {
        "job_id": str(job_id),
        "download_url": signed_url,
        "expires_in": "1 hour",
        "filename": f"contacts_{job_id}.csv"
    }


@router.get(
    "/jobs",
    response_model=List[JobStatus],
    tags=["CSV Processing"],
    summary="Get all jobs",
    description="Get all CSV processing jobs with optional status filter"
)
async def get_jobs_list(
    status: Optional[str] = Query(None, description="Filter by status (queued, processing, completed, failed)"),
    limit: int = Query(50, description="Maximum number of jobs to return", ge=1, le=100),
    api_key: str = Depends(verify_api_key)
):
    """
    Get all jobs with optional filtering.
    
    Args:
        status: Optional status filter
        limit: Maximum number of jobs to return (1-100)
        api_key: API key for authentication
        
    Returns:
        List of JobStatus objects
    """
    jobs = get_all_jobs(status, limit)
    
    # Convert to JobStatus format
    result = []
    for job_data in jobs:
        total = job_data.get("total_rows", 0)
        processed = job_data.get("processed_rows", 0)
        progress = (processed / total * 100) if total > 0 else 0
        
        job_id = job_data["id"]  # Get integer ID
        download_url = None
        if job_data.get("status") == "completed":
            download_url = f"/csv/download/{job_id}"
        
        result.append(JobStatus(
            job_id=str(job_id),  # Convert to string for API response
            status=job_data["status"],
            total_rows=total,
            processed_rows=processed,
            failed_rows=job_data.get("failed_rows", 0),
            progress_percentage=round(progress, 2),
            created_at=job_data.get("created_at"),
            completed_at=job_data.get("completed_at"),
            error=job_data.get("error"),
            download_url=download_url
        ))
    
    return result
