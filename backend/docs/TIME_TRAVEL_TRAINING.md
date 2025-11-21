# 时间旅行训练系统使用指南 (Enhanced Version)

本指南介绍如何使用**增强版时间旅行训练系统**从历史数据中学习交易经验。

> **⚠️ 重要说明**:
> - 本系统已升级为 `enhanced_time_travel_training.py`（增强版）
> - 旧版 `time_travel_training.py` 已弃用并删除
> - **关键改进**: 修复了未来信息泄漏问题，符合时间序列ML原则

## 目录

- [系统概述](#系统概述)
- [Enhanced版本改进](#enhanced版本改进)
- [快速开始](#快速开始)
- [工作原理](#工作原理)
- [使用示例](#使用示例)
- [高级配置](#高级配置)
- [常见问题](#常见问题)

## 系统概述

**时间旅行训练（Time-Travel Training）** 是一种离线强化学习方法，核心思想是：

1. AI假装回到历史某一天
2. 基于当时可获得的数据做交易决策
3. 用未来的真实结果评估决策质量
4. 从成功和失败中学习经验
5. 将经验存储到记忆库供未来使用

这种方法的优势：
- ✅ 不需要真实资金进行试错
- ✅ 可以快速学习大量历史案例
- ✅ 能够学习到市场的真实规律
- ✅ 支持可复现的学习过程
- ✅ **防止未来信息泄漏**（Enhanced版本关键特性）

## Enhanced版本改进

### 🆕 关键改进 (2025-11-21)

**问题**: 旧版`time_travel_training.py`存在时间序列ML的严重问题 - **未来信息泄漏**：
- ❌ `lesson`中包含`outcome.percentage_return`等未来结果
- ❌ 训练时模型能"看到"未来收益
- ❌ 实盘表现远低于回测

**解决方案**: `enhanced_time_travel_training.py`严格分离决策上下文和未来结果：

```python
# ✅ Enhanced版本: 分离决策上下文和未来结果
def abstract_lesson(self, outcome, market_state, decision_chain):
    """
    PART 1: DECISION_CONTEXT (决策时可见信息 - 用于检索)
    - 市场状态
    - Agent分析
    - 决策链
    - ❌ 不包含未来收益！

    PART 2: OUTCOME_RESULT (未来结果 - 仅用于学习评估)
    - 实际收益率
    - 最大回撤
    - 成功/失败标记
    """
```

**实际影响**:
- ✅ 训练数据质量提升
- ✅ 实盘表现更接近回测
- ✅ 符合时间序列ML最佳实践

### 其他改进

- ✅ TaskMonitor支持（断点续跑）
- ✅ 更详细的日志输出
- ✅ JSONL数据导出（支持小模型微调）
- ✅ 改进的统计报告

## 快速开始

### 1. 环境准备

确保已安装所有依赖：

```bash
cd backend
pip install -r requirements.txt
```

配置环境变量（`.env`）：

```bash
# LLM配置
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_api_key

# 数据源配置
TUSHARE_TOKEN=your_tushare_token

# 记忆系统配置
MEMORY_PERSIST_PATH=./memory_db/maxims
EPISODE_MEMORY_PATH=./memory_db/episodes
```

### 2. 运行演示脚本

首先运行演示脚本了解记忆系统：

```bash
python scripts/demo_memory_system.py
```

这会展示：
- ✅ 如何在分析模式下检索历史经验（只读）
- ✅ 如何在训练模式下添加新经验（读写）
- ✅ 记忆系统的统计信息

### 3. 执行时间旅行训练

训练单只股票（示例：贵州茅台）：

```bash
python scripts/enhanced_time_travel_training.py \
  --symbol 600519.SH \
  --start 2020-01-01 \
  --end 2023-12-31 \
  --holding-days 5
```

参数说明：
- `--symbol`: 股票代码（A股格式：XXXXXX.SH/SZ，美股：AAPL）
- `--start`: 训练开始日期（YYYY-MM-DD）
- `--end`: 训练结束日期（YYYY-MM-DD）
- `--holding-days`: 持仓天数（默认5天）

### 4. 查看训练结果

训练完成后，结果会保存在 `training_results/` 目录：

```bash
cat training_results/time_travel_600519.SH_20250109_143022.json
```

输出示例：
```json
{
  "symbol": "600519.SH",
  "start_date": "2020-01-01",
  "end_date": "2023-12-31",
  "holding_days": 5,
  "total_episodes": 245,
  "successful_episodes": 152,
  "failed_episodes": 93,
  "success_rate": 0.62,
  "average_return": 0.0123,
  "timestamp": "2025-01-09T14:30:22"
}
```

### 5. API服务器使用训练结果

启动API服务器后，记忆系统会自动加载训练的经验：

```bash
uvicorn api.main:app --reload
```

检查记忆系统状态：

```bash
curl http://localhost:8000/api/v1/memory/status
```

现在当你分析股票时，系统会自动检索相似的历史案例来辅助决策！

## 工作原理

### 时间旅行训练流程

```
┌─────────────────────────────────────────────────────────┐
│              时间旅行训练循环                              │
└─────────────────────────────────────────────────────────┘

1️⃣ 选择历史日期 (例如: 2020-03-23)
   │
   ▼
2️⃣ 检索相似历史案例 (从记忆库)
   │
   ▼
3️⃣ 执行AI分析 (假装在那一天)
   │  - Market Analyst
   │  - Fundamentals Analyst
   │  - Sentiment Analyst
   │  - News Analyst
   │  - Bull vs Bear辩论
   │  - Risk Management辩论
   │  - Final Decision
   ▼
4️⃣ 模拟交易执行
   │  - 入场: 当天收盘价
   │  - 持仓: N天
   │  - 退出: N天后收盘价
   ▼
5️⃣ 评估交易结果
   │  - 收益率
   │  - 最大回撤
   │  - 成功/失败
   ▼
6️⃣ 抽象经验教训
   │  - 详细lesson (完整描述)
   │  - key_lesson (浓缩版)
   ▼
7️⃣ 存储到记忆库
   │  ├─ Episode Memory (细粒度)
   │  │   └─ 完整的交易案例
   │  └─ Maxim Memory (粗粒度)
   │      └─ 抽象的经验格言
   ▼
8️⃣ 前进到下一个交易日
   │
   └──► 回到步骤1 (直到结束日期)
```

### 记忆系统架构

```
Memory System
│
├── Analysis Mode (API服务器使用)
│   ├── 只读访问
│   ├── 检索相似案例
│   └── 辅助实时决策
│
└── Training Mode (训练脚本使用)
    ├── 读写访问
    ├── 存储新案例
    └── 积累经验知识
```

### Episode数据结构

每个Episode包含：

```python
TradingEpisode(
    episode_id="2020-03-23_600519.SH",
    date="2020-03-23",
    symbol="600519.SH",

    # 市场状态快照
    market_state=MarketState(
        price=850.0,
        rsi=15.0,
        vix=80.0,
        market_regime="panic_selloff"
    ),

    # 4个Agent的完整分析
    agent_analyses={
        'market': AgentAnalysis(...),
        'fundamentals': AgentAnalysis(...),
        'sentiment': AgentAnalysis(...),
        'news': AgentAnalysis(...)
    },

    # 决策链（辩论过程）
    decision_chain=DecisionChain(
        bull_argument="...",
        bear_argument="...",
        final_decision="..."
    ),

    # 交易结果
    outcome=TradeOutcome(
        action="BUY",
        entry_price=850.0,
        exit_price=1050.0,
        percentage_return=0.235  # +23.5%
    ),

    # 经验教训
    lesson="COVID恐慌抄底成功案例...",
    key_lesson="恐慌性下跌 + 基本面完好 = 抄底机会",
    success=True
)
```

## 使用示例

### 示例1：训练A股龙头股

```bash
# 贵州茅台 - 消费龙头
python scripts/enhanced_time_travel_training.py \
  --symbol 600519.SH \
  --start 2015-01-01 \
  --end 2024-12-31 \
  --holding-days 10

# 宁德时代 - 新能源龙头
python scripts/enhanced_time_travel_training.py \
  --symbol 300750.SZ \
  --start 2018-06-01 \
  --end 2024-12-31 \
  --holding-days 5

# 中国平安 - 金融龙头
python scripts/enhanced_time_travel_training.py \
  --symbol 601318.SH \
  --start 2010-01-01 \
  --end 2024-12-31 \
  --holding-days 15
```

### 示例2：训练美股科技股

```bash
# Apple
python scripts/enhanced_time_travel_training.py \
  --symbol AAPL \
  --start 2015-01-01 \
  --end 2024-12-31 \
  --holding-days 10

# NVIDIA
python scripts/enhanced_time_travel_training.py \
  --symbol NVDA \
  --start 2018-01-01 \
  --end 2024-12-31 \
  --holding-days 5
```

### 示例3：特定市场环境训练

```bash
# COVID-19疫情期间 (2020年)
python scripts/enhanced_time_travel_training.py \
  --symbol 600519.SH \
  --start 2020-01-01 \
  --end 2020-12-31 \
  --holding-days 5

# 2015年股灾期间
python scripts/enhanced_time_travel_training.py \
  --symbol 600519.SH \
  --start 2015-06-01 \
  --end 2015-12-31 \
  --holding-days 3
```

## 高级配置

### 自定义持仓策略

修改 `enhanced_time_travel_training.py` 中的 `simulate_trade()` 方法：

```python
def simulate_trade(self, entry_date, processed_signal):
    # 自定义持仓天数（根据市场波动率调整）
    if market_volatility > 0.3:
        holding_days = 3  # 高波动，短持
    else:
        holding_days = 10  # 低波动，长持

    # 自定义仓位（根据信心度调整）
    if confidence > 0.8:
        position_size = 0.2  # 高信心，大仓位
    else:
        position_size = 0.05  # 低信心，小仓位
```

### 批量训练脚本

创建批量训练脚本 `scripts/batch_training.sh`：

```bash
#!/bin/bash

# A股龙头股票列表
symbols=(
    "600519.SH"  # 贵州茅台
    "300750.SZ"  # 宁德时代
    "601318.SH"  # 中国平安
    "600036.SH"  # 招商银行
    "000858.SZ"  # 五粮液
)

# 训练时间范围
start_date="2020-01-01"
end_date="2024-12-31"

# 遍历训练
for symbol in "${symbols[@]}"; do
    echo "🚀 开始训练: $symbol"
    python scripts/enhanced_time_travel_training.py \
        --symbol "$symbol" \
        --start "$start_date" \
        --end "$end_date" \
        --holding-days 5

    echo "✅ 完成训练: $symbol"
    echo ""
done

echo "🎓 所有训练完成！"
```

运行批量训练：

```bash
chmod +x scripts/batch_training.sh
./scripts/batch_training.sh
```

### 自定义市场Regime检测

在 `enhanced_time_travel_training.py` 中添加市场regime检测逻辑：

```python
def detect_market_regime(self, current_date):
    """检测市场状态"""
    # 获取最近20天数据
    data = get_stock_data_by_market(
        symbol=self.symbol,
        start_date=(current_date - timedelta(days=40)).strftime("%Y-%m-%d"),
        end_date=current_date.strftime("%Y-%m-%d")
    )

    # 计算波动率
    volatility = data['close'].pct_change().std()

    # 计算趋势
    ma_5 = data['close'].rolling(5).mean().iloc[-1]
    ma_20 = data['close'].rolling(20).mean().iloc[-1]

    # 判断regime
    if volatility > 0.05:
        return 'volatile' if ma_5 > ma_20 else 'panic'
    elif ma_5 > ma_20 * 1.1:
        return 'bull'
    elif ma_5 < ma_20 * 0.9:
        return 'bear'
    else:
        return 'sideways'
```

## 常见问题

### Q1: 训练需要多长时间？

A: 取决于几个因素：
- 训练时间范围：1年约250个交易日
- LLM速度：每次分析约30-60秒
- 估算：训练1年数据需要约2-4小时

建议：
- 先用短时间范围测试（如3个月）
- 确认无误后再进行长时间训练
- 可以使用`--holding-days`参数跳过部分日期

### Q2: 如何选择持仓天数？

A: 根据交易风格选择：
- **短线交易**: 3-5天
- **波段交易**: 5-10天
- **趋势跟踪**: 10-30天

建议：
- 初次训练使用5天（平衡短线和中线）
- 观察训练结果的胜率和收益
- 根据结果调整持仓天数

### Q3: 训练失败怎么办？

A: 常见问题和解决方案：

**问题1: 数据获取失败**
```
❌ 无法获取600519.SH的历史数据
```
解决：检查Tushare token是否配置正确

**问题2: LLM API失败**
```
❌ DashScope API错误: Invalid API key
```
解决：检查DASHSCOPE_API_KEY环境变量

**问题3: 内存不足**
```
❌ MemoryError: Unable to allocate array
```
解决：减少训练时间范围，或分段训练

### Q4: 如何验证训练效果？

A: 几个方法：

**方法1: 查看统计结果**
```bash
cat training_results/time_travel_*.json
```

关键指标：
- `success_rate > 0.55`: 胜率超过55%
- `average_return > 0.01`: 平均收益超过1%

**方法2: 检查记忆库**
```bash
curl http://localhost:8000/api/v1/memory/status
```

**方法3: 实际使用测试**
```bash
# 分析一只股票
curl -X POST http://localhost:8000/api/v1/agents/analyze-all/600519.SH

# 观察是否引用了历史案例
```

### Q5: 记忆库会越来越大吗？

A: 是的，但有优化措施：

**当前状态**:
- Episode Memory使用向量检索，查询速度不受数据量影响
- Maxim Memory存储抽象格言，数据量相对较小

**未来优化**（TODO）:
- 实现记忆遗忘机制（过期案例降权）
- 添加去重逻辑（相似案例合并）
- 定期清理低价值记忆

### Q6: 可以训练多个股票吗？

A: 可以，有两种方式：

**方式1: 顺序训练**（推荐）
```bash
python scripts/enhanced_time_travel_training.py --symbol 600519.SH ...
python scripts/enhanced_time_travel_training.py --symbol 300750.SZ ...
```

**方式2: 批量训练**
使用上面的批量训练脚本

**注意**:
- 不同股票的经验会存储在同一个记忆库
- 检索时会自动找到最相似的案例（跨股票）
- 这有助于学习通用的市场规律

## 下一步

完成时间旅行训练后，你可以：

1. **查看详细文档**
   - `backend/memory/README.md` - 记忆系统文档
   - `backend/CLAUDE.md` - 后端开发指南

2. **启动API服务器**
   ```bash
   uvicorn api.main:app --reload
   ```

3. **集成前端**
   - 前端会自动使用训练好的记忆库
   - 分析时会显示相似的历史案例

4. **继续优化**
   - 整合CVaR-PPO风险约束
   - 实现自动经验抽象引擎
   - 添加记忆质量评估

---

**最后更新**: 2025-01-09
**维护者**: Claude Code
**项目**: HiddenGem Trading System
