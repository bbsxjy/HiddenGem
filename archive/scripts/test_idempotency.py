"""
Test script to verify idempotency protection for analyze-all endpoint.
Simulates multiple concurrent requests to the same stock symbol.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from loguru import logger


async def test_idempotency():
    """Test idempotency by sending concurrent requests."""

    logger.info("=" * 80)
    logger.info("Testing Idempotency Protection")
    logger.info("=" * 80)

    base_url = "http://localhost:8000"
    symbol = "000001"

    # Send 5 concurrent requests for the same symbol
    logger.info(f"\n📤 Sending 5 concurrent requests for {symbol}...")

    async with httpx.AsyncClient(timeout=400.0) as client:
        tasks = [
            client.post(f"{base_url}/api/v1/agents/analyze-all/{symbol}")
            for _ in range(5)
        ]

        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("\n📊 Results:")

    success_count = 0
    error_count = 0

    for i, response in enumerate(responses, 1):
        if isinstance(response, Exception):
            logger.error(f"  Request {i}: ❌ Error - {response}")
            error_count += 1
        elif response.status_code == 200:
            data = response.json()
            logger.info(f"  Request {i}: ✅ Success")
            logger.info(f"    Symbol: {data.get('symbol')}")
            logger.info(f"    Agents: {len(data.get('agent_results', {}))}")
            logger.info(f"    Signal: {data.get('aggregated_signal', {}).get('direction', 'None')}")
            success_count += 1
        else:
            logger.error(f"  Request {i}: ❌ HTTP {response.status_code}")
            error_count += 1

    logger.info("\n" + "=" * 80)
    logger.info("Summary")
    logger.info("=" * 80)
    logger.info(f"Total requests: 5")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {error_count}")

    logger.info("\n💡 Expected behavior:")
    logger.info("  • All 5 requests should succeed")
    logger.info("  • Backend should only perform 1 actual analysis")
    logger.info("  • Other 4 requests should wait for and share the same result")
    logger.info("")

    logger.info("Check backend logs for:")
    logger.info("  'Creating new analysis task for 000001' - should appear only ONCE")
    logger.info("  'Analysis for 000001 already in progress' - should appear 4 times")
    logger.info("")


async def main():
    """Main entry point."""

    logger.info("Starting idempotency test...")
    logger.info("Make sure backend server is running on localhost:8000\n")

    try:
        await test_idempotency()

        logger.success("\n✓ Test completed!")
        logger.info("\nReview the backend logs to verify:")
        logger.info("  1. Only ONE analysis task was created")
        logger.info("  2. Subsequent requests reused the same task")
        logger.info("  3. No duplicate LLM calls or agent executions")

    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
