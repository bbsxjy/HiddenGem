"""
Quick database initialization for SQLite (no PostgreSQL needed).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Import SQLite config instead of PostgreSQL
from config.database_sqlite import db_config, Base
from database.models import (
    MarketData, Signal, Order, Position, PortfolioSnapshot,
    AgentAnalysis, RiskEvent, StockInfo
)

def main():
    """Initialize SQLite database."""
    logger.info("=" * 60)
    logger.info("Initializing SQLite Database")
    logger.info("=" * 60)

    logger.info("\nCreating tables...")
    try:
        db_config.create_all()
        logger.success("✓ Tables created successfully!")
        logger.info(f"✓ Database file: hiddengem.db")

        logger.info("\n" + "=" * 60)
        logger.success("Database initialization completed!")
        logger.info("=" * 60)
        logger.info("\nYou can now start the server:")
        logger.info("  python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000")

        return 0

    except Exception as e:
        logger.error(f"\n✗ Error: {e}")
        logger.error("\nInitialization failed!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
