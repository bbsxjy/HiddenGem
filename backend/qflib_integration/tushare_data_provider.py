"""
Tushare Data Provider for QF-Lib

将Tushare数据源适配到QF-Lib的数据接口
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np
import logging

# QF-Lib imports (note: package name is qf_lib with underscore)
try:
    from qf_lib.data_providers.abstract_price_data_provider import AbstractPriceDataProvider
    from qf_lib.common.tickers.tickers import Ticker
    from qf_lib.containers.qf_data_array import QFDataArray
    from qf_lib.containers.dataframe.qf_dataframe import QFDataFrame
    from qf_lib.common.enums.price_field import PriceField
except ImportError:
    # 如果QF-Lib未安装，使用占位符
    AbstractPriceDataProvider = object
    Ticker = str
    QFDataArray = None
    QFDataFrame = pd.DataFrame
    PriceField = None

import tushare as ts

logger = logging.getLogger(__name__)


class TushareDataProvider(AbstractPriceDataProvider if AbstractPriceDataProvider != object else object):
    """Tushare数据源适配器（A股）

    将Tushare Pro数据接口适配到QF-Lib的AbstractPriceDataProvider接口，
    用于QF-Lib的事件驱动回测。

    Features:
        -  天然防护Look-Ahead Bias（只返回历史数据）
        -  支持A股数据（日线、周线、月线）
        -  缓存机制（避免重复请求）
        -  运行时检查（禁止访问未来数据）
    """

    def __init__(self, tushare_token: str):
        """初始化Tushare数据提供者

        Args:
            tushare_token: Tushare Pro API Token
        """
        super().__init__()
        self.pro = ts.pro_api(tushare_token)
        self._cache: Dict[str, pd.DataFrame] = {}
        self._current_time: Optional[datetime] = None

        logger.info(" TushareDataProvider initialized")

    def set_current_time(self, current_time: datetime):
        """设置当前回测时间（用于Look-Ahead检查）

        Args:
            current_time: 当前回测时间点
        """
        self._current_time = current_time
        logger.debug(f" Current backtest time set to: {current_time}")

    def get_price(
        self,
        tickers: Union[Ticker, List[Ticker]],
        fields: Union[PriceField, List[PriceField], str, List[str]],
        start_date: datetime,
        end_date: datetime,
        frequency: str = 'D'
    ) -> Union[pd.DataFrame, pd.Series, float]:
        """获取历史价格数据（QF-Lib标准接口）

        Args:
            tickers: 股票代码（Ticker对象或字符串）
            fields: 字段名称（close, open, high, low, volume等）
            start_date: 开始日期
            end_date: 结束日期
            frequency: 频率（'D'=日线, 'W'=周线, 'M'=月线）

        Returns:
            价格数据（DataFrame、Series或float）

        Raises:
            LookAheadBiasError: 如果尝试访问未来数据
        """
        #  Look-Ahead检查
        if self._current_time and end_date > self._current_time:
            error_msg = (
                f" Look-Ahead Bias Detected!\n"
                f"   Attempted to access future data:\n"
                f"   - Requested end_date: {end_date}\n"
                f"   - Current backtest time: {self._current_time}\n"
                f"   This would cause Look-Ahead Bias!"
            )
            logger.error(error_msg)
            raise LookAheadBiasError(error_msg)

        # 标准化输入
        if not isinstance(tickers, list):
            tickers = [tickers]
        if not isinstance(fields, list):
            fields = [fields]

        # 转换Ticker对象为字符串
        tickers_str = [self._ticker_to_ts_code(t) for t in tickers]

        # 获取数据
        result_dict = {}
        for ticker_str in tickers_str:
            df = self._fetch_ticker_data(ticker_str, start_date, end_date, frequency)

            # 提取指定字段
            for field in fields:
                field_name = self._field_to_column(field)
                if field_name in df.columns:
                    key = (ticker_str, field)
                    result_dict[key] = df[field_name]

        # 格式化输出
        if len(tickers) == 1 and len(fields) == 1:
            # 单个ticker和单个field：返回Series
            ticker_str = tickers_str[0]
            field_name = self._field_to_column(fields[0])
            return result_dict.get((ticker_str, fields[0]), pd.Series())
        elif len(tickers) == 1 and len(fields) > 1:
            # 单个ticker和多个field：返回DataFrame，列名为field名称（不含ticker）
            ticker_str = tickers_str[0]
            simple_dict = {}
            for field in fields:
                field_name = self._field_to_column(field)
                key = (ticker_str, field)
                if key in result_dict:
                    simple_dict[field_name] = result_dict[key]
            df = pd.DataFrame(simple_dict)
            df.index.name = 'date'
            return df
        else:
            # 多个ticker：返回DataFrame，列名为(ticker, field)元组
            df = pd.DataFrame(result_dict)
            df.index.name = 'date'
            return df

    def get_last_available_price(
        self,
        tickers: Union[Ticker, List[Ticker]],
        frequency: str = 'D'
    ) -> Union[float, pd.Series]:
        """获取最后可用价格

        Args:
            tickers: 股票代码
            frequency: 频率

        Returns:
            最后可用的收盘价
        """
        if not isinstance(tickers, list):
            tickers = [tickers]

        prices = {}
        for ticker in tickers:
            # 获取最近30天的数据（确保有可用数据）
            end_date = self._current_time if self._current_time else datetime.now()
            start_date = end_date - timedelta(days=30)

            df = self._fetch_ticker_data(
                self._ticker_to_ts_code(ticker),
                start_date,
                end_date,
                frequency
            )

            if not df.empty:
                prices[ticker] = df['close'].iloc[-1]
            else:
                prices[ticker] = np.nan

        if len(tickers) == 1:
            return prices[tickers[0]]
        else:
            return pd.Series(prices)

    def _fetch_ticker_data(
        self,
        ts_code: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = 'D'
    ) -> pd.DataFrame:
        """从Tushare获取单个股票数据（带缓存）

        Args:
            ts_code: Tushare股票代码（如 000001.SZ）
            start_date: 开始日期
            end_date: 结束日期
            frequency: 频率

        Returns:
            价格数据DataFrame
        """
        # 生成缓存键
        cache_key = f"{ts_code}_{start_date.date()}_{end_date.date()}_{frequency}"

        # 检查缓存
        if cache_key in self._cache:
            logger.debug(f" Cache hit: {cache_key}")
            return self._cache[cache_key]

        # 从Tushare获取数据
        try:
            df = self.pro.daily(
                ts_code=ts_code,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )

            if df.empty:
                logger.warning(f" No data for {ts_code} from {start_date} to {end_date}")
                return pd.DataFrame()

            # 数据处理
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date')
            df = df.set_index('trade_date')

            # 重命名列（Tushare -> QF-Lib标准）
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume',  # Tushare的vol单位是手（100股）
                'amount': 'amount'  # 成交额（千元）
            })

            # 缓存数据
            self._cache[cache_key] = df

            logger.debug(f" Fetched {len(df)} rows for {ts_code}")
            return df

        except Exception as e:
            logger.error(f" Error fetching data for {ts_code}: {e}")
            return pd.DataFrame()

    def _ticker_to_ts_code(self, ticker: Union[Ticker, str]) -> str:
        """将Ticker对象转换为Tushare代码

        Args:
            ticker: Ticker对象或字符串

        Returns:
            Tushare股票代码（如 000001.SZ）
        """
        if isinstance(ticker, str):
            ticker_str = ticker
        else:
            # Ticker对象，提取ticker属性
            ticker_str = ticker.ticker if hasattr(ticker, 'ticker') else str(ticker)

        # 如果已经包含交易所后缀，直接返回
        if '.' in ticker_str:
            return ticker_str

        # 根据股票代码自动添加交易所后缀
        # A股代码规则：
        # - 000xxx, 001xxx, 002xxx, 003xxx (深圳主板/中小板) → .SZ
        # - 300xxx (创业板 ChiNext) → .SZ
        # - 600xxx, 601xxx, 603xxx, 605xxx (上海主板) → .SH
        # - 688xxx (科创板 STAR Market) → .SH
        if ticker_str.startswith(('000', '001', '002', '003', '300')):
            return f"{ticker_str}.SZ"
        elif ticker_str.startswith(('600', '601', '603', '605', '688')):
            return f"{ticker_str}.SH"
        else:
            # 未知格式，返回原始字符串（可能已经是正确格式或是其他市场）
            return ticker_str

    def _field_to_column(self, field: Union[str, 'PriceField']) -> str:
        """将PriceField枚举转换为列名

        Args:
            field: 字段名称或PriceField枚举

        Returns:
            列名
        """
        if isinstance(field, str):
            return field.lower()

        # PriceField枚举映射
        field_mapping = {
            'OPEN': 'open',
            'HIGH': 'high',
            'LOW': 'low',
            'CLOSE': 'close',
            'VOLUME': 'volume',
        }

        field_name = str(field).split('.')[-1]  # PriceField.CLOSE -> 'CLOSE'
        return field_mapping.get(field_name, field_name.lower())

    # ==================== Abstract Methods (Required by QF-Lib 4.0.4) ====================

    def get_history(
        self,
        tickers: Union[Ticker, List[Ticker]],
        fields: Union[PriceField, List[PriceField], str, List[str]],
        start_date: datetime,
        end_date: datetime,
        frequency: str = 'D',
        **kwargs
    ) -> Union[QFDataFrame, pd.DataFrame, pd.Series]:
        """Get historical data (required abstract method)

        This is an alias for get_price() to match QF-Lib 4.0.4's DataProvider interface.

        Args:
            tickers: Stock ticker(s)
            fields: Price field(s) to retrieve
            start_date: Start date
            end_date: End date
            frequency: Data frequency ('D' for daily)
            **kwargs: Additional arguments

        Returns:
            Historical price data
        """
        return self.get_price(tickers, fields, start_date, end_date, frequency)

    @property
    def price_field_to_str_map(self) -> Dict[PriceField, str]:
        """Map PriceField enum to string column names (required abstract property)

        Returns:
            Dictionary mapping PriceField to column names
        """
        if PriceField is None:
            # QF-Lib not installed, return empty dict
            return {}

        return {
            PriceField.Open: 'open',
            PriceField.High: 'high',
            PriceField.Low: 'low',
            PriceField.Close: 'close',
            PriceField.Volume: 'volume',
        }

    @property
    def supported_ticker_types(self) -> List[type]:
        """Return list of supported ticker types (required abstract property)

        Returns:
            List of ticker types this provider supports (A-share tickers)
        """
        # Support generic Ticker class from QF-Lib
        if Ticker == str:
            # QF-Lib not installed
            return [str]
        return [Ticker]


class LookAheadBiasError(Exception):
    """Look-Ahead Bias错误

    当尝试访问未来数据时抛出此异常
    """
    pass
