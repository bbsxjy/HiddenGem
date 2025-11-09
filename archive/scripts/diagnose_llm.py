"""
Diagnostic script for LLM service.
Checks configuration, connectivity, and API accessibility.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from config.settings import settings
from core.utils.llm_service import get_llm_service


def print_separator(title: str = ""):
    """Print a separator line."""
    if title:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"  {title}")
        logger.info(f"{'=' * 80}\n")
    else:
        logger.info(f"{'=' * 80}\n")


async def diagnose_llm():
    """Run LLM diagnostics."""

    print_separator("LLM Service Diagnostics")

    # Step 1: Check configuration
    logger.info("📋 Step 1: Checking LLM Configuration")
    logger.info(f"  LLM Enabled: {settings.llm_enabled}")
    logger.info(f"  Base URL: {settings.llm_base_url}")
    logger.info(f"  Model: {settings.llm_model}")
    logger.info(f"  Timeout: {settings.llm_timeout}s")

    # Check API key
    if settings.llm_api_key:
        masked_key = settings.llm_api_key[:10] + "..." + settings.llm_api_key[-4:]
        logger.info(f"  API Key: {masked_key} (configured)")
    else:
        logger.error("  ❌ API Key: NOT CONFIGURED")
        logger.error("\n  Please set LLM_API_KEY in your .env file")
        return False

    if not settings.llm_enabled:
        logger.warning("\n  ⚠️ LLM is disabled in settings")
        logger.warning("  Set LLM_ENABLED=true in .env to enable")
        return False

    logger.success("  ✓ Configuration looks good\n")

    # Step 2: Initialize service
    print_separator("Step 2: Initializing LLM Service")

    try:
        llm_service = get_llm_service()
        logger.success(f"  ✓ LLM service initialized successfully\n")
    except Exception as e:
        logger.error(f"  ❌ Failed to initialize LLM service: {e}\n")
        return False

    # Step 3: Health check
    print_separator("Step 3: Running Health Check")

    try:
        health_result = await llm_service.health_check()

        if health_result["status"] == "healthy":
            logger.success(f"  ✓ LLM service is healthy")
            logger.info(f"  Response time: {health_result.get('response_time_ms', 'N/A')}ms")
            logger.info(f"  Test response: {health_result.get('test_response', 'N/A')}\n")
        else:
            logger.error(f"  ❌ LLM service is unhealthy")
            logger.error(f"  Error: {health_result.get('error', 'Unknown error')}\n")

            # Provide troubleshooting tips
            error = health_result.get('error', '')
            logger.info("  🔧 Troubleshooting tips:")

            if "401" in error or "authentication" in error.lower():
                logger.info("  • Check your API key is correct")
                logger.info("  • Verify the API key hasn't expired")
            elif "404" in error:
                logger.info("  • Check the model name is correct")
                logger.info("  • Verify the model is available for your account")
            elif "timeout" in error.lower() or "连接超时" in error:
                logger.info("  • Check your internet connection")
                logger.info("  • Try increasing LLM_TIMEOUT in .env")
                logger.info("  • Verify the base URL is correct")
            elif "429" in error:
                logger.info("  • You've hit the rate limit")
                logger.info("  • Wait a few minutes and try again")
            else:
                logger.info("  • Check the base URL is correct")
                logger.info("  • Verify your network can access the API")
                logger.info("  • Check API service status")

            return False

    except Exception as e:
        logger.error(f"  ❌ Health check failed with exception: {e}\n")
        logger.exception(e)
        return False

    # Step 4: Test analysis (optional)
    print_separator("Step 4: Testing Trading Signal Analysis")

    logger.info("  Skipping full analysis test (use test_llm_integration.py for that)")
    logger.info("  Health check passed - API is ready for use\n")

    print_separator()
    logger.success("✓✓✓ All diagnostics passed! LLM service is ready to use ✓✓✓")
    print_separator()

    return True


async def main():
    """Main entry point."""

    logger.info("Starting LLM diagnostics...\n")

    try:
        success = await diagnose_llm()

        if success:
            logger.success("\n✓ Diagnostics completed successfully!")
            sys.exit(0)
        else:
            logger.error("\n✗ Diagnostics failed. Please review the errors above.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("\n\nDiagnostics interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nUnexpected error during diagnostics: {e}")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
