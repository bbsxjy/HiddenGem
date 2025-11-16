"""
记忆系统演示脚本

展示如何使用统一记忆系统（MemoryManager）进行检索和存储。

用法：
    python scripts/demo_memory_system.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# 导入记忆系统
from memory import (
    MemoryManager,
    MemoryMode,
    TradingEpisode,
    MarketState,
    AgentAnalysis,
    DecisionChain,
    TradeOutcome,
)

# 导入配置
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.utils.logging_init import get_logger

logger = get_logger("demo_memory")


def demo_analysis_mode():
    """演示分析模式（只读）"""
    logger.info("\n" + "="*60)
    logger.info("示例1: 分析模式（只读）")
    logger.info("="*60 + "\n")

    # 初始化为分析模式
    memory = MemoryManager(
        mode=MemoryMode.ANALYSIS,
        config=DEFAULT_CONFIG
    )

    logger.info(f" 记忆系统状态:")
    logger.info(f"   模式: {memory.get_mode()}")
    logger.info(f"   只读: {memory.is_read_only()}\n")

    #  允许：检索格言
    logger.info(" 1. 检索历史格言...")
    maxims = memory.retrieve_maxims(
        agent_name='bull',
        current_situation="市场恐慌性下跌，VIX达到75，但基本面完好，消费龙头严重超跌",
        n_matches=3
    )

    logger.info(f"   找到{len(maxims)}条相关格言:\n")
    for i, maxim in enumerate(maxims, 1):
        logger.info(f"   [{i}] 相似度: {maxim.get('similarity', 0):.2f}")
        logger.info(f"       情况: {maxim.get('situation', '')[:80]}...")
        logger.info(f"       建议: {maxim.get('recommendation', '')[:80]}...\n")

    #  允许：检索案例
    logger.info(" 2. 检索相似案例...")
    episodes = memory.retrieve_episodes(
        query_context={
            'market_regime': 'panic_selloff',
            'vix': 75,
            'rsi': 20,
            'sector': 'consumer_staples'
        },
        top_k=2
    )

    logger.info(f"   找到{len(episodes)}个相似案例:\n")
    for i, episode in enumerate(episodes, 1):
        logger.info(f"   [{i}] {episode.episode_id}")
        logger.info(f"       日期: {episode.date}")
        logger.info(f"       股票: {episode.symbol}")
        logger.info(f"       决策: {episode.decision_chain.final_decision[:50]}...")
        if episode.outcome:
            logger.info(f"       结果: {episode.outcome.action}, 收益: {episode.outcome.percentage_return:+.2%}")
        logger.info(f"       教训: {episode.key_lesson}\n")

    #  允许：混合检索
    logger.info(" 3. 混合检索（格言+案例）...")
    hybrid = memory.retrieve_hybrid(
        agent_name='bull',
        situation="市场恐慌性下跌，基本面完好",
        market_context={
            'market_regime': 'panic_selloff',
            'vix': 75
        },
        n_maxims=2,
        n_episodes=1
    )

    logger.info(f"   {hybrid['summary']}\n")

    #  禁止：尝试写入（会被拒绝）
    logger.info(" 4. 尝试写入（应该被拒绝）...")
    success = memory.add_maxim(
        agent_name='bull',
        situation="测试情况",
        recommendation="测试建议"
    )

    if not success:
        logger.info("    写入被正确拒绝（符合预期）\n")
    else:
        logger.error("    写入居然成功了（不应该发生！）\n")

    # 统计信息
    logger.info(" 5. 记忆库统计...")
    stats = memory.get_statistics()
    logger.info(f"   模式: {stats['mode']}")

    total_maxims = sum(v.get('count', 0) for v in stats['maxims'].values() if isinstance(v, dict))
    logger.info(f"   格言库: {total_maxims}条")

    total_episodes = stats['episodes'].get('total_episodes', 0)
    logger.info(f"   案例库: {total_episodes}个\n")


def demo_training_mode():
    """演示训练模式（读写）"""
    logger.info("\n" + "="*60)
    logger.info("示例2: 训练模式（读写）")
    logger.info("="*60 + "\n")

    # 初始化为训练模式
    memory = MemoryManager(
        mode=MemoryMode.TRAINING,
        config=DEFAULT_CONFIG
    )

    logger.info(f" 记忆系统状态:")
    logger.info(f"   模式: {memory.get_mode()}")
    logger.info(f"   只读: {memory.is_read_only()}\n")

    #  允许：检索
    logger.info(" 1. 检索格言（训练模式也可以检索）...")
    maxims = memory.retrieve_maxims(
        agent_name='bull',
        current_situation="恐慌性下跌",
        n_matches=1
    )
    logger.info(f"   找到{len(maxims)}条格言\n")

    #  允许：添加格言
    logger.info(" 2. 添加新格言...")
    success = memory.add_maxim(
        agent_name='bull',
        situation="COVID-19疫情恐慌，优质消费股超跌50%，基本面完好，现金流充足",
        recommendation="恐慌性下跌 + 基本面完好 + 充足现金流 = 黄金抄底机会，长期持有可获超额收益"
    )

    if success:
        logger.info("    格言添加成功\n")
    else:
        logger.error("    格言添加失败\n")

    #  允许：添加案例
    logger.info(" 3. 添加新案例...")

    # 创建一个示例Episode
    test_episode = TradingEpisode(
        episode_id="2020-03-23_600519.SH_demo",
        date="2020-03-23",
        symbol="600519.SH",
        market_state=MarketState(
            date="2020-03-23",
            symbol="600519.SH",
            price=850.0,
            rsi=15.0,
            vix=80.0,
            market_regime="panic_selloff",
            sector="consumer_staples"
        ),
        agent_analyses={
            'market': AgentAnalysis(
                agent_name='market',
                full_report="技术面严重超卖，RSI跌至15，MACD严重背离...",
                score=0.2,
                direction='hold',
                confidence=0.4
            ),
            'fundamentals': AgentAnalysis(
                agent_name='fundamentals',
                full_report="基本面完好，现金流充足，负债率低，疫情影响有限...",
                score=0.8,
                direction='long',
                confidence=0.9
            )
        },
        decision_chain=DecisionChain(
            bull_argument="基本面完好，恐慌是黄金坑机会",
            bear_argument="疫情不确定性太高，不宜抄底",
            investment_debate_conclusion="建议分批建仓，但需要风险控制",
            aggressive_view="大胆抄底，黄金坑千载难逢",
            neutral_view="小仓位试探，观察疫情进展",
            conservative_view="继续观望，等待明确信号",
            risk_debate_conclusion="采取中性策略，小仓位分批建仓",
            final_decision="分批买入10%仓位，设置止损8%",
            final_confidence=0.7
        ),
        outcome=TradeOutcome(
            action="BUY",
            position_size=0.1,
            entry_price=850.0,
            entry_date="2020-03-23",
            exit_price=1050.0,
            exit_date="2020-04-23",
            holding_period_days=30,
            absolute_return=200.0,
            percentage_return=0.235,  # +23.5%
            max_drawdown_during=-0.05
        ),
        lesson="COVID恐慌抄底成功案例：基本面完好的消费龙头在疫情恐慌中严重超跌，"
               "分批建仓并持有30天获得23.5%收益。关键因素：基本面完好 + 极度恐慌 + "
               "严格止损 + 耐心持有。",
        key_lesson="恐慌性下跌 + 基本面完好 = 抄底机会（+23.5%）",
        success=True,
        created_at=datetime.now().isoformat(),
        mode='training',
        metadata={
            'demo': True,
            'risk_level': 'medium',
            'market_condition': 'panic'
        }
    )

    success = memory.add_episode(test_episode)

    if success:
        logger.info("    案例添加成功")
        logger.info(f"   Episode ID: {test_episode.episode_id}")
        logger.info(f"   收益: {test_episode.outcome.percentage_return:+.2%}")
        logger.info(f"   教训: {test_episode.key_lesson}\n")
    else:
        logger.error("    案例添加失败\n")

    # 验证：检索刚才添加的案例
    logger.info(" 4. 验证：检索刚才添加的案例...")
    episodes = memory.retrieve_episodes(
        query_context={
            'market_regime': 'panic_selloff',
            'description': '疫情恐慌性下跌，消费股超跌'
        },
        top_k=1
    )

    if episodes and len(episodes) > 0:
        latest = episodes[0]
        logger.info(f"    找到最新案例: {latest.episode_id}")
        logger.info(f"   相似度: {latest.metadata.get('similarity_score', 0):.2f}\n")
    else:
        logger.warning("    未找到刚添加的案例\n")

    # 统计信息
    logger.info(" 5. 更新后的统计...")
    stats = memory.get_statistics()

    total_maxims = sum(v.get('count', 0) for v in stats['maxims'].values() if isinstance(v, dict))
    logger.info(f"   格言库: {total_maxims}条")

    total_episodes = stats['episodes'].get('total_episodes', 0)
    logger.info(f"   案例库: {total_episodes}个\n")


def main():
    """主函数"""
    logger.info("\n" + "="*60)
    logger.info(" 统一记忆系统演示")
    logger.info("="*60)

    # 演示分析模式（只读）
    demo_analysis_mode()

    # 演示训练模式（读写）
    demo_training_mode()

    logger.info("\n" + "="*60)
    logger.info(" 演示完成！")
    logger.info("="*60 + "\n")

    logger.info(" 下一步:")
    logger.info("   1. 查看 backend/memory/README.md 了解详细文档")
    logger.info("   2. 运行 time_travel_training.py 进行实际训练")
    logger.info("   3. 访问 http://localhost:8000/api/v1/memory/status 查看API状态\n")


if __name__ == "__main__":
    main()
