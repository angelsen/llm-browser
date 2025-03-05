"""
Configuration handling for LLM Browser.
"""

import os
import platform
from pathlib import Path
from typing import Optional


class BrowserConfig:
    """Configuration class for LLM Browser."""

    def __init__(
        self, 
        custom_db_path: Optional[str] = None,
        prefer_raw: bool = True,
        include_navigation: bool = True
    ):
        """
        Initialize browser configuration.

        Args:
            custom_db_path: Optional custom path for the database
            prefer_raw: If True, use raw GitHub content when available
            include_navigation: If True, include navigation structure in results
        """
        self.user_agent = "llm-web-browser/0.1.0"
        self.db_path = custom_db_path or self._get_default_db_path()
        self.prefer_raw = prefer_raw
        self.include_navigation = include_navigation

    def _get_default_db_path(self) -> str:
        """
        Get the appropriate database path based on platform and environment variables.

        Returns:
            Path to the database file
        """
        # Check environment variable first
        if "LLM_BROWSER_DB_PATH" in os.environ:
            return os.environ["LLM_BROWSER_DB_PATH"]

        app_name = "llm-browser"

        if platform.system() == "Windows":
            base_dir = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            data_dir = Path(base_dir) / app_name
        elif platform.system() == "Darwin":  # macOS
            base_dir = Path("~/Library/Application Support").expanduser()
            data_dir = base_dir / app_name
        else:  # Linux and others
            base_dir = Path(
                os.environ.get("XDG_DATA_HOME", "~/.local/share")
            ).expanduser()
            data_dir = base_dir / app_name

        # Ensure directory exists
        data_dir.mkdir(parents=True, exist_ok=True)

        return str(data_dir / "web_cache.db")
