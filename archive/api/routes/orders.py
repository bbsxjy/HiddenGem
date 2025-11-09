"""
Order management API routes.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from config.database import get_db
from api.models.request import OrderCreateRequest, OrderResponse, SuccessResponse
from database.models import Order, OrderStatus


router = APIRouter()


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    request: OrderCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new order.

    Args:
        request: Order creation request
        db: Database session

    Returns:
        Created order
    """
    try:
        # Validate quantity (must be multiple of 100 for A-share)
        if request.quantity % 100 != 0:
            raise HTTPException(
                status_code=400,
                detail="Quantity must be multiple of 100 shares"
            )

        # Create order (simplified - would integrate with broker API)
        order = Order(
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            status=OrderStatus.PENDING,
            strategy_name=request.strategy_name,
            created_at=datetime.utcnow()
        )

        db.add(order)
        await db.commit()
        await db.refresh(order)

        logger.info(f"Created order: {order.id} - {order.symbol} {order.side} {order.quantity}")

        return OrderResponse(
            id=order.id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            filled_quantity=order.filled_quantity,
            avg_filled_price=order.avg_filled_price,
            status=order.status.value,
            created_at=order.created_at,
            filled_at=order.filled_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[OrderResponse])
async def list_orders(
    status: Optional[str] = Query(None, description="Filter by status (comma-separated for multiple)"),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    List orders.

    Args:
        status: Filter by status (e.g., "pending" or "pending,submitted")
        limit: Maximum results
        db: Database session

    Returns:
        List of orders
    """
    try:
        stmt = select(Order).order_by(Order.created_at.desc()).limit(limit)

        if status:
            # Parse comma-separated status values
            status_list = [s.strip() for s in status.split(',')]

            # Convert to OrderStatus enums
            try:
                status_enums = [OrderStatus(s) for s in status_list]
                stmt = stmt.where(Order.status.in_(status_enums))
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status value. Valid values: {', '.join([s.value for s in OrderStatus])}"
                )

        result = await db.execute(stmt)
        orders = result.scalars().all()

        return [
            OrderResponse(
                id=o.id,
                symbol=o.symbol,
                side=o.side,
                order_type=o.order_type,
                quantity=o.quantity,
                price=o.price,
                filled_quantity=o.filled_quantity,
                avg_filled_price=o.avg_filled_price,
                status=o.status.value,
                created_at=o.created_at,
                filled_at=o.filled_at
            )
            for o in orders
        ]

    except Exception as e:
        logger.error(f"Error listing orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get order details.

    Args:
        order_id: Order ID
        db: Database session

    Returns:
        Order details
    """
    try:
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        return OrderResponse(
            id=order.id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            filled_quantity=order.filled_quantity,
            avg_filled_price=order.avg_filled_price,
            status=order.status.value,
            created_at=order.created_at,
            filled_at=order.filled_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{order_id}", response_model=SuccessResponse)
async def cancel_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """
    Cancel an order.

    Args:
        order_id: Order ID
        db: Database session

    Returns:
        Success response
    """
    try:
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        # Can only cancel pending or submitted orders
        if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel order with status {order.status.value}"
            )

        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.utcnow()

        await db.commit()

        logger.info(f"Cancelled order: {order_id}")

        return SuccessResponse(
            success=True,
            message=f"Order {order_id} cancelled"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/recent")
async def get_recent_orders(
    days: int = Query(7, le=90),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent order history.

    Args:
        days: Number of days
        db: Database session

    Returns:
        Recent orders
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(Order)
            .where(Order.created_at >= cutoff_date)
            .order_by(Order.created_at.desc())
        )

        result = await db.execute(stmt)
        orders = result.scalars().all()

        return {
            'orders': [
                {
                    'id': o.id,
                    'symbol': o.symbol,
                    'side': o.side,
                    'quantity': o.quantity,
                    'price': float(o.price) if o.price else None,
                    'status': o.status.value,
                    'created_at': o.created_at.isoformat()
                }
                for o in orders
            ],
            'count': len(orders)
        }

    except Exception as e:
        logger.error(f"Error fetching order history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
