# Portfolio-Based Training Design
# 组合式训练方案设计

## 核心思想

从**单股票训练**升级到**组合管理训练**，记录完整的决策链：
- 市场环境 → 板块选择 → 个股筛选 → 组合管理 → 交易结果

---

## 训练数据结构

### 1. 每日训练输入

```python
TrainingContext = {
    "date": "2024-07-01",
    "market_env": {
        "index_trend": "上证指数 +1.2%",
        "market_sentiment": "偏多",
        "hot_sectors": ["科技", "消费"],
        "capital_flow": {
            "northbound": "+50亿",
            "main_force": "流入科技板块"
        }
    },
    "focus_sectors": ["金融", "科技", "消费", "医药", "周期"],
    "current_portfolio": [
        {"symbol": "000001.SZ", "shares": 1000, "cost": 10.5, "days_held": 3},
        {"symbol": "600519.SH", "shares": 100, "cost": 1850, "days_held": 5}
    ],
    "available_cash": 50000  # 可用资金
}
```

### 2. Memory Bank记录格式

```python
PortfolioEpisode = {
    "episode_id": "2024-07-01_portfolio",
    "date": "2024-07-01",

    # 市场分析
    "market_analysis": {
        "environment": "震荡市",
        "sentiment": "中性偏多",
        "hot_sectors": ["科技", "消费"]
    },

    # 板块决策
    "sector_decisions": [
        {
            "sector": "科技",
            "score": 0.85,
            "reasoning": "5G基站建设加速，半导体国产化加速",
            "selected_stocks": ["000063.SZ", "002415.SZ"]
        },
        {
            "sector": "消费",
            "score": 0.72,
            "reasoning": "消费数据回暖，白酒库存处于低位",
            "selected_stocks": ["600519.SH"]
        }
    ],

    # 个股决策
    "stock_decisions": [
        {
            "symbol": "000063.SZ",
            "action": "buy",
            "reasoning": "技术面突破，资金持续流入",
            "allocation": 0.20,  # 20%仓位
            "entry_price": 45.30
        },
        {
            "symbol": "000001.SZ",
            "action": "sell",
            "reasoning": "已持有5天，达到止盈目标",
            "exit_price": 11.20
        }
    ],

    # 组合变化
    "portfolio_changes": {
        "before": [
            {"symbol": "000001.SZ", "weight": 0.25},
            {"symbol": "600519.SH", "weight": 0.30}
        ],
        "after": [
            {"symbol": "600519.SH", "weight": 0.30},
            {"symbol": "000063.SZ", "weight": 0.20},
            {"symbol": "002415.SZ", "weight": 0.15}
        ]
    },

    # 结果评估（5天后）
    "outcomes": [
        {
            "symbol": "000063.SZ",
            "return": 0.08,  # +8%
            "success": True,
            "lesson": "科技板块在5G政策驱动下表现强劲，选股正确"
        },
        {
            "symbol": "000001.SZ",
            "return": 0.067,  # +6.7%
            "success": True,
            "lesson": "及时止盈，避免了后续回调"
        }
    ],

    # 综合教训
    "portfolio_lesson": """
    # 组合管理经验：震荡市中的板块轮动

    ## 市场环境
    - 大盘震荡，个股分化
    - 政策驱动明显（5G建设）
    - 资金偏好确定性机会

    ## 决策过程
    1. **板块选择正确**：科技板块有政策催化，消费板块估值合理
    2. **个股筛选合理**：选择龙头股，避免跟风炒作
    3. **仓位分配得当**：单只不超过30%，保持分散
    4. **及时止盈**：金融股达到目标后果断卖出

    ## 成功原因
    - 抓住了政策驱动的主线（5G）
    - 选择了板块内的龙头
    - 仓位控制合理，风险分散

    ## 关键经验
    - 震荡市中，板块轮动比个股更重要
    - 政策驱动的板块持续性强
    - 及时止盈比持股待涨更安全
    """
}
```

---

## 训练脚本伪代码

```python
class PortfolioTrainer:
    def __init__(self):
        self.sectors = ["金融", "科技", "消费", "医药", "周期"]
        self.max_positions = 5
        self.position_size = 0.2  # 每只20%
        self.holding_days = 5

    def train_one_day(self, date):
        # 1. 分析市场环境
        market_env = self.analyze_market(date)

        # 2. 分析所有板块
        sector_scores = {}
        for sector in self.sectors:
            score = self.analyze_sector(sector, date, market_env)
            sector_scores[sector] = score

        # 3. 选择Top 2-3 板块
        top_sectors = self.select_top_sectors(sector_scores, top_k=3)

        # 4. 从每个板块选择1-2只股票
        stock_candidates = []
        for sector in top_sectors:
            stocks = self.get_sector_stocks(sector)
            for stock in stocks:
                analysis = self.analyze_stock(stock, date)
                stock_candidates.append({
                    "symbol": stock,
                    "sector": sector,
                    "score": analysis["score"],
                    "reasoning": analysis["reasoning"]
                })

        # 5. 组合决策
        portfolio_decisions = self.make_portfolio_decisions(
            current_portfolio=self.get_current_portfolio(),
            candidates=stock_candidates,
            max_positions=self.max_positions
        )

        # 6. 模拟执行并记录
        outcomes = []
        for decision in portfolio_decisions:
            outcome = self.simulate_trade(decision, self.holding_days)
            outcomes.append(outcome)

        # 7. 生成综合经验
        episode = self.create_portfolio_episode(
            date=date,
            market_env=market_env,
            sector_analysis=sector_scores,
            stock_decisions=portfolio_decisions,
            outcomes=outcomes
        )

        self.memory_manager.add_episode(episode)

        return episode
```

---

## 训练数据集建议

### 方案A：精选股票池（推荐新手）

每个板块选3-5只代表股票：

```python
STOCK_POOL = {
    "金融": ["600036.SH", "601318.SH", "600519.SH"],  # 招商银行、平安、茅台
    "科技": ["000063.SZ", "002415.SZ", "600584.SH"],  # 中兴、海康、长电
    "消费": ["600519.SH", "000858.SZ", "603288.SH"],  # 茅台、五粮液、海天
    "医药": ["600276.SH", "000661.SZ", "300015.SZ"],  # 恒瑞、长春高新、爱尔
    "周期": ["600019.SH", "601899.SH", "600309.SH"]   # 宝钢、紫金、万华
}

# 训练：2024年7-8月，每天从15只股票中选5只
```

### 方案B：动态股票池（推荐进阶）

根据实时数据筛选：

```python
def get_sector_top_stocks(sector, date, top_k=5):
    """
    从板块中动态筛选Top K股票
    - 涨幅排名
    - 成交量排名
    - 资金流入排名
    """
    all_stocks = get_all_stocks_in_sector(sector, date)

    # 多维度评分
    scored = []
    for stock in all_stocks:
        score = calculate_stock_score(
            stock, date,
            factors=["momentum", "volume", "fundamentals"]
        )
        scored.append((stock, score))

    # 返回Top K
    return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]
```

---

## Memory Bank查询场景

训练完成后，Memory Bank可以回答：

### 场景1：板块选择
```
Q: 在震荡市中，哪个板块表现最好？
A: 根据10个震荡市案例，科技板块胜率65%，平均收益+3.2%
   主要原因：政策驱动 + 资金抱团
```

### 场景2：个股筛选
```
Q: 科技板块中，如何选择个股？
A: 优先选择：
   1. 技术面突破的龙头股（胜率70%）
   2. 资金连续流入3天以上（胜率68%）
   3. 避免：跟风炒作的小盘股（胜率仅30%）
```

### 场景3：仓位管理
```
Q: 5只股票如何分配仓位？
A: 根据25个案例：
   - 龙头股：30%
   - 次龙头：20% x 2
   - 潜力股：15% x 2
   - 现金：15%（应对突发）
```

---

## 实施建议

### 阶段1：简化版（1-2周）
- 固定5只股票（每个板块1只）
- 每天只做买入/持有/卖出决策
- 记录：股票选择 + 交易结果

### 阶段2：完整版（1个月）
- 15只股票池（每个板块3只）
- 每天最多持仓5只
- 记录：板块选择 + 个股筛选 + 组合管理

### 阶段3：进阶版（长期）
- 动态股票池（实时筛选）
- 板块轮动策略
- 多策略组合（价值 + 成长 + 趋势）

---

## 评估指标

训练质量评估：

1. **板块选择准确率**
   - 选中的板块 vs 实际表现最好的板块

2. **个股选择胜率**
   - 买入股票的盈利概率

3. **组合收益**
   - 总收益率 vs 大盘
   - 夏普比率

4. **风险控制**
   - 最大回撤
   - 单只最大亏损

---

## 总结

**关键改进**：

| 维度 | 当前（单股票） | 改进后（组合） |
|------|--------------|--------------|
| 训练对象 | 1只股票 | 5-15只股票池 |
| 决策层次 | 买/卖 | 板块→个股→组合 |
| 经验类型 | 个股技术面 | 板块轮动+选股+仓位 |
| 实战价值 | 低 | 高 |

**建议优先级**：
1. ⭐⭐⭐ **方案A（精选股票池）** - 立即可用
2. ⭐⭐ 方案B（动态股票池） - 需要更多数据支持
3. ⭐ 多策略组合 - 长期优化目标
