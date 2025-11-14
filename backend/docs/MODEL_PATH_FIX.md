# RL模型路径修复

## 问题描述

系统中多处使用了错误的RL模型路径 `models/ppo_trading_agent.zip`，应该使用正确的路径 `models/production/final_model.zip`。

## 修复的文件

### 1. `trading/rl_strategy.py`

**修改前**:
```python
def __init__(self, model_path: str = 'models/ppo_trading_agent.zip'):
```

**修改后**:
```python
def __init__(self, model_path: str = 'models/production/final_model.zip'):
```

### 2. `trading/strategy_factory.py` (3处)

**修改前**:
```python
# Line 94
def __init__(self, mode_id: str, rl_model_path: str = "models/production/ppo_trading_agent.zip"):

# Line 255
def create_strategy(mode_id: str, rl_model_path: str = "models/production/ppo_trading_agent.zip"):

# Line 280
def create_multi_strategies(mode_ids: List[str], rl_model_path: str = "models/production/ppo_trading_agent.zip"):
```

**修改后**:
```python
# Line 94
def __init__(self, mode_id: str, rl_model_path: str = "models/production/final_model.zip"):

# Line 255
def create_strategy(mode_id: str, rl_model_path: str = "models/production/final_model.zip"):

# Line 280
def create_multi_strategies(mode_ids: List[str], rl_model_path: str = "models/production/final_model.zip"):
```

### 3. `api/routers/strategies.py`

**修改前**:
```python
strategy = RLStrategy(model_path="models/ppo_trading_agent.zip")
```

**修改后**:
```python
strategy = RLStrategy(model_path="models/production/final_model.zip")
```

### 4. `docs/MULTI_STRATEGY_IMPLEMENTATION.md`

文档中所有模型路径引用已更新为 `final_model.zip`。

## 验证结果

运行验证脚本 `scripts/verify_multi_strategy.py`:

```
============================================================
验证结果汇总
============================================================
文件检查: [OK] 通过
模型文件: [OK] 存在
模块导入: [OK] 通过
策略配置: [OK] 通过

[OK] 多策略交易系统配置正确！
```

## 正确的模型路径规范

从此以后，所有RL模型相关代码应使用以下标准路径：

- **生产模型**: `models/production/final_model.zip`
- **训练输出**: `models/production/final_model.zip`
- **默认路径**: `models/production/final_model.zip`

## 其他文件说明

以下文件也包含旧路径，但主要用于测试/演示，暂不修改：

- `scripts/test_qflib_backtest.py` - 测试脚本
- `scripts/train_rl_*.py` - 训练脚本（会生成新模型）
- `scripts/test_paper_trading*.py` - 模拟交易测试
- `scripts/auto_paper_trading.py` - 自动模拟交易
- `scripts/simple_time_travel.py` - 时光机测试

这些脚本如果需要使用RL模型，应该在运行时指定正确的模型路径。

## Git提交

共计3个提交修复此问题：

```
commit 21d350f
fix(trading): 修复strategy_factory中遗漏的模型路径
- 更新 create_strategy 方法的默认参数
- 更新 create_multi_strategies 方法的默认参数

commit bf998b8
fix(trading): 更正RL模型路径为final_model.zip
- 修复 RLStrategy 默认模型路径
- 修复 strategies.py 中的模型路径
- 更新文档中的模型路径引用

commit 2397fe9
docs: 添加RL模型路径修复文档
```

所有核心文件中的模型路径已全部更正完成。

---

**修复日期**: 2025-11-14
**修复人**: Claude Code
**状态**: ✅ 已完成并验证
