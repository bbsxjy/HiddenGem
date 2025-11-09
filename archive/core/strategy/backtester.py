"""
Simple Backtesting Engine for Strategy Validation.

This is a basic backtesting engine. For production, consider using
established frameworks like RQAlpha or Backtrader.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import pandas as pd
from loguru import logger

from core.strategy.base_strategy import BaseStrategy
from core.data.models import BacktestConfig, BacktestResult, OrderRequest, OrderSide
from core.data.sources import data_source


@dataclass
class BacktestPosition:
    """Position in backtest."""
    symbol: str
    quantity: int
    avg_cost: Decimal
    entry_date: datetime
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None


@dataclass
class BacktestTrade:
    """Completed trade in backtest."""
    symbol: str
    entry_date: datetime
    exit_date: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: int
    pnl: Decimal
    pnl_pct: float
    exit_reason: str


@dataclass
class BacktestState:
    """Backtest state."""
    cash: Decimal
    positions: Dict[str, BacktestPosition] = field(default_factory=dict)
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[tuple[datetime, Decimal]] = field(default_factory=list)


class SimpleBacktester:
    """
    Simple backtesting engine.

    Simulates strategy execution on historical data.
    """

    def __init__(self, config: BacktestConfig):
        """
        Initialize backtester.

        Args:
            config: Backtest configuration
        """
        self.config = config
        self.commission_rate = config.commission_rate
        self.slippage = config.slippage

        # State
        self.state = BacktestState(cash=config.initial_capital)
        self.current_date: Optional[datetime] = None

    async def run(
        self,
        strategy: BaseStrategy,
        symbols: Optional[List[str]] = None
    ) -> BacktestResult:
        """
        Run backtest.

        Args:
            strategy: Strategy to test
            symbols: List of symbols (or use config.symbols)

        Returns:
            Backtest results
        """
        symbols = symbols or self.config.symbols or []

        if not symbols:
            raise ValueError("No symbols provided for backtest")

        logger.info(
            f"Starting backtest: strategy={strategy.name}, "
            f"symbols={len(symbols)}, "
            f"period={self.config.start_date} to {self.config.end_date}"
        )

        # Load market data for all symbols
        market_data = await self._load_market_data(symbols)

        if not market_data:
            raise ValueError("Failed to load market data")

        # Get all trading dates
        trading_dates = self._get_trading_dates(market_data)

        logger.info(f"Backtesting {len(trading_dates)} trading days")

        # Run backtest day by day
        for current_date in trading_dates:
            self.current_date = current_date
            await self._process_day(strategy, symbols, market_data, current_date)

        # Calculate results
        result = self._calculate_results(strategy)

        logger.info(
            f"Backtest completed: "
            f"return={result.total_return_pct:.2%}, "
            f"trades={result.num_trades}"
        )

        return result

    async def _load_market_data(
        self,
        symbols: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """Load historical market data."""
        market_data = {}

        for symbol in symbols:
            try:
                df = data_source.get_daily_bars(
                    symbol,
                    self.config.start_date.strftime("%Y-%m-%d"),
                    self.config.end_date.strftime("%Y-%m-%d")
                )

                if not df.empty:
                    market_data[symbol] = df
                    logger.debug(f"Loaded {len(df)} bars for {symbol}")

            except Exception as e:
                logger.warning(f"Failed to load data for {symbol}: {e}")

        return market_data

    def _get_trading_dates(
        self,
        market_data: Dict[str, pd.DataFrame]
    ) -> List[datetime]:
        """Get sorted list of all trading dates."""
        all_dates = set()

        for df in market_data.values():
            if 'date' in df.columns:
                all_dates.update(df['date'].tolist())

        return sorted(all_dates)

    async def _process_day(
        self,
        strategy: BaseStrategy,
        symbols: List[str],
        market_data: Dict[str, pd.DataFrame],
        current_date: datetime
    ):
        """Process one trading day."""
        # 1. Update positions with current prices
        await self._update_positions(market_data, current_date)

        # 2. Check exit conditions for existing positions
        await self._check_exits(strategy, market_data, current_date)

        # 3. Generate entry signals
        await self._generate_entries(strategy, symbols, market_data, current_date)

        # 4. Record equity
        equity = self._calculate_equity(market_data, current_date)
        self.state.equity_curve.append((current_date, equity))

    async def _update_positions(
        self,
        market_data: Dict[str, pd.DataFrame],
        current_date: datetime
    ):
        """Update position prices."""
        for symbol, position in list(self.state.positions.items()):
            if symbol not in market_data:
                continue

            df = market_data[symbol]
            day_data = df[df['date'] == current_date]

            if day_data.empty:
                continue

            current_price = Decimal(str(day_data.iloc[0]['close']))

            # Check stop-loss
            if position.stop_loss and current_price <= position.stop_loss:
                await self._close_position(symbol, current_price, "stop_loss")

            # Check take-profit
            elif position.take_profit and current_price >= position.take_profit:
                await self._close_position(symbol, current_price, "take_profit")

    async def _check_exits(
        self,
        strategy: BaseStrategy,
        market_data: Dict[str, pd.DataFrame],
        current_date: datetime
    ):
        """Check strategy exit conditions."""
        for symbol in list(self.state.positions.keys()):
            if symbol not in market_data:
                continue

            df = market_data[symbol]
            day_data = df[df['date'] == current_date]

            if day_data.empty:
                continue

            current_price = Decimal(str(day_data.iloc[0]['close']))

            # Create position info for strategy
            position = self.state.positions[symbol]
            from core.data.models import PositionInfo

            pos_info = PositionInfo(
                symbol=symbol,
                quantity=position.quantity,
                avg_cost=position.avg_cost,
                current_price=current_price,
                entry_date=position.entry_date,
                board="main"  # Simplified
            )

            # Check strategy exit
            should_exit, reason = strategy.should_exit(pos_info, current_price)

            if should_exit:
                await self._close_position(symbol, current_price, reason)

    async def _generate_entries(
        self,
        strategy: BaseStrategy,
        symbols: List[str],
        market_data: Dict[str, pd.DataFrame],
        current_date: datetime
    ):
        """Generate entry signals."""
        # Don't generate new signals if we're at max positions
        if len(self.state.positions) >= strategy.max_positions:
            return

        # Get signals from strategy
        # (Simplified - would need to pass historical data up to current_date)
        # signals = await strategy.generate_signals(symbols, market_data)

        # For now, skip signal generation in backtest
        # Full implementation would require more sophisticated data handling
        pass

    async def _close_position(
        self,
        symbol: str,
        exit_price: Decimal,
        reason: str
    ):
        """Close a position."""
        if symbol not in self.state.positions:
            return

        position = self.state.positions[symbol]

        # Apply slippage
        actual_exit_price = exit_price * Decimal(str(1 - self.slippage))

        # Calculate P&L
        gross_proceeds = actual_exit_price * position.quantity
        commission = gross_proceeds * Decimal(str(self.commission_rate))
        net_proceeds = gross_proceeds - commission

        cost_basis = position.avg_cost * position.quantity
        pnl = net_proceeds - cost_basis
        pnl_pct = float(pnl / cost_basis)

        # Record trade
        trade = BacktestTrade(
            symbol=symbol,
            entry_date=position.entry_date,
            exit_date=self.current_date,
            entry_price=position.avg_cost,
            exit_price=actual_exit_price,
            quantity=position.quantity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=reason
        )

        self.state.trades.append(trade)
        self.state.cash += net_proceeds

        # Remove position
        del self.state.positions[symbol]

        logger.debug(
            f"Closed position: {symbol}, pnl={pnl:.2f} ({pnl_pct:.2%}), reason={reason}"
        )

    def _calculate_equity(
        self,
        market_data: Dict[str, pd.DataFrame],
        current_date: datetime
    ) -> Decimal:
        """Calculate total equity."""
        equity = self.state.cash

        for symbol, position in self.state.positions.items():
            if symbol in market_data:
                df = market_data[symbol]
                day_data = df[df['date'] == current_date]

                if not day_data.empty:
                    price = Decimal(str(day_data.iloc[0]['close']))
                    equity += price * position.quantity

        return equity

    def _calculate_results(self, strategy: BaseStrategy) -> BacktestResult:
        """Calculate backtest results."""
        if not self.state.equity_curve:
            raise ValueError("No equity curve data")

        initial_capital = self.config.initial_capital
        final_capital = self.state.equity_curve[-1][1]
        total_return = final_capital - initial_capital
        total_return_pct = float(total_return / initial_capital)

        # Calculate annualized return
        days = (self.config.end_date - self.config.start_date).days
        years = days / 365.25
        annual_return_pct = (1 + total_return_pct) ** (1 / years) - 1 if years > 0 else 0

        # Calculate Sharpe ratio (simplified)
        if len(self.state.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.state.equity_curve)):
                prev_equity = self.state.equity_curve[i-1][1]
                curr_equity = self.state.equity_curve[i][1]
                daily_return = float((curr_equity - prev_equity) / prev_equity)
                returns.append(daily_return)

            import numpy as np
            if len(returns) > 0 and np.std(returns) > 0:
                sharpe_ratio = np.mean(returns) / np.std(returns) * (252 ** 0.5)
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0

        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown()

        # Win rate
        winning_trades = [t for t in self.state.trades if t.pnl > 0]
        win_rate = len(winning_trades) / len(self.state.trades) if self.state.trades else 0

        return BacktestResult(
            strategy_name=strategy.name,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            annual_return_pct=annual_return_pct,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            num_trades=len(self.state.trades),
            timestamp=datetime.utcnow()
        )

    def _calculate_max_drawdown(self) -> Optional[float]:
        """Calculate maximum drawdown."""
        if len(self.state.equity_curve) < 2:
            return None

        peak = self.state.equity_curve[0][1]
        max_dd = 0.0

        for _, equity in self.state.equity_curve:
            if equity > peak:
                peak = equity

            dd = float((peak - equity) / peak)
            if dd > max_dd:
                max_dd = dd

        return max_dd
