"""
Real-Time Market Data Feed

提供实时市场数据获取功能，支持：
- 实时行情数据获取
- 数据缓存机制
- API限流处理
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class RealTimeMarketFeed:
    """实时市场数据源

    支持从多个数据源获取实时行情数据，并提供缓存机制。
    """

    def __init__(self, provider: str = 'tushare', cache_ttl: int = 60):
        """
        初始化实时市场数据源

        Args:
            provider: 数据提供商 ('tushare', 'akshare', 'yfinance')
            cache_ttl: 缓存有效期（秒），默认60秒
        """
        self.provider = provider
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, Dict] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.request_count = 0
        self.last_request_time = time.time()

        # API限流配置（每分钟最多请求数）
        self.rate_limit = 60

        logger.info(f" RealTimeMarketFeed initialized (provider={provider}, cache_ttl={cache_ttl}s)")

    def _check_rate_limit(self):
        """检查API限流"""
        current_time = time.time()
        time_diff = current_time - self.last_request_time

        # 每分钟重置计数
        if time_diff >= 60:
            self.request_count = 0
            self.last_request_time = current_time

        # 检查是否超过限制
        if self.request_count >= self.rate_limit:
            wait_time = 60 - time_diff
            if wait_time > 0:
                logger.warning(f"⏳ Rate limit reached, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                self.request_count = 0
                self.last_request_time = time.time()

        self.request_count += 1

    def _is_cache_valid(self, symbol: str) -> bool:
        """检查缓存是否有效"""
        if symbol not in self.cache:
            return False

        cache_time = self.cache_timestamps.get(symbol)
        if cache_time is None:
            return False

        age = (datetime.now() - cache_time).total_seconds()
        return age < self.cache_ttl

    def get_realtime_data(self, symbol: str) -> Optional[Dict]:
        """
        获取实时行情数据（同步版本）

        Args:
            symbol: 股票代码（如'600519.SH'）

        Returns:
            包含实时行情的字典，格式：
            {
                'symbol': str,
                'price': float,      # 当前价
                'open': float,       # 开盘价
                'high': float,       # 最高价
                'low': float,        # 最低价
                'volume': int,       # 成交量
                'amount': float,     # 成交额
                'bid_price': float,  # 买一价
                'ask_price': float,  # 卖一价
                'timestamp': str     # 时间戳
            }
        """
        # 检查缓存
        if self._is_cache_valid(symbol):
            logger.debug(f" Using cached data for {symbol}")
            return self.cache[symbol]

        # 检查限流
        self._check_rate_limit()

        try:
            # 获取实时数据
            data = self._fetch_realtime_data(symbol)

            if data:
                # 更新缓存
                self.cache[symbol] = data
                self.cache_timestamps[symbol] = datetime.now()
                logger.debug(f" Fetched realtime data for {symbol}: ¥{data.get('price', 0):.2f}")
                return data
            else:
                logger.warning(f" No data returned for {symbol}")
                return None

        except Exception as e:
            logger.error(f" Error fetching realtime data for {symbol}: {e}")
            return None

    def _fetch_realtime_data(self, symbol: str) -> Optional[Dict]:
        """
        从数据源获取实时数据（内部方法）

        Args:
            symbol: 股票代码

        Returns:
            实时行情数据
        """
        try:
            if self.provider == 'tushare':
                return self._fetch_from_tushare(symbol)
            elif self.provider == 'akshare':
                return self._fetch_from_akshare(symbol)
            elif self.provider == 'yfinance':
                return self._fetch_from_yfinance(symbol)
            else:
                logger.error(f" Unsupported provider: {self.provider}")
                return None
        except Exception as e:
            logger.error(f" _fetch_realtime_data error: {e}")
            return None

    def _fetch_from_tushare(self, symbol: str) -> Optional[Dict]:
        """从Tushare获取实时数据"""
        try:
            # 这里应该调用实际的Tushare API
            # 为了演示，返回模拟数据
            import random
            base_price = 100.0

            return {
                'symbol': symbol,
                'price': base_price + random.uniform(-5, 5),
                'open': base_price + random.uniform(-3, 3),
                'high': base_price + random.uniform(0, 5),
                'low': base_price + random.uniform(-5, 0),
                'volume': random.randint(1000000, 10000000),
                'amount': random.uniform(100000000, 1000000000),
                'bid_price': base_price - 0.01,
                'ask_price': base_price + 0.01,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f" Tushare fetch error: {e}")
            return None

    def _fetch_from_akshare(self, symbol: str) -> Optional[Dict]:
        """从AkShare获取实时数据"""
        try:
            import akshare as ak

            # 转换股票代码格式
            code = symbol.split('.')[0]

            # 获取实时数据
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == code]

            if stock_data.empty:
                return None

            row = stock_data.iloc[0]
            return {
                'symbol': symbol,
                'price': float(row['最新价']),
                'open': float(row['今开']),
                'high': float(row['最高']),
                'low': float(row['最低']),
                'volume': int(row['成交量']),
                'amount': float(row['成交额']),
                'bid_price': float(row['最新价']) - 0.01,
                'ask_price': float(row['最新价']) + 0.01,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f" AkShare fetch error: {e}")
            return None

    def _fetch_from_yfinance(self, symbol: str) -> Optional[Dict]:
        """从yfinance获取实时数据"""
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                'symbol': symbol,
                'price': info.get('currentPrice', 0),
                'open': info.get('open', 0),
                'high': info.get('dayHigh', 0),
                'low': info.get('dayLow', 0),
                'volume': info.get('volume', 0),
                'amount': info.get('volume', 0) * info.get('currentPrice', 0),
                'bid_price': info.get('bid', 0),
                'ask_price': info.get('ask', 0),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f" yfinance fetch error: {e}")
            return None

    async def get_realtime_data_async(self, symbol: str) -> Optional[Dict]:
        """
        异步获取实时行情数据

        Args:
            symbol: 股票代码

        Returns:
            实时行情数据
        """
        # 在事件循环中运行同步方法
        return await asyncio.to_thread(self.get_realtime_data, symbol)

    def subscribe(self, symbols: List[str]):
        """
        订阅实时行情（WebSocket方式）

        Args:
            symbols: 股票代码列表

        Note:
            此功能需要WebSocket支持，当前为占位实现
        """
        logger.warning(" WebSocket subscription not implemented yet")
        logger.info(f" Would subscribe to: {symbols}")

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info(" Cache cleared")

    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息

        Returns:
            缓存统计字典
        """
        return {
            'cache_size': len(self.cache),
            'symbols': list(self.cache.keys()),
            'request_count': self.request_count,
            'rate_limit': self.rate_limit
        }
