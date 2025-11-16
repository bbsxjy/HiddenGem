# 持仓分析 API 文档

## 概述

持仓分析 API 为已有持仓的用户提供下一步决策建议，包括：
- 是否应该卖出/持有/加仓
- 建议的操作价位
- 如果不卖是否能回本的分析
- 综合市场分析和持仓成本的风险评估

## API 端点

```
POST /api/v1/agents/analyze-position/{symbol}
```

## 请求参数

### Path Parameters
- `symbol` (string, required): 股票代码
  - A股示例: `000001`, `600000`, `300502`
  - 港股示例: `00700.HK`, `09988.HK`
  - 美股示例: `AAPL`, `TSLA`, `NVDA`

### Request Body

```json
{
  "holdings": {
    "quantity": 1000,              // 持仓数量（股）
    "avg_price": 45.50,            // 平均买入价（元/美元）
    "purchase_date": "2024-12-01", // 买入日期 (YYYY-MM-DD)
    "current_price": 42.30         // 当前价格（可选，会自动获取）
  },
  "analysis_date": "2025-01-06"    // 分析日期（可选，默认今天）
}
```

### Request Body 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `holdings.quantity` | float | ✅ | 持仓数量 |
| `holdings.avg_price` | float | ✅ | 平均买入价格 |
| `holdings.purchase_date` | string | ✅ | 买入日期，格式: YYYY-MM-DD |
| `holdings.current_price` | float | ❌ | 当前价格（可选，系统会自动估算） |
| `analysis_date` | string | ❌ | 分析日期，格式: YYYY-MM-DD，默认今天 |

## 响应格式

```json
{
  "success": true,
  "data": {
    "symbol": "300502",
    "analysis_date": "2025-01-06",

    // 完整的市场分析（与 /analyze-all 接口相同）
    "market_analysis": {
      "agent_results": {...},
      "aggregated_signal": {...},
      "llm_analysis": {...}
    },

    // 持仓决策建议（新增）
    "position_analysis": {
      // 主要决策
      "action": "卖出",           // 卖出/持有/加仓
      "urgency": "短期",          // 立即/短期/中期/长期
      "reasoning": "当前亏损7%，市场分析显示继续下跌风险高，建议止损",

      // 盈亏信息
      "profit_loss": {
        "current_pnl": -3200.00,    // 浮动盈亏（元）
        "current_pnl_pct": -7.03,   // 浮动盈亏百分比
        "holding_days": 36,         // 持仓天数
        "cost_price": 45.50,        // 成本价
        "current_price": 42.30,     // 当前价
        "quantity": 1000            // 持仓量
      },

      // 三个方向的详细建议
      "recommendations": {
        "sell": {
          "should_sell": true,
          "suggested_price": 42.0,
          "reason": "当前价位及时止损，避免更大损失"
        },
        "hold": {
          "should_hold": false,
          "hold_until": "市场企稳，基本面改善",
          "reason": "风险较高，不建议继续持有"
        },
        "add": {
          "should_add": false,
          "suggested_price": null,
          "suggested_quantity": null,
          "reason": "下跌趋势未结束，不建议加仓"
        }
      },

      // 回本分析
      "recovery_analysis": {
        "can_recover": true,           // 是否可能回本
        "estimated_days": 45,          // 预计回本天数
        "probability": 0.35,           // 回本概率（0-1）
        "conditions": "需要市场整体反弹，公司基本面改善"
      },

      // 风险警告
      "risk_warnings": [
        "当前技术面弱势，下跌风险较高",
        "基本面存在不确定性",
        "市场情绪偏空"
      ]
    }
  },
  "message": "持仓分析完成: 300502",
  "timestamp": "2025-01-06T15:30:00.000Z"
}
```

## 使用示例

### Python 示例

```python
import requests

# API 基础 URL
base_url = "http://localhost:8000"

# 持仓信息
holdings = {
    "quantity": 1000,
    "avg_price": 45.50,
    "purchase_date": "2024-12-01",
    "current_price": 42.30  # 可选
}

# 发送请求
response = requests.post(
    f"{base_url}/api/v1/agents/analyze-position/300502",
    json={
        "holdings": holdings,
        "analysis_date": "2025-01-06"
    }
)

# 处理响应
if response.status_code == 200:
    result = response.json()

    if result["success"]:
        pos_analysis = result["data"]["position_analysis"]

        print(f"持仓决策: {pos_analysis['action']}")
        print(f"紧急程度: {pos_analysis['urgency']}")
        print(f"决策理由: {pos_analysis['reasoning']}")

        # 盈亏信息
        pnl = pos_analysis['profit_loss']
        print(f"\n盈亏情况:")
        print(f"  浮动盈亏: ¥{pnl['current_pnl']:,.2f} ({pnl['current_pnl_pct']:+.2f}%)")
        print(f"  持仓天数: {pnl['holding_days']}天")

        # 回本分析
        recovery = pos_analysis['recovery_analysis']
        print(f"\n回本分析:")
        print(f"  是否可能回本: {'是' if recovery['can_recover'] else '否'}")
        if recovery['estimated_days']:
            print(f"  预计天数: {recovery['estimated_days']}天")
        print(f"  回本概率: {recovery['probability']:.0%}")
```

### JavaScript/TypeScript 示例

```typescript
interface HoldingsInfo {
  quantity: number;
  avg_price: number;
  purchase_date: string;
  current_price?: number;
}

interface PositionAnalysisRequest {
  holdings: HoldingsInfo;
  analysis_date?: string;
}

async function analyzePosition(
  symbol: string,
  request: PositionAnalysisRequest
) {
  const response = await fetch(
    `http://localhost:8000/api/v1/agents/analyze-position/${symbol}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    }
  );

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const result = await response.json();
  return result.data;
}

// 使用示例
const holdings: HoldingsInfo = {
  quantity: 1000,
  avg_price: 45.50,
  purchase_date: "2024-12-01",
  current_price: 42.30
};

analyzePosition("300502", { holdings })
  .then(data => {
    const pos = data.position_analysis;
    console.log(`持仓决策: ${pos.action}`);
    console.log(`决策理由: ${pos.reasoning}`);
    console.log(`浮动盈亏: ${pos.profit_loss.current_pnl_pct.toFixed(2)}%`);
  })
  .catch(error => {
    console.error('分析失败:', error);
  });
```

### cURL 示例

```bash
curl -X POST "http://localhost:8000/api/v1/agents/analyze-position/300502" \
  -H "Content-Type: application/json" \
  -d '{
    "holdings": {
      "quantity": 1000,
      "avg_price": 45.50,
      "purchase_date": "2024-12-01",
      "current_price": 42.30
    },
    "analysis_date": "2025-01-06"
  }'
```

## 决策逻辑

### action 字段可能的值

| 值 | 说明 | 典型场景 |
|----|------|----------|
| `卖出` | 建议卖出 | 亏损且市场看空；盈利且市场转空（止盈） |
| `持有` | 建议继续持有 | 暂时亏损但市场看多；盈利且继续看多 |
| `加仓` | 建议增加仓位 | 市场看多且价格回调到理想位置 |

### urgency 字段可能的值

| 值 | 说明 | 时间范围 |
|----|------|----------|
| `立即` | 立即操作 | 1-3个交易日 |
| `短期` | 近期操作 | 1-2周 |
| `中期` | 中期操作 | 2-4周 |
| `长期` | 长期持有 | 1个月以上 |

## 分析逻辑说明

持仓分析会综合考虑：

1. **持仓成本** - 当前盈亏状况
2. **市场分析** - 7个Agent的综合建议
3. **风险评估** - 继续持有的风险
4. **回本可能性** - 如果亏损，评估回本概率

### 决策矩阵示例

| 盈亏状态 | 市场建议 | 决策 | 理由 |
|---------|---------|------|------|
| 亏损 >10% | 看空 | 卖出 | 止损，避免更大损失 |
| 亏损 <10% | 看空 | 视情况 | 评估回本概率 |
| 盈利 >10% | 看空 | 卖出 | 止盈，锁定利润 |
| 盈利 >10% | 看多 | 持有/加仓 | 继续持有，享受上涨 |
| 亏损 | 看多 | 持有 | 等待回本 |

## 错误处理

### 常见错误码

| HTTP 状态码 | 说明 | 解决方案 |
|------------|------|----------|
| 400 | 请求参数错误 | 检查请求格式和必填字段 |
| 500 | 服务器内部错误 | 查看后端日志，联系支持 |
| 503 | TradingGraph 未初始化 | 等待系统初始化完成 |

### 错误响应示例

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "holdings.quantity 必须大于 0",
    "details": {...}
  },
  "timestamp": "2025-01-06T15:30:00.000Z"
}
```

## 性能说明

- **响应时间**: 30-60秒（包含完整的7个Agent分析）
- **并发支持**: 建议使用流式接口或队列处理高并发请求
- **缓存**: 市场分析结果可以缓存5分钟

## 注意事项

1. **current_price 参数**
   - 如果不提供，系统会使用分析中的目标价作为参考
   - 建议前端实时获取当前价格并传入，以获得更准确的盈亏计算

2. **回本分析的准确性**
   - 基于历史数据和市场趋势的统计分析
   - 仅供参考，不构成投资建议

3. **决策建议的使用**
   - 建议结合个人风险偏好和投资目标
   - 系统提供的是专业分析，最终决策由用户自行判断

## 相关 API

- `POST /api/v1/agents/analyze-all/{symbol}` - 纯市场分析（不考虑持仓）
- `GET /api/v1/agents/analyze-all-stream/{symbol}` - 流式市场分析

## 更新日志

- **2025-01-06**: 首次发布
  - 支持 A股、港股、美股
  - 提供卖出/持有/加仓三个方向的建议
  - 包含回本可能性分析

---

**文档版本**: 1.0
**最后更新**: 2025-01-06
