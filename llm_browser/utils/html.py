"""
HTML handling and conversion utilities.
"""

import re
from typing import Optional, List, Dict, Tuple

from bs4 import BeautifulSoup
from markdownify import markdownify as md


def html_to_markdown(html_content: str, content_priority: str = "auto") -> str:
    """
    Convert HTML content to markdown format using markdownify with enhanced features.

    This uses a specialized library for better conversion quality with additional
    content filtering and formatting improvements.

    Args:
        html_content: HTML content to convert
        content_priority: Content extraction strategy ("auto", "main", "article", "largest", "dense")
          - auto: Intelligently selects the best strategy based on page structure
          - main: Prioritizes content in <main> tags (good for modern websites)
          - article: Prioritizes content in <article> tags (good for blogs, news)
          - largest: Prioritizes the largest content block by text size (good for legacy sites)
          - dense: Prioritizes the densest content area (text vs HTML ratio) (good for text-heavy sites)
          
        Note: When navigating between pages or traversing website structures, use include_navigation=True

    Returns:
        Markdown representation of the HTML content
    """
    try:
        # Extract main content based on the specified priority
        main_content_html = extract_main_content(
            html_content, 
            content_priority=content_priority
        )
        
        # Parse with BeautifulSoup for preprocessing
        soup = BeautifulSoup(main_content_html, "html.parser")
        
        # Filter out binary images (images with data URLs containing binary data)
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src.startswith("data:image/") and any(enc in src for enc in [";base64,", "%"]):
                # Replace with alt text or remove if no alt text
                alt_text = img.get("alt", "")
                if alt_text:
                    # Create a text node with the alt text
                    new_text = soup.new_string(f"[Image: {alt_text}]")
                    img.replace_with(new_text)
                else:
                    # Just remove the image if no alt text
                    img.decompose()
        
        # Enhance code blocks with proper formatting and language hints
        for pre in soup.find_all("pre"):
            # Check if there's a code element inside
            code = pre.find("code")
            if code:
                # Try to determine language from class
                language = ""
                if code.get("class"):
                    for class_name in code.get("class"):
                        if class_name.startswith(("language-", "lang-")):
                            language = class_name.split("-")[1]
                            break
                
                # Format according to CommonMark/GFM style
                if language:
                    # Add data attribute for markdownify to recognize
                    pre["data-language"] = language
                    
                # Make sure pre block will have proper newlines
                if not code.text.endswith("\n"):
                    code.append("\n")
        
        # Enhance tables for better rendering
        for table in soup.find_all("table"):
            # Add a class for markdownify to recognize
            table["class"] = table.get("class", []) + ["markdown-table"]
            
            # Make sure there are headers
            if not table.find("thead"):
                # If no thead but has rows, convert first row to thead
                tbody = table.find("tbody")
                if tbody and tbody.find("tr"):
                    first_row = tbody.find("tr")
                    # Create thead and append the first row
                    thead = soup.new_tag("thead")
                    thead.append(first_row.extract())
                    table.insert(0, thead)
            
            # Convert td to th in the thead
            thead = table.find("thead")
            if thead:
                for td in thead.find_all("td"):
                    th = soup.new_tag("th")
                    th.string = td.get_text()
                    td.replace_with(th)
        
        # Convert to markdown with markdownify with improved settings
        markdown_options = {
            "heading_style": "ATX",  # Use # style headings
            "strong_em_symbol": "*",  # Use * for emphasis
            "strip": ["script", "style", "meta"],
            "bullets": "-",  # Use - for bullet points
            "code_language_callback": lambda el: el.get("data-language", ""),
        }
        
        markdown_content = md(str(soup), **markdown_options)
        
        # Post-process the markdown to improve formatting
        # Fix code blocks - make sure they have proper spacing
        markdown_content = re.sub(r"```(\w*)\n+", r"```\1\n", markdown_content)
        markdown_content = re.sub(r"\n+```", r"\n```", markdown_content)
        
        # Fix lists - ensure proper spacing
        markdown_content = re.sub(r"(\n- .*?\n)(?!\n|$|- )", r"\1\n", markdown_content)
        
        # Remove excessive blank lines
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)
        
        # Fix reference-style links
        markdown_content = re.sub(r"\[([^\]]+)\]\[([^\]]+)\]", r"[\1](\2)", markdown_content)
        
        return markdown_content
    except Exception as e:
        # Fallback to basic conversion if markdownify fails
        print(f"Enhanced markdown conversion failed: {e}")
        
        try:
            # Try standard markdownify as first fallback
            soup = BeautifulSoup(html_content, "html.parser")
            for tag in soup(["script", "style", "meta", "noscript", "iframe"]):
                tag.decompose()
                
            return md(str(soup), heading_style="ATX")
        except Exception:
            # Basic text extraction as ultimate fallback
            soup = BeautifulSoup(html_content, "html.parser")
            for tag in soup(["script", "style", "meta", "noscript", "iframe"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            return text


def extract_main_content(html: str, content_priority: str = "auto") -> str:
    """
    Extract the main content from an HTML document with configurable priority.

    Uses advanced heuristics to find the main content area of a page,
    with support for different extraction strategies.

    Args:
        html: Raw HTML content
        content_priority: Content extraction mode ("auto", "main", "article", "largest", "dense")

    Returns:
        HTML string of just the main content
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove clearly unwanted elements
    for tag in soup(["script", "style", "meta", "noscript", "iframe"]):
        tag.decompose()
    
    # Identify and mark navigation elements but don't remove them yet
    navigation_elements = []
    for nav in soup.find_all("nav"):
        navigation_elements.append(nav)
    
    # Identify and mark header/footer elements but don't remove them yet
    structural_elements = []
    for tag in soup.find_all(["header", "footer"]):
        structural_elements.append(tag)
    
    # Try to identify ad containers and comment sections
    noise_elements = []
    ad_selectors = [
        ".ad", ".ads", ".advertisement", ".banner", 
        "#ad", "#ads", "#advertisement",
        '[id*="google_ads"]', '[class*="banner"]', '[id*="banner"]',
        '[class*="advert"]', '[id*="advert"]'
    ]
    
    comment_selectors = [
        "#comments", ".comments", ".comment-section", ".user-comments",
        '[id*="comment"]', '[class*="comment"]', ".discussion", "#discussion"
    ]
    
    for selector in ad_selectors + comment_selectors:
        for element in soup.select(selector):
            noise_elements.append(element)
    
    # Store potential content sections with heuristic scores
    content_candidates = []
    
    # Check explicit semantic elements
    main_element = soup.find("main")
    if main_element:
        content_candidates.append((main_element, 100, "main"))
    
    article_elements = soup.find_all("article")
    for article in article_elements:
        # Give preference to longer articles
        article_score = 90 + min(10, len(article.get_text(strip=True)) / 1000)
        content_candidates.append((article, article_score, "article"))
    
    # Check common content selectors
    for selector, score in [
        ("#content", 80),
        (".content", 75),
        ("#main", 70),
        (".main", 65),
        ('[role="main"]', 60),
        (".post", 55),
        (".entry", 50),
        (".blog-post", 50),
        (".page-content", 48),
        (".site-content", 45),
        (".markdown-body", 95),  # GitHub's content class, high score
    ]:
        for element in soup.select(selector):
            # Skip very small elements
            if len(element.get_text(strip=True)) < 100:
                continue
            
            # Skip elements that are clearly not main content 
            if any(ancestor.name in ["nav", "header", "footer"] for ancestor in element.parents):
                continue
                
            content_candidates.append((element, score, selector))
    
    # If we have fewer than 3 candidates or in "largest" or "dense" mode,
    # analyze content relevance by text density and element size
    if content_priority in ["largest", "dense"] or len(content_candidates) < 3:
        # Find divs, sections and other containers with significant content
        for tag_name in ["div", "section", "main", "td", "table"]:
            for element in soup.find_all(tag_name):
                # Skip small elements, navigation, headers, footers
                if (len(element.get_text(strip=True)) < 200 or
                    element in navigation_elements or 
                    element in structural_elements or
                    element in noise_elements):
                    continue
                    
                # Calculate content metrics
                text_length = len(element.get_text(strip=True))
                link_count = len(element.find_all("a"))
                element_html_length = len(str(element))
                
                # Skip if the element is too small
                if element_html_length < 500:
                    continue
                
                # Calculate element text density (text length vs HTML size)
                text_density = text_length / element_html_length if element_html_length > 0 else 0
                
                # Calculate text-to-link ratio (to distinguish content from navigation)
                if link_count > 0:
                    text_to_link_ratio = text_length / link_count
                else:
                    text_to_link_ratio = text_length * 0.5  # Penalty for no links
                
                # Combine metrics with variable weight based on priority mode
                if content_priority == "largest":
                    # Prioritize size over density
                    score = (text_length * 0.6) + (text_density * 20) + (text_to_link_ratio * 0.1)
                elif content_priority == "dense":
                    # Prioritize density over size
                    score = (text_density * 50) + (text_to_link_ratio * 0.2) + (text_length * 0.01)
                else:
                    # Balanced approach
                    score = (text_length * 0.3) + (text_density * 30) + (text_to_link_ratio * 0.15)
                
                # Normalize score to be comparable with selector-based scores
                normalized_score = min(40, score / 50)
                content_candidates.append((element, normalized_score, f"{tag_name}-heuristic"))
    
    # Apply content priority strategy
    if content_priority == "main" and main_element:
        selected_content = main_element
    elif content_priority == "article" and article_elements:
        # Find the largest article if there are multiple
        selected_content = max(article_elements, key=lambda x: len(x.get_text(strip=True)))
    elif content_candidates:
        # Sort by score in descending order
        content_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Get the highest-scoring element
        selected_content = content_candidates[0][0]
        
        # For debugging 
        # top_candidates = content_candidates[:3]
        # print(f"Selected content: {top_candidates[0][2]} (score: {top_candidates[0][1]:.2f})")
        # for i, (_, score, name) in enumerate(top_candidates[1:], 2):
        #     print(f"Candidate {i}: {name} (score: {score:.2f})")
    else:
        # Fallback to body without navigation elements
        for nav in navigation_elements:
            nav.decompose()
        for elem in structural_elements:
            elem.decompose()
        for elem in noise_elements:
            elem.decompose()
        selected_content = soup.body or soup
    
    # Remove navigation, header, footer, and ads from the selected content
    result_soup = BeautifulSoup(str(selected_content), "html.parser")
    
    # Remove obvious non-content elements from the selected content
    for selector in [
        "nav", "header", "footer", "aside", ".sidebar", "#sidebar",
        *ad_selectors, *comment_selectors
    ]:
        for element in result_soup.select(selector):
            element.decompose()
    
    return str(result_soup)


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
            elif "/tree/" in href:
                link_data["is_github_tree"] = True
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
    
    # First, look for GitHub edit/blob/tree links that explicitly mention editing
    for link in links:
        if (link["is_github_edit"] or link["is_github_blob"] or link.get("is_github_tree", False)) and link["is_edit_link"]:
            return link
    
    # Next, look for any GitHub edit/blob/tree links
    for link in links:
        if link["is_github_edit"] or link["is_github_blob"] or link.get("is_github_tree", False):
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
