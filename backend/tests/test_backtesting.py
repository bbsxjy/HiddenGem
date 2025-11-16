"""
Unit Tests for Backtesting System

回测系统单元测试
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from trading.order import Order, OrderType, OrderSide, OrderStatus
from trading.position import Position
from trading.portfolio_manager import PortfolioManager
from trading.order_manager import OrderManager
from trading.metrics import (
    calculate_returns,
    calculate_total_return,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_all_metrics
)
from trading.strategy import BaseStrategy, BuyAndHoldStrategy
from trading.backtester import Backtester


# ============================================================================
# Order Tests
# ============================================================================

def test_order_creation():
    """测试订单创建"""
    order = Order(
        symbol="600519.SH",
        side=OrderSide.BUY,
        quantity=100,
        order_type=OrderType.MARKET
    )

    assert order.symbol == "600519.SH"
    assert order.side == OrderSide.BUY
    assert order.quantity == 100
    assert order.status == OrderStatus.PENDING
    assert order.is_buy is True
    assert order.is_sell is False


def test_order_properties():
    """测试订单属性"""
    order = Order(
        symbol="600519.SH",
        side=OrderSide.BUY,
        quantity=100
    )

    assert order.remaining_quantity == 100

    # 模拟部分成交
    order.filled_quantity = 50
    assert order.remaining_quantity == 50


# ============================================================================
# Position Tests
# ============================================================================

def test_position_creation():
    """测试持仓创建"""
    pos = Position(
        symbol="600519.SH",
        quantity=100,
        avg_price=100.0,
        current_price=105.0
    )

    assert pos.symbol == "600519.SH"
    assert pos.quantity == 100
    assert pos.market_value == 10500.0
    assert pos.cost_basis == 10000.0
    assert pos.unrealized_pnl == 500.0
    assert pos.unrealized_pnl_pct == 5.0


def test_position_add_shares():
    """测试增加持仓"""
    pos = Position(
        symbol="600519.SH",
        quantity=100,
        avg_price=100.0,
        current_price=100.0
    )

    # 以110元再买入100股
    pos.add_shares(100, 110.0)

    assert pos.quantity == 200
    assert pos.avg_price == 105.0  # (100*100 + 100*110) / 200


def test_position_reduce_shares():
    """测试减少持仓"""
    pos = Position(
        symbol="600519.SH",
        quantity=100,
        avg_price=100.0,
        current_price=110.0
    )

    # 卖出50股
    realized_pnl = pos.reduce_shares(50)

    assert pos.quantity == 50
    assert realized_pnl == 500.0  # 50 * (110 - 100)


# ============================================================================
# Portfolio Manager Tests
# ============================================================================

def test_portfolio_initialization():
    """测试投资组合初始化"""
    portfolio = PortfolioManager(initial_capital=100000)

    assert portfolio.initial_capital == 100000
    assert portfolio.cash == 100000
    assert portfolio.total_equity == 100000
    assert len(portfolio.positions) == 0


def test_portfolio_buy():
    """测试买入操作"""
    portfolio = PortfolioManager(initial_capital=100000)

    # 买入100股，价格100，手续费10
    portfolio.execute_buy("600519.SH", 100, 100.0, 10.0)

    assert portfolio.cash == 100000 - 10010  # 扣除成本和手续费
    assert portfolio.has_position("600519.SH")
    assert portfolio.get_position("600519.SH").quantity == 100


def test_portfolio_sell():
    """测试卖出操作"""
    portfolio = PortfolioManager(initial_capital=100000)

    # 先买入
    portfolio.execute_buy("600519.SH", 100, 100.0, 10.0)

    # 更新价格到110
    portfolio.update_prices({"600519.SH": 110.0})

    # 卖出
    portfolio.execute_sell("600519.SH", 100, 110.0, 10.0)

    # 检查盈亏
    assert not portfolio.has_position("600519.SH")
    # 初始100000 - 买入10010 + 卖出(110*100-10) = 100980
    assert abs(portfolio.cash - 100980) < 0.01


# ============================================================================
# Metrics Tests
# ============================================================================

def test_calculate_returns():
    """测试收益率计算"""
    equity_curve = [100, 105, 110, 108]
    returns = calculate_returns(equity_curve)

    expected = np.array([0.05, 0.047619, -0.018182])
    np.testing.assert_array_almost_equal(returns, expected, decimal=5)


def test_calculate_total_return():
    """测试总收益率计算"""
    total_return = calculate_total_return(100000, 120000)
    assert total_return == 20.0


def test_calculate_max_drawdown():
    """测试最大回撤计算"""
    equity_curve = [100, 120, 110, 130, 100, 140]
    dd_info = calculate_max_drawdown(equity_curve)

    # 从130跌到100，回撤30，百分比 30/130 = 23.08%
    assert dd_info['max_drawdown'] > 0
    assert dd_info['max_drawdown_pct'] > 0


def test_calculate_win_rate():
    """测试胜率计算"""
    trades = [
        {'side': 'buy', 'realized_pnl': 0},
        {'side': 'sell', 'realized_pnl': 100},
        {'side': 'sell', 'realized_pnl': -50},
        {'side': 'sell', 'realized_pnl': 200},
    ]

    win_info = calculate_win_rate(trades)

    assert win_info['total_trades'] == 3  # 只统计卖出交易
    assert win_info['winning_trades'] == 2
    assert win_info['losing_trades'] == 1
    assert abs(win_info['win_rate'] - 66.67) < 0.1


# ============================================================================
# Strategy Tests
# ============================================================================

def test_buy_and_hold_strategy():
    """测试买入持有策略"""
    strategy = BuyAndHoldStrategy()

    # 模拟数据
    df = pd.DataFrame({'close': [100, 105, 110]})
    portfolio_state = {'has_position': False}

    # 第一次应该买入
    signal = strategy.generate_signal("600519.SH", df, portfolio_state)
    assert signal['action'] == 'buy'

    # 模拟买入成功
    strategy.on_trade({'side': 'buy'})

    # 之后应该持有
    portfolio_state = {'has_position': True}
    signal = strategy.generate_signal("600519.SH", df, portfolio_state)
    assert signal['action'] == 'hold'


# ============================================================================
# Backtester Tests
# ============================================================================

def test_backtester_initialization():
    """测试回测器初始化"""
    strategy = BuyAndHoldStrategy()
    backtester = Backtester(strategy, initial_capital=100000)

    assert backtester.initial_capital == 100000
    assert backtester.strategy.name == "BuyAndHold"


def test_backtester_with_mock_data():
    """测试回测器（使用模拟数据）"""
    strategy = BuyAndHoldStrategy()
    backtester = Backtester(strategy, initial_capital=100000)

    # 创建模拟数据
    dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
    mock_data = pd.DataFrame({
        'date': dates,
        'close': [100 + i * 2 for i in range(10)],  # 从100涨到118
        'open': [100 + i * 2 for i in range(10)],
        'high': [102 + i * 2 for i in range(10)],
        'low': [98 + i * 2 for i in range(10)],
        'volume': [1000000] * 10
    })

    # 运行回测
    result = backtester.run(
        symbol="600519.SH",
        start_date="2024-01-01",
        end_date="2024-01-10",
        data=mock_data
    )

    # 验证结果
    assert 'metrics' in result
    assert 'equity_curve' in result
    assert 'trades' in result

    # 应该有盈利（价格上涨）
    metrics = result['metrics']
    assert metrics['total_return'] > 0


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_backtest_workflow():
    """测试完整回测流程"""
    # 1. 创建策略
    strategy = BuyAndHoldStrategy()

    # 2. 创建回测器
    backtester = Backtester(
        strategy,
        initial_capital=100000,
        commission_rate=0.0003,
        slippage_rate=0.001
    )

    # 3. 准备数据
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    mock_data = pd.DataFrame({
        'date': dates,
        'close': 100 + np.cumsum(np.random.randn(30) * 2),  # 随机游走
        'open': 100,
        'high': 105,
        'low': 95,
        'volume': 1000000
    })

    # 4. 运行回测
    result = backtester.run(
        symbol="600519.SH",
        start_date="2024-01-01",
        end_date="2024-01-30",
        data=mock_data
    )

    # 5. 验证结果完整性
    assert 'metrics' in result
    assert 'equity_curve' in result
    assert 'trades' in result
    assert 'portfolio_summary' in result

    # 6. 生成报告
    from trading.report_generator import ReportGenerator
    reporter = ReportGenerator(result)

    json_report = reporter.generate_json_report()
    assert 'metrics' in json_report

    html_report = reporter.generate_html_report()
    assert '回测报告' in html_report
    assert strategy.name in html_report

    text_summary = reporter.generate_summary_text()
    assert '回测报告摘要' in text_summary


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
