"""
MCP Orchestrator for coordinating multiple agents.
Handles agent registration, task dispatching, and signal aggregation.
Integrates LLM for intelligent signal analysis.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from decimal import Decimal

from loguru import logger
from redis.asyncio import Redis

from config.agents_config import agents_config
from config.settings import settings
from core.mcp_agents.base_agent import BaseAgent, AgentPool
from core.data.models import (
    AgentAnalysisResult,
    TradingSignal,
    AggregatedSignal,
    SignalDirection
)
from core.utils.llm_service import get_llm_service


class MCPOrchestrator:
    """
    Orchestrator for MCP agents.

    Responsibilities:
    - Register and manage agents
    - Dispatch analysis tasks to agents in parallel
    - Aggregate analysis results into trading signals
    - Monitor agent health
    """

    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize MCP orchestrator.

        Args:
            redis_client: Optional Redis client for agent caching
        """
        self.redis_client = redis_client
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_pool: Optional[AgentPool] = None

        logger.info("Initialized MCP Orchestrator")

    def register_agent(self, agent: BaseAgent):
        """
        Register an agent.

        Args:
            agent: Agent instance
        """
        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")

        # Update agent pool
        self.agent_pool = AgentPool(self.agents)

    def unregister_agent(self, agent_name: str):
        """
        Unregister an agent.

        Args:
            agent_name: Name of agent to unregister
        """
        if agent_name in self.agents:
            del self.agents[agent_name]
            logger.info(f"Unregistered agent: {agent_name}")
            self.agent_pool = AgentPool(self.agents)

    async def analyze_symbol(
        self,
        symbol: str,
        save_to_db: bool = True,
        db_session=None
    ) -> Dict[str, AgentAnalysisResult]:
        """
        Analyze a symbol using all enabled agents in parallel.

        Args:
            symbol: Stock symbol to analyze
            save_to_db: Whether to save results to database
            db_session: Database session (required if save_to_db=True)

        Returns:
            Dictionary of agent name to analysis result
        """
        if not self.agent_pool:
            logger.warning("No agents registered")
            return {}

        logger.info(f"Starting multi-agent analysis for {symbol}")

        # Execute all agents in parallel
        results = await self.agent_pool.execute_all(symbol=symbol)

        # Save to database if requested
        if save_to_db and db_session:
            for agent_name, result in results.items():
                if agent_name in self.agents:
                    try:
                        await self.agents[agent_name].save_analysis_to_db(
                            result,
                            db_session
                        )
                    except Exception as e:
                        logger.error(f"Error saving {agent_name} result: {e}")

        logger.info(
            f"Completed analysis for {symbol}: "
            f"{len(results)} agents, "
            f"{sum(1 for r in results.values() if r.is_error)} errors"
        )

        return results

    async def generate_trading_signal(
        self,
        symbol: str,
        agent_results: Optional[Dict[str, AgentAnalysisResult]] = None,
        save_to_db: bool = True,
        db_session=None
    ) -> tuple[Optional[AggregatedSignal], Optional[Dict[str, Any]]]:
        """
        Generate aggregated trading signal from agent analyses using LLM.

        Args:
            symbol: Stock symbol
            agent_results: Optional pre-computed agent results
            save_to_db: Whether to save signal to database
            db_session: Database session

        Returns:
            Tuple of (Aggregated trading signal or None if criteria not met, LLM analysis dict or None)
        """
        # Get agent results if not provided
        if agent_results is None:
            agent_results = await self.analyze_symbol(
                symbol,
                save_to_db=save_to_db,
                db_session=db_session
            )

        # Filter out errors
        valid_results = {
            name: result
            for name, result in agent_results.items()
            if not result.is_error and result.direction is not None
        }

        if not valid_results:
            logger.warning(f"No valid agent results for {symbol}")
            return None, None

        # Use LLM for intelligent signal analysis if enabled
        if settings.llm_enabled:
            try:
                logger.info(f"Using LLM for intelligent signal analysis of {symbol}")
                llm_analysis, llm_raw_data = await self._generate_signal_with_llm(
                    symbol,
                    agent_results
                )
                return llm_analysis, llm_raw_data
            except Exception as e:
                logger.error(f"LLM analysis failed for {symbol}: {e}, falling back to rule-based aggregation")
                # Fall back to traditional rule-based aggregation
                signal = await self._generate_signal_rule_based(symbol, valid_results)
                return signal, None
        else:
            # Use traditional rule-based aggregation
            logger.info(f"Using rule-based signal aggregation for {symbol}")
            signal = await self._generate_signal_rule_based(symbol, valid_results)
            return signal, None

    async def _generate_signal_with_llm(
        self,
        symbol: str,
        agent_results: Dict[str, AgentAnalysisResult]
    ) -> tuple[Optional[AggregatedSignal], Dict[str, Any]]:
        """
        Generate trading signal using LLM analysis.

        Args:
            symbol: Stock symbol
            agent_results: Results from all agents

        Returns:
            Tuple of (Aggregated signal or None if below threshold, LLM analysis data dict)
        """
        # Get LLM service
        llm_service = get_llm_service()

        # Call LLM for analysis
        llm_result = await llm_service.analyze_trading_signal(
            symbol=symbol,
            agent_results=agent_results,
            market_context=None  # Can add market context here
        )

        # Parse LLM recommendation
        direction_str = llm_result.get("recommended_direction", "HOLD")
        confidence = llm_result.get("confidence", 0.5)
        reasoning = llm_result.get("reasoning", "LLM分析")
        risk_assessment = llm_result.get("risk_assessment", "")
        key_factors = llm_result.get("key_factors", [])

        # Convert direction string to enum
        try:
            direction = SignalDirection[direction_str]
        except KeyError:
            logger.warning(f"Invalid direction from LLM: {direction_str}, using HOLD")
            direction = SignalDirection.HOLD

        # Prepare LLM analysis data (always returned, even if signal is rejected)
        llm_analysis_data = {
            "recommended_direction": direction.value,
            "confidence": confidence,
            "reasoning": reasoning,
            "risk_assessment": risk_assessment,
            "key_factors": key_factors,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }

        # Check minimum signal strength (but still create signal)
        min_signal_strength = agents_config.EXECUTION_AGENT.params.get(
            "min_signal_strength",
            0.60
        )

        # Flag if below threshold
        is_below_threshold = confidence < min_signal_strength

        if is_below_threshold:
            logger.info(
                f"LLM signal for {symbol} below threshold: "
                f"{confidence:.2f} < {min_signal_strength} (signal still generated with warning)"
            )

        # Create individual trading signals from agents
        agent_signals = []
        for agent_name, result in agent_results.items():
            if not result.is_error and result.direction is not None:
                signal = TradingSignal(
                    symbol=symbol,
                    direction=result.direction,
                    strength=result.confidence or 0.5,
                    agent_name=agent_name,
                    reasoning=result.reasoning,
                    metadata=result.analysis,
                    timestamp=result.timestamp
                )
                agent_signals.append(signal)

        # Price targets are no longer provided by LLM
        # These will be set to None and can be calculated by risk management system if needed
        entry_price = None
        stop_loss_price = None
        take_profit_price = None

        # Calculate position size based on LLM confidence
        base_position_size = 0.10  # 10% default
        position_size = min(
            base_position_size * confidence,
            0.10  # Max 10% per position
        )

        # Create aggregated signal with LLM analysis
        aggregated_signal = AggregatedSignal(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            agent_signals=agent_signals,
            entry_price=None,  # No price targets from LLM
            target_price=None,  # No price targets from LLM
            stop_loss_price=None,  # No price targets from LLM
            position_size=position_size,
            timestamp=datetime.utcnow(),
            metadata={
                "analysis_method": "llm",
                "llm_reasoning": reasoning,
                "risk_assessment": risk_assessment,
                "key_factors": key_factors,
                "agent_count": len(agent_signals),
                "below_threshold": is_below_threshold,  # Flag for low confidence
                "min_threshold": min_signal_strength
            }
        )

        logger.info(
            f"Generated LLM-based signal for {symbol}: "
            f"direction={direction}, confidence={confidence:.2f}, "
            f"agents={len(agent_signals)}, below_threshold={is_below_threshold}"
        )

        return aggregated_signal, llm_analysis_data

    async def _generate_signal_rule_based(
        self,
        symbol: str,
        valid_results: Dict[str, AgentAnalysisResult]
    ) -> Optional[AggregatedSignal]:
        """
        Generate trading signal using traditional rule-based aggregation.

        Args:
            symbol: Stock symbol
            valid_results: Valid agent results

        Returns:
            Aggregated signal using weighted voting
        """

        # Get agent weights
        weights = agents_config.get_agent_weights()

        # Calculate weighted direction scores
        direction_scores = {
            SignalDirection.LONG: 0.0,
            SignalDirection.SHORT: 0.0,
            SignalDirection.HOLD: 0.0,
            SignalDirection.CLOSE: 0.0
        }

        for agent_name, result in valid_results.items():
            # Get agent key from full name (e.g., "PolicyAnalystAgent" -> "policy")
            agent_key = self._get_agent_key(agent_name)

            if agent_key in weights and result.direction:
                weight = weights[agent_key]
                confidence = result.confidence or 0.5  # Default confidence

                # Add weighted score
                direction_scores[result.direction] += weight * confidence

        # Determine aggregated direction (highest score)
        aggregated_direction = max(direction_scores, key=direction_scores.get)
        aggregated_confidence = direction_scores[aggregated_direction]

        # Check minimum signal strength (but still create signal)
        min_signal_strength = agents_config.EXECUTION_AGENT.params.get(
            "min_signal_strength",
            0.60
        )

        # Flag if below threshold
        is_below_threshold = aggregated_confidence < min_signal_strength

        if is_below_threshold:
            logger.info(
                f"Signal for {symbol} below threshold: "
                f"{aggregated_confidence:.2f} < {min_signal_strength} (signal still generated with warning)"
            )

        # Check minimum agent agreement (dynamic based on actual agent count)
        min_agreement_config = agents_config.EXECUTION_AGENT.params.get(
            "min_agent_agreement",
            3
        )

        # Adjust min_agreement based on actual number of valid agents
        num_valid_agents = len(valid_results)
        if num_valid_agents >= 6:
            min_agreement = min_agreement_config  # 3 agents for 6+ agents
        elif num_valid_agents >= 4:
            min_agreement = 2  # 2 agents for 4-5 agents (50%)
        else:
            min_agreement = max(2, num_valid_agents // 2 + 1)  # Majority for fewer agents

        agreeing_agents = sum(
            1 for r in valid_results.values()
            if r.direction == aggregated_direction
        )

        # Flag if insufficient agreement
        is_below_agreement = agreeing_agents < min_agreement

        if is_below_agreement:
            logger.info(
                f"Insufficient agent agreement for {symbol}: "
                f"{agreeing_agents} < {min_agreement} "
                f"(adjusted from {min_agreement_config} based on {num_valid_agents} valid agents) "
                f"(signal still generated with warning)"
            )

        # Create individual trading signals
        agent_signals = []
        for agent_name, result in valid_results.items():
            signal = TradingSignal(
                symbol=symbol,
                direction=result.direction,
                strength=result.confidence or 0.5,
                agent_name=agent_name,
                reasoning=result.reasoning,
                metadata=result.analysis,
                timestamp=result.timestamp
            )
            agent_signals.append(signal)

        # Calculate aggregated prices (average from agents)
        entry_prices = [
            s.entry_price for s in agent_signals
            if s.entry_price is not None
        ]
        target_prices = [
            s.target_price for s in agent_signals
            if s.target_price is not None
        ]
        stop_loss_prices = [
            s.stop_loss_price for s in agent_signals
            if s.stop_loss_price is not None
        ]

        # Calculate position size based on confidence
        base_position_size = 0.10  # 10% default
        position_size = min(
            base_position_size * aggregated_confidence,
            0.10  # Max 10% per position
        )

        # Create aggregated signal
        aggregated_signal = AggregatedSignal(
            symbol=symbol,
            direction=aggregated_direction,
            confidence=aggregated_confidence,
            agent_signals=agent_signals,
            entry_price=Decimal(sum(entry_prices) / len(entry_prices)) if entry_prices else None,
            target_price=Decimal(sum(target_prices) / len(target_prices)) if target_prices else None,
            stop_loss_price=Decimal(sum(stop_loss_prices) / len(stop_loss_prices)) if stop_loss_prices else None,
            position_size=position_size,
            timestamp=datetime.utcnow(),
            metadata={
                "analysis_method": "rule_based",
                "agreeing_agents": agreeing_agents,
                "total_agents": len(valid_results),
                "below_threshold": is_below_threshold,  # Flag for low confidence
                "below_agreement": is_below_agreement,  # Flag for low agreement
                "min_threshold": min_signal_strength,
                "min_agreement": min_agreement
            }
        )

        logger.info(
            f"Generated rule-based signal for {symbol}: "
            f"direction={aggregated_direction}, confidence={aggregated_confidence:.2f}, "
            f"agreeing_agents={agreeing_agents}/{len(valid_results)}, "
            f"below_threshold={is_below_threshold}, below_agreement={is_below_agreement}"
        )

        return aggregated_signal

    async def batch_analyze_symbols(
        self,
        symbols: List[str],
        save_to_db: bool = True,
        db_session=None
    ) -> Dict[str, Dict[str, AgentAnalysisResult]]:
        """
        Analyze multiple symbols in parallel.

        Args:
            symbols: List of stock symbols
            save_to_db: Whether to save to database
            db_session: Database session

        Returns:
            Dictionary of symbol to agent results
        """
        logger.info(f"Starting batch analysis for {len(symbols)} symbols")

        tasks = {
            symbol: self.analyze_symbol(symbol, save_to_db, db_session)
            for symbol in symbols
        }

        results = {}
        for symbol, task in tasks.items():
            try:
                results[symbol] = await task
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                results[symbol] = {}

        logger.info(f"Completed batch analysis for {len(symbols)} symbols")

        return results

    async def batch_generate_signals(
        self,
        symbols: List[str],
        save_to_db: bool = True,
        db_session=None
    ) -> Dict[str, Optional[AggregatedSignal]]:
        """
        Generate signals for multiple symbols.

        Args:
            symbols: List of stock symbols
            save_to_db: Whether to save to database
            db_session: Database session

        Returns:
            Dictionary of symbol to aggregated signal
        """
        # First, batch analyze all symbols
        all_results = await self.batch_analyze_symbols(
            symbols,
            save_to_db,
            db_session
        )

        # Then generate signals
        signals = {}
        for symbol, agent_results in all_results.items():
            try:
                signal = await self.generate_trading_signal(
                    symbol,
                    agent_results,
                    save_to_db=False,  # Already saved in analyze
                    db_session=db_session
                )
                signals[symbol] = signal
            except Exception as e:
                logger.error(f"Error generating signal for {symbol}: {e}")
                signals[symbol] = None

        # Log summary
        valid_signals = sum(1 for s in signals.values() if s is not None)
        logger.info(
            f"Generated {valid_signals} valid signals from {len(symbols)} symbols"
        )

        return signals

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all agents.

        Returns:
            Health check results
        """
        if not self.agent_pool:
            return {
                "status": "no_agents",
                "num_agents": 0,
                "agents": {}
            }

        agent_health = await self.agent_pool.health_check_all()

        num_healthy = sum(
            1 for h in agent_health.values()
            if h.get("status") == "healthy"
        )

        return {
            "status": "healthy" if num_healthy > 0 else "unhealthy",
            "num_agents": len(self.agents),
            "num_healthy": num_healthy,
            "num_enabled": sum(1 for a in self.agents.values() if a.is_enabled),
            "agents": agent_health
        }

    def _get_agent_key(self, agent_name: str) -> str:
        """
        Get agent key from full agent name.

        Args:
            agent_name: Full agent name (e.g., "PolicyAnalystAgent")

        Returns:
            Agent key (e.g., "policy")
        """
        # Mapping from full names to keys
        name_to_key = {
            "PolicyAnalystAgent": "policy",
            "MarketMonitorAgent": "market",
            "TechnicalAnalysisAgent": "technical",
            "FundamentalAgent": "fundamental",
            "SentimentAgent": "sentiment",
            "RiskManagerAgent": "risk",
            "ExecutionAgent": "execution"
        }

        return name_to_key.get(agent_name, agent_name.lower())

    def get_agent_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all registered agents.

        Returns:
            Dictionary of agent name to status info
        """
        return {
            name: {
                "name": agent.name,
                "enabled": agent.is_enabled,
                "timeout": agent.config.timeout,
                "weight": agent.config.weight,
                "cache_ttl": agent.config.cache_ttl
            }
            for name, agent in self.agents.items()
        }
