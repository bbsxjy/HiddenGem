"""
Market Data API Router

提供市场数据查询的API端点
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import logging
import pandas as pd

# 导入数据接口
from tradingagents.dataflows.interface import get_stock_data_dataframe

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic Models
class MarketDataRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str


class MarketDataResponse(BaseModel):
    success: bool
    symbol: str
    data: List[Dict]
    count: int
    timestamp: str


@router.get("/data/{symbol}")
async def get_market_data(
    symbol: str,
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    days: Optional[int] = Query(None, description="回看天数（与start_date互斥）"),
    limit: Optional[int] = Query(100, description="返回数据条数")
):
    """
    获取股票市场数据

    Args:
        symbol: 股票代码 (e.g., 600519.SH, 000001.SZ, AAPL)
        start_date: 开始日期，默认为30天前
        end_date: 结束日期，默认为今天
        days: 回看天数（与start_date互斥，优先使用days）
        limit: 返回数据条数，默认100

    Returns:
        MarketDataResponse: 包含OHLCV数据
    """
    try:
        # 设置默认日期
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        # 处理days参数（优先于start_date）
        if days is not None:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        elif start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
       
        logger.info(f"[MARKET_DATA] Fetching {symbol} from {start_date} to {end_date}")

        # 获取数据
        df = get_stock_data_dataframe(symbol, start_date, end_date)

        if df is None or len(df) == 0:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        # 调试: 打印dataframe结构
        logger.info(f"[MARKET_DATA] DataFrame shape: {df.shape}")
        logger.info(f"[MARKET_DATA] DataFrame columns: {list(df.columns)}")
        logger.info(f"[MARKET_DATA] DataFrame index type: {type(df.index)}")
        logger.info(f"[MARKET_DATA] DataFrame index name: {df.index.name}")
        if len(df) > 0:
            logger.info(f"[MARKET_DATA] First index value: {df.index[0]} (type: {type(df.index[0])})")
            logger.info(f"[MARKET_DATA] First row: {df.iloc[0].to_dict()}")

        # 限制返回数量
        if limit and len(df) > limit:
            df = df.tail(limit)

        # 转换为字典列表，并重命名列
        data = []
        for idx, row in df.iterrows():
            # 尝试从多个来源获取日期
            date_str = None

            try:
                # 方法1: 检查row中是否有date/trade_date列
                if 'date' in row:
                    date_value = row['date']
                elif 'trade_date' in row:
                    date_value = row['trade_date']
                else:
                    # 方法2: 使用index（如果是datetime）
                    date_value = idx

                # 转换日期值为字符串
                if hasattr(date_value, 'strftime'):
                    # 已经是datetime对象
                    date_str = date_value.strftime('%Y-%m-%d')
                elif isinstance(date_value, str):
                    # 已经是字符串，验证格式
                    if len(date_value) == 8:  # YYYYMMDD格式
                        date_str = f"{date_value[:4]}-{date_value[4:6]}-{date_value[6:8]}"
                    else:
                        # 验证YYYY-MM-DD格式
                        datetime.strptime(date_value, '%Y-%m-%d')
                        date_str = date_value
                elif isinstance(date_value, (int, float)) and date_value > 19000101:
                    # 可能是YYYYMMDD格式的整数
                    date_str = f"{str(int(date_value))[:4]}-{str(int(date_value))[4:6]}-{str(int(date_value))[6:8]}"
                else:
                    # 尝试用pandas转换（但要检查结果）
                    parsed = pd.to_datetime(date_value)
                    # 检查是否是有效日期（不是1970-01-01）
                    if parsed.year > 1990:
                        date_str = parsed.strftime('%Y-%m-%d')
                    else:
                        raise ValueError(f"Invalid date: {date_value}")

            except Exception as e:
                logger.warning(f"[MARKET_DATA] Skipping row with invalid date: {idx}, error: {e}")
                continue

            # 如果没有获取到有效日期，跳过这行
            if not date_str:
                logger.warning(f"[MARKET_DATA] Skipping row with no valid date")
                continue

            # 验证OHLCV数据
            try:
                bar = {
                    "date": date_str,
                    "open": float(row.get('open', 0)),
                    "high": float(row.get('high', 0)),
                    "low": float(row.get('low', 0)),
                    "close": float(row.get('close', 0)),
                    "volume": float(row.get('volume', 0))
                }
                # 确保OHLC值有效
                if bar["open"] > 0 and bar["high"] > 0 and bar["low"] > 0 and bar["close"] > 0:
                    data.append(bar)
                else:
                    logger.warning(f"[MARKET_DATA] Skipping row with invalid OHLC values: {bar}")
            except (ValueError, TypeError) as e:
                logger.warning(f"[MARKET_DATA] Skipping row due to conversion error: {e}")
                continue

        # 按日期排序（确保升序）
        data.sort(key=lambda x: x["date"])

        # 最终验证：确保没有空数据或重复日期
        if not data:
            raise HTTPException(status_code=404, detail=f"No valid data found for {symbol}")

        # 移除重复日期（保留第一个）
        seen_dates = set()
        unique_data = []
        for bar in data:
            if bar["date"] not in seen_dates:
                seen_dates.add(bar["date"])
                unique_data.append(bar)
            else:
                logger.warning(f"[MARKET_DATA] Removing duplicate date: {bar['date']}")

        data = unique_data
        logger.info(f"[MARKET_DATA] Returning {len(data)} valid bars for {symbol}")

        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "bars": data,
                "count": len(data)
            },
            "timestamp": datetime.now().isoformat()
        }
       
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch market data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/{symbol}")
async def get_stock_info(symbol: str):
    """
    获取股票基本信息

    Args:
        symbol: 股票代码

    Returns:
        股票基本信息
    """
    try:
        # 获取股票数据（最近1天用于获取基本信息）
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        df = get_stock_data_dataframe(symbol, start_date, end_date)

        if df is None or len(df) == 0:
            # 如果最近1天没数据，尝试获取最近7天
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            df = get_stock_data_dataframe(symbol, start_date, end_date)

            if df is None or len(df) == 0:
                raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        # 从数据中提取基本信息
        # 判断市场类型
        if symbol.endswith('.SZ'):
            area = '深圳'
            if symbol.startswith('300'):
                industry = '创业板'
            elif symbol.startswith('000'):
                industry = '主板'
            else:
                industry = '深交所'
        elif symbol.endswith('.SH'):
            area = '上海'
            if symbol.startswith('688'):
                industry = '科创板'
            elif symbol.startswith('600') or symbol.startswith('601') or symbol.startswith('603'):
                industry = '主板'
            else:
                industry = '上交所'
        else:
            area = '未知'
            industry = '未知'

        # 尝试从symbol解析股票名称（这是临时方案，实际应该从数据源获取）
        stock_names = {
            '000001.SZ': '平安银行',
            '000002.SZ': '万科A',
            '600519.SH': '贵州茅台',
            '600036.SH': '招商银行',
            '000858.SZ': '五粮液',
            '300750.SZ': '宁德时代',
        }
        name = stock_names.get(symbol, symbol.split('.')[0])

        # 获取listing_date（如果df中有）
        listing_date = None
        if hasattr(df, 'index') and len(df) > 0:
            listing_date = df.index[0].strftime('%Y-%m-%d') if hasattr(df.index[0], 'strftime') else str(df.index[0])

        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "name": name,
                "industry": industry,
                "area": area,
                "listing_date": listing_date or "N/A"
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch stock info for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_stocks(
    query: str = Query(..., description="搜索关键词（代码或名称）"),
    limit: int = Query(10, description="返回结果数量")
):
    """
    搜索股票

    Args:
        query: 搜索关键词
        limit: 返回结果数量

    Returns:
        搜索结果列表
    """
    try:
        # TODO: 实现股票搜索功能
        # 可以使用tushare的股票列表

        return {
            "success": True,
            "query": query,
            "results": [],
            "count": 0,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"[ERROR] Stock search failed for query '{query}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """
    获取股票最新报价（实时Quote）

    Args:
        symbol: 股票代码

    Returns:
        最新报价信息
    """
    try:
        # 获取最近5天数据（确保能获取到最新数据）
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')

        df = get_stock_data_dataframe(symbol, start_date, end_date)

        if df is None or len(df) == 0:
            raise HTTPException(status_code=404, detail=f"No quote data found for {symbol}")

        # 获取最新一条数据
        latest = df.iloc[-1]

        # 计算涨跌幅和涨跌额
        if len(df) >= 2:
            prev_close = df.iloc[-2].get('close', latest.get('open', 0))
        else:
            prev_close = latest.get('open', 0)

        current_price = latest.get('close', 0)
        change = current_price - prev_close
        change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close != 0 else 0

        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "last_price": float(current_price),
                "price": float(current_price),  # 兼容字段
                "open": float(latest.get('open', 0)),
                "high": float(latest.get('high', 0)),
                "low": float(latest.get('low', 0)),
                "volume": float(latest.get('volume', 0)),
                "change": float(change),
                "change_pct": float(change_pct),  # 旧字段（兼容）
                "change_percent": float(change_pct),  # 新字段
                "timestamp": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/{symbol}")
async def get_technical_indicators(
    symbol: str,
    days: int = Query(90, description="计算指标的天数")
):
    """
    获取技术指标

    Args:
        symbol: 股票代码
        days: 计算指标的天数，默认90天

    Returns:
        技术指标数据
    """
    try:
        import pandas as pd
        import numpy as np

        # 获取历史数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days + 60)).strftime('%Y-%m-%d')  # 多取60天用于指标计算

        df = get_stock_data_dataframe(symbol, start_date, end_date)

        if df is None or len(df) == 0:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        # 计算技术指标
        def calculate_rsi(prices, period=14):
            """计算RSI指标"""
            deltas = np.diff(prices)
            seed = deltas[:period+1]
            up = seed[seed >= 0].sum()/period
            down = -seed[seed < 0].sum()/period
            rs = up/down if down != 0 else 0
            rsi = np.zeros_like(prices)
            rsi[:period] = 100. - 100./(1. + rs)

            for i in range(period, len(prices)):
                delta = deltas[i - 1]
                if delta > 0:
                    upval = delta
                    downval = 0.
                else:
                    upval = 0.
                    downval = -delta

                up = (up*(period - 1) + upval)/period
                down = (down*(period - 1) + downval)/period
                rs = up/down if down != 0 else 0
                rsi[i] = 100. - 100./(1. + rs)

            return rsi[-1]

        def calculate_macd(prices, slow=26, fast=12, signal=9):
            """计算MACD指标"""
            exp1 = pd.Series(prices).ewm(span=fast, adjust=False).mean()
            exp2 = pd.Series(prices).ewm(span=slow, adjust=False).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=signal, adjust=False).mean()
            hist = macd - signal_line
            return float(macd.iloc[-1]), float(signal_line.iloc[-1]), float(hist.iloc[-1])

        def calculate_ma(prices, period):
            """计算移动平均线"""
            return float(pd.Series(prices).rolling(window=period).mean().iloc[-1])

        def calculate_kdj(high, low, close, n=9):
            """计算KDJ指标"""
            low_list = pd.Series(low).rolling(n, min_periods=1).min()
            high_list = pd.Series(high).rolling(n, min_periods=1).max()
            rsv = (close - low_list) / (high_list - low_list) * 100
            k = rsv.ewm(com=2, adjust=False).mean()
            d = k.ewm(com=2, adjust=False).mean()
            j = 3 * k - 2 * d
            return float(k.iloc[-1]), float(d.iloc[-1]), float(j.iloc[-1])

        def calculate_bollinger_bands(prices, period=20, std_dev=2):
            """计算布林带"""
            sma = pd.Series(prices).rolling(window=period).mean()
            std = pd.Series(prices).rolling(window=period).std()
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            return float(upper.iloc[-1]), float(sma.iloc[-1]), float(lower.iloc[-1])

        def calculate_atr(high, low, close, period=14):
            """计算ATR（真实波幅）"""
            high = pd.Series(high)
            low = pd.Series(low)
            close = pd.Series(close)
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(period).mean()
            return float(atr.iloc[-1])

        # 提取价格数据
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values

        # 计算所有指标
        rsi = calculate_rsi(closes)
        macd, macd_signal, macd_hist = calculate_macd(closes)
        ma_5 = calculate_ma(closes, 5)
        ma_20 = calculate_ma(closes, 20)
        ma_60 = calculate_ma(closes, 60)
        kdj_k, kdj_d, kdj_j = calculate_kdj(highs, lows, closes)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
        atr = calculate_atr(highs, lows, closes)

        # ADX计算（简化版）
        adx = 25.0  # 简化处理，返回固定值

        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "indicators": {
                    "rsi": rsi,
                    "macd": macd,
                    "macd_signal": macd_signal,
                    "macd_hist": macd_hist,
                    "ma_5": ma_5,
                    "ma_20": ma_20,
                    "ma_60": ma_60,
                    "kdj_k": kdj_k,
                    "kdj_d": kdj_d,
                    "kdj_j": kdj_j,
                    "bb_upper": bb_upper,
                    "bb_middle": bb_middle,
                    "bb_lower": bb_lower,
                    "atr": atr,
                    "adx": adx
                },
                "calculated_from_days": len(df)
            },
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Failed to calculate indicators for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
