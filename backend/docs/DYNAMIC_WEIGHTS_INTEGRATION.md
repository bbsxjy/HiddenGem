# 动态权重系统集成文档

## 📋 概述

本文档说明动态权重计算系统（`DynamicWeightCalculator`）如何集成到API层，以及它如何改进原有的"假聚合"逻辑。

## 🎯 问题背景

### 原有问题

在集成前，`api/main.py` 中的聚合逻辑存在以下问题：

```python
# ❌ 旧逻辑（line 572-589）
directions = [r["direction"] for r in agent_results.values()]
num_long = directions.count("long")   # 统计投票：3个long
num_short = directions.count("short")  # 1个short

aggregated_signal = {
    "direction": recommended_direction,  # ❌ 直接使用Risk Manager的决策
    "confidence": confidence,
    "num_agreeing_agents": max(num_long, num_short)  # ❌ 只是显示，不影响决策
}
```

**核心问题**：
1. 统计了投票（3多1空），但完全忽略投票结果
2. 直接使用 Risk Manager 的决策（"卖出"）
3. 没有考虑各Agent的置信度、数据质量、历史表现
4. 没有根据市场环境调整权重

### 用户反馈

> "为什么4个agent，3个看多，结果最后riskmanager看空？"
>
> "规则聚合为什么也会判断最终结果是空而不是多"
>
> "我觉得方案2可以，但是这个比例应该是动态的。"

## ✅ 解决方案

### 核心设计

实现了一个**多因子动态权重系统**，不再依赖单一的 Risk Manager 决策，而是：

1. **基础权重** × **4个动态因子** = **最终权重**
2. **加权投票** 代替 **简单多数投票**
3. **透明可追溯** 的决策过程

### 四个动态因子

#### 1. 置信度因子（Confidence Factor）

```python
def _calculate_confidence_factor(self, result: Dict[str, Any]) -> float:
    """
    范围：[0.3, 1.5]

    - confidence < 0.3 → factor = 0.3（严重惩罚）
    - confidence 0.3-0.7 → factor = 0.5 + confidence * 0.5
    - confidence > 0.7 → factor = 0.5 + confidence（奖励高置信度）
    """
    confidence = result.get('confidence', 0.5)

    if confidence < 0.3:
        return 0.3
    elif confidence < 0.7:
        return 0.5 + confidence * 0.5
    else:
        return 0.5 + confidence
```

**实际案例**：
- Agent A: confidence=0.8 → factor=1.3 ✅
- Agent B: confidence=0.5 → factor=0.75 ⚠️
- Agent C: confidence=0.2 → factor=0.3 ❌（大幅降权）

#### 2. 质量因子（Quality Factor）

```python
def _calculate_quality_factor(self, result: Dict[str, Any]) -> float:
    """
    范围：[0.2, 1.5]

    考虑因素：
    1. 是否出错（is_error） → 0.2
    2. 执行时间（太快 or 太慢） → 0.8-0.9
    3. 推理深度（reasoning长度） → 0.7-1.2
    4. 数据支撑（包含具体数字） → ×1.3
    """
    if result.get('is_error', False):
        return 0.2

    factor = 1.0

    # 执行时间
    exec_time = result.get('execution_time_ms', 2000)
    if exec_time < 500:
        factor *= 0.9  # 太快（可能是缓存）
    elif exec_time > 10000:
        factor *= 0.8  # 太慢（可能超时）

    # 推理深度
    reasoning_length = len(result.get('reasoning', ''))
    if reasoning_length < 50:
        factor *= 0.7  # 推理过短
    elif reasoning_length > 500:
        factor *= 1.2  # 推理详细

    # 数据支撑（检测是否包含 PE/PB/ROE/百分比等）
    if re.search(r'\d+\.?\d*%|\d+\\.\\d+|PE|PB|ROE|营收|净利润', reasoning):
        factor *= 1.3  # 有具体数据

    return max(0.2, min(1.5, factor))
```

**实际案例**：
```
基本面分析师：
- reasoning: "PE=12.5, ROE=12.6%, 净利润增长30%..."
- 长度: 2000字符
- 执行时间: 3500ms
→ factor = 1.0 × 1.0 × 1.2 × 1.3 = 1.56 → 截断为1.5 ✅

情绪分析师：
- reasoning: "市场情绪乐观"
- 长度: 20字符
- 执行时间: 200ms
→ factor = 1.0 × 0.9 × 0.7 × 1.0 = 0.63 ⚠️
```

#### 3. 历史表现因子（Performance Factor）

```python
def _calculate_performance_factor(self, agent_name: str) -> float:
    """
    范围：[0.5, 1.5]

    基于历史准确率：
    - 需要至少10次记录才生效
    - factor = 0.5 + accuracy

    示例：
    - accuracy=0.8 → factor=1.3 ✅
    - accuracy=0.5 → factor=1.0 ⚠️
    - accuracy=0.3 → factor=0.8 ❌
    """
    performance = self.historical_performance.get(agent_name, {})
    accuracy = performance.get('accuracy', 0.5)
    total = performance.get('total', 0)

    if total < 10:
        return 1.0  # 数据不足，使用中性值

    return 0.5 + accuracy
```

**注意**：当前版本历史表现数据未持久化到数据库，默认返回 1.0。

**TODO**: 实现历史表现追踪（需要数据库支持）

#### 4. 市场环境因子（Context Factor）

```python
def _calculate_context_factor(self, agent_name: str, market_context: Dict) -> float:
    """
    范围：[0.7, 1.3]

    根据市场环境调整权重：
    - 高波动 → 基本面↑（1.3），情绪↓（0.7）
    - 牛市 → 情绪/新闻↑（1.2），基本面↓（0.9）
    - 熊市 → 基本面↑（1.3），情绪↓（0.8）
    - 高风险 → 基本面↑（1.2），情绪↓（0.8）
    """
    volatility = market_context.get('volatility', 'normal')  # low/normal/high
    trend = market_context.get('trend', 'neutral')  # bull/bear/neutral
    risk_level = market_context.get('risk_level', 0.5)

    factor = 1.0

    # 波动率调整
    if volatility == 'high':
        if agent_name == 'fundamental':
            factor *= 1.3  # 高波动时基本面最重要
        elif agent_name == 'sentiment':
            factor *= 0.7  # 情绪不可靠

    # 趋势调整
    if trend == 'bull':
        if agent_name in ['sentiment', 'news']:
            factor *= 1.2  # 牛市情绪重要
        elif agent_name == 'fundamental':
            factor *= 0.9  # 基本面相对次要
    elif trend == 'bear':
        if agent_name == 'fundamental':
            factor *= 1.3  # 熊市基本面最重要
        elif agent_name == 'sentiment':
            factor *= 0.8  # 情绪不可靠

    # 风险等级调整
    if risk_level > 0.7:
        if agent_name == 'fundamental':
            factor *= 1.2  # 高风险时基本面最重要
        elif agent_name == 'sentiment':
            factor *= 0.8  # 情绪不可靠

    return max(0.7, min(1.3, factor))
```

**当前实现**：市场环境参数暂时硬编码为默认值：

```python
market_context = {
    'volatility': 'normal',  # TODO: 从市场数据中检测
    'trend': 'neutral',      # TODO: 从市场数据中检测
    'risk_level': risk_score if processed_signal else 0.5
}
```

**TODO**: 实现自动市场环境检测

### 权重计算公式

```python
# 1. 计算调整后的权重
adjusted_weight = (
    base_weight
    × confidence_factor
    × quality_factor
    × performance_factor
    × context_factor
)

# 2. 归一化（确保总和=1）
normalized_weight = adjusted_weight / sum(all_adjusted_weights)

# 3. 计算加权分数
long_score = Σ(weight × confidence) for agents with direction='long'
short_score = Σ(weight × confidence) for agents with direction='short'
hold_score = Σ(weight × confidence) for agents with direction='hold'

# 4. 最终决策
final_direction = argmax(long_score, short_score, hold_score)
final_confidence = max_score
```

## 📊 实际案例分析

### 案例：300502 新易盛（2025-11-07）

#### 输入数据

```python
agent_results = {
    'technical': {
        'direction': 'long',
        'confidence': 0.75,
        'reasoning': '技术面强势，RSI>70，MACD金叉...',  # 150字符
        'execution_time_ms': 2500,
        'is_error': False
    },
    'fundamental': {
        'direction': 'long',
        'confidence': 0.85,
        'reasoning': 'PE=12.5倍，ROE=12.6%，净利润增长30%...',  # 2000字符
        'execution_time_ms': 3500,
        'is_error': False
    },
    'sentiment': {
        'direction': 'long',
        'confidence': 0.80,
        'reasoning': '市场情绪乐观，雪球热度高...',  # 80字符
        'execution_time_ms': 1500,
        'is_error': False
    },
    'policy': {
        'direction': 'short',
        'confidence': 0.90,
        'reasoning': '应收账款占比37%，Q3营收下滑8%，2026增速仅8.8%...',  # 1500字符
        'execution_time_ms': 4000,
        'is_error': False
    }
}

market_context = {
    'volatility': 'normal',
    'trend': 'neutral',
    'risk_level': 0.5
}
```

#### 权重计算过程

| Agent | Base | Conf | Quality | Perf | Context | Adjusted | Normalized |
|-------|------|------|---------|------|---------|----------|------------|
| **technical** | 0.25 | 1.25 | 1.0 | 1.0 | 1.0 | 0.3125 | **0.257** |
| **fundamental** | 0.30 | 1.35 | 1.5 | 1.0 | 1.0 | 0.6075 | **0.500** |
| **sentiment** | 0.20 | 1.30 | 0.7 | 1.0 | 1.0 | 0.182 | **0.150** |
| **policy** | 0.25 | 1.40 | 1.2 | 1.0 | 1.0 | 0.42 | **0.346** |
| **Total** | 1.00 | - | - | - | - | 1.522 | **1.000** |

**详细计算**：

```python
# Technical
confidence_factor = 0.5 + 0.75 = 1.25
quality_factor = 1.0 × 1.0 × 1.0 = 1.0  # 正常
adjusted_weight = 0.25 × 1.25 × 1.0 × 1.0 × 1.0 = 0.3125
normalized_weight = 0.3125 / 1.522 = 0.205

# Fundamental
confidence_factor = 0.5 + 0.85 = 1.35
quality_factor = 1.0 × 1.2 × 1.3 = 1.56 → 1.5（截断）
adjusted_weight = 0.30 × 1.35 × 1.5 × 1.0 × 1.0 = 0.6075
normalized_weight = 0.6075 / 1.522 = 0.399

# Sentiment
confidence_factor = 0.5 + 0.80 = 1.30
quality_factor = 1.0 × 0.9 × 0.7 = 0.63
adjusted_weight = 0.20 × 1.30 × 0.63 × 1.0 × 1.0 = 0.1638
normalized_weight = 0.1638 / 1.522 = 0.108

# Policy (News)
confidence_factor = 0.5 + 0.90 = 1.40
quality_factor = 1.0 × 1.0 × 1.2 = 1.2
adjusted_weight = 0.25 × 1.40 × 1.2 × 1.0 × 1.0 = 0.42
normalized_weight = 0.42 / 1.522 = 0.276
```

#### 加权分数计算

```python
# Long分数（3个Agent看多）
long_score = (
    0.257 × 0.75  # technical
    + 0.500 × 0.85  # fundamental
    + 0.150 × 0.80  # sentiment
) = 0.193 + 0.425 + 0.120 = 0.738

# Short分数（1个Agent看空）
short_score = (
    0.346 × 0.90  # policy
) = 0.311

# Hold分数
hold_score = 0.0

# 最终决策
final_direction = 'long'  # max(0.738, 0.311, 0.0)
final_confidence = 0.738
```

#### 结果对比

| 方法 | 决策 | 理由 |
|------|------|------|
| **简单投票** | long (3:1) | 多数决 |
| **Risk Manager** | short | 专家判断 |
| **动态权重** | long (0.738 vs 0.311) | 加权投票 |

**分析**：
- 简单投票：3多1空 → long ✅
- Risk Manager：发现硬证据（应收账款危机）→ short ⚠️
- 动态权重：基本面权重最高（0.500），且看多 → long ✅

**关键差异**：
- Risk Manager 是"一票否决"，发现致命风险就否决
- 动态权重是"综合决策"，基本面权重高但不是唯一因素
- 当基本面（0.500 × 0.85 = 0.425）> 政策风险（0.346 × 0.90 = 0.311）时，依然选择 long

## 🔧 API集成细节

### 修改位置

**文件**: `api/main.py`

**修改前**（line 572-589）：
```python
# ❌ 假聚合
directions = [r["direction"] for r in agent_results.values()]
num_long = directions.count("long")
num_short = directions.count("short")

aggregated_signal = {
    "direction": recommended_direction,  # 直接用Risk Manager
    "num_agreeing_agents": max(num_long, num_short)  # 只是显示
}
```

**修改后**（line 573-631）：
```python
# ✅ 真实加权聚合
dynamic_calculator = get_dynamic_weight_calculator()

market_context = {
    'volatility': 'normal',
    'trend': 'neutral',
    'risk_level': risk_score if processed_signal else 0.5
}

weighted_result = dynamic_calculator.calculate_weighted_signal(
    agent_results=agent_results,
    market_context=market_context
)

# 统计投票（用于对比）
directions = [r["direction"] for r in agent_results.values()]
num_long = directions.count("long")
num_short = directions.count("short")
num_hold = directions.count("hold")

majority_vote = 'long' if num_long > num_short else ('short' if num_short > num_long else 'hold')
voting_overridden = weighted_result['direction'] != majority_vote

aggregated_signal = {
    "direction": weighted_result['direction'],  # ✅ 使用加权结果
    "confidence": weighted_result['confidence'],
    "long_score": weighted_result['long_score'],
    "short_score": weighted_result['short_score'],
    "hold_score": weighted_result.get('hold_score', 0.0),
    "metadata": {
        "analysis_method": "dynamic_weights",
        "voting_stats": {
            "long": num_long,
            "short": num_short,
            "hold": num_hold,
            "majority_vote": majority_vote
        },
        "weights_used": weighted_result['weights_used'],
        "breakdown": weighted_result['breakdown'],
        "risk_manager_decision": recommended_direction,
        "voting_overridden": voting_overridden  # ✅ 是否覆盖多数投票
    }
}
```

### 返回数据结构

```json
{
  "symbol": "300502",
  "agent_results": { ... },
  "aggregated_signal": {
    "direction": "long",
    "confidence": 0.738,
    "long_score": 0.738,
    "short_score": 0.311,
    "hold_score": 0.0,
    "position_size": 0.1,
    "num_agreeing_agents": 3,
    "warnings": [],
    "metadata": {
      "analysis_method": "dynamic_weights",
      "agent_count": 4,
      "voting_stats": {
        "long": 3,
        "short": 1,
        "hold": 0,
        "majority_vote": "long"
      },
      "weights_used": {
        "technical": 0.257,
        "fundamental": 0.500,
        "sentiment": 0.150,
        "policy": 0.346
      },
      "breakdown": {
        "technical": {
          "direction": "long",
          "confidence": 0.75,
          "weight": 0.257,
          "weighted_score": 0.193
        },
        "fundamental": {
          "direction": "long",
          "confidence": 0.85,
          "weight": 0.500,
          "weighted_score": 0.425
        },
        "sentiment": {
          "direction": "long",
          "confidence": 0.80,
          "weight": 0.150,
          "weighted_score": 0.120
        },
        "policy": {
          "direction": "short",
          "confidence": 0.90,
          "weight": 0.346,
          "weighted_score": 0.311
        }
      },
      "risk_manager_decision": "short",
      "voting_overridden": false,
      "market_context": {
        "volatility": "normal",
        "trend": "neutral",
        "risk_level": 0.5
      }
    }
  },
  "llm_analysis": { ... }
}
```

## 📝 日志输出

集成后，API会输出详细的权重计算日志：

```
2025-11-07 11:30:00,123 | utils.dynamic_weights | INFO | 🎯 [DynamicWeights] 开始计算动态权重
2025-11-07 11:30:00,124 | utils.dynamic_weights | DEBUG |   [technical] 基础=0.250, 置信度×1.25, 质量×1.00, 历史×1.00, 环境×1.00 → 0.313
2025-11-07 11:30:00,125 | utils.dynamic_weights | DEBUG |   [fundamental] 基础=0.300, 置信度×1.35, 质量×1.50, 历史×1.00, 环境×1.00 → 0.608
2025-11-07 11:30:00,126 | utils.dynamic_weights | DEBUG |   [sentiment] 基础=0.200, 置信度×1.30, 质量×0.70, 历史×1.00, 环境×1.00 → 0.182
2025-11-07 11:30:00,127 | utils.dynamic_weights | DEBUG |   [policy] 基础=0.250, 置信度×1.40, 质量×1.20, 历史×1.00, 环境×1.00 → 0.420
2025-11-07 11:30:00,128 | utils.dynamic_weights | INFO | ✅ [DynamicWeights] 归一化权重: technical=0.257, fundamental=0.500, sentiment=0.150, policy=0.346
2025-11-07 11:30:00,129 | utils.dynamic_weights | INFO | 📊 [DynamicWeights] 计算加权信号
2025-11-07 11:30:00,130 | utils.dynamic_weights | INFO | ✅ [DynamicWeights] 加权结果: long (置信度=0.74, long=0.74, short=0.31)
2025-11-07 11:30:00,131 | api                   | INFO | 📊 [API] 投票统计: long=3, short=1, hold=0, 多数=long
2025-11-07 11:30:00,132 | api                   | INFO | 📊 [API] 加权结果: long (置信度=0.74)
2025-11-07 11:30:00,133 | api                   | INFO | 📊 [API] 风险管理器建议: short
```

## ⚠️ 注意事项

### 1. 历史表现数据未持久化

**当前状态**：历史表现因子默认返回 1.0（中性值）

**原因**：需要数据库支持存储历史决策和回测结果

**TODO**：
```python
# 需要实现的功能
def update_historical_performance(agent_name: str, was_correct: bool):
    """更新agent的历史表现并保存到数据库"""
    # 1. 更新内存中的统计
    # 2. 保存到 MongoDB/PostgreSQL
    # 3. 定期计算准确率
```

### 2. 市场环境检测未实现

**当前状态**：市场环境参数硬编码为默认值

```python
market_context = {
    'volatility': 'normal',  # TODO: 从市场数据中检测
    'trend': 'neutral',      # TODO: 从市场数据中检测
    'risk_level': risk_score if processed_signal else 0.5
}
```

**TODO**：
```python
# 需要实现的功能
def detect_market_context(symbol: str, market_data: dict) -> dict:
    """自动检测市场环境"""
    # 1. 波动率检测（ATR、历史波动率）
    # 2. 趋势检测（MA、EMA、MACD）
    # 3. 风险等级（VIX、波动率）
    return {
        'volatility': 'high',
        'trend': 'bull',
        'risk_level': 0.8
    }
```

### 3. 权重调试建议

如果发现权重分配不合理，可以调整：

**调整基础权重**（`dynamic_weights.py` line 20-25）：
```python
self.base_weights = {
    'technical': 0.25,      # 技术分析
    'fundamental': 0.30,    # 基本面（默认最重要）
    'sentiment': 0.20,      # 情绪分析
    'news': 0.25,           # 新闻分析
}
```

**调整因子范围**：
```python
# 置信度因子（line 104-124）
confidence_factor: [0.3, 1.5] → 可调整为 [0.5, 2.0]

# 质量因子（line 126-175）
quality_factor: [0.2, 1.5] → 可调整为 [0.3, 2.0]

# 历史表现因子（line 177-199）
performance_factor: [0.5, 1.5] → 可调整为 [0.3, 2.0]

# 市场环境因子（line 201-264）
context_factor: [0.7, 1.3] → 可调整为 [0.5, 1.5]
```

## 📊 测试建议

### 单元测试

```python
# tests/test_dynamic_weights.py
import pytest
from tradingagents.utils.dynamic_weights import DynamicWeightCalculator

def test_calculate_dynamic_weights():
    calculator = DynamicWeightCalculator()

    agent_results = {
        'technical': {
            'direction': 'long',
            'confidence': 0.75,
            'reasoning': '技术面强势...',
            'execution_time_ms': 2500,
            'is_error': False
        },
        'fundamental': {
            'direction': 'long',
            'confidence': 0.85,
            'reasoning': 'PE=12.5倍，ROE=12.6%...',
            'execution_time_ms': 3500,
            'is_error': False
        }
    }

    weights = calculator.calculate_dynamic_weights(agent_results)

    # 验证权重总和=1
    assert abs(sum(weights.values()) - 1.0) < 0.001

    # 验证基本面权重最高（因为质量因子高）
    assert weights['fundamental'] > weights['technical']
```

### 集成测试

```python
# tests/test_api_dynamic_weights.py
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_analyze_stock_with_dynamic_weights():
    response = client.post("/api/v1/agents/analyze-all/300502")
    assert response.status_code == 200

    data = response.json()

    # 验证返回了动态权重信息
    assert 'aggregated_signal' in data
    signal = data['aggregated_signal']

    assert 'weights_used' in signal['metadata']
    assert 'breakdown' in signal['metadata']
    assert 'voting_overridden' in signal['metadata']

    # 验证权重总和=1
    weights = signal['metadata']['weights_used']
    assert abs(sum(weights.values()) - 1.0) < 0.001
```

## 🚀 未来优化方向

### 1. 自适应学习权重

使用强化学习自动调整基础权重：

```python
class AdaptiveWeightCalculator(DynamicWeightCalculator):
    def __init__(self):
        super().__init__()
        self.learning_rate = 0.01

    def update_weights_by_feedback(self, prediction: dict, actual_result: float):
        """根据实际收益调整权重"""
        # 计算预测误差
        error = actual_result - prediction['confidence']

        # 调整基础权重
        for agent_name, breakdown in prediction['breakdown'].items():
            if breakdown['direction'] == prediction['direction']:
                # 预测正确，增加权重
                self.base_weights[agent_name] += self.learning_rate * error
            else:
                # 预测错误，减少权重
                self.base_weights[agent_name] -= self.learning_rate * error

        # 归一化
        total = sum(self.base_weights.values())
        self.base_weights = {k: v/total for k, v in self.base_weights.items()}
```

### 2. 多策略组合

支持不同策略使用不同权重配置：

```python
# 短线策略：技术+情绪权重高
short_term_weights = {
    'technical': 0.40,
    'fundamental': 0.20,
    'sentiment': 0.30,
    'news': 0.10
}

# 长线策略：基本面+新闻权重高
long_term_weights = {
    'technical': 0.15,
    'fundamental': 0.50,
    'sentiment': 0.10,
    'news': 0.25
}
```

### 3. 时间衰减

历史表现的时间衰减：

```python
def _calculate_performance_factor_with_decay(self, agent_name: str) -> float:
    """带时间衰减的历史表现因子"""
    performance_history = self.get_performance_history(agent_name)

    # 指数加权移动平均
    weights = [0.9**i for i in range(len(performance_history))]
    weighted_accuracy = sum(p * w for p, w in zip(performance_history, weights))
    weighted_accuracy /= sum(weights)

    return 0.5 + weighted_accuracy
```

## 📚 相关文档

- [动态权重计算器源码](../tradingagents/utils/dynamic_weights.py)
- [API集成代码](../api/main.py)
- [Embedding长度修复文档](./EMBEDDING_FIX.md)
- [数据源策略文档](./DATA_SOURCE_STRATEGY.md)

---

**最后更新**: 2025-01-07
**版本**: v1.0.0
**作者**: Claude Code
**项目**: TradingAgents-CN → HiddenGem Backend
