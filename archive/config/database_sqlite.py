"""
SQLite database configuration for testing without PostgreSQL.
"""

from typing import AsyncGenerator
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

from config.settings import settings

# Base class for declarative models
Base = declarative_base()


class DatabaseConfig:
    """Database configuration for SQLite."""

    def __init__(self):
        """Initialize database configuration."""
        # Use SQLite for simplicity
        db_path = "sqlite:///./hiddengem.db"
        db_path_async = "sqlite+aiosqlite:///./hiddengem.db"

        # Sync engine
        self.engine = create_engine(
            db_path,
            connect_args={"check_same_thread": False},
            echo=settings.db_echo,
        )

        # Async engine
        self.async_engine = create_async_engine(
            db_path_async,
            echo=settings.db_echo,
        )

        # Session factories
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        self.AsyncSessionLocal = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    def create_all(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)

    def drop_all(self):
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)

    async def close(self):
        """Close all database connections."""
        await self.async_engine.dispose()
        self.engine.dispose()


# Global database config instance
db_config = DatabaseConfig()


# Dependency for FastAPI endpoints
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with db_config.AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
