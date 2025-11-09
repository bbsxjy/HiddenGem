"""
Fundamental Analysis Agent - Enhanced with real Tushare Pro data.
Analyzes fundamental metrics (PE, PB, ROE, debt ratios) for stock valuation.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from loguru import logger

from core.mcp_agents.base_agent import BaseAgent
from core.data.models import AgentAnalysisResult, SignalDirection
from core.data.tushare_api import get_tushare_api
from config.agents_config import agents_config


class FundamentalAgent(BaseAgent):
    """
    Fundamental Analysis Agent.

    Analyzes fundamental metrics using real Tushare Pro data:
    - PE/PB Ratio (from daily_basic)
    - ROE (Return on Equity from fina_indicator)
    - Debt-to-Assets Ratio (from fina_indicator)
    - Profitability metrics
    - Valuation assessment
    """

    def __init__(self, redis_client=None):
        """Initialize Fundamental Analysis Agent."""
        config = agents_config.FUNDAMENTAL_AGENT
        super().__init__(config, redis_client)

        self.metrics = config.params.get("metrics", [])
        self.pe_low = config.params.get("pe_low_threshold", 15)
        self.pe_high = config.params.get("pe_high_threshold", 50)
        self.pb_low = config.params.get("pb_low_threshold", 1.0)
        self.roe_min = config.params.get("roe_min_threshold", 10.0)  # 10%
        self.debt_max = config.params.get("debt_max_threshold", 70.0)  # 70%

        # Try to initialize Tushare API
        try:
            self.tushare = get_tushare_api()
            self.has_tushare = True
        except Exception as e:
            logger.warning(f"Tushare API not available: {e}")
            self.has_tushare = False

    async def analyze(self, symbol: Optional[str] = None, **kwargs) -> AgentAnalysisResult:
        """
        Perform fundamental analysis on a symbol using real Tushare data.

        Args:
            symbol: Stock symbol to analyze
            **kwargs: Additional parameters

        Returns:
            AgentAnalysisResult with fundamental analysis
        """
        start_time = time.time()

        if not symbol:
            return self._create_error_result(None, "Symbol is required for fundamental analysis")

        try:
            # Check cache first
            cache_key = self._create_cache_key(symbol)
            cached_result = await self.get_cached_result(cache_key)
            if cached_result:
                logger.debug(f"Returning cached fundamental analysis for {symbol}")
                return AgentAnalysisResult(**cached_result)

            if not self.has_tushare:
                return self._create_error_result(symbol, "Tushare API not available")

            logger.info(f"Performing fundamental analysis for {symbol} with REAL Tushare data")

            # Convert symbol to Tushare format
            ts_code = self.tushare._convert_symbol(symbol, to_tushare=True)

            # Fetch real fundamental data
            fundamental_data = await self._fetch_fundamental_data(ts_code)

            if not fundamental_data:
                return self._create_error_result(
                    symbol,
                    f"No fundamental data available for {symbol}"
                )

            # Perform fundamental analysis
            analysis_results = self._analyze_fundamentals(fundamental_data)

            # Generate signal
            signal_direction, confidence = self._generate_signal(analysis_results)

            # Create reasoning
            reasoning = self._create_reasoning(analysis_results, signal_direction)

            # Calculate execution time
            execution_time = int((time.time() - start_time) * 1000)

            # Create result
            result = self._create_analysis_result(
                symbol=symbol,
                score=analysis_results.get("overall_score", 0.0),
                direction=signal_direction,
                confidence=confidence,
                analysis=analysis_results,
                reasoning=reasoning,
                execution_time_ms=execution_time
            )

            # Cache result (24h TTL for fundamentals)
            await self.set_cached_result(cache_key, result.model_dump())

            return result

        except Exception as e:
            logger.exception(f"Error in fundamental analysis for {symbol}: {e}")
            return self._create_error_result(symbol, str(e))

    async def _fetch_fundamental_data(self, ts_code: str) -> Dict[str, Any]:
        """
        Fetch fundamental data from Tushare Pro API.

        Args:
            ts_code: Tushare stock code (e.g., '600000.SH')

        Returns:
            Dictionary with fundamental metrics
        """
        data = {}

        try:
            # 1. Get daily basic data (PE, PB, Market Cap)
            trade_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            df_basic = self.tushare.get_daily_basic(ts_code=ts_code, trade_date=trade_date)

            if not df_basic.empty:
                row = df_basic.iloc[0]
                data['pe_ratio'] = row.get('pe_ttm')  # TTM PE ratio
                data['pb_ratio'] = row.get('pb')
                data['ps_ratio'] = row.get('ps_ttm')
                data['total_mv'] = row.get('total_mv')  # Total market value (million RMB)
                data['circ_mv'] = row.get('circ_mv')  # Circulating market value
                data['turnover_rate'] = row.get('turnover_rate')
                data['turnover_rate_f'] = row.get('turnover_rate_f')  # Free float turnover rate
                logger.debug(f"Got daily_basic for {ts_code}: PE={data.get('pe_ratio')}, PB={data.get('pb_ratio')}")
            else:
                logger.warning(f"No daily_basic data for {ts_code} on {trade_date}")

        except Exception as e:
            logger.warning(f"Failed to get daily_basic for {ts_code}: {e}")

        try:
            # 2. Get latest financial indicators (ROE, Debt Ratio, etc.)
            indicators = self.tushare.get_latest_financial_indicators(ts_code)

            if indicators:
                data['roe'] = indicators.get('roe')  # Return on Equity (%)
                data['roe_waa'] = indicators.get('roe_waa')  # Weighted average ROE
                data['roa'] = indicators.get('roa')  # Return on Assets
                data['debt_to_assets'] = indicators.get('debt_to_assets')  # Debt ratio (%)
                data['current_ratio'] = indicators.get('current_ratio')  # Current ratio
                data['quick_ratio'] = indicators.get('quick_ratio')  # Quick ratio
                data['gross_margin'] = indicators.get('gross_margin')  # Gross profit margin (%)
                data['netprofit_margin'] = indicators.get('netprofit_margin')  # Net profit margin (%)
                data['eps'] = indicators.get('eps')  # Earnings per share
                data['bps'] = indicators.get('bps')  # Book value per share
                data['end_date'] = indicators.get('end_date')  # Report period
                logger.debug(f"Got fina_indicator for {ts_code}: ROE={data.get('roe')}, Debt={data.get('debt_to_assets')}")
            else:
                logger.warning(f"No financial indicators for {ts_code}")

        except Exception as e:
            logger.warning(f"Failed to get financial indicators for {ts_code}: {e}")

        return data

    def _analyze_fundamentals(
        self,
        financial_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze fundamental metrics from real Tushare data.

        Args:
            financial_data: Financial metrics from Tushare Pro API

        Returns:
            Dictionary with analysis results
        """
        analysis = {
            'raw_data': financial_data
        }

        # PE Ratio Analysis
        pe_ratio = financial_data.get('pe_ratio')
        if pe_ratio is not None and pe_ratio > 0:
            analysis['pe_ratio'] = {
                'value': float(pe_ratio),
                'undervalued': pe_ratio < self.pe_low,
                'overvalued': pe_ratio > self.pe_high,
                'reasonable': self.pe_low <= pe_ratio <= self.pe_high,
                'score': self._score_pe_ratio(pe_ratio)
            }

        # PB Ratio Analysis
        pb_ratio = financial_data.get('pb_ratio')
        if pb_ratio is not None and pb_ratio > 0:
            analysis['pb_ratio'] = {
                'value': float(pb_ratio),
                'undervalued': pb_ratio < self.pb_low,
                'overvalued': pb_ratio > 3.0,
                'reasonable': self.pb_low <= pb_ratio <= 3.0,
                'score': self._score_pb_ratio(pb_ratio)
            }

        # ROE Analysis (from fina_indicator, already in % format)
        roe = financial_data.get('roe')
        if roe is not None:
            analysis['roe'] = {
                'value': float(roe),
                'excellent': roe > 20.0,  # >20% excellent
                'good': 15.0 <= roe <= 20.0,
                'acceptable': self.roe_min <= roe < 15.0,
                'poor': roe < self.roe_min,
                'score': self._score_roe(roe)
            }

        # Debt-to-Assets Analysis (from fina_indicator, already in % format)
        debt_to_assets = financial_data.get('debt_to_assets')
        if debt_to_assets is not None:
            analysis['debt_to_assets'] = {
                'value': float(debt_to_assets),
                'low_debt': debt_to_assets < 30.0,  # <30%
                'moderate_debt': 30.0 <= debt_to_assets < self.debt_max,
                'high_debt': debt_to_assets >= self.debt_max,
                'score': self._score_debt(debt_to_assets)
            }

        # Market Cap Analysis (total_mv is in million RMB)
        total_mv = financial_data.get('total_mv')
        if total_mv is not None:
            market_cap = total_mv * 1000000  # Convert to RMB
            analysis['market_cap'] = {
                'value': float(market_cap),
                'value_billion': float(market_cap / 1000000000),  # In billion
                'large_cap': market_cap > 100000000000,  # >1000亿
                'mid_cap': 10000000000 <= market_cap <= 100000000000,  # 100-1000亿
                'small_cap': market_cap < 10000000000,  # <100亿
            }

        # PS Ratio Analysis
        ps_ratio = financial_data.get('ps_ratio')
        if ps_ratio is not None and ps_ratio > 0:
            analysis['ps_ratio'] = {
                'value': float(ps_ratio),
                'undervalued': ps_ratio < 2.0,
                'overvalued': ps_ratio > 10.0,
                'score': self._score_ps_ratio(ps_ratio)
            }

        # Profitability Analysis
        gross_margin = financial_data.get('gross_margin')
        netprofit_margin = financial_data.get('netprofit_margin')
        if gross_margin is not None or netprofit_margin is not None:
            analysis['profitability'] = {
                'gross_margin': float(gross_margin) if gross_margin else None,
                'netprofit_margin': float(netprofit_margin) if netprofit_margin else None,
                'high_margin': (netprofit_margin or 0) > 15.0  # >15% net margin
            }

        # Liquidity Analysis
        current_ratio = financial_data.get('current_ratio')
        quick_ratio = financial_data.get('quick_ratio')
        if current_ratio is not None or quick_ratio is not None:
            analysis['liquidity'] = {
                'current_ratio': float(current_ratio) if current_ratio else None,
                'quick_ratio': float(quick_ratio) if quick_ratio else None,
                'healthy': (current_ratio or 0) > 1.5  # Current ratio > 1.5
            }

        # Overall valuation score
        analysis['overall_score'] = self._calculate_overall_score(analysis)

        # Valuation summary
        analysis['valuation'] = self._determine_valuation(analysis)

        return analysis

    def _score_pe_ratio(self, pe: float) -> float:
        """
        Score PE ratio (-1 to 1).

        Args:
            pe: PE ratio

        Returns:
            Score
        """
        if pe < 0:  # Negative earnings
            return -0.5

        if pe < 10:  # Very low, possibly undervalued
            return 0.8
        elif pe < self.pe_low:  # Low, undervalued
            return 0.6
        elif pe <= self.pe_high:  # Reasonable
            return 0.2
        elif pe <= 80:  # High
            return -0.4
        else:  # Very high, overvalued
            return -0.8

    def _score_pb_ratio(self, pb: float) -> float:
        """Score PB ratio (-1 to 1)."""
        if pb < 0.5:  # Very low
            return 0.9
        elif pb < self.pb_low:  # Low, undervalued
            return 0.7
        elif pb <= 2.0:  # Reasonable
            return 0.3
        elif pb <= 4.0:  # High
            return -0.3
        else:  # Very high, overvalued
            return -0.7

    def _score_roe(self, roe: float) -> float:
        """Score ROE (-1 to 1). ROE is in percentage format (e.g., 20.0 for 20%)."""
        if roe < 0:  # Negative ROE
            return -0.8
        elif roe < 5.0:  # Very low (<5%)
            return -0.4
        elif roe < self.roe_min:  # Below threshold (<10%)
            return 0.0
        elif roe < 15.0:  # Acceptable (10-15%)
            return 0.4
        elif roe < 20.0:  # Good (15-20%)
            return 0.7
        else:  # Excellent (>20%)
            return 1.0

    def _score_debt(self, debt: float) -> float:
        """Score debt-to-assets ratio (-1 to 1). Debt is in percentage format (e.g., 70.0 for 70%)."""
        if debt < 20.0:  # Very low debt (<20%)
            return 0.8
        elif debt < 40.0:  # Low debt (20-40%)
            return 0.5
        elif debt < self.debt_max:  # Moderate debt (40-70%)
            return 0.2
        elif debt < 100.0:  # High debt (70-100%)
            return -0.4
        else:  # Very high debt (>100%)
            return -0.8

    def _score_ps_ratio(self, ps: float) -> float:
        """Score PS ratio (-1 to 1)."""
        if ps < 1.0:  # Very low
            return 0.7
        elif ps < 2.0:  # Low
            return 0.4
        elif ps < 5.0:  # Reasonable
            return 0.1
        elif ps < 10.0:  # High
            return -0.3
        else:  # Very high
            return -0.6

    def _calculate_overall_score(self, analysis: Dict[str, Any]) -> float:
        """
        Calculate overall fundamental score.

        Args:
            analysis: Analysis results

        Returns:
            Overall score (-1 to 1)
        """
        scores = []
        weights = []

        # PE ratio (weight: 0.25)
        if 'pe_ratio' in analysis:
            scores.append(analysis['pe_ratio']['score'])
            weights.append(0.25)

        # PB ratio (weight: 0.20)
        if 'pb_ratio' in analysis:
            scores.append(analysis['pb_ratio']['score'])
            weights.append(0.20)

        # ROE (weight: 0.30)
        if 'roe' in analysis:
            scores.append(analysis['roe']['score'])
            weights.append(0.30)

        # Debt (weight: 0.15)
        if 'debt_to_assets' in analysis:
            scores.append(analysis['debt_to_assets']['score'])
            weights.append(0.15)

        # PS ratio (weight: 0.10)
        if 'ps_ratio' in analysis:
            scores.append(analysis['ps_ratio']['score'])
            weights.append(0.10)

        # Calculate weighted average
        if scores and weights:
            total_weight = sum(weights)
            weighted_sum = sum(s * w for s, w in zip(scores, weights))
            return weighted_sum / total_weight
        else:
            return 0.0

    def _determine_valuation(self, analysis: Dict[str, Any]) -> str:
        """
        Determine overall valuation.

        Args:
            analysis: Analysis results

        Returns:
            Valuation description
        """
        score = analysis.get('overall_score', 0.0)

        if score > 0.5:
            return "严重低估"
        elif score > 0.3:
            return "低估"
        elif score > 0.1:
            return "略微低估"
        elif score > -0.1:
            return "合理估值"
        elif score > -0.3:
            return "略微高估"
        elif score > -0.5:
            return "高估"
        else:
            return "严重高估"

    def _generate_signal(
        self,
        analysis: Dict[str, Any]
    ) -> tuple[SignalDirection, float]:
        """
        Generate trading signal from fundamental analysis.

        Args:
            analysis: Analysis results

        Returns:
            Tuple of (signal_direction, confidence)
        """
        overall_score = analysis.get('overall_score', 0.0)

        # Determine direction based on score
        if overall_score > 0.2:
            direction = SignalDirection.LONG
        elif overall_score < -0.2:
            direction = SignalDirection.SHORT
        else:
            direction = SignalDirection.HOLD

        # Calculate confidence based on data quality and consistency
        # Confidence should reflect how reliable the fundamental data is

        # Count available metrics
        available_metrics = 0
        positive_metrics = 0
        negative_metrics = 0

        metrics_list = ['pe_ratio', 'pb_ratio', 'roe', 'debt_to_assets', 'ps_ratio']
        for metric in metrics_list:
            if metric in analysis:
                available_metrics += 1
                score = analysis[metric].get('score', 0)
                if score > 0.2:
                    positive_metrics += 1
                elif score < -0.2:
                    negative_metrics += 1

        # Base confidence on data availability and consistency
        if available_metrics == 0:
            confidence = 0.3
        else:
            # Data completeness factor (more metrics = higher confidence)
            completeness = available_metrics / len(metrics_list)  # 0.2-1.0

            # Consistency factor (how many metrics agree with direction)
            if direction == SignalDirection.LONG:
                agreeing = positive_metrics
            elif direction == SignalDirection.SHORT:
                agreeing = negative_metrics
            else:
                agreeing = available_metrics - positive_metrics - negative_metrics

            consistency = agreeing / available_metrics if available_metrics > 0 else 0

            # Base confidence: 0.5-0.85 range based on consistency
            base_confidence = 0.45 + (consistency * 0.4)

            # Adjust by completeness (more complete data = higher confidence)
            base_confidence += (completeness * 0.1)

            # Adjust by score magnitude
            score_factor = min(abs(overall_score), 1.0)
            confidence = base_confidence + (score_factor * 0.1)

            # Boost confidence for exceptional fundamentals
            if direction == SignalDirection.LONG:
                # Check for exceptional quality
                exceptional_quality = False
                if 'roe' in analysis and analysis['roe'].get('excellent'):
                    exceptional_quality = True
                if 'debt_to_assets' in analysis and analysis['debt_to_assets'].get('low_debt'):
                    exceptional_quality = True

                if exceptional_quality and overall_score > 0.3:
                    confidence = min(confidence * 1.15, 1.0)

            # Ensure reasonable range
            confidence = max(min(confidence, 1.0), 0.4)

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

        # Overall valuation
        valuation = analysis.get('valuation', '未知')
        reasons.append(f"整体估值：{valuation}")

        # PE ratio
        if 'pe_ratio' in analysis:
            pe = analysis['pe_ratio']
            if pe.get('undervalued'):
                reasons.append(f"PE={pe['value']:.2f}，低于{self.pe_low}，估值偏低")
            elif pe.get('overvalued'):
                reasons.append(f"PE={pe['value']:.2f}，高于{self.pe_high}，估值偏高")

        # PB ratio
        if 'pb_ratio' in analysis:
            pb = analysis['pb_ratio']
            if pb.get('undervalued'):
                reasons.append(f"PB={pb['value']:.2f}，低于{self.pb_low}，账面价值被低估")

        # ROE
        if 'roe' in analysis:
            roe = analysis['roe']
            if roe.get('excellent'):
                reasons.append(f"ROE={roe['value']:.1f}%，盈利能力优秀")
            elif roe.get('poor'):
                reasons.append(f"ROE={roe['value']:.1f}%，盈利能力较差")

        # Debt
        if 'debt_to_assets' in analysis:
            debt = analysis['debt_to_assets']
            if debt.get('high_debt'):
                reasons.append(f"负债率={debt['value']:.1f}%，财务风险较高")
            elif debt.get('low_debt'):
                reasons.append(f"负债率={debt['value']:.1f}%，财务稳健")

        # Market cap context
        if 'market_cap' in analysis:
            mc = analysis['market_cap']
            if mc.get('large_cap'):
                reasons.append("大盘股，流动性好")
            elif mc.get('small_cap'):
                reasons.append("小盘股，波动性较大")

        if not reasons:
            reasons.append("基本面数据不足")

        return "；".join(reasons)
