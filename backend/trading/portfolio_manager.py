"""
Portfolio Manager

投资组合管理器 - 管理持仓、资金、交易记录
"""

from datetime import datetime
from typing import Dict, List, Optional
from .position import Position
from .order import Order, OrderSide


class PortfolioManager:
    """投资组合管理器"""

    def __init__(self, initial_capital: float = 100000.0):
        """初始化投资组合

        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital

        # 持仓字典：symbol -> Position
        self.positions: Dict[str, Position] = {}

        # 交易历史
        self.trade_history: List[dict] = []

        # 权益曲线
        self.equity_history: List[dict] = []

    @property
    def total_market_value(self) -> float:
        """总市值（所有持仓）"""
        return sum(pos.market_value for pos in self.positions.values())

    @property
    def total_equity(self) -> float:
        """总权益（现金 + 持仓市值）"""
        return self.cash + self.total_market_value

    @property
    def total_pnl(self) -> float:
        """总盈亏"""
        return self.total_equity - self.initial_capital

    @property
    def total_pnl_pct(self) -> float:
        """总盈亏百分比"""
        if self.initial_capital == 0:
            return 0.0
        return (self.total_pnl / self.initial_capital) * 100

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)

    def has_position(self, symbol: str) -> bool:
        """是否持有某股票"""
        return symbol in self.positions and self.positions[symbol].quantity > 0

    def update_prices(self, prices: Dict[str, float]):
        """批量更新持仓价格

        Args:
            prices: {symbol: price} 字典
        """
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].update_price(price)

    def execute_buy(self, symbol: str, quantity: int, price: float, commission: float = 0.0) -> dict:
        """执行买入

        Args:
            symbol: 股票代码
            quantity: 数量
            price: 价格
            commission: 手续费

        Returns:
            交易记录
        """
        # 计算总成本
        total_cost = quantity * price + commission

        # 检查资金是否充足
        if total_cost > self.cash:
            raise ValueError(f"Insufficient funds: need {total_cost:.2f}, have {self.cash:.2f}")

        # 扣除资金
        self.cash -= total_cost

        # 更新持仓
        if symbol in self.positions:
            self.positions[symbol].add_shares(quantity, price)
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=price,
                current_price=price
            )

        # 记录交易
        trade_record = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': 'buy',
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'total_cost': total_cost,
            'cash_after': self.cash,
            'equity_after': self.total_equity
        }
        self.trade_history.append(trade_record)

        return trade_record

    def execute_sell(self, symbol: str, quantity: int, price: float, commission: float = 0.0) -> dict:
        """执行卖出

        Args:
            symbol: 股票代码
            quantity: 数量
            price: 价格
            commission: 手续费

        Returns:
            交易记录
        """
        # 检查是否持有该股票
        if not self.has_position(symbol):
            raise ValueError(f"No position in {symbol}")

        position = self.positions[symbol]

        # 检查数量是否充足
        if quantity > position.quantity:
            raise ValueError(f"Insufficient shares: need {quantity}, have {position.quantity}")

        # 计算卖出所得
        total_proceeds = quantity * price - commission

        # 计算实现盈亏
        realized_pnl = position.reduce_shares(quantity)

        # 增加资金
        self.cash += total_proceeds

        # 如果持仓为0，删除持仓记录
        if position.quantity == 0:
            del self.positions[symbol]

        # 记录交易
        trade_record = {
            'timestamp': datetime.now(),
            'symbol': symbol,
            'side': 'sell',
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'total_proceeds': total_proceeds,
            'realized_pnl': realized_pnl,
            'cash_after': self.cash,
            'equity_after': self.total_equity
        }
        self.trade_history.append(trade_record)

        return trade_record

    def record_equity(self, timestamp: datetime):
        """记录当前权益（用于绘制权益曲线）"""
        self.equity_history.append({
            'timestamp': timestamp,
            'cash': self.cash,
            'market_value': self.total_market_value,
            'total_equity': self.total_equity,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': self.total_pnl_pct
        })

    def get_summary(self) -> dict:
        """获取投资组合摘要"""
        return {
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'market_value': self.total_market_value,
            'total_equity': self.total_equity,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': self.total_pnl_pct,
            'num_positions': len(self.positions),
            'num_trades': len(self.trade_history)
        }

    def get_positions_dict(self) -> Dict[str, dict]:
        """获取所有持仓（字典格式）"""
        return {
            symbol: pos.to_dict()
            for symbol, pos in self.positions.items()
        }
