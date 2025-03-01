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

    url = Column(String, primary_key=True)
    content = Column(Text)
    markdown_content = Column(Text)
    timestamp = Column(Integer)


class Database:
    """Database handler for the application."""

    def __init__(self, db_path: str):
        """
        Initialize the database handler.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()

    def get_cached_content(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve content from cache if available.

        Args:
            url: Normalized URL to look up in cache

        Returns:
            Dictionary with cached content or None if not in cache
        """
        with self.get_session() as session:
            cache_entry = session.execute(
                select(WebCache).where(WebCache.url == url)
            ).scalar_one_or_none()

            if cache_entry:
                return {
                    "content": cache_entry.content,
                    "markdown_content": cache_entry.markdown_content,
                    "cached": True,
                    "timestamp": cache_entry.timestamp,
                }

        return None

    def cache_content(self, url: str, content: str, markdown_content: str) -> None:
        """
        Store content in cache.

        Args:
            url: Normalized URL to use as key
            content: Raw HTML content
            markdown_content: Converted markdown content
        """
        current_time = int(time.time())

        with self.get_session() as session:
            cache_entry = session.execute(
                select(WebCache).where(WebCache.url == url)
            ).scalar_one_or_none()

            if cache_entry:
                # Update existing entry
                cache_entry.content = content
                cache_entry.markdown_content = markdown_content
                cache_entry.timestamp = current_time
            else:
                # Create new entry
                new_entry = WebCache(
                    url=url,
                    content=content,
                    markdown_content=markdown_content,
                    timestamp=current_time,
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
