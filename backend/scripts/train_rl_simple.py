#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Agent Quick Training - No Emoji Version

使用真实市场数据训练强化学习交易Agent（简化版）
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

# Import stable-baselines3
try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from stable_baselines3.common.callbacks import CheckpointCallback
    from stable_baselines3.common.monitor import Monitor
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    print("[ERROR] stable-baselines3 not installed")
    print("Please install: pip install stable-baselines3[extra]")
    sys.exit(1)

# Configure logging - disable emoji
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def fetch_market_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取市场数据"""
    logger.info(f"[DATA] Fetching market data for {symbol}...")

    try:
        df = get_stock_data_dataframe(symbol, start_date, end_date)

        if df is None or len(df) == 0:
            logger.error(f"[ERROR] No data found for {symbol}")
            return None

        # 验证必需列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            logger.error(f"[ERROR] Missing columns: {missing_columns}")
            return None

        # 清理数据
        df = df.dropna(subset=required_columns)
        df = df[df['close'] > 0]
        df = df[df['volume'] > 0]

        logger.info(f"[SUCCESS] Got {len(df)} records for {symbol}")
        logger.info(f"   Date range: {df.index[0]} to {df.index[-1]}")
        logger.info(f"   Price range: {df['close'].min():.2f} - {df['close'].max():.2f}")

        return df

    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch {symbol}: {e}", exc_info=True)
        return None


def create_env(df: pd.DataFrame, initial_cash: float = 100000.0) -> Monitor:
    """创建训练环境"""
    logger.info(f"[ENV] Creating trading environment...")

    env = SimpleTradingEnv(
        df=df,
        initial_cash=initial_cash,
        commission_rate=0.0003,
        max_shares=100000,
        lookback_window=10
    )

    env = Monitor(env)

    logger.info(f"[SUCCESS] Environment created")
    logger.info(f"   Observation space: {env.observation_space.shape}")
    logger.info(f"   Action space: {env.action_space.n}")

    return env


def train_model(
    env,
    total_timesteps: int = 10000,
    learning_rate: float = 0.0003,
    model_save_path: str = "models/ppo_trading_agent_test.zip"
):
    """训练模型"""
    logger.info(f"[TRAIN] Starting training...")
    logger.info(f"   Total timesteps: {total_timesteps:,}")
    logger.info(f"   Learning rate: {learning_rate}")

    # 向量化环境
    vec_env = DummyVecEnv([lambda: env])
    vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=True)

    # 创建PPO模型（不使用tensorboard）
    logger.info(f"[TRAIN] Initializing PPO model...")
    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        learning_rate=learning_rate,
        n_steps=512,
        batch_size=64,
        n_epochs=5,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        verbose=1,
        tensorboard_log=None,  # 禁用tensorboard
    )

    # 设置回调
    checkpoint_callback = CheckpointCallback(
        save_freq=5000,
        save_path="./logs/ppo_checkpoints/",
        name_prefix="ppo_trading"
    )

    # 训练
    logger.info(f"[TRAIN] Training started...")
    start_time = datetime.now()

    model.learn(
        total_timesteps=total_timesteps,
        callback=checkpoint_callback,
        progress_bar=True
    )

    elapsed_time = datetime.now() - start_time
    logger.info(f"[SUCCESS] Training completed in {elapsed_time}")

    # 保存模型
    os.makedirs(os.path.dirname(model_save_path) or "models", exist_ok=True)
    logger.info(f"[SAVE] Saving model to: {model_save_path}")
    model.save(model_save_path)

    # 保存标准化参数
    vec_env.save(model_save_path.replace('.zip', '_vecnormalize.pkl'))
    logger.info(f"[SAVE] Saved normalization params")

    # 评估
    logger.info(f"[EVAL] Evaluating model...")
    evaluate_model(model, vec_env, n_eval_episodes=5)

    return model


def evaluate_model(model, vec_env, n_eval_episodes: int = 5):
    """评估模型"""
    logger.info(f"[EVAL] Running {n_eval_episodes} evaluation episodes...")

    episode_returns = []

    for episode in range(n_eval_episodes):
        obs = vec_env.reset()
        done = False

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, info = vec_env.step(action)

            if done[0]:
                if 'final_value' in info[0]:
                    final_value = info[0]['final_value']
                    return_pct = info[0]['return'] * 100
                    episode_returns.append(return_pct)
                    logger.info(f"   Episode {episode+1}: Return={return_pct:.2f}%, Final Value={final_value:,.2f}")

    # 统计
    if episode_returns:
        avg_return = np.mean(episode_returns)
        std_return = np.std(episode_returns)
        logger.info(f"[EVAL] Results:")
        logger.info(f"   Average Return: {avg_return:.2f}%")
        logger.info(f"   Std Return: {std_return:.2f}%")
        logger.info(f"   Best Return: {max(episode_returns):.2f}%")
        logger.info(f"   Worst Return: {min(episode_returns):.2f}%")


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info("[START] RL Agent Quick Training")
    logger.info("=" * 80)

    if not SB3_AVAILABLE:
        logger.error("[ERROR] stable-baselines3 not available")
        return 1

    # 配置
    symbol = "000001"
    start_date = "2025-01-01"
    end_date = "2025-03-31"
    initial_cash = 100000.0
    model_save_path = "models/ppo_trading_agent_test.zip"

    logger.info(f"[CONFIG] Symbol: {symbol}")
    logger.info(f"[CONFIG] Period: {start_date} to {end_date}")
    logger.info(f"[CONFIG] Initial Cash: {initial_cash:,.0f}")
    logger.info(f"[CONFIG] Model Path: {model_save_path}")
    logger.info("")

    # 获取数据
    df = fetch_market_data(symbol, start_date, end_date)
    if df is None:
        logger.error("[ERROR] Failed to fetch market data")
        return 1

    # 创建环境
    env = create_env(df, initial_cash)

    # 训练
    try:
        model = train_model(
            env,
            total_timesteps=10000,
            learning_rate=0.0003,
            model_save_path=model_save_path
        )

        logger.info("=" * 80)
        logger.info("[SUCCESS] Training completed!")
        logger.info("=" * 80)
        logger.info(f"[INFO] Model saved to: {model_save_path}")
        logger.info(f"[INFO] You can now use RL strategy in backtest system")

        return 0

    except Exception as e:
        logger.error(f"[ERROR] Training failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
