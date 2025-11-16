"""
Paper Trading Engine

模拟交易引擎，用于实时模拟交易测试。
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging

from .market_data_feed import RealTimeMarketFeed
from .simulated_broker import SimulatedBroker
from .portfolio_manager import PortfolioManager
from .order_manager import OrderManager
from .risk_manager import RiskManager
from .order import Order, OrderType, OrderSide

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """模拟交易引擎

    实时运行模拟交易，支持：
    - 实时数据获取
    - RL决策循环
    - 订单生成和执行
    - 风控检查
    - 启动/停止控制
    """

    def __init__(
        self,
        rl_agent=None,
        initial_cash: float = 100000.0,
        symbols: Optional[List[str]] = None,
        update_interval: int = 60,  # 更新间隔（秒）
        enable_risk_control: bool = True
    ):
        """
        初始化Paper Trading引擎

        Args:
            rl_agent: RL代理（可选，如果不提供则使用简单策略）
            initial_cash: 初始资金
            symbols: 交易股票列表
            update_interval: 更新间隔（秒）
            enable_risk_control: 是否启用风控
        """
        self.rl_agent = rl_agent
        self.initial_cash = initial_cash
        self.symbols = symbols or []
        self.update_interval = update_interval

        # 初始化组件
        self.market_feed = RealTimeMarketFeed(provider='tushare')
        self.broker = SimulatedBroker(initial_cash=initial_cash)
        self.portfolio = PortfolioManager(initial_cash=initial_cash)
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager(enable_controls=enable_risk_control)

        # 运行状态
        self.is_running = False
        self.is_paused = False
        self.total_updates = 0
        self.start_time: Optional[datetime] = None

        logger.info(f" PaperTradingEngine initialized (cash=¥{initial_cash:,.2f}, symbols={symbols})")

    async def run(self, symbols: Optional[List[str]] = None):
        """
        运行模拟交易

        Args:
            symbols: 股票代码列表（覆盖初始化时的设置）
        """
        if symbols:
            self.symbols = symbols

        if not self.symbols:
            logger.error(" No symbols to trade")
            return

        self.is_running = True
        self.start_time = datetime.now()

        logger.info(f" Paper Trading started for symbols: {self.symbols}")

        try:
            while self.is_running:
                if not self.is_paused:
                    await self._update_cycle()

                await asyncio.sleep(self.update_interval)

        except KeyboardInterrupt:
            logger.info("⏹ Paper Trading stopped by user")
        except Exception as e:
            logger.error(f" Error in paper trading loop: {e}")
        finally:
            self.is_running = False
            self._print_summary()

    async def _update_cycle(self):
        """单次更新周期"""
        try:
            self.total_updates += 1
            logger.info(f"\n{'='*60}")
            logger.info(f" Update #{self.total_updates} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'='*60}")

            for symbol in self.symbols:
                await self._process_symbol(symbol)

            # 更新投资组合
            self._update_portfolio()

            # 打印状态
            self._print_status()

        except Exception as e:
            logger.error(f" Error in update cycle: {e}")

    async def _process_symbol(self, symbol: str):
        """
        处理单个股票

        Args:
            symbol: 股票代码
        """
        try:
            # 1. 获取实时数据
            market_data = await self.market_feed.get_realtime_data_async(symbol)

            if not market_data:
                logger.warning(f" No market data for {symbol}")
                return

            current_price = market_data['price']

            # 2. RL决策（如果有RL agent）
            if self.rl_agent:
                action = await self._get_rl_action(symbol, market_data)
            else:
                # 使用简单策略（示例：随机交易）
                action = self._get_simple_action(symbol, current_price)

            # 3. 生成订单
            if action is not None:
                order = self._create_order_from_action(symbol, action, current_price)

                if order:
                    # 4. 风控检查
                    passed, reason = self.risk_manager.validate_order(
                        order, self.portfolio, current_price
                    )

                    if passed:
                        # 5. 提交并执行订单
                        if self.broker.submit_order(order):
                            self.broker.execute_market_order(order, current_price)
                            self.order_manager.add_order(order)

                            # 记录交易
                            if order.commission:
                                self.risk_manager.record_trade(-order.commission)
                    else:
                        logger.warning(f" Order rejected by risk control: {reason}")

        except Exception as e:
            logger.error(f" Error processing {symbol}: {e}")

    async def _get_rl_action(self, symbol: str, market_data: Dict) -> Optional[int]:
        """
        从RL agent获取动作

        Args:
            symbol: 股票代码
            market_data: 市场数据

        Returns:
            动作ID（0=HOLD, 1=BUY_10, 2=BUY_20, 3=SELL_10, 4=SELL_20, 5=CLOSE）
        """
        # TODO: 集成实际的RL agent
        # state = self._build_state(symbol, market_data)
        # action = self.rl_agent.predict(state)
        # return action

        logger.debug(" RL agent not implemented, using simple strategy")
        return None

    def _get_simple_action(self, symbol: str, current_price: float) -> Optional[int]:
        """
        简单策略（示例）

        Args:
            symbol: 股票代码
            current_price: 当前价格

        Returns:
            动作ID
        """
        # 示例：如果没有持仓则买入，有持仓则持有
        if symbol not in self.portfolio.positions:
            return 1  # BUY_10
        else:
            return 0  # HOLD

    def _create_order_from_action(
        self,
        symbol: str,
        action: int,
        current_price: float
    ) -> Optional[Order]:
        """
        从动作创建订单

        Args:
            symbol: 股票代码
            action: 动作ID
            current_price: 当前价格

        Returns:
            订单对象
        """
        # 动作映射
        # 0: HOLD, 1: BUY_10%, 2: BUY_20%, 3: SELL_10%, 4: SELL_20%, 5: CLOSE_ALL

        if action == 0:  # HOLD
            return None

        total_value = self.portfolio.get_total_value()

        if action == 1:  # BUY 10%
            order_value = total_value * 0.1
            quantity = int(order_value / current_price / 100) * 100  # A股100股为1手
            return Order(symbol=symbol, side=OrderSide.BUY, quantity=quantity, order_type=OrderType.MARKET)

        elif action == 2:  # BUY 20%
            order_value = total_value * 0.2
            quantity = int(order_value / current_price / 100) * 100
            return Order(symbol=symbol, side=OrderSide.BUY, quantity=quantity, order_type=OrderType.MARKET)

        elif action == 3:  # SELL 10%
            if symbol in self.portfolio.positions:
                current_shares = self.portfolio.positions[symbol].quantity
                quantity = int(current_shares * 0.1 / 100) * 100
                if quantity > 0:
                    return Order(symbol=symbol, side=OrderSide.SELL, quantity=quantity, order_type=OrderType.MARKET)
            return None

        elif action == 4:  # SELL 20%
            if symbol in self.portfolio.positions:
                current_shares = self.portfolio.positions[symbol].quantity
                quantity = int(current_shares * 0.2 / 100) * 100
                if quantity > 0:
                    return Order(symbol=symbol, side=OrderSide.SELL, quantity=quantity, order_type=OrderType.MARKET)
            return None

        elif action == 5:  # CLOSE ALL
            if symbol in self.portfolio.positions:
                quantity = self.portfolio.positions[symbol].quantity
                return Order(symbol=symbol, side=OrderSide.SELL, quantity=quantity, order_type=OrderType.MARKET)
            return None

        return None

    def _update_portfolio(self):
        """更新投资组合状态"""
        # 同步broker的状态到portfolio
        self.portfolio.cash = self.broker.cash
        self.portfolio.positions = self.broker.positions.copy()

    def _print_status(self):
        """打印当前状态"""
        balance = self.broker.get_balance()

        logger.info(f"\n Portfolio Status:")
        logger.info(f"   Cash: ¥{balance['cash']:,.2f}")
        logger.info(f"   Market Value: ¥{balance['market_value']:,.2f}")
        logger.info(f"   Total Assets: ¥{balance['total_assets']:,.2f}")
        logger.info(f"   Profit: ¥{balance['profit']:,.2f} ({balance['profit_pct']:.2%})")

        if self.broker.positions:
            logger.info(f"\n Positions:")
            for symbol, pos in self.broker.positions.items():
                logger.info(f"   {symbol}: {pos.quantity} shares @ ¥{pos.avg_price:.2f}")

    def _print_summary(self):
        """打印交易总结"""
        if self.start_time:
            duration = datetime.now() - self.start_time
            logger.info(f"\n{'='*60}")
            logger.info(f" Paper Trading Summary")
            logger.info(f"{'='*60}")
            logger.info(f"Duration: {duration}")
            logger.info(f"Total Updates: {self.total_updates}")

        balance = self.broker.get_balance()
        logger.info(f"Final Balance: ¥{balance['total_assets']:,.2f}")
        logger.info(f"Total Profit: ¥{balance['profit']:,.2f} ({balance['profit_pct']:.2%})")
        logger.info(f"Total Trades: {len(self.broker.trade_history)}")

    def stop(self):
        """停止模拟交易"""
        self.is_running = False
        logger.info("⏹ Stopping paper trading...")

    def pause(self):
        """暂停模拟交易"""
        self.is_paused = True
        logger.info("⏸ Paper trading paused")

    def resume(self):
        """恢复模拟交易"""
        self.is_paused = False
        logger.info("▶ Paper trading resumed")

    def get_status(self) -> Dict:
        """
        获取运行状态

        Returns:
            状态信息字典
        """
        balance = self.broker.get_balance()

        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'total_updates': self.total_updates,
            'symbols': self.symbols,
            'balance': balance,
            'positions': self.broker.get_positions(),
            'trade_count': len(self.broker.trade_history),
            'risk_stats': self.risk_manager.get_stats()
        }
