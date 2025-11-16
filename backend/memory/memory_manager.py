"""
统一记忆管理器 - Memory Manager

整合两层记忆系统：
1. 粗粒度记忆（Maxims）：FinancialSituationMemory - 抽象的经验格言
2. 细粒度记忆（Episodes）：EpisodicMemoryBank - 完整的交易案例

核心功能：
- 区分模式：analysis（只读）vs training（读写）
- 双层检索：先查格言，再查案例
- 统一接口：简化上层调用
"""

import os
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from enum import Enum

# 导入两层记忆系统
from tradingagents.agents.utils.memory import FinancialSituationMemory
from .episodic_memory import (
    EpisodicMemoryBank,
    TradingEpisode,
    MarketState,
    AgentAnalysis,
    DecisionChain,
    TradeOutcome,
)

# 导入统一日志系统
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tradingagents.utils.logging_init import get_logger
logger = get_logger("memory.manager")


class MemoryMode(str, Enum):
    """记忆系统模式"""
    ANALYSIS = "analysis"  # 分析模式：只读，不写入任何记忆
    TRAINING = "training"  # 训练模式：读写，会存储新的经验


class MemoryManager:
    """统一记忆管理器

    整合粗粒度记忆（格言库）和细粒度记忆（案例库），
    并强制执行模式限制：
    - analysis模式：只能检索，不能写入
    - training模式：可以检索和写入
    """

    def __init__(
        self,
        mode: MemoryMode,
        config: Dict[str, Any],
        maxim_persist_path: Optional[str] = None,
        episode_persist_path: Optional[str] = None,
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ):
        """初始化记忆管理器

        Args:
            mode: 运行模式（analysis/training）
            config: TradingAgents配置字典
            maxim_persist_path: 格言库持久化路径
            episode_persist_path: 案例库持久化路径
            embedding_model: Sentence-BERT模型名称
        """
        self.mode = MemoryMode(mode)
        self.config = config

        logger.info(f" [MemoryManager] 初始化模式: {self.mode.value}")

        # 初始化格言库（粗粒度记忆）- 总是持久化
        logger.info(f" [MemoryManager] 初始化格言库（粗粒度）...")
        self.maxim_memory = {
            'bull': FinancialSituationMemory("bull_memory_persistent", config, persistent=True),
            'bear': FinancialSituationMemory("bear_memory_persistent", config, persistent=True),
            'trader': FinancialSituationMemory("trader_memory_persistent", config, persistent=True),
            'invest_judge': FinancialSituationMemory("invest_judge_memory_persistent", config, persistent=True),
            'risk_manager': FinancialSituationMemory("risk_manager_memory_persistent", config, persistent=True),
        }

        # 初始化案例库（细粒度记忆）
        logger.info(f" [MemoryManager] 初始化案例库（细粒度）...")
        if episode_persist_path is None:
            episode_persist_path = os.getenv(
                'EPISODE_MEMORY_PATH',
                './memory_db/episodes'
            )

        self.episode_memory = EpisodicMemoryBank(
            persist_directory=episode_persist_path,
            embedding_model=embedding_model
        )

        # 模式验证标志
        self._write_attempted = False

        logger.info(f" [MemoryManager] 初始化完成，模式: {self.mode.value}")
        logger.info(f"   - 格言库: 5个专业记忆库（Bull/Bear/Trader/Judge/RiskManager）")
        logger.info(f"   - 案例库: {episode_persist_path}")
        logger.info(f"   - 写入权限: {'禁止' if self.mode == MemoryMode.ANALYSIS else '允许'}")

    # ==================== 检索接口（分析和训练都可用） ====================

    def retrieve_maxims(
        self,
        agent_name: str,
        current_situation: str,
        n_matches: int = 3
    ) -> List[Dict[str, Any]]:
        """检索相关的经验格言

        Args:
            agent_name: Agent名称（bull/bear/trader/invest_judge/risk_manager）
            current_situation: 当前情况描述
            n_matches: 返回数量

        Returns:
            格言列表，每个格言包含：
                - situation: 情况描述
                - recommendation: 建议
                - similarity: 相似度
        """
        if agent_name not in self.maxim_memory:
            logger.warning(f" [MemoryManager] 未知Agent: {agent_name}")
            return []

        try:
            memories = self.maxim_memory[agent_name].get_memories(
                current_situation,
                n_matches=n_matches
            )

            logger.info(f" [MemoryManager] 检索格言: {agent_name}, 找到{len(memories)}条")
            return memories

        except Exception as e:
            logger.error(f" [MemoryManager] 检索格言失败: {e}")
            return []

    def retrieve_episodes(
        self,
        query_context: Dict[str, Any],
        top_k: int = 5,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[TradingEpisode]:
        """检索相似的历史交易案例

        Args:
            query_context: 查询上下文，例如：
                {
                    'market_regime': 'panic_selloff',
                    'vix': 75,
                    'rsi': 20,
                    'sector': 'consumer_staples'
                }
            top_k: 返回数量
            filter_criteria: 过滤条件，例如 {'symbol': '600519.SH'}

        Returns:
            相似的交易案例列表
        """
        try:
            episodes = self.episode_memory.retrieve_similar(
                query_context=query_context,
                top_k=top_k,
                filter_criteria=filter_criteria
            )

            logger.info(f" [MemoryManager] 检索案例: 找到{len(episodes)}个相似episode")
            return episodes

        except Exception as e:
            logger.error(f" [MemoryManager] 检索案例失败: {e}")
            return []

    def retrieve_hybrid(
        self,
        agent_name: str,
        situation: str,
        market_context: Dict[str, Any],
        n_maxims: int = 3,
        n_episodes: int = 2
    ) -> Dict[str, Any]:
        """混合检索：同时查询格言和案例

        Args:
            agent_name: Agent名称
            situation: 当前情况描述
            market_context: 市场上下文（用于案例检索）
            n_maxims: 格言数量
            n_episodes: 案例数量

        Returns:
            {
                'maxims': [...],
                'episodes': [...],
                'summary': '...'
            }
        """
        maxims = self.retrieve_maxims(agent_name, situation, n_maxims)
        episodes = self.retrieve_episodes(market_context, n_episodes)

        logger.info(f" [MemoryManager] 混合检索: {len(maxims)}条格言 + {len(episodes)}个案例")

        return {
            'maxims': maxims,
            'episodes': episodes,
            'summary': f"检索到{len(maxims)}条相关格言和{len(episodes)}个相似案例"
        }

    # ==================== 写入接口（仅训练模式可用） ====================

    def add_maxim(
        self,
        agent_name: str,
        situation: str,
        recommendation: str
    ) -> bool:
        """添加新的经验格言（仅训练模式）

        Args:
            agent_name: Agent名称
            situation: 情况描述
            recommendation: 建议

        Returns:
            是否成功
        """
        if not self._check_write_permission("add_maxim"):
            return False

        if agent_name not in self.maxim_memory:
            logger.warning(f" [MemoryManager] 未知Agent: {agent_name}")
            return False

        try:
            self.maxim_memory[agent_name].add_situations([(situation, recommendation)])
            logger.info(f" [MemoryManager] 添加格言: {agent_name}")
            return True

        except Exception as e:
            logger.error(f" [MemoryManager] 添加格言失败: {e}")
            return False

    def add_episode(self, episode: TradingEpisode) -> bool:
        """添加新的交易案例（仅训练模式）

        Args:
            episode: 交易案例对象

        Returns:
            是否成功
        """
        if not self._check_write_permission("add_episode"):
            return False

        try:
            self.episode_memory.add_episode(episode)
            logger.info(f" [MemoryManager] 添加案例: {episode.episode_id}")
            return True

        except Exception as e:
            logger.error(f" [MemoryManager] 添加案例失败: {e}")
            return False

    def batch_add_maxims(
        self,
        agent_name: str,
        situations_and_advice: List[tuple]
    ) -> bool:
        """批量添加格言（仅训练模式）

        Args:
            agent_name: Agent名称
            situations_and_advice: [(situation, recommendation), ...]

        Returns:
            是否成功
        """
        if not self._check_write_permission("batch_add_maxims"):
            return False

        if agent_name not in self.maxim_memory:
            logger.warning(f" [MemoryManager] 未知Agent: {agent_name}")
            return False

        try:
            self.maxim_memory[agent_name].add_situations(situations_and_advice)
            logger.info(f" [MemoryManager] 批量添加格言: {agent_name}, {len(situations_and_advice)}条")
            return True

        except Exception as e:
            logger.error(f" [MemoryManager] 批量添加格言失败: {e}")
            return False

    # ==================== 工具方法 ====================

    def _check_write_permission(self, operation: str) -> bool:
        """检查写入权限

        Args:
            operation: 操作名称

        Returns:
            是否允许写入
        """
        if self.mode == MemoryMode.ANALYSIS:
            if not self._write_attempted:
                self._write_attempted = True
                logger.error(f" [MemoryManager] 分析模式禁止写入操作: {operation}")
                logger.error(f"   当前模式: {self.mode.value}")
                logger.error(f"   如需写入，请使用training模式初始化")
            return False

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """获取记忆库统计信息

        Returns:
            {
                'mode': 'analysis/training',
                'maxims': {...},
                'episodes': {...}
            }
        """
        stats = {
            'mode': self.mode.value,
            'maxims': {},
            'episodes': {}
        }

        # 格言库统计
        for agent_name, memory in self.maxim_memory.items():
            try:
                stats['maxims'][agent_name] = {
                    'count': memory.situation_collection.count(),
                    'persistent': memory.persistent
                }
            except Exception as e:
                logger.warning(f" [MemoryManager] 获取{agent_name}统计失败: {e}")
                stats['maxims'][agent_name] = {'error': str(e)}

        # 案例库统计
        try:
            stats['episodes'] = self.episode_memory.get_statistics()
        except Exception as e:
            logger.warning(f" [MemoryManager] 获取案例库统计失败: {e}")
            stats['episodes'] = {'error': str(e)}

        return stats

    def get_mode(self) -> str:
        """获取当前模式"""
        return self.mode.value

    def is_read_only(self) -> bool:
        """是否只读模式"""
        return self.mode == MemoryMode.ANALYSIS


# ==================== 使用示例 ====================

if __name__ == "__main__":
    from tradingagents.default_config import DEFAULT_CONFIG

    # ===== 示例1: 分析模式（只读） =====
    logger.info("=" * 60)
    logger.info("示例1: 分析模式（只读）")
    logger.info("=" * 60)

    analysis_memory = MemoryManager(
        mode=MemoryMode.ANALYSIS,
        config=DEFAULT_CONFIG
    )

    #  允许：检索格言
    maxims = analysis_memory.retrieve_maxims(
        agent_name='bull',
        current_situation="市场恐慌性下跌，VIX达到75，但基本面完好",
        n_matches=3
    )
    print(f"\n检索到{len(maxims)}条格言")

    #  允许：检索案例
    episodes = analysis_memory.retrieve_episodes(
        query_context={
            'market_regime': 'panic_selloff',
            'vix': 75,
            'rsi': 20
        },
        top_k=2
    )
    print(f"检索到{len(episodes)}个案例")

    #  禁止：添加格言（会被拒绝）
    success = analysis_memory.add_maxim(
        agent_name='bull',
        situation="测试情况",
        recommendation="测试建议"
    )
    print(f"\n尝试添加格言: {'成功' if success else '失败（预期行为）'}")

    # ===== 示例2: 训练模式（读写） =====
    logger.info("\n" + "=" * 60)
    logger.info("示例2: 训练模式（读写）")
    logger.info("=" * 60)

    training_memory = MemoryManager(
        mode=MemoryMode.TRAINING,
        config=DEFAULT_CONFIG
    )

    #  允许：检索
    maxims = training_memory.retrieve_maxims(
        agent_name='bull',
        current_situation="市场恐慌性下跌",
        n_matches=2
    )
    print(f"\n检索到{len(maxims)}条格言")

    #  允许：添加格言
    success = training_memory.add_maxim(
        agent_name='bull',
        situation="COVID恐慌时，基本面完好的消费龙头超跌",
        recommendation="恐慌性下跌 + 基本面完好 = 黄金抄底机会"
    )
    print(f"添加格言: {'成功' if success else '失败'}")

    #  允许：添加案例
    test_episode = TradingEpisode(
        episode_id="2020-03-15_600519.SH",
        date="2020-03-15",
        symbol="600519.SH",
        market_state=MarketState(
            date="2020-03-15",
            symbol="600519.SH",
            price=800.0,
            rsi=18.0,
            vix=75.0,
            market_regime="panic_selloff",
            sector="consumer_staples"
        ),
        agent_analyses={
            'market': AgentAnalysis(
                agent_name='market',
                full_report="技术面严重超卖，RSI=18",
                score=0.3,
                direction='hold'
            )
        },
        decision_chain=DecisionChain(
            bull_argument="基本面完好，恐慌是机会",
            bear_argument="不确定性太高",
            final_decision="分批抄底"
        ),
        outcome=TradeOutcome(
            action="BUY",
            position_size=0.05,
            entry_price=800.0,
            exit_price=920.0,
            percentage_return=0.15
        ),
        lesson="COVID恐慌时，基本面完好的消费龙头超跌=黄金坑",
        key_lesson="恐慌性下跌 + 基本面完好 = 抄底机会",
        success=True,
        created_at=datetime.now().isoformat(),
        mode='training'
    )

    success = training_memory.add_episode(test_episode)
    print(f"添加案例: {'成功' if success else '失败'}")

    # 统计信息
    stats = training_memory.get_statistics()
    print(f"\n统计信息:")
    print(f"  模式: {stats['mode']}")
    print(f"  格言库: {sum(v.get('count', 0) for v in stats['maxims'].values() if isinstance(v, dict))}条")
    print(f"  案例库: {stats['episodes'].get('total_episodes', 0)}个")
