"""
WebSocket endpoint for real-time updates.
"""

import asyncio
import json
from typing import Set
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger


router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """
        Accept new WebSocket connection.

        Args:
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection.

        Args:
            websocket: WebSocket connection
        """
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to specific client.

        Args:
            message: Message data
            websocket: WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients.

        Args:
            message: Message data
        """
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/market")
async def websocket_market_data(websocket: WebSocket):
    """
    WebSocket endpoint for real-time market data.

    Args:
        websocket: WebSocket connection
    """
    await manager.connect(websocket)

    try:
        # Send welcome message
        await manager.send_personal_message({
            'type': 'connection',
            'message': 'Connected to market data stream',
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)

        # Keep connection alive and handle incoming messages
        while True:
            # Receive client messages
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle subscription requests
            if message.get('action') == 'subscribe':
                symbols = message.get('symbols', [])
                await manager.send_personal_message({
                    'type': 'subscription',
                    'subscribed_symbols': symbols,
                    'timestamp': datetime.utcnow().isoformat()
                }, websocket)

            elif message.get('action') == 'unsubscribe':
                symbols = message.get('symbols', [])
                await manager.send_personal_message({
                    'type': 'unsubscription',
                    'unsubscribed_symbols': symbols,
                    'timestamp': datetime.utcnow().isoformat()
                }, websocket)

            # Simulate market data updates (in production, this would be real data)
            # await manager.send_personal_message({
            #     'type': 'market_data',
            #     'data': {...}
            # }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from market data stream")

    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/orders")
async def websocket_orders(websocket: WebSocket):
    """
    WebSocket endpoint for order status updates.

    Args:
        websocket: WebSocket connection
    """
    await manager.connect(websocket)

    try:
        await manager.send_personal_message({
            'type': 'connection',
            'message': 'Connected to order updates stream',
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)

        while True:
            data = await websocket.receive_text()
            # Handle incoming messages

            # In production, send real order updates
            # await manager.send_personal_message({
            #     'type': 'order_update',
            #     'order_id': ...,
            #     'status': ...,
            #     'timestamp': ...
            # }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/portfolio")
async def websocket_portfolio(websocket: WebSocket):
    """
    WebSocket endpoint for portfolio updates.

    Args:
        websocket: WebSocket connection
    """
    await manager.connect(websocket)

    try:
        await manager.send_personal_message({
            'type': 'connection',
            'message': 'Connected to portfolio updates stream',
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)

        while True:
            data = await websocket.receive_text()

            # In production, send real portfolio updates
            # await manager.send_personal_message({
            #     'type': 'portfolio_update',
            #     'total_value': ...,
            #     'positions': ...,
            #     'timestamp': ...
            # }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/agents")
async def websocket_agents(websocket: WebSocket):
    """
    WebSocket endpoint for agent analysis updates.

    Args:
        websocket: WebSocket connection
    """
    await manager.connect(websocket)

    try:
        await manager.send_personal_message({
            'type': 'connection',
            'message': 'Connected to agent updates stream',
            'timestamp': datetime.utcnow().isoformat()
        }, websocket)

        while True:
            data = await websocket.receive_text()

            # In production, send real agent analysis results
            # await manager.send_personal_message({
            #     'type': 'agent_analysis',
            #     'agent': ...,
            #     'symbol': ...,
            #     'result': ...,
            #     'timestamp': ...
            # }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Utility function to broadcast updates (can be called from other modules)
async def broadcast_market_update(data: dict):
    """Broadcast market data update to all clients."""
    await manager.broadcast({
        'type': 'market_update',
        'data': data,
        'timestamp': datetime.utcnow().isoformat()
    })


async def broadcast_order_update(order_id: int, status: str, data: dict):
    """Broadcast order update to all clients."""
    await manager.broadcast({
        'type': 'order_update',
        'order_id': order_id,
        'status': status,
        'data': data,
        'timestamp': datetime.utcnow().isoformat()
    })
