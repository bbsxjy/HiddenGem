"""
Agent Analysis API Router

提供TradingAgents多Agent分析的API端点
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json
import asyncio
import os

# 导入TradingAgents
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# 导入任务管理器
from api.services.task_manager import task_manager, Task, TaskStatus

# 导入异常处理工具
from api.utils.exception_handlers import handle_memory_exception
from tradingagents.agents.utils.memory_exceptions import (
    EmbeddingError,
    EmbeddingServiceUnavailable,
    EmbeddingTextTooLong,
    EmbeddingInvalidInput,
    MemoryDisabled
)

PRIMARY_AGENT_FIELDS = [
    ("market_report", {"agent": "technical", "label": "技术面"}),
    ("fundamentals_report", {"agent": "fundamental", "label": "基本面"}),
    ("sentiment_report", {"agent": "sentiment", "label": "情绪面"}),
    ("news_report", {"agent": "policy", "label": "政策面"}),
]
PRIMARY_AGENT_TOTAL = len(PRIMARY_AGENT_FIELDS)
AGENT_PROGRESS_START = 25
AGENT_PROGRESS_END = 75


def _detect_agent_progress_update(update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Inspect a graph update and extract agent progress info if available."""
    if not isinstance(update, dict):
        return None

    for field, meta in PRIMARY_AGENT_FIELDS:
        report = update.get(field)
        if isinstance(report, str) and report.strip():
            return {
                "field": field,
                "agent_key": meta["agent"],
                "agent_label": meta["label"],
                "report": report.strip()
            }
    return None


def _agent_progress_percentage(completed_count: int) -> int:
    """Convert completed primary agents to a coarse progress percentage."""
    if PRIMARY_AGENT_TOTAL == 0:
        return AGENT_PROGRESS_START

    clamped = min(max(completed_count, 0), PRIMARY_AGENT_TOTAL)
    ratio = clamped / PRIMARY_AGENT_TOTAL
    span = AGENT_PROGRESS_END - AGENT_PROGRESS_START
    return AGENT_PROGRESS_START + int(span * ratio)


logger = logging.getLogger(__name__)

router = APIRouter()

# 全局TradingGraph实例（应用启动时初始化）
trading_graph: Optional[TradingAgentsGraph] = None


def _build_config_from_env() -> Dict[str, Any]:
    """
    从环境变量构建配置字典，覆盖 DEFAULT_CONFIG 中的硬编码值

    Returns:
        配置字典
    """
    config = DEFAULT_CONFIG.copy()

    # 从环境变量读取 LLM 配置（这些会覆盖 DEFAULT_CONFIG 中的硬编码值）
    llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
    config["llm_provider"] = llm_provider

    # 根据不同的 provider 设置 backend_url
    if llm_provider == "siliconflow":
        config["backend_url"] = os.getenv("BACKEND_URL", "https://api.siliconflow.cn/v1")
        config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", "Qwen/Qwen3-Next-80B-A3B-Thinking")
        config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", "Qwen/Qwen3-Next-80B-A3B-Instruct")
    elif llm_provider == "openai":
        config["backend_url"] = os.getenv("BACKEND_URL", "https://api.openai.com/v1")
        config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", "gpt-4o")
        config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", "gpt-4o-mini")
    else:
        # 其他 provider（dashscope, deepseek 等）
        config["backend_url"] = os.getenv("BACKEND_URL", config["backend_url"])
        config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", config["deep_think_llm"])
        config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", config["quick_think_llm"])

    logger.info(f"[CONFIG] LLM Provider: {config['llm_provider']}")
    logger.info(f"[CONFIG] Backend URL: {config['backend_url']}")
    logger.info(f"[CONFIG] Deep Think LLM: {config['deep_think_llm']}")
    logger.info(f"[CONFIG] Quick Think LLM: {config['quick_think_llm']}")

    return config


# Pydantic Models
class AnalyzeRequest(BaseModel):
    symbol: str
    trade_date: Optional[str] = None  # 默认为今天


class AnalyzeResponse(BaseModel):
    success: bool
    symbol: str
    agent_results: Dict
    aggregated_signal: Dict
    llm_analysis: Dict
    timestamp: str


class PositionAnalysisRequest(BaseModel):
    """持仓分析请求"""
    holdings: Dict[str, Any]  # 持仓信息
    analysis_date: Optional[str] = None  # 分析日期


class PositionAnalysisResponse(BaseModel):
    """持仓分析响应"""
    success: bool
    symbol: str
    decision: str  # sell, hold, add
    reasoning: str
    suggested_action: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    agent_results: Dict
    timestamp: str


@router.on_event("startup")
async def startup_event():
    """路由启动时初始化TradingGraph"""
    global trading_graph
    try:
        logger.info("[STARTUP] Initializing TradingAgentsGraph...")

        # 从环境变量构建配置（覆盖硬编码的默认值）
        config = _build_config_from_env()

        # 使用配置初始化 TradingAgentsGraph
        trading_graph = TradingAgentsGraph(config=config)

        logger.info("[STARTUP] TradingAgentsGraph initialized successfully")
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize TradingAgentsGraph: {e}")


@router.get("/status")
async def get_agents_status():
    """获取所有Agent的状态"""
    return {
        "success": True,
        "data": [
            {"agent_name": "technical", "enabled": True, "weight": 1.0, "status": "active"},
            {"agent_name": "fundamental", "enabled": True, "weight": 1.0, "status": "active"},
            {"agent_name": "sentiment", "enabled": True, "weight": 1.0, "status": "active"},
            {"agent_name": "policy", "enabled": True, "weight": 1.0, "status": "active"},
            {"agent_name": "risk", "enabled": True, "weight": 0.5, "status": "active"},
        ],
        "timestamp": datetime.now().isoformat()
    }


@router.post("/analyze-all/{symbol}")
async def analyze_all_agents(symbol: str, trade_date: Optional[str] = None):
    """
    分析所有Agent对某只股票的看法（同步版本，会阻塞）

    ⚠️ 注意：此接口会阻塞直到分析完成，建议使用 /analyze-all-async/{symbol} 异步版本

    Args:
        symbol: 股票代码 (e.g., 600519.SH, 000001.SZ)
        trade_date: 交易日期，默认为今天

    Returns:
        AnalyzeResponse: 包含所有Agent的分析结果
    """
    global trading_graph

    if trading_graph is None:
        raise HTTPException(status_code=503, detail="TradingAgentsGraph not initialized")

    if trade_date is None:
        trade_date = datetime.now().strftime('%Y-%m-%d')

    try:
        logger.info(f"[ANALYZE] Starting analysis for {symbol} on {trade_date}")

        # 调用TradingAgents进行分析
        final_state, processed_signal = trading_graph.propagate(symbol, trade_date)

        # 格式化为前端期望的格式
        response = _format_response(final_state, processed_signal, symbol)

        logger.info(f"[ANALYZE] Analysis complete for {symbol}")
        return response

    except (MemoryDisabled, EmbeddingServiceUnavailable,
            EmbeddingTextTooLong, EmbeddingInvalidInput, EmbeddingError) as e:
        # 处理memory相关异常，返回用户友好的错误信息
        http_exception = handle_memory_exception(e, f"分析{symbol}")
        if http_exception:
            raise http_exception
        else:
            # 理论上不会到这里
            logger.error(f"[ERROR] Unhandled memory exception for {symbol}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"[ERROR] Analysis failed for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-all-async/{symbol}")
async def analyze_all_agents_async(symbol: str, trade_date: Optional[str] = None):
    """
    异步分析所有Agent对某只股票的看法（推荐）

    此接口立即返回task_id，不会阻塞。
    使用 GET /tasks/{task_id} 查询分析进度和结果

    Args:
        symbol: 股票代码 (e.g., 600519.SH, 000001.SZ)
        trade_date: 交易日期，默认为今天

    Returns:
        {
            "success": true,
            "task_id": "uuid",
            "symbol": "600519.SH",
            "message": "Analysis task created",
            "status_url": "/api/v1/agents/tasks/{task_id}"
        }
    """
    global trading_graph

    if trading_graph is None:
        raise HTTPException(status_code=503, detail="TradingAgentsGraph not initialized")

    if trade_date is None:
        trade_date = datetime.now().strftime('%Y-%m-%d')

    try:
        # 创建任务
        task_id = task_manager.create_task(
            task_type="analyze_all",
            symbol=symbol,
            metadata={"trade_date": trade_date}
        )

        # 在后台运行分析
        task_manager.run_task_in_background(
            task_id=task_id,
            func=_run_analysis_task,
            symbol=symbol,
            trade_date=trade_date
        )

        logger.info(f"[ASYNC] Created analysis task {task_id} for {symbol}")

        return {
            "success": True,
            "task_id": task_id,
            "symbol": symbol,
            "message": "Analysis task created successfully",
            "status_url": f"/api/v1/agents/tasks/{task_id}",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"[ERROR] Failed to create analysis task for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _run_analysis_task(task: Task, symbol: str, trade_date: str):
    """
    执行分析任务（后台函数）

    Args:
        task: 任务对象
        symbol: 股票代码
        trade_date: 交易日期

    Returns:
        分析结果字典
    """
    global trading_graph

    try:
        # 更新进度：0% - 开始
        task_manager.update_progress(task.task_id, 0, f"开始分析 {symbol}")

        # 更新进度：10% - 数据准备
        task_manager.update_progress(task.task_id, 10, "准备数据...")

        # 运行分析（在executor中运行同步函数）
        loop = asyncio.get_event_loop()

        # 启动进度模拟任务
        progress_cancel = asyncio.Event()
        progress_task = asyncio.create_task(_simulate_progress(task.task_id, progress_cancel))
        completed_agents = set()

        def sync_propagate():
            # 更新进度：20% - 分析开始
            task_manager.update_progress(task.task_id, 20, "初始化分析系统...")

            def progress_callback(node_name: str, update: Dict[str, Any], state: Dict[str, Any]):
                info = _detect_agent_progress_update(update)
                if not info:
                    return

                agent_key = info["agent_key"]
                if agent_key in completed_agents:
                    return

                completed_agents.add(agent_key)
                if not progress_cancel.is_set():
                    try:
                        loop.call_soon_threadsafe(progress_cancel.set)
                    except RuntimeError:
                        # 事件循环可能已经关闭，忽略即可
                        pass
                progress_value = _agent_progress_percentage(len(completed_agents))
                message = f"{info['agent_label']}分析完成"
                task_manager.update_progress(task.task_id, progress_value, message)

            # 执行实际分析（这个过程可能需要几分钟）
            final_state, processed_signal = trading_graph.propagate(
                symbol,
                trade_date,
                progress_callback=progress_callback
            )

            return final_state, processed_signal

        try:
            final_state, processed_signal = await loop.run_in_executor(None, sync_propagate)
        finally:
            # 停止进度模拟
            progress_cancel.set()
            try:
                await asyncio.wait_for(progress_task, timeout=1.0)
            except asyncio.TimeoutError:
                progress_task.cancel()

        # 更新进度：80% - 格式化结果
        task_manager.update_progress(task.task_id, 80, "格式化结果...")

        # 更新进度：90% - 生成报告
        task_manager.update_progress(task.task_id, 90, "生成分析报告...")

        # 格式化响应
        result = _format_response(final_state, processed_signal, symbol)

        # 更新进度：100% - 完成
        task_manager.update_progress(task.task_id, 100, "分析完成")

        logger.info(f"[TASK] Analysis completed for {symbol} (task: {task.task_id})")
        return result

    except Exception as e:
        logger.error(f"[TASK] Analysis failed for {symbol} (task: {task.task_id}): {e}", exc_info=True)

        # 检查是否是memory相关异常
        if isinstance(e, (MemoryDisabled, EmbeddingServiceUnavailable,
                         EmbeddingTextTooLong, EmbeddingInvalidInput, EmbeddingError)):
            # 处理memory异常，但不抛出HTTPException（因为是后台任务）
            # 而是将错误信息记录到任务状态中
            http_exception = handle_memory_exception(e, f"异步分析{symbol}")
            if http_exception:
                # 提取友好的错误信息
                error_detail = http_exception.detail
                if isinstance(error_detail, dict):
                    error_message = f"{error_detail.get('message', str(e))} - {error_detail.get('description', '')}"
                else:
                    error_message = str(error_detail)

                # 更新任务为失败状态，但包含友好的错误信息
                task_manager.update_task(task.task_id, status=TaskStatus.FAILED, error=error_message)
                logger.warning(f"⚠️ [TASK] Memory exception in {symbol}: {error_message}")
                return

        # 其他异常正常抛出
        raise


async def _simulate_progress(task_id: str, cancel_event: asyncio.Event):
    """
    模拟分析进度（在实际分析执行期间）

    从20%逐渐增加到75%，每个阶段模拟不同的分析步骤

    Args:
        task_id: 任务ID
        cancel_event: 取消事件
    """
    # 定义进度步骤：(进度%, 消息, 等待时间秒)
    progress_steps = [
        (25, "市场数据分析中...", 8),
        (35, "基本面分析中...", 10),
        (45, "情绪分析中...", 8),
        (55, "政策分析中...", 8),
        (62, "多方观点辩论中...", 10),
        (68, "空方观点辩论中...", 10),
        (73, "风险评估中...", 8),
        (75, "综合分析中...", 5),
    ]

    try:
        for progress, message, wait_time in progress_steps:
            # 检查是否被取消
            if cancel_event.is_set():
                logger.debug(f"[Progress Simulator] Cancelled for task {task_id}")
                return

            # 更新进度
            task_manager.update_progress(task_id, progress, message)
            logger.debug(f"[Progress Simulator] Task {task_id}: {progress}% - {message}")

            # 等待指定时间或直到取消
            try:
                await asyncio.wait_for(cancel_event.wait(), timeout=wait_time)
                # 如果wait成功返回，说明被取消了
                logger.debug(f"[Progress Simulator] Cancelled for task {task_id}")
                return
            except asyncio.TimeoutError:
                # 超时是正常的，继续下一个步骤
                continue

    except Exception as e:
        logger.error(f"[Progress Simulator] Error for task {task_id}: {e}", exc_info=True)


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    获取任务状态和结果

    Args:
        task_id: 任务ID

    Returns:
        任务状态和结果
    """
    task_status = task_manager.get_task_status(task_id)

    if not task_status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return {
        "success": True,
        "data": task_status,
        "timestamp": datetime.now().isoformat()
    }


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    取消任务

    Args:
        task_id: 任务ID

    Returns:
        取消结果
    """
    success = task_manager.cancel_task(task_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} cannot be cancelled (not found or already completed)"
        )

    return {
        "success": True,
        "message": f"Task {task_id} cancelled successfully",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(50, description="Number of tasks to return")
):
    """
    列出任务

    Args:
        status: 过滤状态 (pending, running, completed, failed, cancelled)
        symbol: 过滤股票代码
        limit: 返回数量限制

    Returns:
        任务列表
    """
    status_enum = None
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Must be one of: pending, running, completed, failed, cancelled"
            )

    tasks = task_manager.list_tasks(
        status=status_enum,
        symbol=symbol,
        limit=limit
    )

    return {
        "success": True,
        "data": tasks,
        "total": len(tasks),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/tasks/stats")
async def get_tasks_stats():
    """
    获取任务统计信息

    Returns:
        任务统计
    """
    stats = task_manager.get_stats()

    return {
        "success": True,
        "data": stats,
        "timestamp": datetime.now().isoformat()
    }


def _format_response(final_state: dict, processed_signal: Any, symbol: str) -> dict:
    """
    将TradingAgents的输出格式化为前端期望的格式

    Args:
        final_state: TradingGraph的最终状态
        processed_signal: 处理后的信号
        symbol: 股票代码

    Returns:
        格式化后的响应字典（符合前端AnalyzeAllResponse接口）
    """
    # 提取各个分析师的报告
    agent_results = {
        'technical': _format_agent_result(
            final_state.get('market_report', ''),
            'technical'
        ),
        'fundamental': _format_agent_result(
            final_state.get('fundamentals_report', ''),
            'fundamental'
        ),
        'sentiment': _format_agent_result(
            final_state.get('sentiment_report', ''),
            'sentiment'
        ),
        'policy': _format_agent_result(
            final_state.get('news_report', ''),
            'policy'
        ),
    }

    # 提取辩论结果作为LLM分析
    debate_state = final_state.get('investment_debate_state', {})
    risk_debate_state = final_state.get('risk_debate_state', {})

    # 提取风险分析师反馈（完整内容）
    risk_analysts = {}
    if risk_debate_state:
        # 从risk_debate_state中提取三个风险分析师的反馈
        # 注意：字段名是 current_risky_response, current_safe_response, current_neutral_response
        risky_report = risk_debate_state.get('current_risky_response', '')
        neutral_report = risk_debate_state.get('current_neutral_response', '')
        safe_report = risk_debate_state.get('current_safe_response', '')

        logger.debug(f"[Risk Analysts] risky: {len(risky_report)} chars, neutral: {len(neutral_report)} chars, safe: {len(safe_report)} chars")

        if risky_report:
            risk_analysts['risky'] = {
                'position': '激进',
                'direction': _extract_direction(risky_report),
                'confidence': _extract_confidence(risky_report, default=0.7),
                'reasoning': risky_report,  # 完整内容
                'full_analysis': risky_report  # 保持向后兼容
            }
        if neutral_report:
            risk_analysts['neutral'] = {
                'position': '中立',
                'direction': _extract_direction(neutral_report),
                'confidence': _extract_confidence(neutral_report, default=0.75),
                'reasoning': neutral_report,  # 完整内容
                'full_analysis': neutral_report  # 保持向后兼容
            }
        if safe_report:
            risk_analysts['safe'] = {
                'position': '保守',
                'direction': _extract_direction(safe_report),
                'confidence': _extract_confidence(safe_report, default=0.8),
                'reasoning': safe_report,  # 完整内容
                'full_analysis': safe_report  # 保持向后兼容
            }

    # 构建LLM分析
    # 注意数据来源：
    # 1. reasoning: 投资辩论结果（investment_debate_state.judge_decision）- 来自Research Manager
    # 2. risk_assessment: 风险评估简短摘要（risk_debate_state.judge_decision前300字）- 来自Risk Manager
    # 3. risk_manager_decision: 风险管理者完整决策（risk_debate_state.judge_decision）- 来自Risk Manager
    # 4. signal_processor_summary: 最终交易决策（final_trade_decision）- 来自Risk Manager
    #
    # 注意：在当前TradingAgents架构中，risk_manager_decision 和 signal_processor_summary
    # 是相同的内容，因为 final_trade_decision 就是由 Risk Manager 设置的。
    # 未来如果添加单独的Signal Processor节点，可以在那里设置不同的内容。

    judge_decision_full = debate_state.get('judge_decision', '')  # Research Manager的决策
    risk_judge_decision_full = risk_debate_state.get('judge_decision', '')  # Risk Manager的决策
    final_trade_decision_full = final_state.get('final_trade_decision', '')  # 也是Risk Manager设置的

    # 添加日志以调试
    logger.debug(f"[Data Sources] investment judge_decision: {len(judge_decision_full)} chars")
    logger.debug(f"[Data Sources] risk judge_decision: {len(risk_judge_decision_full)} chars")
    logger.debug(f"[Data Sources] final_trade_decision: {len(final_trade_decision_full)} chars")

    # final_trade_decision应该与risk_judge_decision相同，因为它们来自同一个节点
    if not final_trade_decision_full and risk_judge_decision_full:
        logger.warning("[Data Sources] final_trade_decision is empty, using risk_judge_decision")
        final_trade_decision_full = risk_judge_decision_full
    elif final_trade_decision_full != risk_judge_decision_full:
        logger.warning("[Data Sources] final_trade_decision differs from risk_judge_decision, this is unexpected")

    # 提取风险评估的简短摘要（只取前300字）
    risk_assessment_short = risk_judge_decision_full[:300] + '...' if len(risk_judge_decision_full) > 300 else risk_judge_decision_full or '无风险评估'

    llm_analysis = {
        "recommended_direction": _extract_direction(judge_decision_full or risk_judge_decision_full),
        "confidence": 0.85,
        "reasoning": judge_decision_full[:500] if judge_decision_full else risk_judge_decision_full[:500],  # 投资辩论结果摘要
        "risk_assessment": risk_assessment_short,  # 风险评估简短摘要（300字）
        "key_factors": _extract_key_factors(final_state),
        "risk_score": _calculate_risk_score(risk_debate_state),
        "risk_analysts": risk_analysts if risk_analysts else None,
        "risk_manager_decision": risk_judge_decision_full,  # Risk Manager完整决策
        "price_targets": _extract_price_targets(final_state),
        "analysis_timestamp": datetime.now().isoformat(),
        "signal_processor_summary": final_trade_decision_full  # 最终交易决策（与risk_manager_decision相同）
    }

    # 提取最终决策
    final_decision = final_state.get('final_trade_decision', '')

    # 计算同意的agent数量
    agent_directions = [result['direction'] for result in agent_results.values()]
    recommended_direction = llm_analysis['recommended_direction']
    num_agreeing = sum(1 for d in agent_directions if d == recommended_direction)

    aggregated_signal = {
        "direction": _extract_direction(final_decision),
        "confidence": 0.8,
        "position_size": 0.1,
        "num_agreeing_agents": num_agreeing,
        "warnings": _extract_warnings(final_state),
        "metadata": {
            "analysis_method": "llm",
            "agent_count": len(agent_results),
            "agreeing_agents": num_agreeing,
            "total_agents": len(agent_results)
        }
    }

    return {
        "success": True,
        "symbol": symbol,
        "agent_results": agent_results,
        "aggregated_signal": aggregated_signal,
        "llm_analysis": llm_analysis,
        "signal_rejection_reason": None,
        "timestamp": datetime.now().isoformat()
    }


def _format_agent_result(report: str, agent_name: str) -> dict:
    """
    格式化单个Agent的结果

    Args:
        report: Agent的报告文本
        agent_name: Agent名称

    Returns:
        格式化后的结果字典（符合前端AgentAnalysisResult接口）
    """
    # 简单的方向提取
    direction = _extract_direction(report)

    return {
        "agent_name": agent_name,
        "direction": direction,
        "confidence": 0.8,
        "score": 0.75,
        "reasoning": report[:500] if report else "No analysis available",
        "is_error": False,
        "full_report": report  # 前端期望的顶级字段
    }


def _extract_direction(text: str) -> str:
    """
    从文本中提取交易方向

    Args:
        text: 分析文本

    Returns:
        方向: 'long', 'short', 'hold', 'close'
    """
    if not text:
        return 'hold'

    text_lower = text.lower()

    buy_keywords = ['买入', '看涨', 'buy', 'long', '建议持有', '积极', '推荐买入']
    sell_keywords = ['卖出', '看跌', 'sell', 'short', '减持', '谨慎', '推荐卖出']

    buy_score = sum(1 for kw in buy_keywords if kw in text_lower)
    sell_score = sum(1 for kw in sell_keywords if kw in text_lower)

    if buy_score > sell_score:
        return 'long'
    elif sell_score > buy_score:
        return 'short'
    else:
        return 'hold'


def _extract_confidence(text: str, default: float = 0.75) -> float:
    """
    从文本中提取置信度

    Args:
        text: 分析文本
        default: 默认置信度

    Returns:
        置信度值 (0-1)
    """
    import re

    if not text:
        return default

    # 尝试匹配显式的置信度表述
    confidence_patterns = [
        r'置信度[：:]?\s*(\d+(?:\.\d+)?)[%％]',
        r'confidence[：:]?\s*(\d+(?:\.\d+)?)',
        r'把握[：:]?\s*(\d+)[%％]',
        r'确定性[：:]?\s*(\d+)[%％]',
    ]

    for pattern in confidence_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1))
                # 如果是百分比形式，转换为0-1
                if value > 1:
                    value = value / 100
                return min(max(value, 0), 1)  # 确保在0-1范围内
            except ValueError:
                continue

    # 基于关键词推断置信度
    high_confidence_keywords = ['强烈', '确信', '明确', '肯定', 'strongly', 'definitely']
    medium_confidence_keywords = ['可能', '或许', '建议', 'probably', 'likely']
    low_confidence_keywords = ['不确定', '谨慎', '观望', 'uncertain', 'cautiously']

    text_lower = text.lower()

    if any(kw in text_lower for kw in high_confidence_keywords):
        return 0.85
    elif any(kw in text_lower for kw in low_confidence_keywords):
        return 0.55
    elif any(kw in text_lower for kw in medium_confidence_keywords):
        return 0.70

    return default


def _extract_key_factors(final_state: dict) -> List[str]:
    """
    提取关键因素（从各个报告中提取总结陈词）

    Args:
        final_state: 最终状态

    Returns:
        关键因素列表
    """
    import re

    factors = []

    # 从各个报告中提取总结陈词
    for report_key in ['market_report', 'fundamentals_report', 'sentiment_report', 'news_report']:
        report = final_state.get(report_key, '')
        if not report:
            continue

        # 尝试找到总结性的句子（通常包含"综合"、"总体"、"总结"等关键词）
        summary_keywords = ['综合', '总体', '总结', '综上', '因此', '所以', '建议']

        # 将报告分成句子
        sentences = re.split(r'[。！？\n]', report)

        # 查找包含总结关键词的句子
        summary_sentence = None
        for sentence in sentences:
            sentence = sentence.strip()
            if any(kw in sentence for kw in summary_keywords) and len(sentence) > 10:
                summary_sentence = sentence
                break

        # 如果没有找到总结句，使用最后一句有意义的句子
        if not summary_sentence:
            for sentence in reversed(sentences):
                sentence = sentence.strip()
                if len(sentence) > 20 and not sentence.startswith('#'):
                    summary_sentence = sentence
                    break

        if summary_sentence:
            # 限制长度到100字
            factors.append(summary_sentence[:100])

    return factors[:5]  # 最多返回5个


def _calculate_risk_score(risk_debate_state: dict) -> float:
    """
    计算风险评分（0-1，越高风险越大）

    Args:
        risk_debate_state: 风险辩论状态

    Returns:
        风险评分
    """
    if not risk_debate_state:
        return 0.5

    # 从judge_decision中提取风险关键词
    decision = risk_debate_state.get('judge_decision', '').lower()

    high_risk_keywords = ['高风险', '谨慎', '避免', '危险', '警告', 'high risk', 'caution', 'avoid']
    low_risk_keywords = ['低风险', '安全', '稳健', '可以', 'low risk', 'safe', 'stable']

    high_risk_score = sum(1 for kw in high_risk_keywords if kw in decision)
    low_risk_score = sum(1 for kw in low_risk_keywords if kw in decision)

    # 归一化到0-1范围
    if high_risk_score + low_risk_score == 0:
        return 0.5

    risk_score = high_risk_score / (high_risk_score + low_risk_score)
    return risk_score


def _extract_price_targets(final_state: dict) -> dict:
    """
    提取价格目标（入场价、止损价、止盈价）

    Args:
        final_state: 最终状态

    Returns:
        价格目标字典，包含 entry, stop_loss, take_profit
    """
    import re

    price_targets = {}

    # 搜索所有可能包含价格信息的字段
    search_texts = [
        final_state.get('final_trade_decision', ''),
        final_state.get('risk_debate_state', {}).get('judge_decision', ''),
        final_state.get('investment_debate_state', {}).get('judge_decision', ''),
    ]

    # 合并所有文本
    full_text = '\n'.join(search_texts)

    # 价格提取模式（更全面的匹配）
    price_patterns = {
        'entry': [
            r'入场价[位]?[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'建议价[位]?[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'目标价[位]?[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'买入价[位]?[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
        ],
        'stop_loss': [
            r'止损[价位]?[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'止损线[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'止损点位[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'止损单\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'跌破\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'设[置定]?止损[于在]\s*[¥\$]?(\d+(?:\.\d+)?)',
        ],
        'take_profit': [
            r'止盈[价位]?[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'止盈线[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'止盈点位[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'获利[了结]?[价位]?[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'目标[价位]?[：:]\s*[¥\$]?(\d+(?:\.\d+)?)',
        ]
    }

    # 对每个目标价格类型进行匹配
    for target_type, patterns in price_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1))
                    # 确保价格合理（大于0）
                    if price > 0:
                        price_targets[target_type] = price
                        logger.debug(f"[Price Targets] 提取到 {target_type}: {price}")
                        break  # 找到就跳出
                except (ValueError, IndexError):
                    continue

        # 如果没找到，尝试从具体语句中推断
        if target_type not in price_targets:
            # 例如："1200-1250元区间分批建仓"
            if target_type == 'entry':
                range_match = re.search(r'(\d+(?:\.\d+)?)\s*[-至]\s*(\d+(?:\.\d+)?)\s*元', full_text)
                if range_match:
                    try:
                        low = float(range_match.group(1))
                        high = float(range_match.group(2))
                        price_targets['entry'] = round((low + high) / 2, 2)
                        logger.debug(f"[Price Targets] 从区间推算 entry: {price_targets['entry']}")
                    except ValueError:
                        pass

    # 如果没有任何价格目标，返回空字典
    if not price_targets:
        logger.warning("[Price Targets] 未能提取到任何价格目标")

    return price_targets


def _extract_warnings(final_state: dict) -> List[str]:
    """
    提取警告信息

    Args:
        final_state: 最终状态

    Returns:
        警告列表
    """
    warnings = []

    # 从风险辩论中提取警告
    risk_debate = final_state.get('risk_debate_state', {})
    if risk_debate:
        judge_decision = risk_debate.get('judge_decision', '')
        if any(kw in judge_decision.lower() for kw in ['警告', '风险', '注意', 'warning', 'risk', 'caution']):
            # 提取第一句含有警告词的句子
            for sentence in judge_decision.split('。'):
                if any(kw in sentence for kw in ['警告', '风险', '注意', 'warning', 'risk', 'caution']):
                    warnings.append(sentence.strip())
                    break

    # 从各个分析师报告中提取警告
    for report_key in ['market_report', 'fundamentals_report', 'sentiment_report', 'news_report']:
        report = final_state.get(report_key, '')
        if '风险' in report or '警告' in report or 'warning' in report.lower():
            # 简单提取包含风险关键词的句子
            for sentence in report.split('。'):
                if '风险' in sentence or '警告' in sentence:
                    warnings.append(sentence.strip())
                    if len(warnings) >= 3:  # 最多3个警告
                        break
        if len(warnings) >= 3:
            break

    return warnings[:3]  # 最多返回3个警告


@router.get("/analyze-all-stream/{symbol}")
async def analyze_all_agents_stream(
    symbol: str,
    analysis_date: Optional[str] = Query(None, description="分析日期 YYYY-MM-DD")
):
    """
    流式分析所有Agent对某只股票的看法（Server-Sent Events）

    这个端点返回SSE流，实时推送分析进度：
    - start: 分析开始
    - progress: 每个Agent完成时的进度更新
    - complete: 分析完成，包含完整结果
    - error: 发生错误

    Args:
        symbol: 股票代码 (e.g., 600519.SH, 000001.SZ, NVDA)
        analysis_date: 分析日期，默认为今天

    Returns:
        StreamingResponse: SSE事件流
    """
    global trading_graph

    if trading_graph is None:
        raise HTTPException(status_code=503, detail="TradingAgentsGraph not initialized")

    if analysis_date is None:
        analysis_date = datetime.now().strftime('%Y-%m-%d')

    async def event_generator():
        """生成SSE事件流"""
        loop = asyncio.get_running_loop()
        progress_queue: asyncio.Queue = asyncio.Queue()

        def enqueue_event(event: Dict[str, Any]):
            loop.call_soon_threadsafe(progress_queue.put_nowait, event)

        def run_analysis():
            completed = set()

            def progress_callback(node_name: str, update: Dict[str, Any], state: Dict[str, Any]):
                info = _detect_agent_progress_update(update)
                if not info:
                    return

                agent_key = info["agent_key"]
                if agent_key in completed:
                    return

                completed.add(agent_key)
                enqueue_event({
                    "type": "agent_progress",
                    "agent": agent_key,
                    "label": info["agent_label"],
                    "report": info["report"],
                    "progress": _agent_progress_percentage(len(completed))
                })

            try:
                logger.info(f"[SSE] Starting analysis for {symbol} on {analysis_date}")
                final_state, processed_signal = trading_graph.propagate(
                    symbol,
                    analysis_date,
                    progress_callback=progress_callback
                )
                response = _format_response(final_state, processed_signal, symbol)
                enqueue_event({
                    "type": "complete",
                    "data": response
                })
                logger.info(f"[SSE] Analysis complete for {symbol}")
            except (MemoryDisabled, EmbeddingServiceUnavailable,
                    EmbeddingTextTooLong, EmbeddingInvalidInput, EmbeddingError) as mem_exc:
                enqueue_event({
                    "type": "memory_error",
                    "error": mem_exc
                })
            except Exception as exc:
                enqueue_event({
                    "type": "error",
                    "error": exc
                })

        analysis_future = None
        analysis_future = loop.run_in_executor(None, run_analysis)

        try:
            yield _sse_event({
                "type": "start",
                "symbol": symbol,
                "message": f"开始分析 {symbol}",
                "timestamp": datetime.now().isoformat()
            })

            while True:
                event = await progress_queue.get()
                evt_type = event.get("type")

                if evt_type == "agent_progress":
                    yield _sse_event({
                        "type": "progress",
                        "symbol": symbol,
                        "agent": event["agent"],
                        "agent_label": event["label"],
                        "message": f"{event['label']}分析完成",
                        "progress": event["progress"],
                        "data": {
                            "report": event["report"]
                        },
                        "timestamp": datetime.now().isoformat()
                    })
                elif evt_type == "complete":
                    yield _sse_event({
                        "type": "complete",
                        "symbol": symbol,
                        "message": "分析完成",
                        "data": event["data"],
                        "timestamp": datetime.now().isoformat()
                    })
                    break
                elif evt_type == "memory_error":
                    err = event.get("error")
                    http_exception = handle_memory_exception(err, f"流式分析{symbol}")
                    if http_exception:
                        detail = http_exception.detail
                        if isinstance(detail, dict):
                            error_message = detail.get('message', str(err))
                            error_description = detail.get('description', '')
                            error_suggestion = detail.get('suggestion', '')
                        else:
                            error_message = str(detail)
                            error_description = ''
                            error_suggestion = ''
                    else:
                        error_message = str(err)
                        error_description = ''
                        error_suggestion = ''

                    yield _sse_event({
                        "type": "error",
                        "symbol": symbol,
                        "error": error_message,
                        "description": error_description,
                        "suggestion": error_suggestion,
                        "error_type": "memory_error",
                        "timestamp": datetime.now().isoformat()
                    })
                    break
                elif evt_type == "error":
                    error_message = str(event.get("error", "Unknown error"))
                    logger.error(f"[SSE] Analysis failed for {symbol}: {error_message}")
                    yield _sse_event({
                        "type": "error",
                        "symbol": symbol,
                        "error": error_message,
                        "timestamp": datetime.now().isoformat()
                    })
                    break
        finally:
            if analysis_future and not analysis_future.done():
                analysis_future.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
        }
    )


def _sse_event(data: dict) -> str:
    """
    格式化SSE事件

    Args:
        data: 事件数据

    Returns:
        格式化的SSE消息
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """
    基于任务ID的SSE流式进度推送

    支持页面刷新后重新连接，自动恢复分析进度。

    Args:
        task_id: 任务ID

    Returns:
        StreamingResponse: SSE事件流
    """
    # 检查任务是否存在
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    async def event_generator():
        """生成SSE事件流"""
        try:
            # 发送开始事件
            yield _sse_event({
                "type": "start",
                "task_id": task_id,
                "symbol": task.symbol,
                "message": f"连接任务 {task_id}",
                "timestamp": datetime.now().isoformat()
            })

            # 如果任务已完成，直接返回结果
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                if task.status == TaskStatus.COMPLETED and task.result:
                    yield _sse_event({
                        "type": "complete",
                        "task_id": task_id,
                        "symbol": task.symbol,
                        "data": task.result,
                        "message": "分析已完成",
                        "timestamp": datetime.now().isoformat()
                    })
                elif task.status == TaskStatus.FAILED:
                    yield _sse_event({
                        "type": "error",
                        "task_id": task_id,
                        "symbol": task.symbol,
                        "error": task.error or "Unknown error",
                        "message": "分析失败",
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    yield _sse_event({
                        "type": "error",
                        "task_id": task_id,
                        "symbol": task.symbol,
                        "error": "Task was cancelled",
                        "message": "任务已取消",
                        "timestamp": datetime.now().isoformat()
                    })
                return

            # 监听任务进度（轮询）
            last_progress = -1
            last_message_count = 0

            while True:
                # 重新获取任务状态
                current_task = task_manager.get_task(task_id)
                if not current_task:
                    yield _sse_event({
                        "type": "error",
                        "task_id": task_id,
                        "error": "Task disappeared",
                        "timestamp": datetime.now().isoformat()
                    })
                    break

                # 检查进度是否有变化
                if current_task.progress != last_progress:
                    last_progress = current_task.progress

                    # 发送进度更新
                    yield _sse_event({
                        "type": "progress",
                        "task_id": task_id,
                        "symbol": current_task.symbol,
                        "progress": current_task.progress,
                        "message": current_task.progress_messages[-1]["message"] if current_task.progress_messages else "处理中...",
                        "timestamp": datetime.now().isoformat()
                    })

                # 检查是否有新的进度消息
                current_message_count = len(current_task.progress_messages)
                if current_message_count > last_message_count:
                    # 发送新消息
                    for msg in current_task.progress_messages[last_message_count:]:
                        yield _sse_event({
                            "type": "progress",
                            "task_id": task_id,
                            "symbol": current_task.symbol,
                            "progress": msg.get("progress", current_task.progress),
                            "message": msg.get("message", ""),
                            "timestamp": msg.get("timestamp", datetime.now().isoformat())
                        })
                    last_message_count = current_message_count

                # 检查任务是否完成
                if current_task.status == TaskStatus.COMPLETED:
                    if current_task.result:
                        yield _sse_event({
                            "type": "complete",
                            "task_id": task_id,
                            "symbol": current_task.symbol,
                            "data": current_task.result,
                            "message": "分析完成",
                            "timestamp": datetime.now().isoformat()
                        })
                    break
                elif current_task.status == TaskStatus.FAILED:
                    yield _sse_event({
                        "type": "error",
                        "task_id": task_id,
                        "symbol": current_task.symbol,
                        "error": current_task.error or "Unknown error",
                        "message": "分析失败",
                        "timestamp": datetime.now().isoformat()
                    })
                    break
                elif current_task.status == TaskStatus.CANCELLED:
                    yield _sse_event({
                        "type": "error",
                        "task_id": task_id,
                        "symbol": current_task.symbol,
                        "error": "Task was cancelled",
                        "message": "任务已取消",
                        "timestamp": datetime.now().isoformat()
                    })
                    break

                # 等待一段时间再检查
                await asyncio.sleep(0.5)  # 500ms轮询间隔

        except Exception as e:
            logger.error(f"[SSE] Task stream error for {task_id}: {e}", exc_info=True)
            yield _sse_event({
                "type": "error",
                "task_id": task_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用nginx缓冲
            "Connection": "keep-alive",
        }
    )


@router.post("/analyze-position/{symbol}")
async def analyze_position(
    symbol: str,
    request: PositionAnalysisRequest
):
    """
    分析持仓并给出操作建议

    考虑持仓成本、当前价格、市场状况，给出：
    - 是否卖出/持有/加仓
    - 建议价格点位
    - 风险评估

    Args:
        symbol: 股票代码
        request: 持仓分析请求（包含持仓信息）

    Returns:
        持仓分析结果和操作建议
    """
    global trading_graph

    if trading_graph is None:
        raise HTTPException(status_code=503, detail="TradingAgentsGraph not initialized")

    analysis_date = request.analysis_date or datetime.now().strftime('%Y-%m-%d')

    try:
        logger.info(f"[POSITION] Analyzing position for {symbol}")

        # 1. 先进行常规分析
        final_state, processed_signal = trading_graph.propagate(symbol, analysis_date)
        agent_results_data = _format_response(final_state, processed_signal, symbol)

        # 2. 提取持仓信息
        holdings = request.holdings
        avg_price = holdings.get('avg_price', 0)
        quantity = holdings.get('quantity', 0)
        current_price = holdings.get('current_price', 0)
        purchase_date = holdings.get('purchase_date', '')

        # 3. 计算持仓盈亏
        unrealized_pnl = (current_price - avg_price) * quantity
        unrealized_pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

        # 4. 基于分析结果和持仓情况给出建议
        market_direction = agent_results_data.get('aggregated_signal', {}).get('direction', 'hold')
        confidence = agent_results_data.get('aggregated_signal', {}).get('confidence', 0.5)

        # 决策逻辑
        if unrealized_pnl_pct < -15:  # 亏损超过15%
            if market_direction == 'short':
                decision = 'sell'
                reasoning = f"持仓亏损{unrealized_pnl_pct:.1f}%，且市场看空，建议止损"
            else:
                decision = 'hold'
                reasoning = f"持仓亏损{unrealized_pnl_pct:.1f}%，但市场看多，建议持有待反弹"
        elif unrealized_pnl_pct > 20:  # 盈利超过20%
            if market_direction == 'long':
                decision = 'add'
                reasoning = f"持仓盈利{unrealized_pnl_pct:.1f}%，且市场持续看多，可考虑加仓"
            else:
                decision = 'sell'
                reasoning = f"持仓盈利{unrealized_pnl_pct:.1f}%，市场转空，建议止盈"
        else:  # 盈亏在-15%到20%之间
            if market_direction == 'long' and confidence > 0.7:
                decision = 'hold'
                reasoning = f"持仓盈亏{unrealized_pnl_pct:.1f}%，市场看多且信心较高，建议持有"
            elif market_direction == 'short' and confidence > 0.7:
                decision = 'sell'
                reasoning = f"持仓盈亏{unrealized_pnl_pct:.1f}%，市场看空且信心较高，建议卖出"
            else:
                decision = 'hold'
                reasoning = f"持仓盈亏{unrealized_pnl_pct:.1f}%，市场方向不明确，建议持有观望"

        # 5. 建议操作
        suggested_action = {
            "action": decision,
            "quantity": quantity if decision == 'sell' else int(quantity * 0.3) if decision == 'add' else 0,
            "price_range": {
                "min": current_price * 0.98,
                "max": current_price * 1.02
            },
            "stop_loss": avg_price * 0.92 if decision != 'sell' else None,
            "take_profit": avg_price * 1.15 if decision != 'sell' else None,
        }

        # 6. 风险评估
        risk_level = "high" if abs(unrealized_pnl_pct) > 15 else "medium" if abs(unrealized_pnl_pct) > 8 else "low"
        risk_assessment = {
            "level": risk_level,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "holding_days": (datetime.now() - datetime.fromisoformat(purchase_date)).days if purchase_date else 0,
            "warnings": []
        }

        if unrealized_pnl_pct < -10:
            risk_assessment['warnings'].append(f"持仓亏损{unrealized_pnl_pct:.1f}%，注意风险控制")
        if market_direction != agent_results_data.get('llm_analysis', {}).get('recommended_direction', 'hold'):
            risk_assessment['warnings'].append("市场信号与LLM分析存在分歧，需谨慎判断")

        response = {
            "success": True,
            "symbol": symbol,
            "decision": decision,
            "reasoning": reasoning,
            "suggested_action": suggested_action,
            "risk_assessment": risk_assessment,
            "agent_results": agent_results_data.get('agent_results', {}),
            "aggregated_signal": agent_results_data.get('aggregated_signal', {}),
            "llm_analysis": agent_results_data.get('llm_analysis', {}),
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"[POSITION] Position analysis complete for {symbol}: {decision}")
        return response

    except (MemoryDisabled, EmbeddingServiceUnavailable,
            EmbeddingTextTooLong, EmbeddingInvalidInput, EmbeddingError) as e:
        # 处理memory相关异常，返回用户友好的错误信息
        http_exception = handle_memory_exception(e, f"持仓分析{symbol}")
        if http_exception:
            raise http_exception
        else:
            # 理论上不会到这里
            logger.error(f"[POSITION] Unhandled memory exception for {symbol}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"[POSITION] Position analysis failed for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
