# 后端回测API数据结构总结

## API端点
`POST /api/v1/backtest/qflib/run`

## 返回数据结构

```typescript
{
  success: boolean,
  data: {
    summary: {
      initial_capital: number,        // 初始资金
      final_value: number,            // 最终资金
      total_return: number,           // 总收益率（小数，如0.9051表示90.51%）
      total_return_pct: number,       // 总收益率（百分比，如90.51）
      max_drawdown: number,           // 最大回撤（小数）
      max_drawdown_pct: number,       // 最大回撤（百分比）
      total_trades: number,           // 总交易次数
      sharpe_ratio: number,           // 夏普比率
      win_rate: number,               // 胜率（小数，如0.58表示58%）
      avg_holding_days: number        // 平均持仓天数
    },
    equity_curve: [
      {
        date: "2025-01-02",           // 日期字符串 YYYY-MM-DD
        portfolio_value: 100000,      // 账户总价值（现金+持仓市值）
        cash: 100000                  // 现金余额
      },
      // ... 每个交易日一条记录
    ],
    trades: [
      {
        date: "2025-05-08",           // 交易日期
        ticker: "300502",             // 股票代码
        action: "BUY_25",             // 交易动作: BUY_25, BUY_50, SELL_50, SELL_ALL
        shares: 2800,                 // 交易股数
        price: 8.92,                  // 成交价格
        cost: 24976.0,                // 买入成本（仅买入）
        revenue: null,                // 卖出收入（仅卖出）
        commission: 10.0,             // 手续费
        total_cost: 24986.0,          // 总成本（成本+手续费，仅买入）
        total_revenue: null           // 总收入（收入-手续费-印花税，仅卖出）
      },
      // ... 每笔交易一条记录
    ]
  }
}
```

## 关键数据点

### equity_curve (资金曲线)
- **字段**：`date`, `portfolio_value`, `cash`
- **数量**：每个交易日一条记录（如209条）
- **特点**：
  - `portfolio_value` = `cash` + 所有持仓市值
  - 可能存在空仓期（前N天portfolio_value = initial_capital）
  - 值从最低90K到最高199K（示例数据）

### trades (交易记录)
- **字段**：`date`, `ticker`, `action`, `shares`, `price`, `commission`, `total_cost`/`total_revenue`
- **数量**：每笔交易一条记录（如5条）
- **动作类型**：
  - `BUY_25`: 用25%现金买入
  - `BUY_50`: 用50%现金买入
  - `SELL_50`: 卖出50%持仓
  - `SELL_ALL`: 全部卖出

## 前端需要处理的问题

1. **日期格式**：后端返回 `"2025-01-02"`，需要保持完整性用于X轴dataKey
2. **空仓期**：可能前38%的数据点portfolio_value都等于initial_capital（无变化）
3. **数据映射**：equity_curve使用`portfolio_value`，需要映射为前端的`value`字段
4. **交易点标记**：需要将trades的date匹配到equity_curve的对应点上
