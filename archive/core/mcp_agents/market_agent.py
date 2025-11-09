"""
Market Monitor Agent - Enhanced with real Tushare data.
Monitors market-wide indicators including index trends and market sentiment.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np
from loguru import logger

from core.mcp_agents.base_agent import BaseAgent
from core.data.models import AgentAnalysisResult, SignalDirection
from core.data.tushare_api import get_tushare_api
from config.agents_config import agents_config


class MarketMonitorAgent(BaseAgent):
    """
    Market Monitor Agent.

    Monitors market-wide indicators using real data from Tushare:
    - Market phase from index analysis (上证指数走势)
    - Market sentiment from price momentum and volatility
    - Northbound capital flows (if available)
    - Margin trading (if available)
    """

    def __init__(self, redis_client=None):
        """Initialize Market Monitor Agent."""
        config = agents_config.MARKET_AGENT
        super().__init__(config, redis_client)

        self.northbound_threshold = config.params.get("northbound_threshold", 100000000)
        self.margin_threshold = config.params.get("margin_change_threshold", 0.05)

        # Try to initialize Tushare API
        try:
            self.tushare = get_tushare_api()
            self.has_tushare = True
        except Exception as e:
            logger.warning(f"Tushare API not available: {e}")
            self.has_tushare = False

    async def analyze(self, symbol: Optional[str] = None, **kwargs) -> AgentAnalysisResult:
        """
        Perform market monitoring analysis.

        Args:
            symbol: Stock symbol (can be None for market-wide analysis)
            **kwargs: Additional parameters

        Returns:
            AgentAnalysisResult with market analysis
        """
        start_time = time.time()

        try:
            # Check cache
            cache_key = self._create_cache_key(symbol or "market_wide")
            cached_result = await self.get_cached_result(cache_key)
            if cached_result:
                logger.debug("Returning cached market analysis")
                return AgentAnalysisResult(**cached_result)

            logger.info("Performing market monitoring analysis with real data")

            # Market analysis
            analysis_results = await self._analyze_market_indicators(symbol)

            # Generate signal
            signal_direction, confidence = self._generate_signal(analysis_results)

            # Create reasoning
            reasoning = self._create_reasoning(analysis_results)

            # Calculate execution time
            execution_time = int((time.time() - start_time) * 1000)

            # Create result
            result = self._create_analysis_result(
                symbol=symbol,
                score=analysis_results.get("market_score", 0.0),
                direction=signal_direction,
                confidence=confidence,
                analysis=analysis_results,
                reasoning=reasoning,
                execution_time_ms=execution_time
            )

            # Cache result (shorter TTL for market data - 5 minutes)
            await self.set_cached_result(cache_key, result.model_dump())

            return result

        except Exception as e:
            logger.exception(f"Error in market monitoring: {e}")
            return self._create_error_result(symbol, str(e))

    async def _analyze_market_indicators(self, symbol: Optional[str]) -> Dict[str, Any]:
        """
        Analyze market indicators using real Tushare data.

        Args:
            symbol: Stock symbol (optional)

        Returns:
            Dictionary with market analysis
        """
        analysis = {}

        if not self.has_tushare:
            return self._get_fallback_analysis()

        try:
            # Analyze market phase using SSE Composite Index (000001.SH)
            market_phase = await self._analyze_market_phase()
            analysis['market_phase'] = market_phase

            # Try to get northbound capital flow
            northbound = await self._analyze_northbound_capital()
            analysis['northbound_capital'] = northbound

            # Try to get margin trading data
            margin = await self._analyze_margin_trading()
            analysis['margin_trading'] = margin

            # Calculate market sentiment
            sentiment = await self._calculate_market_sentiment(market_phase, northbound, margin)
            analysis['sentiment'] = sentiment

            # Calculate overall market score
            market_score = self._calculate_market_score(analysis)
            analysis['market_score'] = market_score

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing market indicators: {e}")
            return self._get_fallback_analysis()

    async def _analyze_market_phase(self) -> Dict[str, Any]:
        """
        Analyze market phase using SSE Composite Index.

        Returns:
            Dictionary with market phase information
        """
        try:
            # Get SSE Composite Index data (000001.SH)
            # Note: Free Tushare token may not have permission for index data
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')

            # Try to get index data (may require higher Tushare permission)
            try:
                df = self.tushare.get_index_daily('000001.SH', start_date, end_date)
            except Exception as e:
                logger.debug(f"Index data not available (may need Tushare upgrade): {e}")
                # Fallback: return consolidation phase
                return {
                    'phase': 'consolidation',
                    'confidence': 0.3,
                    'description': '市场处于盘整阶段（数据权限受限，建议升级Tushare账号获取完整分析）'
                }

            if df.empty or len(df) < 20:
                return {
                    'phase': 'unknown',
                    'confidence': 0.0,
                    'description': '市场阶段分析数据不足'
                }

            # Sort by date
            df = df.sort_values('trade_date')

            # Calculate moving averages
            df['ma_5'] = df['close'].rolling(window=5).mean()
            df['ma_20'] = df['close'].rolling(window=20).mean()
            df['ma_60'] = df['close'].rolling(window=60).mean() if len(df) >= 60 else None

            # Get latest data
            latest = df.iloc[-1]
            close = latest['close']
            ma_5 = latest['ma_5']
            ma_20 = latest['ma_20']

            # Calculate price change over different periods
            pct_5d = ((latest['close'] / df.iloc[-6]['close']) - 1) if len(df) > 5 else 0
            pct_20d = ((latest['close'] / df.iloc[-21]['close']) - 1) if len(df) > 20 else 0

            # Determine market phase
            phase = 'consolidation'
            confidence = 0.5

            # Bull market: uptrend with price above MAs
            if close > ma_5 > ma_20 and pct_20d > 0.05:
                phase = 'bull'
                confidence = min(0.9, 0.6 + pct_20d * 2)

            # Bear market: downtrend with price below MAs
            elif close < ma_5 < ma_20 and pct_20d < -0.05:
                phase = 'bear'
                confidence = min(0.9, 0.6 + abs(pct_20d) * 2)

            # Volatile: large swings
            elif abs(pct_5d) > 0.03:
                phase = 'volatile'
                confidence = 0.7

            # Description
            descriptions = {
                'bull': f'市场处于上升趋势（近20日涨幅{pct_20d*100:.2f}%）',
                'bear': f'市场处于下降趋势（近20日跌幅{abs(pct_20d)*100:.2f}%）',
                'consolidation': '市场处于盘整阶段',
                'volatile': f'市场波动较大（近5日波动{abs(pct_5d)*100:.2f}%）'
            }

            return {
                'phase': phase,
                'confidence': float(confidence),
                'description': descriptions.get(phase, '市场阶段未知'),
                'index_close': float(close),
                'pct_5d': float(pct_5d),
                'pct_20d': float(pct_20d),
            }

        except Exception as e:
            logger.error(f"Error analyzing market phase: {e}")
            return {
                'phase': 'unknown',
                'confidence': 0.0,
                'description': f'市场阶段分析失败: {str(e)[:50]}'
            }

    async def _analyze_northbound_capital(self) -> Dict[str, Any]:
        """
        Analyze northbound capital flow (if data available).

        Returns:
            Dictionary with northbound capital info
        """
        try:
            # Get recent northbound capital flow
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')

            df = self.tushare.get_moneyflow_hsgt(start_date=start_date, end_date=end_date)

            if df.empty:
                return {
                    'net_inflow': 0,
                    'is_inflow': False,
                    'significant': False,
                    'description': '北向资金流向数据暂不可用'
                }

            # Get latest data
            df = df.sort_values('trade_date', ascending=False)
            latest = df.iloc[0]

            net_inflow = float(latest.get('north_money', 0)) * 10000  # Convert to RMB (Tushare unit is 万元)
            is_inflow = net_inflow > 0
            significant = abs(net_inflow) > self.northbound_threshold

            # Description
            if significant and is_inflow:
                desc = f'北向资金大幅流入{abs(net_inflow)/100000000:.2f}亿元'
            elif significant and not is_inflow:
                desc = f'北向资金大幅流出{abs(net_inflow)/100000000:.2f}亿元'
            elif is_inflow:
                desc = f'北向资金小幅流入{abs(net_inflow)/100000000:.2f}亿元'
            else:
                desc = f'北向资金小幅流出{abs(net_inflow)/100000000:.2f}亿元'

            return {
                'net_inflow': float(net_inflow),
                'is_inflow': is_inflow,
                'significant': significant,
                'description': desc
            }

        except Exception as e:
            logger.debug(f"Northbound capital data not available: {e}")
            return {
                'net_inflow': 0,
                'is_inflow': False,
                'significant': False,
                'description': '北向资金流向数据暂不可用（可能需要更高权限）'
            }

    async def _analyze_margin_trading(self) -> Dict[str, Any]:
        """
        Analyze margin trading data (if available).

        Returns:
            Dictionary with margin trading info
        """
        try:
            # Get recent margin trading data
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')

            df = self.tushare.get_margin(start_date=start_date, end_date=end_date)

            if df.empty:
                return {
                    'balance': 0,
                    'change_pct': 0.0,
                    'description': '融资融券数据暂不可用'
                }

            # Sort by date
            df = df.sort_values('trade_date', ascending=False)

            if len(df) >= 2:
                latest = df.iloc[0]
                previous = df.iloc[1]

                balance = float(latest.get('rzye', 0)) * 10000  # Convert to RMB
                prev_balance = float(previous.get('rzye', 0)) * 10000
                change_pct = (balance - prev_balance) / prev_balance if prev_balance > 0 else 0

                # Description
                if abs(change_pct) > self.margin_threshold:
                    trend = '增加' if change_pct > 0 else '减少'
                    desc = f'融资余额{trend}{abs(change_pct)*100:.2f}%至{balance/100000000:.2f}亿元'
                else:
                    desc = f'融资余额保持稳定，当前为{balance/100000000:.2f}亿元'

                return {
                    'balance': float(balance),
                    'change_pct': float(change_pct),
                    'description': desc
                }
            else:
                return {
                    'balance': 0,
                    'change_pct': 0.0,
                    'description': '融资融券数据不足'
                }

        except Exception as e:
            logger.debug(f"Margin trading data not available: {e}")
            return {
                'balance': 0,
                'change_pct': 0.0,
                'description': '融资融券数据暂不可用（可能需要更高权限）'
            }

    async def _calculate_market_sentiment(
        self,
        market_phase: Dict[str, Any],
        northbound: Dict[str, Any],
        margin: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate overall market sentiment.

        Args:
            market_phase: Market phase data
            northbound: Northbound capital data
            margin: Margin trading data

        Returns:
            Dictionary with sentiment score and description
        """
        # Base sentiment from market phase
        phase_scores = {
            'bull': 0.7,
            'consolidation': 0.5,
            'volatile': 0.4,
            'bear': 0.3,
            'unknown': 0.5
        }

        sentiment_score = phase_scores.get(market_phase.get('phase'), 0.5)

        # Adjust for northbound capital
        if northbound.get('significant'):
            if northbound.get('is_inflow'):
                sentiment_score += 0.1
            else:
                sentiment_score -= 0.1

        # Adjust for margin trading
        margin_change = margin.get('change_pct', 0)
        if abs(margin_change) > 0.05:  # 5% threshold
            sentiment_score += margin_change * 0.5

        # Clamp to [0, 1]
        sentiment_score = max(0.0, min(1.0, sentiment_score))

        # Description
        if sentiment_score > 0.65:
            desc = '市场情绪偏乐观'
        elif sentiment_score < 0.35:
            desc = '市场情绪偏悲观'
        else:
            desc = '市场情绪中性'

        return {
            'score': float(sentiment_score),
            'description': desc
        }

    def _calculate_market_score(self, analysis: Dict[str, Any]) -> float:
        """
        Calculate overall market score.

        Args:
            analysis: Analysis results

        Returns:
            Market score between -1.0 and 1.0
        """
        # Get market phase contribution
        phase = analysis.get('market_phase', {})
        phase_map = {'bull': 0.5, 'consolidation': 0.0, 'volatile': -0.2, 'bear': -0.5}
        phase_score = phase_map.get(phase.get('phase'), 0.0)
        phase_confidence = phase.get('confidence', 0.5)

        # Get sentiment contribution
        sentiment_score = analysis.get('sentiment', {}).get('score', 0.5)
        sentiment_contribution = (sentiment_score - 0.5) * 2  # Convert to [-1, 1]

        # Get capital flow contribution
        northbound = analysis.get('northbound_capital', {})
        capital_contribution = 0.0
        if northbound.get('significant'):
            capital_contribution = 0.3 if northbound.get('is_inflow') else -0.3

        # Weighted average
        market_score = (
            phase_score * phase_confidence * 0.5 +
            sentiment_contribution * 0.3 +
            capital_contribution * 0.2
        )

        return float(max(-1.0, min(1.0, market_score)))

    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """
        Return fallback analysis when Tushare is not available.

        Returns:
            Dictionary with default analysis
        """
        return {
            'market_phase': {
                'phase': 'unknown',
                'confidence': 0.0,
                'description': '市场数据源不可用'
            },
            'northbound_capital': {
                'net_inflow': 0,
                'is_inflow': False,
                'significant': False,
                'description': '北向资金数据不可用'
            },
            'margin_trading': {
                'balance': 0,
                'change_pct': 0.0,
                'description': '融资融券数据不可用'
            },
            'sentiment': {
                'score': 0.5,
                'description': '市场情绪未知'
            },
            'market_score': 0.0
        }

    def _generate_signal(
        self,
        analysis: Dict[str, Any]
    ) -> tuple[SignalDirection, float]:
        """Generate signal from market analysis."""
        market_score = analysis.get('market_score', 0.0)

        # Market agent provides context, not strong signals
        if market_score > 0.3:
            return SignalDirection.LONG, min(0.6, 0.4 + market_score * 0.5)
        elif market_score < -0.3:
            return SignalDirection.SHORT, min(0.6, 0.4 + abs(market_score) * 0.5)
        else:
            return SignalDirection.HOLD, 0.3

    def _create_reasoning(self, analysis: Dict[str, Any]) -> str:
        """Create reasoning from market analysis."""
        reasons = []

        if 'market_phase' in analysis:
            phase = analysis['market_phase']
            reasons.append(phase.get('description', ''))

        if 'northbound_capital' in analysis:
            reasons.append(analysis['northbound_capital'].get('description', ''))

        if 'margin_trading' in analysis:
            reasons.append(analysis['margin_trading'].get('description', ''))

        if 'sentiment' in analysis:
            reasons.append(analysis['sentiment'].get('description', ''))

        return "；".join(reasons) if reasons else "市场数据分析中"
