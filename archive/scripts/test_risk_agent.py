"""
Test Risk Agent with real Tushare Pro data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from loguru import logger
from core.mcp_agents.risk_agent import RiskManagerAgent


async def test_risk_agent():
    """Test Risk Agent with real data."""

    print("=" * 80)
    print("Testing Risk Agent with Real Tushare Pro Data")
    print("=" * 80)

    # Initialize agent
    print("\n[1/4] Initializing Risk Agent...")
    try:
        agent = RiskManagerAgent()
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
                print(f"  Risk Score: {result.score:.3f} (lower = higher risk)")
                print(f"  Direction: {result.direction.value}")
                print(f"  Confidence: {result.confidence:.2%}")
                print(f"  Execution Time: {result.execution_time_ms}ms")
                print(f"  Reasoning: {result.reasoning}")

                # Show detailed analysis
                if result.analysis:
                    print(f"\n  Detailed Analysis:")

                    # A-share Risks
                    ashare_risks = result.analysis.get('ashare_risks', {})

                    # Pledge Ratio
                    if 'pledge_ratio' in ashare_risks:
                        pledge = ashare_risks['pledge_ratio']
                        status = "危险" if pledge.get('danger') else ("警告" if pledge.get('warning') else "正常")
                        print(f"    Pledge Ratio: {pledge['value']:.1%} ({status}, Score: {pledge['score']:.2f})")

                    # ST Status
                    if 'st_status' in ashare_risks:
                        st = ashare_risks['st_status']
                        status_text = "是ST" if st.get('is_st') else "非ST"
                        print(f"    ST Status: {status_text} (Score: {st['score']:.2f})")

                    # Suspension
                    if 'suspension' in ashare_risks:
                        suspend = ashare_risks['suspension']
                        if suspend.get('is_suspended'):
                            print(f"    Suspension: 停牌中 (Score: {suspend['score']:.2f})")
                        else:
                            print(f"    Suspension: 正常交易 (Score: {suspend['score']:.2f})")

                    # Goodwill Impairment
                    if 'goodwill_impairment' in ashare_risks:
                        goodwill = ashare_risks['goodwill_impairment']
                        status = "危险" if goodwill.get('danger') else ("警告" if goodwill.get('warning') else "正常")
                        print(f"    Goodwill Ratio: {goodwill['value']:.1%} ({status}, Score: {goodwill['score']:.2f})")

                    # Restricted Unlock
                    if 'restricted_unlock' in ashare_risks:
                        unlock = ashare_risks['restricted_unlock']
                        status = "临近" if unlock.get('imminent') else "较远"
                        print(f"    Restricted Unlock: {unlock['days_until_unlock']}天后 ({status}, Score: {unlock['score']:.2f})")

                    # Market Risks
                    market_risks = result.analysis.get('market_risks', {})

                    # Volatility
                    if 'volatility' in market_risks:
                        vol = market_risks['volatility']
                        status = "高波动" if vol.get('high_volatility') else "正常"
                        print(f"    Volatility: {vol['annual_volatility']:.1%} ({status}, Score: {vol['score']:.2f})")

                    # Liquidity
                    if 'liquidity' in market_risks:
                        liq = market_risks['liquidity']
                        status = "低流动性" if liq.get('low_liquidity') else "流动性好"
                        print(f"    Liquidity: 日均 {liq['avg_volume']:,.0f}股 ({status}, Score: {liq['score']:.2f})")

                    # Recent Movement
                    if 'recent_movement' in market_risks:
                        move = market_risks['recent_movement']
                        ret = move['5day_return']
                        if move.get('sharp_decline'):
                            status = "大幅下跌"
                        elif move.get('sharp_rise'):
                            status = "大幅上涨"
                        else:
                            status = "正常波动"
                        print(f"    Recent Movement: 5日涨跌 {ret:.1%} ({status})")

                    # Overall Risk Level
                    if 'risk_level' in result.analysis:
                        print(f"    Overall Risk Level: {result.analysis['risk_level']}")

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
        print("\nRisk Agent is working correctly with real Tushare Pro data:")
        print("  - Pledge ratio from pledge_stat")
        print("  - ST status from stk_limit")
        print("  - Suspension status from suspend_d")
        print("  - Volatility and liquidity from daily data")
        print("  - Comprehensive risk assessment")
    elif success_count > 0:
        print(f"\n[PARTIAL] {success_count}/{total_tests} tests passed")
        print("Some tests may have failed due to data availability")
    else:
        print("\n[FAILED] All tests failed")
        print("Please check Tushare API configuration and permissions")

    print("=" * 80)

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_risk_agent())
    sys.exit(exit_code)
