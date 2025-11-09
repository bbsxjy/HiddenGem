"""
Strategy Runner for Live Execution.
Coordinates strategy execution, order management, and risk control.
"""

import asyncio
from datetime import datetime, time
from decimal import Decimal
from typing import Dict, List, Optional, Set
from collections import defaultdict

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Order, Position, Signal, OrderSide, OrderStatus
from core.strategy.base_strategy import BaseStrategy
from core.execution.order_manager import OrderManager
from core.execution.risk_control import RiskControl
from core.execution.broker_interface import BrokerInterface, create_broker_interface
from core.mcp_agents.orchestrator import MCPOrchestrator
from core.data.models import OrderRequest
from config.settings import settings
from config.database import db_config


class StrategyRunner:
    """
    Strategy Runner for Live Trading.

    Coordinates:
    - Strategy signal generation
    - Order creation and execution
    - Position monitoring
    - Risk management
    - Agent orchestration
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        broker_interface: Optional[BrokerInterface] = None
    ):
        """
        Initialize strategy runner.

        Args:
            strategy: Trading strategy
            broker_interface: Broker interface (optional, defaults to simulation)
        """
        self.strategy = strategy
        self.broker_interface = broker_interface or create_broker_interface("simulation")

        # Initialize components
        self.order_manager = OrderManager(
            broker_interface=self.broker_interface,
            risk_control=RiskControl()
        )
        self.risk_control = RiskControl()
        self.orchestrator = MCPOrchestrator()

        # State
        self.running = False
        self.monitored_symbols: Set[str] = set()
        self.pending_signals: List[Signal] = []

        # Scheduling
        self.scan_interval = 60  # seconds
        self.last_scan_time = None

        logger.info(f"StrategyRunner initialized for strategy: {strategy.name}")

    async def start(self, symbols: List[str]):
        """
        Start live trading.

        Args:
            symbols: List of symbols to monitor
        """
        if self.running:
            logger.warning("StrategyRunner already running")
            return

        self.monitored_symbols = set(symbols)
        self.running = True

        logger.info(f"Starting StrategyRunner with {len(symbols)} symbols")

        # Connect to broker
        try:
            await self.broker_interface.connect()
        except Exception as e:
            logger.exception(f"Failed to connect to broker: {e}")
            self.running = False
            return

        # Start main loop
        try:
            await self._run_main_loop()
        except Exception as e:
            logger.exception(f"Error in main loop: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop live trading."""
        if not self.running:
            return

        logger.info("Stopping StrategyRunner...")
        self.running = False

        # Disconnect from broker
        try:
            await self.broker_interface.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting from broker: {e}")

        logger.info("StrategyRunner stopped")

    async def _run_main_loop(self):
        """Main execution loop."""
        while self.running:
            try:
                # Check if market is open
                if not self._is_market_open():
                    logger.debug("Market closed, waiting...")
                    await asyncio.sleep(60)
                    continue

                # Run strategy scan
                await self._run_strategy_scan()

                # Monitor existing positions
                await self._monitor_positions()

                # Execute pending signals
                await self._execute_pending_signals()

                # Wait for next scan
                await asyncio.sleep(self.scan_interval)

            except Exception as e:
                logger.exception(f"Error in main loop iteration: {e}")
                await asyncio.sleep(10)  # Brief pause before retry

    async def _run_strategy_scan(self):
        """Run strategy analysis on all monitored symbols."""
        logger.info(f"Running strategy scan on {len(self.monitored_symbols)} symbols")

        scan_tasks = []

        async with db_config.AsyncSessionLocal() as db_session:
            for symbol in self.monitored_symbols:
                task = self._analyze_symbol(symbol, db_session)
                scan_tasks.append(task)

            # Run all analyses in parallel
            results = await asyncio.gather(*scan_tasks, return_exceptions=True)

            # Process results
            for symbol, result in zip(self.monitored_symbols, results):
                if isinstance(result, Exception):
                    logger.error(f"Error analyzing {symbol}: {result}")
                elif result:
                    logger.info(f"Generated signal for {symbol}: {result}")

        self.last_scan_time = datetime.utcnow()

    async def _analyze_symbol(
        self,
        symbol: str,
        db_session: AsyncSession
    ) -> Optional[Signal]:
        """
        Analyze symbol and generate signal.

        Args:
            symbol: Stock symbol
            db_session: Database session

        Returns:
            Generated signal or None
        """
        try:
            # Run multi-agent analysis
            agent_results = await self.orchestrator.analyze_symbol(symbol)

            # Generate trading signal
            aggregated_signal = await self.orchestrator.generate_trading_signal(
                symbol,
                agent_results
            )

            if not aggregated_signal:
                logger.debug(f"No signal generated for {symbol}")
                return None

            # Create signal record
            signal = Signal(
                symbol=symbol,
                direction=aggregated_signal.direction,
                strength=aggregated_signal.confidence,
                agent_name="orchestrator",
                strategy_name=self.strategy.name,
                entry_price=aggregated_signal.entry_price,
                target_price=aggregated_signal.target_price,
                stop_loss_price=aggregated_signal.stop_loss_price,
                reasoning=aggregated_signal.reasoning,
                timestamp=datetime.utcnow(),
                is_executed=False
            )

            db_session.add(signal)
            await db_session.commit()
            await db_session.refresh(signal)

            # Add to pending signals
            self.pending_signals.append(signal)

            return signal

        except Exception as e:
            logger.exception(f"Error analyzing {symbol}: {e}")
            return None

    async def _execute_pending_signals(self):
        """Execute pending trading signals."""
        if not self.pending_signals:
            return

        logger.info(f"Executing {len(self.pending_signals)} pending signals")

        async with db_config.AsyncSessionLocal() as db_session:
            executed_signals = []

            for signal in self.pending_signals:
                try:
                    success = await self._execute_signal(signal, db_session)
                    if success:
                        executed_signals.append(signal)
                except Exception as e:
                    logger.exception(f"Error executing signal {signal.id}: {e}")

            # Remove executed signals
            for signal in executed_signals:
                signal.is_executed = True
                self.pending_signals.remove(signal)

            await db_session.commit()

    async def _execute_signal(
        self,
        signal: Signal,
        db_session: AsyncSession
    ) -> bool:
        """
        Execute trading signal.

        Args:
            signal: Trading signal
            db_session: Database session

        Returns:
            True if executed successfully
        """
        logger.info(f"Executing signal: {signal.symbol} {signal.direction.value}")

        # Determine order side
        side = OrderSide.BUY if signal.direction.value in ['buy', 'long'] else OrderSide.SELL

        # Calculate position size
        position_size = await self._calculate_position_size(signal, db_session)

        if position_size <= 0:
            logger.warning(f"Invalid position size for {signal.symbol}: {position_size}")
            return False

        # Create order request
        order_request = OrderRequest(
            symbol=signal.symbol,
            side=side,
            order_type="limit",
            quantity=position_size,
            price=signal.entry_price,
            stop_loss_price=signal.stop_loss_price,
            take_profit_price=signal.target_price,
            strategy_name=self.strategy.name
        )

        try:
            # Create and submit order
            order = await self.order_manager.create_order(order_request, db_session)

            logger.info(
                f"Order created: {order.id} - {order.symbol} {order.side.value} "
                f"{order.quantity} @ {order.price}"
            )

            return True

        except Exception as e:
            logger.exception(f"Failed to execute signal: {e}")
            return False

    async def _calculate_position_size(
        self,
        signal: Signal,
        db_session: AsyncSession
    ) -> int:
        """
        Calculate position size based on signal strength and risk.

        Args:
            signal: Trading signal
            db_session: Database session

        Returns:
            Position size in shares (rounded to nearest lot of 100)
        """
        # Get portfolio value
        portfolio_value = await self.risk_control._get_portfolio_value(db_session)

        # Calculate position value based on signal strength
        # Max position = 10% of portfolio * signal strength
        max_position_value = portfolio_value * Decimal(str(settings.max_position_pct)) * Decimal(str(signal.strength))

        # Calculate shares
        shares = int(max_position_value / signal.entry_price)

        # Round down to nearest lot of 100
        shares = (shares // 100) * 100

        # Ensure minimum lot size
        if shares < 100:
            shares = 0

        logger.info(
            f"Calculated position size for {signal.symbol}: {shares} shares "
            f"(strength={signal.strength:.2f})"
        )

        return shares

    async def _monitor_positions(self):
        """Monitor existing positions for exit signals."""
        async with db_config.AsyncSessionLocal() as db_session:
            # Get current positions
            from sqlalchemy import select
            stmt = select(Position)
            result = await db_session.execute(stmt)
            positions = result.scalars().all()

            if not positions:
                logger.debug("No positions to monitor")
                return

            logger.debug(f"Monitoring {len(positions)} positions")

            for position in positions:
                try:
                    await self._check_position_exit(position, db_session)
                except Exception as e:
                    logger.exception(f"Error monitoring position {position.symbol}: {e}")

    async def _check_position_exit(
        self,
        position: Position,
        db_session: AsyncSession
    ):
        """
        Check if position should be exited.

        Args:
            position: Position to check
            db_session: Database session
        """
        # Get current price (simplified - would use real market data)
        current_price = await self._get_current_price(position.symbol)

        # Check strategy exit conditions
        should_exit, reason = await self.strategy.should_exit(position, current_price)

        if should_exit:
            logger.info(
                f"Exit signal for {position.symbol}: {reason}"
            )

            # Create sell order
            order_request = OrderRequest(
                symbol=position.symbol,
                side=OrderSide.SELL,
                order_type="market",
                quantity=position.quantity,
                price=current_price,
                strategy_name=self.strategy.name
            )

            try:
                order = await self.order_manager.create_order(order_request, db_session)
                logger.info(f"Exit order created: {order.id}")
            except Exception as e:
                logger.exception(f"Failed to create exit order: {e}")

        else:
            # Check risk levels
            risk_assessment = await self.risk_control.check_position_risk(
                position,
                current_price,
                db_session
            )

            if risk_assessment['risk_level'] == 'high':
                logger.warning(
                    f"High risk detected for {position.symbol}: "
                    f"{risk_assessment['risks']}"
                )

    async def _get_current_price(self, symbol: str) -> Decimal:
        """
        Get current market price.

        In production, would fetch from real market data.

        Args:
            symbol: Stock symbol

        Returns:
            Current price
        """
        # Simplified - return simulated price
        # In production, would query from market data source
        return Decimal('10.00')

    def _is_market_open(self) -> bool:
        """
        Check if market is currently open.

        A-share market hours:
        - Morning: 09:30 - 11:30
        - Afternoon: 13:00 - 15:00
        - Monday to Friday (excluding holidays)

        Returns:
            True if market is open
        """
        now = datetime.now()

        # Check day of week (0 = Monday, 6 = Sunday)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        # Check time
        current_time = now.time()

        morning_open = time(9, 30)
        morning_close = time(11, 30)
        afternoon_open = time(13, 0)
        afternoon_close = time(15, 0)

        is_morning_session = morning_open <= current_time <= morning_close
        is_afternoon_session = afternoon_open <= current_time <= afternoon_close

        return is_morning_session or is_afternoon_session

    async def get_status(self) -> Dict:
        """
        Get runner status.

        Returns:
            Status information
        """
        async with db_config.AsyncSessionLocal() as db_session:
            from sqlalchemy import select
            stmt = select(Position)
            result = await db_session.execute(stmt)
            positions = result.scalars().all()

            return {
                'running': self.running,
                'strategy': self.strategy.name,
                'monitored_symbols': list(self.monitored_symbols),
                'pending_signals': len(self.pending_signals),
                'active_positions': len(positions),
                'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
                'market_open': self._is_market_open(),
                'scan_interval': self.scan_interval
            }
