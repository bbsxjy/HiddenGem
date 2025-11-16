"""
RL Training API Router

提供强化学习模型训练相关的API端点
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

router = APIRouter(prefix="/api/v1/rl", tags=["rl-training"])

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class TrainingStatus(str, Enum):
    """训练状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class StockPool(str, Enum):
    """股票池"""
    HS300 = "hs300"  # 沪深300
    CUSTOM = "custom"  # 自定义


# ==================== Request Models ====================

class TrainingConfigRequest(BaseModel):
    """训练配置请求"""
    # 数据配置
    stock_pool: StockPool = Field(StockPool.HS300, description="股票池")
    custom_symbols: Optional[List[str]] = Field(None, description="自定义股票列表")
    max_stocks: int = Field(50, description="最大股票数量")

    train_start: date = Field(..., description="训练开始日期")
    train_end: date = Field(..., description="训练结束日期")
    val_start: date = Field(..., description="验证开始日期")
    val_end: date = Field(..., description="验证结束日期")

    # 环境配置
    initial_cash: float = Field(100000.0, description="初始资金")
    commission_rate: float = Field(0.00013, description="手续费率")
    stamp_duty: float = Field(0.001, description="印花税")
    enable_t1: bool = Field(True, description="启用T+1限制")

    # 训练超参数
    total_timesteps: int = Field(500000, description="总训练步数")
    learning_rate: float = Field(0.0003, description="学习率")
    n_steps: int = Field(2048, description="每次更新的步数")
    batch_size: int = Field(64, description="批次大小")
    n_epochs: int = Field(5, description="PPO epoch数")
    gamma: float = Field(0.995, description="折扣因子")

    # 系统配置
    use_gpu: bool = Field(False, description="使用GPU加速")
    model_name: Optional[str] = Field(None, description="模型名称")

    class Config:
        json_schema_extra = {
            "example": {
                "stock_pool": "hs300",
                "max_stocks": 50,
                "train_start": "2020-01-01",
                "train_end": "2022-12-31",
                "val_start": "2023-01-01",
                "val_end": "2023-12-31",
                "initial_cash": 100000.0,
                "enable_t1": True,
                "total_timesteps": 500000,
                "use_gpu": True,
                "model_name": "hs300_ppo_v1"
            }
        }


# ==================== Response Models ====================

class TrainingProgress(BaseModel):
    """训练进度"""
    timesteps: int = Field(..., description="当前步数")
    total_timesteps: int = Field(..., description="总步数")
    progress_pct: float = Field(..., description="进度百分比")

    # 训练指标
    ep_rew_mean: Optional[float] = Field(None, description="平均episode奖励")
    ep_len_mean: Optional[float] = Field(None, description="平均episode长度")
    fps: Optional[float] = Field(None, description="训练速度(帧/秒)")

    # 训练loss
    policy_loss: Optional[float] = Field(None, description="策略损失")
    value_loss: Optional[float] = Field(None, description="价值损失")
    explained_variance: Optional[float] = Field(None, description="解释方差")

    # 评估指标
    eval_reward: Optional[float] = Field(None, description="评估奖励")
    best_reward: Optional[float] = Field(None, description="最佳奖励")

    # 时间统计
    elapsed_time: float = Field(..., description="已用时间(秒)")
    estimated_remaining: Optional[float] = Field(None, description="预计剩余时间(秒)")


class TrainingInfo(BaseModel):
    """训练信息"""
    training_id: str
    status: TrainingStatus
    config: TrainingConfigRequest
    progress: Optional[TrainingProgress] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class TrainingResponse(BaseModel):
    """训练响应"""
    success: bool
    data: Optional[Dict] = None
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


class ModelInfo(BaseModel):
    """模型信息"""
    model_id: str
    model_name: str
    model_path: str
    model_type: str  # "best", "final", "checkpoint"

    # 训练信息
    training_id: Optional[str] = None
    total_timesteps: Optional[int] = None

    # 性能指标
    final_reward: Optional[float] = None
    best_reward: Optional[float] = None
    sharpe_ratio: Optional[float] = None

    # 文件信息
    file_size: int
    created_at: datetime
    modified_at: datetime

    # 配置
    config: Optional[Dict] = None


# ==================== Global State ====================

# 存储训练任务状态
training_tasks: Dict[str, TrainingInfo] = {}

# 存储后台任务
background_tasks_registry: Dict[str, asyncio.Task] = {}


# ==================== Helper Functions ====================

def generate_training_id() -> str:
    """生成训练ID"""
    from datetime import datetime
    return f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def get_models_directory() -> Path:
    """获取模型目录"""
    backend_dir = Path(__file__).parent.parent.parent
    return backend_dir / "models" / "production"


async def run_training_async(training_id: str, config: TrainingConfigRequest):
    """异步运行训练任务"""
    try:
        logger.info(f" Starting training: {training_id}")

        # 更新状态为运行中
        training_tasks[training_id].status = TrainingStatus.RUNNING
        training_tasks[training_id].started_at = datetime.now()

        # 导入训练模块
        import sys
        backend_dir = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(backend_dir))

        from scripts.train_rl_production import run_training

        # 构建配置字典
        training_config = {
            'train_start': config.train_start.isoformat(),
            'train_end': config.train_end.isoformat(),
            'val_start': config.val_start.isoformat(),
            'val_end': config.val_end.isoformat(),

            'use_hs300': config.stock_pool == StockPool.HS300,
            'custom_symbols': config.custom_symbols,
            'max_stocks': config.max_stocks,

            'initial_cash': config.initial_cash,
            'commission_rate': config.commission_rate,
            'stamp_duty': config.stamp_duty,
            'enable_t1': config.enable_t1,

            'total_timesteps': config.total_timesteps,
            'learning_rate': config.learning_rate,
            'n_steps': config.n_steps,
            'batch_size': config.batch_size,
            'n_epochs': config.n_epochs,
            'gamma': config.gamma,

            'use_gpu': config.use_gpu,
            'model_name': config.model_name or training_id,
            'model_dir': str(get_models_directory() / training_id),
        }

        # 在线程池中运行训练（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_training, training_config)

        # 更新状态为完成
        training_tasks[training_id].status = TrainingStatus.COMPLETED
        training_tasks[training_id].completed_at = datetime.now()

        logger.info(f" Training completed: {training_id}")

    except Exception as e:
        logger.error(f" Training failed: {training_id} - {e}")
        training_tasks[training_id].status = TrainingStatus.FAILED
        training_tasks[training_id].error_message = str(e)


# ==================== API Endpoints ====================

@router.post("/training/start", response_model=TrainingResponse)
async def start_training(
    config: TrainingConfigRequest,
    background_tasks: BackgroundTasks
):
    """启动RL模型训练

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
        training_info = TrainingInfo(
            training_id=training_id,
            status=TrainingStatus.PENDING,
            config=config,
            created_at=datetime.now()
        )
        training_tasks[training_id] = training_info

        # 添加后台任务
        background_tasks.add_task(run_training_async, training_id, config)

        logger.info(f" Training task created: {training_id}")

        return TrainingResponse(
            success=True,
            message=f"训练任务已创建: {training_id}",
            data={
                "training_id": training_id,
                "status": training_info.status,
                "estimated_time": config.total_timesteps / 300  # 假设300 FPS
            }
        )

    except Exception as e:
        logger.error(f" Start training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/status", response_model=TrainingResponse)
async def get_all_training_status():
    """获取所有训练任务的状态

    Returns:
        所有训练任务状态列表
    """
    try:
        # 获取所有训练任务信息
        all_trainings = []

        for training_id, training_info in training_tasks.items():
            # 尝试读取进度文件
            progress_data = None
            if training_info.status == TrainingStatus.RUNNING:
                try:
                    progress_file = get_models_directory() / training_id / "training_progress.json"
                    if progress_file.exists():
                        import json
                        with open(progress_file, 'r') as f:
                            progress_data = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to read progress file for {training_id}: {e}")

            all_trainings.append({
                "training_id": training_id,
                "status": training_info.status,
                "created_at": training_info.created_at.isoformat(),
                "started_at": training_info.started_at.isoformat() if training_info.started_at else None,
                "completed_at": training_info.completed_at.isoformat() if training_info.completed_at else None,
                "error_message": training_info.error_message,
                "progress": progress_data,  # 🆕 添加进度数据
                "config": {
                    "stock_pool": training_info.config.stock_pool,
                    "max_stocks": training_info.config.max_stocks,
                    "total_timesteps": training_info.config.total_timesteps,
                    "model_name": training_info.config.model_name
                }
            })

        # 按创建时间倒序排列
        all_trainings.sort(key=lambda x: x["created_at"], reverse=True)

        return TrainingResponse(
            success=True,
            message=f"Found {len(all_trainings)} training tasks",
            data={
                "trainings": all_trainings,
                "total": len(all_trainings),
                "running": len([t for t in training_tasks.values() if t.status == TrainingStatus.RUNNING]),
                "completed": len([t for t in training_tasks.values() if t.status == TrainingStatus.COMPLETED]),
                "failed": len([t for t in training_tasks.values() if t.status == TrainingStatus.FAILED])
            }
        )

    except Exception as e:
        logger.error(f" Get all training status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/status/{training_id}", response_model=TrainingResponse)
async def get_training_status(training_id: str):
    """查询训练状态

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

        return TrainingResponse(
            success=True,
            message="查询成功",
            data={
                "training_id": training_id,
                "status": training_info.status,
                "created_at": training_info.created_at.isoformat(),
                "started_at": training_info.started_at.isoformat() if training_info.started_at else None,
                "completed_at": training_info.completed_at.isoformat() if training_info.completed_at else None,
                "error_message": training_info.error_message
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Get status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/progress/{training_id}", response_model=TrainingResponse)
async def get_training_progress(training_id: str):
    """获取训练进度

    Args:
        training_id: 训练ID

    Returns:
        训练进度
    """
    try:
        if training_id not in training_tasks:
            raise HTTPException(
                status_code=404,
                detail=f"Training not found: {training_id}"
            )

        training_info = training_tasks[training_id]

        # 读取进度文件
        progress_data = None
        try:
            progress_file = get_models_directory() / training_id / "training_progress.json"
            if progress_file.exists():
                import json
                with open(progress_file, 'r') as f:
                    progress_data = json.load(f)
            else:
                # 如果文件不存在，返回初始进度
                progress_data = {
                    "timesteps": 0,
                    "total_timesteps": training_info.config.total_timesteps,
                    "progress_pct": 0.0,
                    "ep_rew_mean": None,
                    "fps": None,
                    "elapsed_time": 0,
                    "estimated_remaining": None
                }
        except Exception as e:
            logger.warning(f"Failed to read progress file for {training_id}: {e}")
            # 返回默认进度
            progress_data = {
                "timesteps": 0,
                "total_timesteps": training_info.config.total_timesteps,
                "progress_pct": 0.0,
                "ep_rew_mean": None,
                "fps": None,
                "elapsed_time": 0,
                "estimated_remaining": None,
                "error": str(e)
            }

        return TrainingResponse(
            success=True,
            message="查询成功",
            data={
                "training_id": training_id,
                "status": training_info.status,
                "progress": progress_data
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Get progress error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/training/stop/{training_id}", response_model=TrainingResponse)
async def stop_training(training_id: str):
    """停止训练任务

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
            return TrainingResponse(
                success=False,
                message=f"Training is not running: {training_info.status}"
            )

        # TODO: 实现优雅停止逻辑
        # 发送停止信号到训练进程

        training_info.status = TrainingStatus.STOPPED
        training_info.completed_at = datetime.now()

        logger.info(f" Training stopped: {training_id}")

        return TrainingResponse(
            success=True,
            message=f"训练已停止: {training_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Stop training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=TrainingResponse)
async def list_trained_models():
    """列出所有训练好的模型

    Returns:
        模型列表
    """
    try:
        models_dir = get_models_directory()

        if not models_dir.exists():
            return TrainingResponse(
                success=True,
                message="No models found",
                data={"models": []}
            )

        models = []

        # 遍历production目录下的所有子目录和文件
        for item in models_dir.rglob("*.zip"):
            try:
                stat = item.stat()

                # 判断模型类型
                model_type = "checkpoint"
                if "best" in item.stem:
                    model_type = "best"
                elif "final" in item.stem:
                    model_type = "final"

                model_info = {
                    "model_id": item.stem,
                    "model_name": item.stem,
                    "model_path": str(item),
                    "model_type": model_type,
                    "file_size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }

                models.append(model_info)

            except Exception as e:
                logger.warning(f" Error processing model {item}: {e}")
                continue

        # 按修改时间倒序排列
        models.sort(key=lambda x: x["modified_at"], reverse=True)

        logger.info(f" Found {len(models)} models")

        return TrainingResponse(
            success=True,
            message=f"Found {len(models)} models",
            data={"models": models}
        )

    except Exception as e:
        logger.error(f" List models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}", response_model=TrainingResponse)
async def get_model_info(model_id: str):
    """获取特定模型的详细信息

    Args:
        model_id: 模型ID

    Returns:
        模型详细信息
    """
    try:
        models_dir = get_models_directory()

        # 查找匹配的模型文件
        model_files = list(models_dir.rglob(f"{model_id}.zip"))

        if not model_files:
            raise HTTPException(
                status_code=404,
                detail=f"Model not found: {model_id}"
            )

        model_path = model_files[0]
        stat = model_path.stat()

        # 尝试加载训练配置
        config_file = model_path.parent / f"{model_id}_config.json"
        config = None
        if config_file.exists():
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)

        # 尝试加载评估结果
        eval_file = model_path.parent / "evaluations.npz"
        performance = {}
        if eval_file.exists():
            import numpy as np
            eval_data = np.load(eval_file)
            performance = {
                "best_reward": float(np.max(eval_data['results'])),
                "final_reward": float(eval_data['results'][-1].mean()),
            }

        model_info = {
            "model_id": model_id,
            "model_name": model_path.stem,
            "model_path": str(model_path),
            "model_type": "best" if "best" in model_path.stem else "final" if "final" in model_path.stem else "checkpoint",
            "file_size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "config": config,
            "performance": performance
        }

        return TrainingResponse(
            success=True,
            message="查询成功",
            data=model_info
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Get model info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/{model_id}", response_model=TrainingResponse)
async def delete_model(model_id: str):
    """删除指定模型

    Args:
        model_id: 模型ID

    Returns:
        删除响应
    """
    try:
        models_dir = get_models_directory()

        # 查找匹配的模型文件
        model_files = list(models_dir.rglob(f"{model_id}.zip"))

        if not model_files:
            raise HTTPException(
                status_code=404,
                detail=f"Model not found: {model_id}"
            )

        # 删除模型文件
        model_path = model_files[0]
        model_path.unlink()

        # 删除相关文件（配置、归一化参数等）
        for ext in [".pkl", "_config.json"]:
            related_file = model_path.parent / f"{model_id}{ext}"
            if related_file.exists():
                related_file.unlink()

        logger.info(f" Model deleted: {model_id}")

        return TrainingResponse(
            success=True,
            message=f"模型已删除: {model_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Delete model error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/metrics/{training_id}", response_model=TrainingResponse)
async def get_training_metrics(training_id: str):
    """获取训练指标历史（用于绘制曲线）

    Args:
        training_id: 训练ID

    Returns:
        训练指标历史数据
    """
    try:
        if training_id not in training_tasks:
            raise HTTPException(
                status_code=404,
                detail=f"Training not found: {training_id}"
            )

        # 读取metrics历史文件
        metrics_file = get_models_directory() / training_id / "metrics_history.json"

        if not metrics_file.exists():
            # 如果文件不存在，返回空数据
            return TrainingResponse(
                success=True,
                message="Metrics history not available yet",
                data={
                    "training_id": training_id,
                    "metrics": []
                }
            )

        try:
            import json
            with open(metrics_file, 'r') as f:
                metrics_history = json.load(f)

            return TrainingResponse(
                success=True,
                message="查询成功",
                data={
                    "training_id": training_id,
                    "metrics": metrics_history,
                    "total_points": len(metrics_history)
                }
            )

        except Exception as e:
            logger.error(f"Failed to read metrics file for {training_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read metrics file: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" Get metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
