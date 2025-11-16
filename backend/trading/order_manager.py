"""
Order Manager

订单管理器 - 处理订单执行、滑点、手续费计算
"""

from datetime import datetime
from typing import Dict, List, Optional
import numpy as np

from .order import Order, OrderStatus, OrderType, OrderSide
from .portfolio_manager import PortfolioManager


class OrderManager:
    """订单管理器"""

    def __init__(
        self,
        portfolio: PortfolioManager,
        commission_rate: float = 0.0003,  # 手续费率（万3）
        slippage_rate: float = 0.001,     # 滑点率（千1）
        min_commission: float = 5.0       # 最低手续费（5元）
    ):
        """初始化订单管理器

        Args:
            portfolio: 投资组合管理器
            commission_rate: 手续费率（默认万3）
            slippage_rate: 滑点率（默认千1）
            min_commission: 最低手续费（默认5元）
        """
        self.portfolio = portfolio
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.min_commission = min_commission

        # 订单记录
        self.orders: List[Order] = []
        self.pending_orders: List[Order] = []

    def calculate_commission(self, quantity: int, price: float) -> float:
        """计算手续费

        Args:
            quantity: 数量
            price: 价格

        Returns:
            手续费
        """
        commission = quantity * price * self.commission_rate
        return max(commission, self.min_commission)

    def apply_slippage(self, price: float, side: OrderSide) -> float:
        """应用滑点

        Args:
            price: 原始价格
            side: 买卖方向

        Returns:
            滑点后价格
        """
        if side == OrderSide.BUY:
            # 买入：价格向上滑点
            return price * (1 + self.slippage_rate)
        else:
            # 卖出：价格向下滑点
            return price * (1 - self.slippage_rate)

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None
    ) -> Order:
        """创建订单

        Args:
            symbol: 股票代码
            side: 买卖方向
            quantity: 数量
            order_type: 订单类型
            limit_price: 限价（限价单用）

        Returns:
            订单对象
        """
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price
        )

        self.orders.append(order)
        self.pending_orders.append(order)

        return order

    def execute_market_order(self, order: Order, current_price: float) -> bool:
        """执行市价单

        Args:
            order: 订单
            current_price: 当前价格

        Returns:
            是否成功执行
        """
        try:
            # 应用滑点
            executed_price = self.apply_slippage(current_price, order.side)

            # 计算手续费
            commission = self.calculate_commission(order.quantity, executed_price)

            # 执行交易
            if order.is_buy:
                self.portfolio.execute_buy(
                    order.symbol,
                    order.quantity,
                    executed_price,
                    commission
                )
            else:
                self.portfolio.execute_sell(
                    order.symbol,
                    order.quantity,
                    executed_price,
                    commission
                )

            # 更新订单状态
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.filled_price = executed_price
            order.commission = commission
            order.filled_time = datetime.now()

            # 从待处理列表移除
            if order in self.pending_orders:
                self.pending_orders.remove(order)

            return True

        except Exception as e:
            # 订单失败
            order.status = OrderStatus.REJECTED
            print(f"Order execution failed: {e}")
            if order in self.pending_orders:
                self.pending_orders.remove(order)
            return False

    def execute_limit_order(self, order: Order, current_price: float) -> bool:
        """执行限价单

        Args:
            order: 订单
            current_price: 当前价格

        Returns:
            是否成功执行
        """
        # 检查是否触发限价
        if order.is_buy:
            # 买入限价单：当前价 <= 限价时成交
            if current_price > order.limit_price:
                return False
        else:
            # 卖出限价单：当前价 >= 限价时成交
            if current_price < order.limit_price:
                return False

        # 使用限价成交
        executed_price = order.limit_price

        try:
            # 计算手续费
            commission = self.calculate_commission(order.quantity, executed_price)

            # 执行交易
            if order.is_buy:
                self.portfolio.execute_buy(
                    order.symbol,
                    order.quantity,
                    executed_price,
                    commission
                )
            else:
                self.portfolio.execute_sell(
                    order.symbol,
                    order.quantity,
                    executed_price,
                    commission
                )

            # 更新订单状态
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.filled_price = executed_price
            order.commission = commission
            order.filled_time = datetime.now()

            # 从待处理列表移除
            if order in self.pending_orders:
                self.pending_orders.remove(order)

            return True

        except Exception as e:
            order.status = OrderStatus.REJECTED
            print(f"Limit order execution failed: {e}")
            if order in self.pending_orders:
                self.pending_orders.remove(order)
            return False

    def execute_order(self, order: Order, current_price: float) -> bool:
        """执行订单（根据订单类型自动选择执行方式）

        Args:
            order: 订单
            current_price: 当前价格

        Returns:
            是否成功执行
        """
        if order.order_type == OrderType.MARKET:
            return self.execute_market_order(order, current_price)
        else:
            return self.execute_limit_order(order, current_price)

    def cancel_order(self, order: Order) -> bool:
        """撤销订单

        Args:
            order: 订单

        Returns:
            是否成功撤销
        """
        if order.status != OrderStatus.PENDING:
            return False

        order.status = OrderStatus.CANCELLED
        if order in self.pending_orders:
            self.pending_orders.remove(order)

        return True

    def get_order_history(self) -> List[dict]:
        """获取订单历史"""
        return [order.to_dict() for order in self.orders]

    def get_pending_orders(self) -> List[dict]:
        """获取待处理订单"""
        return [order.to_dict() for order in self.pending_orders]
