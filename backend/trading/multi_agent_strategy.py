"""
Multi-Agent Strategy

整合 TradingAgents 的多 Agent 分析系统
"""

import pandas as pd
from typing import Dict, Any
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
    """

    def __init__(self):
        super().__init__("MultiAgent")

        self.trading_graph = None
        self.initialization_attempts = 0
        self.max_init_attempts = 3

        if TRADINGAGENTS_AVAILABLE:
            self._initialize_trading_graph()
        else:
            logger.warning("⚠️ TradingAgents 库不可用，将使用降级策略")

        self.has_position = False
        self.last_signal = None

    def _initialize_trading_graph(self):
        """初始化 TradingAgents Graph，支持重试"""
        while self.initialization_attempts < self.max_init_attempts:
            try:
                self.initialization_attempts += 1
                logger.info(f"🔄 正在初始化 TradingAgents Graph (尝试 {self.initialization_attempts}/{self.max_init_attempts})...")

                self.trading_graph = TradingAgentsGraph(DEFAULT_CONFIG)

                logger.info("✅ TradingAgents Graph 初始化成功")
                return

            except Exception as e:
                logger.error(f"❌ TradingAgents Graph 初始化失败 (尝试 {self.initialization_attempts}/{self.max_init_attempts}): {e}")

                if self.initialization_attempts >= self.max_init_attempts:
                    logger.error(f"❌ TradingAgents Graph 初始化失败达到最大尝试次数，将使用降级策略")
                    self.trading_graph = None
                else:
                    import time
                    time.sleep(2)  # 重试前等待2秒

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
            elif direction == 'short' and self.has_position:
                action = 'sell'
            else:
                action = 'hold'

            self.last_signal = {
                'action': action,
                'reason': f"Multi-Agent({direction}, {confidence:.2f}): {reasoning[:50]}",
                'confidence': confidence,
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
                'reason': 'Multi-Agent fallback: 初始买入'
            }
        else:
            return {
                'action': 'hold',
                'reason': 'Multi-Agent fallback: 持有'
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
