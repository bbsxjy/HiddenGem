#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试：使用 EnhancedTradingEnv 测试模型
"""
import sys
from pathlib import Path
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trading.enhanced_trading_env import EnhancedTradingEnv
from tradingagents.dataflows.interface import get_stock_data_dataframe
from stable_baselines3 import PPO

# 加载模型
model_path = "models/production/best_model.zip"
model = PPO.load(model_path)
print(f"[OK] Model loaded: {model_path}")

# 获取股票数据 (使用2024测试期，与训练配置一致)
symbol = "300502"
start_date = "2024-01-01"
end_date = "2024-11-12"

df = get_stock_data_dataframe(symbol, start_date, end_date)
print(f"[OK] Data loaded: {len(df)} records")

# 创建环境
env = EnhancedTradingEnv(
    df=df,
    initial_cash=100000.0,
    commission_rate=0.0003,
    stamp_duty=0.001,
    enable_t1=True
)

# 运行测试
obs, _ = env.reset()
done = False
truncated = False
step = 0
action_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

print(f"\nStarting backtest...")
print(f"Initial cash: ${env.cash:,.2f}")

while not (done or truncated):
    action, _ = model.predict(obs, deterministic=True)
    action_counts[int(action)] += 1

    # Print first 3 actions
    if step < 3:
        print(f"Step {step}: action={int(action)}, cash={env.cash:,.0f}, position={env.shares_held}")

    obs, reward, done, truncated, info = env.step(action)
    step += 1

# Result statistics
print(f"\n=== Backtest Results ===")
print(f"Total steps: {step}")
print(f"Final value: ${env._get_portfolio_value():,.2f}")
print(f"Total return: {(env._get_portfolio_value() - 100000) / 100000 * 100:.2f}%")
print(f"Number of trades: {len(env.trades)}")

print(f"\n=== Action Statistics ===")
total_actions = sum(action_counts.values())
for action_id, count in action_counts.items():
    action_name = ['HOLD', 'BUY_25', 'BUY_50', 'SELL_50', 'SELL_ALL'][action_id]
    pct = count / total_actions * 100 if total_actions > 0 else 0
    print(f"{action_name:10s}: {count:4d} ({pct:5.1f}%)")

if len(env.trades) > 0:
    print(f"\n=== First 5 Trades ===")
    for i, trade in enumerate(env.trades[:5]):
        print(f"{i+1}. {trade}")
