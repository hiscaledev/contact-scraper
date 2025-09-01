from scraper.db import get_contact_from_db, save_contact_to_db
from scraper.utils import (
    normalize_url,
    fetch_page,
    extract_emails,
    extract_phones,
    extract_links,
)
from scraper.ai import find_contact_page, validate_contacts


def scrape_website(website: str, sheet_name="default"):
    website = normalize_url(website)

    # 1. Check DB
    existing = get_contact_from_db(website)
    if existing:
        print("[DB] Found existing contact info.")
        return existing

    try:
        print(f"[1] Scraping homepage: {website}")
        html = fetch_page(website)
        if not html:
            raise Exception("Failed to fetch homepage")

        emails = extract_emails(html)
        phones = extract_phones(html)
        links = extract_links(html, website)
        print(f"    Found {len(emails)} emails, {len(phones)} phones")

        # 2. Find contact page
        contact_page = find_contact_page(website, links)
        if contact_page and contact_page != website:
            print(f"    Contact page found: {contact_page}")
            c_html = fetch_page(contact_page)
            if c_html:
                emails += extract_emails(c_html)
                phones += extract_phones(c_html)

        if not emails and not phones:
            print("    No emails or phones found. Skipping validation and DB save.")
            return {
                "website": website,
                "email1": None,
                "email2": None,
                "phone1": None,
                "phone2": None,
                "status": "no_contacts_found",
            }
        
        # 3. Validate
        print("    validating contacts...")
        validation = validate_contacts(emails, phones)
        valid_emails = validation["valid_email"]
        valid_phones = validation["valid_phones"]

        email1 = valid_emails[0] if valid_emails else None
        email2 = valid_emails[1] if len(valid_emails) > 1 else None
        phone1 = valid_phones[0] if valid_phones else None
        phone2 = valid_phones[1] if len(valid_phones) > 1 else None

        # 4. Save Success
        print("    saving to DB...")
        save_contact_to_db(sheet_name, website, email1, email2, phone1, phone2)
        return {
            "website": website,
            "email1": email1,
            "email2": email2,
            "phone1": phone1,
            "phone2": phone2,
            "status": "success",
        }

    except Exception as e:
        error_message = str(e)
        print(f"[!] Error scraping {website}: {error_message}")
        return {"website": website, "error": error_message, "status": "error"}
