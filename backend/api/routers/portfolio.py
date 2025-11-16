"""
Portfolio API Router

提供投资组合管理的API端点
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from api.services.trading_service import trading_service

router = APIRouter()


# Pydantic Models
class Position(BaseModel):
    symbol: str
    name: str
    quantity: int
    avg_cost: float  # 修改：前端期望avg_cost而不是avg_price
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float  # 修改：前端期望unrealized_pnl_pct
    today_pnl: float
    today_pnl_pct: float  # 修改：前端期望today_pnl_pct


class PortfolioSummary(BaseModel):
    total_value: float
    cash: float
    positions_value: float
    total_pnl: float
    total_pnl_percent: float
    daily_pnl: float
    daily_pnl_percent: float


class PortfolioHistoryItem(BaseModel):
    timestamp: str  # 修改：前端期望timestamp而不是date
    total_value: float
    cash: float
    positions_value: float
    total_pnl: float  # 新增：前端需要total_pnl
    daily_pnl: float
    daily_pnl_percent: float


@router.get("/summary")
async def get_portfolio_summary():
    """获取投资组合摘要"""
    summary = trading_service.get_portfolio_summary()

    return {
        "success": True,
        "data": summary,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/positions")
async def get_positions():
    """获取当前持仓"""
    positions = trading_service.get_positions()

    return {
        "success": True,
        "data": positions,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/positions/{symbol}")
async def get_position(symbol: str):
    """获取单个持仓详情"""
    position = trading_service.get_position(symbol)

    if not position:
        return {
            "success": False,
            "error": {
                "code": "POSITION_NOT_FOUND",
                "message": f"持仓 {symbol} 不存在"
            },
            "timestamp": datetime.now().isoformat()
        }

    return {
        "success": True,
        "data": position,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/history")
async def get_portfolio_history(days: int = 30):
    """获取投资组合历史数据"""
    snapshots = trading_service.get_portfolio_history(days)

    return {
        "success": True,
        "data": {
            "snapshots": snapshots  # 前端期望{snapshots: []}格式
        },
        "timestamp": datetime.now().isoformat()
    }
