"""
Test Paper Trading with Trained RL Agent (Simplified)

This script demonstrates paper trading with the trained RL model.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trading.rl_strategy import RLStrategy
from trading.simulated_broker import SimulatedBroker
from trading.order import Order, OrderSide, OrderType

# Setup logging (no emoji characters)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

logger = logging.getLogger(__name__)


def simulate_market_data(symbol: str, days: int = 30, start_price: float = 100.0):
    """
    Simulate market data for testing

    Args:
        symbol: Stock symbol
        days: Number of days to simulate
        start_price: Starting price

    Returns:
        DataFrame with OHLCV data
    """
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    prices = [start_price]
    for _ in range(days - 1):
        # Random walk with slight upward bias
        change = np.random.uniform(-0.03, 0.04)
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1.0))  # Ensure price stays positive

    df = pd.DataFrame({
        'date': dates,
        'open': [p * (1 + np.random.uniform(-0.01, 0.01)) for p in prices],
        'high': [p * (1 + np.random.uniform(0.01, 0.03)) for p in prices],
        'low': [p * (1 - np.random.uniform(0.01, 0.03)) for p in prices],
        'close': prices,
        'volume': [np.random.randint(1000000, 5000000) for _ in range(days)]
    })

    return df


def test_paper_trading_simple():
    """
    Run a simplified paper trading test

    This test:
    1. Loads the trained RL model
    2. Simulates market data
    3. Tests trading decisions over multiple days
    4. Reports performance
    """
    logger.info("=" * 80)
    logger.info("[START] Paper Trading Test (Simplified)")
    logger.info("=" * 80)

    # Tomorrow's date
    tomorrow = datetime.now() + timedelta(days=1)
    logger.info(f"[CONFIG] Start Date: {tomorrow.strftime('%Y-%m-%d')} (Tomorrow)")

    # Test configuration
    SYMBOLS = ["000001", "600519", "000858"]
    INITIAL_CASH = 100000.0
    MODEL_PATH = "models/ppo_trading_agent.zip"
    SIMULATION_DAYS = 20

    logger.info(f"[CONFIG] Symbols: {SYMBOLS}")
    logger.info(f"[CONFIG] Initial Cash: CNY {INITIAL_CASH:,.2f}")
    logger.info(f"[CONFIG] Model Path: {MODEL_PATH}")
    logger.info(f"[CONFIG] Simulation Days: {SIMULATION_DAYS}")
    logger.info("")

    # Initialize components
    logger.info("[INIT] Initializing components...")
    rl_strategy = RLStrategy(model_path=MODEL_PATH)

    if rl_strategy.model is None:
        logger.error("[ERROR] RL model not loaded, exiting")
        return False

    logger.info("[SUCCESS] RL Strategy initialized")

    broker = SimulatedBroker(initial_cash=INITIAL_CASH)
    logger.info("[SUCCESS] Simulated Broker initialized")
    logger.info("")

    # Simulate trading for each symbol
    logger.info("[RUN] Starting simulation...")
    logger.info("")

    for symbol in SYMBOLS:
        logger.info(f"[{symbol}] Simulating trading...")

        # Generate market data
        start_prices = {"000001": 12.0, "600519": 1500.0, "000858": 120.0}
        market_data = simulate_market_data(
            symbol,
            days=SIMULATION_DAYS,
            start_price=start_prices.get(symbol, 100.0)
        )

        logger.info(f"[{symbol}] Generated {len(market_data)} days of market data")
        logger.info(f"[{symbol}] Price range: {market_data['close'].min():.2f} - {market_data['close'].max():.2f}")

        # Simulate daily trading
        trades_count = 0

        for i in range(10, len(market_data)):  # Start from day 10 to have enough historical data
            # Get recent historical data
            historical_data = market_data.iloc[:i+1].copy()

            # Portfolio state
            current_price = historical_data.iloc[-1]['close']
            has_position = symbol in broker.positions
            portfolio_state = {
                'has_position': has_position,
                'cash': broker.cash,
                'total_equity': broker.get_balance()['total_assets']
            }

            # Get RL signal
            signal = rl_strategy.generate_signal(symbol, historical_data, portfolio_state)

            # Execute trading
            action = signal['action']

            if action == 'buy' and not has_position:
                # Calculate position size (10% of total equity)
                position_value = portfolio_state['total_equity'] * 0.1
                quantity = int(position_value / current_price / 100) * 100  # Round to 100 shares

                if quantity >= 100:  # Minimum lot size
                    order = Order(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        quantity=quantity,
                        order_type=OrderType.MARKET
                    )

                    if broker.submit_order(order):
                        broker.execute_market_order(order, current_price)
                        trades_count += 1
                        logger.info(
                            f"[{symbol}] Day {i}: BUY {quantity} @ CNY {current_price:.2f} - {signal['reason']}"
                        )

            elif action == 'sell' and has_position:
                position = broker.positions[symbol]
                order = Order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                    order_type=OrderType.MARKET
                )

                if broker.submit_order(order):
                    broker.execute_market_order(order, current_price)
                    trades_count += 1
                    logger.info(
                        f"[{symbol}] Day {i}: SELL {position.quantity} @ CNY {current_price:.2f} - {signal['reason']}"
                    )

        logger.info(f"[{symbol}] Completed: {trades_count} trades executed")
        logger.info("")

    # Print final results
    logger.info("=" * 80)
    logger.info("[COMPLETE] Paper Trading Test Complete")
    logger.info("=" * 80)

    balance = broker.get_balance()
    positions = broker.get_positions()

    logger.info(f"[RESULTS] Initial Cash: CNY {INITIAL_CASH:,.2f}")
    logger.info(f"[RESULTS] Final Cash: CNY {balance['cash']:,.2f}")
    logger.info(f"[RESULTS] Market Value: CNY {balance['market_value']:,.2f}")
    logger.info(f"[RESULTS] Total Assets: CNY {balance['total_assets']:,.2f}")
    logger.info(f"[RESULTS] Total Profit: CNY {balance['profit']:,.2f} ({balance['profit_pct']:.2%})")
    logger.info(f"[RESULTS] Total Trades: {len(broker.trade_history)}")

    if positions:
        logger.info(f"[POSITIONS] Open Positions:")
        for pos in positions:
            logger.info(f"   {pos['symbol']}: {pos['quantity']} shares @ CNY {pos['avg_price']:.2f}")
    else:
        logger.info(f"[POSITIONS] No open positions")

    logger.info("")
    logger.info("[SUCCESS] Test completed successfully!")

    return True


def main():
    """Main entry point"""
    try:
        success = test_paper_trading_simple()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
