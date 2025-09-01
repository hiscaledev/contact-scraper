import json
import os
from urllib.parse import urljoin
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GPT_MODEL = "gpt-4.1-mini"


def find_contact_page(base_url: str, links: list[str]) -> dict:
    """
    Ask GPT to find the most likely contact page URL.
    If not found, return null.
    """
    limited_links = links[:20]  # Limit to save tokens
    prompt = f"""Given the following list of internal website links and the base URL, identify the most likely contact page URL. 
Base URL: {base_url} 
Internal Links: {json.dumps(limited_links, indent=2)} 
Return ONLY a JSON response in this exact format with no additional text: {{"most_likely_contact_page": "URL_HERE"}} 
The contact page could be named: contact, contact-us, contactez-nous, contattaci, kontakt, contato, contacto, about, reach-us, get-in-touch, etc. 
If no contact page is found, return null.
"""

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    try:
        content = json.loads(response.choices[0].message.content.strip())
        contact_page = content.get("most_likely_contact_page")
    except Exception:
        return None

    # Convert relative URL to absolute if not null
    if contact_page and not contact_page.lower() == "null":
        contact_page = urljoin(base_url, contact_page)
    else:
        contact_page = None

    return contact_page


def validate_contacts(emails: list[str], phones: list[str]) -> dict:
    """
    Validate extracted emails and phones with GPT.
    Returns ONLY valid emails and phones.
    """
    # Deduplicate
    emails = list(set([e.strip().lower() for e in emails]))
    phones = list(set([p.strip() for p in phones]))

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

    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    try:
        return json.loads(response.choices[0].message.content.strip())
    except Exception:
        return {"valid_email": [], "valid_phones": []}
