"""
Market data API routes.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from api.models.request import MarketQuoteResponse, MarketBarsResponse
from core.data.sources import data_source
from core.utils.indicators import TechnicalIndicators


router = APIRouter()


@router.get("/quote/{symbol}", response_model=MarketQuoteResponse)
async def get_quote(symbol: str):
    """
    Get real-time quote for a symbol.

    Args:
        symbol: Stock symbol

    Returns:
        Real-time quote
    """
    try:
        quote_data = data_source.get_realtime_quote(symbol)

        # Calculate change percentage if we have both price and open
        change_pct = None
        if quote_data.get('price') and quote_data.get('open') and quote_data['open'] != 0:
            change_pct = ((quote_data['price'] - quote_data['open']) / quote_data['open']) * 100

        return MarketQuoteResponse(
            symbol=quote_data['symbol'],
            price=float(quote_data['price']),
            open=float(quote_data['open']),
            high=float(quote_data['high']),
            low=float(quote_data['low']),
            volume=float(quote_data['volume']),
            change_pct=change_pct,
            timestamp=quote_data['timestamp']
        )

    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch quote: {str(e)}")


@router.get("/bars/{symbol}", response_model=MarketBarsResponse)
async def get_bars(
    symbol: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    days: int = Query(60, description="Number of days (if dates not specified)")
):
    """
    Get historical bars (OHLCV) for a symbol.

    Args:
        symbol: Stock symbol
        start_date: Start date
        end_date: End date
        days: Number of days (if dates not specified)

    Returns:
        Historical bars
    """
    try:
        # Determine date range
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if not start_date:
            start_dt = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days)
            start_date = start_dt.strftime("%Y-%m-%d")

        # Fetch data
        df = data_source.get_daily_bars(symbol, start_date, end_date)

        if df.empty:
            return MarketBarsResponse(symbol=symbol, bars=[], count=0)

        # Convert to list of dicts
        bars = df.to_dict('records')

        # Convert datetime to string
        for bar in bars:
            if 'date' in bar:
                bar['date'] = bar['date'].isoformat()

        return MarketBarsResponse(
            symbol=symbol,
            bars=bars,
            count=len(bars)
        )

    except Exception as e:
        logger.error(f"Error fetching bars for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch bars: {str(e)}")


@router.get("/indicators/{symbol}")
async def get_indicators(
    symbol: str,
    days: int = Query(60, description="Number of days for calculation")
):
    """
    Get technical indicators for a symbol.

    Args:
        symbol: Stock symbol
        days: Number of days

    Returns:
        Technical indicators
    """
    try:
        # Fetch data
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days + 30)).strftime("%Y-%m-%d")

        df = data_source.get_daily_bars(symbol, start_date, end_date)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data available for {symbol}")

        # Calculate indicators
        df = TechnicalIndicators.calculate_all_indicators(df)

        # Get latest values
        latest = df.iloc[-1].to_dict()

        # Convert datetime to string
        if 'date' in latest:
            latest['date'] = latest['date'].isoformat()

        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'indicators': latest,
            'calculated_from_days': len(df)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating indicators for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate indicators: {str(e)}")


@router.get("/search")
async def search_stocks(
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, le=100, description="Maximum results")
):
    """
    Search for stocks by symbol or name.

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        List of matching stocks
    """
    try:
        # This is a simplified implementation
        # Production would have a proper search index
        return {
            'query': query,
            'results': [],
            'message': 'Stock search not yet implemented'
        }

    except Exception as e:
        logger.error(f"Error searching stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/{symbol}")
async def get_stock_info(symbol: str):
    """
    Get stock basic information.

    Args:
        symbol: Stock symbol

    Returns:
        Stock information
    """
    try:
        info = data_source.get_stock_basic_info(symbol)

        return {
            'symbol': info['symbol'],
            'name': info['name'],
            'industry': info.get('industry'),
            'area': info.get('area'),
            'listing_date': info.get('list_date')
        }

    except Exception as e:
        logger.error(f"Error fetching info for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
