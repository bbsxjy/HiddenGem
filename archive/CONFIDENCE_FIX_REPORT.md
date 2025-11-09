# Agent 置信度修复报告

## 问题描述
所有agents的置信度都异常偏低（20%-30%），即使在基本面优秀、技术指标明确的情况下也是如此。

## 根本原因
置信度计算逻辑错误：**直接使用分数绝对值作为置信度**

```python
# 错误的逻辑
confidence = min(abs(overall_score), 1.0)
```

这导致：
- Score = -0.35 → Confidence = 35%
- Score = 0.27 → Confidence = 27%

**问题在于**：
- 置信度应该反映信号的**可靠性**（指标一致性、数据质量）
- 而不是分数的大小
- 即使分数是-0.35（明确的空头信号），我们也可以有80%的置信度，表示对"做空"这个判断很有信心

## 修复方案

### 新的置信度计算逻辑

置信度 = f(指标一致性, 数据完整性, 信号强度)

#### Technical Agent

**修复前**:
```python
confidence = min(abs(overall_score), 1.0)
if weak_trend:
    confidence = confidence * 0.8  # 进一步降低
```

**修复后**:
```python
# 1. 统计指标及其方向
indicator_signals = []
for each indicator:
    if has_clear_signal:
        indicator_signals.append(+1 for long, -1 for short)

# 2. 计算一致性
agreeing = count(signals that agree with direction)
agreement_ratio = agreeing / total_signals

# 3. 基础置信度 (基于一致性)
base_confidence = 0.4 + (agreement_ratio * 0.5)  # 40%-90%

# 4. 调整因子
confidence += score_magnitude * 0.1  # 信号强度
if strong_trend:
    confidence *= 1.15  # 强趋势提升
elif weak_trend:
    confidence *= 0.92  # 弱趋势轻微降低

# 5. 限制范围
confidence = clamp(confidence, 0.3, 1.0)
```

#### Fundamental Agent

**修复前**:
```python
confidence = min(abs(overall_score), 1.0)
```

**修复后**:
```python
# 1. 统计指标
available_metrics = count(pe, pb, roe, debt, ps)
positive_metrics = count(metrics with score > 0.2)
negative_metrics = count(metrics with score < -0.2)

# 2. 数据完整性
completeness = available_metrics / 5

# 3. 一致性
consistency = agreeing_metrics / available_metrics

# 4. 基础置信度
base_confidence = 0.45 + (consistency * 0.4)  # 45%-85%
base_confidence += (completeness * 0.1)       # 数据完整性加分

# 5. 特殊加分
if exceptional_fundamentals (ROE excellent, low debt):
    confidence *= 1.15

# 6. 限制范围
confidence = clamp(confidence, 0.4, 1.0)
```

## 修复结果

### 测试案例: 贵州茅台 (600519.SH)

| Agent | Score | 修复前 | 修复后 | 提升 |
|-------|-------|--------|--------|------|
| Technical | -0.350 | 28% | **86.02%** | +207% |
| Fundamental | 0.270 | 27% | **73.70%** | +173% |
| Risk | -0.160 | 30% | 30% | 待修复 |
| Sentiment | 0.000 | 0% | 0% | 待修复 |

### 分析

**Technical Agent** (86.02%):
- 虽然ADX=13.9（弱趋势）
- 但多个指标（RSI、MACD、均线、KDJ）方向一致
- 高一致性 → 高置信度

**Fundamental Agent** (73.70%):
- ROE=26.4%（优秀）
- 负债率=12.8%（低）
- 估值略微低估
- PE、PB、ROE、Debt 4个指标都可用
- 高数据完整性 + 优秀基本面 → 高置信度

## 待修复的Agents

### Risk Agent (30%)
需要检查其置信度计算逻辑

### Sentiment Agent (0%)
- 当前没有显著情绪信号
- 可能需要调整最低置信度阈值

## 修改的文件

1. `backend/core/mcp_agents/technical_agent.py` (第321-412行)
2. `backend/core/mcp_agents/fundamental_agent.py` (第444-527行)

## 优势

1. **更合理**：置信度反映信号可靠性，而非分数大小
2. **更高**：正常情况下40%-90%的置信度区间
3. **更准确**：考虑指标一致性、数据完整性、特殊因素
4. **有区分度**：优秀信号可以达到80%+置信度

## 下一步

修复 Risk Agent 和 Sentiment Agent 的置信度计算逻辑。
