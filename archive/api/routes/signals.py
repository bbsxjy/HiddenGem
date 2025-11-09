"""
Trading signals API routes.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from config.database import get_db
from api.models.request import SignalResponse, AggregatedSignalResponse
from database.models import Signal


router = APIRouter()


@router.get("/current", response_model=List[SignalResponse])
async def get_current_signals(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current trading signals (not yet executed).

    Args:
        limit: Maximum results
        db: Database session

    Returns:
        List of current signals
    """
    try:
        stmt = (
            select(Signal)
            .where(Signal.is_executed == False)
            .order_by(Signal.timestamp.desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        signals = result.scalars().all()

        return [
            SignalResponse(
                id=s.id,
                symbol=s.symbol,
                direction=s.direction.value,
                strength=s.strength,
                agent_name=s.agent_name,
                strategy_name=s.strategy_name,
                entry_price=s.entry_price,
                target_price=s.target_price,
                stop_loss_price=s.stop_loss_price,
                reasoning=s.reasoning,
                timestamp=s.timestamp,
                is_executed=s.is_executed
            )
            for s in signals
        ]

    except Exception as e:
        logger.error(f"Error fetching current signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[SignalResponse])
async def get_signal_history(
    days: int = Query(7, le=90),
    symbol: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get historical signals.

    Args:
        days: Number of days
        symbol: Filter by symbol
        db: Database session

    Returns:
        Historical signals
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(Signal)
            .where(Signal.timestamp >= cutoff_date)
            .order_by(Signal.timestamp.desc())
        )

        if symbol:
            stmt = stmt.where(Signal.symbol == symbol)

        result = await db.execute(stmt)
        signals = result.scalars().all()

        return [
            SignalResponse(
                id=s.id,
                symbol=s.symbol,
                direction=s.direction.value,
                strength=s.strength,
                agent_name=s.agent_name,
                strategy_name=s.strategy_name,
                entry_price=s.entry_price,
                target_price=s.target_price,
                stop_loss_price=s.stop_loss_price,
                reasoning=s.reasoning,
                timestamp=s.timestamp,
                is_executed=s.is_executed
            )
            for s in signals
        ]

    except Exception as e:
        logger.error(f"Error fetching signal history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(signal_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get signal details.

    Args:
        signal_id: Signal ID
        db: Database session

    Returns:
        Signal details
    """
    try:
        stmt = select(Signal).where(Signal.id == signal_id)
        result = await db.execute(stmt)
        signal = result.scalar_one_or_none()

        if not signal:
            raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")

        return SignalResponse(
            id=signal.id,
            symbol=signal.symbol,
            direction=signal.direction.value,
            strength=signal.strength,
            agent_name=signal.agent_name,
            strategy_name=signal.strategy_name,
            entry_price=signal.entry_price,
            target_price=signal.target_price,
            stop_loss_price=signal.stop_loss_price,
            reasoning=signal.reasoning,
            timestamp=signal.timestamp,
            is_executed=signal.is_executed
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching signal {signal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_signal_stats(
    days: int = Query(30, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    Get signal statistics.

    Args:
        days: Number of days
        db: Database session

    Returns:
        Signal statistics
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(Signal).where(Signal.timestamp >= cutoff_date)
        result = await db.execute(stmt)
        signals = result.scalars().all()

        # Calculate stats
        total_signals = len(signals)
        executed_signals = sum(1 for s in signals if s.is_executed)
        by_direction = {}
        by_agent = {}

        for signal in signals:
            # By direction
            direction = signal.direction.value
            by_direction[direction] = by_direction.get(direction, 0) + 1

            # By agent
            agent = signal.agent_name
            by_agent[agent] = by_agent.get(agent, 0) + 1

        return {
            'period_days': days,
            'total_signals': total_signals,
            'executed_signals': executed_signals,
            'execution_rate': executed_signals / total_signals if total_signals > 0 else 0,
            'by_direction': by_direction,
            'by_agent': by_agent
        }

    except Exception as e:
        logger.error(f"Error calculating signal stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
