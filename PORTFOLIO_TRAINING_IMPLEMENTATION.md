# Portfolio-Based Training Implementation

## Overview

This document describes the implementation of portfolio-based training for the Memory Bank system, upgrading from single-stock training to multi-stock portfolio management training.

## Problem Statement

The previous training approach had a fundamental limitation:
- **Single-stock training**: Only trained agents on buying/selling one stock at a time
- **Limited experience**: Agents had no experience in:
  - Board sector selection
  - Stock screening within sectors
  - Portfolio management (multiple concurrent positions)
  - Sector rotation strategies

This made the training experiences less valuable for real trading scenarios where portfolio management is essential.

## Solution: Portfolio Training (Phase 1)

Implemented a simplified portfolio training system that addresses these limitations.

### Key Features

1. **Multi-Stock Pool**: 5 stocks across 5 sectors
   - 金融 (Finance): 601318.SH - 中国平安
   - 科技 (Technology): 000063.SZ - 中兴通讯
   - 消费 (Consumer): 600519.SH - 贵州茅台
   - 医药 (Healthcare): 600276.SH - 恒瑞医药
   - 周期 (Cyclical): 600019.SH - 宝钢股份

2. **Portfolio Management**:
   - Maximum 5 concurrent positions
   - 20% position sizing per stock
   - Dynamic buy/sell decisions based on agent analysis
   - Automatic position exit after holding period

3. **Training Workflow** (Per Day):
   - Analyze ALL 5 stocks across 5 sectors
   - Review existing positions → sell if holding period reached
   - Evaluate buy candidates → buy if space available
   - Generate portfolio-level lesson

4. **Comprehensive Lessons**:
   Each episode captures:
   - Market environment (portfolio value, cash, position count)
   - Sector analysis (all 5 sectors evaluated)
   - Portfolio actions (buys/sells with reasoning)
   - Current holdings (unrealized P&L for each position)
   - Portfolio-level analysis (why the portfolio gained/lost)
   - Key lessons learned

## Implementation Files

### 1. `backend/scripts/portfolio_time_travel_training.py` (NEW)

Main training script implementing portfolio-based training.

**Key Classes:**
- `Position`: Dataclass for holding position information
- `PortfolioState`: Current portfolio state (positions, cash, total value)
- `PortfolioDecision`: Daily portfolio decision record
- `PortfolioTimeTravelTrainer`: Main trainer class

**Key Methods:**
```python
def analyze_sector(sector, symbol, date)
    # Run multi-agent analysis on each stock

def make_portfolio_decisions(date, sector_analyses)
    # Decide buy/sell based on analyses + current portfolio

def abstract_portfolio_lesson(decision, analyses)
    # Generate comprehensive markdown lesson
```

### 2. `backend/scripts/portfolio_training_design.md` (DESIGN)

Comprehensive design document covering:
- Problem analysis
- Training data structures
- Three-phase roadmap (simplified → complete → advanced)
- Stock pool recommendations
- Evaluation metrics

## Usage

### Basic Usage

```bash
cd backend
python scripts/portfolio_time_travel_training.py \
  --start 2024-07-01 \
  --end 2024-08-31 \
  --holding-days 5
```

### Advanced Options

```bash
python scripts/portfolio_time_travel_training.py \
  --start 2024-07-01 \
  --end 2024-08-31 \
  --holding-days 5 \
  --max-positions 5 \
  --initial-cash 1000000 \
  --position-size 0.2
```

**Parameters:**
- `--start`: Training start date (YYYY-MM-DD)
- `--end`: Training end date (YYYY-MM-DD)
- `--holding-days`: Holding period in days (default: 5)
- `--max-positions`: Maximum concurrent positions (default: 5)
- `--initial-cash`: Initial cash in RMB (default: 1,000,000)
- `--position-size`: Position size per stock 0.0-1.0 (default: 0.2 = 20%)

## Episode Structure

### Memory Bank Storage

Episodes are stored with `symbol="PORTFOLIO"` to distinguish from single-stock episodes.

### Lesson Format

```markdown
# 组合管理成功案例
**组合收益**: +1.23%
**日期**: 2024-07-01
**持仓数**: 3/5

## 📊 市场环境
- **组合总值**: ¥1,000,000 → ¥1,012,300
- **现金余额**: ¥400,000 → ¥200,000
- **持仓变化**: 2只 → 3只

## 🎯 板块分析
### 金融 - 601318.SH
- **分析建议**: 买入
- **当前价格**: ¥45.30

### 科技 - 000063.SZ
...

## 💼 组合操作
### ✅ 买入 000063.SZ (科技)
- **买入价格**: ¥35.20
- **买入数量**: 5,600 股
- **投入资金**: ¥197,120
- **决策理由**: 选择科技板块龙头

### 📤 卖出 600519.SH (消费)
- **卖出价格**: ¥1,875.00
- **卖出数量**: 100 股
- **盈亏金额**: +¥2,500
- **盈亏比例**: +1.35%
- **决策理由**: 持仓5天已到期

## 📋 当前持仓
### 601318.SH (金融)
- **持仓天数**: 3 天
- **成本价**: ¥44.50
- **当前价**: ¥45.30
- **浮动盈亏**: +1.80%

...

## 📝 组合分析
### ✅ 成功因素
本次组合管理获得了 **1.23%** 的收益，主要成功因素：
- **板块选择合理**: 选择了正确的板块进行配置
- **个股筛选得当**: 在板块内选择了优质个股
- **仓位控制适度**: 分散投资降低单一股票风险

## 💡 关键经验
- 分散投资策略有效降低了单一股票风险
- 板块轮动把握了市场热点
- 持仓周期控制得当，及时止盈
```

## Comparison: Single-Stock vs Portfolio Training

| Dimension | Single-Stock (Old) | Portfolio (New) |
|-----------|-------------------|------------------|
| Training Objects | 1 stock | 5 stocks (5 sectors) |
| Decision Layers | Buy/Sell | Sector → Stock → Portfolio |
| Experience Type | Technical analysis only | Sector rotation + Stock selection + Position sizing |
| Practical Value | Low (不全面) | High (接近实战) |
| Lesson Content | Single trade analysis | Multi-dimensional portfolio analysis |
| Memory Retrieval | Single-stock context | Portfolio management context |

## Training Results

The training generates episodes with:
- **Episode Symbol**: "PORTFOLIO" (to distinguish from single-stock)
- **Date**: Trading date
- **Success**: Portfolio gained value (net positive return)
- **Percentage Return**: Portfolio-level return (value change / initial value)
- **Lesson**: 30,000+ character comprehensive markdown lesson

Results are saved to: `backend/training_results/portfolio_training_[timestamp].json`

```json
{
  "training_type": "portfolio",
  "stock_pool": {...},
  "total_episodes": 29,
  "success_rate": 0.48,
  "average_return": -0.0041,
  "final_portfolio_value": 995900.0,
  "total_return_pct": -0.0041
}
```

## Future Enhancements (Phase 2 & 3)

### Phase 2: Complete Portfolio System
- Expand stock pool to 15 stocks (3 per sector)
- Add dynamic position sizing based on confidence
- Implement stop-loss/take-profit logic
- Add sector exposure limits

### Phase 3: Advanced Features
- Dynamic stock pool (real-time filtering)
- Multi-strategy portfolio (value + growth + trend)
- Risk parity allocation
- Market regime detection

## Technical Notes

1. **No-Future-Function**: Training maintains strict no-future-function constraints
   - Each day only sees data up to that date
   - Future data only used for evaluation (outcome calculation)

2. **Memory Bank Integration**:
   - Episodes stored in same ChromaDB as single-stock episodes
   - Symbol="PORTFOLIO" to distinguish episode types
   - Full lesson with markdown formatting

3. **Emoji Encoding Warnings**:
   - Windows console GBK encoding causes emoji display errors
   - Does NOT affect functionality
   - Consider redirecting to log file: `> training.log 2>&1`

4. **Performance**:
   - Each day analyzes 5 stocks = 5x longer than single-stock
   - Estimated 2-3 hours for 2-month training period
   - Can run in background with `nohup`

## Quick Start Example

```bash
# 1. Clear existing memory (optional)
curl -X DELETE http://localhost:8000/api/v1/memory/episodes

# 2. Run portfolio training for July-August 2024
cd backend
nohup python scripts/portfolio_time_travel_training.py \
  --start 2024-07-01 \
  --end 2024-08-31 \
  --holding-days 5 \
  > portfolio_training.log 2>&1 &

# 3. Monitor progress
tail -f portfolio_training.log

# 4. Check results
python scripts/view_memory_bank.py --type episodes --limit 10
```

## Memory Bank API Queries

### Get Portfolio Episodes

```bash
# Get all portfolio episodes
curl "http://localhost:8000/api/v1/memory/episodes?symbol=PORTFOLIO"

# Get portfolio statistics
curl "http://localhost:8000/api/v1/memory/statistics"
```

### Query Scenarios

1. **Sector Rotation Advice**:
   - Query: "在震荡市中，哪个板块表现最好？"
   - System retrieves episodes with similar market conditions
   - Provides sector selection statistics

2. **Stock Selection Within Sector**:
   - Query: "科技板块中，如何选择个股？"
   - Returns historical stock selection decisions + outcomes
   - Shows which screening criteria worked

3. **Position Sizing Strategy**:
   - Query: "如何分配仓位？"
   - Aggregates position sizing decisions
   - Provides optimal allocation patterns

## Summary

This portfolio training implementation provides agents with:

✅ **Sector Selection Experience**: Which sectors to focus on given market conditions
✅ **Stock Screening Experience**: How to choose stocks within selected sectors
✅ **Portfolio Management Experience**: Managing multiple positions simultaneously
✅ **Risk Distribution Experience**: Diversification and position sizing

This creates a much more valuable and practical training dataset for real-world trading scenarios.

---

**Implementation Date**: 2025-11-10
**Implementation Phase**: Phase 1 (Simplified Portfolio System)
**Status**: ✅ Complete - Ready for training
