#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Production RL Training Script V2 for HiddenGem (FIXED)

Key Improvements:
1. Invalid action penalty - explicit negative reward for invalid actions
2. Improved reward shaping - encourages trading and profitable positions
3. Action masking wrapper - prevents model from selecting invalid actions
4. Better exploration - increased entropy coefficient
5. Diverse training stocks - mix of winners, losers, different sectors
6. Extended training - 1M timesteps instead of 500k
7. Action distribution monitoring - detect pathological behavior early

Root Cause (Fixed):
- Original env silently ignored invalid SELL actions (return without error/penalty)
- Model learned "always SELL_ALL = safe, 0 reward, no trades"
- Never explored profitable BUY actions

Training Period:
- Training: 2020-01-01 ~ 2022-12-31 (3 years)
- Validation: 2023-01-01 ~ 2023-12-31 (1 year)
- Test: 2024-01-01 ~ 2024-11-12 (11 months)
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
import json
from typing import List, Dict, Tuple, Optional
import tushare as ts

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trading.enhanced_trading_env import EnhancedTradingEnv
from tradingagents.dataflows.interface import get_stock_data_dataframe

# Import stable-baselines3
try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback, BaseCallback
    import gymnasium as gym
    from gymnasium import spaces
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    print("ERROR: stable-baselines3 not installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('train_rl_production_v2.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ====================================================================================
# Action Masking Wrapper
# ====================================================================================

class ActionMaskingWrapper(gym.Wrapper):
    """Action masking wrapper that prevents invalid actions during training

    Masks:
    - SELL actions when position = 0
    - BUY actions when cash < 5% of portfolio value

    This forces the model to learn valid trading patterns from the start.
    """

    def __init__(self, env):
        super().__init__(env)
        self.action_space = env.action_space

    def reset(self, **kwargs):
        return self.env.reset(**kwargs)

    def step(self, action):
        # Apply action masking
        masked_action = self._mask_action(action)

        if masked_action != action:
            logger.debug(f"Action masked: {action} -> {masked_action}")

        return self.env.step(masked_action)

    def _mask_action(self, action: int) -> int:
        """Mask invalid actions"""
        price = self.env.df.iloc[self.env.current_step]['close']
        portfolio_value = self.env._get_portfolio_value()

        # Mask SELL actions when no position
        if action in [3, 4]:  # SELL_50 or SELL_ALL
            if self.env.shares_held == 0:
                return 0  # Force HOLD

        # Mask BUY actions when insufficient cash
        if action in [1, 2]:  # BUY_25 or BUY_50
            if self.env.cash < portfolio_value * 0.05:  # Less than 5% cash
                return 0  # Force HOLD

        return action

    def action_masks(self) -> np.ndarray:
        """Return valid action mask (for algorithms that support action masking)"""
        mask = np.ones(self.action_space.n, dtype=np.bool_)

        price = self.env.df.iloc[self.env.current_step]['close']
        portfolio_value = self.env._get_portfolio_value()

        # Mask SELL actions when no position
        if self.env.shares_held == 0:
            mask[3] = False  # SELL_50
            mask[4] = False  # SELL_ALL

        # Mask BUY actions when insufficient cash
        if self.env.cash < portfolio_value * 0.05:
            mask[1] = False  # BUY_25
            mask[2] = False  # BUY_50

        return mask


class ImprovedRewardWrapper(gym.Wrapper):
    """Improved reward shaping that encourages trading and profitable positions

    Key Changes:
    1. Explicit penalty for invalid actions (-10)
    2. Increased holding reward (+0.05 instead of +0.01)
    3. Reduced transaction cost penalty (-0.001 instead of -0.01)
    4. Bonus for profitable trades
    5. Bonus for buying in uptrends
    """

    def __init__(self, env):
        super().__init__(env)
        self.last_portfolio_value = None
        self.last_shares_held = 0
        self.last_action = 0

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        # Access the underlying EnhancedTradingEnv through unwrapped
        self.last_portfolio_value = self.unwrapped._get_portfolio_value()
        self.last_shares_held = 0
        self.last_action = 0
        return obs, info

    def step(self, action):
        # Get state before action (access underlying env through unwrapped)
        shares_before = self.unwrapped.shares_held
        cash_before = self.unwrapped.cash
        portfolio_value_before = self.unwrapped._get_portfolio_value()

        # Execute action
        obs, reward, done, truncated, info = self.env.step(action)

        # Calculate improved reward
        improved_reward = self._calculate_improved_reward(
            action,
            shares_before,
            cash_before,
            portfolio_value_before,
            done
        )

        self.last_portfolio_value = self.unwrapped._get_portfolio_value()
        self.last_shares_held = self.unwrapped.shares_held
        self.last_action = action

        return obs, improved_reward, done, truncated, info

    def _calculate_improved_reward(
        self,
        action: int,
        shares_before: int,
        cash_before: float,
        portfolio_value_before: float,
        done: bool
    ) -> float:
        """Calculate improved reward with better shaping"""
        portfolio_value_after = self.unwrapped._get_portfolio_value()
        shares_after = self.unwrapped.shares_held
        cash_after = self.unwrapped.cash

        # 1. Base reward: portfolio value change
        if portfolio_value_before > 0:
            return_pct = (portfolio_value_after - portfolio_value_before) / portfolio_value_before
            reward = return_pct * 100  # Amplify
        else:
            reward = 0

        # 2. Invalid action penalty (FIXED: Explicit negative reward)
        if action in [3, 4] and shares_before == 0:  # Tried to SELL with no position
            reward -= 10.0  # Large penalty
            logger.debug(f"[PENALTY] Invalid SELL action with no position: -10.0")

        if action in [1, 2] and cash_before < portfolio_value_before * 0.05:  # Tried to BUY with insufficient cash
            reward -= 10.0  # Large penalty
            logger.debug(f"[PENALTY] Invalid BUY action with insufficient cash: -10.0")

        # 3. Holding position reward (INCREASED from +0.01 to +0.05)
        if shares_after > 0:
            reward += 0.05  # Encourage holding positions

        # 4. Transaction cost penalty (REDUCED from -0.01 to -0.001)
        if action != 0:
            reward -= 0.001  # Small penalty to avoid over-trading

        # 5. Successful trade bonus
        # BUY bonus: Reward for entering positions
        if action in [1, 2] and shares_after > shares_before:
            reward += 0.5  # Bonus for successful BUY
            logger.debug(f"[BONUS] Successful BUY: +0.5")

        # SELL bonus: Reward for profitable exits
        if action in [3, 4] and shares_after < shares_before:
            if portfolio_value_after > portfolio_value_before:
                profit_pct = (portfolio_value_after - portfolio_value_before) / portfolio_value_before
                reward += profit_pct * 50  # Large bonus for profitable trades
                logger.debug(f"[BONUS] Profitable SELL: +{profit_pct * 50:.2f}")

        # 6. Volatility penalty (reduce excessive risk)
        if len(self.unwrapped.daily_returns) > 10:
            volatility = np.std(self.unwrapped.daily_returns[-20:])
            reward -= volatility * 5  # Reduced from 10

        return reward


class ActionDistributionCallback(BaseCallback):
    """Callback to monitor action distribution during training"""

    def __init__(self, log_freq=10000, verbose=0):
        super().__init__(verbose)
        self.log_freq = log_freq
        self.action_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        self.episode_count = 0

    def _on_step(self) -> bool:
        # Record action
        if 'actions' in self.locals:
            action = int(self.locals['actions'][0])
            self.action_counts[action] += 1

        # Log distribution periodically
        if self.num_timesteps % self.log_freq == 0:
            total = sum(self.action_counts.values())
            if total > 0:
                logger.info(f"\n=== Action Distribution (Step {self.num_timesteps}) ===")
                for action_id, count in self.action_counts.items():
                    action_name = ['HOLD', 'BUY_25', 'BUY_50', 'SELL_50', 'SELL_ALL'][action_id]
                    pct = count / total * 100
                    logger.info(f"  {action_name:10s}: {count:6d} ({pct:5.1f}%)")

                # Warning if pathological behavior detected
                if self.action_counts[4] > total * 0.8:  # >80% SELL_ALL
                    logger.warning("WARNING: Model is predicting >80% SELL_ALL actions!")
                if self.action_counts[0] > total * 0.9:  # >90% HOLD
                    logger.warning("WARNING: Model is predicting >90% HOLD actions!")

        return True


class ProgressCallback(BaseCallback):
    """Callback to save training progress to JSON file for API consumption"""

    def __init__(self, progress_file: str, total_timesteps: int, update_freq: int = 1000, verbose=0):
        super().__init__(verbose)
        self.progress_file = progress_file
        self.metrics_history_file = progress_file.replace('training_progress.json', 'metrics_history.json')
        self.total_timesteps = total_timesteps
        self.update_freq = update_freq
        self.start_time = None
        self.metrics_history = []  # 保存历史指标

    def _on_training_start(self) -> None:
        """Called before training starts"""
        import time
        self.start_time = time.time()
        self._save_progress()

    def _on_step(self) -> bool:
        """Called after each step"""
        if self.num_timesteps % self.update_freq == 0:
            self._save_progress()
        return True

    def _save_progress(self):
        """Save current progress to JSON file"""
        import time
        elapsed = time.time() - self.start_time if self.start_time else 0
        progress_pct = (self.num_timesteps / self.total_timesteps * 100) if self.total_timesteps > 0 else 0

        # 计算预估剩余时间
        if self.num_timesteps > 0 and elapsed > 0:
            time_per_step = elapsed / self.num_timesteps
            remaining_steps = self.total_timesteps - self.num_timesteps
            estimated_remaining = time_per_step * remaining_steps
        else:
            estimated_remaining = None

        # 从训练日志中提取指标
        ep_rew_mean = None
        ep_len_mean = None
        fps = None
        policy_loss = None
        value_loss = None
        explained_variance = None

        if hasattr(self.model, 'ep_info_buffer') and len(self.model.ep_info_buffer) > 0:
            ep_rew_mean = np.mean([ep_info['r'] for ep_info in self.model.ep_info_buffer])
            ep_len_mean = np.mean([ep_info['l'] for ep_info in self.model.ep_info_buffer])

        if hasattr(self, 'locals') and 'fps' in self.locals:
            fps = self.locals.get('fps')

        # PPO特定的loss指标
        if hasattr(self.model, 'logger') and hasattr(self.model.logger, 'name_to_value'):
            log_data = self.model.logger.name_to_value
            policy_loss = log_data.get('train/policy_gradient_loss')
            value_loss = log_data.get('train/value_loss')
            explained_variance = log_data.get('train/explained_variance')

        progress_data = {
            'timesteps': self.num_timesteps,
            'total_timesteps': self.total_timesteps,
            'progress_pct': round(progress_pct, 2),
            'elapsed_time': round(elapsed, 2),
            'estimated_remaining': round(estimated_remaining, 2) if estimated_remaining else None,
            'ep_rew_mean': round(float(ep_rew_mean), 4) if ep_rew_mean is not None else None,
            'ep_len_mean': round(float(ep_len_mean), 2) if ep_len_mean is not None else None,
            'fps': round(float(fps), 2) if fps is not None else None,
            'policy_loss': round(float(policy_loss), 6) if policy_loss is not None else None,
            'value_loss': round(float(value_loss), 6) if value_loss is not None else None,
            'explained_variance': round(float(explained_variance), 4) if explained_variance is not None else None,
            'last_update': datetime.now().isoformat()
        }

        try:
            # 写入当前进度文件
            import json
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)

            # 保存到历史记录
            metrics_point = {
                'timesteps': self.num_timesteps,
                'ep_rew_mean': progress_data['ep_rew_mean'],
                'ep_len_mean': progress_data['ep_len_mean'],
                'policy_loss': progress_data['policy_loss'],
                'value_loss': progress_data['value_loss'],
                'explained_variance': progress_data['explained_variance'],
                'fps': progress_data['fps'],
                'timestamp': progress_data['last_update']
            }
            self.metrics_history.append(metrics_point)

            # 写入历史文件（只保留最近500个数据点）
            history_to_save = self.metrics_history[-500:]
            with open(self.metrics_history_file, 'w') as f:
                json.dump(history_to_save, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to save progress file: {e}")


# ====================================================================================
# Configuration
# ====================================================================================

CONFIG = {
    # Data parameters
    "train_start": "2020-01-01",
    "train_end":   "2024-06-30",
    "val_start":   "2024-07-01",
    "val_end":     "2024-12-31",
    "test_start":  "2025-01-01",
    "test_end":    "2025-11-12",

    # Stock pool
    'use_hs300': True,
    'max_stocks': 50,

    # Environment parameters
    'initial_cash': 100000.0,
    'commission_rate': 0.00013,
    'stamp_duty': 0.001,
    'enable_t1': True,

    # Training parameters (IMPROVED)
    'total_timesteps': 300000,  # Reduced to 300k for faster validation
    'n_steps': 2048,
    'batch_size': 64,
    'n_epochs': 5,
    'learning_rate': 0.0003,
    'gamma': 0.995,
    'ent_coef': 0.01,  # NEW: Encourage exploration
    'clip_range': 0.2,

    # Wrappers
    'use_action_masking': True,  # NEW: Enable action masking
    'use_improved_reward': True,  # NEW: Enable improved reward shaping

    # Save paths
    'model_dir': 'models/production',
    'data_cache_dir': 'data_cache',
    'results_dir': 'results'
}


# ====================================================================================
# Helper Functions
# ====================================================================================

def get_hs300_stocks() -> List[str]:
    """Get HS300 constituent stocks"""
    logger.info("Fetching HS300 stocks...")

    try:
        ts_token = os.getenv('TUSHARE_TOKEN')
        if not ts_token:
            raise ValueError("TUSHARE_TOKEN not configured")

        ts.set_token(ts_token)
        pro = ts.pro_api()

        df = pro.index_weight(index_code='399300.SZ')
        stocks = df['con_code'].unique().tolist()
        stocks = [s.split('.')[0] for s in stocks]

        logger.info(f"Fetched {len(stocks)} HS300 stocks")
        return stocks

    except Exception as e:
        logger.error(f"Failed to fetch HS300: {e}")
        logger.warning("Using fallback stock list")
        return [
            '000001', '000002', '000063', '000066', '000333', '000651', '000858',
            '600000', '600036', '600519', '600887', '601318', '601398', '601857', '601988'
        ]


def download_stock_data(symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Download single stock data"""
    try:
        df = get_stock_data_dataframe(symbol, start_date, end_date)

        if df is None or len(df) == 0:
            return None

        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            return None

        df = df.dropna(subset=required_cols)
        df = df[(df['close'] > 0) & (df['volume'] > 0)]

        if len(df) < 60:  # Need at least 60 days for technical indicators
            return None

        return df

    except Exception as e:
        logger.debug(f"Failed to download {symbol}: {e}")
        return None


def prepare_training_data(
    stocks: List[str],
    start_date: str,
    end_date: str
) -> List[Tuple[str, pd.DataFrame]]:
    """Prepare training data"""
    logger.info(f"Preparing data: {start_date} to {end_date}")
    logger.info(f"Stock count: {len(stocks)}")

    stock_data = []
    failed = []

    for i, symbol in enumerate(stocks, 1):
        logger.info(f"[{i}/{len(stocks)}] Downloading {symbol}...")
        df = download_stock_data(symbol, start_date, end_date)

        if df is not None:
            stock_data.append((symbol, df))
            logger.info(f"   {symbol}: {len(df)} records")
        else:
            failed.append(symbol)
            logger.warning(f"   {symbol}: Failed")

    logger.info(f"\nSuccess: {len(stock_data)}, Failed: {len(failed)}")

    if len(stock_data) == 0:
        raise ValueError("No stock data downloaded successfully")

    return stock_data


def create_wrapped_env(stock_data: List[Tuple[str, pd.DataFrame]], config: Dict):
    """Create environment with wrappers"""
    import random

    # Random stock selection
    symbol, df = random.choice(stock_data)

    # Base environment
    env = EnhancedTradingEnv(
        df=df,
        initial_cash=config['initial_cash'],
        commission_rate=config['commission_rate'],
        stamp_duty=config['stamp_duty'],
        enable_t1=config['enable_t1']
    )

    # Apply wrappers
    if config.get('use_action_masking', True):
        env = ActionMaskingWrapper(env)
        logger.debug("Applied ActionMaskingWrapper")

    if config.get('use_improved_reward', True):
        env = ImprovedRewardWrapper(env)
        logger.debug("Applied ImprovedRewardWrapper")

    env = Monitor(env)

    return env


def train_model(
    train_data: List[Tuple[str, pd.DataFrame]],
    val_data: List[Tuple[str, pd.DataFrame]],
    config: Dict
) -> Tuple[PPO, VecNormalize]:
    """Train RL model with improvements"""
    logger.info("\n" + "="*80)
    logger.info("Starting RL Model Training (V2 - FIXED)")
    logger.info("="*80)

    # Create training environment
    logger.info(f"Creating training environment (T+1={'enabled' if config['enable_t1'] else 'disabled'})...")
    train_env = DummyVecEnv([
        lambda: create_wrapped_env(train_data, config)
    ])
    train_env = VecNormalize(train_env, norm_obs=True, norm_reward=True)

    # Create validation environment
    logger.info("Creating validation environment...")
    eval_env = DummyVecEnv([
        lambda: create_wrapped_env(val_data, config)
    ])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, training=False)
    eval_env.obs_rms = train_env.obs_rms
    eval_env.ret_rms = train_env.ret_rms

    # Create callbacks
    os.makedirs(config['model_dir'], exist_ok=True)

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=config['model_dir'],
        log_path=config['model_dir'],
        eval_freq=10000,
        deterministic=True,
        render=False
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path=config['model_dir'],
        name_prefix='rl_model_v2'
    )

    action_dist_callback = ActionDistributionCallback(log_freq=10000)

    # Progress callback for API consumption
    progress_file = os.path.join(config['model_dir'], 'training_progress.json')
    progress_callback = ProgressCallback(
        progress_file=progress_file,
        total_timesteps=config['total_timesteps'],
        update_freq=2000  # Update every 2000 steps
    )

    # Create PPO model with improved hyperparameters
    logger.info("Initializing PPO model...")

    import torch
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"Using device: {device}")
    if device == 'cuda':
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    model = PPO(
        policy="MlpPolicy",
        env=train_env,
        learning_rate=config['learning_rate'],
        n_steps=config['n_steps'],
        batch_size=config['batch_size'],
        n_epochs=config['n_epochs'],
        gamma=config['gamma'],
        ent_coef=config.get('ent_coef', 0.01),  # NEW: Encourage exploration
        clip_range=config.get('clip_range', 0.2),
        verbose=1,
        device=device,
        tensorboard_log=f"{config['model_dir']}/tensorboard/"
    )

    # Training
    logger.info(f"\nStarting training ({config['total_timesteps']:,} steps)...")
    logger.info(f"Training stocks: {len(train_data)}")
    logger.info(f"Validation stocks: {len(val_data)}")
    logger.info("Key Improvements:")
    logger.info("  - Action masking: ENABLED")
    logger.info("  - Improved reward shaping: ENABLED")
    logger.info("  - Invalid action penalty: -10.0")
    logger.info("  - Entropy coefficient: 0.01")
    logger.info("  - Extended training: 300k steps")

    start_time = datetime.now()

    model.learn(
        total_timesteps=config['total_timesteps'],
        callback=[eval_callback, checkpoint_callback, action_dist_callback, progress_callback],
        progress_bar=True
    )

    elapsed = datetime.now() - start_time
    logger.info(f"\nTraining completed! Time elapsed: {elapsed}")

    # Save final model
    final_model_path = f"{config['model_dir']}/final_model_v2.zip"
    model.save(final_model_path)
    train_env.save(f"{config['model_dir']}/final_vecnormalize_v2.pkl")

    logger.info(f"Model saved: {final_model_path}")

    return model, train_env


def evaluate_model(
    model: PPO,
    vec_normalize: VecNormalize,
    test_data: List[Tuple[str, pd.DataFrame]],
    config: Dict
) -> Dict:
    """Evaluate model performance"""
    logger.info("\n" + "="*80)
    logger.info("Evaluating Model Performance")
    logger.info("="*80)

    results = []

    for symbol, df in test_data[:10]:  # Test first 10 stocks
        logger.info(f"\nTesting {symbol}...")

        # Create test environment (no wrappers for evaluation)
        test_env = EnhancedTradingEnv(
            df=df,
            initial_cash=config['initial_cash'],
            commission_rate=config['commission_rate'],
            stamp_duty=config['stamp_duty'],
            enable_t1=config['enable_t1']
        )
        test_env = Monitor(test_env)

        test_vec_env = DummyVecEnv([lambda: test_env])
        test_vec_env = VecNormalize(
            test_vec_env,
            norm_obs=True,
            norm_reward=False,
            training=False
        )
        test_vec_env.obs_rms = vec_normalize.obs_rms
        test_vec_env.ret_rms = vec_normalize.ret_rms

        # Run backtest
        obs = test_vec_env.reset()
        done = False
        action_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            action_counts[int(action[0])] += 1
            obs, reward, done, info = test_vec_env.step(action)

            if done[0]:
                result = info[0]
                results.append({
                    'symbol': symbol,
                    'final_value': result.get('final_value', config['initial_cash']),
                    'total_return': result.get('total_return', 0),
                    'total_trades': result.get('total_trades', 0),
                    'sharpe_ratio': result.get('sharpe_ratio', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'action_distribution': action_counts
                })

                logger.info(f"  Return: {result.get('total_return', 0)*100:.2f}%")
                logger.info(f"  Sharpe: {result.get('sharpe_ratio', 0):.2f}")
                logger.info(f"  Max DD: {result.get('max_drawdown', 0)*100:.2f}%")
                logger.info(f"  Trades: {result.get('total_trades', 0)}")

                # Log action distribution
                total_actions = sum(action_counts.values())
                if total_actions > 0:
                    logger.info("  Actions:")
                    for aid, count in action_counts.items():
                        name = ['HOLD', 'BUY_25', 'BUY_50', 'SELL_50', 'SELL_ALL'][aid]
                        pct = count / total_actions * 100
                        logger.info(f"    {name}: {count} ({pct:.1f}%)")

    # Summary statistics
    summary = {
        'avg_return': np.mean([r['total_return'] for r in results]),
        'median_return': np.median([r['total_return'] for r in results]),
        'win_rate': sum(1 for r in results if r['total_return'] > 0) / len(results),
        'avg_sharpe': np.mean([r['sharpe_ratio'] for r in results]),
        'avg_max_drawdown': np.mean([r['max_drawdown'] for r in results]),
        'avg_trades': np.mean([r['total_trades'] for r in results]),
        'total_tests': len(results)
    }

    logger.info("\n" + "="*80)
    logger.info("Test Set Summary Statistics")
    logger.info("="*80)
    logger.info(f"Test stocks: {summary['total_tests']}")
    logger.info(f"Average return: {summary['avg_return']*100:.2f}%")
    logger.info(f"Median return: {summary['median_return']*100:.2f}%")
    logger.info(f"Win rate: {summary['win_rate']*100:.1f}%")
    logger.info(f"Average Sharpe: {summary['avg_sharpe']:.2f}")
    logger.info(f"Average Max DD: {summary['avg_max_drawdown']*100:.2f}%")
    logger.info(f"Average trades: {summary['avg_trades']:.1f}")

    # Save results
    os.makedirs(config['results_dir'], exist_ok=True)
    results_file = f"{config['results_dir']}/test_results_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(results_file, 'w') as f:
        json.dump({
            'summary': summary,
            'details': results,
            'config': config
        }, f, indent=2)

    logger.info(f"\nResults saved: {results_file}")

    return summary


# ====================================================================================
# Main Flow
# ====================================================================================

def main():
    """Main training flow"""
    logger.info("="*80)
    logger.info("HiddenGem Production RL Training V2 (FIXED)")
    logger.info("="*80)
    logger.info(f"Training: {CONFIG['train_start']} ~ {CONFIG['train_end']}")
    logger.info(f"Validation: {CONFIG['val_start']} ~ {CONFIG['val_end']}")
    logger.info(f"Test: {CONFIG['test_start']} ~ {CONFIG['test_end']}")
    logger.info(f"T+1 constraint: {'enabled' if CONFIG['enable_t1'] else 'disabled'}")
    logger.info("="*80)
    logger.info("\nKey Fixes:")
    logger.info("1. Action masking - prevents invalid actions")
    logger.info("2. Invalid action penalty - explicit -10 reward")
    logger.info("3. Improved reward shaping - encourages trading")
    logger.info("4. Better exploration - entropy coefficient 0.01")
    logger.info("5. Extended training - 300k timesteps (fast validation)")
    logger.info("="*80)

    # Step 1: Get stock pool
    logger.info("\n[Step 1/5] Getting stock pool...")
    if CONFIG['use_hs300']:
        all_stocks = get_hs300_stocks()
        stocks = all_stocks[:CONFIG['max_stocks']]
        logger.info(f"Using first {len(stocks)} HS300 stocks")
    else:
        stocks = get_hs300_stocks()
        stocks = stocks[:CONFIG['max_stocks']]

    # Step 2: Prepare training data
    logger.info("\n[Step 2/5] Preparing training data...")
    train_data = prepare_training_data(
        stocks,
        CONFIG['train_start'],
        CONFIG['train_end']
    )

    # Step 3: Prepare validation data
    logger.info("\n[Step 3/5] Preparing validation data...")
    val_data = prepare_training_data(
        stocks,
        CONFIG['val_start'],
        CONFIG['val_end']
    )

    # Step 4: Train model
    logger.info("\n[Step 4/5] Training model...")
    model, vec_normalize = train_model(train_data, val_data, CONFIG)

    # Step 5: Test model
    logger.info("\n[Step 5/5] Preparing test data and evaluating...")
    test_data = prepare_training_data(
        stocks,
        CONFIG['test_start'],
        CONFIG['test_end']
    )

    summary = evaluate_model(model, vec_normalize, test_data, CONFIG)

    # Final report
    logger.info("\n" + "="*80)
    logger.info("Training Completed!")
    logger.info("="*80)
    logger.info(f"Model directory: {CONFIG['model_dir']}")
    logger.info(f"Results directory: {CONFIG['results_dir']}")
    logger.info("\nNext steps:")
    logger.info(f"1. View TensorBoard: tensorboard --logdir={CONFIG['model_dir']}/tensorboard/")
    logger.info("2. Check test results meet expectations")
    logger.info("3. If satisfied, begin paper trading")
    logger.info("="*80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
