"""
Trading Service

全局交易服务，管理模拟交易引擎和投资组合
"""

from typing import Optional
from trading.portfolio_manager import PortfolioManager
from trading.order_manager import OrderManager


class TradingService:
    """交易服务单例"""

    _instance: Optional['TradingService'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # 初始化交易组件
            self.initial_capital = 100000.0  # 初始资金10万
            self.portfolio = PortfolioManager(initial_capital=self.initial_capital)
            self.order_manager = OrderManager(
                portfolio=self.portfolio,
                commission_rate=0.0003,  # 万3手续费
                slippage_rate=0.001,     # 千1滑点
                min_commission=5.0       # 最低5元
            )

            # 存储策略配置
            self.strategies = {}

            TradingService._initialized = True

    def get_portfolio_summary(self) -> dict:
        """获取投资组合摘要"""
        return {
            "total_value": self.portfolio.total_equity,
            "cash": self.portfolio.cash,
            "positions_value": self.portfolio.total_market_value,
            "total_pnl": self.portfolio.total_pnl,
            "total_pnl_percent": self.portfolio.total_pnl_pct,
            "daily_pnl": 0.0,  # TODO: 需要从历史记录计算
            "daily_pnl_percent": 0.0
        }

    def get_positions(self) -> list:
        """获取当前所有持仓"""
        positions = []
        for symbol, position in self.portfolio.positions.items():
            positions.append({
                "symbol": symbol,
                "name": symbol.split('.')[0],  # TODO: 从market API获取股票名称
                "quantity": position.quantity,
                "avg_cost": position.avg_cost,
                "current_price": position.current_price,
                "market_value": position.market_value,
                "cost_basis": position.cost_basis,
                "unrealized_pnl": position.unrealized_pnl,
                "unrealized_pnl_pct": position.unrealized_pnl_pct,
                "today_pnl": 0.0,  # TODO: 需要从日内价格变化计算
                "today_pnl_pct": 0.0
            })
        return positions

    def get_position(self, symbol: str) -> Optional[dict]:
        """获取单个持仓"""
        position = self.portfolio.get_position(symbol)
        if not position:
            return None

        return {
            "symbol": symbol,
            "name": symbol.split('.')[0],
            "quantity": position.quantity,
            "avg_cost": position.avg_cost,
            "current_price": position.current_price,
            "market_value": position.market_value,
            "cost_basis": position.cost_basis,
            "unrealized_pnl": position.unrealized_pnl,
            "unrealized_pnl_pct": position.unrealized_pnl_pct,
            "today_pnl": 0.0,
            "today_pnl_pct": 0.0
        }

    def get_portfolio_history(self, days: int = 30) -> list:
        """获取投资组合历史"""
        # 返回equity_history中的最后days天数据
        history = self.portfolio.equity_history[-days:] if self.portfolio.equity_history else []
        return history

    def get_orders(self, status: Optional[str] = None) -> list:
        """获取订单列表"""
        orders = []
        order_id_counter = 1000  # 从1000开始的数字ID

        for order in self.order_manager.orders:
            # 过滤状态
            if status and order.status.value != status:
                continue

            orders.append({
                "order_id": order_id_counter,
                "symbol": order.symbol,
                "name": order.symbol.split('.')[0],
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "price": order.limit_price,
                "filled_quantity": order.filled_quantity,
                "avg_fill_price": order.filled_price if order.filled_quantity > 0 else None,
                "status": order.status.value,
                "created_at": order.created_time.isoformat(),
                "updated_at": (order.filled_time or order.created_time).isoformat()
            })
            order_id_counter += 1

        return orders

    def get_order(self, order_id: int) -> Optional[dict]:
        """获取单个订单"""
        # 由于Order使用字符串ID，我们需要通过索引获取
        # order_id从1000开始，索引从0开始
        index = order_id - 1000

        if 0 <= index < len(self.order_manager.orders):
            order = self.order_manager.orders[index]
            return {
                "order_id": order_id,
                "symbol": order.symbol,
                "name": order.symbol.split('.')[0],
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "price": order.limit_price,
                "filled_quantity": order.filled_quantity,
                "avg_fill_price": order.filled_price if order.filled_quantity > 0 else None,
                "status": order.status.value,
                "created_at": order.created_time.isoformat(),
                "updated_at": (order.filled_time or order.created_time).isoformat()
            }
        return None

    def create_order(self, order_data: dict) -> dict:
        """创建订单"""
        from trading.order import OrderSide, OrderType

        # 解析订单参数
        symbol = order_data.get("symbol")
        side = OrderSide.BUY if order_data.get("side") == "buy" else OrderSide.SELL
        quantity = order_data.get("quantity")
        order_type = OrderType.LIMIT if order_data.get("order_type") == "limit" else OrderType.MARKET
        limit_price = order_data.get("price")

        # 创建订单
        order = self.order_manager.create_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price
        )

        # 生成数字ID
        order_id = 1000 + len(self.order_manager.orders) - 1

        return {
            "order_id": order_id,
            "symbol": order.symbol,
            "name": order.symbol.split('.')[0],
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": order.quantity,
            "price": order.limit_price,
            "filled_quantity": 0,
            "avg_fill_price": None,
            "status": order.status.value,
            "created_at": order.created_time.isoformat(),
            "updated_at": order.created_time.isoformat()
        }

    def cancel_order(self, order_id: int) -> bool:
        """取消订单"""
        from trading.order import OrderStatus

        # order_id从1000开始，索引从0开始
        index = order_id - 1000

        if 0 <= index < len(self.order_manager.pending_orders):
            order = self.order_manager.pending_orders[index]
            order.status = OrderStatus.CANCELLED  # Direct assignment instead of order.cancel()
            self.order_manager.pending_orders.remove(order)
            return True
        return False


# 全局单例
trading_service = TradingService()
