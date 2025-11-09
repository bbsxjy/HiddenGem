"""
Swing Trading Strategy.

Holds positions for 7-14 days to capture medium-term price swings.
Uses technical indicators, sentiment, and fundamental screening.

Entry Criteria:
- RSI oversold (<30) with reversal signs
- MACD bullish crossover
- Price near support level
- Positive fundamental score (PE, PB reasonable)
- Low to medium risk level

Exit Criteria:
- Target profit reached (15% default)
- Stop loss hit (8% default)
- RSI overbought (>70)
- Holding period exceeded (14 days)
- Risk level becomes high
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any

import pandas as pd
from loguru import logger

from core.strategy.base_strategy import BaseStrategy
from core.data.models import TradingSignal, PositionInfo, SignalDirection, StrategyConfig
from core.data.sources import data_source
from core.utils.indicators import TechnicalIndicators
from core.mcp_agents.orchestrator import MCPOrchestrator


class SwingTradingStrategy(BaseStrategy):
    """
    Swing Trading Strategy.

    Captures short to medium-term price movements (7-14 days).
    """

    def __init__(
        self,
        config: StrategyConfig,
        orchestrator: Optional[MCPOrchestrator] = None
    ):
        """Initialize swing trading strategy."""
        super().__init__(config, orchestrator)

        # Strategy-specific parameters
        self.min_holding_days = self.params.get('min_holding_days', 7)
        self.max_holding_days = self.params.get('max_holding_days', 14)
        self.rsi_oversold = self.params.get('rsi_oversold', 30)
        self.rsi_overbought = self.params.get('rsi_overbought', 70)
        self.min_agent_confidence = self.params.get('min_agent_confidence', 0.6)
        self.lookback_days = self.params.get('lookback_days', 60)

        logger.info(
            f"Swing Trading Strategy initialized: "
            f"holding period {self.min_holding_days}-{self.max_holding_days} days"
        )

    async def generate_signals(
        self,
        symbols: List[str],
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs
    ) -> List[TradingSignal]:
        """
        Generate swing trading signals for symbols.

        Args:
            symbols: List of symbols to analyze
            market_data: Optional pre-loaded market data
            **kwargs: Additional parameters

        Returns:
            List of trading signals
        """
        signals = []

        for symbol in symbols:
            try:
                signal = await self._analyze_symbol_for_entry(symbol, market_data)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error generating signal for {symbol}: {e}")

        logger.info(f"Generated {len(signals)} swing trading signals from {len(symbols)} symbols")
        return signals

    async def _analyze_symbol_for_entry(
        self,
        symbol: str,
        market_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Optional[TradingSignal]:
        """
        Analyze symbol for entry opportunity.

        Args:
            symbol: Stock symbol
            market_data: Optional market data

        Returns:
            Trading signal or None
        """
        # Get market data
        if market_data and symbol in market_data:
            df = market_data[symbol]
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days + 30)

            df = data_source.get_daily_bars(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

        if df.empty or len(df) < 30:
            logger.debug(f"Insufficient data for {symbol}")
            return None

        # Calculate technical indicators
        df = TechnicalIndicators.calculate_all_indicators(df)
        latest = df.iloc[-1]
        current_price = Decimal(str(latest['close']))

        # Get MCP agent analysis
        agent_analysis = await self.analyze_symbol(symbol, use_agents=True)

        # Check entry criteria
        should_enter, confidence = self.should_enter(
            symbol,
            current_price,
            agent_analysis,
            df=df,
            latest=latest
        )

        if not should_enter:
            return None

        # Create signal
        signal = TradingSignal(
            symbol=symbol,
            direction=SignalDirection.LONG,
            strength=confidence,
            agent_name="SwingTradingStrategy",
            strategy_name=self.name,
            entry_price=current_price,
            target_price=current_price * Decimal(str(1 + self.take_profit_pct)),
            stop_loss_price=current_price * Decimal(str(1 - self.stop_loss_pct)),
            suggested_position_size=self.position_size,
            reasoning=self._create_entry_reasoning(latest, agent_analysis)
        )

        return signal

    def should_enter(
        self,
        symbol: str,
        current_price: Decimal,
        agent_analysis: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> tuple[bool, float]:
        """
        Determine if should enter a swing trade.

        Args:
            symbol: Stock symbol
            current_price: Current price
            agent_analysis: MCP agent analysis
            **kwargs: Must contain 'df' and 'latest'

        Returns:
            Tuple of (should_enter, confidence)
        """
        df = kwargs.get('df')
        latest = kwargs.get('latest')

        if df is None or latest is None:
            return False, 0.0

        entry_score = 0.0
        max_score = 0.0

        # 1. Technical indicators (40% weight)
        max_score += 40

        # RSI check - looking for oversold with reversal
        rsi = latest.get('rsi')
        if pd.notna(rsi):
            if rsi < self.rsi_oversold:
                entry_score += 15  # Strong buy signal
            elif rsi < 40:
                entry_score += 8   # Moderate buy signal
            elif rsi > 60:
                entry_score -= 10  # Penalty for already high

        # MACD check - looking for bullish crossover
        macd_hist = latest.get('macd_hist')
        if pd.notna(macd_hist) and len(df) > 1:
            prev_hist = df.iloc[-2].get('macd_hist', 0)
            if macd_hist > 0 and prev_hist <= 0:
                entry_score += 15  # Bullish crossover
            elif macd_hist > 0:
                entry_score += 5   # Already bullish

        # Moving averages
        price = latest.get('close')
        ma_20 = latest.get('ma_20')
        ma_60 = latest.get('ma_60')

        if all(pd.notna([price, ma_20, ma_60])):
            # Price above MA20 but below MA60 (pullback)
            if ma_20 < price < ma_60:
                entry_score += 10
            # Price bouncing off MA20 support
            elif abs(price - ma_20) / ma_20 < 0.02:  # Within 2%
                entry_score += 8

        # 2. Agent analysis (30% weight)
        max_score += 30

        if agent_analysis and agent_analysis.get('aggregated_signal'):
            agg_signal = agent_analysis['aggregated_signal']

            if agg_signal.direction == SignalDirection.LONG:
                # Scale confidence to score
                entry_score += 30 * agg_signal.confidence
            elif agg_signal.direction == SignalDirection.SHORT:
                # Penalty for conflicting signal
                entry_score -= 20

        # 3. Risk check (30% weight)
        max_score += 30

        if agent_analysis and 'agent_results' in agent_analysis:
            risk_result = agent_analysis['agent_results'].get('RiskManagerAgent')

            if risk_result and not risk_result.is_error:
                risk_score = risk_result.score or 0.0

                # Risk score is negative (0 = low risk, -1 = high risk)
                # Convert to positive score
                risk_contribution = (1 + risk_score) * 30  # 0 to 30
                entry_score += risk_contribution

        # Calculate confidence
        confidence = min(entry_score / max_score, 1.0) if max_score > 0 else 0.0

        # Minimum confidence threshold
        should_enter = confidence >= self.min_agent_confidence

        logger.debug(
            f"{symbol}: Entry score={entry_score:.1f}/{max_score}, "
            f"confidence={confidence:.2f}, enter={should_enter}"
        )

        return should_enter, confidence

    def should_exit(
        self,
        position: PositionInfo,
        current_price: Decimal,
        **kwargs
    ) -> tuple[bool, str]:
        """
        Determine if should exit a swing trade.

        Args:
            position: Current position
            current_price: Current price
            **kwargs: Additional data (df, latest)

        Returns:
            Tuple of (should_exit, reason)
        """
        # 1. Stop-loss check
        if position.stop_loss_price and current_price <= position.stop_loss_price:
            return True, "stop_loss"

        # 2. Take-profit check
        if position.take_profit_price and current_price >= position.take_profit_price:
            return True, "take_profit"

        # 3. Holding period check
        holding_days = (datetime.utcnow() - position.entry_date).days

        if holding_days >= self.max_holding_days:
            return True, f"max_holding_period_{holding_days}days"

        # 4. Technical exit signals
        df = kwargs.get('df')
        latest = kwargs.get('latest')

        if df is not None and latest is not None:
            # RSI overbought
            rsi = latest.get('rsi')
            if pd.notna(rsi) and rsi > self.rsi_overbought:
                # Check if we have profit
                pnl_pct = position.unrealized_pnl_pct or 0.0
                if pnl_pct > 0.05:  # At least 5% profit
                    return True, "rsi_overbought_with_profit"

            # MACD bearish crossover
            macd_hist = latest.get('macd_hist')
            if pd.notna(macd_hist) and len(df) > 1:
                prev_hist = df.iloc[-2].get('macd_hist', 0)
                if macd_hist < 0 and prev_hist >= 0:
                    # Bearish crossover, exit if profitable
                    pnl_pct = position.unrealized_pnl_pct or 0.0
                    if pnl_pct > 0:
                        return True, "macd_bearish_crossover"

        # 5. Risk-based exit (if available)
        if kwargs.get('risk_level') == 'high':
            return True, "elevated_risk"

        # Don't exit
        return False, ""

    def _create_entry_reasoning(
        self,
        latest: pd.Series,
        agent_analysis: Optional[Dict[str, Any]]
    ) -> str:
        """Create human-readable entry reasoning."""
        reasons = []

        # Technical reasons
        rsi = latest.get('rsi')
        if pd.notna(rsi):
            if rsi < 30:
                reasons.append(f"RSI超卖({rsi:.1f})")
            elif rsi < 40:
                reasons.append(f"RSI偏低({rsi:.1f})")

        macd_hist = latest.get('macd_hist')
        if pd.notna(macd_hist) and macd_hist > 0:
            reasons.append("MACD多头")

        # Agent reasons
        if agent_analysis and agent_analysis.get('aggregated_signal'):
            agg = agent_analysis['aggregated_signal']
            if agg.direction == SignalDirection.LONG:
                reasons.append(f"多Agent看多(置信度{agg.confidence:.1%})")

        # Strategy info
        reasons.append(f"摆动交易策略({self.min_holding_days}-{self.max_holding_days}天)")

        return "；".join(reasons) if reasons else "符合摆动交易入场条件"

    async def on_new_bar(
        self,
        symbol: str,
        bar_data: Dict[str, Any],
        **kwargs
    ):
        """
        Called when new bar formed.

        Check if we should exit existing positions.
        """
        position = self.get_position(symbol)
        if not position:
            return

        current_price = Decimal(str(bar_data.get('close', 0)))
        if current_price <= 0:
            return

        # Get recent data for exit decision
        df = kwargs.get('df')
        latest = kwargs.get('latest')

        should_exit, reason = self.should_exit(
            position,
            current_price,
            df=df,
            latest=latest
        )

        if should_exit:
            logger.info(
                f"Swing trade exit signal: {symbol}, "
                f"reason={reason}, "
                f"holding_days={(datetime.utcnow() - position.entry_date).days}"
            )

            # Create exit order
            exit_order = self.create_exit_order(position, current_price, reason)

            # Note: Actual order submission would be handled by execution system
            # Here we just log and potentially emit an event
