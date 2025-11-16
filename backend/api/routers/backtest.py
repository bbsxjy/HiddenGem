"""
Backtest API Router

提供回测相关的API端点，包括简单回测和QF-Lib专业回测
"""

# Force reload: 2025-11-13 15:00 (added action masking to fix invalid SELL_ALL actions)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import List, Optional, Dict
import logging
import os

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])

logger = logging.getLogger(__name__)


# ==================== Request Models ====================

class SimpleBacktestRequest(BaseModel):
    """简单回测请求"""
    model_path: str = Field(..., description="RL模型路径")
    symbols: List[str] = Field(..., description="股票代码列表")
    start_date: date = Field(..., description="回测开始日期")
    end_date: date = Field(..., description="回测结束日期")
    initial_capital: float = Field(1000000.0, description="初始资金")


class QFLibBacktestRequest(BaseModel):
    """QF-Lib回测请求"""
    model_path: str = Field(..., description="RL模型路径")
    symbols: List[str] = Field(..., description="股票代码列表")
    start_date: date = Field(..., description="回测开始日期")
    end_date: date = Field(..., description="回测结束日期")
    initial_capital: float = Field(1000000.0, description="初始资金")
    commission_rate: float = Field(0.00013, description="手续费率")


# ==================== Response Models ====================

class BacktestSummary(BaseModel):
    """回测摘要"""
    initial_capital: float
    final_value: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int


class BacktestResponse(BaseModel):
    """回测响应"""
    success: bool
    data: Optional[Dict] = None
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


# ==================== API Endpoints ====================

@router.post("/simple/start", response_model=BacktestResponse)
async def start_simple_backtest(request: SimpleBacktestRequest):
    """启动回测（内部重定向到QF-Lib回测）

    注意：此端点已重定向到QF-Lib回测实现。
    "简单回测"和"QF-Lib回测"目前使用相同的实现。

    Args:
        request: 回测请求参数

    Returns:
        回测启动响应
    """
    try:
        logger.info(f" Redirecting simple backtest to QF-Lib implementation: {request.symbols}")

        # 转换请求格式并调用QF-Lib回测
        qflib_request = QFLibBacktestRequest(
            model_path=request.model_path,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate  # 使用请求中的手续费率
        )

        # 调用QF-Lib回测实现
        return await start_qflib_backtest(qflib_request)

    except Exception as e:
        logger.error(f" Simple backtest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qflib/start", response_model=BacktestResponse)
async def start_qflib_backtest(request: QFLibBacktestRequest):
    """启动QF-Lib回测（事件驱动，专业级）

    特点：
    -  使用 QF-Lib 4.0.4 核心组件
    -  RL 模型驱动的交易信号
    -  A股交易规则（T+1、涨跌停、印花税）
    -  详细的性能指标

    Args:
        request: QF-Lib回测请求

    Returns:
        回测结果
    """
    try:
        logger.info(f" Starting QF-Lib backtest: {request.symbols}")

        # 检查模型文件是否存在
        if not os.path.exists(request.model_path):
            raise HTTPException(
                status_code=404,
                detail=f"Model not found: {request.model_path}"
            )

        # 获取 Tushare Token（从环境变量）
        tushare_token = os.getenv('TUSHARE_TOKEN')
        if not tushare_token:
            raise HTTPException(
                status_code=500,
                detail="TUSHARE_TOKEN not configured in environment"
            )

        # 导入并运行回测
        from qflib_integration.backtest_runner import QFLibBacktestRunner
        from datetime import datetime

        runner = QFLibBacktestRunner(
            model_path=request.model_path,
            tushare_token=tushare_token,
            symbols=request.symbols,
            start_date=datetime.combine(request.start_date, datetime.min.time()),
            end_date=datetime.combine(request.end_date, datetime.min.time()),
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate
        )

        # 异步运行回测
        results = await runner.run_async()

        return BacktestResponse(
            success=True,
            message="QF-Lib回测完成",
            data=results
        )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f" QF-Lib import error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"QF-Lib components not available: {str(e)}"
        )
    except Exception as e:
        logger.error(f" QF-Lib backtest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qflib/status/{backtest_id}", response_model=BacktestResponse)
async def get_qflib_status(backtest_id: str):
    """获取QF-Lib回测状态

    Args:
        backtest_id: 回测ID

    Returns:
        回测状态
    """
    try:
        # TODO: 实现状态查询逻辑
        # 如果使用后台任务队列（Celery），这里查询任务状态

        return BacktestResponse(
            success=True,
            message="状态查询功能开发中",
            data={
                "backtest_id": backtest_id,
                "status": "running",
                "progress": 0.5
            }
        )

    except Exception as e:
        logger.error(f" Status query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qflib/results/{backtest_id}", response_model=BacktestResponse)
async def get_qflib_results(backtest_id: str):
    """获取QF-Lib回测结果

    Args:
        backtest_id: 回测ID

    Returns:
        回测结果
    """
    try:
        # TODO: 从数据库或缓存中获取回测结果

        return BacktestResponse(
            success=True,
            message="结果查询功能开发中",
            data={
                "backtest_id": backtest_id,
                "summary": {
                    "initial_capital": 1000000.0,
                    "final_value": 1250000.0,
                    "total_return": 0.25,
                    "sharpe_ratio": 1.5,
                    "max_drawdown": -0.15,
                    "win_rate": 0.58,
                    "total_trades": 120
                },
                "equity_curve": [],
                "trades": []
            }
        )

    except Exception as e:
        logger.error(f" Results query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=BacktestResponse)
async def list_trained_models():
    """列出已训练的模型

    Returns:
        模型列表
    """
    try:
        models_dir = os.path.join(os.path.dirname(__file__), '../../models')

        if not os.path.exists(models_dir):
            return BacktestResponse(
                success=True,
                message="No models found",
                data={"models": []}
            )

        # 查找所有.zip模型文件
        model_files = []
        for file in os.listdir(models_dir):
            if file.endswith('.zip'):
                file_path = os.path.join(models_dir, file)
                stat = os.stat(file_path)

                model_files.append({
                    "name": file,
                    "path": file_path,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        return BacktestResponse(
            success=True,
            message=f"Found {len(model_files)} models",
            data={"models": model_files}
        )

    except Exception as e:
        logger.error(f" List models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
