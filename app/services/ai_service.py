"""AI-powered services using OpenAI for contact validation and page detection."""

import json
from typing import Optional
from urllib.parse import urljoin

from openai import OpenAI

from app.core.config import get_settings

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout)


def find_contact_page(base_url: str, links: list[str]) -> Optional[str]:
    """
    Use GPT to find the most likely contact page URL from a list of links.

    Args:
        base_url: The base website URL
        links: List of internal links to analyze

    Returns:
        Contact page URL if found, None otherwise
    """
    limited_links = links[:20]  # Limit to save tokens

    prompt = f"""Given the following list of internal website links and the base URL, identify the most likely contact page URL.
Base URL: {base_url}
Internal Links: {json.dumps(limited_links, indent=2)}
Return ONLY a JSON response in this exact format with no additional text: {{"most_likely_contact_page": "URL_HERE"}}
The contact page could be named: contact, contact-us, contactez-nous, contattaci, kontakt, contato, contacto, about, reach-us, get-in-touch, etc.
If no contact page is found, return null.
"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=settings.openai_timeout,
        )

        content = json.loads(response.choices[0].message.content.strip())
        contact_page = content.get("most_likely_contact_page")

        # Convert relative URL to absolute if not null
        if contact_page and contact_page.lower() != "null":
            return urljoin(base_url, contact_page)

    except Exception as e:
        print(f"[!] Error finding contact page: {e}")

    return None


def validate_contacts(
    emails: list[str],
    phones: list[str],
    linkedin_urls: Optional[dict[str, list[str]]] = None,
    validate_linkedin: bool = False,
) -> dict[str, list[str]]:
    """
    Validate extracted emails, phones, and optionally LinkedIn URLs using GPT.

    Args:
        emails: List of extracted email addresses
        phones: List of extracted phone numbers
        linkedin_urls: Dictionary with 'company' and 'personal' LinkedIn URLs
        validate_linkedin: Whether to use AI to validate LinkedIn URLs

    Returns:
        Dictionary with 'valid_email', 'valid_phones', and 'valid_linkedin_urls' keys
    """
    # Deduplicate and normalize
    emails = list(set([e.strip().lower() for e in emails]))
    phones = list(set([p.strip() for p in phones]))

    # Build prompt based on whether LinkedIn validation is requested
    if validate_linkedin and linkedin_urls:
        prompt = f"""Validate the following extracted contact information.
Return ONLY valid contact information in JSON format.

Emails: {json.dumps(emails, indent=2)}
Phones: {json.dumps(phones, indent=2)}
LinkedIn URLs: {json.dumps(linkedin_urls, indent=2)}

Return ONLY this JSON structure with no additional text:
{{
  "valid_email": ["email1@domain.com", "email2@domain.com"],
  "valid_phones": ["+1 202 555 0185", "123-456-7890"],
  "valid_linkedin_urls": {{
    "company": ["https://linkedin.com/company/example"],
    "personal": ["https://linkedin.com/in/john-doe"]
  }}
}}

For phone numbers:
- Include numbers that look like real phone numbers (7-15 digits)
- Preserve formatting including "+" if present
- Prefer international numbers first

For LinkedIn URLs:
- Only include valid, accessible LinkedIn URLs
- Remove broken or invalid URLs
- Keep company pages separate from personal profiles
"""
    else:
        prompt = f"""Validate the following extracted emails and phone numbers.
Return ONLY valid contact information in JSON format.

Emails: {json.dumps(emails, indent=2)}
Phones: {json.dumps(phones, indent=2)}

Return ONLY this JSON structure with no additional text:
{{
  "valid_email": ["email1@domain.com", "email2@domain.com"],
  "valid_phones": ["+1 202 555 0185", "123-456-7890"]
}}

For phone numbers:
- Include numbers that look like real phone numbers (7-15 digits)
- Preserve formatting including "+" if present
- Prefer international numbers first
"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=settings.openai_timeout,
        )

        validated = json.loads(response.choices[0].message.content.strip())

        # If LinkedIn validation was disabled but URLs were provided, add them back without validation
        if not validate_linkedin and linkedin_urls:
            validated["valid_linkedin_urls"] = linkedin_urls

        return validated

    except Exception as e:
        print(f"[!] Error validating contacts: {e}")
        result = {"valid_email": [], "valid_phones": []}
        if linkedin_urls:
            result["valid_linkedin_urls"] = linkedin_urls
        return result
