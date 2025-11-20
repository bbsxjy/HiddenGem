"""
Episodic Memory Bank - 细粒度案例库

存储完整的交易episode，包括：
- 市场状态快照
- 4个agents的完整分析
- 决策链（bull/bear辩论、风险评估）
- 实际执行和结果
- 抽象的经验教训

用于深度学习、模式识别、可复现分析。
"""

import chromadb
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# 导入统一日志系统
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tradingagents.utils.logging_init import get_logger
logger = get_logger("memory.episodic")


# ==================== Pydantic Models（Episode Schema） ====================

class MarketState(BaseModel):
    """市场状态快照"""
    date: str
    symbol: str
    price: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None

    # 技术指标
    rsi: Optional[float] = None
    macd: Optional[float] = None
    ma_5: Optional[float] = None
    ma_20: Optional[float] = None
    ma_60: Optional[float] = None

    # 市场环境
    vix: Optional[float] = None
    market_regime: Optional[str] = None  # bull, bear, sideways, volatile, panic
    sector: Optional[str] = None

    # 额外metadata
    metadata: Optional[Dict[str, Any]] = None


class AgentAnalysis(BaseModel):
    """单个Agent的完整分析"""
    agent_name: str
    full_report: str
    score: Optional[float] = None
    direction: Optional[str] = None  # long, short, hold
    confidence: Optional[float] = None
    key_points: Optional[List[str]] = None
    reasoning: Optional[str] = None


class DecisionChain(BaseModel):
    """完整的决策链"""
    # Bull vs Bear辩论
    bull_argument: Optional[str] = None
    bear_argument: Optional[str] = None
    investment_debate_conclusion: Optional[str] = None

    # 风险辩论
    aggressive_view: Optional[str] = None
    neutral_view: Optional[str] = None
    conservative_view: Optional[str] = None
    risk_debate_conclusion: Optional[str] = None

    # 最终决策
    final_decision: str
    final_confidence: Optional[float] = None


class TradeOutcome(BaseModel):
    """交易结果"""
    action: str  # BUY, SELL, HOLD
    position_size: Optional[float] = None
    entry_price: Optional[float] = None
    entry_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_date: Optional[str] = None
    holding_period_days: Optional[int] = None

    # 收益指标
    absolute_return: Optional[float] = None
    percentage_return: Optional[float] = None
    max_drawdown_during: Optional[float] = None
    sharpe_ratio: Optional[float] = None


class TradingEpisode(BaseModel):
    """完整的交易episode"""
    # 基本信息
    episode_id: str
    date: str
    symbol: str

    # 市场状态
    market_state: MarketState

    # Agent分析
    agent_analyses: Dict[str, AgentAnalysis]  # {agent_name: analysis}

    # 决策链
    decision_chain: DecisionChain

    # 交易结果（训练时才有）
    outcome: Optional[TradeOutcome] = None

    # 抽象的经验教训
    lesson: Optional[str] = None
    key_lesson: Optional[str] = None  # 浓缩版（用于embedding）
    success: Optional[bool] = None

    # Metadata
    created_at: str
    mode: str  # 'analysis' or 'training'
    metadata: Optional[Dict[str, Any]] = None


# ==================== Episodic Memory Bank ====================

class EpisodicMemoryBank:
    """Episode记忆库（细粒度案例库）

    存储完整的交易案例，用于：
    1. 深度学习：通过历史案例学习模式
    2. 可复现：给定日期可重现完整分析
    3. Meta-learning：学习"如何学习"
    """

    def __init__(
        self,
        persist_directory: str = None,
        embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ):
        """初始化Episode记忆库

        Args:
            persist_directory: 持久化目录，默认 ./memory_db/episodes
            embedding_model: Sentence-BERT模型名称
        """
        if persist_directory is None:
            persist_directory = os.getenv(
                'EPISODE_MEMORY_PATH',
                './memory_db/episodes'
            )

        self.persist_directory = persist_directory

        try:
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.collection = self.client.get_or_create_collection(
                name="trading_episodes",
                metadata={"description": "Complete trading episodes with full context"}
            )
            logger.info(f" [EpisodicMemory] 初始化完成: {persist_directory}")
        except Exception as e:
            logger.error(f" [EpisodicMemory] 初始化失败: {e}")
            raise

        # 初始化embedding模型
        try:
            self.encoder = SentenceTransformer(embedding_model)
            logger.info(f" [EpisodicMemory] Embedding模型加载完成: {embedding_model}")
        except Exception as e:
            logger.warning(f" [EpisodicMemory] Embedding模型加载失败: {e}")
            self.encoder = None

    def add_episode(self, episode: TradingEpisode) -> None:
        """添加一个完整的episode

        Args:
            episode: TradingEpisode对象

        Note:
            为了避免future leakage，embedding只基于当前时刻的信息：
            - 市场状态
            - Agent分析
            - 决策理由
            outcome（未来结果）会被存储但不参与embedding
        """
        try:
            # ========== 关键改进：只使用当前时刻的信息生成embedding ==========
            # 不包含outcome，避免future leakage
            if episode.key_lesson:
                # 如果提供了key_lesson，确保它不包含未来信息
                # key_lesson应该只描述"当时的决策逻辑"，不包含"事后结果"
                text_for_embedding = episode.key_lesson
            else:
                # 组合关键信息 - 只使用当前可知的信息
                text_for_embedding = f"""
                日期: {episode.date}
                股票: {episode.symbol}
                市场状态: {episode.market_state.market_regime or '未知'}
                RSI: {episode.market_state.rsi}
                MACD: {episode.market_state.macd}
                决策: {episode.decision_chain.final_decision}
                决策信心: {episode.decision_chain.final_confidence}
                """
                # 注意：不包含outcome，不包含absolute_return等未来信息

            if self.encoder:
                embedding = self.encoder.encode(text_for_embedding).tolist()
            else:
                logger.warning(" Encoder未初始化，使用空向量")
                embedding = [0.0] * 384  # MiniLM的维度

            # 序列化为JSON（完整episode，包含outcome，但outcome不参与embedding）
            episode_json = episode.model_dump_json()

            # 准备metadata（用于快速过滤）
            # outcome信息可以在metadata中，方便事后分析，但不影响相似度计算
            metadata = {
                'date': episode.date,
                'symbol': episode.symbol,
                'market_regime': episode.market_state.market_regime or 'unknown',
                'action': episode.outcome.action if episode.outcome else 'unknown',
                'mode': episode.mode,
                'success': str(episode.success) if episode.success is not None else 'unknown',
                # 标记：outcome仅供事后分析，不参与检索匹配
                '_outcome_for_analysis_only': 'true'
            }

            # 存入ChromaDB
            self.collection.add(
                ids=[episode.episode_id],
                embeddings=[embedding],
                documents=[episode_json],
                metadatas=[metadata]
            )

            logger.info(f" [EpisodicMemory] Episode已存储: {episode.episode_id} "
                       f"({episode.symbol} @ {episode.date}) - outcome已隔离")

        except Exception as e:
            logger.error(f" [EpisodicMemory] 存储Episode失败: {e}")
            raise

    def retrieve_similar(
        self,
        query_context: Dict[str, Any],
        top_k: int = 5,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[TradingEpisode]:
        """检索相似的历史episodes

        Args:
            query_context: 当前情况描述，例如：
                {
                    'market_regime': 'panic_selloff',
                    'vix': 75,
                    'rsi': 20,
                    'sector': 'consumer_staples'
                }
            top_k: 返回最相似的k个episodes
            filter_criteria: 过滤条件，例如 {'symbol': '600519.SH'}

        Returns:
            List[TradingEpisode]: 相似的episodes列表
        """
        try:
            # 构建查询文本
            query_text = self._build_query_text(query_context)

            if not self.encoder:
                logger.warning(" Encoder未初始化，返回空列表")
                return []

            # 生成query embedding
            query_embedding = self.encoder.encode(query_text).tolist()

            # 检索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.collection.count()),
                where=filter_criteria  # 可选的元数据过滤
            )

            # 解析结果
            episodes = []
            if results and results['documents'] and len(results['documents'][0]) > 0:
                for i, doc_json in enumerate(results['documents'][0]):
                    try:
                        episode_dict = json.loads(doc_json)
                        episode = TradingEpisode(**episode_dict)

                        # 添加相似度分数
                        if results['distances'] and len(results['distances'][0]) > i:
                            distance = results['distances'][0][i]
                            similarity = 1.0 - distance
                            if episode.metadata is None:
                                episode.metadata = {}
                            episode.metadata['similarity_score'] = similarity

                        episodes.append(episode)
                    except Exception as parse_error:
                        logger.warning(f" 解析Episode失败: {parse_error}")
                        continue

                logger.info(f" [EpisodicMemory] 检索完成: 找到{len(episodes)}个相似episode")
            else:
                logger.info(" [EpisodicMemory] 没有找到相似的episode")

            return episodes

        except Exception as e:
            logger.error(f" [EpisodicMemory] 检索失败: {e}")
            return []

    def get_episode_by_id(self, episode_id: str) -> Optional[TradingEpisode]:
        """根据ID获取特定episode

        Args:
            episode_id: Episode的唯一ID

        Returns:
            TradingEpisode或None
        """
        try:
            results = self.collection.get(ids=[episode_id])

            if results and results['documents'] and len(results['documents']) > 0:
                doc_json = results['documents'][0]
                episode_dict = json.loads(doc_json)
                episode = TradingEpisode(**episode_dict)
                logger.info(f" [EpisodicMemory] 获取Episode: {episode_id}")
                return episode
            else:
                logger.warning(f" [EpisodicMemory] Episode不存在: {episode_id}")
                return None

        except Exception as e:
            logger.error(f" [EpisodicMemory] 获取Episode失败: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取记忆库统计信息"""
        try:
            total_count = self.collection.count()

            # 获取所有episodes的metadata
            all_data = self.collection.get(include=['metadatas'])

            stats = {
                'total_episodes': total_count,
                'persist_directory': self.persist_directory
            }

            if all_data and all_data['metadatas']:
                metadatas = all_data['metadatas']

                # 统计各种信息
                symbols = [m.get('symbol') for m in metadatas]
                regimes = [m.get('market_regime') for m in metadatas]
                actions = [m.get('action') for m in metadatas]

                from collections import Counter
                stats['unique_symbols'] = len(set(symbols))
                stats['regime_distribution'] = dict(Counter(regimes))
                stats['action_distribution'] = dict(Counter(actions))

            logger.info(f" [EpisodicMemory] 统计信息: {total_count}个episodes")
            return stats

        except Exception as e:
            logger.error(f" [EpisodicMemory] 获取统计失败: {e}")
            return {'error': str(e)}

    def _build_query_text(self, context: Dict[str, Any]) -> str:
        """将context字典转换为查询文本"""
        parts = []

        if 'market_regime' in context:
            parts.append(f"市场regime: {context['market_regime']}")

        if 'vix' in context:
            parts.append(f"VIX: {context['vix']}")

        if 'rsi' in context:
            parts.append(f"RSI: {context['rsi']}")

        if 'sector' in context:
            parts.append(f"板块: {context['sector']}")

        if 'description' in context:
            parts.append(context['description'])

        return " ".join(parts)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 创建记忆库
    memory = EpisodicMemoryBank()

    # 创建一个示例episode
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
                full_report="技术面严重超卖...",
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

    # 存储
    memory.add_episode(test_episode)

    # 检索
    similar = memory.retrieve_similar({
        'market_regime': 'panic_selloff',
        'vix': 72,
        'rsi': 20
    })

    print(f"找到{len(similar)}个相似episode")

    # 统计
    stats = memory.get_statistics()
    print(f"统计信息: {stats}")
