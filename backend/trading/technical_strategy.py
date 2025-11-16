"""
Technical Analysis Strategy

基于技术指标的交易策略
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from .strategy import BaseStrategy


class TechnicalStrategy(BaseStrategy):
    """技术分析策略

    使用多个技术指标生成交易信号：
    - RSI（相对强弱指标）
    - MACD（移动平均收敛散度）
    - MA（移动平均线）
    """

    def __init__(
        self,
        rsi_period: int = 14,
        rsi_overbought: float = 70,
        rsi_oversold: float = 30,
        ma_short: int = 5,
        ma_long: int = 20,
        use_macd: bool = True
    ):
        super().__init__("Technical")

        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.use_macd = use_macd

        self.has_position = False

    def generate_signal(
        self,
        symbol: str,
        current_data: pd.DataFrame,
        portfolio_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成技术分析信号"""

        # 需要足够的历史数据
        if len(current_data) < max(self.ma_long, self.rsi_period):
            return {'action': 'hold', 'reason': 'Insufficient data'}

        # 计算技术指标
        indicators = self._calculate_indicators(current_data)

        # 更新持仓状态
        self.has_position = portfolio_state.get('has_position', False)

        # 生成信号
        signal = self._generate_signal_from_indicators(indicators)

        return signal

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算技术指标"""
        indicators = {}

        # 1. RSI
        rsi = self._calculate_rsi(df['close'], self.rsi_period)
        indicators['rsi'] = rsi

        # 2. 移动平均线
        ma_short = df['close'].rolling(window=self.ma_short).mean().iloc[-1]
        ma_long = df['close'].rolling(window=self.ma_long).mean().iloc[-1]
        indicators['ma_short'] = ma_short
        indicators['ma_long'] = ma_long
        indicators['ma_cross'] = ma_short - ma_long

        # 3. MACD（可选）
        if self.use_macd:
            macd_line, signal_line, histogram = self._calculate_macd(df['close'])
            indicators['macd'] = macd_line
            indicators['macd_signal'] = signal_line
            indicators['macd_histogram'] = histogram

        # 4. 当前价格
        indicators['price'] = df['close'].iloc[-1]

        return indicators

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """计算RSI指标"""
        delta = prices.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1]

    def _calculate_macd(
        self,
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> tuple:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return (
            macd_line.iloc[-1],
            signal_line.iloc[-1],
            histogram.iloc[-1]
        )

    def _generate_signal_from_indicators(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """根据技术指标生成交易信号"""

        reasons = []
        buy_score = 0
        sell_score = 0

        # 1. RSI 信号
        rsi = indicators.get('rsi', 50)
        if rsi < self.rsi_oversold:
            buy_score += 2
            reasons.append(f"RSI超卖({rsi:.1f})")
        elif rsi > self.rsi_overbought:
            sell_score += 2
            reasons.append(f"RSI超买({rsi:.1f})")

        # 2. MA 金叉/死叉
        ma_cross = indicators.get('ma_cross', 0)
        if ma_cross > 0:
            buy_score += 1
            reasons.append(f"均线金叉(MA{self.ma_short}>{self.ma_long})")
        elif ma_cross < 0:
            sell_score += 1
            reasons.append(f"均线死叉(MA{self.ma_short}<{self.ma_long})")

        # 3. MACD 信号
        if self.use_macd:
            macd_histogram = indicators.get('macd_histogram', 0)
            if macd_histogram > 0:
                buy_score += 1
                reasons.append("MACD柱状图为正")
            elif macd_histogram < 0:
                sell_score += 1
                reasons.append("MACD柱状图为负")

        # 决策逻辑
        if not self.has_position:
            # 没有持仓，考虑买入
            if buy_score >= 2:
                return {
                    'action': 'buy',
                    'reason': ' + '.join(reasons)
                }
        else:
            # 有持仓，考虑卖出
            if sell_score >= 2:
                return {
                    'action': 'sell',
                    'reason': ' + '.join(reasons)
                }

        return {
            'action': 'hold',
            'reason': f'信号不明确 (买入:{buy_score}, 卖出:{sell_score})'
        }

    def on_trade(self, trade_info: Dict[str, Any]):
        """交易执行后的回调"""
        side = trade_info.get('side')
        if side == 'buy':
            self.has_position = True
        elif side == 'sell':
            self.has_position = False

    def reset(self):
        """重置策略状态"""
        self.has_position = False
