"""
Performance Metrics Calculator

性能指标计算模块 - 计算夏普比率、最大回撤、卡玛比率等指标
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Union, Optional
from datetime import datetime


def calculate_returns(equity_curve: Union[List[float], pd.Series]) -> np.ndarray:
    """计算收益率序列

    Args:
        equity_curve: 权益曲线

    Returns:
        收益率数组
    """
    if isinstance(equity_curve, list):
        equity_curve = np.array(equity_curve)
    elif isinstance(equity_curve, pd.Series):
        equity_curve = equity_curve.values

    returns = np.diff(equity_curve) / equity_curve[:-1]
    return returns


def calculate_total_return(initial_value: float, final_value: float) -> float:
    """计算总收益率

    Args:
        initial_value: 初始价值
        final_value: 最终价值

    Returns:
        总收益率（百分比）
    """
    if initial_value == 0:
        return 0.0
    return ((final_value - initial_value) / initial_value) * 100


def calculate_annualized_return(
    total_return: float,
    days: int,
    trading_days_per_year: int = 252
) -> float:
    """计算年化收益率

    Args:
        total_return: 总收益率（小数形式，如0.15表示15%）
        days: 总天数
        trading_days_per_year: 每年交易日数（默认252）

    Returns:
        年化收益率（百分比）
    """
    if days == 0:
        return 0.0

    years = days / trading_days_per_year
    annualized = (1 + total_return / 100) ** (1 / years) - 1
    return annualized * 100


def calculate_volatility(
    returns: Union[List[float], np.ndarray],
    annualized: bool = True,
    trading_days_per_year: int = 252
) -> float:
    """计算波动率（标准差）

    Args:
        returns: 收益率序列
        annualized: 是否年化
        trading_days_per_year: 每年交易日数

    Returns:
        波动率（百分比）
    """
    if isinstance(returns, list):
        returns = np.array(returns)

    if len(returns) == 0:
        return 0.0

    volatility = np.std(returns, ddof=1)

    if annualized:
        volatility *= np.sqrt(trading_days_per_year)

    return volatility * 100


def calculate_sharpe_ratio(
    returns: Union[List[float], np.ndarray],
    risk_free_rate: float = 0.03,
    trading_days_per_year: int = 252
) -> float:
    """计算夏普比率

    Sharpe Ratio = (年化收益率 - 无风险利率) / 年化波动率

    Args:
        returns: 收益率序列
        risk_free_rate: 无风险利率（年化，如0.03表示3%）
        trading_days_per_year: 每年交易日数

    Returns:
        夏普比率
    """
    if isinstance(returns, list):
        returns = np.array(returns)

    if len(returns) == 0:
        return 0.0

    # 计算年化收益率
    mean_return = np.mean(returns)
    annualized_return = mean_return * trading_days_per_year

    # 计算年化波动率
    volatility = np.std(returns, ddof=1)
    annualized_volatility = volatility * np.sqrt(trading_days_per_year)

    if annualized_volatility == 0:
        return 0.0

    # 夏普比率
    sharpe = (annualized_return - risk_free_rate) / annualized_volatility
    return sharpe


def calculate_sortino_ratio(
    returns: Union[List[float], np.ndarray],
    risk_free_rate: float = 0.03,
    trading_days_per_year: int = 252
) -> float:
    """计算索提诺比率

    Sortino Ratio = (年化收益率 - 无风险利率) / 下行波动率

    Args:
        returns: 收益率序列
        risk_free_rate: 无风险利率
        trading_days_per_year: 每年交易日数

    Returns:
        索提诺比率
    """
    if isinstance(returns, list):
        returns = np.array(returns)

    if len(returns) == 0:
        return 0.0

    # 计算年化收益率
    mean_return = np.mean(returns)
    annualized_return = mean_return * trading_days_per_year

    # 计算下行波动率（只考虑负收益）
    downside_returns = returns[returns < 0]
    if len(downside_returns) == 0:
        return float('inf')  # 没有下行风险

    downside_volatility = np.std(downside_returns, ddof=1)
    annualized_downside_volatility = downside_volatility * np.sqrt(trading_days_per_year)

    if annualized_downside_volatility == 0:
        return float('inf')

    # 索提诺比率
    sortino = (annualized_return - risk_free_rate) / annualized_downside_volatility
    return sortino


def calculate_max_drawdown(equity_curve: Union[List[float], np.ndarray, pd.Series]) -> Dict[str, float]:
    """计算最大回撤

    Args:
        equity_curve: 权益曲线

    Returns:
        包含最大回撤信息的字典
    """
    if isinstance(equity_curve, list):
        equity_curve = np.array(equity_curve)
    elif isinstance(equity_curve, pd.Series):
        equity_curve = equity_curve.values

    if len(equity_curve) == 0:
        return {'max_drawdown': 0.0, 'max_drawdown_pct': 0.0}

    # 计算累计最大值
    cumulative_max = np.maximum.accumulate(equity_curve)

    # 计算回撤
    drawdowns = equity_curve - cumulative_max
    drawdowns_pct = (drawdowns / cumulative_max) * 100

    # 最大回撤
    max_drawdown = np.min(drawdowns)
    max_drawdown_pct = np.min(drawdowns_pct)

    # 找到最大回撤的位置
    max_dd_idx = np.argmin(drawdowns)
    peak_idx = np.argmax(cumulative_max[:max_dd_idx + 1]) if max_dd_idx > 0 else 0

    return {
        'max_drawdown': abs(max_drawdown),
        'max_drawdown_pct': abs(max_drawdown_pct),
        'peak_index': int(peak_idx),
        'trough_index': int(max_dd_idx)
    }


def calculate_calmar_ratio(
    annualized_return: float,
    max_drawdown_pct: float
) -> float:
    """计算卡玛比率

    Calmar Ratio = 年化收益率 / 最大回撤

    Args:
        annualized_return: 年化收益率（百分比）
        max_drawdown_pct: 最大回撤（百分比）

    Returns:
        卡玛比率
    """
    if max_drawdown_pct == 0:
        return 0.0

    return annualized_return / max_drawdown_pct


def calculate_win_rate(trades: List[dict]) -> Dict[str, Union[float, int]]:
    """计算胜率

    Args:
        trades: 交易记录列表

    Returns:
        包含胜率信息的字典
    """
    if not trades:
        return {
            'win_rate': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

    # 只统计卖出交易（有实现盈亏）
    sell_trades = [t for t in trades if t.get('side') == 'sell']

    if not sell_trades:
        return {
            'win_rate': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }

    # 统计盈利和亏损交易
    winning_trades = sum(1 for t in sell_trades if t.get('realized_pnl', 0) > 0)
    losing_trades = sum(1 for t in sell_trades if t.get('realized_pnl', 0) < 0)
    total_trades = len(sell_trades)

    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    return {
        'win_rate': win_rate,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades
    }


def calculate_profit_factor(trades: List[dict]) -> float:
    """计算盈亏比

    Profit Factor = 总盈利 / 总亏损

    Args:
        trades: 交易记录列表

    Returns:
        盈亏比
    """
    if not trades:
        return 0.0

    # 只统计卖出交易
    sell_trades = [t for t in trades if t.get('side') == 'sell']

    if not sell_trades:
        return 0.0

    # 计算总盈利和总亏损
    total_profit = sum(t.get('realized_pnl', 0) for t in sell_trades if t.get('realized_pnl', 0) > 0)
    total_loss = abs(sum(t.get('realized_pnl', 0) for t in sell_trades if t.get('realized_pnl', 0) < 0))

    if total_loss == 0:
        return float('inf') if total_profit > 0 else 0.0

    return total_profit / total_loss


def calculate_all_metrics(
    initial_capital: float,
    equity_curve: List[float],
    trades: List[dict],
    trading_days: int,
    risk_free_rate: float = 0.03
) -> Dict[str, Union[float, int, dict]]:
    """计算所有性能指标

    Args:
        initial_capital: 初始资金
        equity_curve: 权益曲线
        trades: 交易记录
        trading_days: 交易天数
        risk_free_rate: 无风险利率

    Returns:
        包含所有指标的字典
    """
    if not equity_curve or len(equity_curve) < 2:
        return {}

    # 计算收益率
    returns = calculate_returns(equity_curve)

    # 基础指标
    final_value = equity_curve[-1]
    total_return = calculate_total_return(initial_capital, final_value)
    annualized_return = calculate_annualized_return(total_return, trading_days)

    # 风险指标
    volatility = calculate_volatility(returns, annualized=True)
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate)
    sortino = calculate_sortino_ratio(returns, risk_free_rate)

    # 回撤指标
    drawdown_info = calculate_max_drawdown(equity_curve)
    calmar = calculate_calmar_ratio(annualized_return, drawdown_info['max_drawdown_pct'])

    # 交易指标
    win_rate_info = calculate_win_rate(trades)
    profit_factor = calculate_profit_factor(trades)

    return {
        # 收益指标
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,

        # 风险指标
        'volatility': volatility,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,

        # 回撤指标
        'max_drawdown': drawdown_info['max_drawdown'],
        'max_drawdown_pct': drawdown_info['max_drawdown_pct'],
        'calmar_ratio': calmar,

        # 交易指标
        'win_rate': win_rate_info['win_rate'],
        'total_trades': win_rate_info['total_trades'],
        'winning_trades': win_rate_info['winning_trades'],
        'losing_trades': win_rate_info['losing_trades'],
        'profit_factor': profit_factor,

        # 时间指标
        'trading_days': trading_days
    }
