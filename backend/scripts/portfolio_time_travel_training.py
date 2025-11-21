# -*- coding: utf-8 -*-
"""
Portfolio-Based Time Travel Training Script

Implements portfolio management training with:
- Multi-stock pool (5 stocks across 5 sectors)
- Portfolio decisions (up to 5 positions)
- Sector rotation experience
- Stock selection within sectors
- Portfolio-level lessons

Usage:
    python scripts/portfolio_time_travel_training.py --start 2024-07-01 --end 2024-08-31 --holding-days 5
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import argparse
import json
import logging
from dataclasses import dataclass

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

# Import TaskMonitor for checkpoint support
from tradingagents.utils.task_monitor import get_task_monitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# Stock pool - Phase 1: 5 stocks (1 per sector)
STOCK_POOL = {
    "金融": "601318.SH",  # 中国平安
    "科技": "000063.SZ",  # 中兴通讯
    "消费": "600519.SH",  # 贵州茅台
    "医药": "600276.SH",  # 恒瑞医药
    "周期": "600019.SH",  # 宝钢股份
}


@dataclass
class Position:
    """持仓"""
    symbol: str
    sector: str
    entry_date: str
    entry_price: float
    shares: int
    days_held: int


@dataclass
class PortfolioState:
    """组合状态"""
    date: str
    positions: List[Position]
    cash: float
    total_value: float

    def get_position_count(self) -> int:
        return len(self.positions)

    def has_position(self, symbol: str) -> bool:
        return any(p.symbol == symbol for p in self.positions)

    def get_position(self, symbol: str) -> Optional[Position]:
        for p in self.positions:
            if p.symbol == symbol:
                return p
        return None


@dataclass
class PortfolioDecision:
    """组合决策"""
    date: str
    sector_analysis: Dict[str, Any]  # 板块分析
    stock_candidates: List[Dict[str, Any]]  # 股票候选
    actions: List[Dict[str, Any]]  # 具体操作 (buy/sell/hold)
    portfolio_before: PortfolioState
    portfolio_after: PortfolioState


class PortfolioTimeTravelTrainer:
    """Portfolio Time Travel Trainer"""

    def __init__(
        self,
        start_date: str,
        end_date: str,
        holding_days: int = 5,
        max_positions: int = 5,
        initial_cash: float = 1000000.0,  # 100万初始资金
        position_size: float = 0.2,  # 每只20%仓位
        config: Dict[str, Any] = None
    ):
        """
        Initialize Portfolio Trainer

        Args:
            start_date: Training start date (YYYY-MM-DD)
            end_date: Training end date (YYYY-MM-DD)
            holding_days: Default holding period (days)
            max_positions: Maximum concurrent positions
            initial_cash: Initial cash (RMB)
            position_size: Position size per stock (0.0-1.0)
            config: TradingAgents configuration
        """
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.holding_days = holding_days
        self.max_positions = max_positions
        self.initial_cash = initial_cash
        self.position_size = position_size
        self.config = config or DEFAULT_CONFIG.copy()

        # Initialize TradingAgentsGraph
        logger.info("Initializing TradingAgents system...")
        self.trading_graph = TradingAgentsGraph(config=self.config)

        # TaskMonitor for checkpoint support
        self.task_monitor = get_task_monitor()
        self.task_id = f"portfolio_tt_{start_date}_{end_date}"

        # Initialize Memory Bank
        self.memory_manager = None
        if MEMORY_AVAILABLE:
            logger.info("Initializing Memory Bank (TRAINING mode: read/write)...")
            self.memory_manager = MemoryManager(
                mode=MemoryMode.TRAINING,
                config=self.config
            )

        # Portfolio state
        self.portfolio = PortfolioState(
            date=start_date,
            positions=[],
            cash=initial_cash,
            total_value=initial_cash
        )

        # Statistics
        self.total_episodes = 0
        self.successful_episodes = 0
        self.failed_episodes = 0
        self.total_return = 0.0

        logger.info("Portfolio Time Travel Trainer initialized")
        logger.info(f"   Stock pool: {len(STOCK_POOL)} stocks across {len(set(STOCK_POOL.keys()))} sectors")
        logger.info(f"   Time range: {start_date} to {end_date}")
        logger.info(f"   Max positions: {max_positions}")
        logger.info(f"   Position size: {position_size:.1%}")
        logger.info(f"   Initial cash: ¥{initial_cash:,.0f}")

    def get_trading_days(self) -> List[datetime]:
        """Get all trading days in the training period"""
        logger.info("Fetching trading days...")

        try:
            # Use first stock to get trading calendar
            first_symbol = list(STOCK_POOL.values())[0]

            data = get_china_stock_data_tushare(
                symbol=first_symbol,
                start_date=self.start_date.strftime("%Y-%m-%d"),
                end_date=self.end_date.strftime("%Y-%m-%d")
            )

            if data is None or data.empty:
                logger.error(f"CRITICAL: No data available for trading calendar")
                return []

            trading_days = [
                datetime.strptime(str(date)[:10], "%Y-%m-%d")
                for date in data['trade_date']
            ]

            logger.info(f"Found {len(trading_days)} real trading days")
            return sorted(trading_days)

        except Exception as e:
            logger.error(f"CRITICAL: Failed to fetch trading days: {e}")
            return []

    def get_current_price(self, symbol: str, date: datetime) -> Optional[float]:
        """Get current price for a symbol on a specific date"""
        try:
            data = get_china_stock_data_tushare(
                symbol=symbol,
                start_date=date.strftime("%Y-%m-%d"),
                end_date=date.strftime("%Y-%m-%d")
            )

            if data is None or data.empty:
                return None

            return float(data['close'].iloc[-1])

        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None

    def analyze_sector(
        self,
        sector: str,
        symbol: str,
        current_date: datetime
    ) -> Dict[str, Any]:
        """Analyze a sector/stock using multi-agent system"""
        try:
            logger.info(f"   Analyzing {sector}: {symbol}")

            # Run multi-agent analysis
            final_state, processed_signal = self.trading_graph.propagate(
                symbol,
                current_date.strftime("%Y-%m-%d")
            )

            # Extract recommendation
            action = processed_signal.get('action', '持有')
            direction = processed_signal.get('direction', 'hold')

            # Get current price
            price = self.get_current_price(symbol, current_date)

            return {
                'sector': sector,
                'symbol': symbol,
                'action': action,
                'direction': direction,
                'price': price,
                'final_state': final_state,
                'processed_signal': processed_signal
            }

        except Exception as e:
            logger.error(f"Analysis failed for {sector}/{symbol}: {e}")
            return {
                'sector': sector,
                'symbol': symbol,
                'action': '持有',
                'direction': 'hold',
                'price': None,
                'final_state': {},
                'processed_signal': {}
            }

    def make_portfolio_decisions(
        self,
        current_date: datetime,
        sector_analyses: List[Dict[str, Any]]
    ) -> PortfolioDecision:
        """Make portfolio management decisions"""

        actions = []

        # 1. Check existing positions - sell if holding period exceeded
        positions_to_keep = []
        for position in self.portfolio.positions:
            position.days_held += 1

            if position.days_held >= self.holding_days:
                # Sell position
                current_price = self.get_current_price(position.symbol, current_date)

                if current_price:
                    sell_value = position.shares * current_price
                    self.portfolio.cash += sell_value

                    pnl = (current_price - position.entry_price) * position.shares
                    pnl_pct = (current_price - position.entry_price) / position.entry_price

                    actions.append({
                        'action': 'sell',
                        'symbol': position.symbol,
                        'sector': position.sector,
                        'reason': f'持仓{position.days_held}天已到期',
                        'entry_price': position.entry_price,
                        'exit_price': current_price,
                        'shares': position.shares,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })

                    logger.info(f"      SELL {position.symbol}: {pnl_pct:+.2%} after {position.days_held} days")
                else:
                    # Keep if no price data
                    positions_to_keep.append(position)
            else:
                # Keep holding
                positions_to_keep.append(position)

        portfolio_before = PortfolioState(
            date=current_date.strftime("%Y-%m-%d"),
            positions=[p for p in self.portfolio.positions],
            cash=self.portfolio.cash,
            total_value=self.portfolio.total_value
        )

        # Update positions after sells
        self.portfolio.positions = positions_to_keep

        # 2. Consider new buys if we have space
        if len(self.portfolio.positions) < self.max_positions:
            # Filter buy candidates (not already holding)
            buy_candidates = [
                analysis for analysis in sector_analyses
                if (analysis['action'] in ['买入', 'buy'] or analysis['direction'] == 'long')
                and not self.portfolio.has_position(analysis['symbol'])
                and analysis['price'] is not None
            ]

            # Sort by strength (TODO: add scoring logic)
            buy_candidates.sort(key=lambda x: 1, reverse=True)

            # Buy until max_positions or out of candidates
            for candidate in buy_candidates:
                if len(self.portfolio.positions) >= self.max_positions:
                    break

                # Calculate position size
                position_value = self.portfolio.cash * self.position_size
                shares = int(position_value / candidate['price'] / 100) * 100  # Round to 100 shares

                if shares > 0 and shares * candidate['price'] <= self.portfolio.cash:
                    # Execute buy
                    cost = shares * candidate['price']
                    self.portfolio.cash -= cost

                    new_position = Position(
                        symbol=candidate['symbol'],
                        sector=candidate['sector'],
                        entry_date=current_date.strftime("%Y-%m-%d"),
                        entry_price=candidate['price'],
                        shares=shares,
                        days_held=0
                    )

                    self.portfolio.positions.append(new_position)

                    actions.append({
                        'action': 'buy',
                        'symbol': candidate['symbol'],
                        'sector': candidate['sector'],
                        'reason': f"选择{candidate['sector']}板块龙头",
                        'entry_price': candidate['price'],
                        'shares': shares,
                        'cost': cost
                    })

                    logger.info(f"      BUY {candidate['symbol']} ({candidate['sector']}): {shares} shares @ ¥{candidate['price']:.2f}")

        # 3. Calculate portfolio value
        position_value = sum(
            p.shares * (self.get_current_price(p.symbol, current_date) or p.entry_price)
            for p in self.portfolio.positions
        )
        self.portfolio.total_value = self.portfolio.cash + position_value

        portfolio_after = PortfolioState(
            date=current_date.strftime("%Y-%m-%d"),
            positions=[p for p in self.portfolio.positions],
            cash=self.portfolio.cash,
            total_value=self.portfolio.total_value
        )

        return PortfolioDecision(
            date=current_date.strftime("%Y-%m-%d"),
            sector_analysis={
                analysis['sector']: {
                    'symbol': analysis['symbol'],
                    'action': analysis['action'],
                    'price': analysis['price']
                }
                for analysis in sector_analyses
            },
            stock_candidates=[],
            actions=actions,
            portfolio_before=portfolio_before,
            portfolio_after=portfolio_after
        )

    def abstract_portfolio_lesson(
        self,
        decision: PortfolioDecision,
        sector_analyses: List[Dict[str, Any]]
    ) -> tuple[str, str, bool]:
        """Abstract comprehensive portfolio-level lesson"""

        # Calculate portfolio performance
        value_change = decision.portfolio_after.total_value - decision.portfolio_before.total_value
        pct_change = value_change / decision.portfolio_before.total_value if decision.portfolio_before.total_value > 0 else 0

        success = pct_change > 0.0

        lesson_parts = []

        # === Header ===
        if success:
            lesson_parts.append(f"# 组合管理成功案例")
            lesson_parts.append(f"**组合收益**: +{pct_change:.2%}")
        else:
            lesson_parts.append(f"# 组合管理失败案例")
            lesson_parts.append(f"**组合亏损**: {pct_change:.2%}")

        lesson_parts.append(f"**日期**: {decision.date}")
        lesson_parts.append(f"**持仓数**: {decision.portfolio_after.get_position_count()}/{self.max_positions}")
        lesson_parts.append("")

        # === Market Environment ===
        lesson_parts.append("##  市场环境")
        lesson_parts.append(f"- **组合总值**: ¥{decision.portfolio_before.total_value:,.0f} → ¥{decision.portfolio_after.total_value:,.0f}")
        lesson_parts.append(f"- **现金余额**: ¥{decision.portfolio_before.cash:,.0f} → ¥{decision.portfolio_after.cash:,.0f}")
        lesson_parts.append(f"- **持仓变化**: {decision.portfolio_before.get_position_count()}只 → {decision.portfolio_after.get_position_count()}只")
        lesson_parts.append("")

        # === Sector Analysis ===
        lesson_parts.append("##  板块分析")
        for analysis in sector_analyses:
            lesson_parts.append(f"### {analysis['sector']} - {analysis['symbol']}")
            lesson_parts.append(f"- **分析建议**: {analysis['action']}")
            lesson_parts.append(f"- **当前价格**: ¥{analysis['price']:.2f}" if analysis['price'] else "- **价格**: 无数据")
            lesson_parts.append("")

        # === Portfolio Actions ===
        lesson_parts.append("##  组合操作")
        if not decision.actions:
            lesson_parts.append("本日无交易操作（继续持有现有仓位）")
        else:
            for action in decision.actions:
                if action['action'] == 'buy':
                    lesson_parts.append(f"###  买入 {action['symbol']} ({action['sector']})")
                    lesson_parts.append(f"- **买入价格**: ¥{action['entry_price']:.2f}")
                    lesson_parts.append(f"- **买入数量**: {action['shares']} 股")
                    lesson_parts.append(f"- **投入资金**: ¥{action['cost']:,.0f}")
                    lesson_parts.append(f"- **决策理由**: {action['reason']}")
                elif action['action'] == 'sell':
                    lesson_parts.append(f"###  卖出 {action['symbol']} ({action['sector']})")
                    lesson_parts.append(f"- **卖出价格**: ¥{action['exit_price']:.2f}")
                    lesson_parts.append(f"- **卖出数量**: {action['shares']} 股")
                    lesson_parts.append(f"- **盈亏金额**: ¥{action['pnl']:+,.0f}")
                    lesson_parts.append(f"- **盈亏比例**: {action['pnl_pct']:+.2%}")
                    lesson_parts.append(f"- **决策理由**: {action['reason']}")
                lesson_parts.append("")

        # === Current Holdings ===
        lesson_parts.append("##  当前持仓")
        if not decision.portfolio_after.positions:
            lesson_parts.append("空仓（现金观望）")
        else:
            for pos in decision.portfolio_after.positions:
                current_price = next(
                    (a['price'] for a in sector_analyses if a['symbol'] == pos.symbol),
                    pos.entry_price
                )
                unrealized_pnl = (current_price - pos.entry_price) / pos.entry_price if current_price else 0

                lesson_parts.append(f"### {pos.symbol} ({pos.sector})")
                lesson_parts.append(f"- **持仓天数**: {pos.days_held} 天")
                lesson_parts.append(f"- **成本价**: ¥{pos.entry_price:.2f}")
                lesson_parts.append(f"- **当前价**: ¥{current_price:.2f}")
                lesson_parts.append(f"- **浮动盈亏**: {unrealized_pnl:+.2%}")
                lesson_parts.append("")

        # === Outcome Analysis ===
        lesson_parts.append("##  组合分析")
        if success:
            lesson_parts.append("###  成功因素")
            lesson_parts.append(f"本次组合管理获得了 **{pct_change:.2%}** 的收益，主要成功因素：")
            lesson_parts.append("")
            lesson_parts.append("- **板块选择合理**: 选择了正确的板块进行配置")
            lesson_parts.append("- **个股筛选得当**: 在板块内选择了优质个股")
            lesson_parts.append("- **仓位控制适度**: 分散投资降低单一股票风险")
        else:
            lesson_parts.append("###  失败原因")
            lesson_parts.append(f"本次组合管理产生了 **{abs(pct_change):.2%}** 的亏损，主要原因：")
            lesson_parts.append("")
            lesson_parts.append("- **板块选择失误**: 配置的板块表现不佳")
            lesson_parts.append("- **个股筛选欠佳**: 板块内未选择到强势个股")
            lesson_parts.append("- **时机把握不当**: 买入时机或持仓周期需要调整")

        lesson_parts.append("")

        # === Key Lessons ===
        lesson_parts.append("##  关键经验")
        if success:
            lesson_parts.append("- 分散投资策略有效降低了单一股票风险")
            lesson_parts.append("- 板块轮动把握了市场热点")
            lesson_parts.append("- 持仓周期控制得当，及时止盈")
        else:
            lesson_parts.append("- 需要提高板块选择的准确性")
            lesson_parts.append("- 个股筛选标准需要优化")
            lesson_parts.append("- 考虑动态调整持仓周期")

        lesson_parts.append("")
        lesson_parts.append("---")
        lesson_parts.append(f"*记录时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        lesson = "\n".join(lesson_parts)

        # Key lesson (for embedding)
        key_lesson = f"Portfolio {decision.date}: {pct_change:+.2%}, {len(decision.actions)} actions, {decision.portfolio_after.get_position_count()} positions"

        return lesson, key_lesson, success

    def train_one_day(self, current_date: datetime) -> bool:
        """Train one trading day with portfolio management"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Time Travel to: {current_date.strftime('%Y-%m-%d')}")
        logger.info(f"{'='*60}")

        try:
            # 1. Analyze all sectors
            logger.info("Analyzing all sectors...")
            sector_analyses = []

            for sector, symbol in STOCK_POOL.items():
                analysis = self.analyze_sector(sector, symbol, current_date)
                sector_analyses.append(analysis)

            # 2. Make portfolio decisions
            logger.info("Making portfolio decisions...")
            decision = self.make_portfolio_decisions(current_date, sector_analyses)

            logger.info(f"   Actions: {len(decision.actions)}")
            logger.info(f"   Portfolio value: ¥{decision.portfolio_after.total_value:,.0f}")

            # 3. Abstract lesson
            if decision.actions:  # Only create episode if there were actions
                logger.info("Abstracting portfolio lesson...")

                lesson, key_lesson, success = self.abstract_portfolio_lesson(
                    decision, sector_analyses
                )

                # 4. Store to Memory Bank (use first action's symbol as primary)
                if self.memory_manager and decision.actions:
                    primary_action = decision.actions[0]
                    primary_symbol = primary_action['symbol']

                    # Create synthetic outcome for memory system
                    value_change = decision.portfolio_after.total_value - decision.portfolio_before.total_value
                    pct_change = value_change / decision.portfolio_before.total_value

                    outcome = TradeOutcome(
                        action='portfolio',
                        position_size=len(decision.portfolio_after.positions) / self.max_positions,
                        entry_price=decision.portfolio_before.total_value,
                        entry_date=decision.date,
                        exit_price=decision.portfolio_after.total_value,
                        exit_date=decision.date,
                        holding_period_days=0,
                        absolute_return=value_change,
                        percentage_return=pct_change,
                        max_drawdown_during=0.0
                    )

                    market_state = MarketState(
                        date=decision.date,
                        symbol=primary_symbol,
                        price=primary_action.get('entry_price', 0.0)
                    )

                    decision_chain = DecisionChain(
                        bull_argument="Portfolio management",
                        bear_argument="Portfolio management",
                        investment_debate_conclusion="Multi-stock portfolio",
                        aggressive_view="",
                        neutral_view="",
                        conservative_view="",
                        risk_debate_conclusion="",
                        final_decision=f"{len(decision.actions)} portfolio actions"
                    )

                    episode = TradingEpisode(
                        episode_id=f"{decision.date}_portfolio",
                        date=decision.date,
                        symbol="PORTFOLIO",
                        market_state=market_state,
                        agent_analyses={},
                        decision_chain=decision_chain,
                        outcome=outcome,
                        lesson=lesson,
                        key_lesson=key_lesson,
                        success=success,
                        created_at=datetime.now().isoformat(),
                        mode='training'
                    )

                    self.memory_manager.add_episode(episode)

                    # Update statistics
                    self.total_episodes += 1
                    self.total_return += pct_change

                    if success:
                        self.successful_episodes += 1
                        logger.info("Episode stored (profitable)")
                    else:
                        self.failed_episodes += 1
                        logger.info("Episode stored (loss)")

                return True
            else:
                logger.info("No actions taken, skipping episode")
                return False

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            return False

    def run(self):
        """Execute complete portfolio training"""
        logger.info(f"\n{'='*60}")
        logger.info("Starting Portfolio Time Travel Training")
        logger.info(f"{'='*60}\n")

        # Get trading days
        trading_days = self.get_trading_days()

        if not trading_days:
            logger.error("No trading days found, training terminated")
            return

        # Filter out last N days (need future data for evaluation)
        buffer_days = self.holding_days + 5
        training_days = trading_days[:-buffer_days]

        logger.info("Training statistics:")
        logger.info(f"   Total trading days: {len(trading_days)}")
        logger.info(f"   Trainable days: {len(training_days)}")
        logger.info(f"   Buffer reserve: {buffer_days} days\n")

        # Check for existing checkpoint (resume support)
        start_idx = 0
        checkpoint = self.task_monitor.get_checkpoint(self.task_id)

        if checkpoint and checkpoint.status in ["RUNNING", "PAUSED"]:
            completed_steps = checkpoint.completed_steps
            logger.info(f"\n⏮️  发现检查点: {checkpoint.task_id}")
            logger.info(f"   上次进度: {checkpoint.progress:.1%} ({completed_steps}/{len(training_days)} days)")
            logger.info(f"   恢复训练从第 {completed_steps + 1} 天...\n")
            start_idx = completed_steps
            self.task_monitor.resume_task(self.task_id)
        else:
            # Start new task
            self.task_monitor.start_task(
                task_id=self.task_id,
                task_type="PORTFOLIO_TIME_TRAVEL",
                total_steps=len(training_days),
                metadata={
                    'start_date': self.start_date.strftime("%Y-%m-%d"),
                    'end_date': self.end_date.strftime("%Y-%m-%d"),
                    'holding_days': self.holding_days,
                    'max_positions': self.max_positions,
                    'stock_pool': list(STOCK_POOL.values())
                }
            )
            logger.info(f"🆕 创建新训练任务: {self.task_id}\n")

        # Train each day (resume from start_idx if needed)
        for i in range(start_idx, len(training_days)):
            current_date = training_days[i]
            day_num = i + 1

            logger.info(f"[{day_num}/{len(training_days)}] Progress: {day_num/len(training_days):.1%}")

            self.train_one_day(current_date)

            # Update checkpoint progress
            self.task_monitor.update_progress(
                task_id=self.task_id,
                current_step=f"Training day {current_date}",
                completed_steps=day_num,
                metadata_update={
                    'current_date': current_date,
                    'total_episodes': self.total_episodes,
                    'successful_episodes': self.successful_episodes,
                    'portfolio_value': self.portfolio.total_value
                }
            )

            # Print statistics every 10 episodes
            if day_num % 10 == 0:
                self.print_statistics()

        # Mark task as complete
        self.task_monitor.complete_task(
            self.task_id,
            final_metadata={
                'total_episodes': self.total_episodes,
                'successful_episodes': self.successful_episodes,
                'failed_episodes': self.failed_episodes,
                'final_portfolio_value': self.portfolio.total_value,
                'total_return_pct': (self.portfolio.total_value - self.initial_cash) / self.initial_cash
            }
        )

        # Final statistics
        logger.info(f"\n{'='*60}")
        logger.info("Training completed!")
        logger.info(f"{'='*60}\n")

        self.print_statistics()
        self.save_results()

    def print_statistics(self):
        """Print training statistics"""
        if self.total_episodes == 0:
            return

        avg_return = self.total_return / self.total_episodes
        success_rate = self.successful_episodes / self.total_episodes

        logger.info("\nTraining statistics:")
        logger.info(f"   Total Episodes: {self.total_episodes}")
        logger.info(f"   Successful: {self.successful_episodes} ({success_rate:.1%})")
        logger.info(f"   Failed: {self.failed_episodes} ({1-success_rate:.1%})")
        logger.info(f"   Average return: {avg_return:+.2%}")
        logger.info(f"   Current portfolio: {len(self.portfolio.positions)} positions")
        logger.info(f"   Portfolio value: ¥{self.portfolio.total_value:,.0f}\n")

    def save_results(self):
        """Save training results to JSON"""
        results = {
            'training_type': 'portfolio',
            'stock_pool': STOCK_POOL,
            'start_date': self.start_date.strftime("%Y-%m-%d"),
            'end_date': self.end_date.strftime("%Y-%m-%d"),
            'holding_days': self.holding_days,
            'max_positions': self.max_positions,
            'total_episodes': self.total_episodes,
            'successful_episodes': self.successful_episodes,
            'failed_episodes': self.failed_episodes,
            'success_rate': self.successful_episodes / self.total_episodes if self.total_episodes > 0 else 0,
            'average_return': self.total_return / self.total_episodes if self.total_episodes > 0 else 0,
            'final_portfolio_value': self.portfolio.total_value,
            'total_return_pct': (self.portfolio.total_value - self.initial_cash) / self.initial_cash,
            'timestamp': datetime.now().isoformat()
        }

        # Save to file
        output_dir = Path("training_results")
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"portfolio_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Training results saved: {output_file}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Portfolio Time Travel Training')

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
        help='Default holding period (default: 5 days)'
    )

    parser.add_argument(
        '--max-positions',
        type=int,
        default=5,
        help='Maximum concurrent positions (default: 5)'
    )

    parser.add_argument(
        '--initial-cash',
        type=float,
        default=1000000.0,
        help='Initial cash in RMB (default: 1000000)'
    )

    parser.add_argument(
        '--position-size',
        type=float,
        default=0.2,
        help='Position size per stock 0.0-1.0 (default: 0.2)'
    )

    args = parser.parse_args()

    # Create trainer
    trainer = PortfolioTimeTravelTrainer(
        start_date=args.start,
        end_date=args.end,
        holding_days=args.holding_days,
        max_positions=args.max_positions,
        initial_cash=args.initial_cash,
        position_size=args.position_size
    )

    # Execute training
    trainer.run()


if __name__ == "__main__":
    main()
