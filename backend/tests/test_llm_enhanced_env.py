"""
Unit tests for LLMEnhancedTradingEnv

测试LLM增强的交易环境的各个功能组件。
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.rl.llm_enhanced_env import LLMEnhancedTradingEnv


@pytest.fixture
def sample_data():
    """创建示例股票数据"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    data = pd.DataFrame({
        'date': dates,
        'open': 100 + np.random.randn(100) * 2,
        'high': 102 + np.random.randn(100) * 2,
        'low': 98 + np.random.randn(100) * 2,
        'close': 100 + np.random.randn(100) * 2,
        'volume': 1000000 + np.random.randint(-100000, 100000, 100),
        'tic': ['600519.SH'] * 100,
        'day': dates
    })

    # 添加技术指标
    data['macd'] = np.random.randn(100) * 0.5
    data['rsi_30'] = 50 + np.random.randn(100) * 20
    data['cci_30'] = np.random.randn(100) * 50
    data['dx_30'] = 20 + np.random.randn(100) * 10

    return data


@pytest.fixture
def mock_trading_graph():
    """创建mock TradingAgentsGraph"""
    mock_graph = Mock()

    mock_final_state = {
        'company_of_interest': '600519.SH',
        'market_report': '技术面分析：看涨信号',
        'investment_debate_state': {'judge_decision': '建议买入'}
    }

    mock_signal = {
        'direction': 'long',
        'confidence': 0.85,
        'risk_level': 0.3,
        'agent_agreement': 0.8
    }

    mock_graph.propagate.return_value = (mock_final_state, mock_signal)
    return mock_graph


@pytest.fixture
def mock_memory_manager():
    """创建mock MemoryManager"""
    mock_memory = Mock()

    mock_episodes = [
        {
            'context': {'symbol': '600519.SH'},
            'outcome': {'return': 0.05},
            'similarity_score': 0.9
        }
    ]

    mock_memory.retrieve_episodes.return_value = mock_episodes
    return mock_memory


@pytest.fixture
def env(sample_data, mock_trading_graph, mock_memory_manager):
    """创建测试环境实例"""
    return LLMEnhancedTradingEnv(
        df=sample_data,
        trading_graph=mock_trading_graph,
        memory_manager=mock_memory_manager,
        initial_cash=100000.0
    )


def test_environment_initialization(env):
    """测试环境初始化"""
    assert env.initial_cash == 100000.0
    assert env.action_space.n == 6
    # Observation space is dynamically updated on first reset/step
    # Just check it has a reasonable dimension
    assert env.observation_space.shape[0] > 0


def test_reset_functionality(env):
    """测试reset功能"""
    obs, info = env.reset()

    assert obs.shape == env.observation_space.shape
    assert np.all(np.isfinite(obs))
    assert 'day' in info
    assert env.cash == env.initial_cash
    assert env.shares_held == 0


def test_step_basic(env):
    """测试基本step功能"""
    env.reset()

    obs, reward, terminated, truncated, info = env.step(0)  # HOLD

    assert isinstance(obs, np.ndarray)
    assert isinstance(reward, (float, np.floating))
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)


def test_buy_action(env):
    """测试买入动作"""
    env.reset()

    initial_cash = env.cash

    obs, reward, terminated, truncated, info = env.step(1)  # BUY 10%

    assert env.cash <= initial_cash  # 现金应减少或不变
    assert env.shares_held >= 0  # 持仓非负


def test_sell_with_no_shares(env):
    """测试无持仓时卖出"""
    env.reset()

    initial_cash = env.cash

    obs, reward, terminated, truncated, info = env.step(3)  # SELL 10%

    assert env.cash == initial_cash  # 现金不变
    assert env.shares_held == 0  # 持仓仍为0


def test_complete_episode(env):
    """测试完整episode"""
    obs, info = env.reset()

    steps = 0
    max_steps = 20

    while steps < max_steps:
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)

        assert np.all(np.isfinite(obs))
        assert np.isfinite(reward)
        assert env.cash >= 0
        assert env.shares_held >= 0

        if terminated or truncated:
            break

        steps += 1

    print(f"Episode completed: {steps} steps")
    assert steps > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
