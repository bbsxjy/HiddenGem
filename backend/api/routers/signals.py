"""
Signals API Router

提供交易信号的API端点
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import random

router = APIRouter()


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


@router.get("/recent")
async def get_recent_signals(limit: int = Query(20, description="Maximum number of recent signals")):
    """获取最近的交易信号"""
    # 复用 current signals 的逻辑
    return await get_current_signals(limit)


@router.get("/current")
async def get_current_signals(limit: int = Query(20, description="Maximum number of signals")):
    """获取当前有效的交易信号"""
    # TODO: 从Agent分析结果或信号系统获取真实信号
    # 当前返回模拟数据

    symbols = [
        ("600519.SH", "贵州茅台"),
        ("000001.SZ", "平安银行"),
        ("NVDA", "英伟达"),
        ("AAPL", "苹果"),
        ("TSLA", "特斯拉"),
        ("600036.SS", "招商银行"),
        ("000858.SZ", "五粮液"),
    ]

    signals = []
    for i in range(min(limit, len(symbols))):
        symbol, name = symbols[i]
        direction_raw = random.choice(["buy", "sell", "hold"])

        # 生成合理的价格
        base_price = round(random.uniform(100, 2000), 2)
        entry_price = base_price
        target_price = round(base_price * (1.1 if direction_raw == "buy" else 0.9), 2) if direction_raw != "hold" else None
        stop_loss_price = round(base_price * (0.95 if direction_raw == "buy" else 1.05), 2) if direction_raw != "hold" else None

        created_time = datetime.now() - timedelta(hours=random.randint(0, 24))

        signals.append({
            "id": 5000 + i,  # 前端期望id而不是signal_id
            "symbol": symbol,
            "direction": direction_raw,  # buy, sell, hold (前端期望这些值)
            "strength": round(random.uniform(0.5, 1.0), 2),
            "agent_name": random.choice(["technical", "fundamental", "sentiment", "multi-agent"]),  # 前端期望agent_name
            "strategy_name": None,
            "entry_price": entry_price,  # 前端期望entry_price
            "target_price": target_price,
            "stop_loss_price": stop_loss_price,  # 前端期望stop_loss_price而不是stop_loss
            "reasoning": f"基于{random.choice(['技术面', '基本面', '情绪面', '多Agent综合'])}分析，{name}显示{direction_raw}信号",
            "timestamp": created_time.isoformat(),  # 前端期望timestamp
            "is_executed": False,  # 前端期望is_executed
        })

    # Sort by strength descending
    signals.sort(key=lambda x: x["strength"], reverse=True)

    return {
        "success": True,
        "data": signals[:limit],
        "timestamp": datetime.now().isoformat()
    }


@router.get("/history")
async def get_signal_history(
    days: int = Query(30, description="Number of days to look back"),
    symbol: Optional[str] = Query(None, description="Filter by symbol")
):
    """获取历史信号"""
    # TODO: 从数据库获取真实信号历史

    signals = []
    for i in range(20):
        created_time = datetime.now() - timedelta(days=random.randint(0, days-1))

        signals.append({
            "signal_id": 6000 + i,
            "symbol": symbol if symbol else random.choice(["600519.SH", "NVDA", "000001.SZ"]),
            "name": "贵州茅台" if not symbol else "未知",
            "direction": random.choice(["long", "short", "hold"]),
            "strength": round(random.uniform(0.5, 1.0), 2),
            "confidence": round(random.uniform(0.6, 0.95), 2),
            "source": random.choice(["technical", "fundamental", "sentiment", "multi-agent"]),
            "reasoning": "历史信号记录",
            "target_price": round(random.uniform(100, 2000), 2),
            "stop_loss": round(random.uniform(50, 1500), 2),
            "created_at": created_time.isoformat(),
            "expires_at": (created_time + timedelta(days=7)).isoformat(),
            "actual_return": round(random.uniform(-0.1, 0.2), 4),  # 实际收益率
            "status": random.choice(["active", "expired", "triggered"]),
        })

    signals.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "success": True,
        "data": signals,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/{signal_id}")
async def get_signal(signal_id: int):
    """获取单个信号详情"""
    # TODO: 从数据库获取真实信号

    signal = {
        "signal_id": signal_id,
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "direction": "long",
        "strength": 0.85,
        "confidence": 0.78,
        "source": "multi-agent",
        "reasoning": "多Agent综合分析显示强烈买入信号",
        "target_price": 1800.0,
        "stop_loss": 1550.0,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
        "agent_votes": {
            "technical": "long",
            "fundamental": "long",
            "sentiment": "hold",
            "policy": "long",
        }
    }

    return {
        "success": True,
        "data": signal,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/stats/summary")
async def get_signal_stats():
    """获取信号统计摘要"""
    # TODO: 从数据库计算真实统计

    stats = {
        "total_signals": 156,
        "active_signals": 7,
        "avg_accuracy": 0.68,
        "total_profit": 45600.0,
        "win_rate": 0.65,
        "best_performing_source": "multi-agent",
        "signals_by_direction": {
            "long": 89,
            "short": 45,
            "hold": 22,
        },
        "signals_by_source": {
            "technical": 52,
            "fundamental": 38,
            "sentiment": 31,
            "multi-agent": 35,
        }
    }

    return {
        "success": True,
        "data": stats,
        "timestamp": datetime.now().isoformat()
    }
