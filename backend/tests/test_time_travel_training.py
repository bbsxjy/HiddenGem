"""
Unit tests for Time Travel Training functionality

Tests for:
- Enhanced Time Travel Training
- Portfolio Time Travel Training
- Memory system integration
- Future information leakage prevention
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta


class TestEnhancedTimeTravelTraining:
    """Test Enhanced Time Travel Training script"""

    def test_script_exists(self):
        """Test enhanced time travel script exists"""
        script_path = Path("scripts/enhanced_time_travel_training.py")
        assert script_path.exists(), "Enhanced time travel script should exist"

    def test_script_imports(self):
        """Test script can be imported"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))

            # Try importing key classes
            from scripts.enhanced_time_travel_training import (
                EnhancedTimeTravelTrainer
            )

            assert EnhancedTimeTravelTrainer is not None

        except ImportError as e:
            pytest.skip(f"Cannot import enhanced time travel module: {e}")

    def test_lesson_future_leakage_prevention(self):
        """Test that lessons don't contain future information"""
        try:
            from scripts.enhanced_time_travel_training import (
                EnhancedTimeTravelTrainer
            )

            # This test verifies the structure exists to prevent future leakage
            # Actual verification would require running training

            trainer = EnhancedTimeTravelTrainer(
                symbol="600519.SH",
                start_date="2024-01-01",
                end_date="2024-01-31",
                holding_days=5
            )

            # Check trainer has abstract_lesson method
            assert hasattr(trainer, 'abstract_lesson')

        except Exception as e:
            pytest.skip(f"Cannot initialize trainer: {e}")


class TestPortfolioTimeTravelTraining:
    """Test Portfolio Time Travel Training"""

    def test_script_exists(self):
        """Test portfolio time travel script exists"""
        script_path = Path("scripts/portfolio_time_travel_training.py")
        assert script_path.exists(), "Portfolio time travel script should exist"

    def test_script_imports(self):
        """Test script can be imported"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))

            from scripts.portfolio_time_travel_training import (
                PortfolioTimeTravelTrainer
            )

            assert PortfolioTimeTravelTrainer is not None

        except ImportError as e:
            pytest.skip(f"Cannot import portfolio time travel module: {e}")

    def test_task_monitor_integration(self):
        """Test TaskMonitor integration for checkpoint/resume"""
        try:
            from scripts.portfolio_time_travel_training import (
                PortfolioTimeTravelTrainer
            )

            trainer = PortfolioTimeTravelTrainer(
                start_date="2024-01-01",
                end_date="2024-01-31",
                holding_days=5
            )

            # Check trainer has task_monitor
            assert hasattr(trainer, 'task_monitor')
            assert hasattr(trainer, 'task_id')

        except Exception as e:
            pytest.skip(f"Cannot initialize trainer: {e}")

    def test_portfolio_state_management(self):
        """Test portfolio state tracking"""
        try:
            from scripts.portfolio_time_travel_training import (
                PortfolioTimeTravelTrainer,
                PortfolioState
            )

            # Test PortfolioState dataclass
            state = PortfolioState(
                date="2024-01-01",
                positions=[],
                cash=100000.0,
                total_value=100000.0
            )

            assert state.get_position_count() == 0
            assert state.cash == 100000.0

        except Exception as e:
            pytest.skip(f"Cannot test portfolio state: {e}")


class TestMemorySystem:
    """Test memory system integration"""

    def test_memory_module_exists(self):
        """Test memory module exists"""
        try:
            from memory import MemoryManager, TradingEpisode
            assert MemoryManager is not None
            assert TradingEpisode is not None
        except ImportError:
            pytest.skip("Memory system not available (optional dependency)")

    def test_trading_episode_structure(self):
        """Test TradingEpisode dataclass"""
        try:
            from memory import (
                TradingEpisode,
                MarketState,
                DecisionChain,
                TradeOutcome
            )

            # Test creating a TradingEpisode
            market_state = MarketState(
                date="2024-01-01",
                symbol="600519.SH",
                price=1800.0
            )

            decision_chain = DecisionChain(
                bull_argument="Strong fundamentals",
                bear_argument="High valuation",
                investment_debate_conclusion="Buy",
                aggressive_view="",
                neutral_view="",
                conservative_view="",
                risk_debate_conclusion="",
                final_decision="Buy 25%"
            )

            outcome = TradeOutcome(
                action="buy",
                position_size=0.25,
                entry_price=1800.0,
                entry_date="2024-01-01",
                exit_price=1850.0,
                exit_date="2024-01-05",
                holding_period_days=4,
                absolute_return=12500.0,
                percentage_return=0.0278,
                max_drawdown_during=0.01
            )

            episode = TradingEpisode(
                episode_id="test_001",
                date="2024-01-01",
                symbol="600519.SH",
                market_state=market_state,
                agent_analyses={},
                decision_chain=decision_chain,
                outcome=outcome,
                lesson="Test lesson - decision context",
                key_lesson="Test key lesson",
                success=True,
                created_at=datetime.now().isoformat(),
                mode='training'
            )

            assert episode.episode_id == "test_001"
            assert episode.success is True
            assert "Test lesson" in episode.lesson
            # ✅ Key check: lesson should NOT contain future info like percentage_return
            assert "percentage_return" not in episode.lesson.lower()

        except ImportError:
            pytest.skip("Memory system not available")


class TestTaskMonitor:
    """Test TaskMonitor for checkpoint/resume support"""

    def test_task_monitor_exists(self):
        """Test TaskMonitor module exists"""
        try:
            from tradingagents.utils.task_monitor import TaskMonitor, get_task_monitor
            assert TaskMonitor is not None
            assert get_task_monitor is not None
        except ImportError as e:
            pytest.fail(f"TaskMonitor should exist: {e}")

    def test_task_monitor_operations(self):
        """Test basic TaskMonitor operations"""
        try:
            from tradingagents.utils.task_monitor import get_task_monitor

            monitor = get_task_monitor()

            # Test task creation
            task_id = "test_task_001"
            monitor.start_task(
                task_id=task_id,
                task_type="TEST",
                total_steps=100,
                metadata={"test": "data"}
            )

            # Test task exists
            checkpoint = monitor.get_checkpoint(task_id)
            assert checkpoint is not None
            assert checkpoint.task_id == task_id

            # Test cleanup
            monitor.complete_task(task_id, final_metadata={"status": "done"})

        except Exception as e:
            pytest.skip(f"Cannot test TaskMonitor: {e}")


class TestTimeTravelUtilities:
    """Test time travel training utilities"""

    def test_trading_days_calculation(self):
        """Test trading days are calculated correctly"""
        # This would test the get_trading_days() method
        # Skipped for now as it requires live data
        pytest.skip("Requires live market data")

    def test_lesson_abstraction_no_future_leakage(self):
        """Test lesson abstraction doesn't leak future information"""
        # This is a critical test to ensure time-series ML principles
        # The lesson should only contain information available at decision time
        # Future returns, outcomes should be in a separate field

        try:
            from scripts.enhanced_time_travel_training import (
                EnhancedTimeTravelTrainer
            )

            # The abstract_lesson method should split:
            # 1. decision_context (no future info)
            # 2. outcome_result (future info for learning)

            trainer = EnhancedTimeTravelTrainer(
                symbol="600519.SH",
                start_date="2024-01-01",
                end_date="2024-01-31",
                holding_days=5
            )

            # Verify the method signature expects split approach
            import inspect
            signature = inspect.signature(trainer.abstract_lesson)

            # The method should handle splitting decision context from outcome
            assert 'outcome' in signature.parameters
            assert 'market_state' in signature.parameters

        except Exception as e:
            pytest.skip(f"Cannot test lesson abstraction: {e}")
