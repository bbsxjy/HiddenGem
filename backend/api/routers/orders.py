"""
Orders API Router

提供订单管理的API端点
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from api.services.trading_service import trading_service

router = APIRouter()


# Pydantic Models
class Order(BaseModel):
    id: int  # 前端期望 id 而不是 order_id
    symbol: str
    name: str
    side: str  # buy, sell
    order_type: str  # market, limit
    quantity: int
    price: Optional[float] = None
    filled_quantity: int
    avg_filled_price: Optional[float] = None
    status: str  # pending, filled, cancelled, rejected
    created_at: str
    updated_at: str
    strategy_name: Optional[str] = None  # 策略名称
    reasoning: Optional[str] = None  # 交易原因


@router.get("/")
async def get_orders(
    status: Optional[str] = Query(None, description="Filter by status: pending, filled, cancelled"),
    limit: int = Query(50, description="Maximum number of orders to return")
):
    """获取订单列表"""
    orders = trading_service.get_orders(status)

    # Apply limit
    limited_orders = orders[:limit]

    return {
        "success": True,
        "data": limited_orders,
        "total": len(orders),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/history/recent")
async def get_recent_orders(days: int = Query(7, description="Number of days to look back")):
    """获取最近的订单历史"""
    # 获取所有订单，按创建时间过滤
    all_orders = trading_service.get_orders()

    # 过滤最近days天的订单
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_orders = [
        order for order in all_orders
        if order.get("created_at") and datetime.fromisoformat(order["created_at"]) >= cutoff_date
    ]

    # 按创建时间降序排序
    recent_orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # 前端期望 {orders: [...], count: ...} 格式
    return {
        "success": True,
        "data": {
            "orders": recent_orders,
            "count": len(recent_orders)
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/{order_id}")
async def get_order(order_id: int):
    """获取单个订单详情"""
    order = trading_service.get_order(order_id)

    if not order:
        return {
            "success": False,
            "error": {
                "code": "ORDER_NOT_FOUND",
                "message": f"订单 {order_id} 不存在"
            },
            "timestamp": datetime.now().isoformat()
        }

    return {
        "success": True,
        "data": order,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/")
async def create_order(order: dict):
    """创建新订单"""
    try:
        new_order = trading_service.create_order(order)

        return {
            "success": True,
            "data": new_order,
            "message": "订单创建成功",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "ORDER_CREATE_FAILED",
                "message": str(e)
            },
            "timestamp": datetime.now().isoformat()
        }


@router.delete("/{order_id}")
async def cancel_order(order_id: int):
    """取消订单"""
    success = trading_service.cancel_order(order_id)

    if not success:
        return {
            "success": False,
            "error": {
                "code": "ORDER_NOT_FOUND",
                "message": f"订单 {order_id} 不存在或无法取消"
            },
            "timestamp": datetime.now().isoformat()
        }

    return {
        "success": True,
        "message": f"订单 {order_id} 已取消",
        "timestamp": datetime.now().isoformat()
    }
