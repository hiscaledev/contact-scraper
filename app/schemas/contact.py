"""Contact scraping request and response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ScrapeRequest(BaseModel):
    """Request schema for scraping a website."""

    website: str = Field(
        ..., description="Website URL to scrape for contact information"
    )

    class Config:
        json_schema_extra = {"example": {"website": "https://example.com"}}


class ContactInfo(BaseModel):
    """Contact information response schema."""

    website: str = Field(..., description="The normalized website URL")
    emails: list[str] = Field(
        default_factory=list, description="List of email addresses found"
    )
    phones: list[str] = Field(
        default_factory=list, description="List of phone numbers found"
    )
    linkedin_urls: dict[str, list[str]] = Field(
        default_factory=lambda: {"company": [], "personal": []},
        description="LinkedIn URLs categorized by type (company/personal)",
    )
    status: str = Field(..., description="Status of the scraping operation")

    class Config:
        json_schema_extra = {
            "example": {
                "website": "http://example.com",
                "emails": ["contact@example.com", "info@example.com"],
                "phones": ["+1-555-0100", "+1-555-0101"],
                "linkedin_urls": {
                    "company": ["https://linkedin.com/company/example"],
                    "personal": ["https://linkedin.com/in/john-doe"],
                },
                "status": "success",
            }
        }


class ContactErrorResponse(BaseModel):
    """Error response schema for failed scraping."""

    website: str = Field(..., description="The website that failed to scrape")
    error: str = Field(..., description="Error message")
    status: str = Field(default="error", description="Status indicator")

    class Config:
        json_schema_extra = {
            "example": {
                "website": "http://example.com",
                "error": "Failed to fetch homepage",
                "status": "error",
            }
        }


class LinkedInOnlyResponse(BaseModel):
    """LinkedIn-only scraping response schema."""

    website: str = Field(..., description="The normalized website URL")
    company_linkedin: List[str] = Field(
        default_factory=list, description="Company LinkedIn URLs"
    )
    personal_linkedin: List[str] = Field(
        default_factory=list, description="Personal LinkedIn URLs"
    )
    status: str = Field(..., description="Status of the scraping operation")

    class Config:
        json_schema_extra = {
            "example": {
                "website": "http://example.com",
                "company_linkedin": ["https://linkedin.com/company/example"],
                "personal_linkedin": ["https://linkedin.com/in/john-doe"],
                "status": "success",
            }
        }


class LinkedInErrorResponse(BaseModel):
    """Error response schema for LinkedIn-only scraping."""

    website: str = Field(..., description="The website that failed to scrape")
    error: str = Field(..., description="Error message")
    status: str = Field(default="error", description="Status indicator")

    class Config:
        json_schema_extra = {
            "example": {
                "website": "http://example.com",
                "error": "Failed to fetch homepage",
                "status": "error",
            }
        }


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="healthy", description="API health status")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "message": "Contact Scraper API is running",
            }
        }
