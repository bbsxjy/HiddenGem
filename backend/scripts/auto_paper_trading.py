"""
Automated Paper Trading with China Trading Hours

This script runs automated paper trading that:
1. Respects China trading hours (9:30-11:30am, 1-3pm Beijing time)
2. Uses RL Strategy + Multi-Agent LLM Strategy
3. Starts from tomorrow (or specified date)
4. Provides detailed logging and performance tracking
"""

import sys
from pathlib import Path
from datetime import datetime, time, timedelta
import pytz
import asyncio
import logging
import signal

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trading.rl_strategy import RLStrategy
from trading.multi_agent_strategy import MultiAgentStrategy
from trading.simulated_broker import SimulatedBroker
from trading.order import Order, OrderSide, OrderType

# Setup logging (no emoji)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)

logger = logging.getLogger(__name__)

# China timezone
CHINA_TZ = pytz.timezone('Asia/Shanghai')

# Trading hours (Beijing time)
MORNING_SESSION_START = time(9, 30)
MORNING_SESSION_END = time(11, 30)
AFTERNOON_SESSION_START = time(13, 0)
AFTERNOON_SESSION_END = time(15, 0)


class AutoPaperTrader:
    """
    Automated Paper Trading System

    Combines RL Strategy and Multi-Agent LLM Strategy for intelligent trading
    during China market hours.
    """

    def __init__(
        self,
        symbols: list,
        initial_cash: float = 100000.0,
        rl_model_path: str = "models/ppo_trading_agent.zip",
        check_interval_minutes: int = 5,
        use_multi_agent: bool = True
    ):
        """
        Initialize Auto Paper Trader

        Args:
            symbols: List of stock symbols to trade
            initial_cash: Initial capital (CNY)
            rl_model_path: Path to trained RL model
            check_interval_minutes: How often to check for trades (minutes)
            use_multi_agent: Whether to use Multi-Agent LLM strategy
        """
        self.symbols = symbols
        self.initial_cash = initial_cash
        self.check_interval = timedelta(minutes=check_interval_minutes)
        self.use_multi_agent = use_multi_agent

        # Initialize strategies
        logger.info("[INIT] Initializing strategies...")
        self.rl_strategy = RLStrategy(model_path=rl_model_path)

        if use_multi_agent:
            self.multi_agent_strategy = MultiAgentStrategy()
            logger.info("[INIT] Multi-Agent strategy initialized")
        else:
            self.multi_agent_strategy = None

        # Initialize broker
        self.broker = SimulatedBroker(initial_cash=initial_cash)
        logger.info(f"[INIT] Broker initialized with CNY {initial_cash:,.2f}")

        # Trading state
        self.is_running = False
        self.start_time = None
        self.trades_today = 0
        self.last_check_time = None

        logger.info("[SUCCESS] Auto Paper Trader initialized")

    def is_trading_hours(self, current_time: datetime = None) -> bool:
        """
        Check if current time is within China trading hours

        Args:
            current_time: Time to check (defaults to now)

        Returns:
            True if within trading hours
        """
        if current_time is None:
            current_time = datetime.now(CHINA_TZ)

        current_time_only = current_time.time()

        # Check if it's a weekday (Monday=0, Sunday=6)
        if current_time.weekday() >= 5:  # Saturday or Sunday
            return False

        # Check trading sessions
        in_morning = MORNING_SESSION_START <= current_time_only <= MORNING_SESSION_END
        in_afternoon = AFTERNOON_SESSION_START <= current_time_only <= AFTERNOON_SESSION_END

        return in_morning or in_afternoon

    def get_next_trading_time(self, current_time: datetime = None) -> datetime:
        """
        Get the next trading time

        Args:
            current_time: Current time (defaults to now)

        Returns:
            Next trading time
        """
        if current_time is None:
            current_time = datetime.now(CHINA_TZ)

        current_time_only = current_time.time()

        # If before morning session, wait for morning
        if current_time_only < MORNING_SESSION_START:
            next_time = current_time.replace(
                hour=MORNING_SESSION_START.hour,
                minute=MORNING_SESSION_START.minute,
                second=0,
                microsecond=0
            )
            return next_time

        # If in morning session, continue
        if MORNING_SESSION_START <= current_time_only <= MORNING_SESSION_END:
            return current_time

        # If between sessions, wait for afternoon
        if MORNING_SESSION_END < current_time_only < AFTERNOON_SESSION_START:
            next_time = current_time.replace(
                hour=AFTERNOON_SESSION_START.hour,
                minute=AFTERNOON_SESSION_START.minute,
                second=0,
                microsecond=0
            )
            return next_time

        # If in afternoon session, continue
        if AFTERNOON_SESSION_START <= current_time_only <= AFTERNOON_SESSION_END:
            return current_time

        # If after market close, wait for tomorrow morning
        next_day = current_time + timedelta(days=1)
        while next_day.weekday() >= 5:  # Skip weekends
            next_day += timedelta(days=1)

        next_time = next_day.replace(
            hour=MORNING_SESSION_START.hour,
            minute=MORNING_SESSION_START.minute,
            second=0,
            microsecond=0
        )
        return next_time

    async def run(self):
        """Run the auto trading system"""
        self.is_running = True
        self.start_time = datetime.now(CHINA_TZ)

        logger.info("=" * 80)
        logger.info("[START] Auto Paper Trading System")
        logger.info("=" * 80)
        logger.info(f"[CONFIG] Symbols: {self.symbols}")
        logger.info(f"[CONFIG] Initial Cash: CNY {self.initial_cash:,.2f}")
        logger.info(f"[CONFIG] Check Interval: {self.check_interval.total_seconds() / 60} minutes")
        logger.info(f"[CONFIG] Multi-Agent: {'Enabled' if self.use_multi_agent else 'Disabled'}")
        logger.info(f"[CONFIG] Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info("")

        try:
            while self.is_running:
                current_time = datetime.now(CHINA_TZ)

                # Check if in trading hours
                if self.is_trading_hours(current_time):
                    # Perform trading check
                    await self.trading_cycle(current_time)

                    # Wait for next check
                    await asyncio.sleep(self.check_interval.total_seconds())

                else:
                    # Not in trading hours, calculate wait time
                    next_trading_time = self.get_next_trading_time(current_time)
                    wait_seconds = (next_trading_time - current_time).total_seconds()

                    logger.info(f"[WAIT] Outside trading hours. Next session: {next_trading_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                    logger.info(f"[WAIT] Waiting {wait_seconds / 3600:.1f} hours...")

                    # Sleep until next trading time (with periodic checks)
                    sleep_interval = min(wait_seconds, 300)  # Check every 5 minutes max
                    await asyncio.sleep(sleep_interval)

        except KeyboardInterrupt:
            logger.info("[STOP] Interrupted by user")
        except Exception as e:
            logger.error(f"[ERROR] Trading loop failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self.is_running = False
            self.print_summary()

    async def trading_cycle(self, current_time: datetime):
        """
        Perform one trading cycle

        Args:
            current_time: Current time
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"[CYCLE] Trading Check at {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info("=" * 80)

        for symbol in self.symbols:
            await self.check_symbol(symbol, current_time)

        # Print current status
        self.print_status()

    async def check_symbol(self, symbol: str, current_time: datetime):
        """
        Check and potentially trade a symbol

        Args:
            symbol: Stock symbol
            current_time: Current time
        """
        logger.info(f"[{symbol}] Checking...")

        try:
            # 1. 获取实时行情数据
            from api.services.realtime_data_service import realtime_data_service
            quote = realtime_data_service.get_realtime_quote(symbol)

            if not quote:
                logger.warning(f"[{symbol}] No market data available, skipping")
                return

            current_price = quote['price']
            change_pct = quote['change']
            logger.info(f"[{symbol}] Price: {current_price:.2f}, Change: {change_pct:+.2f}%")

            # 2. 生成交易决策（简化版）
            decision = self._make_decision(symbol, quote)

            if decision['action'] == 'hold':
                logger.info(f"[{symbol}] Decision: HOLD - {decision['reason']}")
                return

            # 3. 检查当前持仓
            current_position = self.broker.positions.get(symbol)
            has_position = current_position is not None and current_position.quantity > 0

            # 4. 执行交易决策
            if decision['action'] == 'buy' and not has_position:
                # 计算购买数量
                quantity = self._calculate_buy_quantity(current_price, decision['confidence'])

                if quantity >= 100:  # A股最小100股
                    logger.info(f"[{symbol}] Decision: BUY {quantity} shares @ {current_price:.2f}")
                    logger.info(f"[{symbol}] Reason: {decision['reason']}")

                    # 下买单
                    order = Order(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=quantity,
                        price=current_price
                    )

                    filled_order = self.broker.submit_order(order)

                    if filled_order:
                        self.trades_today += 1
                        logger.info(f"[{symbol}] ORDER FILLED: Bought {quantity} shares @ {filled_order.filled_price:.2f}")
                    else:
                        logger.warning(f"[{symbol}] ORDER FAILED: Insufficient funds or other error")
                else:
                    logger.info(f"[{symbol}] Buy quantity too small ({quantity}), skipping")

            elif decision['action'] == 'sell' and has_position:
                # 卖出全部持仓
                quantity = current_position.quantity

                logger.info(f"[{symbol}] Decision: SELL {quantity} shares @ {current_price:.2f}")
                logger.info(f"[{symbol}] Reason: {decision['reason']}")

                # 下卖单
                order = Order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=quantity,
                    price=current_price
                )

                filled_order = self.broker.submit_order(order)

                if filled_order:
                    self.trades_today += 1
                    profit = (filled_order.filled_price - current_position.avg_price) * quantity
                    profit_pct = ((filled_order.filled_price / current_position.avg_price) - 1) * 100

                    logger.info(f"[{symbol}] ORDER FILLED: Sold {quantity} shares @ {filled_order.filled_price:.2f}")
                    logger.info(f"[{symbol}] PROFIT: {profit:+,.2f} ({profit_pct:+.2f}%)")
                else:
                    logger.warning(f"[{symbol}] ORDER FAILED: Insufficient position or other error")

        except Exception as e:
            logger.error(f"[{symbol}] Error during check: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _make_decision(self, symbol: str, quote: dict) -> dict:
        """
        Make trading decision based on market data (T+1 制度)

        T+1 规则：
        - 今天买入的股票明天才能卖出
        - 买入条件更严格（因为至少持有1天）
        - 止损止盈阈值调整（无法日内快速止损）

        Args:
            symbol: Stock symbol
            quote: Market quote data

        Returns:
            Decision dict with action, reason, confidence
        """
        change_pct = quote['change']
        volume_ratio = quote.get('volume_ratio', 1.0)
        turnover_rate = quote.get('turnover_rate', 0)
        amplitude = quote.get('amplitude', 0)

        position = self.broker.positions.get(symbol)

        # === 买入决策 ===
        if not position:
            # T+1 买入条件：更严格（涨幅 > 3%, 量比 > 1.2）
            if change_pct > 3.0 and volume_ratio > 1.2:
                # 隔夜风险控制
                if amplitude > 8:  # 振幅过大，风险高
                    return {
                        'action': 'hold',
                        'reason': f'振幅{amplitude:.2f}%过大，隔夜风险高',
                        'confidence': 0.3
                    }

                if turnover_rate > 15:  # 换手率过高，投机性强
                    return {
                        'action': 'hold',
                        'reason': f'换手率{turnover_rate:.2f}%过高，投机性强',
                        'confidence': 0.3
                    }

                return {
                    'action': 'buy',
                    'reason': f'涨幅{change_pct:.2f}%，量比{volume_ratio:.2f}，趋势强劲（T+1）',
                    'confidence': min(0.6 + change_pct / 20, 0.9)
                }

        # === 卖出决策 (T+1: 只能卖持仓 >= 1天的股票) ===
        if position:
            # 计算持仓天数
            hold_days = (datetime.now() - position.opened_time).days

            if hold_days < 1:
                # T+1 限制：当天买入无法卖出
                return {
                    'action': 'hold',
                    'reason': f'T+1限制：持仓{hold_days}天，明天才能卖出',
                    'confidence': 0.5
                }

            # 持仓 >= 1天，可以卖出
            current_price = quote['price']
            profit_pct = ((current_price / position.avg_price) - 1) * 100

            # 止损：-5% (T+1 无法快速止损，阈值放宽)
            if profit_pct < -5.0:
                return {
                    'action': 'sell',
                    'reason': f'持仓{hold_days}天，亏损{abs(profit_pct):.2f}%，止损',
                    'confidence': 0.9
                }

            # 止盈：+8% (T+1 降低交易频率，提高目标)
            if profit_pct > 8.0:
                return {
                    'action': 'sell',
                    'reason': f'持仓{hold_days}天，盈利{profit_pct:.2f}%，止盈',
                    'confidence': 0.9
                }

            # 日内大跌警告（但无法卖出）
            if change_pct < -3.0 and hold_days < 1:
                return {
                    'action': 'hold',
                    'reason': f'日内跌幅{abs(change_pct):.2f}%，但T+1无法卖出',
                    'confidence': 0.2
                }

        # 默认持有
        return {
            'action': 'hold',
            'reason': f'涨跌幅{change_pct:.2f}%，未达到交易条件',
            'confidence': 0.5
        }

    def _calculate_buy_quantity(self, price: float, confidence: float) -> int:
        """
        Calculate buy quantity based on price and confidence (T+1 仓位管理)

        T+1 制度下，无法当天止损，风险更高，因此：
        - 单个仓位从10%降低到5-8%
        - 根据置信度和风险调整

        Args:
            price: Current stock price
            confidence: Decision confidence (0-1)

        Returns:
            Quantity in lots of 100 (A-share minimum unit)
        """
        balance = self.broker.get_balance()

        # T+1 最大单个仓位：总资金的5%（原10%）
        # 因为无法当天止损，风险更高
        max_position_value = balance['cash'] * 0.05

        # 根据置信度调整仓位
        position_value = max_position_value * confidence

        # 计算数量（取整到100的倍数）
        quantity = int(position_value / price / 100) * 100

        return max(100, quantity)  # 至少100股

    def print_status(self):
        """Print current portfolio status"""
        balance = self.broker.get_balance()

        logger.info("")
        logger.info("[STATUS] Portfolio:")
        logger.info(f"   Cash: CNY {balance['cash']:,.2f}")
        logger.info(f"   Market Value: CNY {balance['market_value']:,.2f}")
        logger.info(f"   Total Assets: CNY {balance['total_assets']:,.2f}")
        logger.info(f"   Profit: CNY {balance['profit']:,.2f} ({balance['profit_pct']:.2%})")
        logger.info(f"   Trades Today: {self.trades_today}")

        if self.broker.positions:
            logger.info("[POSITIONS]:")
            for symbol, pos in self.broker.positions.items():
                logger.info(f"   {symbol}: {pos.quantity} shares @ CNY {pos.avg_price:.2f}")

    def print_summary(self):
        """Print trading session summary"""
        if self.start_time:
            duration = datetime.now(CHINA_TZ) - self.start_time
            logger.info("")
            logger.info("=" * 80)
            logger.info("[SUMMARY] Trading Session Summary")
            logger.info("=" * 80)
            logger.info(f"Duration: {duration}")
            logger.info(f"Total Trades: {len(self.broker.trade_history)}")

        balance = self.broker.get_balance()
        logger.info(f"Final Balance: CNY {balance['total_assets']:,.2f}")
        logger.info(f"Total Profit: CNY {balance['profit']:,.2f} ({balance['profit_pct']:.2%})")
        logger.info("=" * 80)

    def stop(self):
        """Stop the auto trading system"""
        self.is_running = False
        logger.info("[STOP] Stopping auto trading system...")


def main():
    """Main entry point"""

    # Configuration
    SYMBOLS = ["000001", "600519", "000858"]
    INITIAL_CASH = 100000.0
    RL_MODEL_PATH = "models/ppo_trading_agent.zip"
    CHECK_INTERVAL = 5  # minutes
    USE_MULTI_AGENT = True

    logger.info("=" * 80)
    logger.info("Auto Paper Trading System")
    logger.info("=" * 80)
    logger.info("")

    # Show trading hours info
    now = datetime.now(CHINA_TZ)
    logger.info(f"Current Time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"Trading Hours:")
    logger.info(f"   Morning: {MORNING_SESSION_START} - {MORNING_SESSION_END}")
    logger.info(f"   Afternoon: {AFTERNOON_SESSION_START} - {AFTERNOON_SESSION_END}")
    logger.info("")

    # Create trader
    trader = AutoPaperTrader(
        symbols=SYMBOLS,
        initial_cash=INITIAL_CASH,
        rl_model_path=RL_MODEL_PATH,
        check_interval_minutes=CHECK_INTERVAL,
        use_multi_agent=USE_MULTI_AGENT
    )

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("\n[SIGNAL] Received interrupt signal")
        trader.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run trader
    try:
        asyncio.run(trader.run())
    except KeyboardInterrupt:
        logger.info("\n[EXIT] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[ERROR] Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
