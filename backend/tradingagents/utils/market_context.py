"""
市场上下文模块
提供交易时间判断、涨跌幅限制、价格类型标注等市场规则信息
"""
from datetime import datetime, time, timedelta
from typing import Dict, Any, Tuple, Optional
import re

# 导入日志
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('market_context')


class MarketContext:
    """市场上下文管理器"""

    # A股交易时间（不含节假日检查）
    TRADING_SESSIONS = [
        (time(9, 30), time(11, 30)),   # 上午
        (time(13, 0), time(15, 0)),     # 下午
    ]

    # 涨跌幅限制规则
    PRICE_LIMIT_RULES = {
        'main_board': {'up': 0.10, 'down': -0.10, 'description': '主板（沪深主板）'},
        'star_market': {'up': 0.20, 'down': -0.20, 'description': '科创板（688xxx）'},
        'chinext': {'up': 0.20, 'down': -0.20, 'description': '创业板（300xxx）'},
        'bse': {'up': 0.30, 'down': -0.30, 'description': '北交所（8xxxxx）'},
        'st_stock': {'up': 0.05, 'down': -0.05, 'description': 'ST股票'},
    }

    @staticmethod
    def get_board_type(symbol: str) -> str:
        """
        根据股票代码判断板块类型

        Args:
            symbol: 股票代码（支持多种格式）

        Returns:
            板块类型: 'main_board', 'star_market', 'chinext', 'bse', 'unknown'
        """
        # 清理股票代码，提取数字部分
        code = re.sub(r'[^0-9]', '', symbol)

        if not code:
            return 'unknown'

        # 科创板：688xxx
        if code.startswith('688'):
            return 'star_market'

        # 创业板：300xxx
        if code.startswith('300'):
            return 'chinext'

        # 北交所：8xxxxx（6位数字，以8开头）
        if len(code) == 6 and code.startswith('8'):
            return 'bse'

        # 主板：000xxx, 001xxx, 002xxx, 600xxx, 601xxx, 603xxx等
        if code.startswith(('000', '001', '002', '600', '601', '603', '605')):
            return 'main_board'

        # 默认主板
        return 'main_board'

    @staticmethod
    def get_price_limit(symbol: str, is_st: bool = False) -> Dict[str, Any]:
        """
        获取股票的涨跌幅限制

        Args:
            symbol: 股票代码
            is_st: 是否为ST股票

        Returns:
            涨跌幅限制信息
        """
        if is_st:
            rule = MarketContext.PRICE_LIMIT_RULES['st_stock']
            board = 'ST股票'
        else:
            board_type = MarketContext.get_board_type(symbol)
            rule = MarketContext.PRICE_LIMIT_RULES.get(
                board_type,
                MarketContext.PRICE_LIMIT_RULES['main_board']
            )
            board = rule['description']

        return {
            'up_limit_pct': rule['up'],
            'down_limit_pct': rule['down'],
            'board_type': board,
            'symbol': symbol
        }

    @staticmethod
    def is_trading_day(check_date: datetime = None) -> bool:
        """
        判断是否为交易日（仅检查周末，不包括节假日）

        Args:
            check_date: 要检查的日期，默认为当前日期

        Returns:
            是否为交易日
        """
        if check_date is None:
            check_date = datetime.now()

        weekday = check_date.weekday()
        # 0=周一, 1=周二, ..., 5=周六, 6=周日
        # 周末不是交易日
        return weekday < 5

    @staticmethod
    def get_previous_trading_day(from_date: datetime = None, max_lookback: int = 7) -> Optional[str]:
        """
        获取指定日期之前的最近一个交易日

        Args:
            from_date: 起始日期，默认为当前日期
            max_lookback: 最大回溯天数，默认7天

        Returns:
            上一个交易日的日期字符串（YYYY-MM-DD格式），如果未找到则返回None
        """
        if from_date is None:
            from_date = datetime.now()

        # 从前一天开始查找
        check_date = from_date - timedelta(days=1)

        for _ in range(max_lookback):
            if MarketContext.is_trading_day(check_date):
                result_date = check_date.strftime('%Y-%m-%d')
                logger.info(f" [交易日检测] {from_date.strftime('%Y-%m-%d')} 的上一个交易日是 {result_date}")
                return result_date

            check_date -= timedelta(days=1)

        # 未找到交易日
        logger.warning(f" [交易日检测] 在{max_lookback}天内未找到{from_date.strftime('%Y-%m-%d')}之前的交易日")
        return None

    @staticmethod
    def is_trading_time(check_time: datetime = None) -> Tuple[bool, str]:
        """
        判断是否在交易时间内

        Args:
            check_time: 要检查的时间，默认为当前时间

        Returns:
            (是否交易时间, 状态描述)
        """
        if check_time is None:
            check_time = datetime.now()

        current_time = check_time.time()
        weekday = check_time.weekday()

        # 检查是否是周末
        if weekday >= 5:  # 5=周六, 6=周日
            return False, f"非交易日（周{'六' if weekday == 5 else '日'}）"

        # 检查是否在交易时段
        for session_start, session_end in MarketContext.TRADING_SESSIONS:
            if session_start <= current_time <= session_end:
                if session_start == time(9, 30):
                    return True, "交易时间（上午盘）"
                else:
                    return True, "交易时间（下午盘）"

        # 判断具体的非交易时段
        if current_time < time(9, 30):
            return False, "盘前时间（开盘前）"
        elif time(11, 30) < current_time < time(13, 0):
            return False, "午间休市"
        elif current_time > time(15, 0):
            return False, "盘后时间（收盘后）"
        else:
            return False, "非交易时间"

    @staticmethod
    def get_price_type(check_time: datetime = None) -> str:
        """
        根据时间判断价格类型

        Args:
            check_time: 要检查的时间，默认为当前时间

        Returns:
            价格类型: '盘中实时价', '昨日收盘价', '今日收盘价'
        """
        if check_time is None:
            check_time = datetime.now()

        is_trading, status = MarketContext.is_trading_time(check_time)

        if is_trading:
            return "盘中实时价"
        elif "盘前" in status or "午间" in status:
            return "昨日收盘价"
        else:  # 盘后
            return "今日收盘价"

    @staticmethod
    def generate_context_prompt(symbol: str, current_time: datetime = None) -> str:
        """
        生成市场上下文提示文本（注入到Agent的prompt中）

        Args:
            symbol: 股票代码
            current_time: 当前时间，默认为系统时间

        Returns:
            市场上下文文本
        """
        if current_time is None:
            current_time = datetime.now()

        # 交易时间状态
        is_trading, time_status = MarketContext.is_trading_time(current_time)
        price_type = MarketContext.get_price_type(current_time)

        # 涨跌幅限制
        price_limit = MarketContext.get_price_limit(symbol)

        # 格式化时间
        time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
        date_str = current_time.strftime('%Y年%m月%d日')
        weekday_cn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][current_time.weekday()]

        prompt = f"""
【市场上下文信息】
 **分析时间**：{time_str} ({date_str} {weekday_cn})
⏰ **交易状态**：{' ' + time_status if is_trading else ' ' + time_status}
 **价格类型**：系统提供的价格为「{price_type}」

 **涨跌幅限制**：
- 板块：{price_limit['board_type']}
- 涨幅上限：+{price_limit['up_limit_pct'] * 100:.0f}%
- 跌幅下限：{price_limit['down_limit_pct'] * 100:.0f}%

 **重要提示**：
1. 如果当前是「盘中实时价」，价格会持续波动，分析应考虑日内趋势
2. 如果当前是「昨日收盘价」或「今日收盘价」，价格为固定值，应基于日线数据分析
3. 价格异常波动超过涨跌幅限制时，可能触及涨停/跌停板
4. 非交易时间的分析应注重中长期判断，避免过度关注短期波动

【A股交易时间规则】
- 上午盘：09:30 - 11:30
- 下午盘：13:00 - 15:00
- 非交易日：周六、周日、法定节假日
"""
        return prompt.strip()

    @staticmethod
    def calculate_price_limits(current_price: float, symbol: str, is_st: bool = False) -> Dict[str, float]:
        """
        计算涨跌停价格

        Args:
            current_price: 当前价格（前一交易日收盘价）
            symbol: 股票代码
            is_st: 是否为ST股票

        Returns:
            涨跌停价格
        """
        limit_info = MarketContext.get_price_limit(symbol, is_st)
        up_limit_pct = limit_info['up_limit_pct']
        down_limit_pct = limit_info['down_limit_pct']

        up_limit_price = round(current_price * (1 + up_limit_pct), 2)
        down_limit_price = round(current_price * (1 + down_limit_pct), 2)

        return {
            'up_limit': up_limit_price,
            'down_limit': down_limit_price,
            'up_limit_pct': up_limit_pct,
            'down_limit_pct': down_limit_pct,
        }


def enrich_market_data_with_context(
    market_data: Dict[str, Any],
    symbol: str,
    current_time: datetime = None
) -> Dict[str, Any]:
    """
    为市场数据添加上下文信息

    Args:
        market_data: 原始市场数据
        symbol: 股票代码
        current_time: 当前时间

    Returns:
        带有上下文信息的市场数据
    """
    if current_time is None:
        current_time = datetime.now()

    enriched_data = market_data.copy()

    # 添加时间上下文
    is_trading, time_status = MarketContext.is_trading_time(current_time)
    price_type = MarketContext.get_price_type(current_time)

    enriched_data['market_context'] = {
        'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
        'is_trading_time': is_trading,
        'time_status': time_status,
        'price_type': price_type,
        'weekday': current_time.weekday(),
        'weekday_cn': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][current_time.weekday()],
    }

    # 添加涨跌幅限制
    price_limit = MarketContext.get_price_limit(symbol)
    enriched_data['price_limit'] = price_limit

    # 如果有价格数据，计算涨跌停价格
    if 'close' in market_data and market_data['close']:
        limits = MarketContext.calculate_price_limits(market_data['close'], symbol)
        enriched_data['calculated_limits'] = limits

    logger.info(f" [MarketContext] 为{symbol}添加市场上下文：{time_status}, 价格类型={price_type}")

    return enriched_data


# 示例使用
if __name__ == "__main__":
    # 测试科创板
    symbol = "688876"
    context = MarketContext.generate_context_prompt(symbol)
    print(context)
    print("\n" + "="*60 + "\n")

    # 测试创业板
    symbol = "300394"
    context = MarketContext.generate_context_prompt(symbol)
    print(context)
    print("\n" + "="*60 + "\n")

    # 测试涨跌停计算
    limits = MarketContext.calculate_price_limits(100.0, "688876")
    print(f"科创板股票价格100元：涨停={limits['up_limit']}, 跌停={limits['down_limit']}")

    limits = MarketContext.calculate_price_limits(100.0, "000001")
    print(f"主板股票价格100元：涨停={limits['up_limit']}, 跌停={limits['down_limit']}")
