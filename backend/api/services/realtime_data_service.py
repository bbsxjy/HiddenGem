"""
Real-time Stock Data Service using MiniShare

提供实时股票行情数据
使用 MiniShare SDK（更稳定、更快速）
"""

import minishare as ms
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import logging
import os
import time

logger = logging.getLogger(__name__)

# MiniShare Token
MINISHARE_TOKEN = "8iSkc52Xim6EFhTZmr2Ptt3oCFd47GtNy00v0SETk9mDFC5tHCgzrVUneb60d394"


def retry_on_connection_error(max_retries=3, delay=1, backoff=2):
    """
    重试装饰器，用于处理网络连接错误

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟时间的倍增系数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retry_delay = delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    # 只重试连接相关的错误
                    if any(keyword in error_msg for keyword in ['connection', 'timeout', 'network', 'proxy']):
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"连接失败 (尝试 {attempt + 1}/{max_retries}): {e}, "
                                f"{retry_delay}秒后重试..."
                            )
                            time.sleep(retry_delay)
                            retry_delay *= backoff
                            continue
                    # 非连接错误或最后一次尝试失败，直接抛出
                    raise
            return None
        return wrapper
    return decorator


class RealtimeDataService:
    """实时数据服务（基于 MiniShare SDK）"""

    def __init__(self):
        self.cache = {}  # 简单的内存缓存
        self.cache_ttl = 30  # 缓存30秒（MiniShare官方：30秒更新一次）
        self.api = ms.pro_api(MINISHARE_TOKEN)
        self._full_data_cache = None  # 全量数据缓存
        self._full_data_cache_time = None  # 全量数据缓存时间
        logger.info("MiniShare 实时数据服务已初始化")

    @retry_on_connection_error(max_retries=3, delay=1, backoff=2)
    def _fetch_all_stocks_data(self) -> Optional[pd.DataFrame]:
        """
        获取所有A股实时行情（使用 MiniShare SDK）
        带缓存，避免频繁调用API

        Returns:
            DataFrame 或 None
        """
        # 检查缓存
        if self._full_data_cache is not None and self._full_data_cache_time is not None:
            elapsed = (datetime.now() - self._full_data_cache_time).seconds
            if elapsed < self.cache_ttl:
                logger.debug(f"使用全量数据缓存（已缓存 {elapsed} 秒）")
                return self._full_data_cache

        try:
            # 获取所有A股数据（包括主板、创业板、科创板）
            # 使用通配符获取所有市场
            logger.info("📡 从 MiniShare 获取全量实时行情...")

            # 分别获取深圳和上海的股票
            df_sz = self.api.rt_k_ms(ts_code='*.SZ')  # 深圳：主板0、创业板3
            df_sh = self.api.rt_k_ms(ts_code='*.SH')  # 上海：主板6、科创板688

            # 合并数据
            df = pd.concat([df_sz, df_sh], ignore_index=True)

            logger.info(f"✅ 成功获取 {len(df)} 只股票的实时行情（深圳：{len(df_sz)}，上海：{len(df_sh)}）")

            # 更新缓存
            self._full_data_cache = df
            self._full_data_cache_time = datetime.now()

            return df

        except Exception as e:
            logger.error(f"❌ MiniShare API 调用失败: {e}")
            raise  # 让重试装饰器处理

    def _convert_minishare_to_standard_format(self, row: pd.Series, symbol: str) -> Dict:
        """
        将 MiniShare 数据格式转换为标准格式

        Args:
            row: MiniShare 返回的数据行
            symbol: 原始股票代码（可能包含后缀）

        Returns:
            标准格式的行情字典
        """
        try:
            return {
                "symbol": symbol,
                "name": row['name'],
                "price": float(row['close']),  # MiniShare 用 close 表示当前价
                "change": float(row['pct_chg']),  # 涨跌幅（%）
                "change_amount": float(row['change']),  # 涨跌额
                "volume": int(row['vol']),  # 成交量（手）
                "turnover": int(row['amount']),  # 成交额（元）
                "amplitude": float(row['high'] - row['low']) / float(row['pre_close']) * 100 if row['pre_close'] > 0 else 0,  # 振幅
                "high": float(row['high']),
                "low": float(row['low']),
                "open": float(row['open']),
                "prev_close": float(row['pre_close']),
                "volume_ratio": float(row.get('volume_ratio', 0)),
                "turnover_rate": float(row.get('turnover_rate', 0)),
                "pe_ratio": float(row.get('pe_ttm', 0)),  # 市盈率
                "pb_ratio": float(row.get('pb', 0)),  # 市净率
                "total_market_cap": 0,  # MiniShare 不提供，设为0
                "circulation_market_cap": 0,  # MiniShare 不提供，设为0
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"数据转换失败: {e}, row={row.to_dict()}")
            raise

    def get_realtime_quote(self, symbol: str) -> Optional[Dict]:
        """
        获取股票实时行情（单只股票）
        建议使用 get_batch_quotes() 批量获取以提高效率

        Args:
            symbol: 股票代码，如 "000001", "600519", "300502" 或 "000001.SZ"

        Returns:
            实时行情数据字典
        """
        try:
            # 移除后缀（如果有），获取纯代码
            clean_symbol = symbol.split('.')[0]

            # 检查单只股票缓存
            cache_key = f"quote_{clean_symbol}"
            if cache_key in self.cache:
                cached_data, cached_time = self.cache[cache_key]
                if (datetime.now() - cached_time).seconds < self.cache_ttl:
                    logger.debug(f"✓ 使用缓存数据: {symbol}")
                    return cached_data

            # 获取实时行情（会使用全量数据缓存）
            df = self._fetch_all_stocks_data()

            if df is None or df.empty:
                logger.warning(f"❌ 无法获取实时行情数据")
                return None

            # 查找对应股票（MiniShare 用 symbol 字段存储纯代码）
            stock_data = df[df['symbol'] == clean_symbol]

            if stock_data.empty:
                logger.warning(f"⚠️ 股票 {symbol} 未找到行情数据")
                return None

            row = stock_data.iloc[0]

            # 转换为标准格式
            quote = self._convert_minishare_to_standard_format(row, symbol)

            # 更新缓存
            self.cache[cache_key] = (quote, datetime.now())
            logger.debug(f"✓ 成功获取 {symbol} 实时行情: 价格={quote['price']}, 涨跌幅={quote['change']}%")

            return quote

        except Exception as e:
            logger.error(f"❌ 获取 {symbol} 实时行情失败: {e}")
            return None

    def get_batch_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        批量获取实时行情（优化版：一次获取所有数据，带缓存）

        Args:
            symbols: 股票代码列表

        Returns:
            {symbol: quote_data} 字典
        """
        results = {}

        try:
            # 一次性获取所有股票数据（会使用缓存）
            df = self._fetch_all_stocks_data()

            if df is None or df.empty:
                logger.warning("❌ 批量获取失败：无法获取实时行情数据")
                return results

            # 为每个股票代码提取数据
            for symbol in symbols:
                clean_symbol = symbol.split('.')[0]

                # 从DataFrame中查找（MiniShare 用 symbol 字段）
                stock_data = df[df['symbol'] == clean_symbol]

                if not stock_data.empty:
                    row = stock_data.iloc[0]

                    # 转换为标准格式
                    quote = self._convert_minishare_to_standard_format(row, symbol)

                    # 更新单只股票缓存（用于直接调用 get_realtime_quote 的场景）
                    cache_key = f"quote_{clean_symbol}"
                    self.cache[cache_key] = (quote, datetime.now())
                    results[symbol] = quote
                else:
                    logger.warning(f"⚠️ 股票 {symbol} 未找到行情数据")

            logger.info(f"✅ 批量获取成功：{len(results)}/{len(symbols)} 只股票")

        except Exception as e:
            logger.error(f"❌ 批量获取实时行情失败: {e}")

        return results

    def is_trading_hours(self) -> bool:
        """
        检查当前是否在交易时间

        Returns:
            True if within trading hours
        """
        now = datetime.now()
        current_time = now.time()

        # 排除周末
        if now.weekday() >= 5:  # 5=周六, 6=周日
            return False

        # 交易时间：9:30-11:30, 13:00-15:00
        morning_start = datetime.strptime("09:30", "%H:%M").time()
        morning_end = datetime.strptime("11:30", "%H:%M").time()
        afternoon_start = datetime.strptime("13:00", "%H:%M").time()
        afternoon_end = datetime.strptime("15:00", "%H:%M").time()

        is_morning = morning_start <= current_time <= morning_end
        is_afternoon = afternoon_start <= current_time <= afternoon_end

        return is_morning or is_afternoon

    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码

        Returns:
            股票基本信息
        """
        try:
            clean_symbol = symbol.split('.')[0]

            # 使用 akshare 获取股票信息
            info_df = ak.stock_individual_info_em(symbol=clean_symbol)

            if info_df.empty:
                return None

            # 转换为字典
            info_dict = dict(zip(info_df['item'], info_df['value']))

            return {
                "symbol": symbol,
                "name": info_dict.get('股票简称', ''),
                "industry": info_dict.get('行业', ''),
                "listing_date": info_dict.get('上市时间', ''),
                "total_share_capital": info_dict.get('总股本', ''),
                "circulation_share_capital": info_dict.get('流通股', ''),
            }

        except Exception as e:
            logger.error(f"Error fetching stock info for {symbol}: {e}")
            return None


# 创建全局单例
realtime_data_service = RealtimeDataService()
