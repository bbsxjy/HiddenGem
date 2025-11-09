"""
测试修复后的停牌检测功能
"""
import sys
from pathlib import Path
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from core.mcp_agents.risk_agent import RiskManagerAgent


async def test_suspension_fix():
    """测试修复后的停牌检测"""

    try:
        # Initialize Risk Agent
        risk_agent = RiskManagerAgent()

        # Test symbols
        test_symbols = [
            ('300502', '新易盛 - 之前误报停牌'),
            ('000001', '平安银行 - 对照组'),
        ]

        for symbol, description in test_symbols:
            print(f"\n{'='*80}")
            print(f"测试股票: {symbol} ({description})")
            print(f"{'='*80}")

            # Run risk analysis
            result = await risk_agent.analyze(symbol=symbol)

            if result.is_error:
                print(f"[ERROR] 分析失败: {result.reasoning}")
                continue

            # Extract suspension info
            ashare_risks = result.analysis.get('ashare_risks', {})
            suspension = ashare_risks.get('suspension', {})

            print(f"\n停牌状态检测结果:")
            print(f"  是否停牌: {suspension.get('is_suspended', 'N/A')}")

            if suspension.get('is_suspended'):
                print(f"  停牌日期: {suspension.get('suspend_date', 'N/A')}")
                print(f"  复牌日期: {suspension.get('resume_date', 'N/A')}")
                print(f"  停牌原因: {suspension.get('suspend_reason', 'N/A')}")
                print(f"  风险评分: {suspension.get('score', 'N/A')}")
            else:
                print(f"  [OK] 股票正常交易，未停牌")

            # Show overall reasoning
            print(f"\n总体风险评估:")
            print(f"  {result.reasoning}")
            print(f"\n风险评分: {result.score:.3f}")
            print(f"风险等级: {result.analysis.get('risk_level', 'N/A')}")
            print(f"信号方向: {result.direction.value if result.direction else 'N/A'}")
            print(f"信号置信度: {result.confidence:.2f}")

        print(f"\n{'='*80}")
        print("[OK] 测试完成")
        print(f"{'='*80}")

    except Exception as e:
        logger.exception(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_suspension_fix())
