"""
Test script for price fetching functionality.
Tests the fixed _fetch_current_price method.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from core.utils.llm_service import LLMService


async def test_fetch_current_price():
    """Test the _fetch_current_price method with stock 300502."""

    logger.info("=" * 80)
    logger.info("Testing Current Price Fetching for 300502")
    logger.info("=" * 80)

    # Initialize LLM service
    llm_service = LLMService()

    # Test symbol
    test_symbol = "300502"

    logger.info(f"\nTesting price fetch for symbol: {test_symbol}")

    try:
        # Call the fixed _fetch_current_price method
        price = await llm_service._fetch_current_price(test_symbol)

        if price:
            logger.success(f"✅ Successfully fetched current price for {test_symbol}: {price:.2f}")
        else:
            logger.error(f"❌ Failed to fetch current price for {test_symbol}")

        return price

    except Exception as e:
        logger.error(f"❌ Error during price fetch: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_multiple_symbols():
    """Test price fetching for multiple symbols."""

    logger.info("\n" + "=" * 80)
    logger.info("Testing Multiple Symbols")
    logger.info("=" * 80)

    test_symbols = [
        "300502",  # ChiNext stock
        "600519",  # Main board stock (Kweichow Moutai)
        "000001",  # Shenzhen stock (Ping An Bank)
    ]

    llm_service = LLMService()

    results = {}

    for symbol in test_symbols:
        logger.info(f"\nTesting symbol: {symbol}")
        try:
            price = await llm_service._fetch_current_price(symbol)
            results[symbol] = price

            if price:
                logger.success(f"  ✅ {symbol}: {price:.2f}")
            else:
                logger.warning(f"  ⚠️  {symbol}: Failed to fetch price")

        except Exception as e:
            logger.error(f"  ❌ {symbol}: Error - {e}")
            results[symbol] = None

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Summary")
    logger.info("=" * 80)

    success_count = sum(1 for p in results.values() if p is not None)
    total_count = len(results)

    logger.info(f"Successfully fetched: {success_count}/{total_count}")

    for symbol, price in results.items():
        status = "✅" if price else "❌"
        price_str = f"{price:.2f}" if price else "N/A"
        logger.info(f"{status} {symbol}: {price_str}")


async def main():
    """Main test function."""

    # Test 1: Single symbol (300502)
    await test_fetch_current_price()

    # Test 2: Multiple symbols
    await test_multiple_symbols()

    logger.info("\n" + "=" * 80)
    logger.info("All tests completed!")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
