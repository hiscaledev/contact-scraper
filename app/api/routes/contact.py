"""Contact scraping API routes."""

from typing import Union

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.core.auth import verify_api_key
from app.schemas.contact import (
    ContactErrorResponse,
    ContactInfo,
    HealthResponse,
    LinkedInErrorResponse,
    LinkedInOnlyResponse,
)
from app.services.contact_service import scrape_website
from app.services.linkedin_service import scrape_linkedin_only

router = APIRouter()


@router.get("/", response_model=HealthResponse, tags=["Health"])
def health_check():
    """
    Health check endpoint to verify API is running.
    """
    return HealthResponse(status="healthy", message="Contact Scraper API is running")


@router.get(
    "/scrap",
    tags=["Scraping"],
    summary="Scrape website for contact information",
    description="Extract email addresses, phone numbers, and LinkedIn URLs from a website",
)
def scrape_contact(
    website: str = Query(
        ...,
        description="Website URL to scrape for contact information",
        example="https://example.com",
    ),
    validate_linkedin: bool = Query(
        default=False,
        description="Whether to use AI to validate LinkedIn URLs (default: False)",
    ),
    skip_contact_page: bool = Query(
        default=False,
        description="Skip AI contact page detection for faster results (default: False)",
    ),
    api_key: str = Depends(verify_api_key),
):
    """
    Scrape a website for contact information including LinkedIn URLs.

    This endpoint:
    - Requires a valid API key in X-API-Key header
    - Normalizes the URL
    - Checks cache for existing data
    - Scrapes homepage and contact page for emails, phones, and LinkedIn URLs
    - Uses AI to validate contacts (LinkedIn validation optional)
    - Returns emails, phone numbers, and LinkedIn URLs

    Args:
        website: The URL of the website to scrape
        validate_linkedin: Whether to use AI to validate LinkedIn URLs (default: False)
        skip_contact_page: Skip AI contact page detection for faster results (default: False)
        api_key: API key for authentication (from X-API-Key header)

    Returns:
        ContactInfo with scraped data or ContactErrorResponse on failure
    """
    result = scrape_website(
        website,
        validate_linkedin=validate_linkedin,
        skip_contact_page=skip_contact_page,
    )

    # Return plain dict for n8n compatibility (FastAPI will handle serialization)
    return result


@router.get(
    "/scrap-linkedin",
    response_model=LinkedInOnlyResponse,
    tags=["Scraping"],
    summary="Scrape website for LinkedIn URLs only (fast)",
    description="Extract only LinkedIn URLs from homepage (no AI, no contact page, no validation)",
)
def scrape_linkedin(
    website: str = Query(
        ...,
        description="Website URL to scrape for LinkedIn URLs",
        example="https://example.com",
    ),
    api_key: str = Depends(verify_api_key),
):
    """
    Fast LinkedIn-only scraping from homepage.

    This endpoint:
    - Scrapes only the homepage (no contact page detection)
    - Extracts only LinkedIn URLs (company and personal)
    - No AI validation or processing
    - No emails or phone numbers returned
    - Fastest response time (2-5 seconds)
    - Uses separate cache from full contact scraping
    - Results are cached for 24 hours

    Args:
        website: The URL of the website to scrape
        api_key: API key for authentication (from X-API-Key header)

    Returns:
        LinkedInOnlyResponse with company_linkedin and personal_linkedin arrays only
    """
    result = scrape_linkedin_only(website)

    # Return plain response (FastAPI will handle serialization)
    return result
