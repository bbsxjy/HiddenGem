"""
Test Market Agent with real Tushare data.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mcp_agents.market_agent import MarketMonitorAgent


async def test_market_agent():
    """Test Market Agent analysis."""

    print("=" * 80)
    print("Market Agent Test - Real Tushare Data")
    print("=" * 80)

    # Initialize agent
    print("\n[1/2] Initializing Market Agent...")
    try:
        agent = MarketMonitorAgent()
        print("  [OK] Agent initialized")
    except Exception as e:
        print(f"  [FAILED] {e}")
        return 1

    # Test analysis
    print("\n[2/2] Running market analysis...")
    try:
        result = await agent.analyze()

        print(f"\n  [OK] Market Analysis Complete")
        print(f"\n  Agent: {result.agent_name}")
        print(f"  Score: {result.score:.3f}")
        print(f"  Direction: {result.direction}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Execution Time: {result.execution_time_ms}ms")
        print(f"\n  Reasoning:\n    {result.reasoning}")

        # Display detailed analysis
        if result.analysis:
            print(f"\n  Detailed Analysis:")

            # Market Phase
            if 'market_phase' in result.analysis:
                phase = result.analysis['market_phase']
                print(f"\n  Market Phase:")
                print(f"    Phase: {phase.get('phase')}")
                print(f"    Confidence: {phase.get('confidence', 0):.2%}")
                print(f"    Description: {phase.get('description')}")
                if 'index_close' in phase:
                    print(f"    SSE Index: {phase['index_close']:.2f}")
                    if 'pct_5d' in phase:
                        print(f"    5-day Change: {phase['pct_5d']:.2%}")
                    if 'pct_20d' in phase:
                        print(f"    20-day Change: {phase['pct_20d']:.2%}")

            # Northbound Capital
            if 'northbound_capital' in result.analysis:
                nb = result.analysis['northbound_capital']
                print(f"\n  Northbound Capital:")
                print(f"    Description: {nb.get('description')}")
                if nb.get('net_inflow') != 0:
                    print(f"    Net Inflow: {nb['net_inflow']/100000000:.2f}亿元")

            # Margin Trading
            if 'margin_trading' in result.analysis:
                margin = result.analysis['margin_trading']
                print(f"\n  Margin Trading:")
                print(f"    Description: {margin.get('description')}")
                if margin.get('balance') != 0:
                    print(f"    Balance: {margin['balance']/100000000:.2f}亿元")
                    print(f"    Change: {margin.get('change_pct', 0):.2%}")

            # Sentiment
            if 'sentiment' in result.analysis:
                sentiment = result.analysis['sentiment']
                print(f"\n  Market Sentiment:")
                print(f"    Score: {sentiment.get('score', 0):.2%}")
                print(f"    Description: {sentiment.get('description')}")

        print("\n" + "=" * 80)
        print("[SUCCESS] Market Agent is using REAL Tushare data!")
        print("=" * 80)

        return 0

    except Exception as e:
        print(f"  [FAILED] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_market_agent())
    sys.exit(exit_code)
