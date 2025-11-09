"""
Broker Interface.
Provides abstraction for broker API integration.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from enum import Enum

from loguru import logger

from database.models import OrderSide, OrderType, OrderStatus


class BrokerInterface(ABC):
    """
    Abstract broker interface.

    Provides abstraction for different broker implementations.
    In production, would be implemented by specific brokers (VNpy, etc.).
    """

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to broker API.

        Returns:
            True if connected successfully
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from broker API.

        Returns:
            True if disconnected successfully
        """
        pass

    @abstractmethod
    async def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: Optional[Decimal],
        order_type: OrderType
    ) -> str:
        """
        Submit order to broker.

        Args:
            symbol: Stock symbol
            side: Buy or Sell
            quantity: Order quantity
            price: Order price (None for market orders)
            order_type: Order type

        Returns:
            Broker order ID

        Raises:
            Exception: If submission fails
        """
        pass

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """
        Cancel order.

        Args:
            broker_order_id: Broker order ID

        Returns:
            True if cancelled successfully

        Raises:
            Exception: If cancellation fails
        """
        pass

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> Dict:
        """
        Get order status from broker.

        Args:
            broker_order_id: Broker order ID

        Returns:
            Order status information

        Raises:
            Exception: If query fails
        """
        pass

    @abstractmethod
    async def get_account_info(self) -> Dict:
        """
        Get account information.

        Returns:
            Account info (cash, margin, etc.)

        Raises:
            Exception: If query fails
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Dict]:
        """
        Get current positions from broker.

        Returns:
            List of position dictionaries

        Raises:
            Exception: If query fails
        """
        pass


class SimulationBroker(BrokerInterface):
    """
    Simulation broker for testing.

    Simulates broker behavior without real trading.
    All orders are immediately filled at order price.
    """

    def __init__(self):
        """Initialize simulation broker."""
        self.connected = False
        self.orders: Dict[str, Dict] = {}
        self.order_counter = 0

        # Simulation account
        self.cash = Decimal('1000000.00')  # 1M RMB
        self.positions: Dict[str, Dict] = {}

        logger.info("SimulationBroker initialized")

    async def connect(self) -> bool:
        """
        Connect to simulation broker.

        Returns:
            True (always succeeds)
        """
        self.connected = True
        logger.info("SimulationBroker connected")
        return True

    async def disconnect(self) -> bool:
        """
        Disconnect from simulation broker.

        Returns:
            True (always succeeds)
        """
        self.connected = False
        logger.info("SimulationBroker disconnected")
        return True

    async def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: Optional[Decimal],
        order_type: OrderType
    ) -> str:
        """
        Submit order to simulation broker.

        Orders are immediately filled at order price (or simulated market price).

        Args:
            symbol: Stock symbol
            side: Buy or Sell
            quantity: Order quantity
            price: Order price
            order_type: Order type

        Returns:
            Broker order ID
        """
        if not self.connected:
            raise RuntimeError("Broker not connected")

        # Generate broker order ID
        self.order_counter += 1
        broker_order_id = f"SIM_{self.order_counter}_{int(datetime.utcnow().timestamp())}"

        # Determine fill price
        if order_type == OrderType.MARKET or price is None:
            # Simulate market price (in production, would use real market data)
            fill_price = self._get_simulated_market_price(symbol)
        else:
            fill_price = price

        # Create order record
        order = {
            'broker_order_id': broker_order_id,
            'symbol': symbol,
            'side': side.value,
            'quantity': quantity,
            'price': price,
            'order_type': order_type.value,
            'status': 'filled',
            'filled_quantity': quantity,
            'avg_filled_price': fill_price,
            'submitted_at': datetime.utcnow(),
            'filled_at': datetime.utcnow()
        }

        self.orders[broker_order_id] = order

        # Update simulated positions
        self._update_simulated_position(symbol, side, quantity, fill_price)

        logger.info(
            f"SimulationBroker: Order filled {broker_order_id} - "
            f"{symbol} {side.value} {quantity} @ {fill_price}"
        )

        return broker_order_id

    async def cancel_order(self, broker_order_id: str) -> bool:
        """
        Cancel order (simulation).

        In simulation, orders are immediately filled, so cancellation always fails.

        Args:
            broker_order_id: Broker order ID

        Returns:
            False (orders already filled)
        """
        if broker_order_id not in self.orders:
            raise ValueError(f"Order {broker_order_id} not found")

        order = self.orders[broker_order_id]

        if order['status'] == 'filled':
            raise ValueError(f"Cannot cancel filled order {broker_order_id}")

        # In simulation, all orders are immediately filled
        # So this should never happen
        order['status'] = 'cancelled'
        logger.info(f"SimulationBroker: Cancelled order {broker_order_id}")

        return True

    async def get_order_status(self, broker_order_id: str) -> Dict:
        """
        Get order status.

        Args:
            broker_order_id: Broker order ID

        Returns:
            Order status
        """
        if broker_order_id not in self.orders:
            raise ValueError(f"Order {broker_order_id} not found")

        return self.orders[broker_order_id].copy()

    async def get_account_info(self) -> Dict:
        """
        Get account information.

        Returns:
            Account info
        """
        # Calculate total position value
        position_value = sum(
            pos['quantity'] * pos['avg_cost']
            for pos in self.positions.values()
        )

        return {
            'cash': float(self.cash),
            'position_value': float(position_value),
            'total_value': float(self.cash + position_value),
            'margin_used': 0.0,
            'margin_available': float(self.cash)
        }

    async def get_positions(self) -> List[Dict]:
        """
        Get current positions.

        Returns:
            List of positions
        """
        return [
            {
                'symbol': symbol,
                'quantity': pos['quantity'],
                'avg_cost': float(pos['avg_cost']),
                'current_price': float(self._get_simulated_market_price(symbol)),
                'market_value': float(pos['quantity'] * self._get_simulated_market_price(symbol))
            }
            for symbol, pos in self.positions.items()
            if pos['quantity'] > 0
        ]

    def _get_simulated_market_price(self, symbol: str) -> Decimal:
        """
        Get simulated market price.

        In production, would fetch real market data.

        Args:
            symbol: Stock symbol

        Returns:
            Simulated price
        """
        # Simplified - return fixed price based on symbol
        # In production, would use real market data
        base_price = Decimal('10.00')

        # Add some variation based on symbol
        symbol_hash = sum(ord(c) for c in symbol)
        variation = Decimal(str(symbol_hash % 100)) / Decimal('10')

        return base_price + variation

    def _update_simulated_position(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: Decimal
    ):
        """
        Update simulated position.

        Args:
            symbol: Stock symbol
            side: Buy or Sell
            quantity: Order quantity
            price: Fill price
        """
        if symbol not in self.positions:
            self.positions[symbol] = {
                'quantity': 0,
                'avg_cost': Decimal('0')
            }

        position = self.positions[symbol]

        if side == OrderSide.BUY:
            # Buy - add to position
            total_cost = (position['avg_cost'] * position['quantity'] +
                         price * quantity)
            total_quantity = position['quantity'] + quantity

            position['avg_cost'] = total_cost / total_quantity if total_quantity > 0 else Decimal('0')
            position['quantity'] = total_quantity

            # Reduce cash
            order_value = price * quantity
            commission = max(order_value * Decimal('0.0003'), Decimal('5.00'))
            self.cash -= (order_value + commission)

        else:  # SELL
            # Sell - reduce position
            position['quantity'] -= quantity

            # Add cash
            order_value = price * quantity
            commission = max(order_value * Decimal('0.0003'), Decimal('5.00'))
            stamp_duty = order_value * Decimal('0.001')  # A-share stamp duty
            self.cash += (order_value - commission - stamp_duty)

            # Remove position if quantity is 0
            if position['quantity'] <= 0:
                del self.positions[symbol]

        logger.debug(
            f"Updated simulated position: {symbol} "
            f"qty={position.get('quantity', 0)} "
            f"avg_cost={position.get('avg_cost', 0)}"
        )


class VNpyBroker(BrokerInterface):
    """
    VNpy broker interface (placeholder).

    In production, would integrate with VNpy for real broker connectivity.
    """

    def __init__(self, gateway_name: str, settings: Dict):
        """
        Initialize VNpy broker.

        Args:
            gateway_name: VNpy gateway name (e.g., 'CTP', 'MINI')
            settings: Gateway connection settings
        """
        self.gateway_name = gateway_name
        self.settings = settings
        self.connected = False

        logger.info(f"VNpyBroker initialized with gateway: {gateway_name}")

    async def connect(self) -> bool:
        """
        Connect to VNpy gateway.

        Returns:
            True if connected
        """
        # TODO: Implement VNpy connection
        # from vnpy.trader.engine import MainEngine
        # from vnpy.trader.ui import create_qapp
        # self.engine = MainEngine(...)
        # self.engine.add_gateway(...)
        # self.engine.connect(...)

        raise NotImplementedError("VNpy integration not yet implemented")

    async def disconnect(self) -> bool:
        """Disconnect from VNpy gateway."""
        raise NotImplementedError("VNpy integration not yet implemented")

    async def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: Optional[Decimal],
        order_type: OrderType
    ) -> str:
        """Submit order via VNpy."""
        raise NotImplementedError("VNpy integration not yet implemented")

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel order via VNpy."""
        raise NotImplementedError("VNpy integration not yet implemented")

    async def get_order_status(self, broker_order_id: str) -> Dict:
        """Get order status from VNpy."""
        raise NotImplementedError("VNpy integration not yet implemented")

    async def get_account_info(self) -> Dict:
        """Get account info from VNpy."""
        raise NotImplementedError("VNpy integration not yet implemented")

    async def get_positions(self) -> List[Dict]:
        """Get positions from VNpy."""
        raise NotImplementedError("VNpy integration not yet implemented")


def create_broker_interface(mode: str = "simulation", **kwargs) -> BrokerInterface:
    """
    Factory function to create broker interface.

    Args:
        mode: Broker mode ('simulation' or 'vnpy')
        **kwargs: Additional arguments for broker

    Returns:
        Broker interface instance
    """
    if mode == "simulation":
        return SimulationBroker()
    elif mode == "vnpy":
        gateway_name = kwargs.get('gateway_name', 'CTP')
        settings = kwargs.get('settings', {})
        return VNpyBroker(gateway_name, settings)
    else:
        raise ValueError(f"Unknown broker mode: {mode}")
