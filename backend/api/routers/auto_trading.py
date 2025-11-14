"""
Auto Trading API Router

提供自动交易控制的API端点
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from api.services.auto_trading_service import auto_trading_service

router = APIRouter()


# Pydantic Models
class RiskParams(BaseModel):
    """风险控制参数"""
    buyPriceChangeMin: float = 3.0
    buyVolumeRatioMin: float = 1.2
    buyAmplitudeMax: float = 8.0
    buyTurnoverRateMax: float = 15.0
    minHoldingDays: int = 1
    stopLossPct: float = 5.0
    takeProfitPct: float = 8.0
    maxPositionPct: float = 5.0


class AutoTradingConfig(BaseModel):
    """自动交易配置"""
    symbols: List[str]  # 交易股票列表
    initial_cash: float = 100000.0  # 初始资金
    check_interval: int = 5  # 检查间隔（分钟）
    use_multi_agent: bool = True  # 是否使用多Agent分析（已废弃）
    strategy_modes: List[str] = []  # 策略模式列表（新增）
    risk_params: Optional[RiskParams] = None  # 风险控制参数（可选）


class StrategyPerformance(BaseModel):
    """策略表现数据"""
    strategy_id: str
    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_loss: float
    profit_loss_pct: float
    num_positions: int
    current_cash: float
    current_value: float


class AutoTradingStatus(BaseModel):
    """自动交易状态"""
    is_running: bool
    started_at: Optional[str] = None
    current_symbols: List[str] = []
    total_trades: int = 0
    current_cash: float = 0.0
    total_assets: float = 0.0
    profit_loss: float = 0.0
    profit_loss_pct: float = 0.0
    next_check_time: Optional[str] = None
    is_trading_hours: bool = False
    strategy_performances: List[StrategyPerformance] = []  # 多策略表现数据
    num_strategies: int = 0  # 策略数量


@router.post("/start")
async def start_auto_trading(config: AutoTradingConfig):
    """启动自动交易，支持多策略"""
    try:
        # 检查是否已经在运行
        if auto_trading_service.is_running():
            raise HTTPException(
                status_code=400,
                detail="自动交易已经在运行中，请先停止当前交易"
            )

        # 启动自动交易（传递strategy_modes）
        success = await auto_trading_service.start(
            symbols=config.symbols,
            initial_cash=config.initial_cash,
            check_interval=config.check_interval,
            use_multi_agent=config.use_multi_agent,
            strategy_modes=config.strategy_modes  # 传递策略模式列表
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="启动自动交易失败"
            )

        return {
            "success": True,
            "message": f"自动交易已启动，运行 {len(config.strategy_modes)} 个策略",
            "data": {
                "symbols": config.symbols,
                "started_at": datetime.now().isoformat(),
                "check_interval": config.check_interval,
                "strategy_modes": config.strategy_modes,
                "num_strategies": len(config.strategy_modes)
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"启动自动交易失败: {str(e)}"
        )


@router.post("/stop")
async def stop_auto_trading():
    """停止自动交易"""
    try:
        # 检查是否正在运行
        if not auto_trading_service.is_running():
            raise HTTPException(
                status_code=400,
                detail="自动交易未在运行"
            )

        # 停止自动交易
        success = await auto_trading_service.stop()

        if not success:
            raise HTTPException(
                status_code=500,
                detail="停止自动交易失败"
            )

        return {
            "success": True,
            "message": "自动交易已停止",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"停止自动交易失败: {str(e)}"
        )


@router.get("/status")
async def get_auto_trading_status():
    """获取自动交易状态"""
    try:
        status = auto_trading_service.get_status()

        return {
            "success": True,
            "data": status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取状态失败: {str(e)}"
        )


@router.get("/config")
async def get_auto_trading_config():
    """获取当前配置"""
    try:
        config = auto_trading_service.get_config()

        return {
            "success": True,
            "data": config,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取配置失败: {str(e)}"
        )


@router.get("/performance")
async def get_auto_trading_performance():
    """获取交易表现"""
    try:
        performance = auto_trading_service.get_performance()

        return {
            "success": True,
            "data": performance,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取表现失败: {str(e)}"
        )


@router.get("/decisions")
async def get_stock_decisions():
    """获取实时股票决策"""
    try:
        decisions = auto_trading_service.get_stock_decisions()

        return {
            "success": True,
            "data": decisions,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取决策失败: {str(e)}"
        )

