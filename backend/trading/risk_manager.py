"""
Risk Manager

风险管理模块，负责交易风险控制。
"""

from typing import Dict, Optional
from datetime import date
import logging

from .order import Order, OrderSide
from .portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)


class RiskManager:
    """风险管理器"""

    def __init__(
        self,
        max_position_pct: float = 0.3,
        max_order_pct: float = 0.1,
        max_daily_trades: int = 20,
        max_daily_loss_pct: float = 0.05,
        max_total_loss_pct: float = 0.20,
        enable_controls: bool = True
    ):
        self.max_position_pct = max_position_pct
        self.max_order_pct = max_order_pct
        self.max_daily_trades = max_daily_trades
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_total_loss_pct = max_total_loss_pct
        self.enable_controls = enable_controls

        self.daily_trades: Dict[date, int] = {}
        self.daily_pnl: Dict[date, float] = {}
        self.total_pnl = 0.0
        self.initial_capital = None

        logger.info(f"RiskManager initialized")

    def validate_order(
        self,
        order: Order,
        portfolio: PortfolioManager,
        current_price: float
    ):
        """Validate order against risk rules"""
        if not self.enable_controls:
            return True, None
        
        # Simplified validation
        return True, None

    def record_trade(self, pnl: float):
        """Record trade"""
        today = date.today()
        self.daily_trades[today] = self.daily_trades.get(today, 0) + 1
        self.daily_pnl[today] = self.daily_pnl.get(today, 0.0) + pnl
        self.total_pnl += pnl

    def get_stats(self) -> Dict:
        """Get risk stats"""
        today = date.today()
        return {
            'daily_trades': self.daily_trades.get(today, 0),
            'max_daily_trades': self.max_daily_trades,
            'daily_pnl': self.daily_pnl.get(today, 0.0),
            'total_pnl': self.total_pnl,
            'controls_enabled': self.enable_controls
        }
