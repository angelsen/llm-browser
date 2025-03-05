"""
HTML handling and conversion utilities.
"""

import re
from typing import Optional, List, Dict, Tuple

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


def extract_links_enhanced(html: str) -> List[Dict]:
    """
    Extract all links from an HTML document with enhanced metadata.

    Args:
        html: Raw HTML content

    Returns:
        List of dictionaries with href, text, and metadata for each link
    """
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = a_tag.get_text(strip=True)
        
        # Skip javascript links and empty links
        if not href or not text or href.startswith("javascript:"):
            continue
            
        # Create a dictionary with basic link info
        link_data = {
            "href": href,
            "text": text,
            "is_github": False,
            "is_github_edit": False,
            "is_github_blob": False,
            "raw_url": None,
            "attributes": {}
        }
        
        # Add all attributes
        for attr_name, attr_value in a_tag.attrs.items():
            if attr_name != "href":  # href is already included separately
                link_data["attributes"][attr_name] = attr_value
                
        # Check for GitHub links
        if "github.com" in href:
            link_data["is_github"] = True
            
            if "/edit/" in href:
                link_data["is_github_edit"] = True
                from llm_browser.utils.url import github_url_to_raw
                link_data["raw_url"] = github_url_to_raw(href)
            elif "/blob/" in href:
                link_data["is_github_blob"] = True
                from llm_browser.utils.url import github_url_to_raw
                link_data["raw_url"] = github_url_to_raw(href)
                
        # Check for common edit link texts
        edit_phrases = ["edit this page", "edit on github", "contribute to this page", "view source"]
        link_data["is_edit_link"] = any(phrase in text.lower() for phrase in edit_phrases)
            
        links.append(link_data)

    return links


def find_github_source_link(html: str) -> Optional[Dict]:
    """
    Find the most likely GitHub source link in an HTML document.
    
    Args:
        html: Raw HTML content
        
    Returns:
        Dictionary with link information or None if no suitable link found
    """
    links = extract_links_enhanced(html)
    
    # First, look for GitHub edit/blob links that explicitly mention editing
    for link in links:
        if (link["is_github_edit"] or link["is_github_blob"]) and link["is_edit_link"]:
            return link
    
    # Next, look for any GitHub edit/blob links
    for link in links:
        if link["is_github_edit"] or link["is_github_blob"]:
            return link
    
    # Finally, try any GitHub link
    for link in links:
        if link["is_github"]:
            return link
    
    return None


def extract_navigation(html: str) -> List[Dict]:
    """
    Extract navigation structures from HTML.
    
    Looks for common navigation patterns including:
    - <nav> elements
    - Lists of links (<ul>/<ol> with multiple <li><a> elements)
    - Elements with navigation-related classes
    
    Args:
        html: Raw HTML content
        
    Returns:
        List of dictionaries with navigation items and their structure
    """
    soup = BeautifulSoup(html, "html.parser")
    navigation_sections = []
    
    # Find explicit nav elements
    nav_elements = soup.find_all("nav")
    
    # Find elements with navigation-related classes
    nav_classes = ["menu", "navigation", "nav", "navbar", "sidebar", "toc", "table-of-contents"]
    class_nav_elements = []
    for cls in nav_classes:
        elements = soup.find_all(class_=lambda c: c and cls in c.lower())
        class_nav_elements.extend(elements)
    
    # Find lists that likely represent navigation
    list_elements = []
    for list_tag in soup.find_all(["ul", "ol"]):
        # Count links inside this list
        links = list_tag.find_all("a")
        if len(links) >= 3:  # Arbitrary threshold for navigation lists
            list_elements.append(list_tag)
    
    # Process all potential navigation elements
    for element in set(nav_elements + class_nav_elements + list_elements):
        # Extract navigation items with their hierarchy
        nav_structure = _extract_hierarchical_navigation(element)
        
        if nav_structure:  # Only add if we found navigation items
            # Try to determine a title for this navigation section
            title = _extract_navigation_title(element)
            
            navigation_sections.append({
                "title": title,
                "element_type": element.name,
                "classes": element.get("class", []),
                "items": nav_structure
            })
    
    return navigation_sections


def _extract_hierarchical_navigation(element) -> List[Dict]:
    """
    Extract navigation links from an element, preserving hierarchy.
    
    Args:
        element: BeautifulSoup element to extract navigation from
        
    Returns:
        List of navigation items with their hierarchical structure
    """
    items = []
    
    # Handle direct links in the element
    direct_links = element.find_all("a", href=True, recursive=False)
    for link in direct_links:
        items.append({
            "href": link["href"],
            "text": link.get_text(strip=True),
            "is_active": _has_active_marker(link),
            "level": 0
        })
    
    # Handle list items which may contain links
    list_items = element.find_all("li")
    for li in list_items:
        items.extend(_process_list_item(li))
    
    return items


def _process_list_item(li_element, level=0) -> List[Dict]:
    """
    Process a list item element to extract links and nested structures.
    
    Args:
        li_element: The list item element to process
        level: Current nesting level (for hierarchical navigation)
        
    Returns:
        List of navigation items from this list item and its children
    """
    items = []
    
    # Find direct links in this list item
    links = li_element.find_all("a", href=True, recursive=False)
    for link in links:
        items.append({
            "href": link["href"],
            "text": link.get_text(strip=True),
            "is_active": _has_active_marker(link),
            "level": level
        })
    
    # If no direct links, try one level deeper
    if not links:
        deeper_links = li_element.find_all("a", href=True, limit=1)
        for link in deeper_links:
            items.append({
                "href": link["href"],
                "text": link.get_text(strip=True),
                "is_active": _has_active_marker(link),
                "level": level
            })
    
    # Look for nested lists (submenus)
    nested_lists = li_element.find_all(["ul", "ol"], recursive=False)
    for nested_list in nested_lists:
        nested_items = nested_list.find_all("li")
        for nested_item in nested_items:
            items.extend(_process_list_item(nested_item, level=level+1))
            
    # Check for details/summary structures (common in modern navigation)
    details = li_element.find_all("details", recursive=False)
    for detail in details:
        # Extract the summary text (often the parent menu item)
        summary = detail.find("summary")
        if summary:
            summary_text = summary.get_text(strip=True)
            items.append({
                "text": summary_text,
                "is_category": True,
                "level": level
            })
        
        # Extract links within the details
        detail_lists = detail.find_all(["ul", "ol"])
        for detail_list in detail_lists:
            detail_items = detail_list.find_all("li")
            for detail_item in detail_items:
                items.extend(_process_list_item(detail_item, level=level+1))
    
    return items


def _has_active_marker(element) -> bool:
    """
    Check if an element has indicators of being the active/current page.
    
    Args:
        element: The element to check
        
    Returns:
        True if the element appears to be marked as active
    """
    # Check for common active classes
    active_classes = ["active", "current", "selected", "highlight"]
    classes = element.get("class", [])
    if any(cls in ' '.join(classes) or f"{cls}-item" in ' '.join(classes) for cls in active_classes):
        return True
    
    # Check for aria-current attribute
    if element.get("aria-current"):
        return True
    
    return False


def _extract_navigation_title(element) -> Optional[str]:
    """
    Try to find a title for the navigation element.
    
    Args:
        element: Navigation element
        
    Returns:
        Title string or None if no title found
    """
    # Try to find heading directly before the element
    prev_element = element.find_previous_sibling()
    while prev_element:
        if prev_element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            return prev_element.get_text(strip=True)
        prev_element = prev_element.find_previous_sibling()
    
    # Look for heading within the element (often in nav sections)
    heading = element.find(["h1", "h2", "h3", "h4", "h5", "h6"])
    if heading:
        return heading.get_text(strip=True)
    
    # Look for elements with title-like classes
    title_classes = ["title", "heading", "header", "nav-title"]
    for cls in title_classes:
        title_elem = element.find(class_=lambda c: c and cls in c.lower())
        if title_elem:
            return title_elem.get_text(strip=True)
    
    # Infer from element attributes or parent container
    if element.get("aria-label"):
        return element.get("aria-label")
    
    # If the element has an ID, use it as a fallback
    if element.get("id"):
        # Convert id like "main-navigation" to "Main Navigation"
        id_text = element.get("id").replace("-", " ").replace("_", " ")
        return id_text.title()
    
    return None


def format_navigation_as_markdown(navigation_sections: List[Dict]) -> str:
    """
    Format extracted navigation as a markdown document.
    
    Args:
        navigation_sections: List of navigation sections with their items
        
    Returns:
        Markdown representation of the navigation
    """
    if not navigation_sections:
        return ""
        
    markdown = "# Site Navigation\n\n"
    
    for section in navigation_sections:
        # Add section header
        title = section.get("title") or "Navigation"
        markdown += f"## {title}\n\n"
        
        # Add items
        for item in section["items"]:
            # Indent based on level
            indent = "  " * item.get("level", 0)
            
            # Format as category or link
            if item.get("is_category"):
                markdown += f"{indent}- **{item['text']}**\n"
            elif "href" in item:
                text = item["text"]
                href = item["href"]
                active_marker = " (current)" if item.get("is_active") else ""
                markdown += f"{indent}- [{text}]({href}){active_marker}\n"
            else:
                markdown += f"{indent}- {item['text']}\n"
        
        markdown += "\n"
    
    return markdown
