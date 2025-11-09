"""
Base agent class for MCP (Model Context Protocol) agents.
All agents inherit from this class and implement the analyze() method.
"""

import time
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from loguru import logger
from redis.asyncio import Redis

from config.settings import settings
from config.agents_config import AgentConfig
from core.data.models import MCPRequest, MCPResponse, MCPError, AgentAnalysisResult


class BaseAgent(ABC):
    """
    Base class for all MCP agents.

    Provides:
    - JSON-RPC 2.0 message handling
    - Async execution
    - Error handling
    - Caching
    - Logging
    """

    def __init__(self, config: AgentConfig, redis_client: Optional[Redis] = None):
        """
        Initialize base agent.

        Args:
            config: Agent configuration
            redis_client: Optional Redis client for caching
        """
        self.config = config
        self.name = config.name
        self.redis_client = redis_client
        self.is_enabled = config.enabled

        logger.info(f"Initialized agent: {self.name}")

    @abstractmethod
    async def analyze(self, symbol: Optional[str] = None, **kwargs) -> AgentAnalysisResult:
        """
        Perform analysis.

        This method must be implemented by all agents.

        Args:
            symbol: Stock symbol to analyze (None for market-wide analysis)
            **kwargs: Additional parameters specific to the agent

        Returns:
            AgentAnalysisResult: Analysis result
        """
        pass

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Handle MCP JSON-RPC 2.0 request.

        Args:
            request: MCP request

        Returns:
            MCPResponse: MCP response
        """
        try:
            # Validate request
            if request.jsonrpc != "2.0":
                return self._create_error_response(
                    request.id,
                    -32600,
                    "Invalid Request: jsonrpc must be 2.0"
                )

            # Route method
            if request.method == "analyze":
                result = await self._execute_with_timeout(
                    self.analyze,
                    **(request.params or {})
                )
                return MCPResponse(
                    jsonrpc="2.0",
                    result=result.model_dump(),
                    id=request.id
                )

            elif request.method == "ping":
                return MCPResponse(
                    jsonrpc="2.0",
                    result={"status": "ok", "agent": self.name},
                    id=request.id
                )

            elif request.method == "get_config":
                return MCPResponse(
                    jsonrpc="2.0",
                    result=self.config.model_dump(),
                    id=request.id
                )

            else:
                return self._create_error_response(
                    request.id,
                    -32601,
                    f"Method not found: {request.method}"
                )

        except asyncio.TimeoutError:
            logger.error(f"Agent {self.name} timed out")
            return self._create_error_response(
                request.id,
                -32000,
                f"Agent timeout after {self.config.timeout}s"
            )

        except Exception as e:
            logger.exception(f"Error in agent {self.name}: {e}")
            return self._create_error_response(
                request.id,
                -32603,
                f"Internal error: {str(e)}"
            )

    async def _execute_with_timeout(self, func, **kwargs):
        """
        Execute function with timeout.

        Args:
            func: Async function to execute
            **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
        """
        return await asyncio.wait_for(
            func(**kwargs),
            timeout=self.config.timeout
        )

    async def _execute_with_retry(self, func, **kwargs):
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries fail
        """
        last_error = None

        for attempt in range(self.config.retry_attempts + 1):
            try:
                return await func(**kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.config.retry_attempts:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Agent {self.name} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Agent {self.name} failed after {attempt + 1} attempts")

        raise last_error

    async def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis result.

        Args:
            cache_key: Cache key

        Returns:
            Cached result or None if not found/expired
        """
        if not self.redis_client or self.config.cache_ttl == 0:
            return None

        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for {cache_key}")
                import json
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None

    async def set_cached_result(self, cache_key: str, data: Dict[str, Any]):
        """
        Cache analysis result.

        Args:
            cache_key: Cache key
            data: Data to cache
        """
        if not self.redis_client or self.config.cache_ttl == 0:
            return

        try:
            import json
            await self.redis_client.setex(
                cache_key,
                self.config.cache_ttl,
                json.dumps(data, default=str)
            )
            logger.debug(f"Cached result for {cache_key}")
        except Exception as e:
            logger.warning(f"Error writing cache: {e}")

    def _create_cache_key(self, symbol: Optional[str], **kwargs) -> str:
        """
        Create cache key for analysis.

        Args:
            symbol: Stock symbol
            **kwargs: Additional parameters

        Returns:
            Cache key
        """
        import hashlib
        import json

        key_data = {
            "agent": self.name,
            "symbol": symbol,
            **kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        return f"agent:{self.name}:{key_hash}"

    def _create_error_response(
        self,
        request_id: Optional[str],
        code: int,
        message: str,
        data: Any = None
    ) -> MCPResponse:
        """
        Create MCP error response.

        Args:
            request_id: Request ID
            code: Error code
            message: Error message
            data: Optional error data

        Returns:
            MCPResponse with error
        """
        error = MCPError(code=code, message=message, data=data)
        return MCPResponse(
            jsonrpc="2.0",
            error=error.model_dump(),
            id=request_id
        )

    def _create_analysis_result(
        self,
        symbol: Optional[str],
        score: Optional[float],
        direction: Optional[str],
        confidence: Optional[float],
        analysis: Dict[str, Any],
        reasoning: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> AgentAnalysisResult:
        """
        Create standardized analysis result.

        Args:
            symbol: Stock symbol
            score: Agent-specific score
            direction: Signal direction (long/short/hold/close)
            confidence: Confidence level (0.0 to 1.0)
            analysis: Detailed analysis data
            reasoning: Human-readable reasoning
            execution_time_ms: Execution time in milliseconds

        Returns:
            AgentAnalysisResult
        """
        return AgentAnalysisResult(
            agent_name=self.name,
            symbol=symbol,
            score=score,
            direction=direction,
            confidence=confidence,
            analysis=analysis,
            reasoning=reasoning,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow(),
            is_error=False,
            error_message=None
        )

    def _create_error_result(
        self,
        symbol: Optional[str],
        error_message: str
    ) -> AgentAnalysisResult:
        """
        Create error analysis result.

        Args:
            symbol: Stock symbol
            error_message: Error message

        Returns:
            AgentAnalysisResult with error
        """
        return AgentAnalysisResult(
            agent_name=self.name,
            symbol=symbol,
            score=None,
            direction=None,
            confidence=None,
            analysis={},
            reasoning=None,
            execution_time_ms=None,
            timestamp=datetime.utcnow(),
            is_error=True,
            error_message=error_message
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Returns:
            Health check result
        """
        return {
            "agent": self.name,
            "status": "healthy" if self.is_enabled else "disabled",
            "enabled": self.is_enabled,
            "config": {
                "timeout": self.config.timeout,
                "retry_attempts": self.config.retry_attempts,
                "cache_ttl": self.config.cache_ttl,
                "weight": self.config.weight
            }
        }

    def log_analysis(self, result: AgentAnalysisResult):
        """
        Log analysis result.

        Args:
            result: Analysis result
        """
        if result.is_error:
            logger.error(
                f"Agent {self.name} error for {result.symbol}: {result.error_message}"
            )
        else:
            logger.info(
                f"Agent {self.name} analyzed {result.symbol}: "
                f"direction={result.direction}, confidence={result.confidence:.2f}, "
                f"time={result.execution_time_ms}ms"
            )

    async def save_analysis_to_db(self, result: AgentAnalysisResult, db_session):
        """
        Save analysis result to database.

        Args:
            result: Analysis result
            db_session: Database session
        """
        from database.models import AgentAnalysis

        try:
            db_analysis = AgentAnalysis(
                agent_name=result.agent_name,
                symbol=result.symbol,
                score=result.score,
                direction=result.direction,
                confidence=result.confidence,
                analysis=result.analysis,
                reasoning=result.reasoning,
                execution_time_ms=result.execution_time_ms,
                is_error=result.is_error,
                error_message=result.error_message,
                timestamp=result.timestamp
            )

            db_session.add(db_analysis)
            await db_session.commit()

            logger.debug(f"Saved analysis from {self.name} to database")

        except Exception as e:
            logger.error(f"Error saving analysis to database: {e}")
            await db_session.rollback()


class AgentPool:
    """Pool of agents for parallel execution."""

    def __init__(self, agents: Dict[str, BaseAgent]):
        """
        Initialize agent pool.

        Args:
            agents: Dictionary of agent name to agent instance
        """
        self.agents = agents
        logger.info(f"Initialized agent pool with {len(agents)} agents")

    async def execute_all(
        self,
        symbol: Optional[str] = None,
        **kwargs
    ) -> Dict[str, AgentAnalysisResult]:
        """
        Execute all enabled agents in parallel.

        Args:
            symbol: Stock symbol to analyze
            **kwargs: Additional parameters

        Returns:
            Dictionary of agent name to analysis result
        """
        # Filter enabled agents
        enabled_agents = {
            name: agent
            for name, agent in self.agents.items()
            if agent.is_enabled
        }

        if not enabled_agents:
            logger.warning("No enabled agents in pool")
            return {}

        # Execute agents in parallel using asyncio.gather
        logger.info(f"Executing {len(enabled_agents)} agents in parallel for {symbol}")

        tasks = [
            agent.analyze(symbol=symbol, **kwargs)
            for agent in enabled_agents.values()
        ]
        names = list(enabled_agents.keys())

        # Gather results with exception handling
        gathered_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        results = {}
        for name, result in zip(names, gathered_results):
            if isinstance(result, Exception):
                logger.error(f"Agent {name} failed: {result}")
                results[name] = enabled_agents[name]._create_error_result(
                    symbol,
                    str(result)
                )
            else:
                results[name] = result
                enabled_agents[name].log_analysis(result)

        return results

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Health check all agents.

        Returns:
            Dictionary of agent name to health status
        """
        results = {}
        for name, agent in self.agents.items():
            results[name] = await agent.health_check()
        return results
