"""
Sentiment Analysis Agent - Enhanced with real Tushare Pro data.
Analyzes market sentiment through money flow, institutional behavior, and trading activity.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from loguru import logger

from core.mcp_agents.base_agent import BaseAgent
from core.data.models import AgentAnalysisResult, SignalDirection
from core.data.tushare_api import get_tushare_api
from config.agents_config import agents_config


class SentimentAgent(BaseAgent):
    """
    Sentiment Analysis Agent.

    Analyzes market sentiment from real data:
    - Money flow (individual stock capital flow)
    - Foreign capital holdings (HK Stock Connect)
    - Shareholder trading (insider buying/selling)
    - Dragon-Tiger List (institutional/speculative activity)
    """

    def __init__(self, redis_client=None):
        """Initialize Sentiment Agent."""
        config = agents_config.SENTIMENT_AGENT
        super().__init__(config, redis_client)

        # Try to initialize Tushare API
        try:
            self.tushare = get_tushare_api()
            self.has_tushare = True
        except Exception as e:
            logger.warning(f"Tushare API not available: {e}")
            self.has_tushare = False

    async def analyze(self, symbol: Optional[str] = None, **kwargs) -> AgentAnalysisResult:
        """
        Perform sentiment analysis on a symbol using real Tushare data.

        Args:
            symbol: Stock symbol to analyze
            **kwargs: Additional parameters

        Returns:
            AgentAnalysisResult with sentiment analysis
        """
        start_time = time.time()

        if not symbol:
            return self._create_error_result(None, "Symbol is required for sentiment analysis")

        try:
            # Check cache first
            cache_key = self._create_cache_key(symbol)
            cached_result = await self.get_cached_result(cache_key)
            if cached_result:
                logger.debug(f"Returning cached sentiment analysis for {symbol}")
                return AgentAnalysisResult(**cached_result)

            if not self.has_tushare:
                return self._create_error_result(symbol, "Tushare API not available")

            logger.info(f"Performing sentiment analysis for {symbol} with REAL Tushare data")

            # Convert symbol to Tushare format
            ts_code = self.tushare._convert_symbol(symbol, to_tushare=True)

            # Collect sentiment factors
            sentiment_analysis = {}

            # 1. Money flow analysis
            money_flow = await self._analyze_money_flow(ts_code)
            sentiment_analysis['money_flow'] = money_flow

            # 2. Foreign capital sentiment
            foreign_capital = await self._analyze_foreign_capital(ts_code)
            sentiment_analysis['foreign_capital'] = foreign_capital

            # 3. Insider trading
            insider_trading = await self._analyze_insider_trading(ts_code)
            sentiment_analysis['insider_trading'] = insider_trading

            # 4. Dragon-Tiger List activity
            dragon_tiger = await self._analyze_dragon_tiger(ts_code)
            sentiment_analysis['dragon_tiger'] = dragon_tiger

            # Calculate overall sentiment score
            sentiment_score = self._calculate_sentiment_score(sentiment_analysis)
            sentiment_analysis['overall_score'] = sentiment_score

            # Determine sentiment level
            sentiment_level = self._determine_sentiment_level(sentiment_score)
            sentiment_analysis['sentiment_level'] = sentiment_level

            # Generate signal
            signal_direction, confidence = self._generate_signal(sentiment_analysis)

            # Create reasoning
            reasoning = self._create_reasoning(sentiment_analysis, signal_direction)

            # Calculate execution time
            execution_time = int((time.time() - start_time) * 1000)

            # Create result
            result = self._create_analysis_result(
                symbol=symbol,
                score=sentiment_score,
                direction=signal_direction,
                confidence=confidence,
                analysis=sentiment_analysis,
                reasoning=reasoning,
                execution_time_ms=execution_time
            )

            # Cache result (shorter TTL for sentiment - 1 hour)
            await self.set_cached_result(cache_key, result.model_dump())

            return result

        except Exception as e:
            logger.exception(f"Error in sentiment analysis for {symbol}: {e}")
            return self._create_error_result(symbol, str(e))

    async def _analyze_money_flow(self, ts_code: str) -> Dict[str, Any]:
        """
        Analyze money flow patterns (主力资金流向).

        Args:
            ts_code: Tushare stock code

        Returns:
            Dictionary with money flow analysis
        """
        flow = {}

        try:
            # Get recent money flow data (last 5 trading days)
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

            df = self.tushare.get_moneyflow(ts_code, start_date=start_date, end_date=end_date)

            if not df.empty:
                # Latest day
                latest = df.iloc[0]
                net_flow = latest.get('net_mf_amount', 0)  # in million RMB

                # Large order flow (big players)
                buy_lg = latest.get('buy_lg_amount', 0)
                sell_lg = latest.get('sell_lg_amount', 0)
                net_lg = buy_lg - sell_lg

                # Extra large order flow (主力)
                buy_elg = latest.get('buy_elg_amount', 0)
                sell_elg = latest.get('sell_elg_amount', 0)
                net_elg = buy_elg - sell_elg

                flow['net_flow'] = float(net_flow)
                flow['net_large_flow'] = float(net_lg)
                flow['net_extra_large_flow'] = float(net_elg)

                # 5-day trend
                if len(df) >= 3:
                    recent_flows = df['net_mf_amount'].head(3).tolist()
                    flow['3day_trend'] = 'inflow' if sum(recent_flows) > 0 else 'outflow'
                    flow['3day_total'] = float(sum(recent_flows))

                # Score money flow
                flow['score'] = self._score_money_flow(net_flow, net_lg, net_elg)

                logger.debug(f"Got money flow for {ts_code}: net={net_flow:.0f}, large={net_lg:.0f}, elg={net_elg:.0f}")

            else:
                logger.warning(f"No money flow data for {ts_code}")
                flow['score'] = 0.0

        except Exception as e:
            logger.warning(f"Failed to get money flow for {ts_code}: {e}")
            flow['score'] = 0.0

        return flow

    async def _analyze_foreign_capital(self, ts_code: str) -> Dict[str, Any]:
        """
        Analyze foreign capital sentiment (北向资金).

        Args:
            ts_code: Tushare stock code

        Returns:
            Dictionary with foreign capital analysis
        """
        foreign = {}

        try:
            # Get recent HK holdings (last 10 trading days)
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=15)).strftime('%Y%m%d')

            df = self.tushare.get_hk_hold(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if not df.empty and len(df) >= 2:
                # Sort by date
                df = df.sort_values('trade_date', ascending=False)

                # Latest holdings
                latest = df.iloc[0]
                latest_ratio = latest.get('ratio', 0)  # Holdings ratio %

                # Previous holdings for comparison
                previous = df.iloc[1]
                previous_ratio = previous.get('ratio', 0)

                # Change in holdings
                ratio_change = latest_ratio - previous_ratio

                foreign['holdings_ratio'] = float(latest_ratio)
                foreign['ratio_change'] = float(ratio_change)
                foreign['trend'] = 'increasing' if ratio_change > 0 else 'decreasing'

                # Score foreign capital sentiment
                foreign['score'] = self._score_foreign_capital(latest_ratio, ratio_change)

                logger.debug(f"Got HK holdings for {ts_code}: ratio={latest_ratio:.2f}%, change={ratio_change:.2f}%")

            else:
                logger.debug(f"No HK holdings for {ts_code} (not in Stock Connect)")
                foreign['score'] = 0.0

        except Exception as e:
            logger.warning(f"Failed to get HK holdings for {ts_code}: {e}")
            foreign['score'] = 0.0

        return foreign

    async def _analyze_insider_trading(self, ts_code: str) -> Dict[str, Any]:
        """
        Analyze insider trading sentiment (股东增减持).

        Args:
            ts_code: Tushare stock code

        Returns:
            Dictionary with insider trading analysis
        """
        insider = {}

        try:
            # Get shareholder trading records (last 6 months)
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')

            df = self.tushare.get_stk_holdertrade(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if not df.empty:
                # Count increases vs decreases
                increases = df[df['in_de'] == '增持']
                decreases = df[df['in_de'] == '减持']

                # Calculate total change ratio
                increase_total = increases['change_ratio'].sum() if not increases.empty else 0
                decrease_total = decreases['change_ratio'].sum() if not decreases.empty else 0

                insider['increase_count'] = len(increases)
                insider['decrease_count'] = len(decreases)
                insider['net_change_ratio'] = float(increase_total - decrease_total)

                # Recent activity (last 30 days)
                recent_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                recent_df = df[df['ann_date'] >= recent_date]

                if not recent_df.empty:
                    insider['recent_activity'] = True
                    insider['recent_type'] = recent_df.iloc[0]['in_de']

                # Score insider trading
                insider['score'] = self._score_insider_trading(insider['increase_count'], insider['decrease_count'], insider['net_change_ratio'])

                logger.debug(f"Got insider trading for {ts_code}: inc={insider['increase_count']}, dec={insider['decrease_count']}")

            else:
                logger.debug(f"No insider trading records for {ts_code}")
                insider['score'] = 0.0

        except Exception as e:
            logger.warning(f"Failed to get insider trading for {ts_code}: {e}")
            insider['score'] = 0.0

        return insider

    async def _analyze_dragon_tiger(self, ts_code: str) -> Dict[str, Any]:
        """
        Analyze Dragon-Tiger List activity (龙虎榜).

        Args:
            ts_code: Tushare stock code

        Returns:
            Dictionary with dragon-tiger list analysis
        """
        dragon = {}

        try:
            # Check recent appearances on top list (last 5 days is enough)
            # Dragon-tiger list is for recent hot stocks, no need to check 30 days
            # This reduces API calls from 30 to 5 for stocks not on the list
            max_lookback_days = 5  # Reduced from 30 to 5

            # Search by date range (get all, then filter by symbol)
            all_records = []
            for i in range(max_lookback_days):
                trade_date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
                df = self.tushare.get_top_list(ts_code=ts_code, trade_date=trade_date)
                if not df.empty:
                    all_records.append(df)
                    break  # Found records, stop searching

            if all_records:
                df = all_records[0]  # Most recent
                latest = df.iloc[0]

                dragon['on_list'] = True
                dragon['list_date'] = latest.get('trade_date')
                dragon['net_amount'] = float(latest.get('net_amount', 0))  # Million RMB
                dragon['reason'] = latest.get('reason', 'Unknown')

                # Check for institutional activity
                try:
                    inst_df = self.tushare.get_top_inst(trade_date=latest.get('trade_date'), ts_code=ts_code)
                    if not inst_df.empty:
                        dragon['institutional'] = True
                        dragon['inst_net_buy'] = float(inst_df['net_buy'].sum())
                    else:
                        dragon['institutional'] = False
                except:
                    dragon['institutional'] = False

                # Score dragon-tiger activity
                dragon['score'] = self._score_dragon_tiger(dragon['net_amount'], dragon.get('institutional', False))

                logger.debug(f"Got dragon-tiger for {ts_code}: net={dragon['net_amount']:.0f}, inst={dragon.get('institutional')}")

            else:
                logger.debug(f"Not on dragon-tiger list in last {max_lookback_days} days: {ts_code}")
                dragon['on_list'] = False
                dragon['score'] = 0.0

        except Exception as e:
            logger.warning(f"Failed to get dragon-tiger data for {ts_code}: {e}")
            dragon['score'] = 0.0

        return dragon

    def _score_money_flow(self, net_flow: float, net_lg: float, net_elg: float) -> float:
        """Score money flow (-1 to 1)."""
        # Focus on large and extra-large orders (institutional money)
        main_flow = net_lg + net_elg

        if main_flow > 50000:  # >500 million RMB inflow
            return 0.9
        elif main_flow > 20000:  # >200 million RMB inflow
            return 0.6
        elif main_flow > 5000:  # >50 million RMB inflow
            return 0.3
        elif main_flow > -5000:  # Small flow
            return 0.0
        elif main_flow > -20000:  # Moderate outflow
            return -0.3
        elif main_flow > -50000:  # Large outflow
            return -0.6
        else:  # Massive outflow
            return -0.9

    def _score_foreign_capital(self, holdings_ratio: float, ratio_change: float) -> float:
        """Score foreign capital sentiment (-1 to 1)."""
        if ratio_change > 1.0:  # >1% increase
            return 0.8
        elif ratio_change > 0.5:  # >0.5% increase
            return 0.5
        elif ratio_change > 0:  # Any increase
            return 0.2
        elif ratio_change > -0.5:  # Small decrease
            return -0.2
        elif ratio_change > -1.0:  # Moderate decrease
            return -0.5
        else:  # Large decrease
            return -0.8

    def _score_insider_trading(self, increase_count: int, decrease_count: int, net_ratio: float) -> float:
        """Score insider trading sentiment (-1 to 1)."""
        # Net sentiment from count
        net_count = increase_count - decrease_count

        if net_count >= 3:  # Multiple increases
            return 0.7
        elif net_count >= 1:  # Some increases
            return 0.4
        elif net_count == 0:  # Balanced
            return 0.0
        elif net_count >= -1:  # Some decreases
            return -0.4
        else:  # Multiple decreases
            return -0.7

    def _score_dragon_tiger(self, net_amount: float, institutional: bool) -> float:
        """Score dragon-tiger list activity (-1 to 1)."""
        if institutional and net_amount > 0:
            return 0.6  # Institutional buying
        elif institutional and net_amount < 0:
            return -0.6  # Institutional selling
        elif net_amount > 50000:  # Large speculative buying
            return 0.3  # Neutral-positive (could be pump)
        elif net_amount < -50000:  # Large speculative selling
            return -0.3  # Neutral-negative
        else:
            return 0.0

    def _calculate_sentiment_score(self, sentiment_analysis: Dict[str, Any]) -> float:
        """
        Calculate overall sentiment score.

        Args:
            sentiment_analysis: Sentiment analysis results

        Returns:
            Overall sentiment score (-1 to 1)
        """
        scores = []
        weights = []

        # Money flow (weight: 0.40) - Most important
        money_flow = sentiment_analysis.get('money_flow', {})
        if 'score' in money_flow:
            scores.append(money_flow['score'])
            weights.append(0.40)

        # Foreign capital (weight: 0.25)
        foreign = sentiment_analysis.get('foreign_capital', {})
        if 'score' in foreign:
            scores.append(foreign['score'])
            weights.append(0.25)

        # Insider trading (weight: 0.20)
        insider = sentiment_analysis.get('insider_trading', {})
        if 'score' in insider:
            scores.append(insider['score'])
            weights.append(0.20)

        # Dragon-tiger list (weight: 0.15)
        dragon = sentiment_analysis.get('dragon_tiger', {})
        if 'score' in dragon:
            scores.append(dragon['score'])
            weights.append(0.15)

        # Calculate weighted average
        if scores and weights:
            total_weight = sum(weights)
            weighted_sum = sum(s * w for s, w in zip(scores, weights))
            return weighted_sum / total_weight
        else:
            return 0.0

    def _determine_sentiment_level(self, sentiment_score: float) -> str:
        """Determine sentiment level from score."""
        if sentiment_score > 0.6:
            return "极度乐观"
        elif sentiment_score > 0.3:
            return "乐观"
        elif sentiment_score > 0.1:
            return "略微乐观"
        elif sentiment_score > -0.1:
            return "中性"
        elif sentiment_score > -0.3:
            return "略微悲观"
        elif sentiment_score > -0.6:
            return "悲观"
        else:
            return "极度悲观"

    def _generate_signal(
        self,
        sentiment_analysis: Dict[str, Any]
    ) -> tuple[SignalDirection, float]:
        """
        Generate trading signal from sentiment analysis.

        Args:
            sentiment_analysis: Sentiment analysis results

        Returns:
            Tuple of (signal_direction, confidence)
        """
        sentiment_score = sentiment_analysis.get('overall_score', 0.0)

        # Determine direction based on sentiment
        if sentiment_score > 0.3:
            direction = SignalDirection.LONG
        elif sentiment_score < -0.3:
            direction = SignalDirection.SHORT
        else:
            direction = SignalDirection.HOLD

        # Confidence is based on absolute score
        confidence = min(abs(sentiment_score), 1.0)

        return direction, confidence

    def _create_reasoning(
        self,
        sentiment_analysis: Dict[str, Any],
        direction: SignalDirection
    ) -> str:
        """
        Create human-readable reasoning.

        Args:
            sentiment_analysis: Sentiment analysis results
            direction: Signal direction

        Returns:
            Reasoning text
        """
        reasons = []

        # Overall sentiment
        sentiment_level = sentiment_analysis.get('sentiment_level', '未知')
        reasons.append(f"市场情绪：{sentiment_level}")

        # Money flow
        money_flow = sentiment_analysis.get('money_flow', {})
        if 'net_extra_large_flow' in money_flow:
            net_elg = money_flow['net_extra_large_flow']
            if abs(net_elg) > 10000:  # >100 million
                flow_text = "特大单流入" if net_elg > 0 else "特大单流出"
                reasons.append(f"{flow_text}{abs(net_elg)/10000:.1f}亿")

        # Foreign capital
        foreign = sentiment_analysis.get('foreign_capital', {})
        if 'ratio_change' in foreign:
            change = foreign['ratio_change']
            if abs(change) > 0.1:
                trend_text = "北向增持" if change > 0 else "北向减持"
                reasons.append(f"{trend_text}{abs(change):.2f}%")

        # Insider trading
        insider = sentiment_analysis.get('insider_trading', {})
        if insider.get('recent_activity'):
            recent_type = insider.get('recent_type', '')
            reasons.append(f"股东近期{recent_type}")

        # Dragon-tiger list
        dragon = sentiment_analysis.get('dragon_tiger', {})
        if dragon.get('on_list'):
            if dragon.get('institutional'):
                reasons.append("机构上榜买入")
            else:
                reasons.append("游资炒作")

        if not reasons or len(reasons) == 1:
            reasons.append("市场活跃度一般")

        return "；".join(reasons)
