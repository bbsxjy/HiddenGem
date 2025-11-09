"""
Portfolio management API routes.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from config.database import get_db
from api.models.request import PortfolioSummaryResponse, PositionResponse
from database.models import Position, PortfolioSnapshot


router = APIRouter()


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(db: AsyncSession = Depends(get_db)):
    """
    Get portfolio summary.

    Args:
        db: Database session

    Returns:
        Portfolio summary
    """
    try:
        # Get latest snapshot
        stmt = select(PortfolioSnapshot).order_by(PortfolioSnapshot.timestamp.desc()).limit(1)
        result = await db.execute(stmt)
        snapshot = result.scalar_one_or_none()

        if not snapshot:
            # Return default if no snapshot
            return PortfolioSummaryResponse(
                total_value=Decimal(0),
                cash=Decimal(0),
                positions_value=Decimal(0),
                total_pnl=Decimal(0),
                total_pnl_pct=0.0,
                daily_pnl=None,
                num_positions=0,
                timestamp=datetime.utcnow()
            )

        return PortfolioSummaryResponse(
            total_value=snapshot.total_value,
            cash=snapshot.cash,
            positions_value=snapshot.positions_value,
            total_pnl=snapshot.total_pnl,
            total_pnl_pct=snapshot.total_pnl_pct,
            daily_pnl=snapshot.daily_pnl,
            num_positions=snapshot.num_positions,
            timestamp=snapshot.timestamp
        )

    except Exception as e:
        logger.error(f"Error fetching portfolio summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(db: AsyncSession = Depends(get_db)):
    """
    Get all current positions.

    Args:
        db: Database session

    Returns:
        List of positions
    """
    try:
        stmt = select(Position)
        result = await db.execute(stmt)
        positions = result.scalars().all()

        return [
            PositionResponse(
                symbol=p.symbol,
                quantity=p.quantity,
                avg_cost=p.avg_cost,
                current_price=p.current_price,
                market_value=p.current_price * p.quantity if p.current_price else None,
                unrealized_pnl=p.unrealized_pnl,
                unrealized_pnl_pct=p.unrealized_pnl_pct,
                entry_date=p.entry_date,
                strategy_name=p.strategy_name
            )
            for p in positions
        ]

    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions/{symbol}", response_model=PositionResponse)
async def get_position(symbol: str, db: AsyncSession = Depends(get_db)):
    """
    Get position for a specific symbol.

    Args:
        symbol: Stock symbol
        db: Database session

    Returns:
        Position details
    """
    try:
        stmt = select(Position).where(Position.symbol == symbol)
        result = await db.execute(stmt)
        position = result.scalar_one_or_none()

        if not position:
            raise HTTPException(status_code=404, detail=f"No position found for {symbol}")

        return PositionResponse(
            symbol=position.symbol,
            quantity=position.quantity,
            avg_cost=position.avg_cost,
            current_price=position.current_price,
            market_value=position.current_price * position.quantity if position.current_price else None,
            unrealized_pnl=position.unrealized_pnl,
            unrealized_pnl_pct=position.unrealized_pnl_pct,
            entry_date=position.entry_date,
            strategy_name=position.strategy_name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching position for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_portfolio_history(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Get portfolio history snapshots.

    Args:
        days: Number of days
        db: Database session

    Returns:
        Historical snapshots
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.timestamp >= cutoff_date)
            .order_by(PortfolioSnapshot.timestamp.asc())
        )

        result = await db.execute(stmt)
        snapshots = result.scalars().all()

        return {
            'snapshots': [
                {
                    'timestamp': s.timestamp.isoformat(),
                    'total_value': float(s.total_value),
                    'total_pnl': float(s.total_pnl),
                    'total_pnl_pct': s.total_pnl_pct,
                    'num_positions': s.num_positions
                }
                for s in snapshots
            ],
            'count': len(snapshots)
        }

    except Exception as e:
        logger.error(f"Error fetching portfolio history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
