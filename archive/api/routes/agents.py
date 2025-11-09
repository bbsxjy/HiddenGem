"""
MCP Agents API routes.
"""

import asyncio
import json
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from api.models.request import (
    AgentStatusResponse, AgentAnalysisRequest, AgentAnalysisResponse
)
from config.agents_config import agents_config
from core.mcp_agents.technical_agent import TechnicalAnalysisAgent
from core.mcp_agents.fundamental_agent import FundamentalAgent
from core.mcp_agents.risk_agent import RiskManagerAgent
from core.mcp_agents.market_agent import MarketMonitorAgent
from core.mcp_agents.policy_agent import PolicyAnalystAgent
from core.mcp_agents.sentiment_agent import SentimentAgent
from core.mcp_agents.orchestrator import MCPOrchestrator


router = APIRouter()

# Initialize agents (simplified - would be managed centrally)
orchestrator = MCPOrchestrator()
agents = {
    'technical': TechnicalAnalysisAgent(),
    'fundamental': FundamentalAgent(),
    'risk': RiskManagerAgent(),
    'market': MarketMonitorAgent(),
    'policy': PolicyAnalystAgent(),
    'sentiment': SentimentAgent()
}

# Register agents
for agent in agents.values():
    orchestrator.register_agent(agent)


# ==================== 幂等性保护 ====================
# 跟踪正在进行的分析请求
_ongoing_analyses: Dict[str, Dict[str, Any]] = {}
_analysis_lock = asyncio.Lock()


async def get_or_create_analysis(symbol: str):
    """
    获取正在进行的分析或创建新的分析任务。

    实现幂等性：同一个symbol的多个请求会共享同一个分析任务。

    Args:
        symbol: 股票代码

    Returns:
        分析结果（如果已完成）或Future（如果正在进行）
    """
    async with _analysis_lock:
        # 检查是否已有正在进行的分析
        if symbol in _ongoing_analyses:
            analysis_info = _ongoing_analyses[symbol]

            # 检查是否已过期（超过10分钟视为失败，可以重新分析）
            started_at = analysis_info['started_at']
            if datetime.utcnow() - started_at > timedelta(minutes=10):
                logger.warning(f"Analysis for {symbol} expired, will restart")
                del _ongoing_analyses[symbol]
            else:
                logger.info(f"Analysis for {symbol} already in progress, returning existing task")
                return analysis_info['task']

        # 创建新的分析任务
        logger.info(f"Creating new analysis task for {symbol}")
        task = asyncio.create_task(_perform_analysis(symbol))

        _ongoing_analyses[symbol] = {
            'task': task,
            'started_at': datetime.utcnow()
        }

        return task


async def _perform_analysis(symbol: str):
    """
    执行实际的分析（内部函数）。

    Args:
        symbol: 股票代码

    Returns:
        分析结果
    """
    try:
        logger.info(f"Starting multi-agent analysis for {symbol}")

        # Run all agents
        agent_results = await orchestrator.analyze_symbol(symbol)

        # Generate aggregated signal (now returns tuple)
        aggregated_signal, llm_analysis = await orchestrator.generate_trading_signal(
            symbol,
            agent_results
        )

        # Build response
        result = _build_analysis_response(
            symbol,
            agent_results,
            aggregated_signal,
            llm_analysis
        )

        return result

    except Exception as e:
        logger.exception(f"Error in multi-agent analysis for {symbol}: {e}")
        raise
    finally:
        # 清理完成的任务
        async with _analysis_lock:
            if symbol in _ongoing_analyses:
                del _ongoing_analyses[symbol]
                logger.debug(f"Cleaned up analysis task for {symbol}")


def _build_analysis_response(symbol: str, agent_results, aggregated_signal, llm_analysis):
    """构建分析响应（提取为独立函数）"""
    # Build aggregated signal response with metadata
    aggregated_signal_response = None
    signal_warnings = []  # 收集警告信息
    signal_rejection_reason = None  # 初始化拒绝原因

    if aggregated_signal:
        metadata = aggregated_signal.metadata or {}

        # Check for warning flags
        if metadata.get('below_threshold'):
            signal_warnings.append(
                f"信号强度低于阈值 ({aggregated_signal.confidence:.2f} < {metadata.get('min_threshold', 0.6)})"
            )

        if metadata.get('below_agreement'):
            signal_warnings.append(
                f"Agent一致性不足 ({metadata.get('agreeing_agents', 0)}/{metadata.get('total_agents', 0)} < {metadata.get('min_agreement', 3)})"
            )

        aggregated_signal_response = {
            'direction': aggregated_signal.direction.value,
            'confidence': aggregated_signal.confidence,
            'position_size': aggregated_signal.position_size,
            'num_agreeing_agents': aggregated_signal.num_agreeing_agents,
            'metadata': metadata,
            'warnings': signal_warnings  # 添加警告列表
        }
    else:
        # Fallback: if signal is None (shouldn't happen now, but keep for safety)
        # Provide diagnostic information when no signal is generated
        valid_results = {
            name: result for name, result in agent_results.items()
            if not result.is_error and result.direction is not None
        }

        if not valid_results:
            signal_rejection_reason = "所有Agent分析失败或无有效方向"
        else:
            # Count direction consensus
            from collections import Counter
            directions = [r.direction.value for r in valid_results.values()]
            direction_counts = Counter(directions)
            max_agreement = max(direction_counts.values()) if direction_counts else 0

            # Calculate weighted confidence
            from config.agents_config import agents_config
            weights = agents_config.get_agent_weights()
            direction_scores = {}
            for agent_name, result in valid_results.items():
                agent_key = agent_name.replace('Agent', '').lower()
                if 'technical' in agent_key.lower():
                    agent_key = 'technical'
                elif 'fundamental' in agent_key.lower():
                    agent_key = 'fundamental'
                elif 'risk' in agent_key.lower():
                    agent_key = 'risk'
                elif 'market' in agent_key.lower():
                    agent_key = 'market'

                if agent_key in weights:
                    direction = result.direction.value
                    if direction not in direction_scores:
                        direction_scores[direction] = 0
                    direction_scores[direction] += weights[agent_key] * (result.confidence or 0.5)

            max_confidence = max(direction_scores.values()) if direction_scores else 0

            min_strength = 0.60
            min_agreement = 3

            reasons = []
            if max_agreement < min_agreement:
                reasons.append(f"Agent一致性不足({max_agreement}/{min_agreement})")
            if max_confidence < min_strength:
                reasons.append(f"信号强度不足({max_confidence:.2f}/{min_strength})")

            signal_rejection_reason = "；".join(reasons) if reasons else "未知原因"

    return {
        'symbol': symbol,
        'agent_results': {
            name: {
                'direction': result.direction.value if result.direction else None,
                'confidence': result.confidence,
                'score': result.score,
                'reasoning': result.reasoning,
                'is_error': result.is_error
            }
            for name, result in agent_results.items()
        },
        'aggregated_signal': aggregated_signal_response,
        'signal_rejection_reason': signal_rejection_reason if not aggregated_signal else None,  # 只在没有signal时使用
        'llm_analysis': llm_analysis  # Add LLM analysis data
    }
# ==================== End 幂等性保护 ====================


@router.get("/status", response_model=List[AgentStatusResponse])
async def get_agents_status():
    """
    Get status of all agents.

    Returns:
        List of agent statuses
    """
    try:
        health = await orchestrator.health_check()

        agent_statuses = []
        for agent_name, status_info in health.get('agents', {}).items():
            agent_statuses.append(AgentStatusResponse(
                name=status_info['agent'],
                enabled=status_info['enabled'],
                weight=status_info['config']['weight'],
                timeout=status_info['config']['timeout'],
                cache_ttl=status_info['config']['cache_ttl']
            ))

        return agent_statuses

    except Exception as e:
        logger.error(f"Error fetching agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{agent_name}", response_model=AgentAnalysisResponse)
async def analyze_with_agent(
    agent_name: str,
    request: AgentAnalysisRequest
):
    """
    Run analysis with a specific agent.

    Args:
        agent_name: Agent name (technical, fundamental, risk, market)
        request: Analysis request

    Returns:
        Agent analysis result
    """
    if agent_name not in agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available: {list(agents.keys())}"
        )

    agent = agents[agent_name]

    try:
        logger.info(f"Running {agent_name} analysis for {request.symbol}")

        result = await agent.analyze(symbol=request.symbol)

        return AgentAnalysisResponse(
            agent_name=result.agent_name,
            symbol=result.symbol,
            score=result.score,
            direction=result.direction.value if result.direction else None,
            confidence=result.confidence,
            reasoning=result.reasoning,
            analysis=result.analysis,
            execution_time_ms=result.execution_time_ms,
            timestamp=result.timestamp,
            is_error=result.is_error
        )

    except Exception as e:
        logger.exception(f"Error in {agent_name} analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-all/{symbol}")
async def analyze_with_all_agents(symbol: str):
    """
    Run analysis with all agents (orchestrated).

    实现幂等性保护：同一个symbol的多个并发请求会共享同一个分析任务。

    Args:
        symbol: Stock symbol

    Returns:
        Analysis from all agents and aggregated signal
    """
    try:
        logger.info(f"Received analyze-all request for {symbol}")

        # 使用幂等性保护：获取或创建分析任务
        task = await get_or_create_analysis(symbol)

        # Await the task to get the actual result
        result = await task

        return result

    except Exception as e:
        logger.exception(f"Error in multi-agent analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_agent_performance():
    """
    Get agent performance metrics.

    Returns:
        Agent performance stats
    """
    try:
        # This would track agent accuracy over time
        # Simplified implementation
        return {
            'message': 'Agent performance tracking not yet implemented',
            'agents': list(agents.keys())
        }

    except Exception as e:
        logger.error(f"Error fetching agent performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze-all-stream/{symbol}")
async def analyze_with_all_agents_stream(symbol: str):
    """
    Run analysis with all agents using SSE (Server-Sent Events) for real-time streaming.

    This endpoint provides a better UX by streaming agent results as they complete,
    rather than waiting for all analyses to finish.

    Args:
        symbol: Stock symbol

    Returns:
        SSE stream with agent results and LLM analysis
    """

    async def event_generator():
        """Generate SSE events for agent results and LLM analysis"""
        try:
            logger.info(f"Starting streaming analysis for {symbol}")

            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'symbol': symbol, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Create tasks for all agents
            agent_tasks = {}
            for agent_name, agent in agents.items():
                task = asyncio.create_task(agent.analyze(symbol=symbol))
                agent_tasks[agent_name] = task

            # Wait for agent tasks and stream results as they complete
            agent_results = {}
            completed_count = 0
            total_agents = len(agent_tasks)

            while agent_tasks:
                # Wait for next task to complete
                done, pending = await asyncio.wait(
                    agent_tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in done:
                    # Find which agent completed
                    agent_name = None
                    for name, t in agent_tasks.items():
                        if t == task:
                            agent_name = name
                            break

                    if agent_name:
                        try:
                            result = await task
                            agent_results[agent_name] = result
                            completed_count += 1

                            # Stream agent result immediately
                            agent_data = {
                                'type': 'agent_result',
                                'agent_name': agent_name,
                                'progress': f"{completed_count}/{total_agents}",
                                'result': {
                                    'direction': result.direction.value if result.direction else None,
                                    'confidence': result.confidence,
                                    'score': result.score,
                                    'reasoning': result.reasoning,
                                    'is_error': result.is_error
                                },
                                'timestamp': datetime.utcnow().isoformat()
                            }
                            yield f"data: {json.dumps(agent_data)}\n\n"

                        except Exception as e:
                            logger.error(f"Error in {agent_name} analysis: {e}")
                            error_data = {
                                'type': 'agent_error',
                                'agent_name': agent_name,
                                'error': str(e),
                                'timestamp': datetime.utcnow().isoformat()
                            }
                            yield f"data: {json.dumps(error_data)}\n\n"

                        # Remove completed task
                        del agent_tasks[agent_name]

            # All agents completed, now generate trading signal with LLM
            logger.info(f"All agents completed for {symbol}, generating signal with LLM")

            yield f"data: {json.dumps({'type': 'llm_start', 'message': 'Generating trading signal with LLM...', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            try:
                # Generate signal (returns tuple now)
                aggregated_signal, llm_analysis = await orchestrator.generate_trading_signal(
                    symbol,
                    agent_results
                )

                # Build final response
                final_response = _build_analysis_response(
                    symbol,
                    agent_results,
                    aggregated_signal,
                    llm_analysis
                )

                # Stream final result
                yield f"data: {json.dumps({'type': 'complete', 'data': final_response, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            except Exception as e:
                logger.error(f"Error in LLM analysis: {e}")
                error_data = {
                    'type': 'llm_error',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        except Exception as e:
            logger.exception(f"Error in streaming analysis: {e}")
            error_data = {
                'type': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
