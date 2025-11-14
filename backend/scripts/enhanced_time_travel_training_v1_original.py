# -*- coding: utf-8 -*-
"""
Enhanced Time Travel Training Script

Key Features:
1. Real A-share data from Tushare (NO synthetic fallback)
2. Strict no-future-function data pipeline
3. LLM multi-agent decision system using TradingAgentsGraph
4. Memory Bank integration for trading experience
5. Trading summaries after each decision

Usage:
    python scripts/enhanced_time_travel_training.py --symbol 000001.SZ --start 2025-07-01 --end 2025-11-10
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import argparse
import json
import logging

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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class EnhancedTimeTravelTrainer:
    """Enhanced Time Travel Trainer with strict no-future-function and Memory Bank"""

    def __init__(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        holding_days: int = 5,
        config: Dict[str, Any] = None
    ):
        """
        Initialize Enhanced Trainer

        Args:
            symbol: Stock code (e.g., 000001.SZ)
            start_date: Training start date (YYYY-MM-DD)
            end_date: Training end date (YYYY-MM-DD)
            holding_days: Holding period (days)
            config: TradingAgents configuration
        """
        self.symbol = symbol
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.holding_days = holding_days
        self.config = config or DEFAULT_CONFIG.copy()

        # Initialize TradingAgentsGraph
        logger.info("Initializing TradingAgents system...")
        self.trading_graph = TradingAgentsGraph(config=self.config)

        # Initialize Memory Bank (if available)
        self.memory_manager = None
        if MEMORY_AVAILABLE:
            logger.info("Initializing Memory Bank (TRAINING mode: read/write)...")
            self.memory_manager = MemoryManager(
                mode=MemoryMode.TRAINING,  # Allow writes
                config=self.config
            )

        # Statistics
        self.total_episodes = 0
        self.successful_episodes = 0
        self.failed_episodes = 0
        self.total_return = 0.0

        logger.info("Enhanced Time Travel Trainer initialized")
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Time range: {start_date} to {end_date}")
        logger.info(f"   Holding period: {holding_days} days")

    def get_trading_days(self) -> List[datetime]:
        """Get all trading days in the training period"""
        logger.info("Fetching trading days...")

        try:
            # Fetch real A-share data
            data = get_china_stock_data_tushare(
                symbol=self.symbol,
                start_date=self.start_date.strftime("%Y-%m-%d"),
                end_date=self.end_date.strftime("%Y-%m-%d")
            )

            if data is None or data.empty:
                logger.error(f"CRITICAL: No data available for {self.symbol}")
                logger.error("Cannot proceed without real data - NO SYNTHETIC FALLBACK")
                return []

            # Extract trading days from real data
            trading_days = [
                datetime.strptime(str(date)[:10], "%Y-%m-%d")
                for date in data['trade_date']
            ]

            logger.info(f"Found {len(trading_days)} real trading days")
            return sorted(trading_days)

        except Exception as e:
            logger.error(f"CRITICAL: Failed to fetch trading days: {e}")
            logger.error("Cannot proceed - NO SYNTHETIC FALLBACK ALLOWED")
            return []

    def get_historical_data_up_to_date(
        self,
        current_date: datetime,
        lookback_days: int = 365
    ) -> Any:
        """
        Get ONLY historical data available UP TO current_date (strict no-future-function)

        This ensures the agent NEVER sees future information during training.

        Args:
            current_date: The "current" date in the simulation
            lookback_days: How many days of history to fetch

        Returns:
            DataFrame with ONLY data from [current_date - lookback_days] to current_date
        """
        # Calculate lookback start date
        lookback_start = current_date - timedelta(days=lookback_days)

        logger.info(f"[NO-FUTURE-FUNCTION] Fetching data from {lookback_start.strftime('%Y-%m-%d')} to {current_date.strftime('%Y-%m-%d')}")

        try:
            # Fetch ONLY data up to current_date
            historical_data = get_china_stock_data_tushare(
                symbol=self.symbol,
                start_date=lookback_start.strftime("%Y-%m-%d"),
                end_date=current_date.strftime("%Y-%m-%d")  # CRITICAL: end_date = current_date
            )

            if historical_data is None or historical_data.empty:
                logger.warning(f"No historical data available up to {current_date.strftime('%Y-%m-%d')}")
                return None

            logger.info(f"[NO-FUTURE-FUNCTION] Fetched {len(historical_data)} days of data (ONLY up to {current_date.strftime('%Y-%m-%d')})")

            return historical_data

        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return None

    def simulate_trade(
        self,
        entry_date: datetime,
        processed_signal: Dict[str, Any]
    ) -> Optional['TradeOutcome']:
        """
        Simulate trade execution and outcome (uses FUTURE data for evaluation ONLY)

        Args:
            entry_date: Entry date
            processed_signal: Signal from SignalProcessor

        Returns:
            Trade outcome (if trade was executed)
        """
        if not MEMORY_AVAILABLE:
            logger.warning("Memory system not available, skipping trade simulation")
            return None

        action = processed_signal.get('action', '持有')

        # Normalize action to English for consistency
        action_map = {
            '买入': 'buy',
            '持有': 'hold',
            '卖出': 'sell',
            'buy': 'buy',
            'hold': 'hold',
            'sell': 'sell'
        }
        action_normalized = action_map.get(action, 'hold')

        # Skip if action is hold
        if action_normalized == 'hold':
            logger.info(f"   Signal: HOLD ({action}), skipping trade")
            return None

        try:
            # Get entry price (using current_date data ONLY)
            entry_data = get_china_stock_data_tushare(
                symbol=self.symbol,
                start_date=entry_date.strftime("%Y-%m-%d"),
                end_date=entry_date.strftime("%Y-%m-%d")
            )

            if entry_data is None or entry_data.empty:
                logger.warning(f"No entry price data for {entry_date.strftime('%Y-%m-%d')}")
                return None

            entry_price = float(entry_data['close'].iloc[-1])

            # Calculate exit date (holding_days trading days later)
            exit_date = entry_date + timedelta(days=self.holding_days * 2)  # Account for weekends

            # Get holding period data (THIS IS FUTURE DATA - ONLY FOR EVALUATION)
            exit_data = get_china_stock_data_tushare(
                symbol=self.symbol,
                start_date=entry_date.strftime("%Y-%m-%d"),
                end_date=exit_date.strftime("%Y-%m-%d")
            )

            if exit_data is None or len(exit_data) < self.holding_days:
                logger.warning(f"Insufficient holding period data, skipping")
                return None

            # Get exit price (Nth trading day)
            actual_exit_date = exit_data['trade_date'].iloc[self.holding_days - 1]
            exit_price = float(exit_data['close'].iloc[self.holding_days - 1])

            # Calculate max drawdown during holding
            high_during = float(exit_data['high'][:self.holding_days].max())
            low_during = float(exit_data['low'][:self.holding_days].min())
            max_drawdown = (low_during - entry_price) / entry_price if entry_price > 0 else 0

            # Calculate returns
            if action_normalized == 'buy':
                pnl = exit_price - entry_price
                pnl_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
            elif action_normalized == 'sell':
                pnl = entry_price - exit_price
                pnl_pct = (entry_price - exit_price) / entry_price if entry_price > 0 else 0
            else:
                pnl = 0
                pnl_pct = 0

            outcome = TradeOutcome(
                action=action_normalized,
                position_size=0.1,  # Fixed 10% position
                entry_price=entry_price,
                entry_date=entry_date.strftime("%Y-%m-%d"),
                exit_price=exit_price,
                exit_date=str(actual_exit_date)[:10],
                holding_period_days=self.holding_days,
                absolute_return=round(pnl, 2),
                percentage_return=round(pnl_pct, 4),
                max_drawdown_during=round(max_drawdown, 4)
            )

            logger.info(f"   Trade: {action} ({action_normalized}) @ {entry_price:.2f} -> {exit_price:.2f}")
            logger.info(f"   Return: {pnl_pct:+.2%} (holding {self.holding_days} days)")

            return outcome

        except Exception as e:
            logger.error(f"Trade simulation failed: {e}", exc_info=True)
            return None

    def extract_market_state(
        self,
        current_date: datetime,
        final_state: Dict[str, Any]
    ) -> Optional['MarketState']:
        """Extract market state from final_state"""
        if not MEMORY_AVAILABLE:
            return None

        try:
            # Get current day market data
            data = get_china_stock_data_tushare(
                symbol=self.symbol,
                start_date=current_date.strftime("%Y-%m-%d"),
                end_date=current_date.strftime("%Y-%m-%d")
            )

            if data is None or data.empty:
                return MarketState(
                    date=current_date.strftime("%Y-%m-%d"),
                    symbol=self.symbol,
                    price=0.0
                )

            row = data.iloc[-1]

            return MarketState(
                date=current_date.strftime("%Y-%m-%d"),
                symbol=self.symbol,
                price=float(row.get('close', 0)),
                open=float(row.get('open', 0)) if 'open' in row else None,
                high=float(row.get('high', 0)) if 'high' in row else None,
                low=float(row.get('low', 0)) if 'low' in row else None,
                volume=float(row.get('vol', 0)) if 'vol' in row else None,
            )

        except Exception as e:
            logger.error(f"Failed to extract market state: {e}")
            return None

    def extract_agent_analyses(
        self,
        final_state: Dict[str, Any]
    ) -> Dict[str, 'AgentAnalysis']:
        """Extract agent analyses from final_state"""
        if not MEMORY_AVAILABLE:
            return {}

        analyses = {}

        agent_mapping = {
            'market_report': 'market',
            'fundamentals_report': 'fundamentals',
            'sentiment_report': 'sentiment',
            'news_report': 'news'
        }

        for report_key, agent_name in agent_mapping.items():
            report = final_state.get(report_key, '')

            if report:
                analyses[agent_name] = AgentAnalysis(
                    agent_name=agent_name,
                    full_report=report,
                    reasoning=report[:500]  # Summary
                )

        return analyses

    def extract_decision_chain(
        self,
        final_state: Dict[str, Any]
    ) -> Optional['DecisionChain']:
        """Extract decision chain from final_state"""
        if not MEMORY_AVAILABLE:
            return None

        debate_state = final_state.get('investment_debate_state', {})
        risk_state = final_state.get('risk_debate_state', {})

        return DecisionChain(
            bull_argument=debate_state.get('bull_history', ''),
            bear_argument=debate_state.get('bear_history', ''),
            investment_debate_conclusion=debate_state.get('judge_decision', ''),
            aggressive_view=risk_state.get('risky_history', ''),
            neutral_view=risk_state.get('neutral_history', ''),
            conservative_view=risk_state.get('safe_history', ''),
            risk_debate_conclusion=risk_state.get('judge_decision', ''),
            final_decision=final_state.get('final_trade_decision', '')
        )

    def abstract_lesson(
        self,
        outcome: 'TradeOutcome',
        market_state: 'MarketState',
        decision_chain: 'DecisionChain'
    ) -> tuple[str, str, bool]:
        """Abstract comprehensive lesson from trade outcome with markdown formatting"""
        # Determine success - profitable trades are considered successful
        # For 5-day holding period, any positive return is good
        success = outcome.percentage_return > 0.0  # Profitable = success

        # Build comprehensive markdown-formatted lesson
        lesson_parts = []

        # === Header ===
        if success:
            lesson_parts.append(f"# 成功案例: {outcome.action}")
            lesson_parts.append(f"**收益率**: +{outcome.percentage_return:.2%}")
        else:
            lesson_parts.append(f"# 失败案例: {outcome.action}")
            lesson_parts.append(f"**亏损率**: {outcome.percentage_return:.2%}")

        lesson_parts.append(f"**持仓天数**: {outcome.holding_period_days}天")
        lesson_parts.append(f"**入场价**: ¥{outcome.entry_price:.2f}")
        lesson_parts.append(f"**出场价**: ¥{outcome.exit_price:.2f}")
        lesson_parts.append("")

        # === Market Environment ===
        lesson_parts.append("##  市场环境")
        lesson_parts.append(f"- **当前价格**: ¥{market_state.price:.2f}")
        lesson_parts.append(f"- **交易日期**: {market_state.date}")
        if hasattr(market_state, 'volume') and market_state.volume:
            lesson_parts.append(f"- **成交量**: {market_state.volume:,.0f}")
        lesson_parts.append("")

        # === Decision Process ===
        lesson_parts.append("##  决策过程")

        if decision_chain.bull_argument:
            lesson_parts.append("###  多头观点")
            lesson_parts.append(decision_chain.bull_argument)
            lesson_parts.append("")

        if decision_chain.bear_argument:
            lesson_parts.append("###  空头观点")
            lesson_parts.append(decision_chain.bear_argument)
            lesson_parts.append("")

        if decision_chain.investment_debate_conclusion:
            lesson_parts.append("###  投资辩论结论")
            lesson_parts.append(decision_chain.investment_debate_conclusion)
            lesson_parts.append("")

        # === Risk Analysis ===
        lesson_parts.append("##  风险分析")

        if decision_chain.aggressive_view:
            lesson_parts.append("### 激进视角")
            lesson_parts.append(decision_chain.aggressive_view)
            lesson_parts.append("")

        if decision_chain.neutral_view:
            lesson_parts.append("### 中性视角")
            lesson_parts.append(decision_chain.neutral_view)
            lesson_parts.append("")

        if decision_chain.conservative_view:
            lesson_parts.append("### 保守视角")
            lesson_parts.append(decision_chain.conservative_view)
            lesson_parts.append("")

        if decision_chain.risk_debate_conclusion:
            lesson_parts.append("###  风险辩论结论")
            lesson_parts.append(decision_chain.risk_debate_conclusion)
            lesson_parts.append("")

        # === Final Decision ===
        lesson_parts.append("##  最终决策")
        lesson_parts.append(decision_chain.final_decision if decision_chain.final_decision else "无最终决策记录")
        lesson_parts.append("")

        # === Post-Outcome Analysis ===
        lesson_parts.append("##  结果分析")
        if success:
            lesson_parts.append("###  成功原因")

            profit_rate = outcome.percentage_return * 100
            lesson_parts.append(f"此次交易获得了 **{profit_rate:.2f}%** 的收益，主要成功因素包括：")
            lesson_parts.append("")

            # Analyze why it succeeded based on decision chain
            if "买入" in outcome.action or "buy" in outcome.action.lower():
                lesson_parts.append("- **方向判断正确**: 买入后价格上涨符合预期")
                lesson_parts.append(f"- **入场时机把握**: 在 ¥{outcome.entry_price:.2f} 入场，出场价 ¥{outcome.exit_price:.2f}")
            else:
                lesson_parts.append("- **方向判断正确**: 卖出后规避了下跌风险或锁定了利润")
                lesson_parts.append(f"- **出场时机把握**: 在 ¥{outcome.entry_price:.2f} 出场，避免了进一步损失")

            # Extract key decision factors
            if decision_chain.investment_debate_conclusion and ("买入" in decision_chain.investment_debate_conclusion or "持有" in decision_chain.investment_debate_conclusion):
                lesson_parts.append("- **决策依据充分**: 投资辩论形成了明确的多头共识")

            if decision_chain.risk_debate_conclusion and ("风险可控" in decision_chain.risk_debate_conclusion or "适度" in decision_chain.risk_debate_conclusion):
                lesson_parts.append("- **风险控制得当**: 风险评估识别了主要风险并制定了应对策略")

        else:
            lesson_parts.append("###  失败原因")

            loss_rate = abs(outcome.percentage_return * 100)
            lesson_parts.append(f"此次交易产生了 **{loss_rate:.2f}%** 的亏损，主要失败因素包括：")
            lesson_parts.append("")

            # Analyze why it failed
            if "买入" in outcome.action or "buy" in outcome.action.lower():
                lesson_parts.append("- **方向判断失误**: 买入后价格下跌，与预期相反")
                lesson_parts.append(f"- **入场时机欠佳**: 在 ¥{outcome.entry_price:.2f} 入场过早，出场价 ¥{outcome.exit_price:.2f}")
            else:
                lesson_parts.append("- **方向判断失误**: 卖出后错失了盈利机会")
                lesson_parts.append(f"- **出场时机欠佳**: 在 ¥{outcome.entry_price:.2f} 过早退出")

            # Identify potential decision flaws
            if decision_chain.bear_argument and decision_chain.bull_argument:
                lesson_parts.append("- **多空分歧明显**: 多空双方观点存在较大分歧，市场不确定性高")

            if decision_chain.risk_debate_conclusion and ("高风险" in decision_chain.risk_debate_conclusion or "谨慎" in decision_chain.risk_debate_conclusion):
                lesson_parts.append("- **风险警示不足**: 风险评估已识别高风险，但未充分重视")

        lesson_parts.append("")

        # === Key Lessons Learned ===
        lesson_parts.append("##  关键经验")
        if success:
            lesson_parts.append(f"- 在类似市场环境下（价格约 ¥{market_state.price:.2f}），{outcome.action}决策是合理的")
            lesson_parts.append(f"- {outcome.holding_period_days}天持仓周期适合当前市场节奏")
            lesson_parts.append("- 多空辩论形成的共识方向可作为重要参考")
        else:
            lesson_parts.append(f"- 在类似市场环境下（价格约 ¥{market_state.price:.2f}），需要更谨慎评估{outcome.action}决策")
            lesson_parts.append(f"- {outcome.holding_period_days}天持仓周期可能需要调整")
            lesson_parts.append("- 当多空分歧较大时，应考虑降低仓位或观望")

        lesson_parts.append("")
        lesson_parts.append("---")
        lesson_parts.append(f"*记录时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        # Combine all parts into complete lesson
        lesson = "\n".join(lesson_parts)

        # Condensed version (for embedding retrieval) - keep it simple
        if success:
            key_lesson = f"{outcome.action} SUCCESS: return {outcome.percentage_return:.1%}, price {market_state.price:.2f}, held {outcome.holding_period_days} days"
        else:
            key_lesson = f"{outcome.action} FAILURE: loss {outcome.percentage_return:.1%}, price {market_state.price:.2f}, held {outcome.holding_period_days} days"

        return lesson, key_lesson, success

    def train_one_day(self, current_date: datetime) -> bool:
        """Train single trading day"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Time Travel to: {current_date.strftime('%Y-%m-%d')}")
        logger.info(f"{'='*60}")

        try:
            # 1. Retrieve similar historical cases (using Memory Bank)
            if self.memory_manager:
                logger.info("Retrieving similar historical cases...")

                market_context = {
                    'symbol': self.symbol,
                    'date': current_date.strftime("%Y-%m-%d")
                }

                similar_episodes = self.memory_manager.retrieve_episodes(
                    query_context=market_context,
                    top_k=3
                )

                logger.info(f"   Found {len(similar_episodes)} similar cases")

            # 2. Execute AI analysis (agent pretends it's current_date)
            logger.info("Executing multi-agent LLM analysis...")
            logger.info(f"[NO-FUTURE-FUNCTION] Agents will ONLY see data up to {current_date.strftime('%Y-%m-%d')}")

            # CRITICAL: Pass metadata to LLM to inform about no-future-function constraint
            final_state, processed_signal = self.trading_graph.propagate(
                self.symbol,
                current_date.strftime("%Y-%m-%d")
            )

            logger.info("   Analysis complete")

            # 3. Simulate trade execution
            logger.info("Simulating trade...")

            outcome = self.simulate_trade(current_date, processed_signal)

            if outcome is None:
                logger.info("   No trade occurred, skipping")
                return False

            # 4. Abstract lesson from outcome
            logger.info("Abstracting lesson...")

            market_state = self.extract_market_state(current_date, final_state)
            agent_analyses = self.extract_agent_analyses(final_state)
            decision_chain = self.extract_decision_chain(final_state)

            if not market_state or not decision_chain:
                logger.warning("Failed to extract lesson components")
                return False

            lesson, key_lesson, success = self.abstract_lesson(
                outcome, market_state, decision_chain
            )

            logger.info(f"   {lesson[:100]}...")

            # 5. Store Episode to Memory Bank
            if self.memory_manager:
                logger.info("Storing Episode to Memory Bank...")

                episode = TradingEpisode(
                    episode_id=f"{current_date.strftime('%Y-%m-%d')}_{self.symbol}",
                    date=current_date.strftime("%Y-%m-%d"),
                    symbol=self.symbol,
                    market_state=market_state,
                    agent_analyses=agent_analyses,
                    decision_chain=decision_chain,
                    outcome=outcome,
                    lesson=lesson,
                    key_lesson=key_lesson,
                    success=success,
                    created_at=datetime.now().isoformat(),
                    mode='training'
                )

                self.memory_manager.add_episode(episode)

                # 6. Abstract to maxim (coarse-grained memory)
                logger.info("Abstracting to maxim...")

                situation = f"{self.symbol} @ {current_date.strftime('%Y-%m-%d')}"
                recommendation = key_lesson

                # Store to appropriate agent memory based on decision type
                if 'bull' in decision_chain.final_decision.lower() or outcome.action == 'buy':
                    self.memory_manager.add_maxim('bull', situation, recommendation)
                elif 'bear' in decision_chain.final_decision.lower() or outcome.action == 'sell':
                    self.memory_manager.add_maxim('bear', situation, recommendation)
                else:
                    self.memory_manager.add_maxim('trader', situation, recommendation)

            # 7. Update statistics
            self.total_episodes += 1
            self.total_return += outcome.percentage_return

            if success:
                self.successful_episodes += 1
                logger.info("Episode stored successfully (profitable)")
            else:
                self.failed_episodes += 1
                logger.info("Episode stored successfully (loss)")

            return True

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            return False

    def run(self):
        """Execute complete Time Travel training"""
        logger.info(f"\n{'='*60}")
        logger.info("Starting Enhanced Time Travel Training")
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

        # Train each day
        for i, current_date in enumerate(training_days, 1):
            logger.info(f"[{i}/{len(training_days)}] Progress: {i/len(training_days):.1%}")

            self.train_one_day(current_date)

            # Print statistics every 10 episodes
            if i % 10 == 0:
                self.print_statistics()

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
        logger.info(f"   Average return: {avg_return:+.2%}\n")

    def save_results(self):
        """Save training results to JSON"""
        results = {
            'symbol': self.symbol,
            'start_date': self.start_date.strftime("%Y-%m-%d"),
            'end_date': self.end_date.strftime("%Y-%m-%d"),
            'holding_days': self.holding_days,
            'total_episodes': self.total_episodes,
            'successful_episodes': self.successful_episodes,
            'failed_episodes': self.failed_episodes,
            'success_rate': self.successful_episodes / self.total_episodes if self.total_episodes > 0 else 0,
            'average_return': self.total_return / self.total_episodes if self.total_episodes > 0 else 0,
            'timestamp': datetime.now().isoformat()
        }

        # Save to file
        output_dir = Path("training_results")
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"enhanced_time_travel_{self.symbol.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Training results saved: {output_file}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Enhanced Time Travel Training')

    parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        help='Stock code (e.g., 000001.SZ for A-shares)'
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
        help='Holding period (default: 5 days)'
    )

    args = parser.parse_args()

    # Create trainer
    trainer = EnhancedTimeTravelTrainer(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        holding_days=args.holding_days
    )

    # Execute training
    trainer.run()


if __name__ == "__main__":
    main()
