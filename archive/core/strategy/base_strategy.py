"""
Base Strategy Framework.
All trading strategies inherit from this base class.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any

import pandas as pd
from loguru import logger

from core.data.models import (
    TradingSignal, PositionInfo, SignalDirection,
    StrategyConfig, OrderRequest, OrderSide
)
from core.mcp_agents.orchestrator import MCPOrchestrator
from core.utils.helpers import (
    calculate_position_size, calculate_stop_loss_price,
    calculate_take_profit_price, get_trading_board
)
from database.models import TradingBoard


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.

    Provides common functionality for:
    - Position management
    - Risk management
    - Signal generation
    - Order creation
    """

    def __init__(
        self,
        config: StrategyConfig,
        orchestrator: Optional[MCPOrchestrator] = None
    ):
        """
        Initialize strategy.

        Args:
            config: Strategy configuration
            orchestrator: MCP orchestrator for agent-based analysis
        """
        self.config = config
        self.name = config.name
        self.orchestrator = orchestrator
        self.enabled = config.enabled

        # Strategy parameters
        self.max_positions = config.max_positions
        self.position_size = config.position_size
        self.stop_loss_pct = config.stop_loss_pct
        self.take_profit_pct = config.take_profit_pct
        self.params = config.params

        # Internal state
        self.positions: Dict[str, PositionInfo] = {}
        self.signals: List[TradingSignal] = []

        logger.info(f"Initialized strategy: {self.name}")

    @abstractmethod
    async def generate_signals(
        self,
        symbols: List[str],
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs
    ) -> List[TradingSignal]:
        """
        Generate trading signals for given symbols.

        This method must be implemented by all strategies.

        Args:
            symbols: List of stock symbols to analyze
            market_data: Optional pre-loaded market data
            **kwargs: Additional strategy-specific parameters

        Returns:
            List of trading signals
        """
        pass

    @abstractmethod
    def should_enter(
        self,
        symbol: str,
        current_price: Decimal,
        agent_analysis: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> tuple[bool, float]:
        """
        Determine if should enter a position.

        Args:
            symbol: Stock symbol
            current_price: Current price
            agent_analysis: Optional MCP agent analysis results
            **kwargs: Additional parameters

        Returns:
            Tuple of (should_enter, confidence)
        """
        pass

    @abstractmethod
    def should_exit(
        self,
        position: PositionInfo,
        current_price: Decimal,
        **kwargs
    ) -> tuple[bool, str]:
        """
        Determine if should exit a position.

        Args:
            position: Current position
            current_price: Current price
            **kwargs: Additional parameters

        Returns:
            Tuple of (should_exit, reason)
        """
        pass

    async def analyze_symbol(
        self,
        symbol: str,
        use_agents: bool = True,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a symbol using MCP agents.

        Args:
            symbol: Stock symbol
            use_agents: Whether to use MCP agents
            **kwargs: Additional parameters

        Returns:
            Agent analysis results or None
        """
        if not use_agents or not self.orchestrator:
            return None

        try:
            # Run all agents
            agent_results = await self.orchestrator.analyze_symbol(symbol)

            # Generate aggregated signal
            aggregated_signal = await self.orchestrator.generate_trading_signal(
                symbol,
                agent_results
            )

            return {
                'agent_results': agent_results,
                'aggregated_signal': aggregated_signal
            }

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None

    def calculate_position_size_for_symbol(
        self,
        symbol: str,
        current_price: Decimal,
        portfolio_value: Decimal,
        confidence: float = 1.0
    ) -> int:
        """
        Calculate position size for a symbol.

        Args:
            symbol: Stock symbol
            current_price: Current price
            portfolio_value: Total portfolio value
            confidence: Signal confidence (0.0 to 1.0)

        Returns:
            Number of shares to buy
        """
        # Base position size from config
        base_position_pct = self.position_size

        # Adjust by confidence
        adjusted_pct = base_position_pct * confidence

        # Calculate shares
        shares = calculate_position_size(
            portfolio_value,
            adjusted_pct,
            current_price
        )

        return shares

    def create_entry_order(
        self,
        symbol: str,
        current_price: Decimal,
        quantity: int,
        confidence: float = 1.0
    ) -> OrderRequest:
        """
        Create an entry order.

        Args:
            symbol: Stock symbol
            current_price: Current price
            quantity: Number of shares
            confidence: Signal confidence

        Returns:
            Order request
        """
        # Calculate stop-loss and take-profit
        stop_loss = calculate_stop_loss_price(
            current_price,
            self.stop_loss_pct,
            is_long=True
        )

        take_profit = calculate_take_profit_price(
            current_price,
            self.take_profit_pct,
            is_long=True
        )

        logger.info(
            f"Creating entry order for {symbol}: "
            f"{quantity} shares @ {current_price}, "
            f"SL={stop_loss}, TP={take_profit}"
        )

        return OrderRequest(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=quantity,
            price=current_price,
            order_type="limit",
            strategy_name=self.name
        )

    def create_exit_order(
        self,
        position: PositionInfo,
        current_price: Decimal,
        reason: str = "strategy_exit"
    ) -> OrderRequest:
        """
        Create an exit order.

        Args:
            position: Position to exit
            current_price: Current price
            reason: Exit reason

        Returns:
            Order request
        """
        logger.info(
            f"Creating exit order for {position.symbol}: "
            f"{position.quantity} shares @ {current_price}, "
            f"reason={reason}"
        )

        return OrderRequest(
            symbol=position.symbol,
            side=OrderSide.SELL,
            quantity=position.quantity,
            price=current_price,
            order_type="limit",
            strategy_name=self.name
        )

    def check_risk_limits(
        self,
        symbol: str,
        new_position_value: Decimal,
        portfolio_value: Decimal
    ) -> tuple[bool, Optional[str]]:
        """
        Check if new position passes risk limits.

        Args:
            symbol: Stock symbol
            new_position_value: Value of new position
            portfolio_value: Total portfolio value

        Returns:
            Tuple of (passes, rejection_reason)
        """
        # Check max positions
        if len(self.positions) >= self.max_positions:
            return False, f"Maximum positions reached ({self.max_positions})"

        # Check position size limit
        position_pct = float(new_position_value / portfolio_value)
        max_position_pct = 0.10  # 10% max per position

        if position_pct > max_position_pct:
            return False, f"Position size {position_pct:.1%} exceeds limit {max_position_pct:.1%}"

        # Check if already have position in this symbol
        if symbol in self.positions:
            return False, f"Already have position in {symbol}"

        return True, None

    def update_position(self, position: PositionInfo):
        """
        Update position in internal tracking.

        Args:
            position: Updated position info
        """
        self.positions[position.symbol] = position

    def remove_position(self, symbol: str):
        """
        Remove position from internal tracking.

        Args:
            symbol: Stock symbol
        """
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"Removed position: {symbol}")

    def get_position(self, symbol: str) -> Optional[PositionInfo]:
        """
        Get position for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Position info or None
        """
        return self.positions.get(symbol)

    def get_all_positions(self) -> List[PositionInfo]:
        """
        Get all positions.

        Returns:
            List of all positions
        """
        return list(self.positions.values())

    def get_symbols_to_monitor(self) -> List[str]:
        """
        Get list of symbols to monitor.

        Returns:
            List of symbols (from config or positions)
        """
        # Start with configured symbols
        symbols = set(self.config.symbols)

        # Add symbols we have positions in
        symbols.update(self.positions.keys())

        return list(symbols)

    async def on_market_open(self, **kwargs):
        """
        Called when market opens.
        Can be overridden by strategies for specific logic.
        """
        logger.info(f"Strategy {self.name}: Market opened")

    async def on_market_close(self, **kwargs):
        """
        Called when market closes.
        Can be overridden by strategies for specific logic.
        """
        logger.info(f"Strategy {self.name}: Market closed")

    async def on_new_bar(
        self,
        symbol: str,
        bar_data: Dict[str, Any],
        **kwargs
    ):
        """
        Called when a new bar (candle) is formed.

        Args:
            symbol: Stock symbol
            bar_data: Bar data (OHLCV)
            **kwargs: Additional parameters
        """
        pass

    def get_strategy_stats(self) -> Dict[str, Any]:
        """
        Get strategy statistics.

        Returns:
            Dictionary with strategy stats
        """
        positions = self.get_all_positions()

        total_value = sum(
            p.quantity * p.current_price
            for p in positions
            if p.current_price
        )

        total_pnl = sum(
            p.unrealized_pnl
            for p in positions
            if p.unrealized_pnl
        )

        return {
            'strategy_name': self.name,
            'enabled': self.enabled,
            'num_positions': len(positions),
            'total_position_value': float(total_value),
            'total_unrealized_pnl': float(total_pnl),
            'max_positions': self.max_positions,
            'position_size_pct': self.position_size,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct
        }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"name={self.name}, "
            f"positions={len(self.positions)}, "
            f"enabled={self.enabled})>"
        )
