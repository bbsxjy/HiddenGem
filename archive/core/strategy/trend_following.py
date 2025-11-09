"""
Trend Following Strategy.

Holds positions for weeks to months to capture long-term trends.
Uses moving averages, ADX, and fundamental strength.

Entry Criteria:
- Strong uptrend: Price > MA20 > MA60
- High ADX (>25) indicating strong trend
- MA crossover (golden cross)
- Positive fundamental metrics
- Low to medium risk

Exit Criteria:
- Trend reversal (death cross)
- ADX weakening (<20)
- Trailing stop loss hit
- Fundamental deterioration
- High risk level
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


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following Strategy.

    Captures long-term trends (weeks to months).
    """

    def __init__(
        self,
        config: StrategyConfig,
        orchestrator: Optional[MCPOrchestrator] = None
    ):
        """Initialize trend following strategy."""
        super().__init__(config, orchestrator)

        # Strategy-specific parameters
        self.min_adx = self.params.get('min_adx', 25)  # Strong trend threshold
        self.weak_adx = self.params.get('weak_adx', 20)  # Weak trend threshold
        self.ma_fast = self.params.get('ma_fast', 20)
        self.ma_slow = self.params.get('ma_slow', 60)
        self.trailing_stop_pct = self.params.get('trailing_stop_pct', 0.15)  # 15% trailing stop
        self.min_fundamental_score = self.params.get('min_fundamental_score', 0.2)
        self.lookback_days = self.params.get('lookback_days', 120)

        logger.info(
            f"Trend Following Strategy initialized: "
            f"ADX>{self.min_adx}, MA{self.ma_fast}/{self.ma_slow}"
        )

    async def generate_signals(
        self,
        symbols: List[str],
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs
    ) -> List[TradingSignal]:
        """
        Generate trend following signals.

        Args:
            symbols: List of symbols
            market_data: Optional market data
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
                logger.error(f"Error generating trend signal for {symbol}: {e}")

        logger.info(f"Generated {len(signals)} trend following signals from {len(symbols)} symbols")
        return signals

    async def _analyze_symbol_for_entry(
        self,
        symbol: str,
        market_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Optional[TradingSignal]:
        """Analyze symbol for trend following entry."""
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

        if df.empty or len(df) < 60:
            return None

        # Calculate indicators
        df = TechnicalIndicators.calculate_all_indicators(df)
        latest = df.iloc[-1]
        current_price = Decimal(str(latest['close']))

        # Get agent analysis
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
            agent_name="TrendFollowingStrategy",
            strategy_name=self.name,
            entry_price=current_price,
            target_price=None,  # No fixed target for trend following
            stop_loss_price=current_price * Decimal(str(1 - self.trailing_stop_pct)),
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
        Determine if should enter a trend following position.

        Args:
            symbol: Stock symbol
            current_price: Current price
            agent_analysis: Agent analysis
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

        # 1. Trend strength (40% weight)
        max_score += 40

        # ADX - trend strength
        adx = latest.get('adx')
        if pd.notna(adx):
            if adx > self.min_adx:
                entry_score += 20  # Strong trend
            elif adx > self.weak_adx:
                entry_score += 10  # Moderate trend
            else:
                entry_score -= 10  # Weak trend, penalty

        # Moving average alignment
        price = latest.get('close')
        ma_20 = latest.get('ma_20')
        ma_60 = latest.get('ma_60')

        if all(pd.notna([price, ma_20, ma_60])):
            # Ideal: Price > MA20 > MA60 (uptrend)
            if price > ma_20 > ma_60:
                entry_score += 20
            # Also good: Price > MA20 and MA20 rising
            elif price > ma_20:
                if len(df) > 5:
                    ma_20_prev = df.iloc[-6].get('ma_20', 0)
                    if ma_20 > ma_20_prev:
                        entry_score += 12

        # 2. Fundamental quality (30% weight)
        max_score += 30

        if agent_analysis and 'agent_results' in agent_analysis:
            fundamental_result = agent_analysis['agent_results'].get('FundamentalAgent')

            if fundamental_result and not fundamental_result.is_error:
                fund_score = fundamental_result.score or 0.0

                if fund_score >= self.min_fundamental_score:
                    # Scale fundamental score to points
                    entry_score += 30 * (fund_score + 1) / 2  # Convert -1..1 to 0..1
                else:
                    # Penalty for poor fundamentals
                    entry_score -= 15

        # 3. Agent consensus (30% weight)
        max_score += 30

        if agent_analysis and agent_analysis.get('aggregated_signal'):
            agg_signal = agent_analysis['aggregated_signal']

            if agg_signal.direction == SignalDirection.LONG:
                entry_score += 30 * agg_signal.confidence
            elif agg_signal.direction == SignalDirection.SHORT:
                entry_score -= 20

        # Calculate confidence
        confidence = min(entry_score / max_score, 1.0) if max_score > 0 else 0.0

        # Minimum threshold for trend following (higher than swing trading)
        should_enter = confidence >= 0.65

        logger.debug(
            f"{symbol}: Trend entry score={entry_score:.1f}/{max_score}, "
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
        Determine if should exit a trend following position.

        Args:
            position: Current position
            current_price: Current price
            **kwargs: Additional data

        Returns:
            Tuple of (should_exit, reason)
        """
        # 1. Trailing stop loss
        # Update trailing stop if price has moved up significantly
        if position.unrealized_pnl_pct and position.unrealized_pnl_pct > 0.10:
            # If up >10%, use trailing stop from highest price
            # (This would require tracking highest price, simplified here)
            trailing_stop = current_price * Decimal(str(1 - self.trailing_stop_pct))

            if current_price <= trailing_stop:
                return True, "trailing_stop"

        # 2. Regular stop loss
        if position.stop_loss_price and current_price <= position.stop_loss_price:
            return True, "stop_loss"

        # 3. Trend reversal detection
        df = kwargs.get('df')
        latest = kwargs.get('latest')

        if df is not None and latest is not None:
            # ADX weakening significantly
            adx = latest.get('adx')
            if pd.notna(adx) and adx < self.weak_adx:
                return True, "trend_weakened"

            # Death cross (MA20 crosses below MA60)
            ma_20 = latest.get('ma_20')
            ma_60 = latest.get('ma_60')

            if all(pd.notna([ma_20, ma_60])) and len(df) > 1:
                prev_ma_20 = df.iloc[-2].get('ma_20', 0)
                prev_ma_60 = df.iloc[-2].get('ma_60', 0)

                # Death cross just happened
                if ma_20 < ma_60 and prev_ma_20 >= prev_ma_60:
                    return True, "death_cross"

                # Already in death cross for a while
                if ma_20 < ma_60:
                    price = latest.get('close')
                    if pd.notna(price) and price < ma_20:
                        return True, "bearish_alignment"

        # 4. Fundamental deterioration
        if kwargs.get('fundamental_score') is not None:
            if kwargs['fundamental_score'] < -0.3:  # Significantly negative
                return True, "fundamental_deterioration"

        # 5. High risk
        if kwargs.get('risk_level') == 'high':
            return True, "elevated_risk"

        return False, ""

    def _create_entry_reasoning(
        self,
        latest: pd.Series,
        agent_analysis: Optional[Dict[str, Any]]
    ) -> str:
        """Create entry reasoning."""
        reasons = []

        # Trend information
        adx = latest.get('adx')
        if pd.notna(adx):
            if adx > self.min_adx:
                reasons.append(f"强趋势(ADX={adx:.1f})")
            else:
                reasons.append(f"趋势形成中(ADX={adx:.1f})")

        # MA alignment
        price = latest.get('close')
        ma_20 = latest.get('ma_20')
        ma_60 = latest.get('ma_60')

        if all(pd.notna([price, ma_20, ma_60])):
            if price > ma_20 > ma_60:
                reasons.append("多头排列")

        # Agent feedback
        if agent_analysis and agent_analysis.get('aggregated_signal'):
            agg = agent_analysis['aggregated_signal']
            if agg.direction == SignalDirection.LONG:
                reasons.append(f"Agent看多(置信度{agg.confidence:.1%})")

        # Fundamental
        if agent_analysis and 'agent_results' in agent_analysis:
            fund_result = agent_analysis['agent_results'].get('FundamentalAgent')
            if fund_result and not fund_result.is_error:
                if fund_result.score and fund_result.score > 0.3:
                    reasons.append("基本面良好")

        reasons.append("趋势跟踪策略(长期持有)")

        return "；".join(reasons) if reasons else "符合趋势跟踪入场条件"

    async def on_new_bar(
        self,
        symbol: str,
        bar_data: Dict[str, Any],
        **kwargs
    ):
        """Check for trend exit signals on new bar."""
        position = self.get_position(symbol)
        if not position:
            return

        current_price = Decimal(str(bar_data.get('close', 0)))
        if current_price <= 0:
            return

        df = kwargs.get('df')
        latest = kwargs.get('latest')

        should_exit, reason = self.should_exit(
            position,
            current_price,
            df=df,
            latest=latest
        )

        if should_exit:
            holding_days = (datetime.utcnow() - position.entry_date).days
            pnl_pct = position.unrealized_pnl_pct or 0.0

            logger.info(
                f"Trend following exit signal: {symbol}, "
                f"reason={reason}, "
                f"holding_days={holding_days}, "
                f"pnl={pnl_pct:.2%}"
            )

            exit_order = self.create_exit_order(position, current_price, reason)
