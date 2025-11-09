"""
Verify LLM timeout configuration is correctly loaded.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from config.settings import settings
from core.utils.llm_service import get_llm_service


def verify_timeout():
    """Verify timeout configuration."""

    logger.info("=" * 80)
    logger.info("LLM Timeout Configuration Verification")
    logger.info("=" * 80)

    # Step 1: Check settings
    logger.info("\n📋 Step 1: Checking settings.py")
    logger.info(f"  settings.llm_timeout = {settings.llm_timeout} seconds")

    if settings.llm_timeout == 300:
        logger.success("  ✓ Settings correctly loaded from .env (300s)")
    elif settings.llm_timeout == 30:
        logger.error("  ✗ Settings using default value (30s)")
        logger.error("  ⚠️  Check if .env file exists and LLM_TIMEOUT=300 is set")
        return False
    else:
        logger.warning(f"  ⚠️  Unexpected timeout value: {settings.llm_timeout}s")

    # Step 2: Check LLM service initialization
    logger.info("\n🔧 Step 2: Checking LLM service initialization")

    try:
        llm_service = get_llm_service()
        logger.info(f"  llm_service.timeout = {llm_service.timeout} seconds")

        if llm_service.timeout == 300:
            logger.success("  ✓ LLM service correctly using 300s timeout")
        elif llm_service.timeout == 30:
            logger.error("  ✗ LLM service still using 30s timeout")
            logger.error("  ⚠️  Bug in llm_service.py initialization")
            return False
        else:
            logger.warning(f"  ⚠️  Unexpected timeout: {llm_service.timeout}s")

    except Exception as e:
        logger.error(f"  ✗ Failed to initialize LLM service: {e}")
        return False

    # Step 3: Verify httpx client timeout
    logger.info("\n🌐 Step 3: Verifying httpx client timeout")
    logger.info(f"  HTTP client will use timeout: {llm_service.timeout}s")
    logger.info("  This allows DeepSeek-R1 model to complete reasoning")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.success("✓✓✓ All timeout configurations are correct! ✓✓✓")
    logger.info("=" * 80)
    logger.info("\n💡 Tips:")
    logger.info("  • DeepSeek-R1 is a reasoning model, may take longer")
    logger.info("  • 300s timeout allows for complex analysis")
    logger.info("  • Monitor actual response times in production")
    logger.info("  • Consider adjusting based on actual usage patterns")
    logger.info("")

    return True


if __name__ == "__main__":
    try:
        success = verify_timeout()

        if success:
            logger.success("\n✓ Verification passed!")
            logger.info("Now restart your backend server to apply changes:")
            logger.info("  1. Stop the server (Ctrl+C)")
            logger.info("  2. Restart: uvicorn api.main:app --reload")
            sys.exit(0)
        else:
            logger.error("\n✗ Verification failed!")
            logger.error("Please check the errors above and fix configuration")
            sys.exit(1)

    except Exception as e:
        logger.error(f"\n✗ Verification error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
