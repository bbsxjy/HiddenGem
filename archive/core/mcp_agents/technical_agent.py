"""
Technical Analysis Agent.
Analyzes technical indicators (RSI, MACD, MA, etc.) to generate trading signals.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import pandas as pd
from loguru import logger

from core.mcp_agents.base_agent import BaseAgent
from core.data.models import AgentAnalysisResult, SignalDirection
from core.data.sources import data_source
from core.utils.indicators import TechnicalIndicators, SignalGenerator
from config.agents_config import agents_config


class TechnicalAnalysisAgent(BaseAgent):
    """
    Technical Analysis Agent.

    Analyzes technical indicators to generate trading signals:
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence Divergence)
    - Moving Averages (MA 5, 10, 20, 60)
    - Bollinger Bands
    - KDJ
    - Support/Resistance levels
    """

    def __init__(self, redis_client=None):
        """Initialize Technical Analysis Agent."""
        config = agents_config.TECHNICAL_AGENT
        super().__init__(config, redis_client)

        self.indicators_config = config.params.get("indicators", [])
        self.lookback_days = config.params.get("lookback_days", 60)
        self.rsi_oversold = config.params.get("rsi_oversold", 30)
        self.rsi_overbought = config.params.get("rsi_overbought", 70)

    async def analyze(self, symbol: Optional[str] = None, **kwargs) -> AgentAnalysisResult:
        """
        Perform technical analysis on a symbol.

        Args:
            symbol: Stock symbol to analyze
            **kwargs: Additional parameters

        Returns:
            AgentAnalysisResult with technical analysis
        """
        start_time = time.time()

        if not symbol:
            return self._create_error_result(None, "Symbol is required for technical analysis")

        try:
            # Check cache first
            cache_key = self._create_cache_key(symbol)
            cached_result = await self.get_cached_result(cache_key)
            if cached_result:
                logger.debug(f"Returning cached technical analysis for {symbol}")
                return AgentAnalysisResult(**cached_result)

            # Fetch historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days + 30)  # Extra buffer

            logger.info(f"Fetching {self.lookback_days} days of data for {symbol}")

            df = data_source.get_daily_bars(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            if df.empty or len(df) < 20:
                return self._create_error_result(
                    symbol,
                    f"Insufficient data for {symbol}: {len(df)} bars"
                )

            # Calculate all technical indicators
            df = TechnicalIndicators.calculate_all_indicators(df)

            # Get latest values
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else latest

            # Perform technical analysis
            analysis_results = self._analyze_indicators(df, latest, previous)

            # Generate signal
            signal_direction, confidence = self._generate_signal(analysis_results)

            # Create reasoning
            reasoning = self._create_reasoning(analysis_results, signal_direction)

            # Calculate execution time
            execution_time = int((time.time() - start_time) * 1000)

            # Create result
            result = self._create_analysis_result(
                symbol=symbol,
                score=analysis_results.get("overall_score"),
                direction=signal_direction,
                confidence=confidence,
                analysis=analysis_results,
                reasoning=reasoning,
                execution_time_ms=execution_time
            )

            # Cache result
            await self.set_cached_result(cache_key, result.model_dump())

            return result

        except Exception as e:
            logger.exception(f"Error in technical analysis for {symbol}: {e}")
            return self._create_error_result(symbol, str(e))

    def _analyze_indicators(
        self,
        df: pd.DataFrame,
        latest: pd.Series,
        previous: pd.Series
    ) -> Dict[str, Any]:
        """
        Analyze all technical indicators.

        Args:
            df: Full dataframe with indicators
            latest: Latest bar
            previous: Previous bar

        Returns:
            Dictionary with analysis results
        """
        analysis = {}

        # RSI Analysis
        rsi = latest.get('rsi')
        if pd.notna(rsi):
            analysis['rsi'] = {
                'value': float(rsi),
                'signal': SignalGenerator.rsi_signal(rsi, self.rsi_oversold, self.rsi_overbought),
                'oversold': rsi < self.rsi_oversold,
                'overbought': rsi > self.rsi_overbought,
                'neutral': self.rsi_oversold <= rsi <= self.rsi_overbought
            }

        # MACD Analysis
        macd = latest.get('macd')
        macd_signal = latest.get('macd_signal')
        macd_hist = latest.get('macd_hist')

        if all(pd.notna([macd, macd_signal, macd_hist])):
            prev_hist = previous.get('macd_hist', 0)

            analysis['macd'] = {
                'macd': float(macd),
                'signal': float(macd_signal),
                'histogram': float(macd_hist),
                'signal_type': SignalGenerator.macd_signal(macd, macd_signal, macd_hist),
                'bullish_crossover': macd_hist > 0 and prev_hist <= 0,
                'bearish_crossover': macd_hist < 0 and prev_hist >= 0
            }

        # Moving Average Analysis
        price = latest.get('close')
        ma_5 = latest.get('ma_5')
        ma_10 = latest.get('ma_10')
        ma_20 = latest.get('ma_20')
        ma_60 = latest.get('ma_60')

        if all(pd.notna([price, ma_5, ma_10, ma_20, ma_60])):
            analysis['moving_averages'] = {
                'ma_5': float(ma_5),
                'ma_10': float(ma_10),
                'ma_20': float(ma_20),
                'ma_60': float(ma_60),
                'price': float(price),
                'signal': SignalGenerator.ma_crossover_signal(price, ma_5, ma_60),
                'golden_cross': ma_5 > ma_60 and previous.get('ma_5', 0) <= previous.get('ma_60', 0),
                'death_cross': ma_5 < ma_60 and previous.get('ma_5', 0) >= previous.get('ma_60', 0),
                'price_above_ma20': price > ma_20,
                'ma_alignment_bullish': ma_5 > ma_10 > ma_20 > ma_60,
                'ma_alignment_bearish': ma_5 < ma_10 < ma_20 < ma_60
            }

        # Bollinger Bands Analysis
        bb_upper = latest.get('bb_upper')
        bb_middle = latest.get('bb_middle')
        bb_lower = latest.get('bb_lower')

        if all(pd.notna([price, bb_upper, bb_middle, bb_lower])):
            bb_width = (bb_upper - bb_lower) / bb_middle
            bb_position = (price - bb_lower) / (bb_upper - bb_lower)

            analysis['bollinger_bands'] = {
                'upper': float(bb_upper),
                'middle': float(bb_middle),
                'lower': float(bb_lower),
                'price': float(price),
                'signal': SignalGenerator.bollinger_signal(price, bb_upper, bb_lower),
                'width': float(bb_width),
                'position': float(bb_position),  # 0 = lower band, 1 = upper band
                'squeeze': bb_width < 0.1,  # Narrow bands indicate low volatility
                'near_upper': bb_position > 0.9,
                'near_lower': bb_position < 0.1
            }

        # KDJ Analysis
        kdj_k = latest.get('kdj_k')
        kdj_d = latest.get('kdj_d')
        kdj_j = latest.get('kdj_j')

        if all(pd.notna([kdj_k, kdj_d, kdj_j])):
            analysis['kdj'] = {
                'k': float(kdj_k),
                'd': float(kdj_d),
                'j': float(kdj_j),
                'signal': SignalGenerator.kdj_signal(kdj_k, kdj_d, kdj_j),
                'oversold': kdj_k < 20 and kdj_d < 20,
                'overbought': kdj_k > 80 and kdj_d > 80,
                'k_cross_d_up': kdj_k > kdj_d and previous.get('kdj_k', 0) <= previous.get('kdj_d', 0),
                'k_cross_d_down': kdj_k < kdj_d and previous.get('kdj_k', 0) >= previous.get('kdj_d', 0)
            }

        # Trend Analysis using ADX
        adx = latest.get('adx')
        if pd.notna(adx):
            analysis['trend'] = {
                'adx': float(adx),
                'strong_trend': adx > 25,
                'weak_trend': adx < 20,
                'trending': adx > 25,
                'ranging': adx < 20
            }

        # Volatility Analysis using ATR
        atr = latest.get('atr')
        if pd.notna(atr) and pd.notna(price):
            atr_pct = (atr / price) * 100
            analysis['volatility'] = {
                'atr': float(atr),
                'atr_percentage': float(atr_pct),
                'high_volatility': atr_pct > 3.0,
                'low_volatility': atr_pct < 1.0
            }

        # Support/Resistance Analysis
        sr_levels = TechnicalIndicators.detect_support_resistance(df['close'])
        analysis['support_resistance'] = sr_levels

        # Overall score calculation
        analysis['overall_score'] = self._calculate_overall_score(analysis)

        return analysis

    def _calculate_overall_score(self, analysis: Dict[str, Any]) -> float:
        """
        Calculate overall technical score (-1 to 1).

        Args:
            analysis: Analysis results

        Returns:
            Overall score
        """
        scores = []

        # RSI contribution
        if 'rsi' in analysis:
            rsi_signal = analysis['rsi']['signal']
            if rsi_signal == 'long':
                scores.append(0.8)
            elif rsi_signal == 'short':
                scores.append(-0.8)
            else:
                scores.append(0.0)

        # MACD contribution
        if 'macd' in analysis:
            macd_signal = analysis['macd']['signal_type']
            if macd_signal == 'long':
                scores.append(0.7)
            elif macd_signal == 'short':
                scores.append(-0.7)
            else:
                scores.append(0.0)

        # MA contribution
        if 'moving_averages' in analysis:
            ma = analysis['moving_averages']
            if ma.get('ma_alignment_bullish'):
                scores.append(1.0)
            elif ma.get('ma_alignment_bearish'):
                scores.append(-1.0)
            elif ma.get('golden_cross'):
                scores.append(0.8)
            elif ma.get('death_cross'):
                scores.append(-0.8)

        # KDJ contribution
        if 'kdj' in analysis:
            kdj_signal = analysis['kdj']['signal']
            if kdj_signal == 'long':
                scores.append(0.6)
            elif kdj_signal == 'short':
                scores.append(-0.6)

        # Calculate average
        if scores:
            return sum(scores) / len(scores)
        else:
            return 0.0

    def _generate_signal(
        self,
        analysis: Dict[str, Any]
    ) -> tuple[SignalDirection, float]:
        """
        Generate trading signal from analysis.

        Args:
            analysis: Analysis results

        Returns:
            Tuple of (signal_direction, confidence)
        """
        overall_score = analysis.get('overall_score', 0.0)

        # Determine direction
        if overall_score > 0.3:
            direction = SignalDirection.LONG
        elif overall_score < -0.3:
            direction = SignalDirection.SHORT
        else:
            direction = SignalDirection.HOLD

        # Calculate confidence based on signal consistency and strength
        # Confidence should reflect how reliable the signal is, not just the score magnitude

        # Count indicators and their agreement
        indicator_signals = []

        if 'rsi' in analysis and analysis['rsi'].get('signal') != 'neutral':
            indicator_signals.append(1 if analysis['rsi']['signal'] == 'long' else -1)

        if 'macd' in analysis and analysis['macd'].get('signal_type') != 'hold':
            indicator_signals.append(1 if analysis['macd']['signal_type'] == 'long' else -1)

        if 'moving_averages' in analysis:
            ma = analysis['moving_averages']
            if ma.get('ma_alignment_bullish'):
                indicator_signals.append(1)
            elif ma.get('ma_alignment_bearish'):
                indicator_signals.append(-1)
            elif ma.get('golden_cross'):
                indicator_signals.append(1)
            elif ma.get('death_cross'):
                indicator_signals.append(-1)

        if 'kdj' in analysis and analysis['kdj'].get('signal') != 'hold':
            indicator_signals.append(1 if analysis['kdj']['signal'] == 'long' else -1)

        # Calculate agreement
        if indicator_signals:
            # Count how many indicators agree with the overall direction
            direction_value = 1 if direction == SignalDirection.LONG else (-1 if direction == SignalDirection.SHORT else 0)

            if direction == SignalDirection.HOLD:
                # For HOLD, confidence is based on how neutral indicators are
                confidence = max(0.3, 0.5 - abs(overall_score) * 0.3)
            else:
                # Count agreeing indicators
                agreeing = sum(1 for sig in indicator_signals if sig == direction_value)
                total = len(indicator_signals)
                agreement_ratio = agreeing / total if total > 0 else 0

                # Base confidence on agreement ratio and score magnitude
                # agreement_ratio: 0.5 (50% agree) → 0.5 confidence
                # agreement_ratio: 0.75 (75% agree) → 0.7 confidence
                # agreement_ratio: 1.0 (100% agree) → 0.85+ confidence
                base_confidence = 0.4 + (agreement_ratio * 0.5)  # 0.4-0.9 range

                # Adjust by score magnitude (how strong the signal is)
                score_factor = min(abs(overall_score), 1.0)
                confidence = base_confidence + (score_factor * 0.1)  # Add up to 0.1

                # Ensure minimum confidence
                confidence = max(confidence, 0.4)
        else:
            # No clear indicators
            confidence = 0.3

        # Adjust confidence based on trend strength
        if 'trend' in analysis:
            if analysis['trend'].get('strong_trend'):
                # Strong trend increases confidence
                confidence = min(confidence * 1.15, 1.0)
            elif analysis['trend'].get('weak_trend'):
                # Weak trend slightly decreases confidence but not too much
                confidence = max(confidence * 0.92, 0.35)

        # Cap confidence between 0.3 and 1.0
        confidence = min(max(confidence, 0.3), 1.0)

        return direction, confidence

    def _create_reasoning(
        self,
        analysis: Dict[str, Any],
        direction: SignalDirection
    ) -> str:
        """
        Create human-readable reasoning.

        Args:
            analysis: Analysis results
            direction: Signal direction

        Returns:
            Reasoning text
        """
        reasons = []

        # RSI reasoning
        if 'rsi' in analysis:
            rsi = analysis['rsi']
            if rsi.get('oversold'):
                reasons.append(f"RSI处于超卖区域({rsi['value']:.1f})")
            elif rsi.get('overbought'):
                reasons.append(f"RSI处于超买区域({rsi['value']:.1f})")

        # MACD reasoning
        if 'macd' in analysis:
            macd = analysis['macd']
            if macd.get('bullish_crossover'):
                reasons.append("MACD金叉信号")
            elif macd.get('bearish_crossover'):
                reasons.append("MACD死叉信号")

        # MA reasoning
        if 'moving_averages' in analysis:
            ma = analysis['moving_averages']
            if ma.get('golden_cross'):
                reasons.append("均线金叉")
            elif ma.get('death_cross'):
                reasons.append("均线死叉")
            elif ma.get('ma_alignment_bullish'):
                reasons.append("多头排列")
            elif ma.get('ma_alignment_bearish'):
                reasons.append("空头排列")

        # KDJ reasoning
        if 'kdj' in analysis:
            kdj = analysis['kdj']
            if kdj.get('oversold') and kdj.get('k_cross_d_up'):
                reasons.append("KDJ超卖区金叉")
            elif kdj.get('overbought') and kdj.get('k_cross_d_down'):
                reasons.append("KDJ超买区死叉")

        # Trend reasoning
        if 'trend' in analysis:
            trend = analysis['trend']
            if trend.get('strong_trend'):
                reasons.append(f"趋势强劲(ADX={trend['adx']:.1f})")
            elif trend.get('weak_trend'):
                reasons.append(f"趋势较弱(ADX={trend['adx']:.1f})")

        if not reasons:
            reasons.append(f"技术指标中性，建议{direction.value}")

        return "；".join(reasons)
