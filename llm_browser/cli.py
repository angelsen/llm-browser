"""
Command-line interface for LLM Browser.
"""

import argparse
import sys
from typing import List, Optional

from llm_browser import __version__
from llm_browser.config import BrowserConfig
from llm_browser.server import create_server


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: Command-line arguments or None to use sys.argv

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="LLM Browser - A web browser tool for LLMs"
    )

    parser.add_argument(
        "--version", action="version", version=f"LLM Browser v{__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Server command
    server_parser = subparsers.add_parser("server", help="Run the MCP server")
    server_parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport to use for MCP server (default: stdio)",
    )
    server_parser.add_argument("--db-path", help="Custom path for the database")

    # Cache commands
    cache_parser = subparsers.add_parser("cache", help="Cache management commands")
    cache_subparsers = cache_parser.add_subparsers(
        dest="cache_command", help="Cache command to run"
    )

    # Cache clear command
    cache_clear_parser = cache_subparsers.add_parser("clear", help="Clear the cache")
    cache_clear_parser.add_argument("--db-path", help="Custom path for the database")

    # Cache stats command
    cache_stats_parser = cache_subparsers.add_parser(
        "stats", help="Show cache statistics"
    )
    cache_stats_parser.add_argument("--db-path", help="Custom path for the database")

    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        args: Command-line arguments or None to use sys.argv

    Returns:
        Exit code
    """
    parsed_args = parse_args(args)

    if not parsed_args.command:
        print("Error: No command specified. Use --help for more information.")
        return 1

    # Create configuration
    config = BrowserConfig(
        custom_db_path=parsed_args.db_path if hasattr(parsed_args, "db_path") else None
    )

    if parsed_args.command == "server":
        # Run the MCP server
        server = create_server(config)
        server.run(transport=parsed_args.transport)
        return 0

    elif parsed_args.command == "cache":
        if not parsed_args.cache_command:
            print(
                "Error: No cache command specified. Use 'cache --help' for more information."
            )
            return 1

        server = create_server(config)

        if parsed_args.cache_command == "clear":
            # Clear the cache
            print(server.db.clear_cache())
            return 0

        elif parsed_args.cache_command == "stats":
            # Show cache statistics
            stats = server.db.get_cache_stats()

            print("Cache Statistics:")
            print(f"- Database location: {config.db_path}")
            print(f"- Total pages cached: {stats['count']}")
            print(f"- Total cache size: {stats['size_kb']} KB")

            if stats["oldest_entry_time"]:
                hours_old = (stats["current_time"] - stats["oldest_entry_time"]) // 3600
                print(f"- Oldest cache entry: {hours_old} hours old")
            else:
                print("- Oldest cache entry: N/A")

            if stats["newest_entry_time"]:
                hours_old = (stats["current_time"] - stats["newest_entry_time"]) // 3600
                print(f"- Newest cache entry: {hours_old} hours old")
            else:
                print("- Newest cache entry: N/A")

            print("- Recent URLs:")
            if not stats["recent_urls"]:
                print("  - None")
            else:
                for url in stats["recent_urls"]:
                    print(f"  - {url}")

            return 0

    print(f"Error: Unknown command '{parsed_args.command}'")
    return 1


if __name__ == "__main__":
    sys.exit(main())
