"""
Order Manager.
Manages order lifecycle: creation, submission, tracking, cancellation.
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from enum import Enum

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import Order, OrderStatus, OrderSide, Position, TradingBoard
from core.data.models import OrderRequest
from core.utils.helpers import calculate_commission, get_trading_board
from config.settings import settings


class OrderManager:
    """
    Order Manager.

    Handles order lifecycle:
    - Validation
    - Risk checks
    - Submission to broker
    - Status tracking
    - Position updates
    """

    def __init__(self, broker_interface=None, risk_control=None):
        """
        Initialize order manager.

        Args:
            broker_interface: Broker API interface
            risk_control: Risk control system
        """
        self.broker_interface = broker_interface
        self.risk_control = risk_control

        # Order tracking
        self.pending_orders: Dict[int, Order] = {}
        self.active_orders: Dict[int, Order] = {}

        logger.info("OrderManager initialized")

    async def create_order(
        self,
        request: OrderRequest,
        db_session: AsyncSession
    ) -> Order:
        """
        Create and submit an order.

        Args:
            request: Order request
            db_session: Database session

        Returns:
            Created order

        Raises:
            ValueError: If validation fails
        """
        # 1. Validate order
        await self._validate_order(request, db_session)

        # 2. Pre-trade risk checks
        if self.risk_control:
            risk_check = await self.risk_control.check_order(request, db_session)
            if not risk_check['passed']:
                raise ValueError(f"Risk check failed: {risk_check['reason']}")

        # 3. Create order record
        board = get_trading_board(request.symbol)

        order = Order(
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            board=board,
            status=OrderStatus.PENDING,
            strategy_name=request.strategy_name,
            created_at=datetime.utcnow()
        )

        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        logger.info(f"Created order {order.id}: {order.symbol} {order.side} {order.quantity}")

        # 4. Submit to broker
        try:
            await self._submit_order(order, db_session)
        except Exception as e:
            logger.error(f"Failed to submit order {order.id}: {e}")
            order.status = OrderStatus.REJECTED
            order.error_message = str(e)
            await db_session.commit()
            raise

        return order

    async def _validate_order(
        self,
        request: OrderRequest,
        db_session: AsyncSession
    ):
        """
        Validate order request.

        Args:
            request: Order request
            db_session: Database session

        Raises:
            ValueError: If validation fails
        """
        # Check quantity (must be multiple of 100)
        if request.quantity % 100 != 0:
            raise ValueError("Quantity must be multiple of 100 shares")

        # Check minimum quantity
        if request.quantity < 100:
            raise ValueError("Minimum quantity is 100 shares")

        # Check maximum quantity (prevent fat-finger errors)
        if request.quantity > 1000000:
            raise ValueError("Quantity exceeds maximum (1,000,000 shares)")

        # Check price (if limit order)
        if request.order_type == "limit" and request.price:
            if request.price <= 0:
                raise ValueError("Price must be positive")

            # Check price is reasonable (within 20% of last close)
            # This would require fetching last close price
            # Simplified here

        # Check trading hours (simplified)
        # Real implementation would check market calendar
        now = datetime.now()
        if now.hour < 9 or now.hour >= 15:
            logger.warning(f"Order created outside trading hours: {now}")

    async def _submit_order(
        self,
        order: Order,
        db_session: AsyncSession
    ):
        """
        Submit order to broker.

        Args:
            order: Order to submit
            db_session: Database session
        """
        if not self.broker_interface:
            # Simulation mode - auto-fill order
            logger.info(f"Simulation mode: Auto-filling order {order.id}")
            await self._simulate_order_fill(order, db_session)
            return

        # Real broker submission
        try:
            broker_order_id = await self.broker_interface.submit_order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=order.price,
                order_type=order.order_type
            )

            order.broker_order_id = broker_order_id
            order.status = OrderStatus.SUBMITTED
            order.submitted_at = datetime.utcnow()

            await db_session.commit()

            # Track order
            self.active_orders[order.id] = order

            logger.info(f"Submitted order {order.id} to broker: {broker_order_id}")

        except Exception as e:
            logger.exception(f"Broker submission failed: {e}")
            raise

    async def _simulate_order_fill(
        self,
        order: Order,
        db_session: AsyncSession
    ):
        """
        Simulate order fill (for testing/simulation mode).

        Args:
            order: Order to simulate
            db_session: Database session
        """
        # Simulate immediate fill at order price
        fill_price = order.price or Decimal('10.00')  # Default price for market orders

        # Calculate commission
        commission = calculate_commission(
            fill_price,
            order.quantity,
            order.board,
            is_sell=(order.side == OrderSide.SELL)
        )

        # Update order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_filled_price = fill_price
        order.commission = commission
        order.filled_at = datetime.utcnow()
        order.broker_order_id = f"SIM_{order.id}_{int(datetime.utcnow().timestamp())}"

        await db_session.commit()

        # Update position
        await self._update_position(order, db_session)

        logger.info(
            f"Simulated fill: Order {order.id} filled at {fill_price}, "
            f"commission={commission}"
        )

    async def _update_position(
        self,
        order: Order,
        db_session: AsyncSession
    ):
        """
        Update position after order fill.

        Args:
            order: Filled order
            db_session: Database session
        """
        # Get existing position
        stmt = select(Position).where(Position.symbol == order.symbol)
        result = await db_session.execute(stmt)
        position = result.scalar_one_or_none()

        if order.side == OrderSide.BUY:
            # Buy order - add to position
            if position:
                # Update existing position
                total_cost = (position.avg_cost * position.quantity +
                             order.avg_filled_price * order.filled_quantity)
                total_quantity = position.quantity + order.filled_quantity

                position.avg_cost = total_cost / total_quantity
                position.quantity = total_quantity
                position.last_order_id = order.id
                position.updated_at = datetime.utcnow()

            else:
                # Create new position
                position = Position(
                    symbol=order.symbol,
                    quantity=order.filled_quantity,
                    avg_cost=order.avg_filled_price,
                    board=order.board,
                    entry_date=datetime.utcnow(),
                    last_order_id=order.id,
                    strategy_name=order.strategy_name
                )
                db_session.add(position)

            logger.info(
                f"Updated position {order.symbol}: "
                f"qty={position.quantity}, avg_cost={position.avg_cost}"
            )

        else:  # SELL order
            if not position:
                logger.error(f"Sell order for non-existent position: {order.symbol}")
                return

            # Reduce or close position
            if order.filled_quantity >= position.quantity:
                # Close position entirely
                realized_pnl = (
                    (order.avg_filled_price - position.avg_cost) * position.quantity
                    - order.commission
                )
                position.realized_pnl += realized_pnl

                logger.info(
                    f"Closed position {order.symbol}: "
                    f"realized_pnl={realized_pnl}"
                )

                await db_session.delete(position)

            else:
                # Partial close
                realized_pnl = (
                    (order.avg_filled_price - position.avg_cost) * order.filled_quantity
                    - order.commission
                )
                position.realized_pnl += realized_pnl
                position.quantity -= order.filled_quantity
                position.last_order_id = order.id
                position.updated_at = datetime.utcnow()

                logger.info(
                    f"Reduced position {order.symbol}: "
                    f"qty={position.quantity}, realized_pnl={realized_pnl}"
                )

        await db_session.commit()

    async def cancel_order(
        self,
        order_id: int,
        db_session: AsyncSession
    ) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID
            db_session: Database session

        Returns:
            True if cancelled successfully

        Raises:
            ValueError: If order cannot be cancelled
        """
        # Get order
        stmt = select(Order).where(Order.id == order_id)
        result = await db_session.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Check if cancellable
        if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
            raise ValueError(
                f"Cannot cancel order with status {order.status.value}"
            )

        # Cancel with broker
        if self.broker_interface and order.broker_order_id:
            try:
                await self.broker_interface.cancel_order(order.broker_order_id)
            except Exception as e:
                logger.error(f"Broker cancellation failed: {e}")
                raise

        # Update order status
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.utcnow()

        await db_session.commit()

        # Remove from tracking
        if order_id in self.active_orders:
            del self.active_orders[order_id]

        logger.info(f"Cancelled order {order_id}")

        return True

    async def get_order_status(
        self,
        order_id: int,
        db_session: AsyncSession
    ) -> Optional[Order]:
        """
        Get order status.

        Args:
            order_id: Order ID
            db_session: Database session

        Returns:
            Order object or None
        """
        stmt = select(Order).where(Order.id == order_id)
        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def monitor_orders(self, db_session: AsyncSession):
        """
        Monitor active orders and update statuses.

        This would be called periodically to sync with broker.

        Args:
            db_session: Database session
        """
        if not self.active_orders:
            return

        logger.debug(f"Monitoring {len(self.active_orders)} active orders")

        for order_id, order in list(self.active_orders.items()):
            try:
                if self.broker_interface:
                    # Query broker for status
                    broker_status = await self.broker_interface.get_order_status(
                        order.broker_order_id
                    )

                    # Update order if status changed
                    if broker_status['status'] != order.status.value:
                        await self._update_order_from_broker(
                            order,
                            broker_status,
                            db_session
                        )

            except Exception as e:
                logger.error(f"Error monitoring order {order_id}: {e}")

    async def _update_order_from_broker(
        self,
        order: Order,
        broker_status: dict,
        db_session: AsyncSession
    ):
        """Update order from broker status."""
        # Update order fields based on broker response
        # This is broker-specific logic

        await db_session.commit()
