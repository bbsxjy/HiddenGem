"""
Trading System Module

包含Paper Trading、回测系统、订单管理等核心交易功能
"""

import logging

logger = logging.getLogger(__name__)

# Backtest System (Task 2)
from .portfolio_manager import PortfolioManager
from .order_manager import OrderManager
from .order import Order, OrderType, OrderSide, OrderStatus
from .position import Position
from .strategy import BaseStrategy, BuyAndHoldStrategy
from .backtester import Backtester
from .metrics import calculate_all_metrics
from .report_generator import ReportGenerator

# Paper Trading System (Task 3)
try:
    from .market_data_feed import RealTimeMarketFeed
    from .simulated_broker import SimulatedBroker
    from .risk_manager import RiskManager
    from .paper_trading_engine import PaperTradingEngine
    PAPER_TRADING_AVAILABLE = True
except ImportError as e:
    logger.warning(f" Paper Trading modules import failed: {e}")
    PAPER_TRADING_AVAILABLE = False

# 基础模块（总是导出）
__all__ = [
    # Portfolio & Order (Task 2)
    'PortfolioManager',
    'OrderManager',
    'Order',
    'OrderType',
    'OrderSide',
    'OrderStatus',
    'Position',

    # Strategy & Backtesting (Task 2)
    'BaseStrategy',
    'BuyAndHoldStrategy',
    'Backtester',

    # Metrics & Reporting (Task 2)
    'calculate_all_metrics',
    'ReportGenerator',
]

# Paper Trading模块（如果可用）
if PAPER_TRADING_AVAILABLE:
    __all__.extend([
        'RealTimeMarketFeed',
        'SimulatedBroker',
        'RiskManager',
        'PaperTradingEngine',
    ])
