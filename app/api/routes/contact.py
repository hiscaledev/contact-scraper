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
    description="Extract email addresses and phone numbers from a website"
)
def scrape_contact(
    website: str = Query(
        ...,
        description="Website URL to scrape for contact information",
        example="https://example.com"
    ),
    api_key: str = Depends(verify_api_key)
):
    """
    Scrape a website for contact information.
    
    This endpoint:
    - Requires a valid API key in X-API-Key header
    - Normalizes the URL
    - Checks cache for existing data
    - Scrapes homepage and contact page
    - Uses AI to validate contacts
    - Returns emails and phone numbers
    
    Args:
        website: The URL of the website to scrape
        api_key: API key for authentication (from X-API-Key header)
        
    Returns:
        ContactInfo with scraped data or ContactErrorResponse on failure
    """
    result = scrape_website(website)
    return result
