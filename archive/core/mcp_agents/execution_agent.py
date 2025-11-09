"""
Execution Agent.
Coordinates signal aggregation and generates final trading decisions.

Note: Most execution logic is in the MCPOrchestrator.
This agent provides a wrapper for direct execution requests.
"""

import time
from typing import Dict, Any, Optional

from loguru import logger

from core.mcp_agents.base_agent import BaseAgent
from core.data.models import AgentAnalysisResult, SignalDirection
from config.agents_config import agents_config


class ExecutionAgent(BaseAgent):
    """
    Execution Agent.

    Responsible for:
    - Final signal aggregation (handled by Orchestrator)
    - Order generation
    - Execution monitoring
    """

    def __init__(self, redis_client=None):
        """Initialize Execution Agent."""
        config = agents_config.EXECUTION_AGENT
        super().__init__(config, redis_client)

        self.min_signal_strength = config.params.get("min_signal_strength", 0.60)
        self.min_agent_agreement = config.params.get("min_agent_agreement", 3)

    async def analyze(self, symbol: Optional[str] = None, **kwargs) -> AgentAnalysisResult:
        """
        Execution agent analysis (placeholder).

        In practice, execution logic is handled by MCPOrchestrator.
        This method is provided for API compatibility.
        """
        start_time = time.time()

        try:
            logger.info(f"Execution agent called for {symbol}")

            analysis_results = {
                'message': 'Execution is handled by MCPOrchestrator',
                'min_signal_strength': self.min_signal_strength,
                'min_agent_agreement': self.min_agent_agreement
            }

            execution_time = int((time.time() - start_time) * 1000)

            result = self._create_analysis_result(
                symbol=symbol,
                score=None,
                direction=SignalDirection.HOLD,
                confidence=0.0,
                analysis=analysis_results,
                reasoning="执行逻辑由MCPOrchestrator处理",
                execution_time_ms=execution_time
            )

            return result

        except Exception as e:
            logger.exception(f"Error in execution agent: {e}")
            return self._create_error_result(symbol, str(e))
