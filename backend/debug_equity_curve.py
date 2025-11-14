#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug script to analyze equity curve data
"""

import sys
import os
sys.path.insert(0, '.')

from qflib_integration.backtest_runner import QFLibBacktestRunner
from datetime import datetime
import json

# Run a quick backtest
runner = QFLibBacktestRunner(
    model_path='models/production/train_20251114_055800/best_model.zip',
    tushare_token=os.getenv('TUSHARE_TOKEN', ''),
    symbols=['300502'],
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 11, 13),
    initial_capital=100000,
    commission_rate=0.00013
)

print("=" * 80)
print("Running backtest to analyze equity curve...")
print("=" * 80)

try:
    import asyncio
    results = asyncio.run(runner.run_async())

    equity_curve = results['equity_curve']

    print(f"\n✓ Backtest completed!")
    print(f"  Total data points: {len(equity_curve)}")

    # Analyze the data
    values = [point['portfolio_value'] for point in equity_curve]

    print(f"\n📊 Portfolio Value Analysis:")
    print(f"  Min: ¥{min(values):,.2f}")
    print(f"  Max: ¥{max(values):,.2f}")
    print(f"  First: ¥{values[0]:,.2f}")
    print(f"  Last: ¥{values[-1]:,.2f}")

    # Check how many unique values
    unique_values = len(set(values))
    print(f"\n🔍 Unique Values: {unique_values} out of {len(values)}")

    # Check how many times value changes
    changes = sum(1 for i in range(1, len(values)) if values[i] != values[i-1])
    print(f"🔍 Value Changes: {changes} times")

    # Find where changes happen
    print(f"\n📍 First 10 change points:")
    change_count = 0
    for i in range(1, len(equity_curve)):
        if values[i] != values[i-1]:
            point = equity_curve[i]
            print(f"  Day {i}: {point['date']} -> ¥{point['portfolio_value']:,.2f} (change: {values[i] - values[i-1]:+,.2f})")
            change_count += 1
            if change_count >= 10:
                break

    # Check how many consecutive 100000 values at the beginning
    consecutive_100k = 0
    for val in values:
        if val == 100000:
            consecutive_100k += 1
        else:
            break
    print(f"\n⚠️  Consecutive 100,000 values at start: {consecutive_100k}")

    # Show first 5 and last 5 data points
    print(f"\n📋 First 5 data points:")
    for i in range(min(5, len(equity_curve))):
        point = equity_curve[i]
        print(f"  {point['date']}: portfolio_value={point['portfolio_value']:,.2f}, cash={point['cash']:,.2f}")

    print(f"\n📋 Last 5 data points:")
    for i in range(max(0, len(equity_curve)-5), len(equity_curve)):
        point = equity_curve[i]
        print(f"  {point['date']}: portfolio_value={point['portfolio_value']:,.2f}, cash={point['cash']:,.2f}")

    # Save to file for inspection
    with open('debug_equity_curve_output.json', 'w') as f:
        json.dump({
            'summary': {
                'total_points': len(equity_curve),
                'unique_values': unique_values,
                'value_changes': changes,
                'consecutive_100k': consecutive_100k,
                'min': min(values),
                'max': max(values)
            },
            'equity_curve': equity_curve
        }, f, indent=2)

    print(f"\n✅ Full data saved to: debug_equity_curve_output.json")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
