"""
Pytest configuration and fixtures

Provides common fixtures for testing TradingAgents-CN
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


@pytest.fixture(scope="session")
def default_config():
    """Provide default configuration"""
    return DEFAULT_CONFIG.copy()


@pytest.fixture(scope="session")
def trading_graph(default_config):
    """Provide a TradingAgentsGraph instance"""
    return TradingAgentsGraph(config=default_config)


@pytest.fixture
def test_symbol():
    """Provide a test stock symbol"""
    return "600519.SH"  # 贵州茅台


@pytest.fixture
def test_date():
    """Provide a test date"""
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


@pytest.fixture
def date_range():
    """Provide a test date range"""
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)
    return {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }
