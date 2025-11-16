"""
异步任务管理器

支持并发执行AI分析任务，每个任务独立运行互不干扰
"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, Optional, Any, Callable, TYPE_CHECKING
from enum import Enum
import logging
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from api.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class Task:
    """任务数据结构"""
    task_id: str
    task_type: str  # 任务类型：analyze, backtest等
    symbol: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0  # 进度百分比 0-100
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    progress_messages: list = field(default_factory=list)  # 进度消息列表

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "symbol": self.symbol,
            "status": self.status.value,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
            "progress_messages": self.progress_messages
        }


class TaskManager:
    """
    任务管理器 - 单例模式

    管理所有异步分析任务，支持：
    1. 创建和执行任务
    2. 查询任务状态
    3. 取消任务
    4. 清理过期任务
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.tasks: Dict[str, Task] = {}  # task_id -> Task
        self.running_tasks: Dict[str, asyncio.Task] = {}  # task_id -> asyncio.Task
        self.max_concurrent_tasks = 10  # 最大并发任务数
        self.task_ttl = 3600  # 任务结果保留时间（秒），默认1小时
        self.ws_manager: Optional['ConnectionManager'] = None  # WebSocket管理器（延迟注入）
        self._initialized = True

        logger.info("[TaskManager] Initialized")

    def set_ws_manager(self, ws_manager: 'ConnectionManager'):
        """
        设置WebSocket管理器（依赖注入）

        Args:
            ws_manager: WebSocket连接管理器
        """
        self.ws_manager = ws_manager
        logger.info("[TaskManager] WebSocket manager injected")

    def create_task(
        self,
        task_type: str,
        symbol: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        创建新任务

        Args:
            task_type: 任务类型
            symbol: 股票代码
            metadata: 任务元数据

        Returns:
            task_id: 任务ID
        """
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            task_type=task_type,
            symbol=symbol,
            metadata=metadata or {}
        )
        self.tasks[task_id] = task

        logger.info(f"[TaskManager] Created task {task_id} for {symbol} ({task_type})")
        return task_id

    async def execute_task(
        self,
        task_id: str,
        func: Callable,
        *args,
        **kwargs
    ):
        """
        执行任务

        Args:
            task_id: 任务ID
            func: 要执行的函数
            *args, **kwargs: 函数参数
        """
        if task_id not in self.tasks:
            logger.error(f"[TaskManager] Task {task_id} not found")
            return

        task = self.tasks[task_id]

        # 检查并发限制
        if len(self.running_tasks) >= self.max_concurrent_tasks:
            logger.warning(f"[TaskManager] Max concurrent tasks reached, queuing task {task_id}")
            # 可以实现队列机制，这里简单等待
            await asyncio.sleep(1)

        try:
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            logger.info(f"[TaskManager] Starting task {task_id}")

            # 如果是async函数，直接await；否则在executor中运行
            if asyncio.iscoroutinefunction(func):
                result = await func(task, *args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, task, *args, **kwargs)

            # 任务完成
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            task.progress = 100

            logger.info(f"[TaskManager] Task {task_id} completed successfully")

            # 通过WebSocket推送完成消息
            if self.ws_manager:
                asyncio.create_task(
                    self.ws_manager.send_task_complete(task_id, result=result)
                )

        except asyncio.CancelledError:
            # 任务被取消
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            logger.info(f"[TaskManager] Task {task_id} cancelled")

            # 通过WebSocket推送取消消息
            if self.ws_manager:
                asyncio.create_task(
                    self.ws_manager.send_task_complete(task_id, error="Task cancelled")
                )

        except Exception as e:
            # 任务失败
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(e)
            logger.error(f"[TaskManager] Task {task_id} failed: {e}", exc_info=True)

            # 通过WebSocket推送错误消息
            if self.ws_manager:
                asyncio.create_task(
                    self.ws_manager.send_task_complete(task_id, error=str(e))
                )

        finally:
            # 从运行列表中移除
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

    def run_task_in_background(
        self,
        task_id: str,
        func: Callable,
        *args,
        **kwargs
    ):
        """
        在后台运行任务

        Args:
            task_id: 任务ID
            func: 要执行的函数
            *args, **kwargs: 函数参数
        """
        asyncio_task = asyncio.create_task(
            self.execute_task(task_id, func, *args, **kwargs)
        )
        self.running_tasks[task_id] = asyncio_task

        logger.info(f"[TaskManager] Task {task_id} scheduled in background")

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务

        Args:
            task_id: 任务ID

        Returns:
            Task对象，如果不存在返回None
        """
        return self.tasks.get(task_id)

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态字典
        """
        task = self.get_task(task_id)
        if task:
            return task.to_dict()
        return None

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        if task_id in self.running_tasks:
            asyncio_task = self.running_tasks[task_id]
            asyncio_task.cancel()
            logger.info(f"[TaskManager] Cancelled task {task_id}")
            return True

        task = self.get_task(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            logger.info(f"[TaskManager] Cancelled pending task {task_id}")
            return True

        return False

    def update_progress(
        self,
        task_id: str,
        progress: int,
        message: Optional[str] = None
    ):
        """
        更新任务进度

        Args:
            task_id: 任务ID
            progress: 进度百分比 (0-100)
            message: 进度消息
        """
        task = self.get_task(task_id)
        if task:
            task.progress = min(max(progress, 0), 100)
            if message:
                task.progress_messages.append({
                    "progress": progress,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
            logger.debug(f"[TaskManager] Task {task_id} progress: {progress}% - {message}")

            # 通过WebSocket推送进度
            if self.ws_manager:
                asyncio.create_task(
                    self.ws_manager.send_task_progress(task_id, progress, message or "")
                )

    def cleanup_old_tasks(self, ttl: Optional[int] = None):
        """
        清理过期任务

        Args:
            ttl: 保留时间（秒），默认使用self.task_ttl
        """
        ttl = ttl or self.task_ttl
        now = datetime.now()
        expired_tasks = []

        for task_id, task in self.tasks.items():
            # 只清理已完成/失败/取消的任务
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                if task.completed_at:
                    age = (now - task.completed_at).total_seconds()
                    if age > ttl:
                        expired_tasks.append(task_id)

        for task_id in expired_tasks:
            del self.tasks[task_id]
            logger.info(f"[TaskManager] Cleaned up expired task {task_id}")

        if expired_tasks:
            logger.info(f"[TaskManager] Cleaned up {len(expired_tasks)} expired tasks")

    def get_stats(self) -> dict:
        """
        获取任务统计信息

        Returns:
            统计信息字典
        """
        stats = {
            "total_tasks": len(self.tasks),
            "running_tasks": len(self.running_tasks),
            "pending_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
            "completed_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
            "cancelled_tasks": sum(1 for t in self.tasks.values() if t.status == TaskStatus.CANCELLED),
        }
        return stats

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """
        列出任务

        Args:
            status: 过滤状态
            symbol: 过滤股票代码
            limit: 返回数量限制

        Returns:
            任务列表
        """
        tasks = list(self.tasks.values())

        # 过滤
        if status:
            tasks = [t for t in tasks if t.status == status]
        if symbol:
            tasks = [t for t in tasks if t.symbol == symbol]

        # 按创建时间倒序
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        # 限制数量
        tasks = tasks[:limit]

        return [t.to_dict() for t in tasks]


# 全局单例
task_manager = TaskManager()
