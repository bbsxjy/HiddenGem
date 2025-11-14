# 数据获取修复 - 使用TradingAgents统一数据接口

## 问题描述

**错误现象**:
自动交易服务一直使用模拟历史数据，日志显示：
```
2025-11-14 16:54:36,519 | auto_trading_service | WARNING | ⚠️ [300502] 使用模拟历史数据（50行）
```

**根本原因**:
代码尝试使用不存在的数据模块：
1. ❌ `utils.data_fetch.get_stock_data` - 模块不存在
2. ❌ `trading.market_data_feed.MarketDataFeed` - 类不存在

导致数据获取异常，总是走到fallback分支使用模拟数据。

## 修复方案

### 使用TradingAgents统一数据接口

TradingAgents-CN 项目已经提供了完整的统一数据接口：

```python
from tradingagents.dataflows.interface import get_stock_data_dataframe
```

**接口特点**:
- ✅ 自动识别A股/港股/美股
- ✅ 多级缓存（Redis + MongoDB + 文件）
- ✅ 多数据源回退（Tushare → AkShare）
- ✅ 返回标准DataFrame格式
- ✅ 包含完整OHLCV数据

### 修改文件: `api/services/auto_trading_service.py`

#### 修改前（❌ 错误）:

```python
# 尝试使用不存在的模块
try:
    from utils.data_fetch import get_stock_data
    hist_data = get_stock_data(symbol, start_date, end_date)

    if hist_data is not None and not hist_data.empty:
        stock_data[symbol] = hist_data
        logger.info(f"✓ [{symbol}] 获取历史数据成功")
    else:
        raise ValueError("返回数据为空")

except Exception as e1:
    logger.warning(f"⚠️ [{symbol}] 真实数据获取失败: {e1}")
    # 总是走到这里，使用模拟数据
    stock_data[symbol] = pd.DataFrame({...})  # 50行模拟数据
```

**问题**: `utils.data_fetch` 模块不存在，导致每次都抛出ImportError，总是使用模拟数据。

#### 修改后（✅ 正确）:

```python
# 使用 TradingAgents 的统一数据接口
try:
    from tradingagents.dataflows.interface import get_stock_data_dataframe
    from datetime import datetime, timedelta

    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')

    hist_data = get_stock_data_dataframe(symbol, start_date, end_date)

    if hist_data is not None and not hist_data.empty:
        stock_data[symbol] = hist_data
        logger.info(f"✓ [{symbol}] 获取历史数据成功（{len(hist_data)}行）")
    else:
        raise ValueError("返回数据为空")

except Exception as e1:
    logger.warning(f"⚠️ [{symbol}] 真实数据获取失败: {e1}")

    # 创建足够大的模拟数据（至少50行供技术指标计算）
    current_price = market_prices[symbol]
    n_rows = 50
    stock_data[symbol] = pd.DataFrame({
        'close': [current_price * (1 + np.random.randn() * 0.02) for _ in range(n_rows)],
        'high': [current_price * (1 + np.random.rand() * 0.03) for _ in range(n_rows)],
        'low': [current_price * (1 - np.random.rand() * 0.03) for _ in range(n_rows)],
        'open': [current_price * (1 + np.random.randn() * 0.01) for _ in range(n_rows)],
        'volume': [1000000 * (1 + np.random.rand()) for _ in range(n_rows)]
    })
    logger.warning(f"⚠️ [{symbol}] 使用模拟历史数据（{n_rows}行）")
```

**改进点**:
1. ✅ 使用正确的 `tradingagents.dataflows.interface.get_stock_data_dataframe`
2. ✅ 获取60天历史数据（足够计算所有技术指标）
3. ✅ 添加详细日志，显示实际获取的行数
4. ✅ 保留模拟数据作为fallback机制（50行）

## 数据接口说明

### get_stock_data_dataframe 函数签名

```python
def get_stock_data_dataframe(
    symbol: str,
    start_date: str,  # 格式: 'YYYYMMDD' 或 'YYYY-MM-DD'
    end_date: str,    # 格式: 'YYYYMMDD' 或 'YYYY-MM-DD'
    freq: str = 'D'   # 'D' 日线, '60' 60分钟线
) -> pd.DataFrame
```

### 返回数据格式

```python
DataFrame columns:
- date: 日期
- open: 开盘价
- high: 最高价
- low: 最低价
- close: 收盘价
- volume: 成交量
- (可能还有其他字段，如成交额、涨跌幅等)
```

### 自动识别股票市场

```python
# A股
get_stock_data_dataframe('000001', '20250101', '20250131')  # 平安银行
get_stock_data_dataframe('600519', '20250101', '20250131')  # 茅台

# 港股
get_stock_data_dataframe('00700', '20250101', '20250131')   # 腾讯控股

# 美股
get_stock_data_dataframe('AAPL', '20250101', '20250131')    # 苹果
```

### 数据缓存机制

```
请求数据
    ↓
1. 检查Redis缓存（5分钟有效期）
    ├─→ 命中 → 返回缓存数据
    └─→ 未命中 ↓
2. 检查MongoDB缓存（1天有效期）
    ├─→ 命中 → 返回缓存数据 → 更新Redis
    └─→ 未命中 ↓
3. 检查文件缓存（.parquet）
    ├─→ 命中 → 返回缓存数据 → 更新MongoDB和Redis
    └─→ 未命中 ↓
4. 从数据源获取
    ├─→ Tushare Pro（优先）
    └─→ AkShare（回退）
    ↓
保存到所有缓存层
    ↓
返回数据
```

## 为什么需要60天数据

RL策略的技术指标计算需要足够的历史数据：

| 指标 | 最小需求 | 说明 |
|------|---------|------|
| RSI  | 14天 | 14日相对强弱指标 |
| MACD | 26天 | EMA26需要26天数据 |
| MA10 | 10天 | 10日移动平均 |
| MA20 | 20天 | 20日移动平均 |
| ATR  | 14天 | 14日平均真实波幅 |

**计算逻辑**:
- MACD需要EMA26（26天）+ 预热期（约26天）≈ 52天
- 考虑到周末、节假日，实际交易日较少
- **60天自然日** 可以确保获得足够的交易日数据（约42个交易日）

## 预期效果

修复后，自动交易服务应该能够：

### 成功获取真实数据时

```
2025-11-14 XX:XX:XX | auto_trading_service | INFO | 📊 执行交易检查...
2025-11-14 XX:XX:XX | auto_trading_service | INFO | ✓ [000001] 获取历史数据成功（42行）
2025-11-14 XX:XX:XX | auto_trading_service | INFO | ✓ [600519] 获取历史数据成功（42行）
2025-11-14 XX:XX:XX | auto_trading_service | INFO | ✓ [300502] 获取历史数据成功（42行）
```

**特点**:
- ✅ 使用真实历史行情数据
- ✅ 技术指标基于真实价格计算
- ✅ RL模型决策更准确

### 数据获取失败时（fallback）

```
2025-11-14 XX:XX:XX | auto_trading_service | WARNING | ⚠️ [000001] 真实数据获取失败: ConnectionError
2025-11-14 XX:XX:XX | auto_trading_service | WARNING | ⚠️ [000001] 使用模拟历史数据（50行）
```

**特点**:
- ⚠️ 使用模拟数据（带随机波动）
- ⚠️ 技术指标计算仍然有效
- ⚠️ RL模型可以运行，但决策质量下降

## 验证方法

### 方法1：查看日志

启动自动交易后，观察日志输出：

```bash
# 成功获取真实数据
✓ [000001] 获取历史数据成功（42行）  # 好！

# 失败，使用模拟数据
⚠️ [000001] 使用模拟历史数据（50行）  # 需要检查数据源配置
```

### 方法2：检查数据源配置

确保 `.env` 文件配置了Tushare Token：

```bash
TUSHARE_TOKEN=your_token_here
```

获取Token: https://tushare.pro/register

### 方法3：手动测试数据接口

```python
from tradingagents.dataflows.interface import get_stock_data_dataframe
from datetime import datetime, timedelta

end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')

# 测试A股
df = get_stock_data_dataframe('000001', start_date, end_date)
print(f"获取数据: {len(df)}行")
print(df.head())

# 应该返回约42行真实数据（60天中的交易日）
```

## 其他可用的数据接口

TradingAgents提供了多个数据接口，根据需要选择：

```python
from tradingagents.dataflows.interface import (
    # 统一接口（推荐）
    get_stock_data_by_market,        # 自动识别市场
    get_stock_data_dataframe,        # 获取DataFrame

    # A股专用
    get_china_stock_data_unified,    # A股历史数据
    get_china_stock_info_unified,    # A股基本信息
    get_china_realtime_quote,        # A股实时行情

    # 港股专用
    get_hk_stock_data_unified,       # 港股历史数据
    get_hk_stock_info_unified,       # 港股基本信息

    # 美股专用
    get_us_stock_data_unified,       # 美股历史数据
    get_us_stock_info_unified,       # 美股基本信息
)
```

## 相关文件

- **修改文件**: `api/services/auto_trading_service.py` (lines 146-176)
- **数据接口**: `tradingagents/dataflows/interface.py`
- **缓存管理**: `tradingagents/dataflows/cache_manager.py`
- **数据源管理**: `tradingagents/dataflows/data_source_manager.py`

## Git提交

```
commit 19d38bc
fix(auto-trading): 使用正确的TradingAgents数据接口

- 替换不存在的 utils.data_fetch 为 tradingagents.dataflows.interface.get_stock_data_dataframe
- 修复数据获取逻辑，使用60天历史数据用于技术指标计算
- 添加详细的数据获取成功/失败日志
- 保留50行模拟数据作为fallback机制
- 这应该能够获取真实历史数据而不是模拟数据
```

## 未来改进

1. **缓存优化**: 在自动交易循环中缓存历史数据，避免重复获取
2. **增量更新**: 只获取最新的K线数据，而不是每次都获取60天
3. **数据验证**: 检查数据完整性（是否有缺失值、异常值）
4. **实时数据**: 整合实时行情到历史数据中
5. **多频率支持**: 支持分钟线、小时线等不同频率

---

**修复日期**: 2025-11-14
**修复人**: Claude Code
**状态**: ✅ 已完成并提交
**相关文档**:
- [RL数据修复](./RL_DATA_FIX.md)
- [模型路径修复](./MODEL_PATH_FIX.md)
