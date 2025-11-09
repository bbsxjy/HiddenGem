"""
Helper utility functions for the trading system.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
import re

from database.models import TradingBoard


def get_trading_board(symbol: str) -> TradingBoard:
    """
    Determine trading board from stock symbol.

    Args:
        symbol: Stock symbol (e.g., '000001', '688001', '300001')

    Returns:
        TradingBoard enum value
    """
    # Remove exchange suffix if present
    clean_symbol = symbol.split('.')[0] if '.' in symbol else symbol

    # STAR Market (科创板): 688xxx
    if clean_symbol.startswith('688'):
        return TradingBoard.STAR

    # ChiNext (创业板): 300xxx
    elif clean_symbol.startswith('300'):
        return TradingBoard.CHINEXT

    # Main Board (主板): everything else
    else:
        return TradingBoard.MAIN


def get_price_limit(board: TradingBoard) -> float:
    """
    Get daily price limit percentage for trading board.

    Args:
        board: Trading board

    Returns:
        Price limit as decimal (e.g., 0.10 for 10%)
    """
    if board == TradingBoard.MAIN:
        return 0.10  # 10% limit
    else:  # CHINEXT or STAR
        return 0.20  # 20% limit


def calculate_commission(
    price: Decimal,
    quantity: int,
    board: TradingBoard,
    is_sell: bool = False
) -> Decimal:
    """
    Calculate trading commission and fees for A-share.

    Args:
        price: Trade price
        quantity: Number of shares
        board: Trading board
        is_sell: Whether this is a sell order

    Returns:
        Total fees (commission + stamp duty)
    """
    amount = price * quantity

    # Commission (0.03% typical, minimum 5 RMB)
    commission_rate = Decimal('0.0003')
    commission = max(amount * commission_rate, Decimal('5.00'))

    # Stamp duty (0.1%, only on sell)
    stamp_duty = Decimal('0')
    if is_sell:
        stamp_duty_rate = Decimal('0.001')
        stamp_duty = amount * stamp_duty_rate

    return commission + stamp_duty


def validate_symbol(symbol: str) -> bool:
    """
    Validate A-share stock symbol format.

    Args:
        symbol: Stock symbol

    Returns:
        True if valid, False otherwise
    """
    # Pattern: 6 digits, optionally followed by .SH or .SZ
    pattern = r'^\d{6}(\.S[HZ])?$'
    return bool(re.match(pattern, symbol))


def normalize_symbol(symbol: str) -> str:
    """
    Normalize stock symbol format.

    Args:
        symbol: Stock symbol in any format

    Returns:
        Normalized symbol (without exchange suffix)
    """
    return symbol.split('.')[0] if '.' in symbol else symbol


def add_exchange_suffix(symbol: str) -> str:
    """
    Add exchange suffix to symbol if not present.

    Args:
        symbol: Stock symbol

    Returns:
        Symbol with exchange suffix (e.g., '000001.SZ')
    """
    if '.' in symbol:
        return symbol

    if symbol.startswith('6'):
        return f"{symbol}.SH"  # Shanghai
    else:
        return f"{symbol}.SZ"  # Shenzhen


def is_trading_day(date: datetime) -> bool:
    """
    Check if a date is a trading day (simplified).
    Note: This is a simple implementation. Production should use a holiday calendar.

    Args:
        date: Date to check

    Returns:
        True if likely a trading day
    """
    # Weekend check
    if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # TODO: Add Chinese holiday calendar check
    return True


def get_next_trading_day(date: datetime) -> datetime:
    """
    Get next trading day (simplified).

    Args:
        date: Starting date

    Returns:
        Next trading day
    """
    next_day = date + timedelta(days=1)

    while not is_trading_day(next_day):
        next_day += timedelta(days=1)

    return next_day


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format number as percentage string.

    Args:
        value: Decimal value (e.g., 0.15 for 15%)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def format_currency(value: Decimal, currency: str = "¥") -> str:
    """
    Format decimal as currency string.

    Args:
        value: Currency value
        currency: Currency symbol

    Returns:
        Formatted currency string
    """
    return f"{currency}{value:,.2f}"


def calculate_position_size(
    portfolio_value: Decimal,
    position_pct: float,
    price: Decimal,
    max_position_value: Optional[Decimal] = None
) -> int:
    """
    Calculate position size in shares.

    Args:
        portfolio_value: Total portfolio value
        position_pct: Desired position percentage (0.0 to 1.0)
        price: Stock price
        max_position_value: Optional maximum position value

    Returns:
        Number of shares to buy (rounded to lot size of 100)
    """
    target_value = portfolio_value * Decimal(str(position_pct))

    if max_position_value:
        target_value = min(target_value, max_position_value)

    shares = int(target_value / price)

    # Round down to nearest lot (100 shares)
    shares = (shares // 100) * 100

    return shares


def calculate_stop_loss_price(
    entry_price: Decimal,
    stop_loss_pct: float,
    is_long: bool = True
) -> Decimal:
    """
    Calculate stop loss price.

    Args:
        entry_price: Entry price
        stop_loss_pct: Stop loss percentage (e.g., 0.08 for 8%)
        is_long: True for long position, False for short

    Returns:
        Stop loss price
    """
    if is_long:
        return entry_price * Decimal(str(1 - stop_loss_pct))
    else:
        return entry_price * Decimal(str(1 + stop_loss_pct))


def calculate_take_profit_price(
    entry_price: Decimal,
    take_profit_pct: float,
    is_long: bool = True
) -> Decimal:
    """
    Calculate take profit price.

    Args:
        entry_price: Entry price
        take_profit_pct: Take profit percentage (e.g., 0.15 for 15%)
        is_long: True for long position, False for short

    Returns:
        Take profit price
    """
    if is_long:
        return entry_price * Decimal(str(1 + take_profit_pct))
    else:
        return entry_price * Decimal(str(1 - take_profit_pct))


def round_to_tick(price: Decimal, tick_size: Decimal = Decimal('0.01')) -> Decimal:
    """
    Round price to tick size.

    Args:
        price: Price to round
        tick_size: Minimum price increment

    Returns:
        Rounded price
    """
    return (price / tick_size).quantize(Decimal('1')) * tick_size
