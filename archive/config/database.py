"""
Database configuration and session management.
"""

from typing import AsyncGenerator
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool

from config.settings import settings

# Base class for declarative models
Base = declarative_base()


class DatabaseConfig:
    """Database configuration and connection management."""

    def __init__(self):
        """Initialize database configuration."""
        # Sync engine for migrations and scripts
        self.engine = create_engine(
            settings.database_url,
            poolclass=QueuePool,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_pre_ping=True,  # Verify connections before using
            echo=settings.db_echo,
        )

        # Async engine for FastAPI application
        self.async_engine = create_async_engine(
            settings.database_url_async,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
            echo=settings.db_echo,
            connect_args={
                'server_settings': {
                    'client_encoding': 'utf8'
                }
            }
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

        # Set up event listeners
        self._setup_event_listeners()

    def _setup_event_listeners(self):
        """Set up SQLAlchemy event listeners."""

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            """Set PostgreSQL-specific settings on connect."""
            # This is primarily for PostgreSQL optimization
            if "postgresql" in settings.database_url:
                cursor = dbapi_conn.cursor()
                cursor.execute("SET timezone='UTC'")
                cursor.close()

        @event.listens_for(self.engine, "before_cursor_execute", retval=True)
        def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
            """Log SQL statements in debug mode."""
            if settings.debug:
                # Statement logging is handled by echo=True
                pass
            return statement, params

    def get_session(self) -> Session:
        """
        Get a sync database session.
        Use this for scripts and migrations.

        Returns:
            Session: SQLAlchemy session
        """
        return self.SessionLocal()

    async def get_async_session(self) -> AsyncSession:
        """
        Get an async database session.
        Use this for FastAPI endpoints.

        Returns:
            AsyncSession: Async SQLAlchemy session
        """
        return self.AsyncSessionLocal()

    def create_all(self):
        """Create all database tables (sync)."""
        Base.metadata.create_all(bind=self.engine)

    def drop_all(self):
        """Drop all database tables (sync). Use with caution!"""
        Base.metadata.drop_all(bind=self.engine)

    async def close(self):
        """Close all database connections."""
        await self.async_engine.dispose()
        self.engine.dispose()


# Global database config instance
db_config = DatabaseConfig()


# Dependency for FastAPI endpoints
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get async database session.

    Usage:
        @app.get("/items/")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...

    Yields:
        AsyncSession: Database session
    """
    async with db_config.AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """
    Get sync database session for scripts.

    Returns:
        Session: Database session
    """
    session = db_config.SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
