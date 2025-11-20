"""
Multi-Agent Strategy

整合 TradingAgents 的多 Agent 分析系统
"""

import pandas as pd
from typing import Dict, Any, Optional
from .strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)

# 尝试导入 TradingAgents
try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
    TRADINGAGENTS_AVAILABLE = True
except ImportError:
    TRADINGAGENTS_AVAILABLE = False
    logger.warning("TradingAgents not available")


class MultiAgentStrategy(BaseStrategy):
    """多 Agent 策略

    使用 TradingAgents 的 LLM 分析系统：
    - 7个专业 Agent（市场、基本面、情绪、新闻、Bull、Bear、风险）
    - LLM 辩论机制
    - 记忆系统

    使用单例模式避免重复初始化TradingGraph（初始化很重）
    """

    # 类级别的共享实例
    _shared_trading_graph: Optional['TradingAgentsGraph'] = None
    _initialization_lock = False
    _initialization_failed = False

    def __init__(self):
        super().__init__("MultiAgent")

        self.has_position = False
        self.last_signal = None

        # 使用共享的TradingGraph实例
        if TRADINGAGENTS_AVAILABLE:
            self.trading_graph = self._get_or_create_trading_graph()
        else:
            logger.warning("⚠️ TradingAgents 库不可用，将使用降级策略")
            self.trading_graph = None

    @classmethod
    def _get_or_create_trading_graph(cls) -> Optional['TradingAgentsGraph']:
        """获取或创建共享的TradingGraph实例（单例模式）"""

        # 如果已经初始化失败过，直接返回None
        if cls._initialization_failed:
            logger.warning("⚠️ TradingGraph 之前初始化失败，使用降级策略")
            return None

        # 如果已经有实例，直接返回
        if cls._shared_trading_graph is not None:
            logger.info("✅ 复用已有的 TradingGraph 实例")
            return cls._shared_trading_graph

        # 如果正在初始化中（其他线程），等待
        if cls._initialization_lock:
            logger.info("⏳ TradingGraph 正在初始化中，等待...")
            import time
            max_wait = 30  # 最多等待30秒
            waited = 0
            while cls._initialization_lock and waited < max_wait:
                time.sleep(1)
                waited += 1

            if cls._shared_trading_graph is not None:
                logger.info("✅ 等待完成，复用已有的 TradingGraph 实例")
                return cls._shared_trading_graph

        # 开始初始化
        cls._initialization_lock = True

        try:
            logger.info("🔄 首次初始化 TradingAgents Graph...")
            # 修复：使用关键字参数传递config，避免参数位置错误
            cls._shared_trading_graph = TradingAgentsGraph(config=DEFAULT_CONFIG)
            logger.info("✅ TradingAgents Graph 初始化成功（单例）")
            return cls._shared_trading_graph

        except Exception as e:
            logger.error(f"❌ TradingAgents Graph 初始化失败: {e}", exc_info=True)
            cls._initialization_failed = True
            return None

        finally:
            cls._initialization_lock = False

    @classmethod
    def reset_shared_instance(cls):
        """重置共享实例（用于测试或重启）"""
        cls._shared_trading_graph = None
        cls._initialization_failed = False
        logger.info("🔄 TradingGraph 共享实例已重置")

    def generate_signal(
        self,
        symbol: str,
        current_data: pd.DataFrame,
        portfolio_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成多 Agent 分析信号"""

        # 更新持仓状态
        self.has_position = portfolio_state.get('has_position', False)

        if self.trading_graph is None:
            # 降级到简单策略
            logger.debug(f"⚠️ [{symbol}] TradingAgents 不可用，使用降级策略")
            return self._simple_fallback(current_data, portfolio_state)

        try:
            # 获取当前日期
            if current_data.empty:
                logger.warning(f"⚠️ [{symbol}] 数据为空，使用降级策略")
                return self._simple_fallback(current_data, portfolio_state)

            current_date = current_data.iloc[-1].get('date', '')
            if isinstance(current_date, pd.Timestamp):
                current_date = current_date.strftime('%Y-%m-%d')

            logger.info(f"📊 [{symbol}] 调用 TradingAgents 分析 @ {current_date}")

            # 调用多 Agent 分析
            final_state, processed_signal = self.trading_graph.propagate(
                symbol,
                current_date
            )

            # 提取 LLM 分析结果
            llm_analysis = final_state.get('llm_analysis', {})
            direction = llm_analysis.get('recommended_direction', 'hold')
            confidence = llm_analysis.get('confidence', 0.5)
            reasoning = llm_analysis.get('reasoning', '')

            logger.info(f"✅ [{symbol}] 分析完成: {direction} (置信度: {confidence:.2f})")
            if reasoning:
                logger.info(f"   理由: {reasoning[:100]}...")

            # 转换为交易信号
            if direction == 'long' and not self.has_position and confidence > 0.6:
                action = 'buy'
                target_ratio = min(confidence, 0.5)  # 根据置信度调整买入比例，最高50%
            elif direction == 'short' and self.has_position:
                action = 'sell'
                target_ratio = 1.0  # 卖出全部
            else:
                action = 'hold'
                target_ratio = 0.0

            self.last_signal = {
                'action': action,
                'reason': f"Multi-Agent({direction}, {confidence:.2f}): {reasoning[:50]}",
                'confidence': confidence,
                'target_ratio': target_ratio,
                'llm_analysis': llm_analysis
            }

            return self.last_signal

        except Exception as e:
            logger.error(f"❌ [{symbol}] Multi-Agent 分析失败: {e}", exc_info=True)
            return self._simple_fallback(current_data, portfolio_state)

    def _simple_fallback(
        self,
        current_data: pd.DataFrame,
        portfolio_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """简单的降级策略"""
        # 买入持有作为降级方案
        self.has_position = portfolio_state.get('has_position', False)

        if not self.has_position:
            return {
                'action': 'buy',
                'reason': 'Multi-Agent fallback: 初始买入',
                'target_ratio': 0.1  # 使用10%现金
            }
        else:
            return {
                'action': 'hold',
                'reason': 'Multi-Agent fallback: 持有',
                'target_ratio': 0.0
            }

    def on_trade(self, trade_info: Dict[str, Any]):
        """交易执行后的回调"""
        side = trade_info.get('side')
        if side == 'buy':
            self.has_position = True
        elif side == 'sell':
            self.has_position = False

    def reset(self):
        """重置策略状态"""
        self.has_position = False
        self.last_signal = None
