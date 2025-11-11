# AkShare 实时数据集成 - 2025-11-11

## 修复的问题

### 1. Signals API 422 错误 ✅
**问题**：前端调用 `/api/v1/signals/recent` 返回 422 Unprocessable Content
**原因**：`signals.py` 缺少 `/recent` endpoint
**修复**：在 `backend/api/routers/signals.py` 添加了 `/recent` endpoint

### 2. 实时数据缺失 ✅
**问题**：实时监控页面只显示"等待市场数据连接"，没有真实的股票价格和决策
**解决方案**：创建了基于 AkShare 的实时数据服务

---

## 新增文件

### 1. `backend/api/services/realtime_data_service.py` 🆕

**功能**：使用 AkShare 获取A股实时行情数据

**主要方法**：
- `get_realtime_quote(symbol)` - 获取单只股票实时行情
- `get_batch_quotes(symbols)` - 批量获取多只股票行情
- `is_trading_hours()` - 判断是否在交易时间
- `get_stock_info(symbol)` - 获取股票基本信息

**数据字段**：
```python
{
    "symbol": "000001",
    "name": "平安银行",
    "price": 15.23,              # 最新价
    "change": 2.45,              # 涨跌幅 %
    "change_amount": 0.37,       # 涨跌额
    "volume": 12345678,          # 成交量
    "turnover": 1234567890,      # 成交额
    "high": 15.50,               # 最高价
    "low": 14.95,                # 最低价
    "open": 15.00,               # 开盘价
    "prev_close": 14.86,         # 昨收价
    "amplitude": 3.70,           # 振幅 %
    "turnover_rate": 1.23,       # 换手率 %
    "pe_ratio": 8.5,             # 市盈率
    "pb_ratio": 0.85,            # 市净率
    "total_market_cap": 289456789012,      # 总市值
    "circulation_market_cap": 256789123456, # 流通市值
    "timestamp": "2025-11-11T10:30:00"
}
```

**缓存机制**：
- 内存缓存，TTL 5秒
- 避免频繁调用 AkShare API

**使用示例**：
```python
from api.services.realtime_data_service import realtime_data_service

# 获取单只股票
quote = realtime_data_service.get_realtime_quote("000001")

# 批量获取
quotes = realtime_data_service.get_batch_quotes(["000001", "600519", "300502"])
```

---

## 修改的文件

### 1. `backend/api/routers/signals.py`

**新增 endpoint**：
```python
@router.get("/recent")
async def get_recent_signals(limit: int = Query(20)):
    """获取最近的交易信号"""
    return await get_current_signals(limit)
```

### 2. `backend/api/services/auto_trading_service.py`

**新增方法**：

#### `get_stock_decisions() -> List[Dict]`
获取所有监控股票的实时决策状态

**决策逻辑**（简化版）：
- 涨幅 > 2%：买入信号，置信度 0.6 + 涨幅/20
- 跌幅 > 2%：卖出信号，置信度 0.6 + 跌幅/20
- 其他：持有信号，置信度 0.5

**返回数据**：
```python
[
    {
        "symbol": "000001",
        "name": "平安银行",
        "last_check": "2025-11-11T10:30:00",
        "decision": "buy",           # buy | sell | hold
        "reason": "涨幅2.45%，技术面强势",
        "price": 15.23,
        "change": 2.45,
        "volume": 12345678,
        "confidence": 0.72,          # 0-1
        "suggested_quantity": 600    # 建议数量（100的倍数）
    },
    ...
]
```

#### `_calculate_quantity(price, decision) -> int`
计算建议交易数量

**逻辑**：
- 最大单个仓位：10% 的总资金
- 数量取整到100的倍数（A股最小单位）
- 最小100股

**示例**：
```python
初始资金：100,000元
最大仓位：10,000元
股票价格：15.23元
建议数量：(10,000 / 15.23 / 100) * 100 = 600股
```

### 3. `backend/api/routers/auto_trading.py`

**新增 endpoint**：
```python
@router.get("/decisions")
async def get_stock_decisions():
    """获取实时股票决策"""
    decisions = auto_trading_service.get_stock_decisions()
    return {
        "success": True,
        "data": decisions,
        "timestamp": datetime.now().isoformat()
    }
```

---

## 前端集成

### `frontend/src/pages/LiveMonitor.tsx`

**更改**：
1. **移除模拟数据**：删除 `useState` 和 `useEffect` 的模拟逻辑
2. **集成真实API**：调用 `/api/v1/auto-trading/decisions` 获取实时决策
3. **显示更多信息**：
   - 当前价格
   - 涨跌幅（带颜色标识）
   - 成交量（单位：万）
   - 置信度条
   - 建议数量和金额

**新增查询**：
```typescript
const { data: stockDecisions } = useQuery({
  queryKey: ['stockDecisions'],
  queryFn: async () => {
    const response = await axios.get(`${API_BASE_URL}/api/v1/auto-trading/decisions`);
    return response.data.data || [];
  },
  refetchInterval: 5000,
  enabled: autoTradingStatus?.is_running || false,
});
```

**显示效果**：
```
000001 平安银行                              [买入]
最后检查: 10:30:05

决策原因：涨幅2.45%，技术面强势

当前价格: ¥15.23    涨跌幅: +2.45%    成交量: 1234.57万

置信度: ████████░░░░░░░░░░░░ 72%

建议数量: 600股 (约 ¥9,138)
```

---

## API 接口总结

### 新增接口

1. **GET `/api/v1/signals/recent`**
   - 参数：`limit` (默认20)
   - 返回：最近的交易信号列表

2. **GET `/api/v1/auto-trading/decisions`**
   - 参数：无
   - 返回：所有监控股票的实时决策
   - 刷新：前端每5秒自动刷新

### 数据流

```
AkShare API
    ↓
realtime_data_service (缓存5秒)
    ↓
auto_trading_service.get_stock_decisions()
    ↓
/api/v1/auto-trading/decisions
    ↓
LiveMonitor 页面 (每5秒刷新)
```

---

## 使用说明

### 1. 启动自动交易
在设置页面配置股票列表并启动，例如：
```
300502,002759,002407,600547,603579,600353
```

### 2. 查看实时监控
访问 `/live-monitor` 页面，可以看到：
- ✅ 交易时段正确显示（已修复）
- ✅ 每只股票的实时价格
- ✅ 涨跌幅和成交量
- ✅ 智能决策（买/卖/持有）
- ✅ 决策原因和置信度
- ✅ 建议交易数量和金额

### 3. 决策更新频率
- 实时行情：每5秒从 AkShare 获取（带缓存）
- 前端刷新：每5秒自动更新
- 决策逻辑：实时计算

---

## 注意事项

### 1. AkShare 限制
- AkShare 是免费API，有调用频率限制
- 内置5秒缓存减轻API压力
- 非交易时间数据可能不准确

### 2. 决策逻辑
**当前实现（简化版）**：
- 基于涨跌幅的简单判断
- 仅作为演示

**TODO（生产环境需要）**：
- 集成RL策略的决策
- 集成Multi-Agent的综合分析
- 添加技术指标计算
- 风险评估和仓位管理

### 3. 性能优化
- ✅ 5秒缓存减少API调用
- ✅ 批量获取所有股票（单次请求）
- ✅ 前端仅在自动交易运行时获取决策

### 4. 关于 uvicorn 重启
当修改backend代码时，uvicorn 会自动重启服务器，导致：
- 自动交易状态丢失
- Broker 需要重新初始化

**解决方案**：
- 使用 `--reload-exclude` 参数排除日志文件
- 或者在生产环境使用 `--workers 4` 不带 `--reload`

---

## 下一步优化

1. **集成真实策略决策**
   - 从 RL 策略获取信号
   - 从 Multi-Agent 获取综合分析
   - 合并多个信号源

2. **增强数据可视化**
   - 价格走势图表
   - 成交量柱状图
   - 决策历史记录

3. **添加更多指标**
   - RSI、MACD、均线
   - 量价配合分析
   - 盘口数据（买卖五档）

4. **决策日志**
   - 记录每次决策到数据库
   - 支持历史回溯
   - 决策准确率分析

---

**最后更新**：2025-11-11 10:40 CST
**提交记录**：
- 0ba9b36 - 前端集成真实数据
- (backend changes not committed due to .gitignore)
