"""
MCP server implementation for LLM Browser.
"""

from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

from llm_browser.config import BrowserConfig
from llm_browser.models import Database
from llm_browser.utils.grep import GrepOptions, grep_content
from llm_browser.utils.html import html_to_markdown, extract_title
from llm_browser.utils.url import normalize_url, is_valid_url


class BrowserServer:
    """MCP server for LLM Browser."""

    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        Initialize the browser server.

        Args:
            config: Browser configuration or None to use defaults
        """
        self.config = config or BrowserConfig()
        self.db = Database(self.config.db_path)
        self.mcp = FastMCP("web_browser")

        # Register MCP tools
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all MCP tools."""

        @self.mcp.tool()
        async def browse_url(
            url: str,
            grep_pattern: Optional[str] = None,
            context_lines: int = 0,
            invert_match: bool = False,
            show_line_numbers: bool = False,
            whole_words: bool = False,
        ) -> str:
            """
            Fetch a webpage and convert it to markdown, optionally filtering with grep-like functionality.

            Args:
                url: The URL to fetch
                grep_pattern: Optional regex pattern to filter content
                context_lines: Number of lines to show before and after matches (like grep -C)
                invert_match: If True, show non-matching lines (like grep -v)
                show_line_numbers: If True, show line numbers with results (like grep -n)
                whole_words: If True, match whole words only (like grep -w)
            """
            # Validate URL
            if not is_valid_url(url):
                return f"Invalid URL: {url}"

            # Normalize the URL before checking cache
            normalized_url = normalize_url(url)

            # Check cache first
            cached = self.db.get_cached_content(normalized_url)

            if cached:
                content = cached["markdown_content"]
                source = "cache"
            else:
                # Fetch and process if not in cache
                html_content = await self._fetch_url(url)
                if not html_content:
                    return f"Failed to fetch content from {url}"

                # Extract title
                title = extract_title(html_content) or url

                # Convert to markdown
                markdown_content = html_to_markdown(html_content)

                # Add title to the markdown
                content = f"# {title}\n\n{markdown_content}"

                # Cache the results with normalized URL
                self.db.cache_content(normalized_url, html_content, content)

                source = "web"

            # Apply grep filtering if pattern provided
            if grep_pattern:
                options = GrepOptions(
                    pattern=grep_pattern,
                    context_lines=context_lines,
                    invert_match=invert_match,
                    show_line_numbers=show_line_numbers,
                    whole_words=whole_words,
                )

                filtered_content = grep_content(
                    content,
                    grep_pattern,
                    context_lines=context_lines,
                    invert_match=invert_match,
                    show_line_numbers=show_line_numbers,
                    whole_words=whole_words,
                )

                options_str = options.to_cli_flags()
                if options_str:
                    options_str = f" with options: {options_str}"

                return f"### Content from {url} (source: {source}, filtered by: '{grep_pattern}'{options_str})\n\n{filtered_content}"

            return f"### Content from {url} (source: {source})\n\n{content}"

        @self.mcp.tool()
        async def search_cached_content(
            grep_pattern: str,
            context_lines: int = 0,
            invert_match: bool = False,
            show_line_numbers: bool = False,
            whole_words: bool = False,
        ) -> str:
            """
            Search all cached pages for content matching the grep pattern.

            Args:
                grep_pattern: Regex pattern to search for across all cached content
                context_lines: Number of lines to show before and after matches (like grep -C)
                invert_match: If True, show non-matching lines (like grep -v)
                show_line_numbers: If True, show line numbers with results (like grep -n)
                whole_words: If True, match whole words only (like grep -w)
            """
            stats = self.db.get_cache_stats()

            if stats["count"] == 0:
                return "No cached content available to search."

            options = GrepOptions(
                pattern=grep_pattern,
                context_lines=context_lines,
                invert_match=invert_match,
                show_line_numbers=show_line_numbers,
                whole_words=whole_words,
            )

            with self.db.get_session() as session:
                # Get all cache entries
                from llm_browser.models import WebCache

                cache_entries = session.query(WebCache).all()

            matched_results = []

            for entry in cache_entries:
                filtered_content = grep_content(
                    entry.markdown_content,
                    grep_pattern,
                    context_lines=context_lines,
                    invert_match=invert_match,
                    show_line_numbers=show_line_numbers,
                    whole_words=whole_words,
                )

                if filtered_content and "No content matching" not in filtered_content:
                    # Truncate to first 10 matching lines to avoid overwhelming results
                    lines = filtered_content.split("\n")[:10]
                    preview = "\n".join(lines)
                    if len(lines) >= 10:
                        preview += "\n...(more results truncated)..."

                    matched_results.append(f"### URL: {entry.url}\n{preview}\n")

            options_str = options.to_cli_flags()
            if options_str:
                options_str = f" with options: {options_str}"

            if matched_results:
                return (
                    f"### Search Results for '{grep_pattern}'{options_str}:\n\n"
                    + "\n".join(matched_results)
                )
            else:
                return f"No content matching '{grep_pattern}' found in the cache."

        @self.mcp.tool()
        def clear_cache() -> str:
            """
            Clear the entire web browsing cache.

            Returns:
                Confirmation message
            """
            count = self.db.clear_cache()
            return f"Cache cleared successfully. {count} entries removed."

        @self.mcp.tool()
        def get_cache_stats() -> str:
            """
            Get statistics about the cache.

            Returns:
                Formatted string with cache statistics
            """
            stats = self.db.get_cache_stats()

            oldest_entry = "N/A"
            if stats["oldest_entry_time"]:
                hours_old = (stats["current_time"] - stats["oldest_entry_time"]) // 3600
                oldest_entry = f"{hours_old} hours old"

            newest_entry = "N/A"
            if stats["newest_entry_time"]:
                hours_old = (stats["current_time"] - stats["newest_entry_time"]) // 3600
                newest_entry = f"{hours_old} hours old"

            result = f"""
Cache Statistics:
- Database location: {self.config.db_path}
- Total pages cached: {stats["count"]}
- Total cache size: {stats["size_kb"]} KB
- Oldest cache entry: {oldest_entry}
- Newest cache entry: {newest_entry}
- Recent URLs:
"""

            if not stats["recent_urls"]:
                result += "  - None\n"
            else:
                for url in stats["recent_urls"]:
                    result += f"  - {url}\n"

            result += (
                "\nNote: Cache entries are kept indefinitely until manually cleared."
            )

            return result

    async def _fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch content from a URL with proper error handling.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None if fetch failed
        """
        headers = {
            "User-Agent": self.config.user_agent,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, headers=headers, timeout=30.0, follow_redirects=True
                )
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def run(self, transport: str = "stdio") -> None:
        """
        Run the MCP server.

        Args:
            transport: Transport to use ('stdio' or 'http')
        """
        self.mcp.run(transport=transport)


def create_server(config: Optional[BrowserConfig] = None) -> BrowserServer:
    """
    Create and configure a browser server instance.

    Args:
        config: Optional configuration

    Returns:
        Configured BrowserServer instance
    """
    return BrowserServer(config)
