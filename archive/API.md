# HiddenGem API 文档

完整的REST API和WebSocket接口文档，供前端开发使用。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API Version**: `v1`
- **API Prefix**: `/api/v1`
- **文档地址**:
  - Swagger UI: `http://localhost:8000/docs`
  - ReDoc: `http://localhost:8000/redoc`
- **认证**: 暂未实现（后续可能添加JWT）

---

## 目录

- [REST API](#rest-api)
  - [系统健康检查](#1-系统健康检查)
  - [策略管理](#2-策略管理-strategies)
  - [市场数据](#3-市场数据-market)
  - [投资组合](#4-投资组合-portfolio)
  - [订单管理](#5-订单管理-orders)
  - [MCP智能体](#6-mcp智能体-agents)
  - [交易信号](#7-交易信号-signals)
- [WebSocket API](#websocket-api)
- [数据模型](#数据模型)
- [错误处理](#错误处理)

---

## REST API

### 1. 系统健康检查

#### GET `/health`
获取系统健康状态。

**请求参数**: 无

**响应示例**:
```json
{
  "status": "healthy",
  "service": "HiddenGem Trading API",
  "version": "0.1.0",
  "environment": "development"
}
```

#### GET `/`
获取API基本信息。

**响应示例**:
```json
{
  "name": "HiddenGem Trading System API",
  "version": "0.1.0",
  "description": "A-share quantitative trading with MCP agents",
  "docs": "/docs",
  "health": "/health"
}
```

---

### 2. 策略管理 (`/strategies`)

#### POST `/api/v1/strategies/`
创建新策略。

**请求体**:
```json
{
  "name": "my_swing_strategy",
  "strategy_type": "swing_trading",  // 或 "trend_following"
  "enabled": true,
  "symbols": ["000001", "600519", "000858"],
  "max_positions": 5,
  "position_size": 0.2,
  "stop_loss_pct": 0.08,
  "take_profit_pct": 0.15,
  "params": {
    "holding_days_min": 7,
    "holding_days_max": 14
  }
}
```

**响应**: `201 Created`
```json
{
  "name": "my_swing_strategy",
  "strategy_type": "swing_trading",
  "enabled": true,
  "symbols": ["000001", "600519", "000858"],
  "max_positions": 5,
  "position_size": 0.2,
  "stop_loss_pct": 0.08,
  "take_profit_pct": 0.15,
  "num_positions": 0,
  "params": {...},
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET `/api/v1/strategies/`
获取所有策略列表。

**响应**: `200 OK`
```json
[
  {
    "name": "my_swing_strategy",
    "strategy_type": "swing_trading",
    "enabled": true,
    "num_positions": 3,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### GET `/api/v1/strategies/{strategy_name}`
获取指定策略详情。

**路径参数**:
- `strategy_name`: 策略名称

**响应**: `200 OK` 或 `404 Not Found`

#### PATCH `/api/v1/strategies/{strategy_name}`
更新策略配置。

**请求体**:
```json
{
  "enabled": false,
  "symbols": ["000001", "600519"],
  "max_positions": 3,
  "params": {
    "custom_param": "value"
  }
}
```

**响应**: `200 OK`

#### DELETE `/api/v1/strategies/{strategy_name}`
删除策略。

**响应**: `200 OK`
```json
{
  "success": true,
  "message": "Strategy 'my_swing_strategy' deleted"
}
```

#### POST `/api/v1/strategies/{strategy_name}/backtest`
运行策略回测。

**请求体**:
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 1000000,
  "symbols": ["000001", "600519", "000858"]
}
```

**响应**: `200 OK`
```json
{
  "strategy_name": "my_swing_strategy",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 1000000,
  "final_capital": 1150000,
  "total_return": 150000,
  "total_return_pct": 0.15,
  "annual_return_pct": 0.15,
  "sharpe_ratio": 1.8,
  "max_drawdown": 0.12,
  "win_rate": 0.65,
  "num_trades": 42
}
```

#### GET `/api/v1/strategies/{strategy_name}/stats`
获取策略统计信息。

**响应**: `200 OK`

---

### 3. 市场数据 (`/market`)

#### GET `/api/v1/market/quote/{symbol}`
获取实时行情。

**路径参数**:
- `symbol`: 股票代码（如 "000001"）

**响应**: `200 OK`
```json
{
  "symbol": "000001",
  "price": 12.35,
  "open": 12.20,
  "high": 12.50,
  "low": 12.15,
  "volume": 5000000,
  "change_pct": 0.0123,
  "timestamp": "2024-01-15T14:30:00Z"
}
```

#### GET `/api/v1/market/bars/{symbol}`
获取历史K线数据（OHLCV）。

**路径参数**:
- `symbol`: 股票代码

**查询参数**:
- `start_date`: 开始日期（YYYY-MM-DD），可选
- `end_date`: 结束日期（YYYY-MM-DD），可选
- `days`: 天数（如果未指定日期），默认60

**响应**: `200 OK`
```json
{
  "symbol": "000001",
  "bars": [
    {
      "date": "2024-01-15",
      "open": 12.20,
      "high": 12.50,
      "low": 12.10,
      "close": 12.35,
      "volume": 5000000
    }
  ],
  "count": 60
}
```

#### GET `/api/v1/market/indicators/{symbol}`
获取技术指标。

**查询参数**:
- `days`: 计算天数，默认60

**响应**: `200 OK`
```json
{
  "symbol": "000001",
  "timestamp": "2024-01-15T14:30:00Z",
  "indicators": {
    "rsi": 55.2,
    "macd": 0.15,
    "macd_signal": 0.12,
    "macd_hist": 0.03,
    "ma_5": 12.30,
    "ma_20": 12.10,
    "ma_60": 11.80,
    "kdj_k": 65.3,
    "kdj_d": 62.1,
    "kdj_j": 71.7,
    "bb_upper": 12.80,
    "bb_middle": 12.30,
    "bb_lower": 11.80,
    "atr": 0.35,
    "adx": 28.5
  },
  "calculated_from_days": 90
}
```

#### GET `/api/v1/market/search`
搜索股票。

**查询参数**:
- `query`: 搜索关键词（代码或名称）
- `limit`: 最大结果数，默认20，最大100

**响应**: `200 OK`
```json
{
  "query": "平安",
  "results": [],
  "message": "Stock search not yet implemented"
}
```

#### GET `/api/v1/market/info/{symbol}`
获取股票基本信息。

**响应**: `200 OK`
```json
{
  "symbol": "000001",
  "name": "平安银行",
  "industry": "银行",
  "area": "深圳",
  "listing_date": "1991-04-03"
}
```

---

### 4. 投资组合 (`/portfolio`)

#### GET `/api/v1/portfolio/summary`
获取投资组合摘要。

**响应**: `200 OK`
```json
{
  "total_value": 1250000.00,
  "cash": 250000.00,
  "positions_value": 1000000.00,
  "total_pnl": 250000.00,
  "total_pnl_pct": 0.25,
  "daily_pnl": 5000.00,
  "num_positions": 5,
  "timestamp": "2024-01-15T15:00:00Z"
}
```

#### GET `/api/v1/portfolio/positions`
获取所有持仓。

**响应**: `200 OK`
```json
[
  {
    "symbol": "000001",
    "quantity": 10000,
    "avg_cost": 12.00,
    "current_price": 12.50,
    "market_value": 125000.00,
    "unrealized_pnl": 5000.00,
    "unrealized_pnl_pct": 0.0417,
    "entry_date": "2024-01-10T10:00:00Z",
    "strategy_name": "my_swing_strategy"
  }
]
```

#### GET `/api/v1/portfolio/positions/{symbol}`
获取指定股票持仓。

**路径参数**:
- `symbol`: 股票代码

**响应**: `200 OK` 或 `404 Not Found`

#### GET `/api/v1/portfolio/history`
获取组合历史快照。

**查询参数**:
- `days`: 天数，默认30

**响应**: `200 OK`
```json
{
  "snapshots": [
    {
      "timestamp": "2024-01-15T15:00:00Z",
      "total_value": 1250000.00,
      "total_pnl": 250000.00,
      "total_pnl_pct": 0.25,
      "num_positions": 5
    }
  ],
  "count": 30
}
```

---

### 5. 订单管理 (`/orders`)

#### POST `/api/v1/orders/`
创建订单。

**请求体**:
```json
{
  "symbol": "000001",
  "side": "buy",  // 或 "sell"
  "order_type": "limit",  // 或 "market"
  "quantity": 1000,  // 必须是100的倍数
  "price": 12.50,  // limit订单必填
  "strategy_name": "my_swing_strategy"
}
```

**响应**: `201 Created`
```json
{
  "id": 12345,
  "symbol": "000001",
  "side": "buy",
  "order_type": "limit",
  "quantity": 1000,
  "price": 12.50,
  "filled_quantity": 0,
  "avg_filled_price": null,
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "filled_at": null
}
```

#### GET `/api/v1/orders/`
获取订单列表。

**查询参数**:
- `status`: 按状态过滤（pending/submitted/filled/cancelled），可选
- `limit`: 最大结果数，默认50，最大200

**响应**: `200 OK`
```json
[
  {
    "id": 12345,
    "symbol": "000001",
    "side": "buy",
    "order_type": "limit",
    "quantity": 1000,
    "price": 12.50,
    "filled_quantity": 1000,
    "avg_filled_price": 12.48,
    "status": "filled",
    "created_at": "2024-01-15T10:30:00Z",
    "filled_at": "2024-01-15T10:31:00Z"
  }
]
```

#### GET `/api/v1/orders/{order_id}`
获取订单详情。

**路径参数**:
- `order_id`: 订单ID

**响应**: `200 OK` 或 `404 Not Found`

#### DELETE `/api/v1/orders/{order_id}`
取消订单。

**路径参数**:
- `order_id`: 订单ID

**响应**: `200 OK`
```json
{
  "success": true,
  "message": "Order 12345 cancelled"
}
```

**注意**: 只能取消状态为 `pending` 或 `submitted` 的订单。

#### GET `/api/v1/orders/history/recent`
获取最近订单历史。

**查询参数**:
- `days`: 天数，默认7，最大90

**响应**: `200 OK`
```json
{
  "orders": [
    {
      "id": 12345,
      "symbol": "000001",
      "side": "buy",
      "quantity": 1000,
      "price": 12.50,
      "status": "filled",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 15
}
```

---

### 6. MCP智能体 (`/agents`)

#### GET `/api/v1/agents/status`
获取所有智能体状态。

**响应**: `200 OK`
```json
[
  {
    "name": "technical",
    "enabled": true,
    "weight": 0.25,
    "timeout": 10,
    "cache_ttl": 300
  },
  {
    "name": "fundamental",
    "enabled": true,
    "weight": 0.20,
    "timeout": 15,
    "cache_ttl": 600
  }
]
```

#### POST `/api/v1/agents/analyze/{agent_name}`
使用指定智能体分析。

**路径参数**:
- `agent_name`: 智能体名称（technical/fundamental/risk/market）

**请求体**:
```json
{
  "symbol": "000001"
}
```

**响应**: `200 OK`
```json
{
  "agent_name": "technical",
  "symbol": "000001",
  "score": 0.75,
  "direction": "long",
  "confidence": 0.80,
  "reasoning": "技术指标显示：RSI(45.2)处于中性区域，MACD金叉(0.15>0.12)，价格站上MA20(12.30)...",
  "analysis": {
    "rsi": 45.2,
    "macd_signal": "golden_cross",
    "trend": "up",
    "support_level": 12.00,
    "resistance_level": 13.00
  },
  "execution_time_ms": 150,
  "timestamp": "2024-01-15T10:30:00Z",
  "is_error": false
}
```

#### POST `/api/v1/agents/analyze-all/{symbol}`
使用所有智能体协同分析。

**路径参数**:
- `symbol`: 股票代码

**响应**: `200 OK`
```json
{
  "symbol": "000001",
  "agent_results": {
    "technical": {
      "direction": "long",
      "confidence": 0.80,
      "score": 0.75,
      "reasoning": "技术面偏多...",
      "is_error": false
    },
    "fundamental": {
      "direction": "long",
      "confidence": 0.70,
      "score": 0.65,
      "reasoning": "基本面良好...",
      "is_error": false
    },
    "risk": {
      "direction": "hold",
      "confidence": 0.60,
      "score": 0.55,
      "reasoning": "风险可控...",
      "is_error": false
    }
  },
  "aggregated_signal": {
    "direction": "long",
    "confidence": 0.72,
    "position_size": 0.18,
    "num_agreeing_agents": 3
  }
}
```

#### GET `/api/v1/agents/performance`
获取智能体性能指标。

**响应**: `200 OK`
```json
{
  "message": "Agent performance tracking not yet implemented",
  "agents": ["technical", "fundamental", "risk", "market"]
}
```

---

### 7. 交易信号 (`/signals`)

#### GET `/api/v1/signals/current`
获取当前未执行信号。

**查询参数**:
- `limit`: 最大结果数，默认50，最大200

**响应**: `200 OK`
```json
[
  {
    "id": 123,
    "symbol": "000001",
    "direction": "buy",
    "strength": 0.75,
    "agent_name": "orchestrator",
    "strategy_name": "my_swing_strategy",
    "entry_price": 12.50,
    "target_price": 14.00,
    "stop_loss_price": 11.50,
    "reasoning": "多智能体协同分析显示...",
    "timestamp": "2024-01-15T10:00:00Z",
    "is_executed": false
  }
]
```

#### GET `/api/v1/signals/history`
获取历史信号。

**查询参数**:
- `days`: 天数，默认7，最大90
- `symbol`: 按股票过滤，可选

**响应**: `200 OK` (格式同 `/current`)

#### GET `/api/v1/signals/{signal_id}`
获取信号详情。

**路径参数**:
- `signal_id`: 信号ID

**响应**: `200 OK` 或 `404 Not Found`

#### GET `/api/v1/signals/stats/summary`
获取信号统计。

**查询参数**:
- `days`: 统计周期，默认30，最大365

**响应**: `200 OK`
```json
{
  "period_days": 30,
  "total_signals": 150,
  "executed_signals": 120,
  "execution_rate": 0.80,
  "by_direction": {
    "buy": 80,
    "sell": 40,
    "hold": 30
  },
  "by_agent": {
    "orchestrator": 100,
    "technical": 30,
    "fundamental": 20
  }
}
```

---

## WebSocket API

WebSocket基础URL: `ws://localhost:8000/ws`

所有WebSocket连接建立后会收到欢迎消息，然后可以发送订阅请求。

### 1. 市场数据流 (`/ws/market`)

**连接**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/market');
```

**欢迎消息**:
```json
{
  "type": "connection",
  "message": "Connected to market data stream",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**订阅股票**:
```json
{
  "action": "subscribe",
  "symbols": ["000001", "600519"]
}
```

**订阅确认**:
```json
{
  "type": "subscription",
  "subscribed_symbols": ["000001", "600519"],
  "timestamp": "2024-01-15T10:30:01Z"
}
```

**取消订阅**:
```json
{
  "action": "unsubscribe",
  "symbols": ["000001"]
}
```

**市场数据推送**:
```json
{
  "type": "market_data",
  "symbol": "000001",
  "price": 12.50,
  "volume": 5000000,
  "timestamp": "2024-01-15T10:30:05Z"
}
```

### 2. 订单更新流 (`/ws/orders`)

**连接**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/orders');
```

**订单状态更新**:
```json
{
  "type": "order_update",
  "order_id": 12345,
  "status": "filled",
  "filled_quantity": 1000,
  "avg_filled_price": 12.48,
  "timestamp": "2024-01-15T10:31:00Z"
}
```

### 3. 投资组合更新流 (`/ws/portfolio`)

**连接**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/portfolio');
```

**组合更新推送**:
```json
{
  "type": "portfolio_update",
  "total_value": 1250000.00,
  "total_pnl": 250000.00,
  "total_pnl_pct": 0.25,
  "positions": [
    {
      "symbol": "000001",
      "quantity": 10000,
      "unrealized_pnl": 5000.00
    }
  ],
  "timestamp": "2024-01-15T15:00:00Z"
}
```

### 4. 智能体分析流 (`/ws/agents`)

**连接**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/agents');
```

**智能体分析结果**:
```json
{
  "type": "agent_analysis",
  "agent": "technical",
  "symbol": "000001",
  "result": {
    "direction": "long",
    "confidence": 0.80,
    "reasoning": "技术面偏多..."
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 数据模型

### OrderSide（订单方向）
- `buy`: 买入
- `sell`: 卖出

### OrderType（订单类型）
- `market`: 市价单
- `limit`: 限价单

### OrderStatus（订单状态）
- `pending`: 待提交
- `submitted`: 已提交
- `partial_filled`: 部分成交
- `filled`: 全部成交
- `cancelled`: 已取消
- `rejected`: 已拒绝

### SignalDirection（信号方向）
- `long` / `buy`: 做多/买入
- `short` / `sell`: 做空/卖出
- `hold`: 持有
- `close`: 平仓

### TradingBoard（交易板块）
- `main`: 主板
- `chinext`: 创业板
- `star`: 科创板

---

## 错误处理

### 标准错误响应

```json
{
  "error": "错误类型",
  "message": "详细错误信息",
  "path": "/api/v1/orders/"
}
```

### 常见HTTP状态码

- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

### 错误示例

**400 - 参数错误**:
```json
{
  "error": "Validation Error",
  "message": "Quantity must be multiple of 100 shares",
  "path": "/api/v1/orders/"
}
```

**404 - 资源不存在**:
```json
{
  "error": "Not Found",
  "message": "Order 12345 not found",
  "path": "/api/v1/orders/12345"
}
```

**500 - 服务器错误**:
```json
{
  "error": "Internal server error",
  "message": "Database connection failed",
  "path": "/api/v1/portfolio/summary"
}
```

---

## 使用示例

### Python示例

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# 创建策略
response = requests.post(
    f"{BASE_URL}/strategies/",
    json={
        "name": "test_strategy",
        "strategy_type": "swing_trading",
        "enabled": True,
        "symbols": ["000001", "600519"],
        "max_positions": 5,
        "position_size": 0.2,
        "stop_loss_pct": 0.08,
        "take_profit_pct": 0.15
    }
)
print(response.json())

# 获取市场行情
response = requests.get(f"{BASE_URL}/market/quote/000001")
quote = response.json()
print(f"Price: {quote['price']}")

# 创建订单
response = requests.post(
    f"{BASE_URL}/orders/",
    json={
        "symbol": "000001",
        "side": "buy",
        "order_type": "limit",
        "quantity": 1000,
        "price": 12.50,
        "strategy_name": "test_strategy"
    }
)
order = response.json()
print(f"Order ID: {order['id']}")

# 获取持仓
response = requests.get(f"{BASE_URL}/portfolio/positions")
positions = response.json()
for pos in positions:
    print(f"{pos['symbol']}: {pos['quantity']} shares")
```

### JavaScript/TypeScript示例

```typescript
const BASE_URL = 'http://localhost:8000/api/v1';

// 创建策略
async function createStrategy() {
  const response = await fetch(`${BASE_URL}/strategies/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: 'test_strategy',
      strategy_type: 'swing_trading',
      enabled: true,
      symbols: ['000001', '600519'],
      max_positions: 5,
      position_size: 0.2,
      stop_loss_pct: 0.08,
      take_profit_pct: 0.15,
    }),
  });

  const data = await response.json();
  console.log('Strategy created:', data);
}

// WebSocket连接示例
function connectWebSocket() {
  const ws = new WebSocket('ws://localhost:8000/ws/market');

  ws.onopen = () => {
    console.log('Connected to market data stream');

    // 订阅股票
    ws.send(JSON.stringify({
      action: 'subscribe',
      symbols: ['000001', '600519']
    }));
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);

    if (data.type === 'market_data') {
      console.log(`${data.symbol}: ${data.price}`);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('Disconnected from market data stream');
  };
}
```

### cURL示例

```bash
# 获取健康状态
curl http://localhost:8000/health

# 创建策略
curl -X POST http://localhost:8000/api/v1/strategies/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_strategy",
    "strategy_type": "swing_trading",
    "enabled": true,
    "symbols": ["000001"],
    "max_positions": 5,
    "position_size": 0.2,
    "stop_loss_pct": 0.08,
    "take_profit_pct": 0.15
  }'

# 获取行情
curl http://localhost:8000/api/v1/market/quote/000001

# 获取持仓
curl http://localhost:8000/api/v1/portfolio/positions

# 创建订单
curl -X POST http://localhost:8000/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "000001",
    "side": "buy",
    "order_type": "limit",
    "quantity": 1000,
    "price": 12.50,
    "strategy_name": "test_strategy"
  }'
```

---

## 开发建议

### 前端开发注意事项

1. **API基础URL**: 使用环境变量配置，开发环境和生产环境不同
2. **错误处理**: 统一处理HTTP错误状态码
3. **WebSocket重连**: 实现自动重连机制
4. **数据刷新**:
   - 实时数据使用WebSocket
   - 非实时数据可定期轮询REST API
5. **数据验证**:
   - 订单数量必须是100的倍数
   - 日期格式统一为 `YYYY-MM-DD`
   - 时间戳统一为ISO 8601格式

### TypeScript类型定义示例

```typescript
// 可以根据API响应创建TypeScript接口
interface Quote {
  symbol: string;
  price: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  change_pct?: number;
  timestamp: string;
}

interface Order {
  id: number;
  symbol: string;
  side: 'buy' | 'sell';
  order_type: 'market' | 'limit';
  quantity: number;
  price?: number;
  filled_quantity?: number;
  avg_filled_price?: number;
  status: 'pending' | 'submitted' | 'filled' | 'cancelled' | 'rejected';
  created_at: string;
  filled_at?: string;
}

interface Position {
  symbol: string;
  quantity: number;
  avg_cost: number;
  current_price?: number;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
  entry_date: string;
  strategy_name?: string;
}
```

---

## 更新日志

- **v0.1.0** (2024-01-15)
  - 初始API版本
  - 实现策略管理、市场数据、组合管理、订单管理、智能体、信号等模块
  - WebSocket实时推送

---

## 联系与支持

- **Swagger文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **GitHub**: (待添加)

---

**注意**:
1. 此API目前处于开发阶段，部分功能可能尚未完全实现
2. 生产环境需要添加认证和授权机制
3. 建议使用HTTPS协议保护数据传输安全
