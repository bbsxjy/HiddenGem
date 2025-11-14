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

    # 交易配置
    holding_days: int = Field(5, description="持仓天数", ge=1, le=30)

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
                "holding_days": 5,
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

        from scripts.enhanced_time_travel_training import EnhancedTimeTravelTrainer
        import time

        # 创建训练输出目录
        episode_dir = get_memorybank_directory() / training_id
        episode_dir.mkdir(parents=True, exist_ok=True)

        # 记录开始时间
        start_time = time.time()

        # 在线程池中运行训练
        loop = asyncio.get_event_loop()

        def training_worker():
            """训练工作函数 - 使用EnhancedTimeTravelTrainer进行真实的time-travel训练"""
            try:
                # 预先计算所有股票的交易日数量（用于进度估算）
                logger.info("📊 预计算交易日数量...")
                stock_trading_days_count = {}
                for symbol in config.symbols:
                    temp_trainer = EnhancedTimeTravelTrainer(
                        symbol=symbol,
                        start_date=config.start_date.strftime("%Y-%m-%d"),
                        end_date=config.end_date.strftime("%Y-%m-%d"),
                        holding_days=config.holding_days
                    )
                    days = temp_trainer.get_trading_days()
                    stock_trading_days_count[symbol] = len(days) if days else 0
                    logger.info(f"   {symbol}: {stock_trading_days_count[symbol]} 交易日")

                total_episodes = sum(stock_trading_days_count.values())
                logger.info(f"📈 总计: {total_episodes} 个episodes ({len(config.symbols)} 个股票)")

                # 遍历每个股票
                processed_episodes = 0
                total_successful = 0  # 累积所有成功的案例

                for symbol_idx, symbol in enumerate(config.symbols):
                    logger.info(f"\n{'='*60}")
                    logger.info(f"📈 开始训练股票 {symbol} ({symbol_idx + 1}/{len(config.symbols)})")
                    logger.info(f"{'='*60}")

                    # 创建EnhancedTimeTravelTrainer实例
                    trainer = EnhancedTimeTravelTrainer(
                        symbol=symbol,
                        start_date=config.start_date.strftime("%Y-%m-%d"),
                        end_date=config.end_date.strftime("%Y-%m-%d"),
                        holding_days=config.holding_days,
                        config=None  # 使用DEFAULT_CONFIG
                    )

                    # 获取交易日列表
                    trading_days = trainer.get_trading_days()
                    if not trading_days:
                        logger.warning(f"⚠️ 股票 {symbol} 无交易日数据，跳过")
                        continue

                    total_days = len(trading_days)
                    logger.info(f"   找到 {total_days} 个交易日")

                    # Time-travel训练每一天
                    successful_days = 0
                    failed_days = 0

                    for day_idx, current_date in enumerate(trading_days):
                        # 训练单日
                        success = trainer.train_one_day(current_date)

                        if success:
                            successful_days += 1
                            total_successful += 1
                        else:
                            failed_days += 1

                        # 更新总进度
                        processed_episodes += 1

                        # 更新进度
                        elapsed = time.time() - start_time
                        progress_pct = (processed_episodes / total_episodes * 100) if total_episodes > 0 else 0
                        remaining = (elapsed / processed_episodes) * (total_episodes - processed_episodes) if processed_episodes > 0 else 0

                        progress = MemoryBankProgress(
                            processed_episodes=processed_episodes,
                            total_episodes=total_episodes,
                            progress_pct=progress_pct,
                            stored_episodes=total_successful,  # 累积的成功案例数
                            avg_similarity=0.0,  # 不计算相似度
                            memory_usage_mb=0,
                            elapsed_time=elapsed,
                            estimated_remaining=remaining
                        )

                        training_tasks[training_id].progress = progress

                        # 每10个交易日输出一次日志
                        if (day_idx + 1) % 10 == 0 or day_idx == 0:
                            logger.info(
                                f"📚 [{training_id}] {symbol} 进度: {(day_idx + 1)/total_days*100:.1f}% "
                                f"({day_idx + 1}/{total_days}), 成功: {successful_days}, 失败: {failed_days}"
                            )

                    logger.info(
                        f"✅ 股票 {symbol} 训练完成: "
                        f"成功 {successful_days}/{total_days}, "
                        f"失败 {failed_days}/{total_days}"
                    )

            except Exception as e:
                logger.error(f"❌ 训练过程出错: {e}", exc_info=True)
                raise

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
