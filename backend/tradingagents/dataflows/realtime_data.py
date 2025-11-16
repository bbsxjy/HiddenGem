#!/usr/bin/env python3
"""
实时行情数据获取模块
使用AKShare获取A股实时报价，解决历史数据与实时数据混淆问题
"""

import time
from datetime import datetime
from typing import Dict, Optional, Any
import pandas as pd

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')


class RealtimeDataProvider:
    """实时行情数据提供器（基于AKShare）"""

    def __init__(self):
        self.last_api_call = 0
        self.min_api_interval = 1.0  # AKShare实时数据调用间隔

        # 检查AKShare是否可用
        try:
            import akshare as ak
            self.ak = ak
            self.available = True
            logger.info(" 实时行情模块初始化成功（AKShare）")
        except ImportError:
            self.ak = None
            self.available = False
            logger.error(" AKShare未安装，实时行情功能不可用")

    def _wait_for_rate_limit(self):
        """等待API调用间隔"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call

        if time_since_last_call < self.min_api_interval:
            wait_time = self.min_api_interval - time_since_last_call
            time.sleep(wait_time)

        self.last_api_call = time.time()

    def get_realtime_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取A股实时报价

        Args:
            symbol: 股票代码（6位数字，如：000001）

        Returns:
            Dict: 实时报价数据，格式：
            {
                'symbol': '000001',
                'name': '平安银行',
                'current_price': 15.23,
                'open_price': 15.10,
                'high_price': 15.50,
                'low_price': 15.05,
                'prev_close': 15.20,
                'change': 0.03,
                'change_pct': 0.20,
                'volume': 123456789,
                'amount': 1876543210.50,
                'timestamp': '2025-01-07 14:30:00',
                'is_realtime': True,
                'data_source': 'akshare_realtime'
            }
        """
        if not self.available:
            logger.error(" 实时行情功能不可用（AKShare未安装）")
            return None

        try:
            logger.info(f" 获取{symbol}实时报价...")

            # API限制处理
            self._wait_for_rate_limit()

            # 使用AKShare获取实时行情
            # 注意：股票代码需要带市场前缀（如：sz000001, sh600036）
            market_symbol = self._format_symbol_for_akshare(symbol)

            # 获取实时行情（使用东方财富接口）
            df = self.ak.stock_zh_a_spot_em()

            # 筛选目标股票
            stock_data = df[df['代码'] == symbol]

            if stock_data.empty:
                logger.warning(f" 未找到{symbol}的实时行情")
                return None

            # 提取数据
            row = stock_data.iloc[0]

            realtime_quote = {
                'symbol': symbol,
                'name': row.get('名称', f'股票{symbol}'),
                'current_price': float(row.get('最新价', 0)),
                'open_price': float(row.get('今开', 0)),
                'high_price': float(row.get('最高', 0)),
                'low_price': float(row.get('最低', 0)),
                'prev_close': float(row.get('昨收', 0)),
                'change': float(row.get('涨跌额', 0)),
                'change_pct': float(row.get('涨跌幅', 0)),
                'volume': float(row.get('成交量', 0)),
                'amount': float(row.get('成交额', 0)),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_realtime': True,
                'data_source': 'akshare_realtime'
            }

            logger.info(f" {symbol} 实时报价获取成功: ¥{realtime_quote['current_price']} "
                       f"({realtime_quote['change_pct']:+.2f}%)")

            return realtime_quote

        except Exception as e:
            logger.error(f" 获取{symbol}实时报价失败: {e}")
            return None

    def get_market_snapshot(self, symbol: str, lookback_days: int = 5) -> Optional[str]:
        """
        获取市场快照（实时报价 + 最近历史数据）

        Args:
            symbol: 股票代码
            lookback_days: 回看天数（用于技术分析）

        Returns:
            str: 格式化的市场快照报告
        """
        try:
            logger.info(f" 获取{symbol}市场快照（实时+最近{lookback_days}天）...")

            # 1. 获取实时报价
            realtime_quote = self.get_realtime_quote(symbol)

            if not realtime_quote:
                return f" 无法获取{symbol}的实时行情"

            # 2. 获取最近历史数据（用于对比）
            from .data_source_manager import get_data_source_manager
            from datetime import timedelta

            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days + 10)  # 多取一些，确保有足够交易日

            manager = get_data_source_manager()
            historical_data = manager.get_stock_data(
                symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            # 3. 生成市场快照报告
            report = self._format_market_snapshot(realtime_quote, historical_data, lookback_days)

            logger.info(f" {symbol}市场快照生成成功")
            return report

        except Exception as e:
            logger.error(f" 获取{symbol}市场快照失败: {e}")
            return f" 获取{symbol}市场快照失败: {e}"

    def _format_symbol_for_akshare(self, symbol: str) -> str:
        """
        格式化股票代码为AKShare格式

        Args:
            symbol: 6位股票代码（如：000001）

        Returns:
            str: AKShare格式代码（如：sz000001, sh600036）
        """
        if symbol.startswith('6'):
            return f"sh{symbol}"
        else:
            return f"sz{symbol}"

    def _format_market_snapshot(self, realtime_quote: Dict, historical_data: str, lookback_days: int) -> str:
        """格式化市场快照报告"""

        report = f"""#  {realtime_quote['name']}({realtime_quote['symbol']}) - 市场快照

##  实时行情（{realtime_quote['timestamp']}）

** 重要：以下是实时数据，非历史数据！**

- **当前价格**: ¥{realtime_quote['current_price']:.2f}
- **涨跌额**: {realtime_quote['change']:+.2f}元
- **涨跌幅**: {realtime_quote['change_pct']:+.2f}%
- **今日开盘**: ¥{realtime_quote['open_price']:.2f}
- **今日最高**: ¥{realtime_quote['high_price']:.2f} ⬆
- **今日最低**: ¥{realtime_quote['low_price']:.2f} ⬇
- **昨日收盘**: ¥{realtime_quote['prev_close']:.2f}
- **成交量**: {realtime_quote['volume']:,.0f} 股
- **成交额**: ¥{realtime_quote['amount']:,.2f} 元

---

##  价格区间对比

** 注意区分实时价格与历史价格：**

| 指标 | 实时数据（今日） | 最近{lookback_days}天历史 |
|------|----------------|---------------------|
| 最高价 | ¥{realtime_quote['high_price']:.2f}（今日最高） | 见下方历史数据 |
| 最低价 | ¥{realtime_quote['low_price']:.2f}（今日最低） | 见下方历史数据 |
| 收盘价 | ¥{realtime_quote['current_price']:.2f}（当前价，盘中） | 见下方历史数据 |

---

##  最近{lookback_days}天历史数据（用于技术分析）

{historical_data}

---

##  数据说明

1. **实时数据来源**: AKShare东方财富接口（实时更新，延迟<1分钟）
2. **历史数据来源**: TuShare/AKShare（交易日收盘后更新）
3. **数据时间戳**: {realtime_quote['timestamp']}
4. **数据状态**: {' 实时（盘中）' if self._is_trading_time() else ' 非交易时间（显示最近收盘价）'}

---

** LLM分析提示**：
- 今日最高价 ¥{realtime_quote['high_price']:.2f} 和今日最低价 ¥{realtime_quote['low_price']:.2f} 是**今天**的价格，不是历史最高/最低！
- 当前价格 ¥{realtime_quote['current_price']:.2f} 是**实时价格**（或最近收盘价），请勿与历史数据混淆
- 进行技术分析时，请使用上方"最近{lookback_days}天历史数据"部分的数据

**数据生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report

    def _is_trading_time(self) -> bool:
        """判断当前是否为交易时间"""
        now = datetime.now()

        # 周末不交易
        if now.weekday() >= 5:  # 5=周六, 6=周日
            return False

        # 交易时间: 9:30-11:30, 13:00-15:00
        current_time = now.time()
        morning_start = datetime.strptime('09:30', '%H:%M').time()
        morning_end = datetime.strptime('11:30', '%H:%M').time()
        afternoon_start = datetime.strptime('13:00', '%H:%M').time()
        afternoon_end = datetime.strptime('15:00', '%H:%M').time()

        if morning_start <= current_time <= morning_end:
            return True
        if afternoon_start <= current_time <= afternoon_end:
            return True

        return False

    def get_batch_realtime_quotes(self, symbols: list) -> Dict[str, Dict]:
        """
        批量获取实时报价

        Args:
            symbols: 股票代码列表

        Returns:
            Dict: {symbol: quote_data}
        """
        try:
            logger.info(f" 批量获取{len(symbols)}只股票的实时报价...")

            # 获取全市场实时行情
            self._wait_for_rate_limit()
            df = self.ak.stock_zh_a_spot_em()

            # 筛选目标股票
            target_symbols = set(symbols)
            filtered_df = df[df['代码'].isin(target_symbols)]

            # 转换为字典格式
            quotes = {}
            for _, row in filtered_df.iterrows():
                symbol = row['代码']
                quotes[symbol] = {
                    'symbol': symbol,
                    'name': row.get('名称', f'股票{symbol}'),
                    'current_price': float(row.get('最新价', 0)),
                    'change_pct': float(row.get('涨跌幅', 0)),
                    'volume': float(row.get('成交量', 0)),
                    'amount': float(row.get('成交额', 0)),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'is_realtime': True,
                    'data_source': 'akshare_realtime'
                }

            logger.info(f" 批量获取成功，共{len(quotes)}只股票")
            return quotes

        except Exception as e:
            logger.error(f" 批量获取实时报价失败: {e}")
            return {}


# 全局实例
_realtime_provider = None

def get_realtime_data_provider() -> RealtimeDataProvider:
    """获取全局实时数据提供器实例"""
    global _realtime_provider
    if _realtime_provider is None:
        _realtime_provider = RealtimeDataProvider()
    return _realtime_provider


# 便捷函数

def get_realtime_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取A股实时报价（便捷函数）

    Args:
        symbol: 股票代码（6位数字）

    Returns:
        Dict: 实时报价数据
    """
    provider = get_realtime_data_provider()
    return provider.get_realtime_quote(symbol)


def get_market_snapshot(symbol: str, lookback_days: int = 5) -> str:
    """
    获取市场快照（实时+历史，便捷函数）

    Args:
        symbol: 股票代码
        lookback_days: 回看天数

    Returns:
        str: 市场快照报告
    """
    provider = get_realtime_data_provider()
    return provider.get_market_snapshot(symbol, lookback_days)


def get_batch_realtime_quotes(symbols: list) -> Dict[str, Dict]:
    """
    批量获取实时报价（便捷函数）

    Args:
        symbols: 股票代码列表

    Returns:
        Dict: {symbol: quote_data}
    """
    provider = get_realtime_data_provider()
    return provider.get_batch_realtime_quotes(symbols)
