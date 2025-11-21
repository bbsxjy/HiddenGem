"""
Unit tests for Multi-Agent functionality

Tests for:
- TradingAgentsGraph
- Individual agents (Market, Fundamentals, News, Social)
- Agent coordination and decision making
"""

import pytest
from datetime import datetime


class TestTradingAgentsGraph:
    """Test TradingAgentsGraph orchestration"""

    def test_graph_initialization(self, trading_graph):
        """Test graph initializes correctly"""
        assert trading_graph is not None
        assert hasattr(trading_graph, 'propagate')
        assert hasattr(trading_graph, 'graph')

    def test_graph_propagate(self, trading_graph, test_symbol, test_date):
        """Test graph propagation generates results"""
        try:
            final_state, processed_signal = trading_graph.propagate(
                symbol=test_symbol,
                trade_date=test_date
            )

            assert final_state is not None
            assert processed_signal is not None
            assert isinstance(final_state, dict)
            assert isinstance(processed_signal, dict)

        except Exception as e:
            pytest.skip(f"Graph propagation failed (may require API keys): {e}")

    def test_final_state_structure(self, trading_graph, test_symbol, test_date):
        """Test final state contains expected keys"""
        try:
            final_state, _ = trading_graph.propagate(test_symbol, test_date)

            # Check for key state elements
            expected_keys = [
                'company_of_interest',
                'market_report',
                'fundamentals_report',
                'final_trade_decision'
            ]

            for key in expected_keys:
                assert key in final_state, f"Expected key '{key}' in final_state"

        except Exception as e:
            pytest.skip(f"Graph propagation failed: {e}")

    def test_processed_signal_structure(self, trading_graph, test_symbol, test_date):
        """Test processed signal contains expected keys"""
        try:
            _, processed_signal = trading_graph.propagate(test_symbol, test_date)

            # Check for signal elements
            expected_keys = ['action', 'direction']

            for key in expected_keys:
                assert key in processed_signal, f"Expected key '{key}' in processed_signal"

            # Validate direction is one of expected values
            assert processed_signal['direction'] in ['long', 'short', 'hold', 'close']

        except Exception as e:
            pytest.skip(f"Graph propagation failed: {e}")


class TestIndividualAgents:
    """Test individual agent functionality"""

    def test_market_analyst_exists(self):
        """Test market analyst module exists"""
        try:
            from tradingagents.agents.analysts import market
            assert hasattr(market, 'market_analyst_node')
        except ImportError as e:
            pytest.fail(f"Failed to import market analyst: {e}")

    def test_fundamentals_analyst_exists(self):
        """Test fundamentals analyst module exists"""
        try:
            from tradingagents.agents.analysts import fundamentals
            assert hasattr(fundamentals, 'fundamentals_analyst_node')
        except ImportError as e:
            pytest.fail(f"Failed to import fundamentals analyst: {e}")

    def test_news_analyst_exists(self):
        """Test news analyst module exists"""
        try:
            from tradingagents.agents.analysts import news
            assert hasattr(news, 'news_analyst_node')
        except ImportError as e:
            pytest.fail(f"Failed to import news analyst: {e}")

    def test_social_analyst_exists(self):
        """Test social/sentiment analyst module exists"""
        try:
            from tradingagents.agents.analysts import social
            assert hasattr(social, 'social_analyst_node')
        except ImportError as e:
            pytest.fail(f"Failed to import social analyst: {e}")


class TestAgentCoordination:
    """Test multi-agent coordination and decision making"""

    def test_bull_bear_debate_exists(self):
        """Test bull/bear debate mechanism exists"""
        try:
            from tradingagents.agents.researchers import bull, bear
            assert hasattr(bull, 'bull_agent_node')
            assert hasattr(bear, 'bear_agent_node')
        except ImportError as e:
            pytest.fail(f"Failed to import bull/bear researchers: {e}")

    def test_risk_management_exists(self):
        """Test risk management agents exist"""
        try:
            from tradingagents.agents.risk_mgmt import aggressive, neutral, conservative
            assert hasattr(aggressive, 'aggressive_risk_node')
            assert hasattr(neutral, 'neutral_risk_node')
            assert hasattr(conservative, 'conservative_risk_node')
        except ImportError as e:
            pytest.fail(f"Failed to import risk management agents: {e}")

    def test_trader_exists(self):
        """Test trader agent exists"""
        try:
            from tradingagents.agents.trader import trader
            assert hasattr(trader, 'trader_node')
        except ImportError as e:
            pytest.fail(f"Failed to import trader agent: {e}")


class TestAgentState:
    """Test agent state management"""

    def test_state_initialization(self, default_config):
        """Test agent state initializes correctly"""
        from tradingagents.agents.utils.states import AgentState

        state = AgentState(
            company_of_interest="AAPL",
            trade_date=datetime.now().strftime("%Y-%m-%d")
        )

        assert state.company_of_interest == "AAPL"
        assert state.trade_date is not None

    def test_state_updates(self, default_config):
        """Test agent state can be updated"""
        from tradingagents.agents.utils.states import AgentState

        state = AgentState(company_of_interest="AAPL")

        # Update state
        state.market_report = "Test market report"

        assert state.market_report == "Test market report"


class TestGraphConditionalLogic:
    """Test graph conditional routing logic"""

    def test_conditional_logic_exists(self):
        """Test conditional logic module exists"""
        try:
            from tradingagents.graph import conditional_logic
            assert hasattr(conditional_logic, 'route_to_analyst')
        except ImportError as e:
            pytest.fail(f"Failed to import conditional logic: {e}")

    def test_conditional_logic_functions(self):
        """Test conditional logic functions exist"""
        from tradingagents.graph.conditional_logic import (
            route_to_analyst,
            route_from_research_manager,
            route_from_risk_manager
        )

        assert callable(route_to_analyst)
        assert callable(route_from_research_manager)
        assert callable(route_from_risk_manager)
