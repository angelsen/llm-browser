"""
SQLAlchemy models for LLM Browser.
"""

import time
from typing import Optional, Dict, Any

from sqlalchemy import create_engine, Column, String, Integer, Text, select, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()


class WebCache(Base):
    """SQLAlchemy model for the web cache table."""

    __tablename__ = "web_cache"

    # Primary key is now a combination of URL and feature flags
    id = Column(String, primary_key=True)
    url = Column(String, index=True)
    content = Column(Text)
    markdown_content = Column(Text)
    timestamp = Column(Integer)
    
    # Feature flags used to generate this cache entry
    prefer_raw = Column(Integer, default=1)  # 1=True, 0=False
    include_navigation = Column(Integer, default=0)  # 1=True, 0=False
    content_priority = Column(String, default="auto")


class Database:
    """Database handler for the application."""

    def __init__(self, db_path: str):
        """
        Initialize the database handler.
        
        Note: Each time you update to a new version, you may need to delete
        the database file at the path specified and let it recreate.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Initialize database tables
        self._initialize_database()

    def _initialize_database(self):
        """
        Initialize database tables.
        
        Note: For schema changes, it's best to delete the old database file and start fresh.
        """
        # Drop existing tables if they exist
        Base.metadata.drop_all(bind=self.engine)
        
        # Create fresh tables
        Base.metadata.create_all(bind=self.engine)
        
        print(f"Database initialized at: {self.db_path}")
    
    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()

    def _generate_cache_id(self, url: str, prefer_raw: bool = True, include_navigation: bool = False,
                          content_priority: str = "auto") -> str:
        """
        Generate a unique cache ID based on URL and feature flags.
        
        Args:
            url: Normalized URL
            prefer_raw: Whether raw GitHub content is preferred
            include_navigation: Whether navigation is included (set to True when navigating between pages or traversing a website)
            content_priority: Content extraction strategy
            
        Returns:
            A unique cache ID string
        """
        # Convert bool flags to strings
        raw_flag = "1" if prefer_raw else "0"
        nav_flag = "1" if include_navigation else "0" 
        
        # Create a composite key
        return f"{url}|{raw_flag}|{nav_flag}|{content_priority}"

    def get_cached_content(self, url: str, prefer_raw: bool = True, include_navigation: bool = False,
                           content_priority: str = "auto") -> Optional[Dict[str, Any]]:
        """
        Retrieve content from cache if available.

        Args:
            url: Normalized URL to look up in cache
            prefer_raw: Whether raw GitHub content is preferred
            include_navigation: Whether navigation is included (set to True when navigating between pages or traversing a website)
            content_priority: Content extraction strategy

        Returns:
            Dictionary with cached content or None if not in cache
        """
        # Generate cache ID
        cache_id = self._generate_cache_id(
            url, prefer_raw, include_navigation, content_priority
        )
        
        with self.get_session() as session:
            cache_entry = session.execute(
                select(WebCache).where(WebCache.id == cache_id)
            ).scalar_one_or_none()

            if cache_entry:
                return {
                    "content": cache_entry.content,
                    "markdown_content": cache_entry.markdown_content,
                    "cached": True,
                    "timestamp": cache_entry.timestamp,
                    "html_content": cache_entry.content  # Added to support navigation extraction
                }

        return None

    def cache_content(self, url: str, content: str, markdown_content: str, 
                     prefer_raw: bool = True, include_navigation: bool = False,
                     content_priority: str = "auto") -> None:
        """
        Store content in cache.

        Args:
            url: Normalized URL to use as key
            content: Raw HTML content
            markdown_content: Converted markdown content
            prefer_raw: Whether raw GitHub content is preferred
            include_navigation: Whether navigation is included (set to True when navigating between pages or traversing a website)
            content_priority: Content extraction strategy
        """
        current_time = int(time.time())
        
        # Generate cache ID
        cache_id = self._generate_cache_id(
            url, prefer_raw, include_navigation, content_priority
        )

        with self.get_session() as session:
            cache_entry = session.execute(
                select(WebCache).where(WebCache.id == cache_id)
            ).scalar_one_or_none()

            if cache_entry:
                # Update existing entry
                cache_entry.content = content
                cache_entry.markdown_content = markdown_content
                cache_entry.timestamp = current_time
            else:
                # Create new entry
                new_entry = WebCache(
                    id=cache_id,
                    url=url,
                    content=content,
                    markdown_content=markdown_content,
                    timestamp=current_time,
                    prefer_raw=1 if prefer_raw else 0,
                    include_navigation=1 if include_navigation else 0,
                    content_priority=content_priority
                )
                session.add(new_entry)

            session.commit()

    def clear_cache(self) -> int:
        """
        Clear the entire web browsing cache.

        Returns:
            Number of entries deleted
        """
        with self.get_session() as session:
            count = session.query(WebCache).count()
            session.query(WebCache).delete()
            session.commit()
            return count

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        with self.get_session() as session:
            # Get count of cached pages
            count = session.query(WebCache).count()

            # Get total size (approximate)
            size_query = session.query(WebCache).with_entities(
                WebCache.content, WebCache.markdown_content
            )
            total_size = sum(
                len(row.content or "") + len(row.markdown_content or "")
                for row in size_query
            )

            # Get oldest and newest cache entries
            timestamps = session.query(
                func.min(WebCache.timestamp), func.max(WebCache.timestamp)
            ).first()
            min_time, max_time = timestamps if timestamps else (None, None)

            # Get list of cached URLs
            recent_urls = [
                row.url
                for row in session.query(WebCache)
                .order_by(WebCache.timestamp.desc())
                .limit(10)
            ]

        current_time = int(time.time())

        return {
            "count": count,
            "size_kb": total_size // 1024,
            "oldest_entry_time": min_time,
            "newest_entry_time": max_time,
            "current_time": current_time,
            "recent_urls": recent_urls,
        }
