"""
URL-related utility functions.
"""

from typing import Set
import httpx
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def normalize_url(url: str) -> str:
    """
    Normalize URL by removing fragments and normalizing other components.

    This helps prevent duplicate cache entries for essentially the same page.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL
    """
    try:
        # Parse the URL
        parsed = httpx.URL(url)

        # Remove fragment
        normalized = str(parsed.copy_with(fragment=""))

        return normalized
    except Exception:
        # If parsing fails, return the original URL
        return url


def remove_tracking_params(url: str, tracking_params: Set[str] = None) -> str:
    """
    Remove common tracking parameters from URLs.

    Args:
        url: URL to clean
        tracking_params: Set of parameter names to remove, or None for defaults

    Returns:
        URL with tracking parameters removed
    """
    if tracking_params is None:
        tracking_params = {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "fbclid",
            "gclid",
            "msclkid",
            "ref",
            "source",
            "campaign",
        }

    try:
        # Parse the URL
        parsed = urlparse(url)

        # Parse the query parameters
        query_params = parse_qs(parsed.query)

        # Remove tracking parameters
        filtered_params = {
            k: v for k, v in query_params.items() if k not in tracking_params
        }

        # Rebuild the query string
        query_string = urlencode(filtered_params, doseq=True) if filtered_params else ""

        # Rebuild the URL
        clean_url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                query_string,
                parsed.fragment,
            )
        )

        return clean_url
    except Exception:
        # If parsing fails, return the original URL
        return url


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def github_url_to_raw(github_url: str) -> str:
    """
    Convert a GitHub URL (edit or blob) to its raw.githubusercontent.com equivalent.
    
    Args:
        github_url: A GitHub URL pointing to a file
        
    Returns:
        URL for the raw content version or original URL if not convertible
    """
    # Handle different GitHub URL patterns
    if "github.com" not in github_url:
        return github_url
        
    # Extract query parameters to preserve them
    url_parts = github_url.split('?', 1)
    base_url = url_parts[0]
    query = f"?{url_parts[1]}" if len(url_parts) > 1 else ""
    
    # Handle edit links
    if "/edit/" in base_url:
        # Convert /edit/ to /raw/
        raw_url = base_url.replace("/edit/", "/raw/")
        return raw_url + query
        
    # Handle blob links
    elif "/blob/" in base_url:
        # Replace github.com with raw.githubusercontent.com and /blob/ with /
        raw_url = base_url.replace("github.com", "raw.githubusercontent.com")
        raw_url = raw_url.replace("/blob/", "/")
        return raw_url + query
        
    return github_url


def is_github_url(url: str) -> bool:
    """
    Check if a URL is a GitHub URL pointing to a file.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is a GitHub file URL, False otherwise
    """
    return "github.com" in url and ("/blob/" in url or "/edit/" in url)
