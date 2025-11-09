"""
Test script for LLM integration.
Tests the LLM service and orchestrator integration.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from core.utils.llm_service import get_llm_service
from core.data.models import AgentAnalysisResult, SignalDirection
from datetime import datetime


async def test_llm_service():
    """Test LLM service with mock agent results."""

    logger.info("=" * 80)
    logger.info("Testing LLM Service Integration")
    logger.info("=" * 80)

    # Create mock agent results
    mock_results = {
        "TechnicalAnalysisAgent": AgentAnalysisResult(
            agent_name="TechnicalAnalysisAgent",
            symbol="600519.SH",
            score=0.75,
            direction=SignalDirection.LONG,
            confidence=0.80,
            analysis={
                "overall_score": 0.75,
                "rsi": {"value": 45.2, "signal": "neutral"},
                "macd": {"signal_type": "long", "bullish_crossover": True},
                "moving_averages": {
                    "ma_alignment_bullish": True,
                    "price_above_ma20": True
                },
                "trend": {"adx": 28.5, "strong_trend": True}
            },
            reasoning="技术指标显示多头信号：MACD金叉；均线多头排列；趋势强劲(ADX=28.5)",
            execution_time_ms=150,
            timestamp=datetime.utcnow(),
            is_error=False,
            error_message=None
        ),

        "FundamentalAgent": AgentAnalysisResult(
            agent_name="FundamentalAgent",
            symbol="600519.SH",
            score=0.60,
            direction=SignalDirection.LONG,
            confidence=0.70,
            analysis={
                "overall_score": 0.60,
                "valuation": "略微低估",
                "pe_ratio": {"value": 32.5, "undervalued": False, "reasonable": True},
                "pb_ratio": {"value": 8.2, "undervalued": False},
                "roe": {"value": 0.25, "excellent": True},
                "debt_to_equity": {"value": 0.15, "low_debt": True}
            },
            reasoning="整体估值：略微低估；ROE=25.0%，盈利能力优秀；负债率=15.0%，财务稳健",
            execution_time_ms=200,
            timestamp=datetime.utcnow(),
            is_error=False,
            error_message=None
        ),

        "MarketMonitorAgent": AgentAnalysisResult(
            agent_name="MarketMonitorAgent",
            symbol="600519.SH",
            score=0.55,
            direction=SignalDirection.LONG,
            confidence=0.65,
            analysis={
                "northbound_flow": {
                    "net_amount": 125000000.0,
                    "signal": "bullish"
                },
                "margin_balance": {
                    "change_pct": 2.5,
                    "signal": "positive"
                },
                "market_sentiment": "积极"
            },
            reasoning="北向资金净流入1.25亿；融资余额增长2.5%；市场情绪积极",
            execution_time_ms=180,
            timestamp=datetime.utcnow(),
            is_error=False,
            error_message=None
        ),

        "SentimentAgent": AgentAnalysisResult(
            agent_name="SentimentAgent",
            symbol="600519.SH",
            score=0.0,
            direction=SignalDirection.HOLD,
            confidence=0.2,
            analysis={
                "sentiment_score": 0.0,
                "description": "情绪分析功能开发中"
            },
            reasoning="情绪数据暂不可用",
            execution_time_ms=50,
            timestamp=datetime.utcnow(),
            is_error=False,
            error_message=None
        ),

        "PolicyAnalystAgent": AgentAnalysisResult(
            agent_name="PolicyAnalystAgent",
            symbol="600519.SH",
            score=0.0,
            direction=SignalDirection.HOLD,
            confidence=0.2,
            analysis={
                "impact_score": 0.0,
                "description": "政策分析功能开发中，暂无相关政策影响"
            },
            reasoning="暂无重大政策影响",
            execution_time_ms=50,
            timestamp=datetime.utcnow(),
            is_error=False,
            error_message=None
        ),

        "RiskManagerAgent": AgentAnalysisResult(
            agent_name="RiskManagerAgent",
            symbol="600519.SH",
            score=0.85,
            direction=SignalDirection.LONG,
            confidence=0.75,
            analysis={
                "risk_level": "low",
                "share_pledge_ratio": 0.0,
                "goodwill_ratio": 0.0,
                "volatility_score": 0.15
            },
            reasoning="低风险评级；无股权质押；无商誉减值风险；波动率较低",
            execution_time_ms=100,
            timestamp=datetime.utcnow(),
            is_error=False,
            error_message=None
        )
    }

    try:
        # Get LLM service
        llm_service = get_llm_service()
        logger.info(f"LLM Service initialized: {llm_service.base_url}, model={llm_service.model}")

        # Call LLM for analysis
        logger.info("\nCalling LLM for trading signal analysis...")
        result = await llm_service.analyze_trading_signal(
            symbol="600519.SH",
            agent_results=mock_results,
            market_context=None
        )

        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("LLM Analysis Result")
        logger.info("=" * 80)
        logger.info(f"Symbol: 600519.SH (贵州茅台)")
        logger.info(f"Recommended Direction: {result.get('recommended_direction')}")
        logger.info(f"Confidence: {result.get('confidence'):.2%}")
        logger.info(f"\nReasoning:\n{result.get('reasoning')}")
        logger.info(f"\nRisk Assessment:\n{result.get('risk_assessment')}")
        logger.info(f"\nKey Factors:")
        for i, factor in enumerate(result.get('key_factors', []), 1):
            logger.info(f"  {i}. {factor}")

        price_targets = result.get('price_targets', {})
        if price_targets:
            logger.info(f"\nPrice Targets:")
            if 'entry' in price_targets:
                logger.info(f"  Entry: {price_targets['entry']}")
            if 'stop_loss' in price_targets:
                logger.info(f"  Stop Loss: {price_targets['stop_loss']}")
            if 'take_profit' in price_targets:
                logger.info(f"  Take Profit: {price_targets['take_profit']}")

        logger.info("\n" + "=" * 80)
        logger.success("✓ LLM Integration Test PASSED")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"✗ LLM Integration Test FAILED: {e}")
        logger.exception(e)
        return False


async def main():
    """Main test function."""

    logger.info("Starting LLM Integration Tests...")
    logger.info("")

    # Test LLM service
    success = await test_llm_service()

    if success:
        logger.success("\n✓ All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n✗ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
