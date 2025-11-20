#!/usr/bin/env python3
"""
任务监控模块 - 用于长时间运行任务的状态持久化
支持断点恢复和进度监控
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from threading import Lock

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('task_monitor')


@dataclass
class TaskCheckpoint:
    """任务检查点"""
    task_id: str
    task_type: str  # RL_TRAINING, TIME_TRAVEL, AUTO_TRADING等
    status: str  # RUNNING, PAUSED, COMPLETED, FAILED
    progress: float  # 0.0 - 1.0
    current_step: str
    total_steps: Optional[int] = None
    completed_steps: int = 0
    start_time: str = None
    last_update_time: str = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now().isoformat()
        if self.last_update_time is None:
            self.last_update_time = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}


class TaskMonitor:
    """任务监控器 - 单例模式"""

    _instance = None
    _lock = Lock()

    def __new__(cls, checkpoint_dir: str = "./results/checkpoints"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, checkpoint_dir: str = "./results/checkpoints"):
        if not self._initialized:
            self.checkpoint_dir = Path(checkpoint_dir)
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            self._tasks: Dict[str, TaskCheckpoint] = {}
            self._load_checkpoints()
            self._initialized = True
            logger.info(f"任务监控器初始化完成: {self.checkpoint_dir}")

    def _load_checkpoints(self):
        """加载所有现有的检查点"""
        try:
            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        checkpoint = TaskCheckpoint(**data)
                        self._tasks[checkpoint.task_id] = checkpoint
                        logger.debug(f"加载检查点: {checkpoint.task_id}")
                except Exception as e:
                    logger.error(f"加载检查点失败 {checkpoint_file}: {e}")
        except Exception as e:
            logger.error(f"加载检查点目录失败: {e}")

    def start_task(
        self,
        task_id: str,
        task_type: str,
        total_steps: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TaskCheckpoint:
        """
        开始一个新任务

        Args:
            task_id: 任务唯一标识符
            task_type: 任务类型
            total_steps: 总步数（可选）
            metadata: 额外元数据

        Returns:
            TaskCheckpoint: 任务检查点
        """
        with self._lock:
            checkpoint = TaskCheckpoint(
                task_id=task_id,
                task_type=task_type,
                status="RUNNING",
                progress=0.0,
                current_step="初始化",
                total_steps=total_steps,
                completed_steps=0,
                metadata=metadata or {}
            )

            self._tasks[task_id] = checkpoint
            self._save_checkpoint(checkpoint)

            logger.info(f"任务开始: {task_id} ({task_type})")
            return checkpoint

    def update_progress(
        self,
        task_id: str,
        current_step: str,
        completed_steps: Optional[int] = None,
        progress: Optional[float] = None,
        metadata_update: Optional[Dict[str, Any]] = None
    ):
        """
        更新任务进度

        Args:
            task_id: 任务ID
            current_step: 当前步骤描述
            completed_steps: 已完成步数
            progress: 进度（0-1），如果为None则根据completed_steps/total_steps自动计算
            metadata_update: 要更新的元数据
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"任务不存在: {task_id}")
                return

            checkpoint = self._tasks[task_id]
            checkpoint.current_step = current_step
            checkpoint.last_update_time = datetime.now().isoformat()

            if completed_steps is not None:
                checkpoint.completed_steps = completed_steps

            # 计算进度
            if progress is not None:
                checkpoint.progress = progress
            elif checkpoint.total_steps and checkpoint.total_steps > 0:
                checkpoint.progress = checkpoint.completed_steps / checkpoint.total_steps

            # 更新元数据
            if metadata_update:
                checkpoint.metadata.update(metadata_update)

            self._save_checkpoint(checkpoint)

            logger.debug(
                f"任务进度更新: {task_id} - {current_step} "
                f"({checkpoint.progress:.1%})"
            )

    def complete_task(self, task_id: str, final_metadata: Optional[Dict[str, Any]] = None):
        """
        标记任务完成

        Args:
            task_id: 任务ID
            final_metadata: 最终元数据
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"任务不存在: {task_id}")
                return

            checkpoint = self._tasks[task_id]
            checkpoint.status = "COMPLETED"
            checkpoint.progress = 1.0
            checkpoint.current_step = "已完成"
            checkpoint.last_update_time = datetime.now().isoformat()

            if final_metadata:
                checkpoint.metadata.update(final_metadata)

            self._save_checkpoint(checkpoint)

            logger.info(f"任务完成: {task_id}")

    def fail_task(self, task_id: str, error: str):
        """
        标记任务失败

        Args:
            task_id: 任务ID
            error: 错误信息
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"任务不存在: {task_id}")
                return

            checkpoint = self._tasks[task_id]
            checkpoint.status = "FAILED"
            checkpoint.error = error
            checkpoint.current_step = "失败"
            checkpoint.last_update_time = datetime.now().isoformat()

            self._save_checkpoint(checkpoint)

            logger.error(f"任务失败: {task_id} - {error}")

    def pause_task(self, task_id: str):
        """暂停任务"""
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"任务不存在: {task_id}")
                return

            checkpoint = self._tasks[task_id]
            checkpoint.status = "PAUSED"
            checkpoint.last_update_time = datetime.now().isoformat()

            self._save_checkpoint(checkpoint)

            logger.info(f"任务暂停: {task_id}")

    def resume_task(self, task_id: str) -> Optional[TaskCheckpoint]:
        """
        恢复任务

        Args:
            task_id: 任务ID

        Returns:
            TaskCheckpoint: 任务检查点，如果不存在返回None
        """
        with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"任务不存在: {task_id}")
                return None

            checkpoint = self._tasks[task_id]
            checkpoint.status = "RUNNING"
            checkpoint.last_update_time = datetime.now().isoformat()

            self._save_checkpoint(checkpoint)

            logger.info(f"任务恢复: {task_id}")
            return checkpoint

    def get_checkpoint(self, task_id: str) -> Optional[TaskCheckpoint]:
        """获取任务检查点"""
        return self._tasks.get(task_id)

    def get_all_checkpoints(self) -> List[TaskCheckpoint]:
        """获取所有任务检查点"""
        return list(self._tasks.values())

    def get_running_tasks(self) -> List[TaskCheckpoint]:
        """获取所有运行中的任务"""
        return [cp for cp in self._tasks.values() if cp.status == "RUNNING"]

    def get_failed_tasks(self) -> List[TaskCheckpoint]:
        """获取所有失败的任务"""
        return [cp for cp in self._tasks.values() if cp.status == "FAILED"]

    def _save_checkpoint(self, checkpoint: TaskCheckpoint):
        """保存检查点到文件"""
        try:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint.task_id}.json"
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(checkpoint), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存检查点失败 {checkpoint.task_id}: {e}")

    def delete_checkpoint(self, task_id: str):
        """删除检查点"""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]

            checkpoint_file = self.checkpoint_dir / f"{task_id}.json"
            if checkpoint_file.exists():
                try:
                    checkpoint_file.unlink()
                    logger.info(f"检查点已删除: {task_id}")
                except Exception as e:
                    logger.error(f"删除检查点失败 {task_id}: {e}")

    def cleanup_old_checkpoints(self, days: int = 7):
        """清理旧的检查点"""
        cutoff_time = time.time() - (days * 24 * 3600)

        with self._lock:
            to_delete = []

            for task_id, checkpoint in self._tasks.items():
                if checkpoint.status in ["COMPLETED", "FAILED"]:
                    try:
                        last_update = datetime.fromisoformat(checkpoint.last_update_time)
                        if last_update.timestamp() < cutoff_time:
                            to_delete.append(task_id)
                    except Exception:
                        continue

            for task_id in to_delete:
                self.delete_checkpoint(task_id)

            if to_delete:
                logger.info(f"清理了 {len(to_delete)} 个旧检查点")

    def print_status(self):
        """打印所有任务状态"""
        checkpoints = self.get_all_checkpoints()

        if not checkpoints:
            print("没有活跃任务")
            return

        print("=" * 80)
        print("任务监控状态")
        print("=" * 80)

        for cp in checkpoints:
            status_symbol = {
                "RUNNING": "🔄",
                "PAUSED": "⏸️",
                "COMPLETED": "✅",
                "FAILED": "❌"
            }.get(cp.status, "❓")

            print(f"\n{status_symbol} [{cp.task_type}] {cp.task_id}")
            print(f"   状态: {cp.status}")
            print(f"   进度: {cp.progress:.1%}")
            print(f"   当前步骤: {cp.current_step}")

            if cp.total_steps:
                print(f"   步数: {cp.completed_steps}/{cp.total_steps}")

            if cp.error:
                print(f"   错误: {cp.error}")

            print(f"   最后更新: {cp.last_update_time}")

        print("=" * 80)


# 全局单例
_task_monitor = TaskMonitor()


def get_task_monitor() -> TaskMonitor:
    """获取任务监控器实例"""
    return _task_monitor


if __name__ == "__main__":
    # 测试任务监控
    import sys
    import time

    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    monitor = get_task_monitor()

    # 模拟一个训练任务
    task_id = "test_training_20250120"
    monitor.start_task(
        task_id=task_id,
        task_type="RL_TRAINING",
        total_steps=100,
        metadata={"model": "PPO", "env": "TradingEnv"}
    )

    # 模拟进度更新
    for i in range(1, 11):
        time.sleep(0.5)
        monitor.update_progress(
            task_id=task_id,
            current_step=f"训练 Episode {i*10}",
            completed_steps=i*10,
            metadata_update={"current_reward": i * 1.5}
        )

    # 完成任务
    monitor.complete_task(
        task_id=task_id,
        final_metadata={"final_reward": 150.0}
    )

    # 打印状态
    monitor.print_status()
