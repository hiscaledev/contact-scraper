import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.parse import urlparse


def normalize_url(url: str) -> str:
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


def fetch_page(url: str):
    """Fetch a page with timeout and error handling."""
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        res.raise_for_status()
        return res.text
    except Exception as e:
        print(f"[!] Error fetching {url}: {e}")
        return None


def extract_emails(html: str):
    """Extract emails from HTML text."""
    return list(
        set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html))
    )


def extract_phones(html: str):
    """Extract phone numbers from visible text only."""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    phone_regex = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")
    return list(set(phone_regex.findall(text)))


def extract_links(html: str, base_url: str):
    """Extract internal links."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if base_url.split("//")[1].split("/")[0] in href:
            links.append(href)
    return list(set(links))
