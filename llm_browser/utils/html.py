"""
HTML handling and conversion utilities.
"""

import re
from typing import Optional, List

from bs4 import BeautifulSoup
from markdownify import markdownify as md


def html_to_markdown(html_content: str) -> str:
    """
    Convert HTML content to markdown format using markdownify.

    This uses a specialized library for better conversion quality.

    Args:
        html_content: HTML content to convert

    Returns:
        Markdown representation of the HTML content
    """
    try:
        # Parse with BeautifulSoup first to clean up the HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove unwanted elements
        for tag in soup(
            ["script", "style", "meta", "noscript", "iframe", "nav", "footer"]
        ):
            tag.decompose()

        # Try to identify main content
        main_content = None
        for selector in ["main", "article", "#content", ".content", '[role="main"]']:
            main_content = soup.select_one(selector)
            if main_content:
                break

        # If no main content found, use body
        if not main_content:
            main_content = soup.body

        # If still nothing found, use the entire document
        if not main_content:
            main_content = soup

        # Convert to markdown with markdownify
        markdown_content = md(str(main_content), heading_style="ATX")

        # Post-process the markdown to improve formatting
        # Remove excessive blank lines
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        return markdown_content
    except Exception as e:
        # Fallback to basic conversion if markdownify fails
        print(f"Markdownify conversion failed: {e}")

        # Basic fallback conversion
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "meta", "noscript", "iframe"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        return text


def extract_main_content(html: str) -> str:
    """
    Extract the main content from an HTML document.

    Uses heuristics to find the main content area of a page.

    Args:
        html: Raw HTML content

    Returns:
        HTML string of just the main content
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted elements
    for tag in soup(
        ["script", "style", "meta", "noscript", "iframe", "nav", "footer", "header"]
    ):
        tag.decompose()

    # Try different selectors for main content
    selectors = [
        "main",
        "article",
        "#content",
        ".content",
        ".main",
        "#main",
        '[role="main"]',
        ".post",
        ".entry",
        ".blog-post",
    ]

    for selector in selectors:
        content = soup.select_one(selector)
        if content and len(content.get_text(strip=True)) > 100:
            return str(content)

    # If no suitable element found, use the body
    return str(soup.body or soup)


def extract_title(html: str) -> Optional[str]:
    """
    Extract the title from an HTML document.

    Args:
        html: Raw HTML content

    Returns:
        Page title or None if not found
    """
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")

    if title_tag:
        return title_tag.get_text(strip=True)

    # Try h1 if no title tag
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    return None


def extract_links(html: str) -> List[dict]:
    """
    Extract all links from an HTML document.

    Args:
        html: Raw HTML content

    Returns:
        List of dictionaries with href and text for each link
    """
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = a_tag.get_text(strip=True)

        if href and text and not href.startswith("javascript:"):
            links.append({"href": href, "text": text})

    return links
