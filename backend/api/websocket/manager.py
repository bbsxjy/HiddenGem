"""
WebSocket Connection Manager

管理WebSocket连接和消息推送
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 所有活跃连接
        self.active_connections: Set[WebSocket] = set()

        # 股票订阅映射 {symbol: Set[WebSocket]}
        self.subscriptions: Dict[str, Set[WebSocket]] = {}

        # 任务订阅映射 {task_id: Set[WebSocket]}
        self.task_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """
        接受新连接

        Args:
            websocket: WebSocket连接
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"[WS] New connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        断开连接

        Args:
            websocket: WebSocket连接
        """
        # 从所有订阅中移除
        for symbol, subscribers in self.subscriptions.items():
            subscribers.discard(websocket)

        # 从任务订阅中移除
        for task_id, subscribers in self.task_subscriptions.items():
            subscribers.discard(websocket)

        # 移除连接
        self.active_connections.discard(websocket)
        logger.info(f"[WS] Connection closed. Total: {len(self.active_connections)}")

    async def subscribe(self, websocket: WebSocket, symbol: str):
        """
        订阅股票

        Args:
            websocket: WebSocket连接
            symbol: 股票代码
        """
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = set()

        self.subscriptions[symbol].add(websocket)
        logger.info(f"[WS] Client subscribed to {symbol}. Subscribers: {len(self.subscriptions[symbol])}")

        # 发送订阅确认
        await self.send_personal_message({
            "type": "subscribed",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }, websocket)

    async def unsubscribe(self, websocket: WebSocket, symbol: str):
        """
        取消订阅

        Args:
            websocket: WebSocket连接
            symbol: 股票代码
        """
        if symbol in self.subscriptions:
            self.subscriptions[symbol].discard(websocket)
            logger.info(f"[WS] Client unsubscribed from {symbol}")

            # 发送取消订阅确认
            await self.send_personal_message({
                "type": "unsubscribed",
                "symbol": symbol,
                "timestamp": datetime.now().isoformat()
            }, websocket)

    async def subscribe_task(self, websocket: WebSocket, task_id: str):
        """
        订阅任务进度

        Args:
            websocket: WebSocket连接
            task_id: 任务ID
        """
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()

        self.task_subscriptions[task_id].add(websocket)
        logger.info(f"[WS] Client subscribed to task {task_id}. Subscribers: {len(self.task_subscriptions[task_id])}")

        # 发送订阅确认
        await self.send_personal_message({
            "type": "task_subscribed",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }, websocket)

    async def unsubscribe_task(self, websocket: WebSocket, task_id: str):
        """
        取消订阅任务

        Args:
            websocket: WebSocket连接
            task_id: 任务ID
        """
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(websocket)
            logger.info(f"[WS] Client unsubscribed from task {task_id}")

            # 发送取消订阅确认
            await self.send_personal_message({
                "type": "task_unsubscribed",
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            }, websocket)

    async def send_task_progress(self, task_id: str, progress: int, message: str = "", data: dict = None):
        """
        发送任务进度更新给订阅者

        Args:
            task_id: 任务ID
            progress: 进度百分比 (0-100)
            message: 进度消息
            data: 额外数据
        """
        if task_id not in self.task_subscriptions:
            return

        progress_message = {
            "type": "task_progress",
            "task_id": task_id,
            "progress": progress,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }

        disconnected = []
        for connection in self.task_subscriptions[task_id]:
            try:
                await connection.send_text(json.dumps(progress_message))
            except Exception:
                disconnected.append(connection)

        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

        logger.debug(f"[WS] Sent task progress for {task_id}: {progress}% - {message}")

    async def send_task_complete(self, task_id: str, result: dict = None, error: str = None):
        """
        发送任务完成消息给订阅者

        Args:
            task_id: 任务ID
            result: 任务结果
            error: 错误信息（如果失败）
        """
        if task_id not in self.task_subscriptions:
            return

        complete_message = {
            "type": "task_complete" if not error else "task_error",
            "task_id": task_id,
            "result": result,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }

        disconnected = []
        for connection in self.task_subscriptions[task_id]:
            try:
                await connection.send_text(json.dumps(complete_message))
            except Exception:
                disconnected.append(connection)

        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

        # 清理任务订阅（任务完成后不再需要）
        if task_id in self.task_subscriptions:
            del self.task_subscriptions[task_id]

        logger.info(f"[WS] Sent task completion for {task_id}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        发送个人消息

        Args:
            message: 消息字典
            websocket: 目标连接
        """
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"[WS] Failed to send message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """
        广播消息给所有连接

        Args:
            message: 消息字典
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                disconnected.append(connection)

        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

    async def send_to_symbol_subscribers(self, symbol: str, message: dict):
        """
        发送消息给某个股票的订阅者

        Args:
            symbol: 股票代码
            message: 消息字典
        """
        if symbol not in self.subscriptions:
            return

        disconnected = []
        for connection in self.subscriptions[symbol]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                disconnected.append(connection)

        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "total_connections": len(self.active_connections),
            "total_symbol_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
            "total_task_subscriptions": sum(len(subs) for subs in self.task_subscriptions.values()),
            "subscribed_symbols": list(self.subscriptions.keys()),
            "subscribed_tasks": list(self.task_subscriptions.keys()),
            "timestamp": datetime.now().isoformat()
        }
