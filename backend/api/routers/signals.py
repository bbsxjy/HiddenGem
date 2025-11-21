"""
Signals API Router

提供交易信号的API端点
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.services.task_manager import task_manager, TaskStatus

router = APIRouter()
logger = logging.getLogger(__name__)

SIGNAL_TTL_HOURS = int(os.getenv("SIGNAL_TTL_HOURS", "24"))
SIGNAL_TASK_LOOKBACK_MULTIPLIER = int(os.getenv("SIGNAL_LOOKBACK_MULTIPLIER", "4"))
MAX_SIGNAL_LOOKBACK = int(os.getenv("SIGNAL_MAX_LOOKBACK", "200"))

# 样例信号模板，用于没有历史任务时的占位数据
_SAMPLE_SIGNAL_TEMPLATES = [
    {
        "symbol": "NVDA",
        "direction": "long",
        "strength": 0.35,
        "confidence": 0.82,
        "source": "demo-cache",
        "reasoning": (
            "英伟达在AI基础设施需求持续攀升的背景下，营收与利润屡创新高。"
            "多因子信号显示资金流入与估值扩张同步，建议逢回调分批布局。"
        ),
        "target_price": 148.0,
        "stop_loss": 128.5,
    },
    {
        "symbol": "AAPL",
        "direction": "hold",
        "strength": 0.2,
        "confidence": 0.58,
        "source": "demo-cache",
        "reasoning": "苹果基本面稳健，但短期催化剂不足。等待 Vision Pro 量产数据确认后再增持。",
        "target_price": 215.0,
        "stop_loss": 185.0,
    },
    {
        "symbol": "600519.SH",
        "direction": "long",
        "strength": 0.4,
        "confidence": 0.78,
        "source": "demo-cache",
        "reasoning": "茅台批价企稳回升，高端白酒动销改善，机构持仓小幅提升，适合中期配置。",
        "target_price": 2050.0,
        "stop_loss": 1820.0,
    },
    {
        "symbol": "000001.SZ",
        "direction": "short",
        "strength": 0.25,
        "confidence": 0.63,
        "source": "demo-cache",
        "reasoning": "银行板块受净息差收窄与坏账预期影响，指标股短期承压，弹性有限。",
        "target_price": 9.6,
        "stop_loss": 11.1,
    },
]


# Pydantic Models
class Signal(BaseModel):
    signal_id: int
    symbol: str
    name: str
    direction: str  # long, short, hold
    strength: float  # 0-1
    confidence: float  # 0-1
    source: str  # technical, fundamental, sentiment, multi-agent
    reasoning: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    created_at: str
    expires_at: Optional[str] = None


def _clamp_float(value: Optional[float], default: float = 0.5) -> float:
    """Clamp numeric values to [0, 1] after safe conversion."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(0.0, min(1.0, numeric))


def _safe_float(value) -> Optional[float]:
    """Convert arbitrary value to float if possible."""
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(dt_str: Optional[str]) -> datetime:
    if not dt_str:
        return datetime.now()
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return datetime.now()


def _generate_signal_id(task_id: Optional[str], fallback_seed: int) -> int:
    if not task_id:
        return 900000 + fallback_seed
    try:
        return int(UUID(task_id)) % 1_000_000_000
    except (ValueError, AttributeError):
        return abs(hash(task_id)) % 1_000_000_000


def _build_signal_from_task(task: dict, index: int) -> Optional[Signal]:
    result = task.get("result") or {}
    aggregated = result.get("aggregated_signal") or {}
    llm_analysis = result.get("llm_analysis") or {}

    direction = aggregated.get("direction") or llm_analysis.get("recommended_direction")
    if not direction:
        return None

    symbol = task.get("symbol") or result.get("symbol") or "UNKNOWN"
    created_dt = _parse_datetime(task.get("completed_at") or task.get("created_at"))
    expires_dt = created_dt + timedelta(hours=SIGNAL_TTL_HOURS)

    price_targets = llm_analysis.get("price_targets") or {}
    metadata = aggregated.get("metadata") or {}

    strength = _clamp_float(
        aggregated.get("position_size", aggregated.get("confidence"))
    )
    confidence = _clamp_float(
        aggregated.get("confidence", llm_analysis.get("confidence"))
    )

    reasoning = (
        llm_analysis.get("reasoning")
        or metadata.get("llm_reasoning")
        or metadata.get("summary")
        or "多Agent综合信号，建议结合自身风险偏好决策。"
    )

    return Signal(
        signal_id=_generate_signal_id(task.get("task_id"), index),
        symbol=symbol,
        name=f"{symbol} 多Agent综合信号",
        direction=direction,
        strength=strength,
        confidence=confidence,
        source=metadata.get("analysis_method", "multi-agent"),
        reasoning=reasoning,
        target_price=_safe_float(
            price_targets.get("take_profit")
            or price_targets.get("target")
            or price_targets.get("entry")
        ),
        stop_loss=_safe_float(price_targets.get("stop_loss")),
        created_at=created_dt.isoformat(),
        expires_at=expires_dt.isoformat()
    )


def _get_signals_from_recent_tasks(limit: int) -> List[Signal]:
    lookback = min(MAX_SIGNAL_LOOKBACK, max(limit * SIGNAL_TASK_LOOKBACK_MULTIPLIER, limit))
    raw_tasks = task_manager.list_tasks(
        status=TaskStatus.COMPLETED,
        limit=lookback
    )

    signals: List[Signal] = []
    for idx, task in enumerate(raw_tasks):
        if task.get("task_type") not in {"analyze_all"}:
            continue
        if not task.get("result"):
            continue

        signal = _build_signal_from_task(task, idx)
        if signal:
            signals.append(signal)

        if len(signals) >= limit:
            break

    return signals


def _get_fallback_signals(limit: int) -> List[Signal]:
    now = datetime.now()
    fallback_signals: List[Signal] = []

    for idx, template in enumerate(_SAMPLE_SIGNAL_TEMPLATES):
        created_at = now - timedelta(minutes=idx * 5)
        expires_at = created_at + timedelta(hours=SIGNAL_TTL_HOURS)
        fallback_signals.append(
            Signal(
                signal_id=1_000_000 + idx,
                symbol=template["symbol"],
                name=f"{template['symbol']} 样例信号",
                direction=template["direction"],
                strength=_clamp_float(template["strength"], default=0.3),
                confidence=_clamp_float(template["confidence"], default=0.6),
                source=template.get("source", "demo-cache"),
                reasoning=template["reasoning"],
                target_price=_safe_float(template.get("target_price")),
                stop_loss=_safe_float(template.get("stop_loss")),
                created_at=created_at.isoformat(),
                expires_at=expires_at.isoformat()
            )
        )

        if len(fallback_signals) >= limit:
            break

    return fallback_signals


@router.get("/recent")
async def get_recent_signals(limit: int = Query(20, description="Maximum number of recent signals")):
    """获取最近的交易信号"""
    # 复用 current signals 的逻辑
    return await get_current_signals(limit)


@router.get("/current")
async def get_current_signals(limit: int = Query(20, description="Maximum number of signals")):
    """
    获取当前有效的交易信号。

    信号优先从已完成的异步分析任务中提取，若暂未有任务结果，则提供样例信号占位。
    """
    limit = max(1, min(100, limit))

    signals = _get_signals_from_recent_tasks(limit)
    source = "task_cache"

    if not signals:
        signals = _get_fallback_signals(limit)
        source = "fallback"
        logger.info("⚠️ 未找到可用的分析任务结果，返回样例信号。")

    return {
        "success": True,
        "data": [signal.dict() for signal in signals],
        "count": len(signals),
        "source": source,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/history")
async def get_signal_history(
    days: int = Query(30, description="Number of days to look back"),
    symbol: Optional[str] = Query(None, description="Filter by symbol")
):
    """获取历史信号 —— TODO: 待落地MongoDB后接入"""

    logger.warning(f"⚠️ get_signal_history() 尚未落地，返回空列表 (days={days}, symbol={symbol})")

    return {
        "success": True,
        "data": [],
        "message": "Signal history storage not yet implemented - requires MongoDB integration",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/{signal_id}")
async def get_signal(signal_id: int):
    """获取单个信号详情 —— TODO: 待落地MongoDB后接入"""

    logger.warning(f"⚠️ get_signal({signal_id}) 尚未落地")

    from fastapi import HTTPException
    raise HTTPException(
        status_code=404,
        detail=f"Signal {signal_id} not found - signal storage not yet implemented"
    )


@router.get("/stats/summary")
async def get_signal_stats():
    """获取信号统计摘要 —— TODO: 待落地历史仓储后讨论"""

    logger.warning("⚠️ get_signal_stats() 尚未落地")

    stats = {
        "total_signals": 0,
        "active_signals": 0,
        "avg_accuracy": 0.0,
        "total_profit": 0.0,
        "win_rate": 0.0,
        "best_performing_source": None,
        "signals_by_direction": {
            "long": 0,
            "short": 0,
            "hold": 0,
        },
        "signals_by_source": {
            "technical": 0,
            "fundamental": 0,
            "sentiment": 0,
            "multi-agent": 0,
        }
    }

    return {
        "success": True,
        "data": stats,
        "message": "Signal statistics not yet implemented - requires historical signal storage",
        "timestamp": datetime.now().isoformat()
    }
