"""
Simulated Broker

模拟券商，用于Paper Trading，模拟真实交易环境。
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

from .base_broker import BaseBroker
from .order import Order, OrderType, OrderSide, OrderStatus
from .position import Position

logger = logging.getLogger(__name__)


class SimulatedBroker(BaseBroker):
    """模拟券商

    模拟真实券商的交易功能，包括：
    - 市价单执行
    - 限价单执行
    - 滑点模拟
    - 手续费计算
    - 持仓管理
    """

    def __init__(
        self,
        initial_cash: float = 100000.0,
        commission_rate: float = 0.0001,  # 万1佣金
        stamp_duty_rate: float = 0.001,   # 千1印花税（仅卖出）
        slippage_rate: float = 0.001,     # 0.1%滑点
        min_commission: float = 5.0        # 最低佣金5元
    ):
        """
        初始化模拟券商

        Args:
            initial_cash: 初始资金
            commission_rate: 佣金率（买入和卖出都收，万1）
            stamp_duty_rate: 印花税率（仅卖出收取，千1）
            slippage_rate: 滑点率
            min_commission: 最低佣金
        """
        # Initialize parent class with empty config (simulated broker doesn't need real credentials)
        super().__init__({})

        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.stamp_duty_rate = stamp_duty_rate
        self.slippage_rate = slippage_rate
        self.min_commission = min_commission

        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trade_history: List[Dict] = []

        # Mark as logged in (simulated broker is always "logged in")
        self.is_logged_in = True

        logger.info(f"SimulatedBroker initialized (cash: {initial_cash:,.2f})")

    def submit_order(self, order: Order) -> bool:
        """
        提交订单

        Args:
            order: 订单对象

        Returns:
            是否提交成功
        """
        try:
            # 验证订单
            if not self._validate_order(order):
                order.status = OrderStatus.REJECTED
                logger.warning(f"Order rejected: {order}")
                return False

            # 添加到订单列表
            self.orders.append(order)
            order.status = OrderStatus.PENDING
            logger.info(f"Order submitted: {order.symbol} {order.side.value} {order.quantity}")

            return True

        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            order.status = OrderStatus.REJECTED
            return False

    def execute_market_order(self, order: Order, current_price: float) -> bool:
        """
        执行市价单

        Args:
            order: 订单对象
            current_price: 当前市场价格

        Returns:
            是否执行成功
        """
        try:
            # 计算滑点后的成交价
            if order.side == OrderSide.BUY:
                fill_price = current_price * (1 + self.slippage_rate)
            else:  # SELL
                fill_price = current_price * (1 - self.slippage_rate)

            # 计算佣金（买入和卖出都收）
            commission = max(
                fill_price * order.quantity * self.commission_rate,
                self.min_commission
            )

            # 计算印花税（仅卖出收取）
            stamp_duty = 0.0
            if order.side == OrderSide.SELL:
                stamp_duty = fill_price * order.quantity * self.stamp_duty_rate

            # 总费用
            total_fees = commission + stamp_duty

            # 买入
            if order.side == OrderSide.BUY:
                total_cost = fill_price * order.quantity + total_fees

                if total_cost > self.cash:
                    logger.warning(f" Insufficient cash: need ¥{total_cost:,.2f}, have ¥{self.cash:,.2f}")
                    order.status = OrderStatus.REJECTED
                    return False

                # 扣除资金
                self.cash -= total_cost

                # 更新持仓
                if order.symbol not in self.positions:
                    self.positions[order.symbol] = Position(order.symbol, 0, 0.0)

                self.positions[order.symbol].add_shares(order.quantity, fill_price)

            # 卖出
            else:
                if order.symbol not in self.positions:
                    logger.warning(f" No position to sell: {order.symbol}")
                    order.status = OrderStatus.REJECTED
                    return False

                position = self.positions[order.symbol]

                # A股 T+1 限制检查
                if not position.can_sell_today():
                    bought_date_str = position.bought_date.strftime('%Y-%m-%d') if position.bought_date else 'Unknown'
                    logger.warning(
                        f" T+1 restriction: Cannot sell {order.symbol} bought on {bought_date_str} on the same day"
                    )
                    order.status = OrderStatus.REJECTED
                    return False

                if position.quantity < order.quantity:
                    logger.warning(
                        f" Insufficient shares: need {order.quantity}, have {position.quantity}"
                    )
                    order.status = OrderStatus.REJECTED
                    return False

                # 卖出收入（扣除佣金和印花税）
                total_proceeds = fill_price * order.quantity - total_fees
                self.cash += total_proceeds

                # 更新持仓价格（用于计算实现盈亏）
                position.update_price(fill_price)

                # 减少持仓
                position.reduce_shares(order.quantity)

                # 如果持仓清空，删除记录
                if position.quantity == 0:
                    del self.positions[order.symbol]

            # 更新订单状态
            order.status = OrderStatus.FILLED
            order.filled_price = fill_price
            order.filled_quantity = order.quantity
            order.filled_time = datetime.now()
            order.commission = total_fees  # 保存总费用

            # 记录交易历史
            self.trade_history.append({
                'timestamp': datetime.now(),
                'symbol': order.symbol,
                'side': order.side.value,
                'quantity': order.quantity,
                'price': fill_price,
                'commission': commission,
                'stamp_duty': stamp_duty,
                'total_fees': total_fees,
                'cash_change': -total_cost if order.side == OrderSide.BUY else total_proceeds
            })

            # 详细的日志输出
            if order.side == OrderSide.BUY:
                logger.info(
                    f" Order filled: {order.symbol} BUY "
                    f"{order.quantity}@¥{fill_price:.2f} "
                    f"(佣金=¥{commission:.2f}, 总费用=¥{total_fees:.2f})"
                )
            else:
                logger.info(
                    f" Order filled: {order.symbol} SELL "
                    f"{order.quantity}@¥{fill_price:.2f} "
                    f"(佣金=¥{commission:.2f}, 印花税=¥{stamp_duty:.2f}, 总费用=¥{total_fees:.2f})"
                )

            return True

        except Exception as e:
            logger.error(f" Error executing market order: {e}")
            order.status = OrderStatus.REJECTED
            return False

    def execute_limit_order(self, order: Order, current_price: float) -> bool:
        """
        执行限价单

        Args:
            order: 订单对象
            current_price: 当前市场价格

        Returns:
            是否执行成功
        """
        try:
            # 检查是否满足限价条件
            if order.side == OrderSide.BUY:
                # 买入限价单：当前价 <= 限价
                if current_price > order.limit_price:
                    logger.debug(
                        f" Buy limit order not triggered: "
                        f"current=¥{current_price:.2f} > limit=¥{order.limit_price:.2f}"
                    )
                    return False
                fill_price = min(current_price, order.limit_price)
            else:  # SELL
                # 卖出限价单：当前价 >= 限价
                if current_price < order.limit_price:
                    logger.debug(
                        f" Sell limit order not triggered: "
                        f"current=¥{current_price:.2f} < limit=¥{order.limit_price:.2f}"
                    )
                    return False
                fill_price = max(current_price, order.limit_price)

            # 使用市价单执行逻辑（但价格使用限价）
            # 创建临时市价单
            temp_order = Order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                order_type=OrderType.MARKET
            )

            # 手动设置成交价
            return self.execute_market_order(temp_order, fill_price)

        except Exception as e:
            logger.error(f" Error executing limit order: {e}")
            order.status = OrderStatus.REJECTED
            return False

    def _validate_order(self, order: Order) -> bool:
        """
        验证订单有效性

        Args:
            order: 订单对象

        Returns:
            是否有效
        """
        # 检查订单数量
        if order.quantity <= 0:
            logger.warning(f" Invalid quantity: {order.quantity}")
            return False

        # 检查订单类型
        if order.order_type not in [OrderType.MARKET, OrderType.LIMIT]:
            logger.warning(f" Unsupported order type: {order.order_type}")
            return False

        # 限价单必须有限价
        if order.order_type == OrderType.LIMIT and order.limit_price is None:
            logger.warning(" Limit order must have limit_price")
            return False

        return True

    def get_positions(self) -> List[Dict]:
        """
        获取当前持仓

        Returns:
            持仓列表
        """
        return [
            {
                'symbol': symbol,
                'quantity': pos.quantity,
                'avg_price': pos.avg_price,
                'market_value': pos.quantity * pos.avg_price,  # 简化，实际应用当前价
                'cost': pos.quantity * pos.avg_price
            }
            for symbol, pos in self.positions.items()
        ]

    def get_balance(self) -> Dict:
        """
        获取账户资金信息

        Returns:
            资金信息字典
        """
        # 计算持仓市值（简化，使用成本价）
        total_market_value = sum(
            pos.quantity * pos.avg_price
            for pos in self.positions.values()
        )

        total_assets = self.cash + total_market_value

        return {
            'cash': self.cash,
            'market_value': total_market_value,
            'total_assets': total_assets,
            'initial_cash': self.initial_cash,
            'profit': total_assets - self.initial_cash,
            'profit_pct': (total_assets - self.initial_cash) / self.initial_cash
        }

    def cancel_order(self, order_id: str) -> bool:
        """
        撤销订单

        Args:
            order_id: 订单ID

        Returns:
            是否撤销成功
        """
        for order in self.orders:
            if order.order_id == order_id:
                if order.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
                    order.status = OrderStatus.CANCELLED
                    logger.info(f" Order cancelled: {order_id}")
                    return True
                else:
                    logger.warning(f" Cannot cancel order in status: {order.status}")
                    return False

        logger.warning(f" Order not found: {order_id}")
        return False

    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        获取订单状态

        Args:
            order_id: 订单ID

        Returns:
            订单状态
        """
        for order in self.orders:
            if order.order_id == order_id:
                return order.status

        return None

    def get_trade_history(self) -> List[Dict]:
        """
        获取交易历史

        Returns:
            交易记录列表
        """
        return self.trade_history.copy()

    def reset(self):
        """重置券商状态"""
        self.cash = self.initial_cash
        self.positions.clear()
        self.orders.clear()
        self.trade_history.clear()
        logger.info("SimulatedBroker reset")

    # Abstract methods from BaseBroker

    def login(self) -> bool:
        """
        登录券商（模拟券商总是已登录）

        Returns:
            是否登录成功
        """
        self.is_logged_in = True
        logger.info("SimulatedBroker login (simulated)")
        return True

    def logout(self) -> bool:
        """
        登出券商（模拟券商登出是空操作）

        Returns:
            是否登出成功
        """
        self.is_logged_in = False
        logger.info("SimulatedBroker logout (simulated)")
        return True

    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Dict]:
        """
        获取订单列表

        Args:
            status: 订单状态过滤（None表示获取所有订单）

        Returns:
            订单列表
        """
        filtered_orders = self.orders

        if status is not None:
            filtered_orders = [o for o in self.orders if o.status == status]

        return [
            {
                'order_id': order.order_id,
                'symbol': order.symbol,
                'side': order.side.value,
                'quantity': order.quantity,
                'order_type': order.order_type.value,
                'status': order.status.value,
                'limit_price': order.limit_price,
                'filled_price': order.filled_price,
                'filled_quantity': order.filled_quantity,
                'created_time': order.created_time,
                'filled_time': order.filled_time,
                'commission': order.commission
            }
            for order in filtered_orders
        ]
