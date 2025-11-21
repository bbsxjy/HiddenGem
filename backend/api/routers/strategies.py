"""
Strategies API Router

提供策略管理的API端点
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import traceback
import logging

# 导入回测引擎和策略
from trading.backtester import Backtester
from trading.strategy import BaseStrategy, BuyAndHoldStrategy
from trading.technical_strategy import TechnicalStrategy
from trading.multi_agent_strategy import MultiAgentStrategy
from trading.fundamental_strategy import FundamentalStrategy
from trading.rl_strategy import RLStrategy

router = APIRouter()
logger = logging.getLogger(__name__)


def _create_strategy_instance(strategy_name: str) -> BaseStrategy:
    """根据策略名称创建策略实例（内部函数）

    Args:
        strategy_name: 策略名称（rl, technical, fundamental, multi-agent）

    Returns:
        策略实例
    """
    logger.info(f" 创建策略实例: {strategy_name}")

    # 根据策略名称创建不同的策略
    if strategy_name == "technical":
        # 技术分析策略
        strategy = TechnicalStrategy(
            rsi_period=14,
            rsi_overbought=70,
            rsi_oversold=30,
            ma_short=5,
            ma_long=20,
            use_macd=True
        )
        logger.info("    技术分析策略（RSI + MA + MACD）")

    elif strategy_name == "multi-agent":
        # 多 Agent 策略（使用 LLM）
        strategy = MultiAgentStrategy()
        logger.info("    Multi-Agent 策略（7个Agent + LLM辩论）")

    elif strategy_name == "fundamental":
        # 基本面策略（价值投资）
        strategy = FundamentalStrategy(
            max_pe=20,
            max_pb=3,
            min_roe=10,
            max_debt_ratio=70,
            min_fundamental_score=6.5,
            min_valuation_score=7.0
        )
        logger.info("    基本面价值投资策略（PE/PB/ROE/债务率）")

    elif strategy_name == "rl":
        # RL 策略（使用预训练的 PPO 模型）
        strategy = RLStrategy(model_path="models/production/final_model.zip")
        logger.info("    RL 策略（使用 PPO 强化学习模型）")

    else:
        # 默认使用买入持有策略
        strategy = BuyAndHoldStrategy()
        logger.warning(f"    未知策略类型 '{strategy_name}'，使用买入持有")

    # 调试信息
    logger.info(f"   策略类型: {type(strategy).__name__}")
    logger.info(f"   策略名称: {strategy.name}")

    return strategy


# Pydantic Models
class Strategy(BaseModel):
    strategy_name: str
    display_name: str
    description: str
    strategy_type: str  # rl, technical, fundamental, multi-agent
    is_active: bool
    created_at: str
    updated_at: str
    parameters: Dict[str, Any]


class BacktestResult(BaseModel):
    strategy_name: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    total_return: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    avg_holding_days: float


@router.get("/")
async def get_strategies():
    """获取所有策略列表

    注意：当前返回的是系统可用策略的静态配置，而非数据库存储的用户自定义策略。
    这些策略代表了系统实际支持的策略类型（RL、技术面、基本面、多Agent）。

    TODO (Future): 实现用户自定义策略的数据库存储和管理
    - 需要MongoDB collection: strategies
    - 需要实现StrategyRepository
    - 支持用户创建、修改、删除自定义策略配置
    """

    # 系统内置策略列表（静态配置）
    # 这些是实际可用于回测的策略类型
    strategies = [
        {
            "strategy_name": "rl_agent_v1",
            "display_name": "RL Agent 策略 v1",
            "description": "基于强化学习的智能交易策略，使用PPO算法",
            "strategy_type": "rl",
            "is_active": True,
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "updated_at": datetime.now().isoformat(),
            "parameters": {
                "learning_rate": 0.0003,
                "gamma": 0.99,
                "initial_cash": 100000,
                "max_position_size": 0.2
            }
        },
        {
            "strategy_name": "multi_agent_consensus",
            "display_name": "多Agent共识策略",
            "description": "综合技术面、基本面、情绪面等多个Agent的分析结果",
            "strategy_type": "multi-agent",
            "is_active": True,
            "created_at": (datetime.now() - timedelta(days=60)).isoformat(),
            "updated_at": datetime.now().isoformat(),
            "parameters": {
                "min_consensus": 0.75,
                "agent_weights": {
                    "technical": 1.0,
                    "fundamental": 1.0,
                    "sentiment": 0.8,
                    "policy": 0.9
                }
            }
        },
        {
            "strategy_name": "technical_momentum",
            "display_name": "技术面动量策略",
            "description": "基于技术指标（RSI、MACD、MA）的动量交易策略",
            "strategy_type": "technical",
            "is_active": False,
            "created_at": (datetime.now() - timedelta(days=90)).isoformat(),
            "updated_at": (datetime.now() - timedelta(days=10)).isoformat(),
            "parameters": {
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "use_macd": True
            }
        },
        {
            "strategy_name": "fundamental_value",
            "display_name": "基本面价值策略",
            "description": "基于财务指标和估值的价值投资策略",
            "strategy_type": "fundamental",
            "is_active": True,
            "created_at": (datetime.now() - timedelta(days=45)).isoformat(),
            "updated_at": datetime.now().isoformat(),
            "parameters": {
                "max_pe_ratio": 20,
                "min_roe": 0.15,
                "min_pb_ratio": 1.0
            }
        }
    ]

    return {
        "success": True,
        "data": strategies,
        "total": len(strategies),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/{strategy_name}")
async def get_strategy(strategy_name: str):
    """获取单个策略详情

    TODO (Future): 从数据库获取用户自定义策略
    当前返回静态配置的策略信息
    """

    strategy = {
        "strategy_name": strategy_name,
        "display_name": "RL Agent 策略 v1",
        "description": "基于强化学习的智能交易策略，使用PPO算法",
        "strategy_type": "rl",
        "is_active": True,
        "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
        "updated_at": datetime.now().isoformat(),
        "parameters": {
            "learning_rate": 0.0003,
            "gamma": 0.99,
            "initial_cash": 100000,
            "max_position_size": 0.2
        },
        "performance": {
            "total_trades": 156,
            "win_rate": 0.65,
            "avg_return": 0.023,
            "sharpe_ratio": 1.85
        }
    }

    return {
        "success": True,
        "data": strategy,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/")
async def create_strategy(strategy: dict):
    """创建新策略

    TODO (Future): 实现策略持久化到MongoDB
    当前仅返回echo响应，不实际存储
    需要实现：
    - MongoDB strategies collection
    - StrategyRepository.create()
    - 参数验证和schema定义
    """

    new_strategy = {
        "strategy_name": strategy.get("strategy_name"),
        "display_name": strategy.get("display_name"),
        "description": strategy.get("description", ""),
        "strategy_type": strategy.get("strategy_type", "technical"),
        "is_active": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "parameters": strategy.get("parameters", {})
    }

    return {
        "success": True,
        "data": new_strategy,
        "message": "策略创建成功",
        "timestamp": datetime.now().isoformat()
    }


@router.put("/{strategy_name}")
async def update_strategy(strategy_name: str, updates: dict):
    """更新策略配置

    TODO (Future): 实现策略更新到MongoDB
    当前仅返回echo响应，不实际存储
    需要实现：
    - MongoDB strategies collection
    - StrategyRepository.update()
    """

    updated_strategy = {
        "strategy_name": strategy_name,
        "display_name": updates.get("display_name", "Updated Strategy"),
        "description": updates.get("description", ""),
        "strategy_type": updates.get("strategy_type", "technical"),
        "is_active": updates.get("is_active", True),
        "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
        "updated_at": datetime.now().isoformat(),
        "parameters": updates.get("parameters", {})
    }

    return {
        "success": True,
        "data": updated_strategy,
        "message": "策略更新成功",
        "timestamp": datetime.now().isoformat()
    }


@router.delete("/{strategy_name}")
async def delete_strategy(strategy_name: str):
    """删除策略

    TODO (Future): 实现从MongoDB删除策略
    当前仅返回成功响应，不实际删除
    需要实现：
    - MongoDB strategies collection
    - StrategyRepository.delete()
    """

    return {
        "success": True,
        "message": f"策略 {strategy_name} 已删除",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/{strategy_name}/backtest")
async def run_backtest(
    strategy_name: str,
    symbol: str = Query(..., description="Stock symbol to backtest"),
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    initial_capital: float = Query(100000, description="Initial capital")
):
    """运行策略回测（使用真实数据和回测引擎）"""
    try:
        # 创建策略实例
        logger.info(f" [BACKTEST] 开始回测: {symbol} ({start_date} ~ {end_date})")
        logger.info(f" [BACKTEST] 策略类型: {strategy_name}")
        logger.info(f" [BACKTEST] 初始资金: ¥{initial_capital:,.0f}")

        strategy = _create_strategy_instance(strategy_name)

        # 创建回测引擎
        backtester = Backtester(
            strategy=strategy,
            initial_capital=initial_capital,
            commission_rate=0.0003,  # A股手续费约0.03%
            slippage_rate=0.001,      # 滑点0.1%
            min_commission=5.0        # 最低手续费5元
        )

        # 运行回测
        backtest_report = backtester.run(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            position_size=0.95  # 使用95%的可用资金
        )

        # 提取指标
        metrics = backtest_report.get('metrics', {})

        # 转换 equity_curve 为前端期望的格式
        equity_history = backtest_report.get('equity_curve', [])
        equity_curve_formatted = []

        for i, point in enumerate(equity_history):
            # 将 timestamp 转换为 date 字符串
            date_str = str(point.get('timestamp'))
            if isinstance(point.get('timestamp'), datetime):
                date_str = point['timestamp'].strftime('%Y-%m-%d')

            # 计算日收益率（如果有前一天的数据）
            daily_return = None
            if i > 0:
                prev_value = equity_history[i-1].get('total_equity', initial_capital)
                current_value = point.get('total_equity', initial_capital)
                if prev_value > 0:
                    daily_return = ((current_value - prev_value) / prev_value) * 100

            equity_curve_formatted.append({
                'date': date_str,
                'value': point.get('total_equity', initial_capital),
                'daily_return': daily_return
            })

        # 计算平均持仓天数
        trades = backtest_report.get('trades', [])
        avg_holding_days = 0.0
        if trades:
            # 计算完整的买卖对
            completed_trades = [t for t in trades if t.get('side') == 'sell']
            if completed_trades:
                total_holding_days = 0
                for sell_trade in completed_trades:
                    # 假设 trade 包含 holding_days 字段
                    total_holding_days += sell_trade.get('holding_days', 0)
                avg_holding_days = total_holding_days / len(completed_trades) if completed_trades else 0.0

        # 格式化为前端期望的格式
        result = {
            "strategy_name": strategy_name,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "final_value": metrics.get('final_value', initial_capital),
            "total_return": metrics.get('final_value', initial_capital) - initial_capital,
            "total_return_pct": metrics.get('total_return', 0.0),
            "sharpe_ratio": metrics.get('sharpe_ratio', 0.0),
            "max_drawdown": metrics.get('max_drawdown_pct', 0.0),
            "win_rate": metrics.get('win_rate', 0.0) / 100.0,  # 转换为0-1的小数
            "total_trades": metrics.get('total_trades', 0),
            "avg_holding_days": avg_holding_days,
            "equity_curve": equity_curve_formatted,
        }

        return {
            "success": True,
            "data": result,
            "message": "回测完成",
            "timestamp": datetime.now().isoformat()
        }

    except ValueError as e:
        # 数据错误（如股票代码不存在、日期范围无效）
        logger.error(f" [BACKTEST] 数据错误: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 其他错误
        error_detail = f"回测失败: {str(e)}\n{traceback.format_exc()}"
        logger.error(f" [BACKTEST] 错误: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_name}/stats")
async def get_strategy_stats(strategy_name: str):
    """获取策略统计数据

    TODO (Future): 从MongoDB/Redis获取真实统计
    需要实现：
    - 交易历史记录存储（MongoDB trades collection）
    - 实时统计计算逻辑
    - 缓存层（Redis）用于高频访问的统计数据
    当前返回模拟数据
    """

    stats = {
        "strategy_name": strategy_name,
        "total_trades": 156,
        "profitable_trades": 102,
        "losing_trades": 54,
        "win_rate": 0.654,
        "avg_profit": 1250.50,
        "avg_loss": -680.30,
        "profit_factor": 1.85,
        "sharpe_ratio": 1.92,
        "max_drawdown": -12.5,
        "total_return": 23500.0,
        "total_return_pct": 23.5,
        "last_updated": datetime.now().isoformat()
    }

    return {
        "success": True,
        "data": stats,
        "timestamp": datetime.now().isoformat()
    }
