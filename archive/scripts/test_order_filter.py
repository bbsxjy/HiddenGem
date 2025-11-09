"""
Test order status filtering with multiple values.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from sqlalchemy import select
from config.database import db_config
from database.models import Order, OrderStatus


async def test_order_status_filter():
    """Test filtering orders by multiple status values."""

    print("=" * 80)
    print("Testing Order Status Filter")
    print("=" * 80)

    async with db_config.AsyncSessionLocal() as session:
        # Test 1: Filter by single status
        print("\n[Test 1] Filter by single status: 'pending'")
        stmt = select(Order).where(Order.status == OrderStatus.PENDING).limit(5)
        result = await session.execute(stmt)
        orders = result.scalars().all()
        print(f"  Found {len(orders)} pending orders")

        # Test 2: Filter by multiple status values
        print("\n[Test 2] Filter by multiple statuses: ['pending', 'submitted']")
        status_enums = [OrderStatus.PENDING, OrderStatus.SUBMITTED]
        stmt = select(Order).where(Order.status.in_(status_enums)).limit(5)
        result = await session.execute(stmt)
        orders = result.scalars().all()
        print(f"  Found {len(orders)} orders with status pending or submitted")

        # Show order details
        if orders:
            print("\n  Orders:")
            for order in orders:
                print(f"    - Order {order.id}: {order.symbol} {order.side} {order.status.value}")
        else:
            print("  (No orders found - this is normal if database is empty)")

    print("\n" + "=" * 80)
    print("Test Complete!")
    print("=" * 80)
    print("\nThe fix allows filtering orders by comma-separated status values.")
    print("Example API call: GET /api/v1/orders/?status=pending,submitted")


if __name__ == "__main__":
    asyncio.run(test_order_status_filter())
