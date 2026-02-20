"""LinkedIn-only scraping service - fast extraction without AI validation."""

import json
from typing import Union

from app.core.config import get_settings
from app.core.database import redis_client
from app.schemas.contact import LinkedInErrorResponse, LinkedInOnlyResponse
from app.services.scraper_utils import (
    extract_linkedin_urls,
    fetch_page,
    normalize_url,
)

settings = get_settings()


def scrape_linkedin_only(
    website: str,
) -> Union[LinkedInOnlyResponse, LinkedInErrorResponse]:
    """
    Scrape a website for LinkedIn URLs only (homepage only, no AI).

    This is a fast, lightweight version that:
    1. Checks separate LinkedIn-only cache
    2. Scrapes homepage for LinkedIn URLs
    3. Returns immediately (no AI validation, no contact page detection)

    Args:
        website: The website URL to scrape

    Returns:
        LinkedInOnlyResponse with LinkedIn URLs only, or LinkedInErrorResponse on failure
    """
    try:
        website = normalize_url(website)
    except ValueError as e:
        return LinkedInErrorResponse(website=website, error=str(e), status="error")

    # 1. Check LinkedIn-only cache (separate from full contact cache)
    cache_key = f"linkedin:{website}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            print(f"[LinkedIn Cache] Found existing LinkedIn info for {website}")
            cached_data = json.loads(cached)
            return LinkedInOnlyResponse(
                website=website,
                company_linkedin=cached_data.get("company_linkedin", []),
                personal_linkedin=cached_data.get("personal_linkedin", []),
                status="success",
            )
    except Exception as e:
        print(f"[!] Error retrieving from LinkedIn cache: {e}")

    try:
        # 2. Scrape homepage only
        print(f"[LinkedIn Scraper] Fetching homepage: {website}")
        html = fetch_page(website)
        if not html:
            raise Exception("Failed to fetch homepage")

        print(f"[LinkedIn Scraper] Homepage fetched successfully")

        # 3. Extract LinkedIn URLs only (no emails, no phones)
        linkedin_urls = extract_linkedin_urls(html)

        company_count = len(linkedin_urls.get("company", []))
        personal_count = len(linkedin_urls.get("personal", []))
        print(
            f"[LinkedIn Scraper] Found {company_count} company LinkedIn URL(s), "
            f"{personal_count} personal LinkedIn URL(s)"
        )

        company_urls = linkedin_urls.get("company", [])
        personal_urls = linkedin_urls.get("personal", [])

        # 4. Handle no LinkedIn URLs found
        if not company_urls and not personal_urls:
            print(f"[LinkedIn Scraper] No LinkedIn URLs found on {website}")
            result = LinkedInOnlyResponse(
                website=website,
                company_linkedin=[],
                personal_linkedin=[],
                status="no_contacts_found",
            )
            # Cache the empty result to avoid re-scraping
            try:
                cache_data = {
                    "company_linkedin": [],
                    "personal_linkedin": [],
                }
                redis_client.setex(
                    cache_key, settings.cache_ttl, json.dumps(cache_data)
                )
                print(f"[LinkedIn Cache] Saved empty result for {website}")
            except Exception as e:
                print(f"[!] Error saving to LinkedIn cache: {e}")
            return result

        # 5. Save to LinkedIn-only cache and return (no AI validation needed)
        print(f"[LinkedIn Cache] Saving LinkedIn URLs to cache for {website}")
        try:
            cache_data = {
                "company_linkedin": company_urls,
                "personal_linkedin": personal_urls,
            }
            redis_client.setex(cache_key, settings.cache_ttl, json.dumps(cache_data))
            print(f"[LinkedIn Cache] Saved to cache with TTL: {settings.cache_ttl}s")
        except Exception as e:
            print(f"[!] Error saving to LinkedIn cache: {e}")

        return LinkedInOnlyResponse(
            website=website,
            company_linkedin=company_urls,
            personal_linkedin=personal_urls,
            status="success",
        )

    except Exception as e:
        error_message = str(e)
        print(f"[!] Error scraping LinkedIn from {website}: {error_message}")
        return LinkedInErrorResponse(
            website=website, error=error_message, status="error"
        )
