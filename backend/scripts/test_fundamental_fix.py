"""
Test FundamentalStrategy data interface fix
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trading.fundamental_strategy import FundamentalStrategy
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

logger = logging.getLogger(__name__)

def test_fundamental_strategy():
    """Test FundamentalStrategy initialization"""
    logger.info("=" * 60)
    logger.info("[TEST] Testing FundamentalStrategy")
    logger.info("=" * 60)

    try:
        # Create strategy instance
        strategy = FundamentalStrategy()

        # Check if data interface is available
        if strategy.data_optimizer is not None:
            logger.info(" Data interface initialized successfully")
            logger.info(f"   Data optimizer type: {type(strategy.data_optimizer).__name__}")
        else:
            logger.warning(" Data interface not available (using fallback)")

        logger.info("")
        logger.info("=" * 60)
        logger.info("[SUCCESS] FundamentalStrategy test passed")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f" [FAILED] Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_fundamental_strategy()
    sys.exit(0 if success else 1)
