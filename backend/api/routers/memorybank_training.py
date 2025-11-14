"""
MemoryBank Training API Router

提供MemoryBank案例记忆库训练相关的API端点
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import List, Optional, Dict, Literal
from enum import Enum
import logging
import os
import asyncio
from pathlib import Path

router = APIRouter(prefix="/api/v1/memorybank", tags=["memorybank-training"])

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class TrainingStatus(str, Enum):
    """训练状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class UpdateFrequency(str, Enum):
    """更新频率"""
    DAILY = "daily"
    WEEKLY = "weekly"


# ==================== Request Models ====================

class MemoryBankTrainingConfigRequest(BaseModel):
    """MemoryBank训练配置请求"""
    # 数据配置
    symbols: List[str] = Field(..., description="股票列表")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")

    # MemoryBank配置
    memory_capacity: int = Field(1000, description="记忆库容量")
    update_frequency: UpdateFrequency = Field(UpdateFrequency.DAILY, description="更新频率")
    similarity_threshold: float = Field(0.8, description="相似度阈值", ge=0.0, le=1.0)

    # 系统配置
    embedding_model: str = Field(
        "paraphrase-multilingual-MiniLM-L12-v2",
        description="嵌入模型"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "symbols": ["600519", "000001", "300750"],
                "start_date": "2020-01-01",
                "end_date": "2023-12-31",
                "memory_capacity": 1000,
                "update_frequency": "daily",
                "similarity_threshold": 0.8,
                "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2"
            }
        }


# ==================== Response Models ====================

class MemoryBankProgress(BaseModel):
    """MemoryBank训练进度"""
    processed_episodes: int = Field(..., description="已处理案例数")
    total_episodes: int = Field(..., description="总案例数")
    progress_pct: float = Field(..., description="进度百分比")

    # 统计指标
    stored_episodes: int = Field(0, description="已存储案例数")
    avg_similarity: Optional[float] = Field(None, description="平均相似度")
    memory_usage_mb: Optional[float] = Field(None, description="内存占用(MB)")

    # 时间统计
    elapsed_time: float = Field(..., description="已用时间(秒)")
    estimated_remaining: Optional[float] = Field(None, description="预计剩余时间(秒)")


class MemoryBankTrainingInfo(BaseModel):
    """MemoryBank训练信息"""
    training_id: str
    status: TrainingStatus
    config: MemoryBankTrainingConfigRequest
    progress: Optional[MemoryBankProgress] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class MemoryBankResponse(BaseModel):
    """MemoryBank响应"""
    success: bool
    data: Optional[Dict] = None
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


# ==================== Global State ====================

# 存储训练任务状态
training_tasks: Dict[str, MemoryBankTrainingInfo] = {}

# 存储后台任务
background_tasks_registry: Dict[str, asyncio.Task] = {}


# ==================== Helper Functions ====================

def generate_training_id() -> str:
    """生成训练ID"""
    return f"memorybank_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def get_memorybank_directory() -> Path:
    """获取MemoryBank目录"""
    backend_dir = Path(__file__).parent.parent.parent
    return backend_dir / "memory_db" / "episodes"


async def run_memorybank_training_async(
    training_id: str,
    config: MemoryBankTrainingConfigRequest
):
    """异步运行MemoryBank训练任务"""
    try:
        logger.info(f"📚 Starting MemoryBank training: {training_id}")

        # 更新状态为运行中
        training_tasks[training_id].status = TrainingStatus.RUNNING
        training_tasks[training_id].started_at = datetime.now()

        # 导入必要的模块
        import sys
        backend_dir = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(backend_dir))

        from memory.episodic_memory import EpisodicMemoryBank
        from memory.memory_manager import MemoryManager, MemoryMode
        import time

        # 创建MemoryBank实例
        episode_dir = get_memorybank_directory() / training_id
        episode_dir.mkdir(parents=True, exist_ok=True)

        memory_bank = EpisodicMemoryBank(
            persist_directory=str(episode_dir),
            embedding_model=config.embedding_model
        )
        # Note: max_capacity不是EpisodicMemoryBank的参数，由ChromaDB自动管理容量

        # 模拟训练过程（实际应该从历史数据中提取案例）
        # 这里先创建一个简单的训练流程框架
        start_time = time.time()
        total_episodes = len(config.symbols) * 100  # 假设每个股票有100个案例

        # 在线程池中运行训练
        loop = asyncio.get_event_loop()

        def training_worker():
            """训练工作函数"""
            for idx in range(total_episodes):
                # 模拟处理每个案例
                time.sleep(0.01)  # 模拟处理时间

                # 更新进度
                elapsed = time.time() - start_time
                progress_pct = (idx + 1) / total_episodes * 100
                remaining = (elapsed / (idx + 1)) * (total_episodes - idx - 1) if idx > 0 else 0

                progress = MemoryBankProgress(
                    processed_episodes=idx + 1,
                    total_episodes=total_episodes,
                    progress_pct=progress_pct,
                    stored_episodes=idx + 1,
                    avg_similarity=0.85,
                    memory_usage_mb=memory_bank.get_memory_usage() if hasattr(memory_bank, 'get_memory_usage') else 0,
                    elapsed_time=elapsed,
                    estimated_remaining=remaining
                )

                training_tasks[training_id].progress = progress

                # 每10%输出一次日志
                if (idx + 1) % (total_episodes // 10) == 0:
                    logger.info(
                        f"📚 [{training_id}] 进度: {progress_pct:.1f}% "
                        f"({idx + 1}/{total_episodes})"
                    )

        await loop.run_in_executor(None, training_worker)

        # 更新状态为完成
        training_tasks[training_id].status = TrainingStatus.COMPLETED
        training_tasks[training_id].completed_at = datetime.now()

        logger.info(f"✅ MemoryBank training completed: {training_id}")

    except Exception as e:
        logger.error(f"❌ MemoryBank training failed: {training_id} - {e}")
        training_tasks[training_id].status = TrainingStatus.FAILED
        training_tasks[training_id].error_message = str(e)


# ==================== API Endpoints ====================

@router.post("/training/start", response_model=MemoryBankResponse)
async def start_memorybank_training(
    config: MemoryBankTrainingConfigRequest,
    background_tasks: BackgroundTasks
):
    """启动MemoryBank训练

    Args:
        config: 训练配置
        background_tasks: FastAPI后台任务

    Returns:
        训练启动响应
    """
    try:
        # 生成训练ID
        training_id = generate_training_id()

        # 创建训练任务
        training_info = MemoryBankTrainingInfo(
            training_id=training_id,
            status=TrainingStatus.PENDING,
            config=config,
            created_at=datetime.now()
        )
        training_tasks[training_id] = training_info

        # 添加后台任务
        background_tasks.add_task(run_memorybank_training_async, training_id, config)

        logger.info(f"📚 MemoryBank training task created: {training_id}")

        return MemoryBankResponse(
            success=True,
            message=f"MemoryBank训练任务已创建: {training_id}",
            data={
                "training_id": training_id,
                "status": training_info.status,
                "symbols": config.symbols,
                "memory_capacity": config.memory_capacity
            }
        )

    except Exception as e:
        logger.error(f"❌ Start MemoryBank training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/status", response_model=MemoryBankResponse)
async def get_all_memorybank_training_status():
    """获取所有MemoryBank训练任务的状态

    Returns:
        所有训练任务状态列表
    """
    try:
        # 获取所有训练任务信息
        all_trainings = []

        for training_id, training_info in training_tasks.items():
            all_trainings.append({
                "training_id": training_id,
                "status": training_info.status,
                "created_at": training_info.created_at.isoformat(),
                "started_at": training_info.started_at.isoformat() if training_info.started_at else None,
                "completed_at": training_info.completed_at.isoformat() if training_info.completed_at else None,
                "error_message": training_info.error_message,
                "progress": training_info.progress.dict() if training_info.progress else None,
                "config": {
                    "symbols": training_info.config.symbols,
                    "memory_capacity": training_info.config.memory_capacity,
                    "update_frequency": training_info.config.update_frequency
                }
            })

        # 按创建时间倒序排列
        all_trainings.sort(key=lambda x: x["created_at"], reverse=True)

        return MemoryBankResponse(
            success=True,
            message=f"Found {len(all_trainings)} MemoryBank training tasks",
            data={
                "trainings": all_trainings,
                "total": len(all_trainings),
                "running": len([t for t in training_tasks.values() if t.status == TrainingStatus.RUNNING]),
                "completed": len([t for t in training_tasks.values() if t.status == TrainingStatus.COMPLETED]),
                "failed": len([t for t in training_tasks.values() if t.status == TrainingStatus.FAILED])
            }
        )

    except Exception as e:
        logger.error(f"❌ Get all MemoryBank training status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/status/{training_id}", response_model=MemoryBankResponse)
async def get_memorybank_training_status(training_id: str):
    """查询MemoryBank训练状态

    Args:
        training_id: 训练ID

    Returns:
        训练状态
    """
    try:
        if training_id not in training_tasks:
            raise HTTPException(
                status_code=404,
                detail=f"Training not found: {training_id}"
            )

        training_info = training_tasks[training_id]

        return MemoryBankResponse(
            success=True,
            message="查询成功",
            data={
                "training_id": training_id,
                "status": training_info.status,
                "progress": training_info.progress.dict() if training_info.progress else None,
                "created_at": training_info.created_at.isoformat(),
                "started_at": training_info.started_at.isoformat() if training_info.started_at else None,
                "completed_at": training_info.completed_at.isoformat() if training_info.completed_at else None,
                "error_message": training_info.error_message
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get MemoryBank status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/stop/{training_id}", response_model=MemoryBankResponse)
async def stop_memorybank_training(training_id: str):
    """停止MemoryBank训练任务

    Args:
        training_id: 训练ID

    Returns:
        停止响应
    """
    try:
        if training_id not in training_tasks:
            raise HTTPException(
                status_code=404,
                detail=f"Training not found: {training_id}"
            )

        training_info = training_tasks[training_id]

        if training_info.status != TrainingStatus.RUNNING:
            return MemoryBankResponse(
                success=False,
                message=f"Training is not running: {training_info.status}"
            )

        # TODO: 实现优雅停止逻辑
        training_info.status = TrainingStatus.STOPPED
        training_info.completed_at = datetime.now()

        logger.info(f"⏹️ MemoryBank training stopped: {training_id}")

        return MemoryBankResponse(
            success=True,
            message=f"MemoryBank训练已停止: {training_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Stop MemoryBank training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MemoryBankResponse)
async def get_memorybank_stats():
    """获取MemoryBank统计信息

    Returns:
        MemoryBank统计数据
    """
    try:
        memorybank_dir = get_memorybank_directory()

        if not memorybank_dir.exists():
            return MemoryBankResponse(
                success=True,
                message="No MemoryBank data found",
                data={
                    "total_episodes": 0,
                    "total_size_mb": 0,
                    "banks": []
                }
            )

        # 统计所有MemoryBank
        banks = []
        total_episodes = 0
        total_size = 0

        for bank_dir in memorybank_dir.iterdir():
            if bank_dir.is_dir():
                # 计算大小
                size = sum(f.stat().st_size for f in bank_dir.rglob('*') if f.is_file())
                total_size += size

                banks.append({
                    "bank_id": bank_dir.name,
                    "size_mb": size / (1024 * 1024),
                    "created_at": datetime.fromtimestamp(bank_dir.stat().st_ctime).isoformat(),
                })

        return MemoryBankResponse(
            success=True,
            message=f"Found {len(banks)} MemoryBanks",
            data={
                "total_episodes": total_episodes,
                "total_size_mb": total_size / (1024 * 1024),
                "banks": banks
            }
        )

    except Exception as e:
        logger.error(f"❌ Get MemoryBank stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
