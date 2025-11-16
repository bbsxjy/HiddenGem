# 混合数据源使用指南

## 📊 数据源策略总览

### 数据源职责划分

| 数据类型 | 主要数据源 | 备用数据源 | 更新频率 | 适用场景 |
|---------|-----------|-----------|---------|---------|
| **实时行情** | AKShare | - | <1分钟 | 实时价格、盘中分析 |
| **历史K线** | TuShare | AKShare | 每日收盘后 | 技术分析、回测 |
| **财务报表** | TuShare | AKShare | 季度更新 | 基本面分析 |
| **基本面指标** | TuShare | AKShare | 季度更新 | ROE、PE、PB等 |
| **宏观经济** | AKShare | - | 不定期 | 政策分析、宏观判断 |

### 数据融合原则

1. **实时数据优先原则**：需要当前价格时，优先使用AKShare实时接口
2. **历史数据权威原则**：需要历史数据时，优先使用TuShare（付费会员）
3. **降级容错原则**：主数据源失败时，自动降级到备用数据源
4. **明确标注原则**：所有输出都明确标注数据来源和时间戳

---

## 🚀 快速开始

### 1. 获取实时报价（AKShare）

```python
from tradingagents.dataflows.interface import get_realtime_quote_china

# 获取单只股票实时报价
quote = get_realtime_quote_china('000001')

print(f"当前价格: ¥{quote['current_price']}")
print(f"涨跌幅: {quote['change_pct']:+.2f}%")
print(f"今日最高: ¥{quote['high_price']}")
print(f"今日最低: ¥{quote['low_price']}")
```

**返回数据格式**：
```python
{
    'symbol': '000001',
    'name': '平安银行',
    'current_price': 15.23,      # 当前价格（实时）
    'open_price': 15.10,         # 今日开盘价
    'high_price': 15.50,         # 今日最高价 ⚠️ 今天的，非历史最高
    'low_price': 15.05,          # 今日最低价 ⚠️ 今天的，非历史最低
    'prev_close': 15.20,         # 昨日收盘价
    'change': 0.03,              # 涨跌额
    'change_pct': 0.20,          # 涨跌幅 (%)
    'volume': 123456789,         # 成交量
    'amount': 1876543210.50,     # 成交额
    'timestamp': '2025-01-07 14:30:00',
    'is_realtime': True,
    'data_source': 'akshare_realtime'
}
```

---

### 2. 获取市场快照（实时+历史）

```python
from tradingagents.dataflows.interface import get_market_snapshot_china

# 获取市场快照（实时报价 + 最近5天历史）
snapshot = get_market_snapshot_china('000001', lookback_days=5)

print(snapshot)
```

**输出示例**：
```
# 📊 平安银行(000001) - 市场快照

## 🔴 实时行情（2025-01-07 14:30:00）

⚠️ 重要：以下是实时数据，非历史数据！

- 当前价格: ¥15.23
- 今日最高: ¥15.50 ⬆️（今天的最高价，非历史最高）
- 今日最低: ¥15.05 ⬇️（今天的最低价，非历史最低）
- 涨跌幅: +0.20%

---

## 📈 最近5天历史数据（用于技术分析）

[历史K线数据...]

---

⚠️ LLM分析提示：
- 今日最高价 ¥15.50 是**今天**的价格，不是历史最高！
- 今日最低价 ¥15.05 是**今天**的价格，不是历史最低！
```

**推荐场景**：Agent分析时使用，自动区分实时和历史数据

---

### 3. 获取混合数据（历史+实时）

```python
from tradingagents.dataflows.interface import get_stock_data_with_realtime_context

# 获取历史数据 + 实时报价
data = get_stock_data_with_realtime_context(
    symbol='000001',
    start_date='2025-01-01',
    end_date='2025-01-07',
    include_realtime=True  # 是否包含实时报价
)

print(data)
```

**数据融合逻辑**：
1. 历史K线数据：TuShare（优先）→ AKShare（降级）
2. 实时报价：AKShare（免费、实时）
3. 自动融合两种数据，明确标注来源

---

### 4. 批量获取实时报价

```python
from tradingagents.dataflows.interface import get_batch_realtime_quotes_china

# 批量获取多只股票实时报价
symbols = ['000001', '600036', '000002']
quotes = get_batch_realtime_quotes_china(symbols)

for symbol, quote in quotes.items():
    print(f"{quote['name']}: ¥{quote['current_price']} ({quote['change_pct']:+.2f}%)")
```

---

## 🔧 Agent调用指南

### 技术分析Agent

```python
from tradingagents.dataflows.interface import get_market_snapshot_china

def analyze_technical(symbol: str):
    """技术分析：使用实时价格 + 历史K线"""

    # 获取市场快照（实时+历史）
    snapshot = get_market_snapshot_china(symbol, lookback_days=30)

    # 传给LLM分析
    # LLM会看到明确标注的实时数据和历史数据
    analysis = llm.analyze(snapshot)

    return analysis
```

**优点**：
- ✅ 实时价格准确（当前价、今日最高最低）
- ✅ 历史数据完整（用于趋势分析）
- ✅ 明确标注，避免混淆

---

### 基本面分析Agent

```python
from tradingagents.dataflows.interface import get_china_stock_fundamentals_tushare

def analyze_fundamental(symbol: str):
    """基本面分析：使用TuShare财务数据"""

    # 使用TuShare获取财务数据（更准确）
    fundamentals = get_china_stock_fundamentals_tushare(symbol)

    # 传给LLM分析
    analysis = llm.analyze(fundamentals)

    return analysis
```

**数据来源**：
- 优先：TuShare官方财务数据
- 备用：AKShare爬虫数据

---

### 风险管理Agent

```python
from tradingagents.dataflows.interface import get_realtime_quote_china

def assess_risk(symbol: str, portfolio):
    """风险评估：使用实时价格计算持仓风险"""

    # 获取实时报价
    quote = get_realtime_quote_china(symbol)

    if quote:
        current_price = quote['current_price']
        current_pct = quote['change_pct']

        # 计算实时风险指标
        position_value = portfolio[symbol]['shares'] * current_price
        unrealized_pnl = position_value - portfolio[symbol]['cost']
        risk_score = calculate_risk(current_pct, unrealized_pnl)

        return {
            'symbol': symbol,
            'current_price': current_price,
            'position_value': position_value,
            'unrealized_pnl': unrealized_pnl,
            'risk_score': risk_score
        }
```

---

## ⚙️ 配置说明

### 环境变量配置

```bash
# .env文件

# TuShare配置（优先用于历史数据）
TUSHARE_TOKEN=your_tushare_token_here

# 默认中国股票数据源（历史数据）
# 可选: tushare（推荐）, akshare, baostock
DEFAULT_CHINA_DATA_SOURCE=tushare

# AKShare自动用于实时数据，无需配置
```

### 数据源优先级

| 场景 | 第一优先级 | 第二优先级 | 第三优先级 |
|------|-----------|-----------|-----------|
| **实时报价** | AKShare | - | - |
| **历史K线** | TuShare | AKShare | BaoStock |
| **财务数据** | TuShare | AKShare | - |
| **宏观数据** | AKShare | - | - |

---

## 🐛 常见问题

### 1. 为什么会有"今日最高"和"历史最高"的混淆？

**问题**：LLM将历史数据的最高价当成当日最高价。

**原因**：
- 以前只提供历史K线数据，没有明确标注"今日"和"历史"
- LLM看到`high_price`字段，误以为是今天的最高价

**解决方案**：
- ✅ 使用 `get_market_snapshot_china()` 或 `get_stock_data_with_realtime_context()`
- ✅ 这些函数会明确标注"今日最高（今天的）"vs"历史最高"
- ✅ 输出格式包含⚠️警告提示，提醒LLM区分

---

### 2. 如何判断使用实时数据还是历史数据？

| 场景 | 使用数据类型 | 推荐函数 |
|------|------------|---------|
| 需要当前价格 | 实时数据 | `get_realtime_quote_china()` |
| 需要技术分析 | 实时+历史 | `get_market_snapshot_china()` |
| 需要回测 | 历史数据 | `get_china_stock_data_unified()` |
| 需要基本面 | 财务数据 | `get_china_stock_fundamentals_tushare()` |

---

### 3. AKShare实时数据的延迟是多少？

- **延迟**：< 1分钟（通常5-30秒）
- **数据源**：东方财富网实时行情
- **限制**：免费，无调用次数限制（但建议控制频率，避免IP封禁）
- **建议调用间隔**：1秒/次

---

### 4. TuShare和AKShare的数据质量对比

| 维度 | TuShare | AKShare |
|------|---------|---------|
| **准确性** | ⭐⭐⭐⭐⭐ 官方数据 | ⭐⭐⭐⭐ 爬虫数据 |
| **实时性** | ⭐⭐⭐ 延迟15分钟+ | ⭐⭐⭐⭐⭐ <1分钟 |
| **历史数据** | ⭐⭐⭐⭐⭐ 完整 | ⭐⭐⭐⭐ 较完整 |
| **财务数据** | ⭐⭐⭐⭐⭐ 官方财报 | ⭐⭐⭐ 爬虫财报 |
| **成本** | 💰 付费（积分制） | 🆓 完全免费 |
| **稳定性** | ⭐⭐⭐⭐⭐ 官方API | ⭐⭐⭐ 依赖网站 |

**推荐策略**：
- ✅ TuShare用于历史数据、财务数据（付费会员价值最大化）
- ✅ AKShare用于实时数据、补充数据（免费填补缺口）

---

### 5. 如何避免IP被封禁？

**AKShare调用建议**：
- 控制调用频率：1秒/次
- 避免高峰时段大量调用
- 使用批量接口减少请求次数
- 添加随机延迟（0.5-2秒）

**代码示例**：
```python
import time
import random

# 单次调用
quote = get_realtime_quote_china('000001')
time.sleep(random.uniform(1.0, 2.0))  # 随机延迟

# 批量调用（推荐）
quotes = get_batch_realtime_quotes_china(['000001', '600036', '000002'])
# 一次请求获取多只股票，减少API调用
```

---

## 📝 总结

### 核心改进

1. **实时数据模块**：新增 `realtime_data.py`，使用AKShare获取实时报价
2. **明确标注**：所有输出都明确标注"实时"vs"历史"，避免LLM混淆
3. **数据融合**：自动融合TuShare历史数据和AKShare实时数据
4. **降级容错**：主数据源失败时，自动降级到备用数据源

### 使用建议

- ✅ Agent分析时，优先使用 `get_market_snapshot_china()`（自动区分实时和历史）
- ✅ 需要实时价格时，使用 `get_realtime_quote_china()`
- ✅ 需要历史回测时，使用 `get_china_stock_data_unified()`（TuShare优先）
- ✅ 需要基本面数据时，使用 `get_china_stock_fundamentals_tushare()`

---

**最后更新**: 2025-01-07
**作者**: Claude Code
**项目**: TradingAgents-CN / HiddenGem Trading System
