"""
HiddenGem Memory System

统一的记忆系统，包含两层：
1. 粗粒度记忆（Maxims）：经验格言，快速检索
2. 细粒度记忆（Episodes）：完整案例，深度学习

只在训练模式下写入，分析模式只读。
"""

from .episodic_memory import (
    EpisodicMemoryBank,
    TradingEpisode,
    MarketState,
    AgentAnalysis,
    DecisionChain,
    TradeOutcome,
)
from .memory_manager import MemoryManager, MemoryMode

__all__ = [
    # Memory Banks
    'EpisodicMemoryBank',
    'MemoryManager',

    # Memory Mode
    'MemoryMode',

    # Episode Data Models
    'TradingEpisode',
    'MarketState',
    'AgentAnalysis',
    'DecisionChain',
    'TradeOutcome',
]
