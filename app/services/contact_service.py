"""Contact scraping service - main business logic."""

from typing import Union

from app.core.database import get_contact_from_cache, save_contact_to_cache
from app.schemas.contact import ContactErrorResponse, ContactInfo
from app.services.ai_service import find_contact_page, validate_contacts
from app.services.scraper_utils import (
    extract_emails,
    extract_linkedin_urls,
    extract_links,
    extract_phones,
    fetch_page,
    normalize_url,
)


def scrape_website(
    website: str, validate_linkedin: bool = False, skip_contact_page: bool = False
) -> Union[ContactInfo, ContactErrorResponse]:
    """
    Scrape a website for contact information including LinkedIn URLs.

    This function:
    1. Checks the cache for existing data
    2. Scrapes the homepage for emails, phones, and LinkedIn URLs
    3. Uses AI to find and scrape a dedicated contact page (unless skip_contact_page=True)
    4. Validates extracted contacts using AI
    5. Caches and returns the results

    Args:
        website: The website URL to scrape
        validate_linkedin: Whether to use AI to validate LinkedIn URLs (default: False)
        skip_contact_page: Skip AI contact page detection for faster results (default: False)

    Returns:
        ContactInfo with scraped data or ContactErrorResponse on failure
    """
    try:
        website = normalize_url(website)
    except ValueError as e:
        return ContactErrorResponse(website=website, error=str(e), status="error")

    # 1. Check cache
    cached = get_contact_from_cache(website)
    if cached:
        print("[Cache] Found existing contact info.")
        return ContactInfo(**cached, status=cached.get("status", "success"))

    try:
        # 2. Scrape homepage
        print(f"[Scraper] Fetching homepage: {website}")
        html = fetch_page(website)
        if not html:
            raise Exception("Failed to fetch homepage")

        print(f"[Scraper] Homepage fetched successfully")
        emails = extract_emails(html)
        phones = extract_phones(html)
        linkedin_urls = extract_linkedin_urls(html)
        links = extract_links(html, website)

        company_count = len(linkedin_urls.get("company", []))
        personal_count = len(linkedin_urls.get("personal", []))
        print(
            f"[Scraper] Found {len(emails)} email(s), {len(phones)} phone(s), {company_count} company LinkedIn URL(s), {personal_count} personal LinkedIn URL(s) on homepage"
        )

        # 3. Find and scrape contact page (unless skipped for speed)
        if not skip_contact_page:
            print(f"[AI] Sending {len(links)} link(s) to AI to find contact page...")
            contact_page = find_contact_page(website, links)
            if contact_page and contact_page != website:
                print(f"[AI] Contact page found: {contact_page}")
                print(f"[Scraper] Fetching contact page...")
                c_html = fetch_page(contact_page)
                if c_html:
                    c_emails = extract_emails(c_html)
                    c_phones = extract_phones(c_html)
                    c_linkedin = extract_linkedin_urls(c_html)

                    print(
                        f"[Scraper] Found {len(c_emails)} email(s) and {len(c_phones)} phone(s) from contact page"
                    )
                    emails += c_emails
                    phones += c_phones

                    # Merge LinkedIn URLs
                    linkedin_urls["company"].extend(c_linkedin.get("company", []))
                    linkedin_urls["personal"].extend(c_linkedin.get("personal", []))

                    # Deduplicate
                    linkedin_urls["company"] = list(set(linkedin_urls["company"]))
                    linkedin_urls["personal"] = list(set(linkedin_urls["personal"]))

                    company_count = len(linkedin_urls["company"])
                    personal_count = len(linkedin_urls["personal"])
                    print(
                        f"[Scraper] Total: {len(emails)} email(s), {len(phones)} phone(s), {company_count} company LinkedIn URL(s), {personal_count} personal LinkedIn URL(s)"
                    )
            else:
                print(f"[AI] No dedicated contact page found")
        else:
            print(f"[Scraper] Skipping contact page detection (fast mode enabled)")

        # 4. Handle no contacts found
        if (
            not emails
            and not phones
            and not linkedin_urls.get("company")
            and not linkedin_urls.get("personal")
        ):
            print("[Scraper] No contacts found on homepage or contact page")
            result = ContactInfo(
                website=website,
                emails=[],
                phones=[],
                linkedin_urls={"company": [], "personal": []},
                status="no_contacts_found",
            )
            save_contact_to_cache(website, [], [], {"company": [], "personal": []})
            return result

        # 5. Validate with AI
        linkedin_status = "with" if validate_linkedin else "without"
        print(
            f"[AI] Sending {len(emails)} email(s), {len(phones)} phone(s), and LinkedIn URLs to AI for validation ({linkedin_status} LinkedIn validation)..."
        )
        validation = validate_contacts(emails, phones, linkedin_urls, validate_linkedin)
        valid_emails = validation.get("valid_email", [])
        valid_phones = validation.get("valid_phones", [])
        valid_linkedin = validation.get(
            "valid_linkedin_urls", {"company": [], "personal": []}
        )

        company_count = len(valid_linkedin.get("company", []))
        personal_count = len(valid_linkedin.get("personal", []))
        print(
            f"[AI] Validation complete: {len(valid_emails)} valid email(s), {len(valid_phones)} valid phone(s), {company_count} company LinkedIn URL(s), {personal_count} personal LinkedIn URL(s)"
        )

        # 6. Save to cache and return
        print("[Cache] Saving validated contacts to cache")
        save_contact_to_cache(website, valid_emails, valid_phones, valid_linkedin)

        return ContactInfo(
            website=website,
            emails=valid_emails,
            phones=valid_phones,
            linkedin_urls=valid_linkedin,
            status="success",
        )

    except Exception as e:
        error_message = str(e)
        print(f"[!] Error scraping {website}: {error_message}")
        return ContactErrorResponse(
            website=website, error=error_message, status="error"
        )
