"""
Backtester

回测引擎 - 支持 RL 策略和传统策略的性能评估
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
import pandas as pd
import numpy as np

from .strategy import BaseStrategy, BuyAndHoldStrategy
from .portfolio_manager import PortfolioManager
from .order_manager import OrderManager
from .order import OrderSide, OrderType
from .metrics import calculate_all_metrics

# 尝试导入 TradingAgents 数据接口
try:
    from tradingagents.dataflows.interface import get_stock_data_dataframe
    TRADINGAGENTS_AVAILABLE = True
except ImportError:
    TRADINGAGENTS_AVAILABLE = False
    print("Warning: TradingAgents not available. Using mock data for testing.")


class Backtester:
    """回测引擎

    支持对策略进行历史数据回测，评估策略性能
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0003,
        slippage_rate: float = 0.001,
        min_commission: float = 5.0
    ):
        """初始化回测引擎

        Args:
            strategy: 交易策略
            initial_capital: 初始资金
            commission_rate: 手续费率
            slippage_rate: 滑点率
            min_commission: 最低手续费
        """
        self.strategy = strategy
        self.initial_capital = initial_capital

        # 初始化投资组合和订单管理器
        self.portfolio = PortfolioManager(initial_capital)
        self.order_manager = OrderManager(
            self.portfolio,
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
            min_commission=min_commission
        )

        # 回测结果
        self.backtest_data: Optional[pd.DataFrame] = None
        self.trading_days: List[datetime] = []

    def load_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        data: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """加载回测数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            data: 自定义数据（如果提供，则不使用数据接口）

        Returns:
            股票数据
        """
        if data is not None:
            return data

        if TRADINGAGENTS_AVAILABLE:
            # 使用 TradingAgents 数据接口
            df = get_stock_data_dataframe(symbol, start_date, end_date)

            if df is None or df.empty:
                raise ValueError(f"No data found for {symbol} from {start_date} to {end_date}")

            return df
        else:
            # Mock 数据（仅用于测试）
            raise NotImplementedError("Please provide data parameter or install TradingAgents")

    def run(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        data: Optional[pd.DataFrame] = None,
        position_size: float = 1.0
    ) -> Dict[str, Any]:
        """执行回测

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            data: 自定义数据
            position_size: 仓位大小（0-1，如0.5表示每次使用50%资金）

        Returns:
            回测结果字典
        """
        # 加载数据
        df = self.load_data(symbol, start_date, end_date, data)

        # 确保数据按日期排序
        if 'date' in df.columns:
            df = df.sort_values('date').reset_index(drop=True)
        elif df.index.name == 'date' or isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()

        # 重置策略和投资组合
        self.strategy.reset()
        self.portfolio = PortfolioManager(self.initial_capital)
        self.order_manager = OrderManager(
            self.portfolio,
            commission_rate=self.order_manager.commission_rate,
            slippage_rate=self.order_manager.slippage_rate,
            min_commission=self.order_manager.min_commission
        )

        # 回测循环
        self.trading_days = []

        for idx in range(len(df)):
            current_date = df.iloc[idx]['date'] if 'date' in df.columns else df.index[idx]
            current_price = df.iloc[idx]['close']

            # 更新持仓价格
            if self.portfolio.has_position(symbol):
                self.portfolio.update_prices({symbol: current_price})

            # 准备当前数据（包含历史数据）
            current_data = df.iloc[:idx+1].copy()

            # 获取投资组合状态
            portfolio_state = {
                'cash': self.portfolio.cash,
                'total_equity': self.portfolio.total_equity,
                'positions': self.portfolio.get_positions_dict(),
                'has_position': self.portfolio.has_position(symbol)
            }

            # 策略生成信号
            signal = self.strategy.generate_signal(symbol, current_data, portfolio_state)

            # 执行交易
            action = signal.get('action', 'hold')

            if action == 'buy':
                # 买入逻辑
                if not self.portfolio.has_position(symbol):
                    # 计算买入数量
                    available_cash = self.portfolio.cash * position_size
                    quantity = int(available_cash / (current_price * 1.01))  # 预留1%的滑点空间

                    if quantity > 0:
                        # 创建并执行订单
                        order = self.order_manager.create_order(
                            symbol=symbol,
                            side=OrderSide.BUY,
                            quantity=quantity,
                            order_type=OrderType.MARKET
                        )
                        success = self.order_manager.execute_market_order(order, current_price)

                        if success:
                            self.strategy.on_trade({
                                'side': 'buy',
                                'symbol': symbol,
                                'quantity': quantity,
                                'price': order.filled_price,
                                'date': current_date
                            })

            elif action == 'sell':
                # 卖出逻辑
                if self.portfolio.has_position(symbol):
                    position = self.portfolio.get_position(symbol)
                    quantity = position.quantity

                    # 创建并执行订单
                    order = self.order_manager.create_order(
                        symbol=symbol,
                        side=OrderSide.SELL,
                        quantity=quantity,
                        order_type=OrderType.MARKET
                    )
                    success = self.order_manager.execute_market_order(order, current_price)

                    if success:
                        self.strategy.on_trade({
                            'side': 'sell',
                            'symbol': symbol,
                            'quantity': quantity,
                            'price': order.filled_price,
                            'date': current_date
                        })

            # 记录权益
            self.portfolio.record_equity(current_date)
            self.trading_days.append(current_date)

        # 生成回测报告
        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """生成回测报告

        Returns:
            回测报告字典
        """
        if not self.portfolio.equity_history:
            return {}

        # 提取权益曲线
        equity_curve = [e['total_equity'] for e in self.portfolio.equity_history]

        # 计算所有性能指标
        metrics = calculate_all_metrics(
            initial_capital=self.initial_capital,
            equity_curve=equity_curve,
            trades=self.portfolio.trade_history,
            trading_days=len(self.trading_days),
            risk_free_rate=0.03
        )

        # 构建完整报告
        report = {
            'strategy_name': self.strategy.name,
            'metrics': metrics,
            'equity_curve': self.portfolio.equity_history,
            'trades': self.portfolio.trade_history,
            'positions': self.portfolio.get_positions_dict(),
            'portfolio_summary': self.portfolio.get_summary()
        }

        return report

    def compare_with_benchmark(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """与基准策略（买入持有）比较

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            data: 自定义数据

        Returns:
            比较结果
        """
        # 运行当前策略
        strategy_result = self.run(symbol, start_date, end_date, data)

        # 运行基准策略
        benchmark_backtester = Backtester(
            strategy=BuyAndHoldStrategy(),
            initial_capital=self.initial_capital
        )
        benchmark_result = benchmark_backtester.run(symbol, start_date, end_date, data)

        # 比较结果
        comparison = {
            'strategy': {
                'name': self.strategy.name,
                'total_return': strategy_result['metrics']['total_return'],
                'sharpe_ratio': strategy_result['metrics']['sharpe_ratio'],
                'max_drawdown': strategy_result['metrics']['max_drawdown_pct'],
                'win_rate': strategy_result['metrics']['win_rate']
            },
            'benchmark': {
                'name': 'Buy & Hold',
                'total_return': benchmark_result['metrics']['total_return'],
                'sharpe_ratio': benchmark_result['metrics']['sharpe_ratio'],
                'max_drawdown': benchmark_result['metrics']['max_drawdown_pct'],
                'win_rate': benchmark_result['metrics'].get('win_rate', 0)
            },
            'outperformance': {
                'return_diff': strategy_result['metrics']['total_return'] - benchmark_result['metrics']['total_return'],
                'sharpe_diff': strategy_result['metrics']['sharpe_ratio'] - benchmark_result['metrics']['sharpe_ratio']
            }
        }

        return comparison
