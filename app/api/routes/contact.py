"""Contact scraping API routes."""
from fastapi import APIRouter, Query, Depends
from app.schemas.contact import ContactInfo, ContactErrorResponse, HealthResponse
from app.services.contact_service import scrape_website
from app.core.auth import verify_api_key
from typing import Union


router = APIRouter()


@router.get("/", response_model=HealthResponse, tags=["Health"])
def health_check():
    """
    Health check endpoint to verify API is running.
    """
    return HealthResponse(
        status="healthy",
        message="Contact Scraper API is running"
    )


@router.get(
    "/scrap",
    response_model=Union[ContactInfo, ContactErrorResponse],
    tags=["Scraping"],
    summary="Scrape website for contact information",
    description="Extract email addresses, phone numbers, and LinkedIn URLs from a website"
)
def scrape_contact(
    website: str = Query(
        ...,
        description="Website URL to scrape for contact information",
        example="https://example.com"
    ),
    validate_linkedin: bool = Query(
        default=False,
        description="Whether to use AI to validate LinkedIn URLs (default: False)"
    ),
    api_key: str = Depends(verify_api_key)
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
        api_key: API key for authentication (from X-API-Key header)
        
    Returns:
        ContactInfo with scraped data or ContactErrorResponse on failure
    """
    result = scrape_website(website, validate_linkedin=validate_linkedin)
    return result
