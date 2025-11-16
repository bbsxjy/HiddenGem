#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Agent Training Script

使用真实市场数据训练强化学习交易Agent
Training period: 2025-01-01 to 2025-10-31
"""

import os
import sys
import logging
from datetime import datetime, timedelta
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
    from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback, CallbackList
    from stable_baselines3.common.monitor import Monitor
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    print(" stable-baselines3 not installed. Please install it:")
    print("   pip install stable-baselines3[extra]")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class RLTrainer:
    """RL Agent训练器"""

    def __init__(
        self,
        symbols: list = None,
        start_date: str = "2025-01-01",
        end_date: str = "2025-10-31",
        initial_cash: float = 100000.0,
        model_save_path: str = "models/ppo_trading_agent.zip"
    ):
        """初始化训练器

        Args:
            symbols: 训练股票列表（默认使用多只A股）
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            model_save_path: 模型保存路径
        """
        self.symbols = symbols or [
            "000001",  # 平安银行
            "000002",  # 万科A
            "600519",  # 贵州茅台
            "600036",  # 招商银行
            "000858",  # 五粮液
            "300750",  # 宁德时代
        ]
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = initial_cash
        self.model_save_path = model_save_path

        # 确保模型目录存在
        os.makedirs(os.path.dirname(model_save_path) or "models", exist_ok=True)

        logger.info(f"[INIT] RL Training Initializer Ready")
        logger.info(f"   Symbols: {', '.join(self.symbols)}")
        logger.info(f"   Period: {start_date} to {end_date}")
        logger.info(f"   Initial Cash: {initial_cash:,.0f}")
        logger.info(f"   Model Path: {model_save_path}")

    def fetch_market_data(self, symbol: str) -> pd.DataFrame:
        """获取市场数据

        Args:
            symbol: 股票代码

        Returns:
            市场数据DataFrame
        """
        logger.info(f"[DATA] Fetching market data for {symbol}...")

        try:
            # 使用统一数据接口获取数据
            df = get_stock_data_dataframe(symbol, self.start_date, self.end_date)

            if df is None or len(df) == 0:
                logger.error(f" 无法获取{symbol}数据")
                return None

            # 验证必需列
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                logger.error(f" 缺少必需列: {missing_columns}")
                return None

            # 清理数据
            df = df.dropna(subset=required_columns)
            df = df[df['close'] > 0]  # 过滤无效价格
            df = df[df['volume'] > 0]  # 过滤无效成交量

            logger.info(f" 成功获取{symbol}数据: {len(df)}条记录")
            logger.info(f"   时间范围: {df.index[0]} 至 {df.index[-1]}")
            logger.info(f"   价格范围: ¥{df['close'].min():.2f} - ¥{df['close'].max():.2f}")

            return df

        except Exception as e:
            logger.error(f" 获取{symbol}数据失败: {e}", exc_info=True)
            return None

    def create_training_data(self) -> pd.DataFrame:
        """创建训练数据（合并多只股票）

        Returns:
            合并后的训练数据
        """
        logger.info(f" 开始创建训练数据...")

        all_data = []

        for symbol in self.symbols:
            df = self.fetch_market_data(symbol)
            if df is not None:
                all_data.append(df)

        if not all_data:
            raise ValueError(" 没有可用的训练数据！")

        # 合并所有数据
        combined_df = pd.concat(all_data, ignore_index=True)

        # 按日期排序
        if 'date' in combined_df.columns:
            combined_df = combined_df.sort_values('date')
        elif combined_df.index.name == 'date':
            combined_df = combined_df.sort_index()

        logger.info(f" 训练数据创建完成: {len(combined_df)}条记录")
        logger.info(f"   来自{len(all_data)}只股票")

        return combined_df

    def create_env(self, df: pd.DataFrame) -> Monitor:
        """创建训练环境

        Args:
            df: 市场数据

        Returns:
            包装后的环境
        """
        logger.info(f" 创建交易环境...")

        # 创建SimpleTradingEnv
        env = SimpleTradingEnv(
            df=df,
            initial_cash=self.initial_cash,
            commission_rate=0.0003,  # 万3手续费
            max_shares=100000,
            lookback_window=10
        )

        # 包装为Monitor以记录统计信息
        env = Monitor(env)

        logger.info(f" 环境创建完成")
        logger.info(f"   观察空间: {env.observation_space.shape}")
        logger.info(f"   动作空间: {env.action_space.n}")

        return env

    def train(
        self,
        total_timesteps: int = 100000,
        learning_rate: float = 0.0003,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_range: float = 0.2,
        verbose: int = 1
    ):
        """训练RL模型

        Args:
            total_timesteps: 总训练步数
            learning_rate: 学习率
            n_steps: 每次rollout的步数
            batch_size: 批次大小
            n_epochs: 每次更新的epoch数
            gamma: 折扣因子
            gae_lambda: GAE lambda
            clip_range: PPO clip范围
            verbose: 日志详细程度
        """
        logger.info(f" 开始训练RL模型...")
        logger.info(f"   总步数: {total_timesteps:,}")
        logger.info(f"   学习率: {learning_rate}")
        logger.info(f"   批次大小: {batch_size}")

        # 创建训练数据
        train_df = self.create_training_data()

        # 创建环境
        env = self.create_env(train_df)

        # 向量化环境
        vec_env = DummyVecEnv([lambda: env])

        # 标准化环境（重要！）
        vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=True)

        # 创建PPO模型
        logger.info(f" 初始化PPO模型...")
        model = PPO(
            policy="MlpPolicy",
            env=vec_env,
            learning_rate=learning_rate,
            n_steps=n_steps,
            batch_size=batch_size,
            n_epochs=n_epochs,
            gamma=gamma,
            gae_lambda=gae_lambda,
            clip_range=clip_range,
            verbose=verbose,
            tensorboard_log="./logs/ppo_tensorboard/",
        )

        # 设置回调
        checkpoint_callback = CheckpointCallback(
            save_freq=10000,
            save_path="./logs/ppo_checkpoints/",
            name_prefix="ppo_trading"
        )

        # 训练模型
        logger.info(f" 开始训练...")
        start_time = datetime.now()

        model.learn(
            total_timesteps=total_timesteps,
            callback=checkpoint_callback,
            progress_bar=True
        )

        elapsed_time = datetime.now() - start_time
        logger.info(f" 训练完成！耗时: {elapsed_time}")

        # 保存模型
        logger.info(f" 保存模型到: {self.model_save_path}")
        model.save(self.model_save_path)

        # 同时保存标准化参数
        vec_env.save(self.model_save_path.replace('.zip', '_vecnormalize.pkl'))
        logger.info(f" 保存标准化参数到: {self.model_save_path.replace('.zip', '_vecnormalize.pkl')}")

        # 评估模型
        logger.info(f" 评估模型性能...")
        self.evaluate_model(model, vec_env, n_eval_episodes=10)

        return model

    def evaluate_model(self, model, vec_env, n_eval_episodes: int = 10):
        """评估模型性能

        Args:
            model: 训练好的模型
            vec_env: 向量化环境
            n_eval_episodes: 评估回合数
        """
        logger.info(f" 开始评估（{n_eval_episodes}回合）...")

        episode_rewards = []
        episode_returns = []

        for episode in range(n_eval_episodes):
            obs = vec_env.reset()
            done = False
            episode_reward = 0

            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, done, info = vec_env.step(action)
                episode_reward += reward[0]

                if done[0]:
                    if 'final_value' in info[0]:
                        final_value = info[0]['final_value']
                        return_pct = info[0]['return'] * 100
                        episode_returns.append(return_pct)
                        logger.info(f"   Episode {episode+1}: 收益率={return_pct:.2f}%, 最终价值=¥{final_value:,.2f}")

            episode_rewards.append(episode_reward)

        # 统计结果
        avg_reward = np.mean(episode_rewards)
        avg_return = np.mean(episode_returns) if episode_returns else 0
        std_return = np.std(episode_returns) if episode_returns else 0

        logger.info(f" 评估结果:")
        logger.info(f"   平均奖励: {avg_reward:.4f}")
        logger.info(f"   平均收益率: {avg_return:.2f}%")
        logger.info(f"   收益率标准差: {std_return:.2f}%")
        logger.info(f"   最佳收益率: {max(episode_returns) if episode_returns else 0:.2f}%")
        logger.info(f"   最差收益率: {min(episode_returns) if episode_returns else 0:.2f}%")


def main():
    """主函数"""
    logger.info("=" * 80)
    logger.info(" RL Agent训练脚本")
    logger.info("=" * 80)

    # 检查stable-baselines3
    if not SB3_AVAILABLE:
        logger.error(" stable-baselines3不可用")
        return

    # 创建训练器
    trainer = RLTrainer(
        symbols=[
            "000001",  # 平安银行
            "000002",  # 万科A
            "600519",  # 贵州茅台
            "600036",  # 招商银行
            "000858",  # 五粮液
            "300750",  # 宁德时代
        ],
        start_date="2025-01-01",
        end_date="2025-10-31",
        initial_cash=100000.0,
        model_save_path="models/ppo_trading_agent.zip"
    )

    # 开始训练
    try:
        model = trainer.train(
            total_timesteps=100000,  # 10万步训练
            learning_rate=0.0003,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            verbose=1
        )

        logger.info("=" * 80)
        logger.info(" 训练完成！")
        logger.info("=" * 80)
        logger.info(f" 模型已保存到: {trainer.model_save_path}")
        logger.info(f" 现在可以在回测系统中使用RL策略了")

    except Exception as e:
        logger.error(f" 训练失败: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
