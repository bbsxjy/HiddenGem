# HiddenGem Backend API 文档

**版本**: v1.0.0
**基础URL**: `http://localhost:8000/api/v1`
**WebSocket URL**: `ws://localhost:8000/ws`

---

## 📚 目录

- [认证](#认证)
- [响应格式](#响应格式)
- [错误处理](#错误处理)
- [Agent API](#agent-api)
- [Market API](#market-api)
- [Portfolio API](#portfolio-api)
- [Order API](#order-api)
- [Strategy API](#strategy-api)
- [WebSocket API](#websocket-api)
- [数据类型](#数据类型)

---

## 认证

当前版本：**无需认证**（开发阶段）

未来版本将支持：
- JWT Token认证
- API Key认证

---

## 响应格式

所有API响应遵循统一格式：

### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": { ... }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## 错误处理

### HTTP状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

### 错误代码

| 错误码 | 说明 |
|--------|------|
| `VALIDATION_ERROR` | 参数验证失败 |
| `AGENT_ERROR` | Agent分析失败 |
| `DATA_NOT_FOUND` | 数据不存在 |
| `INTERNAL_ERROR` | 内部服务器错误 |

---

## Agent API

### 1. 获取所有Agent状态

```
GET /agents/status
```

**响应示例**:

```json
{
  "success": true,
  "data": [
    {
      "name": "technical",
      "enabled": true,
      "weight": 1.0,
      "timeout": 30,
      "cache_ttl": 300
    },
    {
      "name": "fundamental",
      "enabled": true,
      "weight": 1.0,
      "timeout": 30,
      "cache_ttl": 300
    },
    {
      "name": "sentiment",
      "enabled": true,
      "weight": 1.0,
      "timeout": 30,
      "cache_ttl": 300
    },
    {
      "name": "market",
      "enabled": true,
      "weight": 1.0,
      "timeout": 30,
      "cache_ttl": 300
    },
    {
      "name": "policy",
      "enabled": true,
      "weight": 1.0,
      "timeout": 30,
      "cache_ttl": 300
    },
    {
      "name": "risk",
      "enabled": true,
      "weight": 1.0,
      "timeout": 30,
      "cache_ttl": 300
    },
    {
      "name": "execution",
      "enabled": true,
      "weight": 1.0,
      "timeout": 30,
      "cache_ttl": 300
    }
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 2. 单个Agent分析

```
POST /agents/{agent_name}/analyze
```

**路径参数**:
- `agent_name` (string): Agent名称，可选值：
  - `technical` - 技术分析
  - `fundamental` - 基本面分析
  - `sentiment` - 情绪分析
  - `market` - 市场分析
  - `policy` - 政策分析
  - `risk` - 风险分析
  - `execution` - 执行分析

**请求体**:

```json
{
  "symbol": "000001.SZ"
}
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "agent_name": "technical",
    "symbol": "000001.SZ",
    "score": 0.75,
    "direction": "long",
    "confidence": 0.8,
    "reasoning": "技术面分析显示该股票处于上升趋势，RSI指标未超买，MACD即将金叉...",
    "analysis": {
      "full_report": "完整的技术分析报告...",
      "indicators": {
        "rsi": 55.5,
        "macd": {"value": 0.5, "signal": 0.3, "histogram": 0.2},
        "ma20": 15.2,
        "ma50": 14.8
      }
    },
    "execution_time_ms": 1500,
    "timestamp": "2025-01-15T10:30:00Z",
    "is_error": false
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 3. 所有Agent联合分析

```
POST /agents/analyze-all/{symbol}
```

**路径参数**:
- `symbol` (string): 股票代码，例如 `000001.SZ`, `600036.SS`, `0700.HK`

**响应示例**:

```json
{
  "success": true,
  "data": {
    "symbol": "000001.SZ",
    "agent_results": {
      "technical": {
        "direction": "long",
        "confidence": 0.8,
        "score": 0.75,
        "reasoning": "技术面强势...",
        "is_error": false
      },
      "fundamental": {
        "direction": "long",
        "confidence": 0.75,
        "score": 0.7,
        "reasoning": "基本面稳健...",
        "is_error": false
      },
      "sentiment": {
        "direction": "hold",
        "confidence": 0.6,
        "score": 0.5,
        "reasoning": "市场情绪中性...",
        "is_error": false
      },
      "policy": {
        "direction": "long",
        "confidence": 0.7,
        "score": 0.65,
        "reasoning": "政策面支持...",
        "is_error": false
      }
    },
    "aggregated_signal": {
      "direction": "long",
      "confidence": 0.85,
      "position_size": 0.1,
      "num_agreeing_agents": 3,
      "warnings": [],
      "metadata": {
        "analysis_method": "llm",
        "llm_reasoning": "综合各方面分析...",
        "risk_assessment": "中等风险",
        "key_factors": ["技术面强势", "基本面稳健", "政策支持"],
        "agent_count": 4,
        "agreeing_agents": 3,
        "total_agents": 4
      }
    },
    "signal_rejection_reason": null,
    "llm_analysis": {
      "recommended_direction": "long",
      "confidence": 0.85,
      "reasoning": "综合七个Agent的分析结果，该股票整体表现强势，建议做多...",
      "risk_assessment": "中等风险，建议仓位控制在10%以内",
      "key_factors": [
        "技术面显示上升趋势",
        "基本面财务健康",
        "政策面有利支持",
        "市场情绪相对稳定"
      ],
      "price_targets": {
        "entry": 15.0,
        "stop_loss": 13.5,
        "take_profit": 17.0
      },
      "analysis_timestamp": "2025-01-15T10:30:00Z"
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 4. 流式分析（SSE）

```
POST /agents/analyze-all/{symbol}/stream
```

**说明**: 使用Server-Sent Events (SSE)实时推送分析进度

**路径参数**:
- `symbol` (string): 股票代码

**响应格式**: `text/event-stream`

**事件类型**:

#### 4.1 开始事件

```json
{
  "type": "start",
  "symbol": "000001.SZ",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### 4.2 Agent结果事件

```json
{
  "type": "agent_result",
  "agent_name": "technical",
  "progress": "1/4",
  "result": {
    "direction": "long",
    "confidence": 0.8,
    "score": 0.75,
    "reasoning": "技术面分析...",
    "is_error": false
  },
  "timestamp": "2025-01-15T10:30:05Z"
}
```

#### 4.3 Agent错误事件

```json
{
  "type": "agent_error",
  "agent_name": "fundamental",
  "error": "数据获取失败",
  "timestamp": "2025-01-15T10:30:10Z"
}
```

#### 4.4 LLM开始事件

```json
{
  "type": "llm_start",
  "message": "正在进行最终综合分析...",
  "timestamp": "2025-01-15T10:30:30Z"
}
```

#### 4.5 完成事件

```json
{
  "type": "complete",
  "data": {
    // 与 /analyze-all 响应格式相同
  },
  "timestamp": "2025-01-15T10:30:45Z"
}
```

#### 4.6 错误事件

```json
{
  "type": "error",
  "error": "分析过程中发生错误",
  "timestamp": "2025-01-15T10:30:15Z"
}
```

**客户端使用示例（JavaScript）**:

```javascript
const eventSource = new EventSource('http://localhost:8000/api/v1/agents/analyze-all/000001.SZ/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'start':
      console.log('分析开始:', data.symbol);
      break;
    case 'agent_result':
      console.log(`${data.agent_name} 完成 (${data.progress}):`, data.result);
      break;
    case 'complete':
      console.log('分析完成:', data.data);
      eventSource.close();
      break;
    case 'error':
      console.error('分析错误:', data.error);
      eventSource.close();
      break;
  }
};

eventSource.onerror = (error) => {
  console.error('连接错误:', error);
  eventSource.close();
};
```

### 5. 获取Agent性能指标

```
GET /agents/performance
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "message": "Agent性能统计",
    "agents": [
      "technical",
      "fundamental",
      "sentiment",
      "market",
      "policy",
      "risk",
      "execution"
    ]
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Market API

### 1. 获取市场数据（K线）

```
GET /market/data/{symbol}
```

**路径参数**:
- `symbol` (string): 股票代码

**查询参数**:
- `start_date` (string, 可选): 开始日期，格式 `YYYY-MM-DD`，默认为30天前
- `end_date` (string, 可选): 结束日期，格式 `YYYY-MM-DD`，默认为今天

**响应示例**:

```json
{
  "success": true,
  "data": {
    "symbol": "000001.SZ",
    "market": "A股主板",
    "data": [
      {
        "date": "2025-01-15",
        "open": 15.0,
        "high": 15.5,
        "low": 14.8,
        "close": 15.2,
        "volume": 1000000,
        "amount": 15200000,
        "change": 0.02,
        "change_pct": 0.0132
      }
    ],
    "count": 30
  },
  "message": "成功获取000001.SZ市场数据",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 2. 获取股票基本信息

```
GET /market/info/{symbol}
```

**路径参数**:
- `symbol` (string): 股票代码

**响应示例**:

```json
{
  "success": true,
  "data": {
    "symbol": "000001.SZ",
    "name": "平安银行",
    "market": "深交所",
    "board": "主板",
    "industry": "银行",
    "sector": "金融",
    "list_date": "1991-04-03",
    "market_cap": 250000000000,
    "float_market_cap": 200000000000,
    "total_shares": 19405918198,
    "float_shares": 19405918198,
    "currency": "CNY"
  },
  "message": "成功获取000001.SZ基本信息",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 3. 股票搜索

```
GET /market/search
```

**查询参数**:
- `query` (string): 搜索关键词（股票代码或名称）
- `market` (string, 可选): 市场类型，可选值：`cn` (A股), `hk` (港股), `us` (美股)
- `limit` (int, 可选): 返回结果数量，默认10

**响应示例**:

```json
{
  "success": true,
  "data": {
    "query": "平安",
    "results": [
      {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "market": "深交所",
        "board": "主板"
      },
      {
        "symbol": "601318.SS",
        "name": "中国平安",
        "market": "上交所",
        "board": "主板"
      }
    ],
    "count": 2
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Portfolio API

### 1. 获取当前持仓

```
GET /portfolio/positions
```

**响应示例**:

```json
{
  "success": true,
  "data": [
    {
      "symbol": "000001.SZ",
      "name": "平安银行",
      "quantity": 1000,
      "avg_price": 14.5,
      "current_price": 15.2,
      "market_value": 15200,
      "cost": 14500,
      "profit": 700,
      "profit_pct": 0.0483,
      "position_pct": 0.152,
      "last_updated": "2025-01-15T10:30:00Z"
    }
  ],
  "total_market_value": 100000,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 2. 获取投资组合摘要

```
GET /portfolio/summary
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "total_value": 1000000,
    "cash": 500000,
    "positions_value": 500000,
    "daily_pnl": 5000,
    "daily_pnl_pct": 0.005,
    "total_pnl": 50000,
    "total_pnl_pct": 0.05,
    "position_count": 10
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 3. 获取历史净值

```
GET /portfolio/history
```

**查询参数**:
- `start_date` (string, 可选): 开始日期，格式 `YYYY-MM-DD`
- `end_date` (string, 可选): 结束日期，格式 `YYYY-MM-DD`

**响应示例**:

```json
{
  "success": true,
  "data": [
    {
      "date": "2025-01-15",
      "total_value": 1000000,
      "cash": 500000,
      "positions_value": 500000,
      "daily_return": 0.005,
      "cumulative_return": 0.05
    }
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 4. 获取绩效指标

```
GET /portfolio/performance
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "total_return": 0.05,
    "annual_return": 0.12,
    "sharpe_ratio": 1.5,
    "max_drawdown": -0.15,
    "win_rate": 0.6,
    "profit_factor": 2.0,
    "trades_count": 100,
    "avg_holding_days": 5
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Order API

### 1. 创建订单

```
POST /orders/create
```

**请求体**:

```json
{
  "symbol": "000001.SZ",
  "direction": "long",
  "quantity": 1000,
  "order_type": "market",
  "price": null,
  "stop_loss": 13.5,
  "take_profit": 17.0
}
```

**字段说明**:
- `symbol` (string): 股票代码
- `direction` (string): 方向，`long` (做多) 或 `short` (做空)
- `quantity` (int): 数量
- `order_type` (string): 订单类型，`market` (市价单) 或 `limit` (限价单)
- `price` (float, 可选): 限价单价格
- `stop_loss` (float, 可选): 止损价
- `take_profit` (float, 可选): 止盈价

**响应示例**:

```json
{
  "success": true,
  "data": {
    "order_id": "ORD20250115001",
    "symbol": "000001.SZ",
    "direction": "long",
    "quantity": 1000,
    "order_type": "market",
    "price": null,
    "status": "pending",
    "created_at": "2025-01-15T10:30:00Z"
  },
  "message": "订单创建成功",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 2. 获取订单列表

```
GET /orders/list
```

**查询参数**:
- `status` (string, 可选): 订单状态，`pending`, `filled`, `cancelled`, `rejected`
- `symbol` (string, 可选): 股票代码
- `start_date` (string, 可选): 开始日期
- `end_date` (string, 可选): 结束日期
- `limit` (int, 可选): 返回数量，默认20

**响应示例**:

```json
{
  "success": true,
  "data": [
    {
      "order_id": "ORD20250115001",
      "symbol": "000001.SZ",
      "direction": "long",
      "quantity": 1000,
      "order_type": "market",
      "price": null,
      "filled_price": 15.2,
      "status": "filled",
      "created_at": "2025-01-15T10:30:00Z",
      "filled_at": "2025-01-15T10:30:05Z"
    }
  ],
  "count": 1,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 3. 获取订单详情

```
GET /orders/{order_id}
```

**路径参数**:
- `order_id` (string): 订单ID

**响应示例**:

```json
{
  "success": true,
  "data": {
    "order_id": "ORD20250115001",
    "symbol": "000001.SZ",
    "name": "平安银行",
    "direction": "long",
    "quantity": 1000,
    "order_type": "market",
    "price": null,
    "filled_price": 15.2,
    "filled_quantity": 1000,
    "status": "filled",
    "stop_loss": 13.5,
    "take_profit": 17.0,
    "commission": 15.2,
    "created_at": "2025-01-15T10:30:00Z",
    "filled_at": "2025-01-15T10:30:05Z",
    "cancelled_at": null,
    "cancel_reason": null
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 4. 取消订单

```
POST /orders/{order_id}/cancel
```

**路径参数**:
- `order_id` (string): 订单ID

**响应示例**:

```json
{
  "success": true,
  "data": {
    "order_id": "ORD20250115001",
    "status": "cancelled",
    "cancelled_at": "2025-01-15T10:35:00Z"
  },
  "message": "订单取消成功",
  "timestamp": "2025-01-15T10:35:00Z"
}
```

---

## Strategy API

### 1. 获取策略列表

```
GET /strategies/list
```

**响应示例**:

```json
{
  "success": true,
  "data": [
    {
      "strategy_id": "STRAT001",
      "name": "趋势跟随策略",
      "type": "trend_following",
      "status": "active",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 2. 回测策略

```
POST /strategies/backtest
```

**请求体**:

```json
{
  "strategy_id": "STRAT001",
  "symbols": ["000001.SZ", "600036.SS"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 1000000
}
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "strategy_id": "STRAT001",
    "backtest_id": "BT20250115001",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_capital": 1000000,
    "final_capital": 1200000,
    "total_return": 0.2,
    "annual_return": 0.2,
    "sharpe_ratio": 1.8,
    "max_drawdown": -0.12,
    "win_rate": 0.65,
    "trades_count": 50,
    "status": "completed"
  },
  "message": "回测完成",
  "timestamp": "2025-01-15T10:35:00Z"
}
```

---

## WebSocket API

### 连接地址

```
ws://localhost:8000/ws
```

### 消息格式

所有消息使用JSON格式。

### 客户端 → 服务器

#### 1. 订阅股票行情

```json
{
  "type": "subscribe",
  "symbol": "000001.SZ"
}
```

**响应**:

```json
{
  "type": "subscribed",
  "symbol": "000001.SZ",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### 2. 取消订阅

```json
{
  "type": "unsubscribe",
  "symbol": "000001.SZ"
}
```

**响应**:

```json
{
  "type": "unsubscribed",
  "symbol": "000001.SZ",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### 3. 心跳检测

```json
{
  "type": "ping"
}
```

**响应**:

```json
{
  "type": "pong",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 服务器 → 客户端

#### 1. 市场数据更新

```json
{
  "type": "market_update",
  "symbol": "000001.SZ",
  "price": 15.23,
  "change": 0.05,
  "change_pct": 0.0033,
  "volume": 1000000,
  "amount": 15230000,
  "high": 15.5,
  "low": 14.8,
  "open": 15.0,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### 2. 订单状态变化

```json
{
  "type": "order_status",
  "order_id": "ORD20250115001",
  "symbol": "000001.SZ",
  "status": "filled",
  "filled_price": 15.2,
  "filled_quantity": 1000,
  "timestamp": "2025-01-15T10:30:05Z"
}
```

#### 3. Agent分析结果

```json
{
  "type": "agent_analysis",
  "symbol": "000001.SZ",
  "agent_name": "technical",
  "direction": "long",
  "confidence": 0.8,
  "reasoning": "技术面分析...",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### 4. 投资组合更新

```json
{
  "type": "portfolio_update",
  "total_value": 1005000,
  "cash": 500000,
  "positions_value": 505000,
  "daily_pnl": 5000,
  "daily_pnl_pct": 0.005,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### 5. 交易信号

```json
{
  "type": "signal",
  "symbol": "000001.SZ",
  "direction": "long",
  "confidence": 0.85,
  "reason": "多个Agent建议做多",
  "price_targets": {
    "entry": 15.0,
    "stop_loss": 13.5,
    "take_profit": 17.0
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### JavaScript客户端示例

```javascript
// 创建WebSocket连接
const ws = new WebSocket('ws://localhost:8000/ws');

// 连接成功
ws.onopen = () => {
  console.log('WebSocket connected');

  // 订阅股票行情
  ws.send(JSON.stringify({
    type: 'subscribe',
    symbol: '000001.SZ'
  }));

  // 启动心跳
  setInterval(() => {
    ws.send(JSON.stringify({ type: 'ping' }));
  }, 30000);
};

// 接收消息
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch(data.type) {
    case 'market_update':
      console.log('市场更新:', data.symbol, data.price);
      break;
    case 'order_status':
      console.log('订单状态:', data.order_id, data.status);
      break;
    case 'signal':
      console.log('交易信号:', data.symbol, data.direction);
      break;
    case 'pong':
      console.log('心跳响应');
      break;
  }
};

// 连接关闭
ws.onclose = () => {
  console.log('WebSocket disconnected');
  // 实现重连逻辑
};

// 错误处理
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

---

## 数据类型

### AgentName

```typescript
type AgentName =
  | 'technical'
  | 'fundamental'
  | 'sentiment'
  | 'market'
  | 'policy'
  | 'risk'
  | 'execution';
```

### SignalDirection

```typescript
type SignalDirection = 'long' | 'short' | 'hold' | 'close';
```

### OrderStatus

```typescript
type OrderStatus = 'pending' | 'filled' | 'partial_filled' | 'cancelled' | 'rejected';
```

### OrderType

```typescript
type OrderType = 'market' | 'limit' | 'stop' | 'stop_limit';
```

### Market

```typescript
type Market = 'cn' | 'hk' | 'us';
```

---

## 速率限制

当前版本：**无限制**（开发阶段）

未来版本将实施：
- 普通用户：100请求/分钟
- VIP用户：1000请求/分钟

---

## 版本历史

### v1.0.0 (2025-01-15)
- 初始版本
- 支持Agent分析API
- 支持市场数据API
- 支持投资组合API
- 支持订单API
- 支持WebSocket实时推送

---

## 联系方式

- GitHub Issues: [项目仓库](https://github.com/your-repo)
- Email: support@hiddengem.com

---

**最后更新**: 2025-01-15
**维护者**: HiddenGem Team
