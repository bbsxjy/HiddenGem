"""
Test Fundamental Strategy

Quick test to verify fundamental strategy implementation
"""

import sys
import os

# Add backend to path
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

import pandas as pd
from trading.fundamental_strategy import FundamentalStrategy

def test_fundamental_strategy():
    """Test fundamental strategy"""
    print("[TEST] Testing Fundamental Strategy...")

    # Create strategy instance
    strategy = FundamentalStrategy(
        max_pe=20,
        max_pb=3,
        min_roe=10,
        max_debt_ratio=70
    )

    print(f"[OK] Strategy created: {strategy.name}")

    # Create sample market data
    sample_data = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=30, freq='D'),
        'open': [10.0] * 30,
        'high': [10.5] * 30,
        'low': [9.5] * 30,
        'close': [10.0] * 30,
        'volume': [1000000] * 30
    })

    # Portfolio state
    portfolio_state = {
        'cash': 100000,
        'total_equity': 100000,
        'positions': {},
        'has_position': False
    }

    # Test signal generation
    print(f"\n[TEST] Testing signal generation for 000001.SZ...")
    signal = strategy.generate_signal('000001.SZ', sample_data, portfolio_state)

    print(f"   Signal: {signal.get('action')}")
    print(f"   Reason: {signal.get('reason')}")

    # Test with different stock
    print(f"\n[TEST] Testing signal generation for 600519.SH...")
    signal2 = strategy.generate_signal('600519.SH', sample_data, portfolio_state)

    print(f"   Signal: {signal2.get('action')}")
    print(f"   Reason: {signal2.get('reason')}")

    print("\n[OK] Fundamental strategy test completed!")

if __name__ == "__main__":
    test_fundamental_strategy()
