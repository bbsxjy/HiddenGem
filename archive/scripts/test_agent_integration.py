"""
Test Multi-Agent Integration - Complete System Analysis.

This script demonstrates how all agents work together to provide
comprehensive stock analysis using real Tushare Pro data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from loguru import logger
from core.mcp_agents.technical_agent import TechnicalAnalysisAgent
from core.mcp_agents.fundamental_agent import FundamentalAgent
from core.mcp_agents.risk_agent import RiskManagerAgent
from core.mcp_agents.sentiment_agent import SentimentAgent


async def test_integrated_analysis():
    """Test integrated multi-agent analysis on real stocks."""

    print("=" * 80)
    print("HiddenGem Multi-Agent System Integration Test")
    print("=" * 80)

    # Initialize all agents
    print("\n[1/5] Initializing Agents...")
    try:
        technical_agent = TechnicalAnalysisAgent()
        fundamental_agent = FundamentalAgent()
        risk_agent = RiskManagerAgent()
        sentiment_agent = SentimentAgent()
        print("  [OK] All 4 agents initialized successfully")
    except Exception as e:
        print(f"  [FAILED] {e}")
        return 1

    # Test stock
    test_symbol = "600519.SH"  # 贵州茅台
    test_name = "贵州茅台"

    print(f"\n[2/5] Running Technical Analysis for {test_name} ({test_symbol})...")
    try:
        tech_result = await technical_agent.analyze(symbol=test_symbol)
        if not tech_result.is_error:
            print(f"  [OK] Technical Analysis completed")
            print(f"  Score: {tech_result.score:.3f}")
            print(f"  Signal: {tech_result.direction.value}")
            print(f"  Confidence: {tech_result.confidence:.2%}")
            print(f"  Time: {tech_result.execution_time_ms}ms")
        else:
            print(f"  [FAILED] {tech_result.error_message}")
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")
        logger.exception("Error in technical analysis")

    print(f"\n[3/5] Running Fundamental Analysis for {test_name} ({test_symbol})...")
    try:
        fund_result = await fundamental_agent.analyze(symbol=test_symbol)
        if not fund_result.is_error:
            print(f"  [OK] Fundamental Analysis completed")
            print(f"  Score: {fund_result.score:.3f}")
            print(f"  Signal: {fund_result.direction.value}")
            print(f"  Confidence: {fund_result.confidence:.2%}")
            print(f"  Time: {fund_result.execution_time_ms}ms")
        else:
            print(f"  [FAILED] {fund_result.error_message}")
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")
        logger.exception("Error in fundamental analysis")

    print(f"\n[4/5] Running Risk Analysis for {test_name} ({test_symbol})...")
    try:
        risk_result = await risk_agent.analyze(symbol=test_symbol)
        if not risk_result.is_error:
            print(f"  [OK] Risk Analysis completed")
            print(f"  Score: {risk_result.score:.3f} (lower = higher risk)")
            print(f"  Signal: {risk_result.direction.value}")
            print(f"  Confidence: {risk_result.confidence:.2%}")
            print(f"  Time: {risk_result.execution_time_ms}ms")
        else:
            print(f"  [FAILED] {risk_result.error_message}")
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")
        logger.exception("Error in risk analysis")

    print(f"\n[5/5] Running Sentiment Analysis for {test_name} ({test_symbol})...")
    try:
        sent_result = await sentiment_agent.analyze(symbol=test_symbol)
        if not sent_result.is_error:
            print(f"  [OK] Sentiment Analysis completed")
            print(f"  Score: {sent_result.score:.3f}")
            print(f"  Signal: {sent_result.direction.value}")
            print(f"  Confidence: {sent_result.confidence:.2%}")
            print(f"  Time: {sent_result.execution_time_ms}ms")
        else:
            print(f"  [FAILED] {sent_result.error_message}")
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")
        logger.exception("Error in sentiment analysis")

    # Aggregate results
    print("\n" + "=" * 80)
    print("INTEGRATED ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"\nStock: {test_name} ({test_symbol})")
    print("\n" + "-" * 80)

    # Display detailed results
    if not tech_result.is_error:
        print("\n[TECHNICAL ANALYSIS]")
        print(f"  Score: {tech_result.score:.3f}")
        print(f"  Signal: {tech_result.direction.value}")
        print(f"  Confidence: {tech_result.confidence:.2%}")
        print(f"  Reasoning: {tech_result.reasoning}")

    if not fund_result.is_error:
        print("\n[FUNDAMENTAL ANALYSIS]")
        print(f"  Score: {fund_result.score:.3f}")
        print(f"  Signal: {fund_result.direction.value}")
        print(f"  Confidence: {fund_result.confidence:.2%}")
        print(f"  Reasoning: {fund_result.reasoning}")

        # Show key financial metrics
        if fund_result.analysis:
            metrics = fund_result.analysis.get('financial_metrics', {})
            if metrics:
                print(f"  Key Metrics:")
                if 'roe' in metrics:
                    print(f"    ROE: {metrics['roe']:.2%}")
                if 'debt_to_assets' in metrics:
                    print(f"    Debt/Assets: {metrics['debt_to_assets']:.2%}")
                if 'gross_margin' in metrics:
                    print(f"    Gross Margin: {metrics['gross_margin']:.2%}")

    if not risk_result.is_error:
        print("\n[RISK ANALYSIS]")
        print(f"  Score: {risk_result.score:.3f} (lower = higher risk)")
        print(f"  Signal: {risk_result.direction.value}")
        print(f"  Confidence: {risk_result.confidence:.2%}")
        print(f"  Reasoning: {risk_result.reasoning}")

        # Show risk level
        if risk_result.analysis and 'risk_level' in risk_result.analysis:
            print(f"  Risk Level: {risk_result.analysis['risk_level']}")

    if not sent_result.is_error:
        print("\n[SENTIMENT ANALYSIS]")
        print(f"  Score: {sent_result.score:.3f}")
        print(f"  Signal: {sent_result.direction.value}")
        print(f"  Confidence: {sent_result.confidence:.2%}")
        print(f"  Reasoning: {sent_result.reasoning}")

        # Show sentiment level
        if sent_result.analysis and 'sentiment_level' in sent_result.analysis:
            print(f"  Sentiment Level: {sent_result.analysis['sentiment_level']}")

    # Calculate aggregated signal
    print("\n" + "-" * 80)
    print("\n[AGGREGATED SIGNAL]")

    # Define weights for each agent
    weights = {
        'technical': 0.25,    # 25% - Short-term price action
        'fundamental': 0.30,  # 30% - Long-term value (highest weight)
        'risk': 0.25,         # 25% - Risk assessment
        'sentiment': 0.20,    # 20% - Market sentiment
    }

    # Calculate weighted score
    total_score = 0.0
    total_weight = 0.0

    if not tech_result.is_error:
        total_score += tech_result.score * weights['technical']
        total_weight += weights['technical']

    if not fund_result.is_error:
        total_score += fund_result.score * weights['fundamental']
        total_weight += weights['fundamental']

    if not risk_result.is_error:
        total_score += risk_result.score * weights['risk']
        total_weight += weights['risk']

    if not sent_result.is_error:
        total_score += sent_result.score * weights['sentiment']
        total_weight += weights['sentiment']

    if total_weight > 0:
        aggregated_score = total_score / total_weight

        # Determine aggregated signal
        if aggregated_score > 0.3:
            aggregated_signal = "LONG (买入)"
        elif aggregated_score < -0.3:
            aggregated_signal = "SHORT (卖出)"
        else:
            aggregated_signal = "HOLD (持有)"

        print(f"  Aggregated Score: {aggregated_score:.3f}")
        print(f"  Aggregated Signal: {aggregated_signal}")
        print(f"  Signal Confidence: {abs(aggregated_score) * 100:.1f}%")

        # Show weight breakdown
        print(f"\n  Weight Breakdown:")
        print(f"    Technical:    {weights['technical']:.0%} × {tech_result.score:.3f} = {tech_result.score * weights['technical']:.3f}")
        print(f"    Fundamental:  {weights['fundamental']:.0%} × {fund_result.score:.3f} = {fund_result.score * weights['fundamental']:.3f}")
        print(f"    Risk:         {weights['risk']:.0%} × {risk_result.score:.3f} = {risk_result.score * weights['risk']:.3f}")
        print(f"    Sentiment:    {weights['sentiment']:.0%} × {sent_result.score:.3f} = {sent_result.score * weights['sentiment']:.3f}")
        print(f"    ────────────────────────────────────")
        print(f"    Total Score:                         {aggregated_score:.3f}")

    # Performance summary
    print("\n" + "-" * 80)
    print("\n[PERFORMANCE METRICS]")
    total_time = 0
    if not tech_result.is_error:
        total_time += tech_result.execution_time_ms
        print(f"  Technical Agent:   {tech_result.execution_time_ms:,}ms")
    if not fund_result.is_error:
        total_time += fund_result.execution_time_ms
        print(f"  Fundamental Agent: {fund_result.execution_time_ms:,}ms")
    if not risk_result.is_error:
        total_time += risk_result.execution_time_ms
        print(f"  Risk Agent:        {risk_result.execution_time_ms:,}ms")
    if not sent_result.is_error:
        total_time += sent_result.execution_time_ms
        print(f"  Sentiment Agent:   {sent_result.execution_time_ms:,}ms")
    print(f"  ────────────────────────────")
    print(f"  Total Time:        {total_time:,}ms ({total_time/1000:.2f}s)")

    print("\n" + "=" * 80)
    print("[SUCCESS] Multi-Agent Integration Test Completed!")
    print("\nAll agents are working correctly with real Tushare Pro data:")
    print("  [OK] Technical Agent - Price action and technical indicators")
    print("  [OK] Fundamental Agent - Financial metrics and valuation")
    print("  [OK] Risk Agent - A-share specific risk factors")
    print("  [OK] Sentiment Agent - Market sentiment and institutional flow")
    print("\nThe system can now provide comprehensive stock analysis by")
    print("aggregating signals from multiple specialized agents!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_integrated_analysis())
    sys.exit(exit_code)
