"""
Order data structures and management

订单数据结构定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"  # 市价单
    LIMIT = "limit"    # 限价单


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"      # 待处理
    FILLED = "filled"        # 已成交
    PARTIALLY_FILLED = "partially_filled"  # 部分成交
    CANCELLED = "cancelled"  # 已撤销
    REJECTED = "rejected"    # 已拒绝


@dataclass
class Order:
    """订单数据结构"""
    symbol: str                    # 股票代码
    side: OrderSide                # 买卖方向
    quantity: int                  # 数量（股）
    order_type: OrderType = OrderType.MARKET  # 订单类型
    limit_price: Optional[float] = None       # 限价（限价单用）

    # 订单状态
    order_id: str = ""                        # 订单ID
    status: OrderStatus = OrderStatus.PENDING # 状态

    # 成交信息
    filled_quantity: int = 0       # 已成交数量
    filled_price: float = 0.0      # 成交价格
    commission: float = 0.0        # 手续费

    # 时间信息
    created_time: datetime = field(default_factory=datetime.now)
    filled_time: Optional[datetime] = None

    # 策略和原因（用于前端显示）
    strategy_name: Optional[str] = None  # 策略名称
    reasoning: Optional[str] = None      # 交易原因

    def __post_init__(self):
        """初始化后处理"""
        if not self.order_id:
            # 生成订单ID：时间戳_股票代码_方向
            timestamp = self.created_time.strftime("%Y%m%d%H%M%S%f")
            self.order_id = f"{timestamp}_{self.symbol}_{self.side.value}"

    @property
    def is_filled(self) -> bool:
        """是否完全成交"""
        return self.status == OrderStatus.FILLED

    @property
    def is_buy(self) -> bool:
        """是否买入订单"""
        return self.side == OrderSide.BUY

    @property
    def is_sell(self) -> bool:
        """是否卖出订单"""
        return self.side == OrderSide.SELL

    @property
    def remaining_quantity(self) -> int:
        """剩余未成交数量"""
        return self.quantity - self.filled_quantity

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'limit_price': self.limit_price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'commission': self.commission,
            'created_time': self.created_time.isoformat(),
            'filled_time': self.filled_time.isoformat() if self.filled_time else None,
            'strategy_name': self.strategy_name,
            'reasoning': self.reasoning
        }
