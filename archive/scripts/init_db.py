"""
Database initialization script.

Creates all tables and sets up TimescaleDB hypertables for time-series data.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text

from config.database import db_config, Base
from config.settings import settings
from database.models import (
    MarketData, Signal, Order, Position, PortfolioSnapshot,
    AgentAnalysis, RiskEvent, StockInfo
)


async def create_timescaledb_extension():
    """Create TimescaleDB extension if not exists."""
    try:
        async with db_config.async_engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
        logger.info("TimescaleDB extension created/verified")
    except Exception as e:
        logger.warning(f"Could not create TimescaleDB extension: {e}")
        logger.warning("TimescaleDB features will not be available")


async def create_hypertables():
    """Convert time-series tables to TimescaleDB hypertables."""
    hypertable_configs = [
        {
            "table": "market_data",
            "time_column": "timestamp",
            "chunk_time_interval": "7 days"
        },
        {
            "table": "portfolio_snapshots",
            "time_column": "timestamp",
            "chunk_time_interval": "30 days"
        },
        {
            "table": "agent_analyses",
            "time_column": "timestamp",
            "chunk_time_interval": "7 days"
        },
        {
            "table": "risk_events",
            "time_column": "timestamp",
            "chunk_time_interval": "30 days"
        }
    ]

    try:
        async with db_config.async_engine.begin() as conn:
            for config in hypertable_configs:
                # Check if already a hypertable
                check_query = text("""
                    SELECT * FROM timescaledb_information.hypertables
                    WHERE hypertable_name = :table_name
                """)
                result = await conn.execute(
                    check_query,
                    {"table_name": config["table"]}
                )

                if result.fetchone() is None:
                    # Create hypertable
                    create_query = text(f"""
                        SELECT create_hypertable(
                            '{config["table"]}',
                            '{config["time_column"]}',
                            chunk_time_interval => INTERVAL '{config["chunk_time_interval"]}',
                            if_not_exists => TRUE
                        );
                    """)
                    await conn.execute(create_query)
                    logger.info(f"Created hypertable: {config['table']}")
                else:
                    logger.info(f"Hypertable already exists: {config['table']}")

    except Exception as e:
        logger.warning(f"Could not create hypertables: {e}")
        logger.warning("Tables will remain as regular PostgreSQL tables")


async def create_compression_policies():
    """Add compression policies for TimescaleDB hypertables."""
    compression_configs = [
        {
            "table": "market_data",
            "compress_after": "30 days"
        },
        {
            "table": "agent_analyses",
            "compress_after": "60 days"
        }
    ]

    try:
        async with db_config.async_engine.begin() as conn:
            for config in compression_configs:
                # Enable compression
                enable_query = text(f"""
                    ALTER TABLE {config["table"]}
                    SET (timescaledb.compress);
                """)

                # Add compression policy
                policy_query = text(f"""
                    SELECT add_compression_policy(
                        '{config["table"]}',
                        INTERVAL '{config["compress_after"]}',
                        if_not_exists => TRUE
                    );
                """)

                await conn.execute(enable_query)
                await conn.execute(policy_query)

                logger.info(
                    f"Added compression policy for {config['table']} "
                    f"(compress after {config['compress_after']})"
                )

    except Exception as e:
        logger.warning(f"Could not add compression policies: {e}")


async def create_retention_policies():
    """Add data retention policies."""
    retention_configs = [
        {
            "table": "agent_analyses",
            "retention": "180 days"  # Keep 6 months of agent analyses
        },
        {
            "table": "risk_events",
            "retention": "365 days"  # Keep 1 year of risk events
        }
    ]

    try:
        async with db_config.async_engine.begin() as conn:
            for config in retention_configs:
                policy_query = text(f"""
                    SELECT add_retention_policy(
                        '{config["table"]}',
                        INTERVAL '{config["retention"]}',
                        if_not_exists => TRUE
                    );
                """)

                await conn.execute(policy_query)

                logger.info(
                    f"Added retention policy for {config['table']} "
                    f"(retain {config['retention']})"
                )

    except Exception as e:
        logger.warning(f"Could not add retention policies: {e}")


async def create_indexes():
    """Create additional performance indexes."""
    try:
        async with db_config.async_engine.begin() as conn:
            # Market data indexes
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_market_data_symbol_date
                ON market_data (symbol, timestamp DESC);
            """))

            # Signal indexes
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_signals_direction_strength
                ON signals (direction, strength DESC)
                WHERE is_executed = FALSE;
            """))

            # Order indexes
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_orders_status_created
                ON orders (status, created_at DESC);
            """))

            logger.info("Created additional performance indexes")

    except Exception as e:
        logger.error(f"Error creating indexes: {e}")


def create_all_tables():
    """Create all database tables (sync)."""
    try:
        # Drop all tables if DROP_ALL env var is set
        if settings.debug and input("Drop all existing tables? (yes/no): ").lower() == "yes":
            logger.warning("Dropping all tables...")
            db_config.drop_all()

        # Create all tables
        logger.info("Creating database tables...")
        db_config.create_all()
        logger.info("Successfully created all tables")

        # Print created tables
        from sqlalchemy import inspect
        inspector = inspect(db_config.engine)
        tables = inspector.get_table_names()
        logger.info(f"Created tables: {', '.join(tables)}")

    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise


async def init_database():
    """Initialize database with all tables and TimescaleDB features."""
    logger.info("=" * 60)
    logger.info("HiddenGem Database Initialization")
    logger.info("=" * 60)

    # Display configuration
    logger.info(f"Database URL: {settings.database_url}")
    logger.info(f"Environment: {'Development' if settings.is_development else 'Production'}")

    # Step 1: Create TimescaleDB extension
    logger.info("\n[1/6] Creating TimescaleDB extension...")
    await create_timescaledb_extension()

    # Step 2: Create all tables
    logger.info("\n[2/6] Creating database tables...")
    create_all_tables()

    # Step 3: Convert to hypertables
    logger.info("\n[3/6] Converting time-series tables to hypertables...")
    await create_hypertables()

    # Step 4: Add compression policies
    logger.info("\n[4/6] Adding compression policies...")
    await create_compression_policies()

    # Step 5: Add retention policies
    logger.info("\n[5/6] Adding retention policies...")
    await create_retention_policies()

    # Step 6: Create indexes
    logger.info("\n[6/6] Creating performance indexes...")
    await create_indexes()

    logger.info("\n" + "=" * 60)
    logger.info("Database initialization completed successfully!")
    logger.info("=" * 60)


async def verify_database():
    """Verify database setup."""
    logger.info("\nVerifying database setup...")

    try:
        async with db_config.async_engine.begin() as conn:
            # Check tables
            result = await conn.execute(text("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """))
            tables = [row[0] for row in result]
            logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")

            # Check hypertables
            result = await conn.execute(text("""
                SELECT hypertable_name FROM timescaledb_information.hypertables;
            """))
            hypertables = [row[0] for row in result]
            if hypertables:
                logger.info(f"Found {len(hypertables)} hypertables: {', '.join(hypertables)}")
            else:
                logger.info("No hypertables found (TimescaleDB may not be available)")

            logger.info("Database verification completed")

    except Exception as e:
        logger.error(f"Error verifying database: {e}")


async def main():
    """Main entry point."""
    try:
        # Initialize database
        await init_database()

        # Verify setup
        await verify_database()

        # Close connections
        await db_config.close()

        logger.info("\nDatabase is ready for use!")
        return 0

    except Exception as e:
        logger.exception(f"Database initialization failed: {e}")
        return 1


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Run initialization
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
