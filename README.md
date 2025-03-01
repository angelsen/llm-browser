# LLM Web Browser

A browser-like tool for LLMs that provides websites in markdown format with grep-like filtering capabilities and SQLite caching for improved performance.

## Features

- **Web to Markdown Conversion:** Converts websites to clean, readable markdown format
- **Advanced Grep-like Filtering:** Filter content with powerful pattern matching before sending to LLMs
- **Permanent SQLite Caching:** Cache websites for faster access and bandwidth conservation
- **MCP Integration:** Uses the Model Context Protocol to provide a standardized interface for LLMs
- **Platform-Appropriate Storage:** Stores cache in platform-standard locations

## Installation

```bash
git clone https://github.com/fredrikangelsen/llm-browser.git
cd llm-browser
uv tool install --editable .
```

## Usage

### Running the MCP Server

```bash
# Run the server with default settings
llm-browser server

# Specify a custom database location
llm-browser server --db-path /path/to/your/custom_cache.db
```

### Managing the Cache

```bash
# View cache statistics
llm-browser cache stats

# Clear the cache
llm-browser cache clear
```

### Using with LLMs

The browser provides the following MCP tools:

#### 1. browse_url

Fetches a webpage, converts it to markdown, and optionally filters with grep-like functionality.

```python
browse_url(
    url="https://example.com",
    grep_pattern="optional regex pattern",
    context_lines=2,         # Show 2 lines before and after matches
    invert_match=False,      # If True, show non-matching lines
    show_line_numbers=True,  # Show line numbers with results
    whole_words=False        # Match whole words only
)
```

#### 2. search_cached_content

Searches all cached pages for content matching a grep pattern with advanced filtering options.

```python
search_cached_content(
    grep_pattern="search term",
    context_lines=0,         # Number of context lines to show
    invert_match=False,      # If True, show non-matching lines
    show_line_numbers=False, # Show line numbers with results
    whole_words=False        # Match whole words only
)
```

#### 3. clear_cache

Manually clear the entire web browsing cache.

```python
clear_cache()
```

#### 4. get_cache_stats

Gets statistics about the cache, including location, size, and stored URLs.

```python
get_cache_stats()
```

## Technical Implementation Details

### URL Normalization

The tool normalizes URLs before caching to prevent duplicate entries by removing fragments and preserving the main URL structure.

### Database Implementation

The tool uses SQLAlchemy ORM for database interactions, with the database stored in platform-specific standard locations:

- **Linux**: `~/.local/share/llm-browser/web_cache.db`
- **macOS**: `~/Library/Application Support/llm-browser/web_cache.db`
- **Windows**: `%LOCALAPPDATA%\llm-browser\web_cache.db`

You can specify a custom database location by setting the environment variable `LLM_BROWSER_DB_PATH`.

### HTML to Markdown Conversion

The tool uses `markdownify` for high-quality HTML to Markdown conversion, maintaining formatting while focusing on the main content.

## Example Integration with Claude or Other LLMs

When integrating with Claude or other LLMs:

1. Run the web browser MCP server in one process
2. Connect your LLM client to the server
3. The LLM can then request web content through the MCP protocol

See the `examples` directory for detailed integration examples.

## Adding to Claude Code

You can add llm-browser as an MCP server to Claude Code:

```bash
# Start by installing the tool
git clone https://github.com/fredrikangelsen/llm-browser.git
cd llm-browser
uv tool install --editable .

# Add the MCP server to Claude Code
# Basic syntax (note the -- separator when using flags)
claude mcp add llm-browser -- llm-browser server

# With custom options (e.g., custom database path)
claude mcp add llm-browser -s global -- llm-browser server --db-path /custom/path/cache.db

# Verify it was added correctly
claude mcp list

# Use Claude Code with the browser tool
claude
```

The `-s global` flag stores the configuration globally rather than just for the current project.

Once added, Claude will have access to web browsing capabilities through these tools:
- `browse_url`: Fetch and convert webpages to markdown
- `search_cached_content`: Search across all cached webpages
- `get_cache_stats`: View cache statistics
- `clear_cache`: Clear the webpage cache

### MCP Resources
- [Claude Code: Set up Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/tutorials#set-up-model-context-protocol-mcp)
- [Model Context Protocol: Server Quickstart](https://modelcontextprotocol.io/quickstart/server)

## License

MIT License