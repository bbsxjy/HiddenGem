"""
Pydantic models for API requests and responses.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


# Strategy Models
class StrategyCreateRequest(BaseModel):
    """Request to create a strategy."""
    name: str
    strategy_type: str = Field(description="swing_trading or trend_following")
    enabled: bool = True
    symbols: List[str] = Field(default_factory=list)
    max_positions: int = Field(default=10, ge=1)
    position_size: float = Field(default=0.10, ge=0.01, le=0.50)
    stop_loss_pct: float = Field(default=0.08, ge=0.01)
    take_profit_pct: float = Field(default=0.15, ge=0.01)
    params: Dict[str, Any] = Field(default_factory=dict)


class StrategyUpdateRequest(BaseModel):
    """Request to update a strategy."""
    enabled: Optional[bool] = None
    symbols: Optional[List[str]] = None
    max_positions: Optional[int] = Field(default=None, ge=1)
    position_size: Optional[float] = Field(default=None, ge=0.01, le=0.50)
    params: Optional[Dict[str, Any]] = None


class StrategyResponse(BaseModel):
    """Strategy information response."""
    name: str
    strategy_type: str
    enabled: bool
    symbols: List[str]
    max_positions: int
    position_size: float
    stop_loss_pct: float
    take_profit_pct: float
    num_positions: int
    params: Dict[str, Any]
    created_at: datetime


# Backtest Models
class BacktestRequest(BaseModel):
    """Request to run backtest."""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Field(default=Decimal(1000000))
    symbols: Optional[List[str]] = None


class BacktestResponse(BaseModel):
    """Backtest results response."""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    final_capital: Decimal
    total_return: Decimal
    total_return_pct: float
    annual_return_pct: float
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    win_rate: Optional[float]
    num_trades: int


# Market Data Models
class MarketQuoteResponse(BaseModel):
    """Market quote response."""
    symbol: str
    price: float
    open: float
    high: float
    low: float
    volume: float  # Changed from int - Tushare returns volume as float
    change_pct: Optional[float]
    timestamp: datetime


class MarketBarsResponse(BaseModel):
    """Market bars (OHLCV) response."""
    symbol: str
    bars: List[Dict[str, Any]]
    count: int


# Portfolio Models
class PortfolioSummaryResponse(BaseModel):
    """Portfolio summary response."""
    total_value: Decimal
    cash: Decimal
    positions_value: Decimal
    total_pnl: Decimal
    total_pnl_pct: float
    daily_pnl: Optional[Decimal]
    num_positions: int
    timestamp: datetime


class PositionResponse(BaseModel):
    """Position response."""
    symbol: str
    quantity: int
    avg_cost: Decimal
    current_price: Optional[Decimal]
    market_value: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]
    unrealized_pnl_pct: Optional[float]
    entry_date: datetime
    strategy_name: Optional[str]


# Order Models
class OrderCreateRequest(BaseModel):
    """Request to create order."""
    symbol: str
    side: str = Field(description="buy or sell")
    quantity: int = Field(ge=100)
    price: Optional[Decimal] = None
    order_type: str = Field(default="limit", description="market or limit")
    strategy_name: Optional[str] = None


class OrderResponse(BaseModel):
    """Order response."""
    id: int
    symbol: str
    side: str
    order_type: str
    quantity: int
    price: Optional[Decimal]
    filled_quantity: int
    avg_filled_price: Optional[Decimal]
    status: str
    created_at: datetime
    filled_at: Optional[datetime]


# Agent Models
class AgentStatusResponse(BaseModel):
    """Agent status response."""
    name: str
    enabled: bool
    weight: float
    timeout: int
    cache_ttl: int


class AgentAnalysisRequest(BaseModel):
    """Request for agent analysis."""
    symbol: str
    use_cache: bool = True


class AgentAnalysisResponse(BaseModel):
    """Agent analysis response."""
    agent_name: str
    symbol: Optional[str]
    score: Optional[float]
    direction: Optional[str]
    confidence: Optional[float]
    reasoning: Optional[str]
    analysis: Dict[str, Any]
    execution_time_ms: Optional[int]
    timestamp: datetime
    is_error: bool


# Signal Models
class SignalResponse(BaseModel):
    """Trading signal response."""
    id: int
    symbol: str
    direction: str
    strength: float
    agent_name: str
    strategy_name: Optional[str]
    entry_price: Optional[Decimal]
    target_price: Optional[Decimal]
    stop_loss_price: Optional[Decimal]
    reasoning: Optional[str]
    timestamp: datetime
    is_executed: bool


class AggregatedSignalResponse(BaseModel):
    """Aggregated signal from multiple agents."""
    symbol: str
    direction: str
    confidence: float
    num_agents: int
    num_agreeing: int
    entry_price: Optional[Decimal]
    target_price: Optional[Decimal]
    stop_loss_price: Optional[Decimal]
    position_size: float
    timestamp: datetime


# Common Models
class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    """Success response."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
