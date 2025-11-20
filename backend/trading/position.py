"""
Position data structures

持仓数据结构定义
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Position:
    """持仓数据结构"""
    symbol: str                # 股票代码
    quantity: int              # 持仓数量
    avg_price: float           # 持仓均价
    current_price: float = 0.0 # 当前价格
    prev_close_price: float = 0.0  # 🆕 昨日收盘价（用于计算today_pnl）

    # 时间信息
    opened_time: datetime = None
    last_updated: datetime = None
    bought_date: datetime = None  # 买入日期（用于T+1限制）

    def __post_init__(self):
        """初始化后处理"""
        if self.opened_time is None:
            self.opened_time = datetime.now()
        if self.last_updated is None:
            self.last_updated = datetime.now()
        if self.bought_date is None:
            self.bought_date = datetime.now()

    @property
    def avg_cost(self) -> float:
        """持仓成本（avg_price 的别名，用于兼容性）"""
        return self.avg_price

    @property
    def market_value(self) -> float:
        """市值"""
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        """成本"""
        return self.quantity * self.avg_price

    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        """未实现盈亏百分比"""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100

    @property
    def today_pnl(self) -> float:
        """🆕 今日盈亏（相对于昨日收盘价）"""
        if self.prev_close_price == 0:
            return 0.0
        return self.quantity * (self.current_price - self.prev_close_price)

    @property
    def today_pnl_pct(self) -> float:
        """🆕 今日盈亏百分比"""
        if self.prev_close_price == 0:
            return 0.0
        return ((self.current_price - self.prev_close_price) / self.prev_close_price) * 100

    def update_price(self, new_price: float, is_new_day: bool = False):
        """更新当前价格

        Args:
            new_price: 新价格
            is_new_day: 是否是新的一天（如果是，更新prev_close_price）
        """
        if is_new_day and self.current_price > 0:
            # 新的一天开始，将当前价格保存为昨日收盘价
            self.prev_close_price = self.current_price

        self.current_price = new_price
        self.last_updated = datetime.now()

    def can_sell_today(self) -> bool:
        """检查今天是否可以卖出（A股T+1限制）

        Returns:
            是否可以卖出（买入日期不是今天）
        """
        if self.bought_date is None:
            return True  # 如果没有买入日期记录，允许卖出

        today = datetime.now().date()
        bought_day = self.bought_date.date()

        return bought_day < today  # 只有买入日期在今天之前才能卖出

    def add_shares(self, quantity: int, price: float):
        """增加持仓（买入）"""
        total_cost = self.cost_basis + (quantity * price)
        total_quantity = self.quantity + quantity

        self.avg_price = total_cost / total_quantity
        self.quantity = total_quantity
        self.last_updated = datetime.now()
        self.bought_date = datetime.now()  # 更新买入日期

    def reduce_shares(self, quantity: int) -> float:
        """减少持仓（卖出）

        Args:
            quantity: 卖出数量

        Returns:
            实现盈亏
        """
        if quantity > self.quantity:
            raise ValueError(f"Cannot reduce {quantity} shares from position of {self.quantity}")

        # 计算实现盈亏（按持仓均价计算）
        realized_pnl = quantity * (self.current_price - self.avg_price)

        self.quantity -= quantity
        self.last_updated = datetime.now()

        return realized_pnl

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'avg_price': self.avg_price,
            'current_price': self.current_price,
            'prev_close_price': self.prev_close_price,  # 🆕
            'market_value': self.market_value,
            'cost_basis': self.cost_basis,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'today_pnl': self.today_pnl,  # 🆕
            'today_pnl_pct': self.today_pnl_pct,  # 🆕
            'opened_time': self.opened_time.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'bought_date': self.bought_date.isoformat() if self.bought_date else None,
            'can_sell_today': self.can_sell_today()
        }
