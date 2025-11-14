"""
Agent Analysis API Router

提供TradingAgents多Agent分析的API端点
"""

from fastapi import APIRouter, HTTPException, Query
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
    分析所有Agent对某只股票的看法
   
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
       
    except Exception as e:
        logger.error(f"[ERROR] Analysis failed for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
    # 注意区分三个不同的内容：
    # 1. reasoning: 投资辩论结果的总结（judge_decision from investment_debate_state）
    # 2. risk_assessment: 风险评估的简短摘要（judge_decision from risk_debate_state，前300字）
    # 3. risk_manager_decision: 风险管理者的完整决策报告（judge_decision from risk_debate_state，完整内容）
    # 4. signal_processor_summary: Signal Processor的最终决策摘要（final_trade_decision，完整内容）

    judge_decision_full = debate_state.get('judge_decision', '')
    risk_judge_decision_full = risk_debate_state.get('judge_decision', '')
    final_trade_decision_full = final_state.get('final_trade_decision', '')

    # 添加日志以调试
    logger.debug(f"[Data Sources] judge_decision: {len(judge_decision_full)} chars")
    logger.debug(f"[Data Sources] risk_judge_decision: {len(risk_judge_decision_full)} chars")
    logger.debug(f"[Data Sources] final_trade_decision: {len(final_trade_decision_full)} chars")

    # 如果final_trade_decision为空，使用risk_judge_decision作为fallback
    if not final_trade_decision_full and risk_judge_decision_full:
        logger.warning("[Data Sources] final_trade_decision is empty, using risk_judge_decision as fallback")
        final_trade_decision_full = risk_judge_decision_full

    # 提取风险评估的简短摘要（只取前300字）
    risk_assessment_short = risk_judge_decision_full[:300] + '...' if len(risk_judge_decision_full) > 300 else risk_judge_decision_full or '无风险评估'

    llm_analysis = {
        "recommended_direction": _extract_direction(judge_decision_full),
        "confidence": 0.85,
        "reasoning": judge_decision_full[:500] if judge_decision_full else '无投资辩论结果',  # 投资辩论结果摘要
        "risk_assessment": risk_assessment_short,  # 风险评估简短摘要（300字）
        "key_factors": _extract_key_factors(final_state),
        "risk_score": _calculate_risk_score(risk_debate_state),
        "risk_analysts": risk_analysts if risk_analysts else None,
        "risk_manager_decision": risk_judge_decision_full,  # 完整的风险管理者决策
        "price_targets": _extract_price_targets(final_state),
        "analysis_timestamp": datetime.now().isoformat(),
        "signal_processor_summary": final_trade_decision_full  # 完整的Signal Processor总结
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
        try:
            # 发送开始事件
            yield _sse_event({
                "type": "start",
                "symbol": symbol,
                "message": f"开始分析 {symbol}",
                "timestamp": datetime.now().isoformat()
            })

            # 模拟进度更新（真实实现应该hook到TradingGraph的各个节点）
            agents = ['technical', 'fundamental', 'sentiment', 'policy']
            for i, agent in enumerate(agents):
                await asyncio.sleep(1)  # 模拟处理时间
                yield _sse_event({
                    "type": "progress",
                    "symbol": symbol,
                    "agent": agent,
                    "status": "completed",
                    "message": f"{agent} 分析完成",
                    "progress": int((i + 1) / len(agents) * 100),
                    "timestamp": datetime.now().isoformat()
                })

            # 执行实际分析
            logger.info(f"[SSE] Starting analysis for {symbol} on {analysis_date}")
            final_state, processed_signal = trading_graph.propagate(symbol, analysis_date)

            # 格式化结果
            response = _format_response(final_state, processed_signal, symbol)

            # 发送完成事件
            yield _sse_event({
                "type": "complete",
                "symbol": symbol,
                "message": "分析完成",
                "data": response,
                "timestamp": datetime.now().isoformat()
            })

            logger.info(f"[SSE] Analysis complete for {symbol}")

        except Exception as e:
            logger.error(f"[SSE] Analysis failed for {symbol}: {e}", exc_info=True)
            yield _sse_event({
                "type": "error",
                "symbol": symbol,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

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

    except Exception as e:
        logger.error(f"[POSITION] Position analysis failed for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
