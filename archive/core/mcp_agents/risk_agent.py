"""
Risk Manager Agent - Enhanced with real Tushare Pro data.
Evaluates A-share specific risks and portfolio-level risks.
"""

import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from loguru import logger
from sqlalchemy import select

from core.mcp_agents.base_agent import BaseAgent
from core.data.models import AgentAnalysisResult, SignalDirection
from core.data.sources import data_source
from core.data.tushare_api import get_tushare_api
from config.agents_config import agents_config
from database.models import Position, StockInfo


class RiskManagerAgent(BaseAgent):
    """
    Risk Manager Agent.

    Evaluates multiple risk factors:
    - A-share specific risks:
      * Share pledge ratio (股权质押)
      * Restricted share unlock schedule (限售股解禁)
      * Goodwill impairment risk (商誉减值风险)
    - Portfolio risks:
      * Position size limits
      * Sector concentration
      * Correlation limits
    - Market risks:
      * Volatility
      * Liquidity
    """

    def __init__(self, redis_client=None):
        """Initialize Risk Manager Agent."""
        config = agents_config.RISK_AGENT
        super().__init__(config, redis_client)

        # A-share specific risk thresholds
        self.pledge_warning = config.params.get("pledge_ratio_warning", 0.30)
        self.pledge_danger = config.params.get("pledge_ratio_danger", 0.50)
        self.goodwill_warning = config.params.get("goodwill_ratio_warning", 0.20)
        self.goodwill_danger = config.params.get("goodwill_ratio_danger", 0.30)
        self.unlock_days = config.params.get("restricted_share_unlock_days", 90)

        # Portfolio risk limits
        self.max_correlation = config.params.get("max_position_correlation", 0.70)
        self.max_sector = config.params.get("max_sector_concentration", 0.30)
        self.max_position = config.params.get("max_single_position", 0.10)

        # Market risk thresholds
        self.volatility_threshold = config.params.get("volatility_percentile_threshold", 0.80)
        self.min_volume = config.params.get("liquidity_min_volume", 1000000)

        # Try to initialize Tushare API
        try:
            self.tushare = get_tushare_api()
            self.has_tushare = True
        except Exception as e:
            logger.warning(f"Tushare API not available: {e}")
            self.has_tushare = False

    async def analyze(
        self,
        symbol: Optional[str] = None,
        db_session=None,
        **kwargs
    ) -> AgentAnalysisResult:
        """
        Perform risk analysis on a symbol.

        Args:
            symbol: Stock symbol to analyze
            db_session: Database session for portfolio data
            **kwargs: Additional parameters

        Returns:
            AgentAnalysisResult with risk analysis
        """
        start_time = time.time()

        if not symbol:
            return self._create_error_result(None, "Symbol is required for risk analysis")

        try:
            # Check cache first
            cache_key = self._create_cache_key(symbol, db_session=bool(db_session))
            cached_result = await self.get_cached_result(cache_key)
            if cached_result:
                logger.debug(f"Returning cached risk analysis for {symbol}")
                return AgentAnalysisResult(**cached_result)

            logger.info(f"Performing risk analysis for {symbol}")

            # Collect all risk factors
            risk_analysis = {}

            # 1. A-share specific risks
            ashare_risks = await self._analyze_ashare_risks(symbol, db_session)
            risk_analysis['ashare_risks'] = ashare_risks

            # 2. Market risks
            market_risks = await self._analyze_market_risks(symbol)
            risk_analysis['market_risks'] = market_risks

            # 3. Portfolio risks (if db_session provided)
            if db_session:
                portfolio_risks = await self._analyze_portfolio_risks(symbol, db_session)
                risk_analysis['portfolio_risks'] = portfolio_risks

            # Calculate overall risk score
            risk_score = self._calculate_risk_score(risk_analysis)
            risk_analysis['risk_score'] = risk_score

            # Determine risk level
            risk_level = self._determine_risk_level(risk_score)
            risk_analysis['risk_level'] = risk_level

            # Generate signal (risk acts as a filter/validator)
            signal_direction, confidence = self._generate_signal(risk_analysis)

            # Create reasoning
            reasoning = self._create_reasoning(risk_analysis, signal_direction)

            # Calculate execution time
            execution_time = int((time.time() - start_time) * 1000)

            # Create result
            result = self._create_analysis_result(
                symbol=symbol,
                score=risk_score,
                direction=signal_direction,
                confidence=confidence,
                analysis=risk_analysis,
                reasoning=reasoning,
                execution_time_ms=execution_time
            )

            # Cache result
            await self.set_cached_result(cache_key, result.model_dump())

            return result

        except Exception as e:
            logger.exception(f"Error in risk analysis for {symbol}: {e}")
            return self._create_error_result(symbol, str(e))

    async def _analyze_ashare_risks(
        self,
        symbol: str,
        db_session
    ) -> Dict[str, Any]:
        """
        Analyze A-share specific risks using real Tushare Pro data.

        Args:
            symbol: Stock symbol
            db_session: Database session

        Returns:
            Dictionary with A-share risk analysis
        """
        risks = {}

        if not self.has_tushare:
            logger.warning("Tushare API not available, A-share risk analysis limited")
            return risks

        try:
            # Convert symbol to Tushare format
            ts_code = self.tushare._convert_symbol(symbol, to_tushare=True)

            # 1. Stock Pledge Ratio (股权质押)
            try:
                pledge_ratio = self.tushare.get_latest_pledge_ratio(ts_code)
                if pledge_ratio is not None:
                    risks['pledge_ratio'] = {
                        'value': float(pledge_ratio) / 100.0,  # Convert to decimal
                        'warning': pledge_ratio > (self.pledge_warning * 100),
                        'danger': pledge_ratio > (self.pledge_danger * 100),
                        'score': self._score_pledge_ratio(pledge_ratio / 100.0)
                    }
                    logger.debug(f"Got pledge ratio for {ts_code}: {pledge_ratio}%")
                else:
                    logger.debug(f"No pledge data for {ts_code} (common for some stocks)")
            except Exception as e:
                logger.warning(f"Failed to get pledge ratio for {ts_code}: {e}")

            # 2. ST Status (Special Treatment)
            try:
                is_st = self.tushare.is_st_stock(ts_code)
                risks['st_status'] = {
                    'is_st': is_st,
                    'score': -1.0 if is_st else 0.0
                }
                if is_st:
                    logger.info(f"{ts_code} is ST stock - high risk")
            except Exception as e:
                logger.warning(f"Failed to check ST status for {ts_code}: {e}")

            # 3. Suspension Status (停牌) - Use correct API
            try:
                # Use suspend API (long-term), not suspend_d (intraday)
                df_suspend = self.tushare.get_suspend(ts_code=ts_code)

                if df_suspend.empty:
                    # No suspension records
                    risks['suspension'] = {
                        'is_suspended': False,
                        'score': 0.0
                    }
                    logger.debug(f"{ts_code} has no suspension records")
                else:
                    # Check if currently suspended
                    today = datetime.now().strftime('%Y%m%d')
                    today_int = int(today)

                    # Check each suspension record to see if currently active
                    is_currently_suspended = False
                    current_suspend_info = None

                    for _, row in df_suspend.iterrows():
                        suspend_date_str = str(row.get('suspend_date', '')).split('.')[0]
                        resume_date = row.get('resume_date')

                        if not suspend_date_str or suspend_date_str == '' or suspend_date_str == 'nan':
                            continue

                        suspend_date_int = int(suspend_date_str)

                        # Check if suspension has started
                        if suspend_date_int > today_int:
                            # Future suspension, skip
                            continue

                        # Check if suspension has ended
                        if pd.notna(resume_date):
                            resume_date_str = str(resume_date).split('.')[0]
                            if resume_date_str and resume_date_str != 'nan':
                                resume_date_int = int(resume_date_str)
                                if resume_date_int <= today_int:
                                    # Already resumed, skip
                                    continue

                        # If we reach here, suspension is currently active
                        is_currently_suspended = True
                        current_suspend_info = {
                            'suspend_date': suspend_date_str,
                            'resume_date': str(resume_date) if pd.notna(resume_date) else None,
                            'suspend_reason': row.get('suspend_reason', '未知原因')
                        }
                        break  # Only need the first active suspension

                    if is_currently_suspended:
                        risks['suspension'] = {
                            'is_suspended': True,
                            'suspend_date': current_suspend_info['suspend_date'],
                            'resume_date': current_suspend_info['resume_date'],
                            'suspend_reason': current_suspend_info['suspend_reason'],
                            'score': -0.8  # High risk for suspended stocks
                        }
                        logger.info(f"{ts_code} is currently suspended")
                    else:
                        risks['suspension'] = {
                            'is_suspended': False,
                            'score': 0.0
                        }
                        logger.debug(f"{ts_code} has suspension history but not currently suspended")

            except Exception as e:
                logger.warning(f"Failed to check suspension status for {ts_code}: {e}")

            # 4. Try to get goodwill and restricted shares from database
            # (These are less frequently updated, database is acceptable)
            if db_session:
                try:
                    stmt = select(StockInfo).where(StockInfo.symbol == symbol)
                    result = await db_session.execute(stmt)
                    stock_info = result.scalar_one_or_none()

                    if stock_info:
                        # Goodwill impairment risk
                        goodwill_ratio = stock_info.goodwill_ratio
                        if goodwill_ratio is not None:
                            risks['goodwill_impairment'] = {
                                'value': float(goodwill_ratio),
                                'warning': goodwill_ratio > self.goodwill_warning,
                                'danger': goodwill_ratio > self.goodwill_danger,
                                'score': self._score_goodwill(goodwill_ratio)
                            }

                        # Restricted share unlock
                        if stock_info.next_unlock_date:
                            days_until_unlock = (stock_info.next_unlock_date - datetime.now()).days
                            unlock_ratio = stock_info.restricted_shares_ratio or 0

                            risks['restricted_unlock'] = {
                                'next_unlock_date': stock_info.next_unlock_date.isoformat(),
                                'days_until_unlock': days_until_unlock,
                                'unlock_ratio': float(unlock_ratio),
                                'imminent': days_until_unlock <= self.unlock_days,
                                'score': self._score_unlock_risk(days_until_unlock, unlock_ratio)
                            }
                except Exception as e:
                    logger.warning(f"Error fetching database risk data: {e}")

        except Exception as e:
            logger.exception(f"Error in A-share risk analysis for {symbol}: {e}")

        return risks

    async def _analyze_market_risks(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze market-related risks.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with market risk analysis
        """
        risks = {}

        try:
            # Get recent price data for volatility analysis
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            df = data_source.get_daily_bars(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            if not df.empty and len(df) >= 10:
                # Calculate volatility (standard deviation of returns)
                df['returns'] = df['close'].pct_change()
                volatility = df['returns'].std()
                annual_volatility = volatility * (252 ** 0.5)  # Annualized

                risks['volatility'] = {
                    'daily_volatility': float(volatility),
                    'annual_volatility': float(annual_volatility),
                    'high_volatility': annual_volatility > 0.40,  # >40% annualized
                    'score': self._score_volatility(annual_volatility)
                }

                # Liquidity analysis (average daily volume)
                avg_volume = df['volume'].mean()
                latest_volume = df['volume'].iloc[-1] if len(df) > 0 else 0

                risks['liquidity'] = {
                    'avg_volume': float(avg_volume),
                    'latest_volume': float(latest_volume),
                    'low_liquidity': avg_volume < self.min_volume,
                    'score': self._score_liquidity(avg_volume)
                }

                # Recent price movement
                if len(df) >= 5:
                    recent_return = (df['close'].iloc[-1] / df['close'].iloc[-5] - 1)
                    risks['recent_movement'] = {
                        '5day_return': float(recent_return),
                        'sharp_decline': recent_return < -0.15,  # >15% drop
                        'sharp_rise': recent_return > 0.15,  # >15% rise
                    }

        except Exception as e:
            logger.warning(f"Error analyzing market risks: {e}")

        return risks

    async def _analyze_portfolio_risks(
        self,
        symbol: str,
        db_session
    ) -> Dict[str, Any]:
        """
        Analyze portfolio-level risks.

        Args:
            symbol: Stock symbol
            db_session: Database session

        Returns:
            Dictionary with portfolio risk analysis
        """
        risks = {}

        try:
            # Get current positions
            stmt = select(Position)
            result = await db_session.execute(stmt)
            positions = result.scalars().all()

            if positions:
                # Calculate total portfolio value
                total_value = sum(
                    p.quantity * p.current_price
                    for p in positions
                    if p.current_price
                )

                # Check if symbol already in portfolio
                existing_position = next(
                    (p for p in positions if p.symbol == symbol),
                    None
                )

                if existing_position and existing_position.current_price:
                    position_value = existing_position.quantity * existing_position.current_price
                    position_pct = position_value / total_value if total_value > 0 else 0

                    risks['position_size'] = {
                        'current_position_pct': float(position_pct),
                        'exceeds_limit': position_pct > self.max_position,
                        'score': self._score_position_size(position_pct)
                    }

                # Sector concentration (would need stock_info for sector)
                # This is a simplified version
                risks['num_positions'] = {
                    'count': len(positions),
                    'concentrated': len(positions) < 5,
                    'diversified': len(positions) >= 10
                }

        except Exception as e:
            logger.warning(f"Error analyzing portfolio risks: {e}")

        return risks

    def _score_pledge_ratio(self, ratio: float) -> float:
        """Score pledge ratio risk (lower is better)."""
        if ratio < 0.10:
            return 0.0  # Low risk
        elif ratio < self.pledge_warning:
            return -0.3
        elif ratio < self.pledge_danger:
            return -0.6  # Warning level
        else:
            return -1.0  # Danger level

    def _score_goodwill(self, ratio: float) -> float:
        """Score goodwill impairment risk (lower is better)."""
        if ratio < 0.10:
            return 0.0
        elif ratio < self.goodwill_warning:
            return -0.3
        elif ratio < self.goodwill_danger:
            return -0.6
        else:
            return -1.0

    def _score_unlock_risk(self, days: int, unlock_ratio: float) -> float:
        """Score restricted share unlock risk."""
        if days > 180:  # >6 months away
            return 0.0
        elif days > self.unlock_days:  # 3-6 months
            return -0.2 * unlock_ratio
        else:  # <3 months, imminent
            return -0.5 * unlock_ratio

    def _score_volatility(self, annual_vol: float) -> float:
        """Score volatility risk (lower is better)."""
        if annual_vol < 0.20:  # Low volatility
            return 0.0
        elif annual_vol < 0.30:
            return -0.2
        elif annual_vol < 0.40:
            return -0.4
        else:  # High volatility
            return -0.7

    def _score_liquidity(self, avg_volume: float) -> float:
        """Score liquidity risk (higher volume is better)."""
        if avg_volume >= self.min_volume * 5:
            return 0.0
        elif avg_volume >= self.min_volume:
            return -0.2
        elif avg_volume >= self.min_volume * 0.5:
            return -0.5
        else:
            return -0.8

    def _score_position_size(self, position_pct: float) -> float:
        """Score position size risk."""
        if position_pct < 0.05:  # <5%
            return 0.0
        elif position_pct < self.max_position:  # <10%
            return -0.2
        elif position_pct < 0.15:  # <15%
            return -0.6
        else:  # >15%
            return -1.0

    def _calculate_risk_score(self, risk_analysis: Dict[str, Any]) -> float:
        """
        Calculate overall risk score.
        Lower score = higher risk.

        Args:
            risk_analysis: Risk analysis results

        Returns:
            Risk score (-1 to 0, where 0 is low risk)
        """
        scores = []

        # A-share risks
        ashare = risk_analysis.get('ashare_risks', {})
        for risk_type, risk_data in ashare.items():
            if isinstance(risk_data, dict) and 'score' in risk_data:
                scores.append(risk_data['score'])

        # Market risks
        market = risk_analysis.get('market_risks', {})
        for risk_type, risk_data in market.items():
            if isinstance(risk_data, dict) and 'score' in risk_data:
                scores.append(risk_data['score'])

        # Portfolio risks
        portfolio = risk_analysis.get('portfolio_risks', {})
        for risk_type, risk_data in portfolio.items():
            if isinstance(risk_data, dict) and 'score' in risk_data:
                scores.append(risk_data['score'])

        # Average score (will be <= 0)
        if scores:
            return sum(scores) / len(scores)
        else:
            return 0.0  # No risk data, assume low risk

    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level from score."""
        if risk_score > -0.2:
            return "低风险"
        elif risk_score > -0.4:
            return "中低风险"
        elif risk_score > -0.6:
            return "中等风险"
        elif risk_score > -0.8:
            return "中高风险"
        else:
            return "高风险"

    def _generate_signal(
        self,
        risk_analysis: Dict[str, Any]
    ) -> tuple[SignalDirection, float]:
        """
        Generate risk signal.
        Risk agent acts as a validator - it provides risk assessment confidence.

        Args:
            risk_analysis: Risk analysis results

        Returns:
            Tuple of (signal_direction, confidence)
        """
        risk_score = risk_analysis.get('risk_score', 0.0)

        # Risk score: 0 to -1 (0 = no risk, -1 = extreme risk)
        # Confidence should reflect how certain we are about the risk assessment

        if risk_score < -0.7:  # High risk (70%+)
            direction = SignalDirection.CLOSE
            # High confidence in high risk assessment
            confidence = min(abs(risk_score) + 0.15, 0.95)
        elif risk_score < -0.4:  # Medium-high risk (40%-70%)
            direction = SignalDirection.HOLD
            # Medium-high confidence in medium risk assessment
            confidence = min(abs(risk_score) + 0.25, 0.85)
        elif risk_score < -0.2:  # Medium-low risk (20%-40%)
            direction = SignalDirection.HOLD
            # Medium confidence
            confidence = 0.5 + abs(risk_score)
        else:  # Low risk (< 20%)
            # Very low risk - we can be confident the stock is low risk
            direction = SignalDirection.LONG  # Low risk supports long positions
            # Base confidence on how low the risk is
            # risk_score = -0.1 → confidence = 0.65
            # risk_score = -0.05 → confidence = 0.675
            # risk_score = 0 → confidence = 0.7
            confidence = 0.7 - abs(risk_score) * 0.5
            confidence = max(min(confidence, 0.75), 0.5)

        return direction, confidence

    def _create_reasoning(
        self,
        risk_analysis: Dict[str, Any],
        direction: SignalDirection
    ) -> str:
        """Create human-readable risk reasoning."""
        reasons = []

        # Overall risk level
        risk_level = risk_analysis.get('risk_level', '未知')
        reasons.append(f"风险等级：{risk_level}")

        # A-share risks
        ashare = risk_analysis.get('ashare_risks', {})

        if 'pledge_ratio' in ashare:
            pledge = ashare['pledge_ratio']
            if pledge.get('danger'):
                reasons.append(f"高质押风险({pledge['value']:.1%})")
            elif pledge.get('warning'):
                reasons.append(f"质押率偏高({pledge['value']:.1%})")

        if 'goodwill_impairment' in ashare:
            goodwill = ashare['goodwill_impairment']
            if goodwill.get('danger'):
                reasons.append(f"商誉减值风险高({goodwill['value']:.1%})")

        if 'restricted_unlock' in ashare:
            unlock = ashare['restricted_unlock']
            if unlock.get('imminent'):
                reasons.append(
                    f"限售股即将解禁({unlock['days_until_unlock']}天，"
                    f"占比{unlock['unlock_ratio']:.1%})"
                )

        if 'st_status' in ashare and ashare['st_status'].get('is_st'):
            reasons.append("ST股票，退市风险")

        if 'suspension' in ashare and ashare['suspension'].get('is_suspended'):
            suspend_info = ashare['suspension']
            suspend_date = suspend_info.get('suspend_date', '未知')
            resume_date = suspend_info.get('resume_date', '待定')
            suspend_reason = suspend_info.get('suspend_reason', '未知原因')
            reasons.append(f"股票停牌中(停牌日:{suspend_date}，复牌日:{resume_date}，原因:{suspend_reason})")

        # Market risks
        market = risk_analysis.get('market_risks', {})

        if 'volatility' in market:
            vol = market['volatility']
            if vol.get('high_volatility'):
                reasons.append(f"高波动性({vol['annual_volatility']:.1%})")

        if 'liquidity' in market:
            liq = market['liquidity']
            if liq.get('low_liquidity'):
                reasons.append(f"流动性不足(日均{liq['avg_volume']:,.0f}股)")

        if 'recent_movement' in market:
            move = market['recent_movement']
            if move.get('sharp_decline'):
                reasons.append(f"近期大幅下跌({move['5day_return']:.1%})")

        # Portfolio risks
        portfolio = risk_analysis.get('portfolio_risks', {})

        if 'position_size' in portfolio:
            pos = portfolio['position_size']
            if pos.get('exceeds_limit'):
                reasons.append(f"持仓占比过高({pos['current_position_pct']:.1%})")

        if not reasons:
            reasons.append("未发现重大风险")

        return "；".join(reasons)
