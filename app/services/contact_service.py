"""Contact scraping service - main business logic."""
from typing import Union
from app.core.database import get_contact_from_cache, save_contact_to_cache
from app.services.scraper_utils import (
    normalize_url,
    fetch_page,
    extract_emails,
    extract_phones,
    extract_links,
)
from app.services.ai_service import find_contact_page, validate_contacts
from app.schemas.contact import ContactInfo, ContactErrorResponse


def scrape_website(website: str) -> Union[ContactInfo, ContactErrorResponse]:
    """
    Scrape a website for contact information.
    
    This function:
    1. Checks the cache for existing data
    2. Scrapes the homepage for emails and phones
    3. Uses AI to find and scrape a dedicated contact page
    4. Validates extracted contacts using AI
    5. Caches and returns the results
    
    Args:
        website: The website URL to scrape
        
    Returns:
        ContactInfo with scraped data or ContactErrorResponse on failure
    """
    try:
        website = normalize_url(website)
    except ValueError as e:
        return ContactErrorResponse(
            website=website,
            error=str(e),
            status="error"
        )

    # 1. Check cache
    cached = get_contact_from_cache(website)
    if cached:
        print("[Cache] Found existing contact info.")
        return ContactInfo(**cached, status=cached.get("status", "success"))

    try:
        # 2. Scrape homepage
        print(f"[1] Scraping homepage: {website}")
        html = fetch_page(website)
        if not html:
            raise Exception("Failed to fetch homepage")

        emails = extract_emails(html)
        phones = extract_phones(html)
        links = extract_links(html, website)
        print(f"    Found {len(emails)} emails, {len(phones)} phones on homepage")

        # 3. Find and scrape contact page
        contact_page = find_contact_page(website, links)
        if contact_page and contact_page != website:
            print(f"[2] Contact page found: {contact_page}")
            c_html = fetch_page(contact_page)
            if c_html:
                emails += extract_emails(c_html)
                phones += extract_phones(c_html)
                print(f"    Total: {len(emails)} emails, {len(phones)} phones")

        # 4. Handle no contacts found
        if not emails and not phones:
            print("    No contacts found.")
            result = ContactInfo(
                website=website,
                emails=[],
                phones=[],
                status="no_contacts_found"
            )
            save_contact_to_cache(website, [], [])
            return result
        
        # 5. Validate with AI
        print("[3] Validating contacts with AI...")
        validation = validate_contacts(emails, phones)
        valid_emails = validation.get("valid_email", [])
        valid_phones = validation.get("valid_phones", [])

        # 6. Save to cache and return
        print("[4] Saving to cache...")
        save_contact_to_cache(website, valid_emails, valid_phones)
        
        return ContactInfo(
            website=website,
            emails=valid_emails,
            phones=valid_phones,
            status="success"
        )

    except Exception as e:
        error_message = str(e)
        print(f"[!] Error scraping {website}: {error_message}")
        return ContactErrorResponse(
            website=website,
            error=error_message,
            status="error"
        )
