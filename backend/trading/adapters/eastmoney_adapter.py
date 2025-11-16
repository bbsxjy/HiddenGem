from typing import Dict, List
from ..order import Order, OrderSide, OrderType, OrderStatus
from ..position import Position

class EastmoneyAdapter:
    @staticmethod
    def adapt_order_to_broker(order: Order) -> dict:
        return {
            "symbol": order.symbol,
            "side": order.side.value,
            "quantity": order.quantity,
            "order_type": order.order_type.value,
            "price": order.limit_price if order.limit_price else 0
        }
    
    @staticmethod
    def adapt_order_from_broker(broker_order: dict) -> Order:
        side = OrderSide.BUY if broker_order["side"] == "buy" else OrderSide.SELL
        order_type = OrderType.MARKET if broker_order["order_type"] == "market" else OrderType.LIMIT
        status_mapping = {"pending": OrderStatus.PENDING, "filled": OrderStatus.FILLED, "cancelled": OrderStatus.CANCELLED}
        status = status_mapping.get(broker_order.get("status", "pending"), OrderStatus.PENDING)
        return Order(symbol=broker_order["symbol"], side=side, quantity=broker_order["quantity"], order_type=order_type, order_id=broker_order.get("order_id", ""), status=status)
    
    @staticmethod
    def adapt_position_from_broker(broker_position: dict) -> Position:
        return Position(symbol=broker_position["symbol"], quantity=broker_position["quantity"], avg_price=broker_position["avg_price"], current_price=broker_position.get("current_price", broker_position["avg_price"]))
