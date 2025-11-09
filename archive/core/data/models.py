"""
Pydantic data models for validation and serialization.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# Enums
class SignalDirection(str, Enum):
    """Trading signal direction."""
    LONG = "long"
    SHORT = "short"
    HOLD = "hold"
    CLOSE = "close"


class TradingBoard(str, Enum):
    """A-Share trading boards."""
    MAIN = "main"
    CHINEXT = "chinext"
    STAR = "star"


class OrderSide(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


# Market Data Models
class MarketBarData(BaseModel):
    """Single market bar (OHLCV)."""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Optional[Decimal] = None
    turnover_rate: Optional[float] = None

    class Config:
        from_attributes = True


class RealtimeQuote(BaseModel):
    """Real-time market quote."""
    symbol: str
    price: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    volume: int
    amount: Optional[Decimal] = None
    timestamp: datetime
    change_pct: Optional[float] = None

    class Config:
        from_attributes = True


# Stock Information Models
class StockBasicInfo(BaseModel):
    """Stock basic information."""
    symbol: str
    name: str
    board: TradingBoard
    industry: Optional[str] = None
    sector: Optional[str] = None
    listing_date: Optional[datetime] = None
    is_tradable: bool = True
    is_st: bool = False

    class Config:
        from_attributes = True


class StockFinancials(BaseModel):
    """Stock financial metrics."""
    symbol: str
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    market_cap: Optional[Decimal] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class StockRiskMetrics(BaseModel):
    """A-share specific risk metrics."""
    symbol: str
    pledge_ratio: Optional[float] = None
    restricted_shares_ratio: Optional[float] = None
    next_unlock_date: Optional[datetime] = None
    next_unlock_volume: Optional[int] = None
    goodwill: Optional[Decimal] = None
    total_assets: Optional[Decimal] = None
    goodwill_ratio: Optional[float] = None

    class Config:
        from_attributes = True

    @property
    def is_high_pledge_risk(self) -> bool:
        """Check if pledge ratio indicates high risk (>50%)."""
        return self.pledge_ratio is not None and self.pledge_ratio > 0.50

    @property
    def is_high_goodwill_risk(self) -> bool:
        """Check if goodwill ratio indicates high risk (>30%)."""
        return self.goodwill_ratio is not None and self.goodwill_ratio > 0.30


# Trading Signal Models
class TradingSignal(BaseModel):
    """Trading signal."""
    symbol: str
    direction: SignalDirection
    strength: float = Field(ge=0.0, le=1.0)
    agent_name: str
    strategy_name: Optional[str] = None
    entry_price: Optional[Decimal] = None
    target_price: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    suggested_position_size: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class AggregatedSignal(BaseModel):
    """Aggregated signal from multiple agents."""
    symbol: str
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    agent_signals: List[TradingSignal]
    entry_price: Optional[Decimal] = None
    target_price: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    position_size: float = Field(ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None  # Add metadata field for warnings, analysis method, etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def num_agreeing_agents(self) -> int:
        """Count agents agreeing with the direction."""
        return sum(1 for sig in self.agent_signals if sig.direction == self.direction)


# Agent Analysis Models
class AgentAnalysisResult(BaseModel):
    """Result from an agent analysis."""
    agent_name: str
    symbol: Optional[str] = None
    score: Optional[float] = None
    direction: Optional[SignalDirection] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    analysis: Dict[str, Any]
    reasoning: Optional[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_error: bool = False
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# Order Models
class OrderRequest(BaseModel):
    """Order creation request."""
    symbol: str
    side: OrderSide
    quantity: int = Field(gt=0)
    price: Optional[Decimal] = None
    order_type: str = "limit"
    strategy_name: Optional[str] = None

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        """Ensure quantity is a multiple of 100 (A-share lot size)."""
        if v % 100 != 0:
            raise ValueError("Quantity must be a multiple of 100 shares")
        return v


class OrderResponse(BaseModel):
    """Order response."""
    order_id: int
    symbol: str
    side: OrderSide
    quantity: int
    price: Optional[Decimal]
    status: str
    created_at: datetime
    broker_order_id: Optional[str] = None

    class Config:
        from_attributes = True


# Position Models
class PositionInfo(BaseModel):
    """Position information."""
    symbol: str
    quantity: int
    avg_cost: Decimal
    current_price: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_pct: Optional[float] = None
    realized_pnl: Decimal = Decimal(0)
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None
    entry_date: datetime
    board: TradingBoard

    class Config:
        from_attributes = True

    @property
    def market_value(self) -> Optional[Decimal]:
        """Calculate current market value."""
        if self.current_price:
            return self.current_price * self.quantity
        return None


# Portfolio Models
class PortfolioSummary(BaseModel):
    """Portfolio summary."""
    total_value: Decimal
    cash: Decimal
    positions_value: Decimal
    total_pnl: Decimal
    total_pnl_pct: float
    daily_pnl: Optional[Decimal] = None
    daily_pnl_pct: Optional[float] = None
    num_positions: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


# Risk Models
class RiskAlert(BaseModel):
    """Risk alert."""
    symbol: Optional[str] = None
    risk_type: str
    risk_level: str
    description: str
    metrics: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


# Technical Indicator Models
class TechnicalIndicators(BaseModel):
    """Technical indicators for a symbol."""
    symbol: str
    timestamp: datetime
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    ma_5: Optional[Decimal] = None
    ma_10: Optional[Decimal] = None
    ma_20: Optional[Decimal] = None
    ma_60: Optional[Decimal] = None
    bb_upper: Optional[Decimal] = None
    bb_middle: Optional[Decimal] = None
    bb_lower: Optional[Decimal] = None
    kdj_k: Optional[float] = None
    kdj_d: Optional[float] = None
    kdj_j: Optional[float] = None
    turnover_rate: Optional[float] = None

    class Config:
        from_attributes = True


# MCP Protocol Models
class MCPRequest(BaseModel):
    """MCP JSON-RPC 2.0 request."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPResponse(BaseModel):
    """MCP JSON-RPC 2.0 response."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPError(BaseModel):
    """MCP JSON-RPC 2.0 error."""
    code: int
    message: str
    data: Optional[Any] = None


# Strategy Models
class StrategyConfig(BaseModel):
    """Strategy configuration."""
    name: str
    enabled: bool = True
    symbols: List[str] = Field(default_factory=list)
    max_positions: int = Field(default=10, gt=0)
    position_size: float = Field(default=0.1, ge=0.0, le=1.0)
    stop_loss_pct: float = Field(default=0.08, ge=0.0)
    take_profit_pct: float = Field(default=0.15, ge=0.0)
    params: Dict[str, Any] = Field(default_factory=dict)


class BacktestConfig(BaseModel):
    """Backtesting configuration."""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Field(default=Decimal(1000000))
    commission_rate: float = Field(default=0.0003, ge=0.0)
    slippage: float = Field(default=0.001, ge=0.0)
    symbols: Optional[List[str]] = None


class BacktestResult(BaseModel):
    """Backtesting result."""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    final_capital: Decimal
    total_return: Decimal
    total_return_pct: float
    annual_return_pct: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    num_trades: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
