"""CSV processing request and response schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CSVUploadResponse(BaseModel):
    """Response schema for CSV upload."""
    job_id: str = Field(..., description="Unique job ID for tracking progress")
    message: str = Field(..., description="Upload confirmation message")
    total_rows: int = Field(..., description="Total number of rows to process")
    status: str = Field(default="queued", description="Initial job status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "CSV uploaded successfully. Processing started.",
                "total_rows": 100,
                "status": "queued"
            }
        }


class JobStatus(BaseModel):
    """Job status response schema."""
    job_id: str = Field(..., description="Unique job ID")
    status: str = Field(..., description="Job status: queued, processing, completed, failed")
    total_rows: int = Field(..., description="Total number of rows")
    processed_rows: int = Field(..., description="Number of rows processed")
    failed_rows: int = Field(..., description="Number of rows that failed")
    progress_percentage: float = Field(..., description="Progress percentage")
    created_at: Optional[str] = Field(None, description="Job creation timestamp")
    completed_at: Optional[str] = Field(None, description="Job completion timestamp")
    error: Optional[str] = Field(None, description="Error message if failed")
    download_url: Optional[str] = Field(None, description="Download URL when completed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "total_rows": 100,
                "processed_rows": 45,
                "failed_rows": 2,
                "progress_percentage": 45.0,
                "created_at": "2026-01-05T10:00:00",
                "completed_at": None,
                "error": None,
                "download_url": None
            }
        }


class JobError(BaseModel):
    """Error response for job operations."""
    error: str = Field(..., description="Error message")
    job_id: Optional[str] = Field(None, description="Job ID if applicable")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Job not found",
                "job_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
