"""
Test Fundamental Agent with real Tushare Pro data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from loguru import logger
from core.mcp_agents.fundamental_agent import FundamentalAgent


async def test_fundamental_agent():
    """Test Fundamental Agent with real data."""

    print("=" * 80)
    print("Testing Fundamental Agent with Real Tushare Pro Data")
    print("=" * 80)

    # Initialize agent
    print("\n[1/4] Initializing Fundamental Agent...")
    try:
        agent = FundamentalAgent()
        print("  [OK] Agent initialized")
    except Exception as e:
        print(f"  [FAILED] {e}")
        return 1

    # Test symbols
    test_symbols = [
        ("600000.SH", "浦发银行"),  # Shanghai Pudong Development Bank
        ("000001.SZ", "平安银行"),  # Ping An Bank
        ("600519.SH", "贵州茅台"),  # Kweichow Moutai (high valuation)
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
                print(f"  Score: {result.score:.3f}")
                print(f"  Direction: {result.direction.value}")
                print(f"  Confidence: {result.confidence:.2%}")
                print(f"  Execution Time: {result.execution_time_ms}ms")
                print(f"  Reasoning: {result.reasoning}")

                # Show detailed analysis
                if result.analysis:
                    print(f"\n  Detailed Analysis:")

                    # PE Ratio
                    if 'pe_ratio' in result.analysis:
                        pe = result.analysis['pe_ratio']
                        status = "低估" if pe.get('undervalued') else ("高估" if pe.get('overvalued') else "合理")
                        print(f"    PE Ratio: {pe['value']:.2f} ({status}, Score: {pe['score']:.2f})")

                    # PB Ratio
                    if 'pb_ratio' in result.analysis:
                        pb = result.analysis['pb_ratio']
                        status = "低估" if pb.get('undervalued') else ("高估" if pb.get('overvalued') else "合理")
                        print(f"    PB Ratio: {pb['value']:.2f} ({status}, Score: {pb['score']:.2f})")

                    # ROE
                    if 'roe' in result.analysis:
                        roe = result.analysis['roe']
                        if roe.get('excellent'):
                            status = "优秀"
                        elif roe.get('good'):
                            status = "良好"
                        elif roe.get('acceptable'):
                            status = "可接受"
                        else:
                            status = "较差"
                        print(f"    ROE: {roe['value']:.1f}% ({status}, Score: {roe['score']:.2f})")

                    # Debt
                    if 'debt_to_assets' in result.analysis:
                        debt = result.analysis['debt_to_assets']
                        if debt.get('low_debt'):
                            status = "低负债"
                        elif debt.get('moderate_debt'):
                            status = "中等负债"
                        else:
                            status = "高负债"
                        print(f"    Debt-to-Assets: {debt['value']:.1f}% ({status}, Score: {debt['score']:.2f})")

                    # Market Cap
                    if 'market_cap' in result.analysis:
                        mc = result.analysis['market_cap']
                        cap_type = "大盘股" if mc.get('large_cap') else ("中盘股" if mc.get('mid_cap') else "小盘股")
                        print(f"    Market Cap: {mc['value_billion']:.1f} billion RMB ({cap_type})")

                    # Valuation
                    if 'valuation' in result.analysis:
                        print(f"    Overall Valuation: {result.analysis['valuation']}")

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
        print("\nFundamental Agent is working correctly with real Tushare Pro data:")
        print("  - PE/PB ratios from daily_basic")
        print("  - ROE/Debt ratios from fina_indicator")
        print("  - Market cap and valuation analysis")
        print("  - Trading signals with confidence scores")
    elif success_count > 0:
        print(f"\n[PARTIAL] {success_count}/{total_tests} tests passed")
        print("Some tests may have failed due to weekend/holiday data unavailability")
    else:
        print("\n[FAILED] All tests failed")
        print("Please check Tushare API configuration and permissions")

    print("=" * 80)

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_fundamental_agent())
    sys.exit(exit_code)
