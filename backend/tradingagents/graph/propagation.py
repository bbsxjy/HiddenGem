# TradingAgents/graph/propagation.py

from typing import Dict, Any

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)

# 导入市场上下文模块
from tradingagents.utils.market_context import MarketContext


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=100):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self, company_name: str, trade_date: str
    ) -> Dict[str, Any]:
        """Create the initial state for the agent graph."""

        # 添加人类可读的时间描述，帮助LLM理解当前分析的时间点
        from datetime import datetime
        try:
            date_obj = datetime.strptime(str(trade_date), '%Y-%m-%d')
            date_display = date_obj.strftime('%Y年%m月%d日')
        except Exception as e:
            logger.warning(f" 日期格式化失败: {e}, 使用原始格式")
            date_display = str(trade_date)

        # 创建明确的分析上下文，用于在所有Agent间传递
        analysis_context = f"分析时间点：{date_display}，分析目标股票：{company_name}"

        # 🆕 生成市场上下文提示（包含交易时间、涨跌幅限制等）
        # 使用当前系统时间来判断是盘前/盘中/盘后
        current_time = datetime.now()
        market_context_prompt = MarketContext.generate_context_prompt(
            symbol=company_name,
            current_time=current_time
        )

        logger.info(f" [Propagator] 创建初始状态 - {analysis_context}")
        logger.info(f" [Propagator] 市场上下文: {MarketContext.is_trading_time(current_time)[1]}")

        return {
            "messages": [("human", company_name)],
            "company_of_interest": company_name,
            "trade_date": str(trade_date),
            "trade_date_display": date_display,  # 新增：人类可读格式
            "analysis_context": analysis_context,  # 新增：明确上下文
            "market_context_prompt": market_context_prompt,  # 🆕 市场上下文（交易时间、涨跌幅等）
            "investment_debate_state": InvestDebateState(
                {"history": "", "current_response": "", "count": 0}
            ),
            "risk_debate_state": RiskDebateState(
                {
                    "history": "",
                    "current_risky_response": "",
                    "current_safe_response": "",
                    "current_neutral_response": "",
                    "count": 0,
                }
            ),
            "market_report": "",
            "fundamentals_report": "",
            "sentiment_report": "",
            "news_report": "",
        }

    def get_graph_args(self) -> Dict[str, Any]:
        """Get arguments for the graph invocation."""
        return {
            "stream_mode": "values",
            "config": {"recursion_limit": self.max_recur_limit},
        }
