#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Agent Full Training - No Emoji Version

完整训练：6只股票，10个月数据，100,000步
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.dataflows.interface import get_stock_data_dataframe
from trading.simple_trading_env import SimpleTradingEnv

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from stable_baselines3.common.callbacks import CheckpointCallback
    from stable_baselines3.common.monitor import Monitor
    SB3_AVAILABLE = True
except ImportError:
    print("[ERROR] stable-baselines3 not installed")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def fetch_market_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取市场数据"""
    logger.info(f"[DATA] Fetching {symbol}...")

    try:
        df = get_stock_data_dataframe(symbol, start_date, end_date)

        if df is None or len(df) == 0:
            logger.error(f"[ERROR] No data for {symbol}")
            return None

        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_columns if col not in df.columns]

        if missing:
            logger.error(f"[ERROR] Missing columns: {missing}")
            return None

        df = df.dropna(subset=required_columns)
        df = df[df['close'] > 0]
        df = df[df['volume'] > 0]

        logger.info(f"[OK] {symbol}: {len(df)} records, Price: {df['close'].min():.2f}-{df['close'].max():.2f}")
        return df

    except Exception as e:
        logger.error(f"[ERROR] {symbol}: {e}")
        return None


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("[START] RL Agent FULL Training")
    logger.info("=" * 80)

    # 配置
    symbols = ["000001", "000002", "600519", "600036", "000858", "300750"]
    start_date = "2025-01-01"
    end_date = "2025-10-31"
    initial_cash = 100000.0
    model_save_path = "models/ppo_trading_agent.zip"

    logger.info(f"[CONFIG] Symbols: {', '.join(symbols)}")
    logger.info(f"[CONFIG] Period: {start_date} to {end_date}")
    logger.info(f"[CONFIG] Initial Cash: {initial_cash:,.0f}")
    logger.info(f"[CONFIG] Total Timesteps: 100,000")
    logger.info("")

    # 获取所有股票数据
    logger.info("[DATA] Fetching all stocks data...")
    all_data = []
    for symbol in symbols:
        df = fetch_market_data(symbol, start_date, end_date)
        if df is not None:
            all_data.append(df)
        else:
            logger.warning(f"[SKIP] {symbol} - no data")

    if not all_data:
        logger.error("[ERROR] No data available!")
        return 1

    # 合并数据
    combined_df = pd.concat(all_data, ignore_index=True)
    if 'date' in combined_df.columns:
        combined_df = combined_df.sort_values('date')

    logger.info(f"[DATA] Combined: {len(combined_df)} total records from {len(all_data)} stocks")
    logger.info("")

    # 创建环境
    logger.info("[ENV] Creating environment...")
    env = SimpleTradingEnv(
        df=combined_df,
        initial_cash=initial_cash,
        commission_rate=0.0003,
        max_shares=100000,
        lookback_window=10
    )
    env = Monitor(env)
    logger.info(f"[OK] Observation: {env.observation_space.shape}, Actions: {env.action_space.n}")
    logger.info("")

    # 向量化环境
    vec_env = DummyVecEnv([lambda: env])
    vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=True)

    # 创建模型
    logger.info("[MODEL] Creating PPO model...")
    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        verbose=1,
        tensorboard_log=None,
    )
    logger.info("[OK] Model initialized")
    logger.info("")

    # 设置回调
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path="./logs/ppo_checkpoints/",
        name_prefix="ppo_full"
    )

    # 训练
    logger.info("[TRAIN] Starting training (100,000 steps)...")
    logger.info("[TRAIN] This may take 30-60 minutes...")
    logger.info("")
    start_time = datetime.now()

    model.learn(
        total_timesteps=100000,
        callback=checkpoint_callback,
        progress_bar=True
    )

    elapsed = datetime.now() - start_time
    logger.info("")
    logger.info(f"[SUCCESS] Training completed in {elapsed}")
    logger.info("")

    # 保存
    os.makedirs(os.path.dirname(model_save_path) or "models", exist_ok=True)
    logger.info(f"[SAVE] Saving to: {model_save_path}")
    model.save(model_save_path)
    vec_env.save(model_save_path.replace('.zip', '_vecnormalize.pkl'))
    logger.info("[OK] Model and normalization saved")
    logger.info("")

    # 评估
    logger.info("[EVAL] Evaluating (10 episodes)...")
    episode_returns = []

    for ep in range(10):
        obs = vec_env.reset()
        done = False

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, info = vec_env.step(action)

            if done[0] and 'final_value' in info[0]:
                ret = info[0]['return'] * 100
                val = info[0]['final_value']
                episode_returns.append(ret)
                logger.info(f"   Episode {ep+1}: Return={ret:.2f}%, Value={val:,.2f}")

    if episode_returns:
        logger.info("")
        logger.info("[EVAL] Results:")
        logger.info(f"   Average Return: {np.mean(episode_returns):.2f}%")
        logger.info(f"   Std Return: {np.std(episode_returns):.2f}%")
        logger.info(f"   Best Return: {max(episode_returns):.2f}%")
        logger.info(f"   Worst Return: {min(episode_returns):.2f}%")

    logger.info("")
    logger.info("=" * 80)
    logger.info("[SUCCESS] FULL TRAINING COMPLETED!")
    logger.info("=" * 80)
    logger.info(f"[INFO] Model: {model_save_path}")
    logger.info("[INFO] Ready to use in backtest system!")
    logger.info("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
