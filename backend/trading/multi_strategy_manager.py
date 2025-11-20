"""
Multi-Strategy Manager

管理多个策略的并行运行和表现追踪
"""

from typing import Dict, List, Any
from datetime import datetime
import logging

from .strategy import BaseStrategy
from .simulated_broker import SimulatedBroker
from .portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)


class StrategyPerformance:
    """策略表现追踪"""

    def __init__(self, strategy_id: str, strategy_name: str, initial_cash: float):
        """初始化策略表现追踪

        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            initial_cash: 初始资金
        """
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.initial_cash = initial_cash

        # 交易统计
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0

        # 持仓信息
        self.num_positions = 0
        self.current_cash = initial_cash
        self.current_value = initial_cash

        # 交易记录
        self.trade_history: List[Dict] = []

    def record_trade(self, trade_info: Dict[str, Any]):
        """记录交易

        Args:
            trade_info: 交易信息
        """
        self.total_trades += 1
        self.trade_history.append({
            'timestamp': datetime.now().isoformat(),
            **trade_info
        })

        # 更新盈亏统计
        pnl = trade_info.get('pnl', 0.0)
        if pnl > 0:
            self.winning_trades += 1
            self.total_profit += pnl
        elif pnl < 0:
            self.losing_trades += 1
            self.total_loss += abs(pnl)

    def update_portfolio(self, cash: float, positions: Dict, market_prices: Dict):
        """更新投资组合状态

        Args:
            cash: 当前现金
            positions: 持仓字典 {symbol: quantity}
            market_prices: 市场价格 {symbol: price}
        """
        self.current_cash = cash
        self.num_positions = len(positions)

        # 计算总资产
        total_value = cash
        for symbol, quantity in positions.items():
            price = market_prices.get(symbol, 0)
            total_value += quantity * price

        self.current_value = total_value

    @property
    def profit_loss(self) -> float:
        """总盈亏"""
        return self.current_value - self.initial_cash

    @property
    def profit_loss_pct(self) -> float:
        """盈亏百分比"""
        if self.initial_cash <= 0:
            return 0.0
        return (self.profit_loss / self.initial_cash) * 100

    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'profit_loss': self.profit_loss,
            'profit_loss_pct': self.profit_loss_pct,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'num_positions': self.num_positions,
            'current_cash': self.current_cash,
            'current_value': self.current_value,
        }


class MultiStrategyManager:
    """多策略管理器

    管理多个策略的并行运行，每个策略有独立的broker和投资组合
    """

    def __init__(
        self,
        strategies: Dict[str, BaseStrategy],
        initial_cash: float = 100000.0,
        shared_broker: SimulatedBroker = None  # 新增：共享broker
    ):
        """初始化多策略管理器

        Args:
            strategies: 策略字典 {mode_id: strategy}
            initial_cash: 每个策略的初始资金
            shared_broker: 共享的broker（如果提供，所有策略共享同一个broker）
        """
        self.strategies = strategies
        self.initial_cash = initial_cash
        self.use_shared_broker = shared_broker is not None

        # 为每个策略创建独立的broker或使用共享broker
        self.brokers: Dict[str, SimulatedBroker] = {}
        self.performances: Dict[str, StrategyPerformance] = {}

        for strategy_id, strategy in strategies.items():
            # 如果提供了shared_broker，所有策略共享
            if self.use_shared_broker:
                self.brokers[strategy_id] = shared_broker
                logger.info(f"✓ [{strategy.name}] 使用共享Broker")
            else:
                # 创建独立的broker
                self.brokers[strategy_id] = SimulatedBroker(initial_cash=initial_cash)
                logger.info(f"✓ [{strategy.name}] 创建独立Broker")

            # 创建表现追踪
            self.performances[strategy_id] = StrategyPerformance(
                strategy_id=strategy_id,
                strategy_name=strategy.name,
                initial_cash=initial_cash
            )

            logger.info(f"✓ [{strategy.name}] 策略管理器已初始化，初始资金: ¥{initial_cash:,.2f}")

    def generate_signals(
        self,
        symbol: str,
        current_data,
        market_prices: Dict[str, float]
    ) -> Dict[str, Dict[str, Any]]:
        """为所有策略生成交易信号

        Args:
            symbol: 股票代码
            current_data: 当前数据
            market_prices: 市场价格

        Returns:
            所有策略的信号 {strategy_id: signal}
        """
        all_signals = {}

        for strategy_id, strategy in self.strategies.items():
            broker = self.brokers[strategy_id]

            # 准备portfolio_state
            portfolio_state = {
                'cash': broker.cash,
                'total_equity': broker.cash,  # 简化版本
                'has_position': symbol in broker.positions
            }

            # 生成信号
            try:
                signal = strategy.generate_signal(symbol, current_data, portfolio_state)
                all_signals[strategy_id] = signal

                logger.debug(
                    f"📊 [{strategy.name}] {symbol}: "
                    f"{signal.get('action', 'hold')} - {signal.get('reason', '')}"
                )

            except Exception as e:
                logger.error(f"✗ [{strategy.name}] 生成信号失败: {e}")
                all_signals[strategy_id] = {
                    'action': 'hold',
                    'reason': f'信号生成失败: {str(e)}'
                }

        return all_signals

    def execute_signals(
        self,
        symbol: str,
        signals: Dict[str, Dict[str, Any]],
        current_price: float,
        market_prices: Dict[str, float]
    ):
        """执行所有策略的交易信号

        Args:
            symbol: 股票代码
            signals: 所有策略的信号
            current_price: 当前价格
            market_prices: 市场价格
        """
        for strategy_id, signal in signals.items():
            action = signal.get('action', 'hold')

            if action == 'hold':
                continue

            broker = self.brokers[strategy_id]
            strategy = self.strategies[strategy_id]
            performance = self.performances[strategy_id]

            try:
                # 执行交易
                if action == 'buy':
                    # 从信号中获取目标比例，默认10%
                    target_ratio = signal.get('target_ratio', 0.1)

                    # 计算买入数量（使用target_ratio比例的资金）
                    max_value = broker.cash * target_ratio
                    quantity = int(max_value / current_price / 100) * 100  # 取整到100的倍数

                    if quantity >= 100 and broker.cash >= quantity * current_price:
                        # 提交订单
                        from trading.order import Order, OrderSide, OrderType

                        order = Order(
                            symbol=symbol,
                            side=OrderSide.BUY,
                            quantity=quantity,
                            order_type=OrderType.MARKET,
                            strategy_name=strategy.name,  # 添加策略名称
                            reasoning=signal.get('reasoning', f'{strategy.name}策略买入信号')  # 添加交易原因
                        )

                        success = broker.submit_order(order)

                        if success:
                            # 执行市价单
                            executed = broker.execute_market_order(order, current_price)

                            if executed:
                                # 记录交易
                                performance.record_trade({
                                    'symbol': symbol,
                                    'side': 'buy',
                                    'quantity': quantity,
                                    'price': current_price,
                                    'order_id': order.order_id
                                })

                                # 通知策略
                                strategy.on_trade({
                                    'side': 'buy',
                                    'symbol': symbol,
                                    'quantity': quantity,
                                    'price': current_price
                                })

                                logger.info(
                                    f"✓ [{strategy.name}] 买入 {symbol}: "
                                    f"{quantity}股 @ ¥{current_price:.2f}"
                                )

                elif action == 'sell':
                    # 检查是否有持仓
                    if symbol in broker.positions:
                        position = broker.positions[symbol]

                        # 从信号中获取目标比例，默认100%（全部卖出）
                        target_ratio = signal.get('target_ratio', 1.0)

                        # 计算卖出数量（target_ratio * 持仓量）
                        quantity = int(position.quantity * target_ratio / 100) * 100  # 取整到100的倍数

                        # 确保至少卖出100股，且不超过持仓量
                        if quantity < 100:
                            quantity = min(100, position.quantity)
                        quantity = min(quantity, position.quantity)

                        # 提交订单
                        from trading.order import Order, OrderSide, OrderType

                        order = Order(
                            symbol=symbol,
                            side=OrderSide.SELL,
                            quantity=quantity,
                            order_type=OrderType.MARKET,
                            strategy_name=strategy.name,  # 添加策略名称
                            reasoning=signal.get('reasoning', f'{strategy.name}策略卖出信号')  # 添加交易原因
                        )

                        success = broker.submit_order(order)

                        if success:
                            # 执行市价单
                            executed = broker.execute_market_order(order, current_price)

                            if executed:
                                # 计算盈亏
                                pnl = (current_price - position.avg_cost) * quantity

                                # 记录交易
                                performance.record_trade({
                                    'symbol': symbol,
                                    'side': 'sell',
                                    'quantity': quantity,
                                    'price': current_price,
                                    'pnl': pnl,
                                    'order_id': order.order_id
                                })

                                # 通知策略
                                strategy.on_trade({
                                    'side': 'sell',
                                    'symbol': symbol,
                                    'quantity': quantity,
                                    'price': current_price,
                                    'pnl': pnl
                                })

                                logger.info(
                                    f"✓ [{strategy.name}] 卖出 {symbol}: "
                                    f"{quantity}股 @ ¥{current_price:.2f}, "
                                    f"盈亏: {'+' if pnl >= 0 else ''}¥{pnl:.2f}"
                                )

            except Exception as e:
                logger.error(f"✗ [{strategy.name}] 执行交易失败: {e}")

            # 更新投资组合状态
            positions = {s: p.quantity for s, p in broker.positions.items()}
            performance.update_portfolio(
                cash=broker.cash,
                positions=positions,
                market_prices=market_prices
            )

    def get_performances(self) -> List[Dict[str, Any]]:
        """获取所有策略的表现数据

        Returns:
            表现数据列表
        """
        return [perf.to_dict() for perf in self.performances.values()]

    def get_summary(self) -> Dict[str, Any]:
        """获取汇总信息

        Returns:
            汇总数据
        """
        performances = self.get_performances()

        # 找出表现最好的策略
        best_strategy = max(
            performances,
            key=lambda p: p['profit_loss_pct']
        ) if performances else None

        return {
            'total_strategies': len(self.strategies),
            'performances': performances,
            'best_strategy': best_strategy,
        }
