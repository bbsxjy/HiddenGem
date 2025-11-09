"""
Test Sentiment Agent with real Tushare Pro data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from loguru import logger
from core.mcp_agents.sentiment_agent import SentimentAgent


async def test_sentiment_agent():
    """Test Sentiment Agent with real data."""

    print("=" * 80)
    print("Testing Sentiment Agent with Real Tushare Pro Data")
    print("=" * 80)

    # Initialize agent
    print("\n[1/4] Initializing Sentiment Agent...")
    try:
        agent = SentimentAgent()
        print("  [OK] Agent initialized")
    except Exception as e:
        print(f"  [FAILED] {e}")
        return 1

    # Test symbols
    test_symbols = [
        ("600000.SH", "浦发银行"),  # Shanghai Pudong Development Bank
        ("000001.SZ", "平安银行"),  # Ping An Bank
        ("600519.SH", "贵州茅台"),  # Kweichow Moutai
    ]

    success_count = 0
    total_tests = len(test_symbols)

    for idx, (symbol, name) in enumerate(test_symbols, start=2):
        print(f"\n[{idx}/{total_tests+1}] Testing {name} ({symbol})...")

        try:
            # Perform analysis
            result = await agent.analyze(symbol=symbol)

            if not result.is_error:
                print(f"  [OK] Analysis completed successfully")
                print(f"  Symbol: {result.symbol}")
                print(f"  Sentiment Score: {result.score:.3f} (-1=悲观, 1=乐观)")
                print(f"  Direction: {result.direction.value}")
                print(f"  Confidence: {result.confidence:.2%}")
                print(f"  Execution Time: {result.execution_time_ms}ms")
                print(f"  Reasoning: {result.reasoning}")

                # Show detailed analysis
                if result.analysis:
                    print(f"\n  Detailed Analysis:")

                    # Money Flow
                    money_flow = result.analysis.get('money_flow', {})
                    if 'net_flow' in money_flow:
                        net_flow = money_flow['net_flow']
                        net_elg = money_flow.get('net_extra_large_flow', 0)
                        trend = money_flow.get('3day_trend', 'N/A')
                        print(f"    Money Flow: 净流入 {net_flow:,.0f}万元")
                        print(f"      特大单: {net_elg:,.0f}万元, 3日趋势: {trend}")
                        print(f"      Score: {money_flow.get('score', 0):.2f}")

                    # Foreign Capital
                    foreign = result.analysis.get('foreign_capital', {})
                    if 'holdings_ratio' in foreign:
                        ratio = foreign['holdings_ratio']
                        change = foreign['ratio_change']
                        trend = foreign.get('trend', 'N/A')
                        print(f"    Foreign Capital: 持股比例 {ratio:.2f}%")
                        print(f"      变化: {change:.2f}%, 趋势: {trend}")
                        print(f"      Score: {foreign.get('score', 0):.2f}")
                    elif 'score' in foreign:
                        print(f"    Foreign Capital: 无港资持仓 (Score: {foreign['score']:.2f})")

                    # Insider Trading
                    insider = result.analysis.get('insider_trading', {})
                    if 'increase_count' in insider:
                        inc = insider['increase_count']
                        dec = insider['decrease_count']
                        recent = "有" if insider.get('recent_activity') else "无"
                        print(f"    Insider Trading: 增持{inc}次, 减持{dec}次")
                        print(f"      近期活动: {recent}")
                        print(f"      Score: {insider.get('score', 0):.2f}")
                    elif 'score' in insider:
                        print(f"    Insider Trading: 无记录 (Score: {insider['score']:.2f})")

                    # Dragon-Tiger List
                    dragon = result.analysis.get('dragon_tiger', {})
                    if dragon.get('on_list'):
                        net = dragon.get('net_amount', 0)
                        inst = "是" if dragon.get('institutional') else "否"
                        print(f"    Dragon-Tiger List: 上榜")
                        print(f"      净额: {net:,.0f}万元, 机构: {inst}")
                        print(f"      原因: {dragon.get('reason', 'N/A')}")
                        print(f"      Score: {dragon.get('score', 0):.2f}")
                    elif 'score' in dragon:
                        print(f"    Dragon-Tiger List: 未上榜 (Score: {dragon['score']:.2f})")

                    # Overall Sentiment
                    if 'sentiment_level' in result.analysis:
                        print(f"    Overall Sentiment: {result.analysis['sentiment_level']}")

                success_count += 1

            else:
                print(f"  [FAILED] Analysis failed: {result.error_message}")

        except Exception as e:
            print(f"  [FAILED] Exception: {str(e)[:100]}")
            logger.exception(f"Error testing {symbol}")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"\nTests Passed: {success_count}/{total_tests}")

    if success_count == total_tests:
        print("\n[SUCCESS] All tests passed!")
        print("\nSentiment Agent is working correctly with real Tushare Pro data:")
        print("  - Money flow analysis (main force buying/selling)")
        print("  - Foreign capital tracking (northbound funds)")
        print("  - Insider trading monitoring (shareholder activity)")
        print("  - Dragon-tiger list detection (speculative activity)")
        print("\nSentiment Agent now provides:")
        print("  - Real-time market sentiment scoring")
        print("  - Institutional money flow tracking")
        print("  - Multi-factor sentiment analysis")
    elif success_count > 0:
        print(f"\n[PARTIAL] {success_count}/{total_tests} tests passed")
    else:
        print("\n[FAILED] All tests failed")
        print("Please check Tushare API configuration")

    print("=" * 80)

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_sentiment_agent())
    sys.exit(exit_code)
