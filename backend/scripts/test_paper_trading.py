"""
Test Paper Trading with Trained RL Agent

This script tests the paper trading system with the trained RL model,
simulating real-time trading starting from tomorrow.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trading.paper_trading_engine import PaperTradingEngine
from trading.rl_strategy import RLStrategy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

logger = logging.getLogger(__name__)


class RLPaperTradingEngine(PaperTradingEngine):
    """
    Extended Paper Trading Engine with RL Strategy Integration

    This class wraps the RLStrategy to work with the PaperTradingEngine.
    """

    def __init__(
        self,
        model_path: str = "models/ppo_trading_agent.zip",
        initial_cash: float = 100000.0,
        symbols: list = None,
        update_interval: int = 60,
        enable_risk_control: bool = True
    ):
        """
        Initialize RL Paper Trading Engine

        Args:
            model_path: Path to trained RL model
            initial_cash: Initial capital
            symbols: List of stock symbols to trade
            update_interval: Update interval in seconds
            enable_risk_control: Enable risk management
        """
        super().__init__(
            rl_agent=None,  # We'll use RLStrategy instead
            initial_cash=initial_cash,
            symbols=symbols,
            update_interval=update_interval,
            enable_risk_control=enable_risk_control
        )

        # Initialize RL Strategy
        logger.info(f"[INIT] Loading RL Strategy from: {model_path}")
        self.rl_strategy = RLStrategy(model_path=model_path)

        if self.rl_strategy.model is not None:
            logger.info("[SUCCESS] RL model loaded successfully")
        else:
            logger.warning("[WARNING] RL model not available, will use fallback strategy")

    async def _get_rl_action(self, symbol: str, market_data: dict):
        """
        Get action from RL Strategy

        Args:
            symbol: Stock symbol
            market_data: Real-time market data

        Returns:
            Action ID (0=HOLD, 1=BUY, 2=SELL)
        """
        try:
            # Build state for RL strategy
            portfolio_state = {
                'has_position': symbol in self.portfolio.positions,
                'cash': self.broker.cash,
                'total_equity': self.broker.get_balance()['total_assets']
            }

            # For RL strategy, we need historical price data
            # In paper trading, we simulate this with current market data
            import pandas as pd
            import numpy as np

            # Create a simple DataFrame with current market data
            # In real implementation, you'd fetch recent historical data
            current_price = market_data['price']

            # Simulate recent price history (for demo purposes)
            # In production, fetch actual historical data
            prices = [current_price * (1 + np.random.uniform(-0.02, 0.02)) for _ in range(30)]
            prices.append(current_price)

            df = pd.DataFrame({
                'close': prices,
                'high': [p * 1.01 for p in prices],
                'low': [p * 0.99 for p in prices],
                'open': prices,
                'volume': [1000000] * len(prices)
            })

            # Get signal from RL strategy
            signal = self.rl_strategy.generate_signal(symbol, df, portfolio_state)

            # Map signal to action
            action_map = {
                'hold': 0,
                'buy': 1,
                'sell': 2
            }

            action = action_map.get(signal['action'], 0)
            logger.info(f"[RL] {symbol}: {signal['action'].upper()} - {signal['reason']}")

            return action

        except Exception as e:
            logger.error(f"[ERROR] RL action generation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0  # HOLD on error


async def test_paper_trading(
    symbols: list,
    initial_cash: float = 100000.0,
    model_path: str = "models/ppo_trading_agent.zip",
    duration_minutes: int = 5,
    update_interval: int = 30
):
    """
    Test paper trading system

    Args:
        symbols: List of stock symbols to trade
        initial_cash: Initial capital
        model_path: Path to RL model
        duration_minutes: How long to run the test (minutes)
        update_interval: Update interval (seconds)
    """
    logger.info("=" * 80)
    logger.info("[START] Paper Trading Test")
    logger.info("=" * 80)

    # Tomorrow's date
    tomorrow = datetime.now() + timedelta(days=1)
    logger.info(f"[CONFIG] Start Date: {tomorrow.strftime('%Y-%m-%d')} (Tomorrow)")
    logger.info(f"[CONFIG] Symbols: {symbols}")
    logger.info(f"[CONFIG] Initial Cash: ¥{initial_cash:,.2f}")
    logger.info(f"[CONFIG] Model Path: {model_path}")
    logger.info(f"[CONFIG] Test Duration: {duration_minutes} minutes")
    logger.info(f"[CONFIG] Update Interval: {update_interval} seconds")
    logger.info("")

    # Create paper trading engine
    engine = RLPaperTradingEngine(
        model_path=model_path,
        initial_cash=initial_cash,
        symbols=symbols,
        update_interval=update_interval,
        enable_risk_control=True
    )

    # Run paper trading for specified duration
    logger.info("[RUN] Starting paper trading engine...")
    logger.info(f"[RUN] Will run for {duration_minutes} minutes")
    logger.info("")

    # Create a task to run the engine
    trading_task = asyncio.create_task(engine.run(symbols))

    try:
        # Wait for the specified duration
        await asyncio.sleep(duration_minutes * 60)

        # Stop the engine
        logger.info("")
        logger.info("[STOP] Test duration completed, stopping engine...")
        engine.stop()

        # Wait for the engine to finish
        await trading_task

    except KeyboardInterrupt:
        logger.info("")
        logger.info("[STOP] Test interrupted by user")
        engine.stop()
        await trading_task

    except Exception as e:
        logger.error(f"[ERROR] Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        engine.stop()

    finally:
        # Print final status
        logger.info("")
        logger.info("=" * 80)
        logger.info("[COMPLETE] Paper Trading Test Complete")
        logger.info("=" * 80)

        status = engine.get_status()
        logger.info(f"[STATS] Total Updates: {status['total_updates']}")
        logger.info(f"[STATS] Total Trades: {status['trade_count']}")
        logger.info(f"[STATS] Final Cash: ¥{status['balance']['cash']:,.2f}")
        logger.info(f"[STATS] Final Assets: ¥{status['balance']['total_assets']:,.2f}")
        logger.info(f"[STATS] Total Profit: ¥{status['balance']['profit']:,.2f} ({status['balance']['profit_pct']:.2%})")

        if status['positions']:
            logger.info(f"[POSITIONS] Open Positions:")
            for pos in status['positions']:
                logger.info(f"   {pos['symbol']}: {pos['quantity']} shares @ ¥{pos['avg_price']:.2f}")
        else:
            logger.info(f"[POSITIONS] No open positions")


def main():
    """Main entry point"""

    # Test configuration
    TEST_SYMBOLS = [
        "000001",  # 平安银行
        "600519",  # 贵州茅台
        "000858",  # 五粮液
    ]

    INITIAL_CASH = 100000.0  # ¥100,000
    MODEL_PATH = "models/ppo_trading_agent.zip"
    TEST_DURATION = 5  # minutes
    UPDATE_INTERVAL = 30  # seconds

    # Run test
    asyncio.run(test_paper_trading(
        symbols=TEST_SYMBOLS,
        initial_cash=INITIAL_CASH,
        model_path=MODEL_PATH,
        duration_minutes=TEST_DURATION,
        update_interval=UPDATE_INTERVAL
    ))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
