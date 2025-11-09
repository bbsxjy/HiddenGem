"""
Strategy management API routes.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from config.database import get_db
from api.models.request import (
    StrategyCreateRequest, StrategyUpdateRequest, StrategyResponse,
    BacktestRequest, BacktestResponse, SuccessResponse
)
from core.data.models import StrategyConfig, BacktestConfig
from core.strategy.swing_trading import SwingTradingStrategy
from core.strategy.trend_following import TrendFollowingStrategy
from core.strategy.backtester import SimpleBacktester
from core.mcp_agents.orchestrator import MCPOrchestrator


router = APIRouter()

# In-memory strategy storage (simplified)
# Production would use database
strategies_store: dict = {}
orchestrator = MCPOrchestrator()  # Shared orchestrator


def _initialize_default_strategies():
    """Initialize default tech-focused strategies."""
    if strategies_store:  # Already initialized
        return

    default_strategies = [
        {
            "name": "科技龙头跟踪",
            "type": "trend_following",
            "enabled": True,
            "symbols": [
                "300750",  # 宁德时代 - 新能源电池
                "002594",  # 比亚迪 - 新能源汽车
                "688981",  # 中芯国际 - 半导体制造
                "300059",  # 东方财富 - 金融科技
                "002415",  # 海康威视 - 安防AI
                "000725",  # 京东方A - 显示面板
                "603501",  # 韦尔股份 - 半导体设计
                "688111"   # 金山办公 - 软件
            ],
            "max_positions": 4,
            "position_size": 0.08,
            "stop_loss_pct": 0.08,
            "take_profit_pct": 0.15,
            "params": {
                "trend_period": 20,
                "min_trend_strength": 0.6,
                "sector": "technology"
            }
        },
        {
            "name": "芯片半导体突破",
            "type": "swing_trading",
            "enabled": True,
            "symbols": [
                "688981",  # 中芯国际
                "603501",  # 韦尔股份
                "688396",  # 华润微
                "688008",  # 澜起科技
                "688012",  # 中微公司
                "300782",  # 卓胜微
                "688099",  # 晶晨股份
                "300456"   # 赛微电子
            ],
            "max_positions": 3,
            "position_size": 0.10,
            "stop_loss_pct": 0.08,
            "take_profit_pct": 0.12,
            "params": {
                "breakout_period": 20,
                "volume_threshold": 1.5,
                "sector": "semiconductor"
            }
        },
        {
            "name": "AI算力基建",
            "type": "trend_following",
            "enabled": True,
            "symbols": [
                "002153",  # 石基信息 - 云计算
                "300454",  # 深信服 - 网络安全
                "002353",  # 杰瑞股份 - 智能装备
                "300418",  # 昆仑万维 - AI大模型
                "002230",  # 科大讯飞 - AI语音
                "300413",  # 芒果超媒 - 数字内容
                "600588"   # 用友网络 - 企业软件
            ],
            "max_positions": 3,
            "position_size": 0.09,
            "stop_loss_pct": 0.08,
            "take_profit_pct": 0.18,
            "params": {
                "trend_period": 30,
                "min_trend_strength": 0.65,
                "sector": "ai_infrastructure"
            }
        },
        {
            "name": "新能源产业链",
            "type": "swing_trading",
            "enabled": True,
            "symbols": [
                "300750",  # 宁德时代 - 电池
                "002594",  # 比亚迪 - 整车
                "300014",  # 亿纬锂能 - 电池
                "002459",  # 晶澳科技 - 光伏
                "601012",  # 隆基绿能 - 光伏
                "300124",  # 汇川技术 - 工控
                "688599",  # 天合光能 - 光伏
                "300316"   # 晶盛机电 - 设备
            ],
            "max_positions": 4,
            "position_size": 0.08,
            "stop_loss_pct": 0.08,
            "take_profit_pct": 0.15,
            "params": {
                "breakout_period": 15,
                "volume_threshold": 1.3,
                "sector": "new_energy"
            }
        },
        {
            "name": "5G通信设备",
            "type": "trend_following",
            "enabled": False,  # 默认禁用
            "symbols": [
                "600050",  # 中国联通
                "000063",  # 中兴通讯
                "600487",  # 亨通光电
                "002281",  # 光迅科技
                "300134",  # 大富科技
                "300308"   # 中际旭创
            ],
            "max_positions": 2,
            "position_size": 0.10,
            "stop_loss_pct": 0.08,
            "take_profit_pct": 0.12,
            "params": {
                "trend_period": 25,
                "min_trend_strength": 0.60,
                "sector": "5g_communication"
            }
        }
    ]

    created_time = datetime.utcnow()

    for strategy_def in default_strategies:
        config = StrategyConfig(
            name=strategy_def["name"],
            enabled=strategy_def["enabled"],
            symbols=strategy_def["symbols"],
            max_positions=strategy_def["max_positions"],
            position_size=strategy_def["position_size"],
            stop_loss_pct=strategy_def["stop_loss_pct"],
            take_profit_pct=strategy_def["take_profit_pct"],
            params=strategy_def["params"]
        )

        # Create strategy instance
        if strategy_def["type"] == "swing_trading":
            strategy = SwingTradingStrategy(config, orchestrator)
        else:  # trend_following
            strategy = TrendFollowingStrategy(config, orchestrator)

        strategies_store[strategy_def["name"]] = {
            'strategy': strategy,
            'type': strategy_def["type"],
            'created_at': created_time
        }

    logger.info(f"Initialized {len(default_strategies)} default tech-focused strategies")


# Initialize default strategies on module load
_initialize_default_strategies()


@router.post("/", response_model=StrategyResponse, status_code=201)
async def create_strategy(
    request: StrategyCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new trading strategy.

    Args:
        request: Strategy creation request
        db: Database session

    Returns:
        Created strategy information
    """
    # Check if strategy name already exists
    if request.name in strategies_store:
        raise HTTPException(status_code=400, detail=f"Strategy '{request.name}' already exists")

    # Create strategy config
    config = StrategyConfig(
        name=request.name,
        enabled=request.enabled,
        symbols=request.symbols,
        max_positions=request.max_positions,
        position_size=request.position_size,
        stop_loss_pct=request.stop_loss_pct,
        take_profit_pct=request.take_profit_pct,
        params=request.params
    )

    # Create strategy instance
    if request.strategy_type == "swing_trading":
        strategy = SwingTradingStrategy(config, orchestrator)
    elif request.strategy_type == "trend_following":
        strategy = TrendFollowingStrategy(config, orchestrator)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy type: {request.strategy_type}"
        )

    # Store strategy
    strategies_store[request.name] = {
        'strategy': strategy,
        'type': request.strategy_type,
        'created_at': datetime.utcnow()
    }

    logger.info(f"Created strategy: {request.name} ({request.strategy_type})")

    return StrategyResponse(
        name=strategy.name,
        strategy_type=request.strategy_type,
        enabled=strategy.enabled,
        symbols=config.symbols,
        max_positions=strategy.max_positions,
        position_size=strategy.position_size,
        stop_loss_pct=strategy.stop_loss_pct,
        take_profit_pct=strategy.take_profit_pct,
        num_positions=len(strategy.positions),
        params=config.params,
        created_at=strategies_store[request.name]['created_at']
    )


@router.get("/", response_model=List[StrategyResponse])
async def list_strategies():
    """
    List all strategies.

    Returns:
        List of strategies
    """
    strategies = []

    for name, data in strategies_store.items():
        strategy = data['strategy']
        strategies.append(StrategyResponse(
            name=strategy.name,
            strategy_type=data['type'],
            enabled=strategy.enabled,
            symbols=strategy.config.symbols,
            max_positions=strategy.max_positions,
            position_size=strategy.position_size,
            stop_loss_pct=strategy.stop_loss_pct,
            take_profit_pct=strategy.take_profit_pct,
            num_positions=len(strategy.positions),
            params=strategy.config.params,
            created_at=data['created_at']
        ))

    return strategies


@router.get("/{strategy_name}", response_model=StrategyResponse)
async def get_strategy(strategy_name: str):
    """
    Get strategy details.

    Args:
        strategy_name: Strategy name

    Returns:
        Strategy information
    """
    if strategy_name not in strategies_store:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")

    data = strategies_store[strategy_name]
    strategy = data['strategy']

    return StrategyResponse(
        name=strategy.name,
        strategy_type=data['type'],
        enabled=strategy.enabled,
        symbols=strategy.config.symbols,
        max_positions=strategy.max_positions,
        position_size=strategy.position_size,
        stop_loss_pct=strategy.stop_loss_pct,
        take_profit_pct=strategy.take_profit_pct,
        num_positions=len(strategy.positions),
        params=strategy.config.params,
        created_at=data['created_at']
    )


@router.patch("/{strategy_name}", response_model=StrategyResponse)
async def update_strategy(
    strategy_name: str,
    request: StrategyUpdateRequest
):
    """
    Update strategy configuration.

    Args:
        strategy_name: Strategy name
        request: Update request

    Returns:
        Updated strategy information
    """
    if strategy_name not in strategies_store:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")

    data = strategies_store[strategy_name]
    strategy = data['strategy']

    # Update fields
    if request.enabled is not None:
        strategy.enabled = request.enabled

    if request.symbols is not None:
        strategy.config.symbols = request.symbols

    if request.max_positions is not None:
        strategy.max_positions = request.max_positions

    if request.position_size is not None:
        strategy.position_size = request.position_size

    if request.params is not None:
        strategy.params.update(request.params)

    logger.info(f"Updated strategy: {strategy_name}")

    return StrategyResponse(
        name=strategy.name,
        strategy_type=data['type'],
        enabled=strategy.enabled,
        symbols=strategy.config.symbols,
        max_positions=strategy.max_positions,
        position_size=strategy.position_size,
        stop_loss_pct=strategy.stop_loss_pct,
        take_profit_pct=strategy.take_profit_pct,
        num_positions=len(strategy.positions),
        params=strategy.config.params,
        created_at=data['created_at']
    )


@router.delete("/{strategy_name}", response_model=SuccessResponse)
async def delete_strategy(strategy_name: str):
    """
    Delete a strategy.

    Args:
        strategy_name: Strategy name

    Returns:
        Success response
    """
    if strategy_name not in strategies_store:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")

    del strategies_store[strategy_name]
    logger.info(f"Deleted strategy: {strategy_name}")

    return SuccessResponse(
        success=True,
        message=f"Strategy '{strategy_name}' deleted"
    )


@router.post("/{strategy_name}/backtest", response_model=BacktestResponse)
async def run_backtest(
    strategy_name: str,
    request: BacktestRequest
):
    """
    Run backtest for a strategy.

    Args:
        strategy_name: Strategy name
        request: Backtest request

    Returns:
        Backtest results
    """
    if strategy_name not in strategies_store:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")

    data = strategies_store[strategy_name]
    strategy = data['strategy']

    # Create backtest config
    config = BacktestConfig(
        strategy_name=strategy_name,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital,
        symbols=request.symbols
    )

    # Run backtest
    logger.info(f"Starting backtest for {strategy_name}")

    backtester = SimpleBacktester(config)

    try:
        result = await backtester.run(strategy, config.symbols)

        return BacktestResponse(
            strategy_name=result.strategy_name,
            start_date=result.start_date,
            end_date=result.end_date,
            initial_capital=result.initial_capital,
            final_capital=result.final_capital,
            total_return=result.total_return,
            total_return_pct=result.total_return_pct,
            annual_return_pct=result.annual_return_pct,
            sharpe_ratio=result.sharpe_ratio,
            max_drawdown=result.max_drawdown,
            win_rate=result.win_rate,
            num_trades=result.num_trades
        )

    except Exception as e:
        logger.exception(f"Backtest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.get("/{strategy_name}/stats")
async def get_strategy_stats(strategy_name: str):
    """
    Get strategy statistics.

    Args:
        strategy_name: Strategy name

    Returns:
        Strategy stats
    """
    if strategy_name not in strategies_store:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")

    data = strategies_store[strategy_name]
    strategy = data['strategy']

    return strategy.get_strategy_stats()
