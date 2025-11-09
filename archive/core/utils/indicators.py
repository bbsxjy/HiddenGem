"""
Technical indicators calculation utilities.
Wraps TA-Lib and implements custom A-share indicators.
"""

from typing import Dict, Optional, Tuple
from decimal import Decimal

import numpy as np
import pandas as pd
import talib
from loguru import logger


class TechnicalIndicators:
    """
    Technical indicators calculator.

    Provides methods for calculating various technical indicators
    used in A-share trading strategies.
    """

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        Args:
            prices: Price series (usually close prices)
            period: RSI period (default 14)

        Returns:
            RSI values
        """
        try:
            rsi = talib.RSI(prices.values, timeperiod=period)
            return pd.Series(rsi, index=prices.index)
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return pd.Series(index=prices.index)

    @staticmethod
    def calculate_macd(
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            prices: Price series
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period

        Returns:
            Tuple of (macd, signal, histogram)
        """
        try:
            macd, signal, hist = talib.MACD(
                prices.values,
                fastperiod=fast_period,
                slowperiod=slow_period,
                signalperiod=signal_period
            )
            return (
                pd.Series(macd, index=prices.index),
                pd.Series(signal, index=prices.index),
                pd.Series(hist, index=prices.index)
            )
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            empty = pd.Series(index=prices.index)
            return empty, empty, empty

    @staticmethod
    def calculate_moving_averages(
        prices: pd.Series,
        periods: list = [5, 10, 20, 60]
    ) -> Dict[str, pd.Series]:
        """
        Calculate multiple moving averages.

        Args:
            prices: Price series
            periods: List of MA periods

        Returns:
            Dictionary of MA period to MA series
        """
        try:
            mas = {}
            for period in periods:
                ma = talib.SMA(prices.values, timeperiod=period)
                mas[f"ma_{period}"] = pd.Series(ma, index=prices.index)
            return mas
        except Exception as e:
            logger.error(f"Error calculating moving averages: {e}")
            return {f"ma_{p}": pd.Series(index=prices.index) for p in periods}

    @staticmethod
    def calculate_bollinger_bands(
        prices: pd.Series,
        period: int = 20,
        std_dev: int = 2
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands.

        Args:
            prices: Price series
            period: MA period
            std_dev: Number of standard deviations

        Returns:
            Tuple of (upper, middle, lower)
        """
        try:
            upper, middle, lower = talib.BBANDS(
                prices.values,
                timeperiod=period,
                nbdevup=std_dev,
                nbdevdn=std_dev,
                matype=0
            )
            return (
                pd.Series(upper, index=prices.index),
                pd.Series(middle, index=prices.index),
                pd.Series(lower, index=prices.index)
            )
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            empty = pd.Series(index=prices.index)
            return empty, empty, empty

    @staticmethod
    def calculate_kdj(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate KDJ indicator (popular in Chinese markets).

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            n: Period for RSV calculation
            m1: Period for K smoothing
            m2: Period for D smoothing

        Returns:
            Tuple of (K, D, J)
        """
        try:
            # Calculate RSV (Raw Stochastic Value)
            low_n = low.rolling(window=n, min_periods=1).min()
            high_n = high.rolling(window=n, min_periods=1).max()

            rsv = (close - low_n) / (high_n - low_n) * 100
            rsv = rsv.fillna(50)  # Fill NaN with neutral value

            # Calculate K and D
            k = rsv.ewm(com=m1 - 1, adjust=False).mean()
            d = k.ewm(com=m2 - 1, adjust=False).mean()

            # Calculate J
            j = 3 * k - 2 * d

            return k, d, j

        except Exception as e:
            logger.error(f"Error calculating KDJ: {e}")
            empty = pd.Series(index=close.index)
            return empty, empty, empty

    @staticmethod
    def calculate_turnover_rate(
        volume: pd.Series,
        total_shares: float
    ) -> pd.Series:
        """
        Calculate turnover rate (换手率).

        Args:
            volume: Trading volume
            total_shares: Total outstanding shares

        Returns:
            Turnover rate percentage
        """
        try:
            if total_shares <= 0:
                logger.warning("Invalid total_shares for turnover rate")
                return pd.Series(index=volume.index)

            turnover_rate = (volume / total_shares) * 100
            return turnover_rate

        except Exception as e:
            logger.error(f"Error calculating turnover rate: {e}")
            return pd.Series(index=volume.index)

    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Average True Range (ATR) for volatility.

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period

        Returns:
            ATR values
        """
        try:
            atr = talib.ATR(
                high.values,
                low.values,
                close.values,
                timeperiod=period
            )
            return pd.Series(atr, index=close.index)
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return pd.Series(index=close.index)

    @staticmethod
    def calculate_adx(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Average Directional Index (ADX) for trend strength.

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ADX period

        Returns:
            ADX values
        """
        try:
            adx = talib.ADX(
                high.values,
                low.values,
                close.values,
                timeperiod=period
            )
            return pd.Series(adx, index=close.index)
        except Exception as e:
            logger.error(f"Error calculating ADX: {e}")
            return pd.Series(index=close.index)

    @staticmethod
    def detect_support_resistance(
        prices: pd.Series,
        window: int = 20,
        tolerance: float = 0.02
    ) -> Dict[str, float]:
        """
        Detect support and resistance levels.

        Args:
            prices: Price series
            window: Window for local min/max detection
            tolerance: Tolerance for level clustering (2%)

        Returns:
            Dictionary with support and resistance levels
        """
        try:
            # Find local minima (support) and maxima (resistance)
            local_min = prices.rolling(window=window, center=True).min()
            local_max = prices.rolling(window=window, center=True).max()

            support_levels = prices[prices == local_min].unique()
            resistance_levels = prices[prices == local_max].unique()

            # Cluster nearby levels
            def cluster_levels(levels, tolerance):
                if len(levels) == 0:
                    return []

                levels = sorted(levels)
                clustered = []
                current_cluster = [levels[0]]

                for level in levels[1:]:
                    if abs(level - current_cluster[-1]) / current_cluster[-1] <= tolerance:
                        current_cluster.append(level)
                    else:
                        clustered.append(np.mean(current_cluster))
                        current_cluster = [level]

                clustered.append(np.mean(current_cluster))
                return clustered

            support = cluster_levels(support_levels, tolerance)
            resistance = cluster_levels(resistance_levels, tolerance)

            return {
                "support_levels": support,
                "resistance_levels": resistance,
                "nearest_support": min(support, key=lambda x: abs(x - prices.iloc[-1])) if support else None,
                "nearest_resistance": min(resistance, key=lambda x: abs(x - prices.iloc[-1])) if resistance else None
            }

        except Exception as e:
            logger.error(f"Error detecting support/resistance: {e}")
            return {
                "support_levels": [],
                "resistance_levels": [],
                "nearest_support": None,
                "nearest_resistance": None
            }

    @staticmethod
    def calculate_all_indicators(
        df: pd.DataFrame,
        total_shares: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Calculate all technical indicators for a DataFrame.

        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
            total_shares: Total outstanding shares for turnover rate

        Returns:
            DataFrame with all indicators added
        """
        try:
            result = df.copy()

            # Validate required columns
            required = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in result.columns for col in required):
                logger.error(f"Missing required columns. Need: {required}")
                return result

            # RSI
            result['rsi'] = TechnicalIndicators.calculate_rsi(result['close'])

            # MACD
            macd, signal, hist = TechnicalIndicators.calculate_macd(result['close'])
            result['macd'] = macd
            result['macd_signal'] = signal
            result['macd_hist'] = hist

            # Moving Averages
            mas = TechnicalIndicators.calculate_moving_averages(result['close'])
            for ma_name, ma_series in mas.items():
                result[ma_name] = ma_series

            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = TechnicalIndicators.calculate_bollinger_bands(
                result['close']
            )
            result['bb_upper'] = bb_upper
            result['bb_middle'] = bb_middle
            result['bb_lower'] = bb_lower

            # KDJ
            k, d, j = TechnicalIndicators.calculate_kdj(
                result['high'],
                result['low'],
                result['close']
            )
            result['kdj_k'] = k
            result['kdj_d'] = d
            result['kdj_j'] = j

            # ATR
            result['atr'] = TechnicalIndicators.calculate_atr(
                result['high'],
                result['low'],
                result['close']
            )

            # ADX
            result['adx'] = TechnicalIndicators.calculate_adx(
                result['high'],
                result['low'],
                result['close']
            )

            # Turnover rate (if total_shares provided)
            if total_shares:
                result['turnover_rate'] = TechnicalIndicators.calculate_turnover_rate(
                    result['volume'],
                    total_shares
                )

            logger.debug(f"Calculated all technical indicators, shape: {result.shape}")
            return result

        except Exception as e:
            logger.error(f"Error calculating all indicators: {e}")
            return df


class SignalGenerator:
    """Generate trading signals from technical indicators."""

    @staticmethod
    def rsi_signal(rsi: float, oversold: float = 30, overbought: float = 70) -> str:
        """
        Generate signal from RSI.

        Args:
            rsi: Current RSI value
            oversold: Oversold threshold
            overbought: Overbought threshold

        Returns:
            Signal: 'long', 'short', or 'hold'
        """
        if pd.isna(rsi):
            return 'hold'

        if rsi < oversold:
            return 'long'  # Oversold, potential buy
        elif rsi > overbought:
            return 'short'  # Overbought, potential sell
        else:
            return 'hold'

    @staticmethod
    def macd_signal(macd: float, signal: float, hist: float) -> str:
        """
        Generate signal from MACD.

        Args:
            macd: MACD line
            signal: Signal line
            hist: MACD histogram

        Returns:
            Signal: 'long', 'short', or 'hold'
        """
        if any(pd.isna([macd, signal, hist])):
            return 'hold'

        # MACD crosses above signal line
        if macd > signal and hist > 0:
            return 'long'
        # MACD crosses below signal line
        elif macd < signal and hist < 0:
            return 'short'
        else:
            return 'hold'

    @staticmethod
    def ma_crossover_signal(
        price: float,
        ma_short: float,
        ma_long: float
    ) -> str:
        """
        Generate signal from MA crossover.

        Args:
            price: Current price
            ma_short: Short-term MA
            ma_long: Long-term MA

        Returns:
            Signal: 'long', 'short', or 'hold'
        """
        if any(pd.isna([price, ma_short, ma_long])):
            return 'hold'

        # Golden cross
        if ma_short > ma_long and price > ma_short:
            return 'long'
        # Death cross
        elif ma_short < ma_long and price < ma_short:
            return 'short'
        else:
            return 'hold'

    @staticmethod
    def bollinger_signal(price: float, bb_upper: float, bb_lower: float) -> str:
        """
        Generate signal from Bollinger Bands.

        Args:
            price: Current price
            bb_upper: Upper band
            bb_lower: Lower band

        Returns:
            Signal: 'long', 'short', or 'hold'
        """
        if any(pd.isna([price, bb_upper, bb_lower])):
            return 'hold'

        # Price near lower band (oversold)
        if price < bb_lower * 1.01:  # Within 1% of lower band
            return 'long'
        # Price near upper band (overbought)
        elif price > bb_upper * 0.99:  # Within 1% of upper band
            return 'short'
        else:
            return 'hold'

    @staticmethod
    def kdj_signal(k: float, d: float, j: float) -> str:
        """
        Generate signal from KDJ indicator.

        Args:
            k: K value
            d: D value
            j: J value

        Returns:
            Signal: 'long', 'short', or 'hold'
        """
        if any(pd.isna([k, d, j])):
            return 'hold'

        # K crosses above D in oversold area
        if k > d and k < 20:
            return 'long'
        # K crosses below D in overbought area
        elif k < d and k > 80:
            return 'short'
        else:
            return 'hold'
