"""Web scraping utility functions."""
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Optional


def normalize_url(url: str) -> str:
    """
    Normalize a URL to a consistent format.
    
    Args:
        url: Raw URL string
        
    Returns:
        Normalized URL string
        
    Raises:
        ValueError: If URL is invalid
    """
    url = url.strip()

    # If no scheme, add http
    # Always convert to http://
    if url.startswith("https://"):
        url = "http://" + url[len("https://") :]
    elif not url.startswith("http://"):
        url = "http://" + url

    parsed = urlparse(url)

    # Ensure netloc (domain) exists
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    # Normalize www
    netloc = parsed.netloc.lower()
    # Example: remove "www." for consistency
    if netloc.startswith("www."):
        netloc = netloc[4:]

    normalized = f"{parsed.scheme}://{netloc}{parsed.path}".rstrip("/")
    return normalized


def fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch a webpage with timeout and error handling.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        HTML content as string, or None if fetch failed
    """
    try:
        res = requests.get(
            url, 
            timeout=timeout, 
            headers={"User-Agent": "Mozilla/5.0"}
        )
        res.raise_for_status()
        return res.text
    except Exception as e:
        print(f"[!] Error fetching {url}: {e}")
        return None


def extract_emails(html: str) -> list[str]:
    """
    Extract email addresses from HTML text.
    
    Args:
        html: HTML content
        
    Returns:
        List of unique email addresses
    """
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, html)))


def extract_phones(html: str) -> list[str]:
    """
    Extract phone numbers from visible text only.
    
    Args:
        html: HTML content
        
    Returns:
        List of unique phone numbers
    """
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    phone_regex = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")
    return list(set(phone_regex.findall(text)))


def extract_links(html: str, base_url: str) -> list[str]:
    """
    Extract internal links from HTML.
    
    Args:
        html: HTML content
        base_url: Base URL for resolving relative links
        
    Returns:
        List of unique internal links
    """
    soup = BeautifulSoup(html, "html.parser")
    links = []
    base_domain = base_url.split("//")[1].split("/")[0]
    
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if base_domain in href:
            links.append(href)
            
    return list(set(links))


def extract_linkedin_urls(html: str) -> dict[str, list[str]]:
    """
    Extract LinkedIn URLs from HTML content.
    Prioritizes company pages over personal profiles.
    
    Args:
        html: HTML content
        
    Returns:
        Dictionary with 'company' and 'personal' keys containing lists of LinkedIn URLs
    """
    company_urls = []
    personal_urls = []
    
    # Regex patterns for LinkedIn URLs
    company_pattern = r'https?://(?:www\.)?linkedin\.com/company/[a-zA-Z0-9_-]+'
    personal_pattern = r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+'
    
    # Find all LinkedIn URLs in HTML (including href attributes and plain text)
    soup = BeautifulSoup(html, "html.parser")
    
    # Extract from href attributes
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "linkedin.com/company/" in href:
            match = re.search(company_pattern, href)
            if match:
                company_urls.append(match.group(0))
        elif "linkedin.com/in/" in href:
            match = re.search(personal_pattern, href)
            if match:
                personal_urls.append(match.group(0))
    
    # Extract from plain text
    text_content = str(soup)
    company_urls.extend(re.findall(company_pattern, text_content))
    personal_urls.extend(re.findall(personal_pattern, text_content))
    
    # Remove duplicates and normalize
    company_urls = list(set(url.rstrip('/') for url in company_urls))
    personal_urls = list(set(url.rstrip('/') for url in personal_urls))
    
    return {
        "company": company_urls,
        "personal": personal_urls
    }
