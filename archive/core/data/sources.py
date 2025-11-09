"""
Data source integrations for market data.
Implements Tushare Pro and AkShare clients with rate limiting and fallback logic.
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio
from functools import wraps

import pandas as pd
import tushare as ts
import akshare as ak
from loguru import logger

from config.settings import settings


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, max_calls: int, time_window: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in time window
            time_window: Time window in seconds (default 60s = 1 minute)
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: List[float] = []

    def __call__(self, func):
        """Decorator to apply rate limiting."""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            await self._wait_if_needed()
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            self._wait_if_needed_sync()
            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    async def _wait_if_needed(self):
        """Wait if rate limit is exceeded (async)."""
        now = time.time()
        # Remove calls outside the time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]

        if len(self.calls) >= self.max_calls:
            sleep_time = self.time_window - (now - self.calls[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                self.calls = []

        self.calls.append(now)

    def _wait_if_needed_sync(self):
        """Wait if rate limit is exceeded (sync)."""
        now = time.time()
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]

        if len(self.calls) >= self.max_calls:
            sleep_time = self.time_window - (now - self.calls[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.calls = []

        self.calls.append(now)


class DataSource(ABC):
    """Abstract base class for data sources."""

    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """Get list of all stocks."""
        pass

    @abstractmethod
    def get_daily_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Get daily OHLCV data."""
        pass

    @abstractmethod
    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote."""
        pass

    @abstractmethod
    def get_stock_basic_info(self, symbol: str) -> Dict[str, Any]:
        """Get stock basic information."""
        pass

    @abstractmethod
    def get_financial_data(self, symbol: str) -> Dict[str, Any]:
        """Get financial metrics (PE, PB, ROE, etc.)."""
        pass


class TushareSource(DataSource):
    """Tushare Pro data source."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize Tushare source.

        Args:
            token: Tushare API token (uses settings if not provided)
        """
        self.token = token or settings.tushare_token
        if not self.token:
            raise ValueError("Tushare token not configured")

        ts.set_token(self.token)
        self.pro = ts.pro_api()
        self.rate_limiter = RateLimiter(settings.tushare_rate_limit, 60)

    @staticmethod
    def _convert_symbol(symbol: str, to_tushare: bool = True) -> str:
        """
        Convert symbol format between standard and Tushare format.

        Args:
            symbol: Stock symbol
            to_tushare: If True, convert to Tushare format (e.g., 000001.SZ)
                       If False, convert from Tushare format (e.g., 000001)

        Returns:
            Converted symbol
        """
        if to_tushare:
            if '.' in symbol:
                return symbol  # Already in Tushare format
            # Determine exchange
            if symbol.startswith('6'):
                return f"{symbol}.SH"  # Shanghai
            else:
                return f"{symbol}.SZ"  # Shenzhen
        else:
            return symbol.split('.')[0] if '.' in symbol else symbol

    def get_stock_list(self) -> pd.DataFrame:
        """Get list of all stocks."""
        try:
            self.rate_limiter._wait_if_needed_sync()
            df = self.pro.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol,name,area,industry,list_date'
            )
            logger.info(f"Retrieved {len(df)} stocks from Tushare")
            return df
        except Exception as e:
            logger.error(f"Error fetching stock list from Tushare: {e}")
            raise

    def get_daily_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Get daily OHLCV data.

        Args:
            symbol: Stock symbol (e.g., '000001' or '000001.SZ')
            start_date: Start date (YYYYMMDD or YYYY-MM-DD)
            end_date: End date (YYYYMMDD or YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
        try:
            ts_symbol = self._convert_symbol(symbol, to_tushare=True)
            start_date = start_date.replace('-', '')
            end_date = end_date.replace('-', '')

            self.rate_limiter._wait_if_needed_sync()
            df = self.pro.daily(
                ts_code=ts_symbol,
                start_date=start_date,
                end_date=end_date
            )

            if df is not None and not df.empty:
                # Rename columns to standard format
                df = df.rename(columns={
                    'trade_date': 'date',
                    'vol': 'volume'
                })
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                logger.debug(f"Retrieved {len(df)} bars for {symbol}")
                return df
            else:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching daily bars for {symbol}: {e}")
            raise

    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote (Note: Tushare has limited real-time data)."""
        try:
            ts_symbol = self._convert_symbol(symbol, to_tushare=True)
            self.rate_limiter._wait_if_needed_sync()

            # Get latest daily data (Tushare doesn't provide true real-time)
            today = datetime.now().strftime('%Y%m%d')
            df = self.pro.daily(ts_code=ts_symbol, start_date=today, end_date=today)

            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    'symbol': symbol,
                    'price': row['close'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'volume': row['vol'],
                    'timestamp': datetime.now()
                }
            else:
                raise ValueError(f"No real-time data for {symbol}")

        except Exception as e:
            logger.error(f"Error fetching real-time quote for {symbol}: {e}")
            raise

    def get_stock_basic_info(self, symbol: str) -> Dict[str, Any]:
        """Get stock basic information."""
        try:
            ts_symbol = self._convert_symbol(symbol, to_tushare=True)
            self.rate_limiter._wait_if_needed_sync()

            df = self.pro.stock_basic(ts_code=ts_symbol)

            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    'symbol': self._convert_symbol(row['ts_code'], to_tushare=False),
                    'name': row['name'],
                    'industry': row.get('industry', ''),
                    'area': row.get('area', ''),
                    'list_date': row.get('list_date', '')
                }
            else:
                raise ValueError(f"No basic info for {symbol}")

        except Exception as e:
            logger.error(f"Error fetching basic info for {symbol}: {e}")
            raise

    def get_financial_data(self, symbol: str) -> Dict[str, Any]:
        """Get financial metrics (PE, PB, ROE, etc.)."""
        try:
            ts_symbol = self._convert_symbol(symbol, to_tushare=True)
            self.rate_limiter._wait_if_needed_sync()

            # Get daily basic info (includes PE, PB)
            today = datetime.now().strftime('%Y%m%d')
            df = self.pro.daily_basic(
                ts_code=ts_symbol,
                start_date=today,
                end_date=today,
                fields='ts_code,trade_date,pe,pb,ps,dv_ratio,total_mv'
            )

            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    'symbol': symbol,
                    'pe_ratio': row.get('pe'),
                    'pb_ratio': row.get('pb'),
                    'ps_ratio': row.get('ps'),
                    'market_cap': row.get('total_mv'),
                    'timestamp': datetime.now()
                }
            else:
                logger.warning(f"No financial data for {symbol}")
                return {}

        except Exception as e:
            logger.error(f"Error fetching financial data for {symbol}: {e}")
            raise


class AkShareSource(DataSource):
    """AkShare data source."""

    def __init__(self):
        """Initialize AkShare source."""
        self.rate_limiter = RateLimiter(settings.akshare_rate_limit, 60)

    def get_stock_list(self) -> pd.DataFrame:
        """Get list of all stocks."""
        try:
            self.rate_limiter._wait_if_needed_sync()
            df = ak.stock_info_a_code_name()
            logger.info(f"Retrieved {len(df)} stocks from AkShare")
            return df
        except Exception as e:
            logger.error(f"Error fetching stock list from AkShare: {e}")
            raise

    def get_daily_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """Get daily OHLCV data."""
        try:
            self.rate_limiter._wait_if_needed_sync()
            # AkShare uses symbol without exchange suffix
            clean_symbol = symbol.split('.')[0] if '.' in symbol else symbol

            df = ak.stock_zh_a_hist(
                symbol=clean_symbol,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # Forward adjusted
            )

            if df is not None and not df.empty:
                # Rename columns to standard format
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '最高': 'high',
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '换手率': 'turnover_rate'
                })
                df['date'] = pd.to_datetime(df['date'])
                logger.debug(f"Retrieved {len(df)} bars for {symbol} from AkShare")
                return df
            else:
                logger.warning(f"No data returned for {symbol} from AkShare")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching daily bars for {symbol} from AkShare: {e}")
            raise

    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote."""
        try:
            self.rate_limiter._wait_if_needed_sync()
            df = ak.stock_zh_a_spot_em()

            # Find the stock
            clean_symbol = symbol.split('.')[0] if '.' in symbol else symbol
            stock_data = df[df['代码'] == clean_symbol]

            if not stock_data.empty:
                row = stock_data.iloc[0]
                return {
                    'symbol': symbol,
                    'price': row['最新价'],
                    'open': row['今开'],
                    'high': row['最高'],
                    'low': row['最低'],
                    'volume': row['成交量'],
                    'amount': row['成交额'],
                    'timestamp': datetime.now()
                }
            else:
                raise ValueError(f"No real-time data for {symbol}")

        except Exception as e:
            logger.error(f"Error fetching real-time quote for {symbol}: {e}")
            raise

    def get_stock_basic_info(self, symbol: str) -> Dict[str, Any]:
        """Get stock basic information."""
        try:
            self.rate_limiter._wait_if_needed_sync()
            df = ak.stock_info_a_code_name()

            clean_symbol = symbol.split('.')[0] if '.' in symbol else symbol
            stock_data = df[df['code'] == clean_symbol]

            if not stock_data.empty:
                row = stock_data.iloc[0]
                return {
                    'symbol': symbol,
                    'name': row['name']
                }
            else:
                raise ValueError(f"No basic info for {symbol}")

        except Exception as e:
            logger.error(f"Error fetching basic info for {symbol}: {e}")
            raise

    def get_financial_data(self, symbol: str) -> Dict[str, Any]:
        """Get financial metrics."""
        try:
            self.rate_limiter._wait_if_needed_sync()
            clean_symbol = symbol.split('.')[0] if '.' in symbol else symbol

            # AkShare provides individual indicator functions
            # This is a simplified implementation
            return {
                'symbol': symbol,
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"Error fetching financial data for {symbol}: {e}")
            raise


class DataSourceAggregator:
    """
    Aggregates multiple data sources with fallback logic.
    Tries Tushare first, falls back to AkShare if needed.
    """

    def __init__(self):
        """Initialize data source aggregator."""
        self.sources: List[DataSource] = []

        # Initialize Tushare if token is available
        if settings.tushare_token:
            try:
                self.sources.append(TushareSource())
                logger.info("Tushare source initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Tushare: {e}")

        # Initialize AkShare if enabled
        if settings.akshare_enabled:
            try:
                self.sources.append(AkShareSource())
                logger.info("AkShare source initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize AkShare: {e}")

        if not self.sources:
            raise ValueError("No data sources available")

    def get_daily_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Get daily OHLCV data with fallback.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with OHLCV data
        """
        for source in self.sources:
            try:
                df = source.get_daily_bars(symbol, start_date, end_date)
                if df is not None and not df.empty:
                    logger.debug(f"Successfully retrieved data from {source.__class__.__name__}")
                    return df
            except Exception as e:
                logger.warning(f"Failed to get data from {source.__class__.__name__}: {e}")
                continue

        raise ValueError(f"Failed to get daily bars for {symbol} from all sources")

    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time quote with fallback."""
        for source in self.sources:
            try:
                data = source.get_realtime_quote(symbol)
                if data:
                    logger.debug(f"Successfully retrieved quote from {source.__class__.__name__}")
                    return data
            except Exception as e:
                logger.warning(f"Failed to get quote from {source.__class__.__name__}: {e}")
                continue

        raise ValueError(f"Failed to get real-time quote for {symbol} from all sources")

    def get_stock_basic_info(self, symbol: str) -> Dict[str, Any]:
        """Get stock basic info with fallback."""
        for source in self.sources:
            try:
                data = source.get_stock_basic_info(symbol)
                if data:
                    logger.debug(f"Successfully retrieved info from {source.__class__.__name__}")
                    return data
            except Exception as e:
                logger.warning(f"Failed to get info from {source.__class__.__name__}: {e}")
                continue

        raise ValueError(f"Failed to get basic info for {symbol} from all sources")

    def get_financial_data(self, symbol: str) -> Dict[str, Any]:
        """Get financial data with fallback."""
        for source in self.sources:
            try:
                data = source.get_financial_data(symbol)
                if data:
                    logger.debug(f"Successfully retrieved financial data from {source.__class__.__name__}")
                    return data
            except Exception as e:
                logger.warning(f"Failed to get financial data from {source.__class__.__name__}: {e}")
                continue

        raise ValueError(f"Failed to get financial data for {symbol} from all sources")


# Global data source instance
data_source = DataSourceAggregator()
