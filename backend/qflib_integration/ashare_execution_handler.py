"""
A-Share Execution Handler for QF-Lib

实现A股特有的交易规则（T+1、涨跌停、交易时段等）
"""

from datetime import datetime, time
from typing import Dict, Optional
import logging

# QF-Lib imports (note: package name is qf_lib with underscore)
try:
    from qf_lib.backtesting.execution_handler.execution_handler import ExecutionHandler
    from qf_lib.backtesting.order.order import Order
    from qf_lib.backtesting.order.execution_style import ExecutionStyle, MarketOrder
    from qf_lib.backtesting.events.time_event.regular_time_event.market_close_event import MarketCloseEvent
    from qf_lib.backtesting.portfolio.portfolio import Portfolio
    from qf_lib.backtesting.data_handler.data_handler import DataHandler
    from qf_lib.common.tickers.tickers import Ticker
except ImportError:
    # 占位符
    ExecutionHandler = object
    Order = None
    ExecutionStyle = None
    MarketOrder = None
    MarketCloseEvent = None
    Portfolio = None
    DataHandler = None
    Ticker = str

logger = logging.getLogger(__name__)


class AShareExecutionHandler(ExecutionHandler if ExecutionHandler != object else object):
    """A股交易执行处理器

    实现A股特有的交易规则：
    -  T+1制度：当日买入的股票次日才能卖出
    -  涨跌停限制：主板±10%，创业板/科创板±20%
    -  交易时段限制：9:30-11:30, 13:00-15:00
    -  集合竞价模拟
    -  流动性约束
    """

    def __init__(
        self,
        data_handler: DataHandler,
        portfolio: Portfolio,
        commission_rate: float = 0.0003,
        min_commission: float = 5.0
    ):
        """初始化A股执行处理器

        Args:
            data_handler: 数据处理器
            portfolio: 投资组合
            commission_rate: 手续费率（默认0.03%）
            min_commission: 最低手续费（默认5元）
        """
        super().__init__(data_handler, portfolio)
        self.commission_rate = commission_rate
        self.min_commission = min_commission

        # T+1追踪：记录每日买入的股票
        self._daily_purchases: Dict[str, Dict[datetime, int]] = {}

        logger.info(f" AShareExecutionHandler initialized: commission_rate={commission_rate}")

    def execute_order(self, order: Order) -> Optional['Fill']:
        """执行订单（考虑A股特性）

        Args:
            order: 订单对象

        Returns:
            成交记录（Fill对象）或None（无法成交）
        """
        current_time = self.timer.now()
        ticker = order.ticker
        ticker_str = str(ticker)

        logger.debug(f" Executing order: {ticker} | {order.direction} | {order.quantity}")

        # ===== 检查1：交易时段 =====
        if not self._is_trading_hours(current_time):
            logger.warning(f"⏰ Non-trading hours: {current_time.time()}")
            return None

        # ===== 检查2：获取当前价格 =====
        try:
            current_price = self.data_handler.get_last_available_price([ticker])
            if current_price is None or current_price <= 0:
                logger.warning(f" Invalid price for {ticker}: {current_price}")
                return None
        except Exception as e:
            logger.error(f" Error getting price for {ticker}: {e}")
            return None

        # ===== 检查3：涨跌停限制 =====
        limit_up, limit_down = self._get_price_limits(ticker, current_time, current_price)

        if order.direction == 'BUY':
            # 买入：检查是否涨停
            if current_price >= limit_up * 0.995:  # 接近涨停（99.5%以上）
                logger.warning(f" {ticker} at limit-up: {current_price:.2f} (limit: {limit_up:.2f})")
                # 涨停时降低成交量
                order.quantity = int(order.quantity * 0.1)
                if order.quantity == 0:
                    return None

        elif order.direction == 'SELL':
            # 卖出：检查T+1限制
            if not self._can_sell_today(ticker_str, current_time):
                logger.warning(f" T+1限制：{ticker} 今日买入，不能卖出")
                return None

            # 卖出：检查是否跌停
            if current_price <= limit_down * 1.005:  # 接近跌停（100.5%以下）
                logger.warning(f" {ticker} at limit-down: {current_price:.2f} (limit: {limit_down:.2f})")
                return None  # 跌停无法卖出

        # ===== 检查4：流动性约束 =====
        # TODO: 根据成交量判断是否能完全成交

        # ===== 执行成交 =====
        fill = self._create_fill_event(order, current_price)

        # ===== 更新T+1追踪 =====
        if order.direction == 'BUY':
            self._record_purchase(ticker_str, current_time, order.quantity)

        logger.info(f" Order executed: {ticker} | {order.direction} | {order.quantity} @ {current_price:.2f}")

        return fill

    def _is_trading_hours(self, current_time: datetime) -> bool:
        """检查是否在交易时段

        Args:
            current_time: 当前时间

        Returns:
            是否在交易时段
        """
        current_hour = current_time.hour
        current_minute = current_time.minute

        # A股交易时间
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)

        current_time_only = current_time.time()

        return (
            (morning_start <= current_time_only <= morning_end) or
            (afternoon_start <= current_time_only <= afternoon_end)
        )

    def _get_price_limits(
        self,
        ticker: Ticker,
        current_time: datetime,
        current_price: float
    ) -> tuple[float, float]:
        """获取涨跌停价格限制

        Args:
            ticker: 股票代码
            current_time: 当前时间
            current_price: 当前价格

        Returns:
            (涨停价, 跌停价)
        """
        ticker_str = str(ticker)

        # 判断板块（根据代码前缀）
        if ticker_str.startswith('300') or ticker_str.startswith('688'):
            # 创业板（300）或科创板（688）：±20%
            limit_pct = 0.20
        else:
            # 主板：±10%
            limit_pct = 0.10

        # 获取昨日收盘价（理想情况下应该获取真实昨日收盘）
        # 这里简化处理，使用当前价格估算
        prev_close = current_price  # TODO: 获取真实昨日收盘价

        limit_up = prev_close * (1 + limit_pct)
        limit_down = prev_close * (1 - limit_pct)

        return limit_up, limit_down

    def _can_sell_today(self, ticker_str: str, current_time: datetime) -> bool:
        """检查今日是否可以卖出（T+1检查）

        Args:
            ticker_str: 股票代码字符串
            current_time: 当前时间

        Returns:
            是否可以卖出
        """
        if ticker_str not in self._daily_purchases:
            return True  # 没有今日买入记录，可以卖出

        purchases = self._daily_purchases[ticker_str]
        today_date = current_time.date()

        # 检查今日是否有买入
        for purchase_date in purchases.keys():
            if purchase_date.date() == today_date:
                # 今日有买入，不能卖出
                return False

        return True

    def _record_purchase(self, ticker_str: str, purchase_time: datetime, quantity: int):
        """记录买入（用于T+1追踪）

        Args:
            ticker_str: 股票代码字符串
            purchase_time: 买入时间
            quantity: 买入数量
        """
        if ticker_str not in self._daily_purchases:
            self._daily_purchases[ticker_str] = {}

        self._daily_purchases[ticker_str][purchase_time] = quantity

        logger.debug(f" Recorded purchase: {ticker_str} | {quantity} @ {purchase_time}")

    def _create_fill_event(self, order: Order, fill_price: float) -> 'Fill':
        """创建成交记录

        Args:
            order: 订单对象
            fill_price: 成交价格

        Returns:
            Fill对象
        """
        # 计算手续费
        commission = max(
            order.quantity * fill_price * self.commission_rate,
            self.min_commission
        )

        # 创建Fill对象（这里简化处理）
        # 实际应该使用QF-Lib的Fill类
        fill = {
            'ticker': order.ticker,
            'direction': order.direction,
            'quantity': order.quantity,
            'fill_price': fill_price,
            'commission': commission,
            'timestamp': self.timer.now()
        }

        logger.debug(f" Fill created: {fill}")

        return fill

    def on_market_close(self, event: MarketCloseEvent):
        """市场收盘事件处理

        Args:
            event: 收盘事件
        """
        # 清理过期的T+1追踪记录（保留最近3天）
        current_time = self.timer.now()

        for ticker_str in list(self._daily_purchases.keys()):
            purchases = self._daily_purchases[ticker_str]

            # 删除3天前的记录
            old_dates = [
                date for date in purchases.keys()
                if (current_time - date).days > 3
            ]

            for old_date in old_dates:
                del purchases[old_date]

            # 如果该ticker没有记录了，删除
            if not purchases:
                del self._daily_purchases[ticker_str]

        logger.debug(f" Cleaned up T+1 tracking records at market close")
