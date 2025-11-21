"""
Unit tests for RL Training functionality

Tests for:
- EnhancedTradingEnv
- RL model loading and prediction
- Training scripts
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

# Import RL components
try:
    from trading.enhanced_trading_env import EnhancedTradingEnv
    from stable_baselines3 import PPO
    RL_AVAILABLE = True
except ImportError:
    RL_AVAILABLE = False


@pytest.mark.skipif(not RL_AVAILABLE, reason="RL dependencies not installed")
class TestEnhancedTradingEnv:
    """Test EnhancedTradingEnv functionality"""

    @pytest.fixture
    def sample_df(self):
        """Create sample price data"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'date': dates,
            'open': np.random.uniform(10, 20, 100),
            'high': np.random.uniform(15, 25, 100),
            'low': np.random.uniform(5, 15, 100),
            'close': np.random.uniform(10, 20, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })
        df['date'] = pd.to_datetime(df['date'])
        return df

    def test_env_initialization(self, sample_df):
        """Test environment initializes correctly"""
        env = EnhancedTradingEnv(
            df=sample_df,
            initial_cash=100000.0,
            commission_rate=0.0003,
            enable_t1=True
        )

        assert env.initial_cash == 100000.0
        assert env.commission_rate == 0.0003
        assert env.enable_t1 is True
        assert len(env.df) == 100

    def test_env_reset(self, sample_df):
        """Test environment reset"""
        env = EnhancedTradingEnv(df=sample_df, initial_cash=100000.0)

        obs, info = env.reset()

        assert obs is not None
        assert isinstance(obs, np.ndarray)
        assert env.cash == 100000.0
        assert env.shares_held == 0

    def test_env_action_space(self, sample_df):
        """Test action space is correct (5 actions)"""
        env = EnhancedTradingEnv(df=sample_df, initial_cash=100000.0)

        # Action space should be Discrete(5)
        assert env.action_space.n == 5  # HOLD, BUY_25, BUY_50, SELL_50, SELL_ALL

    def test_env_step_hold(self, sample_df):
        """Test HOLD action"""
        env = EnhancedTradingEnv(df=sample_df, initial_cash=100000.0)
        env.reset()

        # Action 0 = HOLD
        obs, reward, done, truncated, info = env.step(0)

        assert env.shares_held == 0  # No position change
        assert env.cash == 100000.0  # No cash change

    def test_env_buy_action(self, sample_df):
        """Test BUY actions"""
        env = EnhancedTradingEnv(df=sample_df, initial_cash=100000.0)
        env.reset()

        initial_cash = env.cash

        # Action 1 = BUY_25 (买入25%资金)
        obs, reward, done, truncated, info = env.step(1)

        assert env.cash < initial_cash  # Cash decreased
        assert env.shares_held > 0  # Shares increased

    def test_env_sell_action(self, sample_df):
        """Test SELL actions"""
        env = EnhancedTradingEnv(df=sample_df, initial_cash=100000.0)
        env.reset()

        # First buy some shares
        env.step(2)  # BUY_50

        shares_before = env.shares_held
        cash_before = env.cash

        # Then sell half
        env.step(3)  # SELL_50

        assert env.shares_held < shares_before  # Shares decreased
        assert env.cash > cash_before  # Cash increased

    def test_env_episode_completion(self, sample_df):
        """Test environment completes episode"""
        env = EnhancedTradingEnv(df=sample_df, initial_cash=100000.0)
        env.reset()

        done = False
        truncated = False
        steps = 0

        while not (done or truncated) and steps < 200:
            action = env.action_space.sample()  # Random action
            obs, reward, done, truncated, info = env.step(action)
            steps += 1

        assert done or truncated  # Episode should end
        assert steps <= len(sample_df)  # Should not exceed data length


@pytest.mark.skipif(not RL_AVAILABLE, reason="RL dependencies not installed")
class TestRLModel:
    """Test RL model loading and prediction"""

    def test_model_loading(self):
        """Test loading a trained RL model"""
        model_path = Path("models/production/best_model.zip")

        if not model_path.exists():
            pytest.skip(f"Model not found at {model_path}")

        model = PPO.load(str(model_path))

        assert model is not None
        assert hasattr(model, 'predict')

    def test_model_prediction(self, sample_df):
        """Test model makes predictions"""
        model_path = Path("models/production/best_model.zip")

        if not model_path.exists():
            pytest.skip(f"Model not found at {model_path}")

        model = PPO.load(str(model_path))
        env = EnhancedTradingEnv(df=sample_df, initial_cash=100000.0)

        obs, _ = env.reset()

        action, _ = model.predict(obs, deterministic=True)

        assert action is not None
        assert 0 <= action < 5  # Valid action range


class TestRLTrainingScripts:
    """Test RL training scripts exist and have correct structure"""

    def test_training_scripts_exist(self):
        """Test training scripts exist"""
        scripts = [
            "scripts/train_rl_model.py",
            "scripts/test_model_with_env.py",
        ]

        for script_path in scripts:
            path = Path(script_path)
            assert path.exists(), f"Training script {script_path} should exist"

    def test_env_script_imports(self):
        """Test enhanced_trading_env script can be imported"""
        try:
            from trading import enhanced_trading_env
            assert hasattr(enhanced_trading_env, 'EnhancedTradingEnv')
        except ImportError as e:
            pytest.fail(f"Failed to import enhanced_trading_env: {e}")
