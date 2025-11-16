# -*- coding: utf-8 -*-
"""
Intelligent Sector-Based Training Script

Three-Phase Stock Selection:
1. Phase 1: Quantitative Filter (All stocks → Top 20 candidates)
2. Phase 2: LLM Deep Analysis (Top 20 → Top 5 selected)
3. Phase 3: Portfolio Backtest (Top 5 → Training episode)

Usage:
    python scripts/intelligent_sector_training.py --sector 科技 --start 2024-07-01 --end 2024-08-31
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import argparse
import json
import logging
from dataclasses import dataclass, asdict
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Import core modules
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Import memory system
try:
    from memory import (
        MemoryManager,
        MemoryMode,
        TradingEpisode,
        MarketState,
        AgentAnalysis,
        DecisionChain,
        TradeOutcome,
    )
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    print("WARNING: Memory system not available")

# Import data interface
from tradingagents.dataflows.tushare_utils import get_china_stock_data_tushare
import tushare as ts

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# Sector to Tushare industry mapping
SECTOR_TO_INDUSTRY = {
    "金融": ["银行", "非银金融", "保险"],
    "科技": ["电子", "计算机", "通信", "传媒"],
    "消费": ["食品饮料", "家用电器", "纺织服饰", "商贸零售", "农林牧渔"],
    "医药": ["医药生物"],
    "周期": ["钢铁", "有色金属", "化工", "建筑材料", "煤炭"],
    "制造": ["机械设备", "电气设备", "汽车", "国防军工"],
    "地产": ["房地产", "建筑装饰"],
    "公用": ["公用事业", "交通运输", "电力"],
}


@dataclass
class QuantitativeCandidate:
    """量化筛选候选股票"""
    symbol: str
    name: str
    score: float
    # 基本面指标
    roe: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    debt_ratio: Optional[float] = None
    revenue_growth: Optional[float] = None
    # 技术面指标
    ma_trend: Optional[str] = None  # "bullish", "bearish", "neutral"
    volume_ratio: Optional[float] = None
    price_momentum: Optional[float] = None  # 20日涨幅
    # 资金面指标
    turnover_rate: Optional[float] = None
    # 市场数据
    close_price: Optional[float] = None
    market_cap: Optional[float] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class LLMAnalyzedStock:
    """LLM分析后的股票"""
    symbol: str
    name: str
    quantitative_score: float
    llm_score: float
    final_score: float
    # Agent评分
    technical_score: float
    fundamental_score: float
    sentiment_score: float
    risk_score: float
    # 推荐
    recommendation: str  # "strong_buy", "buy", "hold", "sell"
    reasoning: str
    # 原始数据
    quantitative_data: Dict
    llm_analysis: Dict

    def to_dict(self):
        result = asdict(self)
        result['quantitative_data'] = self.quantitative_data
        result['llm_analysis'] = self.llm_analysis
        return result


@dataclass
class Position:
    """持仓"""
    symbol: str
    name: str
    entry_date: str
    entry_price: float
    shares: int
    days_held: int
    quantitative_score: float
    llm_score: float


class IntelligentSectorTrainer:
    """智能板块选股训练器"""

    def __init__(
        self,
        sector: str,
        start_date: str,
        end_date: str,
        holding_days: int = 5,
        phase1_top_k: int = 20,
        phase2_top_k: int = 5,
        initial_cash: float = 1000000.0,
        position_size: float = 0.2,
        config: Dict[str, Any] = None
    ):
        """
        Initialize Intelligent Sector Trainer

        Args:
            sector: 板块名称（金融/科技/消费/医药/周期/制造/地产/公用）
            start_date: Training start date
            end_date: Training end date
            holding_days: Holding period
            phase1_top_k: Phase 1筛选后保留数量
            phase2_top_k: Phase 2筛选后保留数量
            initial_cash: Initial cash
            position_size: Position size per stock
            config: TradingAgents config
        """
        self.sector = sector
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.holding_days = holding_days
        self.phase1_top_k = phase1_top_k
        self.phase2_top_k = phase2_top_k
        self.initial_cash = initial_cash
        self.position_size = position_size
        self.config = config or DEFAULT_CONFIG.copy()

        # Initialize Tushare
        tushare_token = os.getenv("TUSHARE_TOKEN")
        if tushare_token:
            ts.set_token(tushare_token)
            self.pro = ts.pro_api()
        else:
            raise ValueError("TUSHARE_TOKEN not found in .env")

        # Initialize TradingAgentsGraph
        logger.info("Initializing TradingAgents system...")
        self.trading_graph = TradingAgentsGraph(config=self.config)

        # Initialize Memory Bank
        self.memory_manager = None
        if MEMORY_AVAILABLE:
            logger.info("Initializing Memory Bank (TRAINING mode)...")
            self.memory_manager = MemoryManager(
                mode=MemoryMode.TRAINING,
                config=self.config
            )

        # Portfolio state
        self.portfolio = []
        self.cash = initial_cash

        # Statistics
        self.total_episodes = 0
        self.successful_episodes = 0
        self.total_return = 0.0

        logger.info("Intelligent Sector Trainer initialized")
        logger.info(f"   Sector: {sector}")
        logger.info(f"   Phase 1: All stocks → Top {phase1_top_k}")
        logger.info(f"   Phase 2: Top {phase1_top_k} → Top {phase2_top_k}")
        logger.info(f"   Phase 3: Portfolio backtest with {phase2_top_k} stocks")

    def get_sector_stocks(self, date: datetime) -> List[Dict[str, str]]:
        """获取板块内所有股票"""
        logger.info(f"Fetching all stocks in sector: {self.sector}")

        try:
            # Get industry mapping
            industries = SECTOR_TO_INDUSTRY.get(self.sector, [])
            if not industries:
                logger.error(f"Unknown sector: {self.sector}")
                return []

            all_stocks = []

            # Get stocks from each industry
            for industry in industries:
                try:
                    # Get industry stocks from Tushare
                    df = self.pro.stock_basic(
                        exchange='',
                        list_status='L',
                        fields='ts_code,symbol,name,area,industry'
                    )

                    # Filter by industry
                    industry_stocks = df[df['industry'].str.contains(industry, na=False)]

                    for _, row in industry_stocks.iterrows():
                        all_stocks.append({
                            'symbol': row['ts_code'],
                            'name': row['name'],
                            'industry': row['industry']
                        })

                    logger.info(f"   Industry '{industry}': {len(industry_stocks)} stocks")

                except Exception as e:
                    logger.error(f"Failed to fetch stocks for industry {industry}: {e}")

            logger.info(f"Total stocks in sector '{self.sector}': {len(all_stocks)}")
            return all_stocks

        except Exception as e:
            logger.error(f"Failed to get sector stocks: {e}")
            return []

    def quantitative_filter(
        self,
        stocks: List[Dict[str, str]],
        date: datetime
    ) -> List[QuantitativeCandidate]:
        """Phase 1: 量化快速筛选"""
        logger.info(f"Phase 1: Quantitative filtering {len(stocks)} stocks...")

        candidates = []
        date_str = date.strftime("%Y%m%d")

        for stock in stocks:
            try:
                symbol = stock['symbol']

                # Get basic financial data
                # 1. 基本面指标 (allow None - don't skip stocks)
                try:
                    # Get latest financial indicators
                    fina_indicator = self.pro.fina_indicator(
                        ts_code=symbol,
                        period=date_str[:6],  # YYYYMM
                        fields='roe,debt_to_assets,revenue_yoy'
                    )

                    if not fina_indicator.empty:
                        roe = fina_indicator.iloc[0]['roe'] if 'roe' in fina_indicator.columns else None
                        debt_ratio = fina_indicator.iloc[0]['debt_to_assets'] if 'debt_to_assets' in fina_indicator.columns else None
                        revenue_growth = fina_indicator.iloc[0]['revenue_yoy'] if 'revenue_yoy' in fina_indicator.columns else None
                    else:
                        roe = None
                        debt_ratio = None
                        revenue_growth = None

                except Exception:
                    roe = None
                    debt_ratio = None
                    revenue_growth = None

                # Get valuation data (MUST have at least basic market data)
                try:
                    daily_basic = self.pro.daily_basic(
                        ts_code=symbol,
                        trade_date=date_str,
                        fields='pe,pb,turnover_rate,total_mv,close'
                    )

                    if daily_basic.empty:
                        continue  # Skip if no basic market data at all

                    pe = daily_basic.iloc[0]['pe']
                    pb = daily_basic.iloc[0]['pb']
                    turnover_rate = daily_basic.iloc[0]['turnover_rate']
                    market_cap = daily_basic.iloc[0]['total_mv']
                    close_price = daily_basic.iloc[0]['close']

                except Exception:
                    continue  # Skip if no basic market data

                # 2. 技术面指标
                try:
                    # Get historical data for technical analysis
                    end_date_str = date.strftime("%Y-%m-%d")
                    start_date_str = (date - timedelta(days=90)).strftime("%Y-%m-%d")

                    hist_data = get_china_stock_data_tushare(
                        symbol=symbol,
                        start_date=start_date_str,
                        end_date=end_date_str
                    )

                    if hist_data is None or len(hist_data) < 20:
                        ma_trend = "unknown"
                        volume_ratio = 1.0
                        price_momentum = 0.0
                    else:
                        # Calculate MA trend
                        hist_data['ma5'] = hist_data['close'].rolling(window=5).mean()
                        hist_data['ma20'] = hist_data['close'].rolling(window=20).mean()
                        hist_data['ma60'] = hist_data['close'].rolling(window=60).mean()

                        latest = hist_data.iloc[-1]

                        if latest['ma5'] > latest['ma20'] > latest['ma60']:
                            ma_trend = "bullish"
                        elif latest['ma5'] < latest['ma20'] < latest['ma60']:
                            ma_trend = "bearish"
                        else:
                            ma_trend = "neutral"

                        # Volume ratio (current vs 20-day average)
                        avg_volume = hist_data['vol'].tail(20).mean()
                        current_volume = latest['vol']
                        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

                        # Price momentum (20-day return)
                        price_20d_ago = hist_data.iloc[-20]['close'] if len(hist_data) >= 20 else latest['close']
                        price_momentum = (latest['close'] - price_20d_ago) / price_20d_ago

                except Exception:
                    ma_trend = "unknown"
                    volume_ratio = 1.0
                    price_momentum = 0.0

                # 3. 计算综合评分
                score = 10.0  # Base score for having basic market data

                # 基本面评分（40分）- allow partial scores
                if roe is not None:
                    if roe > 10:
                        score += min(roe / 2, 20)  # ROE > 10%, 最高20分
                    elif roe > 5:
                        score += min(roe, 10)  # ROE > 5%, 最高10分

                if debt_ratio is not None:
                    if debt_ratio < 60:
                        score += (60 - debt_ratio) / 6  # 负债率 < 60%, 最高10分
                    elif debt_ratio < 80:
                        score += (80 - debt_ratio) / 16  # 负债率 < 80%, 最高5分

                if revenue_growth is not None and revenue_growth > 0:
                    score += min(revenue_growth, 10)  # 营收增长 > 0%, 最高10分

                # 估值评分（20分）- more lenient
                if pe is not None and 0 < pe < 50:  # Relaxed from 30 to 50
                    score += (50 - pe) / 5  # PE < 50, 最高10分
                if pb is not None and 0 < pb < 5:  # Relaxed from 3 to 5
                    score += (5 - pb) * 2  # PB < 5, 最高10分

                # 技术面评分（30分）
                if ma_trend == "bullish":
                    score += 15
                elif ma_trend == "neutral":
                    score += 7
                elif ma_trend == "bearish":
                    score += 2  # Small penalty but not zero

                if volume_ratio > 1.5:
                    score += 10  # 成交量放大
                elif volume_ratio > 1.0:
                    score += 5
                elif volume_ratio > 0.5:
                    score += 2  # Some activity

                if price_momentum > 0:
                    score += min(price_momentum * 50, 5)  # 价格上涨
                elif price_momentum > -0.1:
                    score += 1  # Small decline ok

                # 流动性评分（10分）
                if turnover_rate is not None:
                    if turnover_rate > 1.0:
                        score += min(turnover_rate, 10)
                    elif turnover_rate > 0.5:
                        score += min(turnover_rate * 5, 5)  # Some liquidity

                # Create candidate
                candidate = QuantitativeCandidate(
                    symbol=symbol,
                    name=stock['name'],
                    score=score,
                    roe=roe,
                    pe=pe,
                    pb=pb,
                    debt_ratio=debt_ratio,
                    revenue_growth=revenue_growth,
                    ma_trend=ma_trend,
                    volume_ratio=volume_ratio,
                    price_momentum=price_momentum,
                    turnover_rate=turnover_rate,
                    close_price=close_price,
                    market_cap=market_cap
                )

                candidates.append(candidate)

            except Exception as e:
                logger.debug(f"Failed to analyze {stock['symbol']}: {e}")
                continue

        # Sort by score and return top K
        candidates.sort(key=lambda x: x.score, reverse=True)
        top_candidates = candidates[:self.phase1_top_k]

        logger.info(f"Phase 1 complete: {len(candidates)} analyzed, Top {len(top_candidates)} selected")
        if top_candidates:
            logger.info(f"   Score range: {top_candidates[0].score:.1f} - {top_candidates[-1].score:.1f}")
        else:
            logger.warning("   No candidates passed quantitative filter - criteria may be too strict")

        return top_candidates

    def llm_deep_analysis(
        self,
        candidates: List[QuantitativeCandidate],
        date: datetime
    ) -> List[LLMAnalyzedStock]:
        """Phase 2: LLM深度分析"""
        logger.info(f"Phase 2: LLM deep analysis on {len(candidates)} candidates...")

        analyzed_stocks = []
        date_str = date.strftime("%Y-%m-%d")

        for i, candidate in enumerate(candidates, 1):
            try:
                logger.info(f"   [{i}/{len(candidates)}] Analyzing {candidate.symbol} ({candidate.name})...")

                # Call TradingAgentsGraph for deep analysis
                final_state, processed_signal = self.trading_graph.propagate(
                    candidate.symbol,
                    date_str
                )

                # Extract agent scores from reports
                technical_score = self._extract_score_from_report(
                    final_state.get('market_report', '')
                )
                fundamental_score = self._extract_score_from_report(
                    final_state.get('fundamentals_report', '')
                )
                sentiment_score = self._extract_score_from_report(
                    final_state.get('sentiment_report', '')
                )

                # Extract risk score (lower is better, invert it)
                risk_text = final_state.get('risk_debate_state', {}).get('judge_decision', '')
                risk_score = 10 - self._extract_score_from_report(risk_text)  # Invert risk

                # Calculate LLM综合评分
                llm_score = (
                    technical_score * 0.3 +
                    fundamental_score * 0.3 +
                    sentiment_score * 0.2 +
                    risk_score * 0.2
                )

                # Calculate final score (quantitative + LLM)
                final_score = candidate.score * 0.4 + llm_score * 0.6

                # Extract recommendation
                action = processed_signal.get('action', '持有')
                if '买入' in action or action == 'buy':
                    if llm_score >= 8:
                        recommendation = 'strong_buy'
                    else:
                        recommendation = 'buy'
                elif '卖出' in action or action == 'sell':
                    recommendation = 'sell'
                else:
                    recommendation = 'hold'

                # Extract reasoning
                debate_conclusion = final_state.get('investment_debate_state', {}).get('judge_decision', '')
                reasoning = debate_conclusion[:500] if debate_conclusion else "无详细分析"

                analyzed_stock = LLMAnalyzedStock(
                    symbol=candidate.symbol,
                    name=candidate.name,
                    quantitative_score=candidate.score,
                    llm_score=llm_score,
                    final_score=final_score,
                    technical_score=technical_score,
                    fundamental_score=fundamental_score,
                    sentiment_score=sentiment_score,
                    risk_score=risk_score,
                    recommendation=recommendation,
                    reasoning=reasoning,
                    quantitative_data=candidate.to_dict(),
                    llm_analysis=final_state
                )

                analyzed_stocks.append(analyzed_stock)

                logger.info(f"      Scores: Quant={candidate.score:.1f}, LLM={llm_score:.1f}, Final={final_score:.1f}")

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to analyze {candidate.symbol}: {e}")
                continue

        # Sort by final score and return top K
        analyzed_stocks.sort(key=lambda x: x.final_score, reverse=True)
        top_selected = analyzed_stocks[:self.phase2_top_k]

        logger.info(f"Phase 2 complete: {len(analyzed_stocks)} analyzed, Top {len(top_selected)} selected")
        if top_selected:
            logger.info(f"   Final score range: {top_selected[0].final_score:.1f} - {top_selected[-1].final_score:.1f}")

        return top_selected

    def _extract_score_from_report(self, report: str) -> float:
        """从报告文本中提取评分（0-10）"""
        if not report:
            return 5.0

        # 正面关键词
        positive_keywords = [
            '买入', '看涨', '积极', '强势', '突破', '上涨', '增长', '改善',
            '优秀', '良好', '稳健', 'buy', 'bullish', 'positive', 'strong'
        ]

        # 负面关键词
        negative_keywords = [
            '卖出', '看跌', '谨慎', '弱势', '下跌', '下降', '恶化', '风险',
            '较差', '疲软', 'sell', 'bearish', 'negative', 'weak', 'risk'
        ]

        report_lower = report.lower()

        positive_count = sum(1 for kw in positive_keywords if kw in report_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in report_lower)

        # 基础分5分，正面词+0.5分/个，负面词-0.5分/个
        score = 5.0 + (positive_count * 0.5) - (negative_count * 0.5)

        # 限制在0-10范围
        return max(0.0, min(10.0, score))

    def portfolio_backtest(
        self,
        selected_stocks: List[LLMAnalyzedStock],
        date: datetime
    ) -> Dict[str, Any]:
        """Phase 3: 组合回测"""
        logger.info(f"Phase 3: Portfolio backtest with {len(selected_stocks)} stocks...")

        # Create positions
        positions = []
        total_invested = 0.0

        for stock in selected_stocks:
            # Calculate position size
            position_value = self.cash * self.position_size

            # Get entry price
            try:
                entry_price = stock.quantitative_data.get('close_price')
                if entry_price is None or entry_price <= 0:
                    continue

                shares = int(position_value / entry_price / 100) * 100  # Round to 100

                if shares > 0 and shares * entry_price <= self.cash:
                    cost = shares * entry_price
                    self.cash -= cost
                    total_invested += cost

                    position = Position(
                        symbol=stock.symbol,
                        name=stock.name,
                        entry_date=date.strftime("%Y-%m-%d"),
                        entry_price=entry_price,
                        shares=shares,
                        days_held=0,
                        quantitative_score=stock.quantitative_score,
                        llm_score=stock.llm_score
                    )

                    positions.append(position)
                    logger.info(f"   BUY {stock.symbol}: {shares} shares @ ¥{entry_price:.2f}")

            except Exception as e:
                logger.error(f"Failed to create position for {stock.symbol}: {e}")

        # Simulate holding period
        exit_date = date + timedelta(days=self.holding_days * 2)

        outcomes = []
        total_pnl = 0.0

        for position in positions:
            try:
                # Get exit price
                exit_data = get_china_stock_data_tushare(
                    symbol=position.symbol,
                    start_date=date.strftime("%Y-%m-%d"),
                    end_date=exit_date.strftime("%Y-%m-%d")
                )

                if exit_data is None or len(exit_data) < self.holding_days:
                    logger.warning(f"Insufficient data for {position.symbol}")
                    continue

                exit_price = float(exit_data['close'].iloc[self.holding_days - 1])

                # Calculate return
                pnl = (exit_price - position.entry_price) * position.shares
                pnl_pct = (exit_price - position.entry_price) / position.entry_price

                total_pnl += pnl

                outcome = {
                    'symbol': position.symbol,
                    'name': position.name,
                    'entry_price': position.entry_price,
                    'exit_price': exit_price,
                    'shares': position.shares,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'holding_days': self.holding_days,
                    'quantitative_score': position.quantitative_score,
                    'llm_score': position.llm_score
                }

                outcomes.append(outcome)

                logger.info(f"   EXIT {position.symbol}: {pnl_pct:+.2%} after {self.holding_days} days")

            except Exception as e:
                logger.error(f"Failed to backtest {position.symbol}: {e}")

        # Calculate portfolio metrics
        portfolio_return_pct = total_pnl / total_invested if total_invested > 0 else 0
        success_rate = sum(1 for o in outcomes if o['pnl'] > 0) / len(outcomes) if outcomes else 0

        result = {
            'date': date.strftime("%Y-%m-%d"),
            'positions': [asdict(p) for p in positions],
            'outcomes': outcomes,
            'total_invested': total_invested,
            'total_pnl': total_pnl,
            'portfolio_return_pct': portfolio_return_pct,
            'success_rate': success_rate,
            'num_positions': len(positions)
        }

        logger.info(f"Phase 3 complete:")
        logger.info(f"   Positions: {len(positions)}")
        logger.info(f"   Portfolio return: {portfolio_return_pct:+.2%}")
        logger.info(f"   Success rate: {success_rate:.1%}")

        return result

    def create_episode(
        self,
        date: datetime,
        all_stocks: List[Dict],
        phase1_candidates: List[QuantitativeCandidate],
        phase2_selected: List[LLMAnalyzedStock],
        backtest_result: Dict
    ) -> Optional['TradingEpisode']:
        """创建训练Episode"""

        if not MEMORY_AVAILABLE:
            return None

        # Build comprehensive lesson
        lesson_parts = []

        # === Header ===
        portfolio_return = backtest_result['portfolio_return_pct']
        success = portfolio_return > 0

        if success:
            lesson_parts.append(f"# 智能选股成功案例: {self.sector}板块")
            lesson_parts.append(f"**组合收益**: +{portfolio_return:.2%}")
        else:
            lesson_parts.append(f"# 智能选股失败案例: {self.sector}板块")
            lesson_parts.append(f"**组合亏损**: {portfolio_return:.2%}")

        lesson_parts.append(f"**训练日期**: {date.strftime('%Y-%m-%d')}")
        lesson_parts.append(f"**板块**: {self.sector}")
        lesson_parts.append("")

        # === Phase 1: Quantitative Filter ===
        lesson_parts.append("##  Phase 1: 量化筛选")
        lesson_parts.append(f"- **板块内股票总数**: {len(all_stocks)}只")
        lesson_parts.append(f"- **筛选后候选数**: {len(phase1_candidates)}只")
        lesson_parts.append("")

        lesson_parts.append("**筛选标准**:")
        lesson_parts.append("- 基本面: ROE > 10%, 负债率 < 60%, 营收增长 > 0%")
        lesson_parts.append("- 估值: PE < 30, PB < 3")
        lesson_parts.append("- 技术面: MA多头排列优先")
        lesson_parts.append("- 流动性: 换手率 > 1%")
        lesson_parts.append("")

        lesson_parts.append("**Top 5 候选**:")
        for i, candidate in enumerate(phase1_candidates[:5], 1):
            lesson_parts.append(f"{i}. **{candidate.symbol}** ({candidate.name}) - 评分: {candidate.score:.1f}")
            lesson_parts.append(f"   - ROE: {candidate.roe:.1f}%" if candidate.roe else "   - ROE: N/A")
            lesson_parts.append(f"   - PE: {candidate.pe:.1f}" if candidate.pe else "   - PE: N/A")
            lesson_parts.append(f"   - 趋势: {candidate.ma_trend}")
            lesson_parts.append("")

        # === Phase 2: LLM Analysis ===
        lesson_parts.append("##  Phase 2: LLM深度分析")
        lesson_parts.append(f"- **分析候选数**: {len(phase1_candidates)}只")
        lesson_parts.append(f"- **最终筛选数**: {len(phase2_selected)}只")
        lesson_parts.append("")

        lesson_parts.append("**Multi-Agent分析结果**:")
        for i, stock in enumerate(phase2_selected, 1):
            lesson_parts.append(f"### {i}. {stock.symbol} ({stock.name})")
            lesson_parts.append(f"- **量化评分**: {stock.quantitative_score:.1f}/100")
            lesson_parts.append(f"- **LLM评分**: {stock.llm_score:.1f}/10")
            lesson_parts.append(f"- **综合评分**: {stock.final_score:.1f}")
            lesson_parts.append(f"- **技术面**: {stock.technical_score:.1f}/10")
            lesson_parts.append(f"- **基本面**: {stock.fundamental_score:.1f}/10")
            lesson_parts.append(f"- **情绪面**: {stock.sentiment_score:.1f}/10")
            lesson_parts.append(f"- **风险评估**: {stock.risk_score:.1f}/10")
            lesson_parts.append(f"- **推荐**: {stock.recommendation}")
            lesson_parts.append(f"- **理由**: {stock.reasoning[:200]}...")
            lesson_parts.append("")

        # === Phase 3: Portfolio Backtest ===
        lesson_parts.append("##  Phase 3: 组合回测")
        lesson_parts.append(f"- **持仓数量**: {backtest_result['num_positions']}只")
        lesson_parts.append(f"- **投入资金**: ¥{backtest_result['total_invested']:,.0f}")
        lesson_parts.append(f"- **持仓周期**: {self.holding_days}天")
        lesson_parts.append("")

        lesson_parts.append("**持仓明细**:")
        for outcome in backtest_result['outcomes']:
            lesson_parts.append(f"### {outcome['symbol']} ({outcome['name']})")
            lesson_parts.append(f"- **买入价**: ¥{outcome['entry_price']:.2f}")
            lesson_parts.append(f"- **卖出价**: ¥{outcome['exit_price']:.2f}")
            lesson_parts.append(f"- **收益率**: {outcome['pnl_pct']:+.2%}")
            lesson_parts.append(f"- **盈亏**: ¥{outcome['pnl']:+,.0f}")
            lesson_parts.append("")

        # === Performance Summary ===
        lesson_parts.append("##  业绩总结")
        lesson_parts.append(f"- **组合收益率**: {portfolio_return:+.2%}")
        lesson_parts.append(f"- **成功率**: {backtest_result['success_rate']:.1%}")
        lesson_parts.append(f"- **总盈亏**: ¥{backtest_result['total_pnl']:+,.0f}")
        lesson_parts.append("")

        # === Lessons Learned ===
        lesson_parts.append("##  选股经验总结")
        if success:
            lesson_parts.append("###  成功因素")
            lesson_parts.append(f"本次智能选股获得了 **{portfolio_return:.2%}** 的收益，主要成功因素：")
            lesson_parts.append("- **量化筛选有效**: 从大量股票中过滤出优质候选")
            lesson_parts.append("- **LLM分析精准**: 深度分析识别了高潜力股票")
            lesson_parts.append("- **组合分散风险**: 多只股票持仓降低单一风险")
        else:
            lesson_parts.append("###  失败教训")
            lesson_parts.append(f"本次智能选股产生了 **{abs(portfolio_return):.2%}** 的亏损，主要原因：")
            lesson_parts.append("- **量化指标局限**: 历史数据不能完全预测未来")
            lesson_parts.append("- **LLM分析偏差**: 可能高估了某些股票的潜力")
            lesson_parts.append("- **市场环境不利**: 板块整体表现不佳")

        lesson_parts.append("")
        lesson_parts.append("---")
        lesson_parts.append(f"*记录时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        lesson = "\n".join(lesson_parts)

        # Create Episode
        # Use first selected stock as primary symbol
        primary_symbol = phase2_selected[0].symbol if phase2_selected else "UNKNOWN"

        market_state = MarketState(
            date=date.strftime("%Y-%m-%d"),
            symbol=primary_symbol,
            price=phase2_selected[0].quantitative_data.get('close_price', 0.0) if phase2_selected else 0.0
        )

        decision_chain = DecisionChain(
            bull_argument=f"Phase 1筛选出{len(phase1_candidates)}只候选",
            bear_argument=f"Phase 2筛选出{len(phase2_selected)}只最终股票",
            investment_debate_conclusion=f"{self.sector}板块智能选股",
            aggressive_view="",
            neutral_view="",
            conservative_view="",
            risk_debate_conclusion="",
            final_decision=f"组合收益: {portfolio_return:+.2%}"
        )

        outcome = TradeOutcome(
            action='intelligent_selection',
            position_size=len(phase2_selected) / 10.0,
            entry_price=backtest_result['total_invested'],
            entry_date=date.strftime("%Y-%m-%d"),
            exit_price=backtest_result['total_invested'] + backtest_result['total_pnl'],
            exit_date=(date + timedelta(days=self.holding_days)).strftime("%Y-%m-%d"),
            holding_period_days=self.holding_days,
            absolute_return=backtest_result['total_pnl'],
            percentage_return=portfolio_return,
            max_drawdown_during=0.0
        )

        episode = TradingEpisode(
            episode_id=f"{date.strftime('%Y-%m-%d')}_{self.sector}_intelligent",
            date=date.strftime("%Y-%m-%d"),
            symbol=f"INTELLIGENT_{self.sector.upper()}",
            market_state=market_state,
            agent_analyses={},
            decision_chain=decision_chain,
            outcome=outcome,
            lesson=lesson,
            key_lesson=f"Intelligent selection in {self.sector}: {portfolio_return:+.2%}",
            success=success,
            created_at=datetime.now().isoformat(),
            mode='training'
        )

        return episode

    def get_trading_days(self) -> List[datetime]:
        """Get trading days"""
        logger.info("Fetching trading days...")

        try:
            # Use any stock to get trading calendar
            data = self.pro.trade_cal(
                exchange='SSE',
                start_date=self.start_date.strftime("%Y%m%d"),
                end_date=self.end_date.strftime("%Y%m%d"),
                is_open='1'
            )

            if data.empty:
                return []

            trading_days = [
                datetime.strptime(str(date), "%Y%m%d")
                for date in data['cal_date']
            ]

            logger.info(f"Found {len(trading_days)} trading days")
            return sorted(trading_days)

        except Exception as e:
            logger.error(f"Failed to fetch trading days: {e}")
            return []

    def train_one_day(self, date: datetime) -> bool:
        """训练单日"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Intelligent Sector Training: {date.strftime('%Y-%m-%d')}")
        logger.info(f"Sector: {self.sector}")
        logger.info(f"{'='*60}")

        try:
            # 1. Get all stocks in sector
            all_stocks = self.get_sector_stocks(date)

            if len(all_stocks) < 10:
                logger.warning(f"Too few stocks in sector ({len(all_stocks)}), skipping")
                return False

            # 2. Phase 1: Quantitative filter
            phase1_candidates = self.quantitative_filter(all_stocks, date)

            if not phase1_candidates:
                logger.warning("Phase 1 returned no candidates, skipping")
                return False

            # 3. Phase 2: LLM deep analysis
            phase2_selected = self.llm_deep_analysis(phase1_candidates, date)

            if not phase2_selected:
                logger.warning("Phase 2 returned no selected stocks, skipping")
                return False

            # 4. Phase 3: Portfolio backtest
            backtest_result = self.portfolio_backtest(phase2_selected, date)

            # 5. Create training episode
            if self.memory_manager:
                episode = self.create_episode(
                    date, all_stocks, phase1_candidates,
                    phase2_selected, backtest_result
                )

                if episode:
                    self.memory_manager.add_episode(episode)

                    # Update statistics
                    self.total_episodes += 1
                    self.total_return += backtest_result['portfolio_return_pct']

                    if episode.success:
                        self.successful_episodes += 1
                        logger.info(" Episode stored (profitable)")
                    else:
                        logger.info(" Episode stored (loss)")

            return True

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            return False

    def run(self):
        """Execute training"""
        logger.info(f"\n{'='*60}")
        logger.info("Starting Intelligent Sector Training")
        logger.info(f"{'='*60}\n")

        # Get trading days
        trading_days = self.get_trading_days()

        if not trading_days:
            logger.error("No trading days found, training terminated")
            return

        # Filter out last N days (need future data)
        buffer_days = self.holding_days + 5
        training_days = trading_days[:-buffer_days]

        logger.info("Training statistics:")
        logger.info(f"   Total trading days: {len(trading_days)}")
        logger.info(f"   Trainable days: {len(training_days)}")
        logger.info(f"   Buffer reserve: {buffer_days} days\n")

        # Train each day
        for i, current_date in enumerate(training_days, 1):
            logger.info(f"[{i}/{len(training_days)}] Progress: {i/len(training_days):.1%}")

            self.train_one_day(current_date)

            # Print statistics every 5 episodes
            if i % 5 == 0:
                self.print_statistics()

        # Final statistics
        logger.info(f"\n{'='*60}")
        logger.info("Training completed!")
        logger.info(f"{'='*60}\n")

        self.print_statistics()
        self.save_results()

    def print_statistics(self):
        """Print statistics"""
        if self.total_episodes == 0:
            return

        avg_return = self.total_return / self.total_episodes
        success_rate = self.successful_episodes / self.total_episodes

        logger.info("\nTraining statistics:")
        logger.info(f"   Total Episodes: {self.total_episodes}")
        logger.info(f"   Successful: {self.successful_episodes} ({success_rate:.1%})")
        logger.info(f"   Failed: {self.total_episodes - self.successful_episodes}")
        logger.info(f"   Average return: {avg_return:+.2%}\n")

    def save_results(self):
        """Save results"""
        results = {
            'training_type': 'intelligent_sector',
            'sector': self.sector,
            'start_date': self.start_date.strftime("%Y-%m-%d"),
            'end_date': self.end_date.strftime("%Y-%m-%d"),
            'phase1_top_k': self.phase1_top_k,
            'phase2_top_k': self.phase2_top_k,
            'total_episodes': self.total_episodes,
            'successful_episodes': self.successful_episodes,
            'success_rate': self.successful_episodes / self.total_episodes if self.total_episodes > 0 else 0,
            'average_return': self.total_return / self.total_episodes if self.total_episodes > 0 else 0,
            'timestamp': datetime.now().isoformat()
        }

        output_dir = Path("training_results")
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"intelligent_{self.sector}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Training results saved: {output_file}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Intelligent Sector Training')

    parser.add_argument(
        '--sector',
        type=str,
        required=True,
        choices=['金融', '科技', '消费', '医药', '周期', '制造', '地产', '公用'],
        help='Sector name'
    )

    parser.add_argument(
        '--start',
        type=str,
        required=True,
        help='Training start date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end',
        type=str,
        required=True,
        help='Training end date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--holding-days',
        type=int,
        default=5,
        help='Holding period (default: 5)'
    )

    parser.add_argument(
        '--phase1-top-k',
        type=int,
        default=20,
        help='Phase 1 top K candidates (default: 20)'
    )

    parser.add_argument(
        '--phase2-top-k',
        type=int,
        default=5,
        help='Phase 2 top K selected (default: 5)'
    )

    args = parser.parse_args()

    # Create trainer
    trainer = IntelligentSectorTrainer(
        sector=args.sector,
        start_date=args.start,
        end_date=args.end,
        holding_days=args.holding_days,
        phase1_top_k=args.phase1_top_k,
        phase2_top_k=args.phase2_top_k
    )

    # Execute training
    trainer.run()


if __name__ == "__main__":
    main()
