# 多策略并行交易系统实现文档

## 概述

本文档描述了HiddenGem交易系统中多策略并行交易功能的实现。该系统允许用户同时运行多个交易策略并进行实时性能对照。

## 功能特性

### 1. 五种预定义策略模式

| 模式ID | 名称 | 描述 | 组件 |
|--------|------|------|------|
| `rl_only` | 单RL模型 | 纯强化学习决策，基于历史数据训练的PPO模型 | RL |
| `llm_agent_only` | 单LLM Agent | 多Agent智能分析系统，7个专业分析师协同决策 | LLM Agent |
| `llm_memory` | LLM + Memory Bank | LLM分析结合历史案例记忆库，从相似场景中学习 | LLM Agent, Memory Bank |
| `rl_llm` | RL + LLM | 强化学习与LLM双重验证，提高决策准确性 | RL, LLM Agent |
| `rl_llm_memory` | RL + LLM + Memory | 完整系统：强化学习 + LLM分析 + 历史案例，三重保障 | RL, LLM Agent, Memory Bank |

### 2. 核心功能

- ✅ **单选/多选策略**: 用户可以选择一个或多个策略同时运行
- ✅ **并行执行**: 多个策略在同一交易周期内并行生成信号并执行
- ✅ **独立资金管理**: 每个策略拥有独立的SimulatedBroker和初始资金
- ✅ **实时性能追踪**: 记录每个策略的盈亏、胜率、交易次数等指标
- ✅ **性能对照展示**: 前端以卡片形式展示各策略表现，支持排名比较
- ✅ **策略组合**: 支持RL和LLM策略的灵活组合，使用加权投票机制

## 架构设计

### 后端架构

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                      │
│  /api/v1/auto-trading/start (strategy_modes: [])           │
│  /api/v1/auto-trading/status (strategy_performances: [])   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              AutoTradingService                             │
│  - 接收strategy_modes参数                                    │
│  - 使用StrategyFactory创建多个策略实例                        │
│  - 使用MultiStrategyManager管理并行执行                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              StrategyFactory                                │
│  - create_strategy(mode_id) -> CombinedStrategy            │
│  - create_multi_strategies(mode_ids) -> Dict[Strategy]     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              CombinedStrategy                               │
│  - 根据mode_info初始化rl_strategy和llm_strategy              │
│  - generate_signal(): 组合多个子策略的信号                    │
│  - _combine_signals(): 使用加权投票机制                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  RLStrategy  │  │MultiAgentStr │  │ MemoryBank   │
│              │  │ategy         │  │ (TODO)       │
└──────────────┘  └──────────────┘  └──────────────┘
```

### MultiStrategyManager架构

```
┌─────────────────────────────────────────────────────────────┐
│              MultiStrategyManager                           │
│                                                             │
│  strategies: {                                              │
│    'rl_only': CombinedStrategy(RL),                        │
│    'llm_agent_only': CombinedStrategy(LLM)                 │
│  }                                                          │
│                                                             │
│  brokers: {                                                 │
│    'rl_only': SimulatedBroker(cash=100000),                │
│    'llm_agent_only': SimulatedBroker(cash=100000)          │
│  }                                                          │
│                                                             │
│  performances: {                                            │
│    'rl_only': StrategyPerformance(...),                    │
│    'llm_agent_only': StrategyPerformance(...)              │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

## 核心代码文件

### 1. `trading/strategy_factory.py`

**职责**: 策略工厂，负责创建和配置策略实例

**关键类**:
- `StrategyMode`: 定义5种策略模式的元数据
- `CombinedStrategy`: 组合策略类，可包含多个子策略
- `StrategyFactory`: 工厂类，创建单个或多个策略实例

**关键方法**:
```python
@staticmethod
def create_strategy(mode_id: str, rl_model_path: str) -> BaseStrategy:
    """根据mode_id创建单个策略"""

@staticmethod
def create_multi_strategies(mode_ids: List[str], rl_model_path: str) -> Dict[str, BaseStrategy]:
    """批量创建多个策略"""
```

### 2. `trading/multi_strategy_manager.py`

**职责**: 管理多个策略的并行执行和性能追踪

**关键类**:
- `StrategyPerformance`: 单个策略的性能追踪
- `MultiStrategyManager`: 多策略管理器

**关键方法**:
```python
def generate_signals(self, symbol: str, current_data, market_prices: Dict) -> Dict[str, Dict]:
    """为所有策略生成交易信号"""

def execute_signals(self, symbol: str, signals: Dict, current_price: float, market_prices: Dict):
    """执行所有策略的交易信号"""

def get_performances(self) -> List[Dict[str, Any]]:
    """获取所有策略的表现数据"""
```

### 3. `api/services/auto_trading_service.py`

**职责**: 自动交易服务层，封装业务逻辑

**关键修改**:
```python
async def start(
    self,
    symbols: List[str],
    initial_cash: float = 100000.0,
    check_interval: int = 5,
    use_multi_agent: bool = True,
    strategy_modes: List[str] = None  # 新增参数
):
    """启动自动交易，支持多策略"""
    # 使用StrategyFactory创建多个策略
    strategies = StrategyFactory.create_multi_strategies(strategy_modes)
    # 使用MultiStrategyManager管理
    self.strategy_manager = MultiStrategyManager(strategies, initial_cash)
```

### 4. `api/routers/auto_trading.py`

**职责**: FastAPI路由，处理HTTP请求

**关键修改**:
```python
class AutoTradingConfig(BaseModel):
    strategy_modes: List[str] = []  # 新增字段

class StrategyPerformance(BaseModel):  # 新增模型
    strategy_id: str
    strategy_name: str
    total_trades: int
    win_rate: float
    profit_loss: float
    profit_loss_pct: float

class AutoTradingStatus(BaseModel):
    strategy_performances: List[StrategyPerformance] = []  # 新增字段
    num_strategies: int = 0  # 新增字段
```

### 5. `frontend/src/components/trading/tabs/AutoTradingTab.tsx`

**职责**: 前端交易界面，策略选择和性能展示

**关键功能**:
- 策略模式选择UI（lines 744-831）
- 多策略性能对照面板（lines 375-473）
- API调用传递strategy_modes（lines 162-177）

## 数据流

### 启动流程

```
用户选择策略 → Frontend
                   │
                   │ POST /api/v1/auto-trading/start
                   │ { strategy_modes: ['rl_only', 'llm_agent_only'] }
                   ▼
            AutoTradingRouter
                   │
                   ▼
         AutoTradingService.start()
                   │
                   ├─→ StrategyFactory.create_multi_strategies()
                   │        │
                   │        ├─→ create_strategy('rl_only')
                   │        │      └─→ CombinedStrategy(RL)
                   │        │
                   │        └─→ create_strategy('llm_agent_only')
                   │               └─→ CombinedStrategy(LLM)
                   │
                   └─→ MultiStrategyManager(strategies, initial_cash)
                            │
                            ├─→ 为每个策略创建独立broker
                            └─→ 为每个策略创建performance tracker
```

### 交易循环

```
每个check_interval:
    │
    ├─→ MultiStrategyManager.generate_signals()
    │        │
    │        ├─→ strategy_1.generate_signal() → signal_1
    │        ├─→ strategy_2.generate_signal() → signal_2
    │        └─→ 返回 {strategy_1: signal_1, strategy_2: signal_2}
    │
    ├─→ MultiStrategyManager.execute_signals()
    │        │
    │        ├─→ 对每个signal:
    │        │     ├─→ 使用对应的broker执行交易
    │        │     ├─→ 记录到对应的performance
    │        │     └─→ 更新投资组合状态
    │        │
    │        └─→ 完成
    │
    └─→ 等待下一个周期
```

### 状态查询

```
用户刷新页面 → Frontend
                    │
                    │ GET /api/v1/auto-trading/status
                    ▼
            AutoTradingRouter
                    │
                    ▼
         AutoTradingService.get_status()
                    │
                    ├─→ MultiStrategyManager.get_performances()
                    │        │
                    │        └─→ [
                    │              {strategy_id: 'rl_only', profit_loss: 1200, ...},
                    │              {strategy_id: 'llm_agent_only', profit_loss: 800, ...}
                    │            ]
                    │
                    └─→ 返回 {
                          is_running: true,
                          strategy_performances: [...],
                          num_strategies: 2,
                          ...
                        }
                    ▼
                Frontend
                    │
                    └─→ 显示多策略对照面板
```

## 关键设计决策

### 1. 独立Broker vs 共享Broker

**决策**: 每个策略使用独立的SimulatedBroker

**理由**:
- 确保策略之间完全隔离，互不影响
- 便于精确追踪每个策略的资金使用情况
- 支持不同策略使用不同的初始资金
- 避免资金竞争和持仓冲突

### 2. 策略组合机制

**决策**: 使用加权投票机制组合多个子策略

**实现**:
```python
def _combine_signals(self, signals: List[Dict]) -> Dict:
    action_weights = {'buy': 0.0, 'sell': 0.0, 'hold': 0.0}

    for sig in signals:
        action = sig['signal'].get('action', 'hold')
        weight = sig['weight']
        action_weights[action] += weight

    final_action = max(action_weights, key=action_weights.get)
    return {
        'action': final_action,
        'confidence': action_weights[final_action] / len(signals)
    }
```

**优点**:
- 简单直观，易于理解
- 支持灵活的权重配置
- 可扩展支持更多子策略

### 3. 前端策略名称映射

**问题**: 前端期望的名称与TradingAgents内部名称不同

**解决**: 在StrategyMode中统一定义，后端直接使用这些ID

**映射**:
- `rl_only` → RL模型
- `llm_agent_only` → LLM Agent
- `llm_memory` → LLM + Memory Bank
- `rl_llm` → RL + LLM
- `rl_llm_memory` → RL + LLM + Memory

## 已修复的Bug

### Bug 1: SimulatedBroker属性访问错误

**错误**: `AttributeError: 'SimulatedBroker' object has no attribute 'portfolio'`

**原因**: SimulatedBroker直接存储`cash`和`positions`，不是嵌套在`portfolio`下

**修复**:
```python
# 错误写法:
broker.portfolio.cash
broker.portfolio.positions

# 正确写法:
broker.cash
broker.positions
```

### Bug 2: Order初始化参数错误

**错误**: `Order.__init__() got an unexpected keyword argument 'price'`

**原因**: Order类不接受`price`参数，市价单不需要价格

**修复**:
```python
# 错误写法:
Order(symbol=symbol, side=OrderSide.BUY, quantity=100, order_type=OrderType.MARKET, price=10.0)

# 正确写法:
Order(symbol=symbol, side=OrderSide.BUY, quantity=100, order_type=OrderType.MARKET)
```

### Bug 3: RL模型路径错误

**错误**: `Model file not found: models/production/final_model.zip`

**修复**: 更新为 `models/production/final_model.zip`

### Bug 4: 前端重复变量声明

**错误**: `Identifier 'isEditingRisk' has already been declared`

**修复**: 移除重复的useState声明

## 测试建议

### 1. 单策略测试

```bash
# 启动后端
cd backend
uvicorn main:app --reload

# 前端选择单个策略（如'单RL模型'）
# 验证:
# - 策略正常启动
# - 能够生成交易信号
# - 性能数据正确显示
```

### 2. 多策略对照测试

```bash
# 前端选择多个策略（如'单RL模型' + '单LLM Agent'）
# 验证:
# - 两个策略同时启动
# - 各自独立执行交易
# - 性能对照面板显示两个策略的指标
# - 排名正确显示
```

### 3. 策略组合测试

```bash
# 前端选择'RL + LLM'策略
# 验证:
# - RL和LLM子策略都被初始化
# - 信号通过投票机制生成
# - 最终决策逻辑正确
```

### 4. 并发测试

```bash
# 选择全部5个策略同时运行
# 验证:
# - 系统能够处理5个策略的并发执行
# - 性能追踪数据准确
# - 前端显示不卡顿
```

## API使用示例

### 启动多策略交易

```bash
curl -X POST "http://localhost:8000/api/v1/auto-trading/start" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["000001", "600519", "000858"],
    "initial_cash": 100000,
    "check_interval": 5,
    "use_multi_agent": true,
    "strategy_modes": ["rl_only", "llm_agent_only", "rl_llm"]
  }'
```

**响应**:
```json
{
  "success": true,
  "message": "自动交易已启动，运行 3 个策略",
  "data": {
    "symbols": ["000001", "600519", "000858"],
    "started_at": "2025-01-14T10:30:00",
    "num_strategies": 3,
    "strategy_modes": ["rl_only", "llm_agent_only", "rl_llm"]
  }
}
```

### 查询状态

```bash
curl "http://localhost:8000/api/v1/auto-trading/status"
```

**响应**:
```json
{
  "success": true,
  "data": {
    "is_running": true,
    "num_strategies": 3,
    "strategy_performances": [
      {
        "strategy_id": "rl_only",
        "strategy_name": "单RL模型",
        "total_trades": 5,
        "winning_trades": 3,
        "win_rate": 60.0,
        "profit_loss": 1200.50,
        "profit_loss_pct": 1.20,
        "num_positions": 2,
        "current_cash": 95000.00,
        "current_value": 101200.50
      },
      {
        "strategy_id": "llm_agent_only",
        "strategy_name": "单LLM Agent",
        "total_trades": 4,
        "winning_trades": 3,
        "win_rate": 75.0,
        "profit_loss": 800.30,
        "profit_loss_pct": 0.80,
        "num_positions": 1,
        "current_cash": 97000.00,
        "current_value": 100800.30
      },
      {
        "strategy_id": "rl_llm",
        "strategy_name": "RL + LLM",
        "total_trades": 6,
        "winning_trades": 4,
        "win_rate": 66.67,
        "profit_loss": 1500.80,
        "profit_loss_pct": 1.50,
        "num_positions": 3,
        "current_cash": 92000.00,
        "current_value": 101500.80
      }
    ]
  }
}
```

## 未来改进

### 1. Memory Bank集成

当前Memory Bank功能标记为TODO，需要:
- 实现MemoryBankStrategy类
- 集成ChromaDB存储历史案例
- 在CombinedStrategy中支持use_memory配置

### 2. 策略权重配置

允许用户自定义子策略的投票权重:
```python
{
  "mode_id": "rl_llm",
  "weights": {
    "rl": 0.6,
    "llm": 0.4
  }
}
```

### 3. 动态策略调整

支持在运行时添加或移除策略，无需重启系统

### 4. 高级性能指标

添加更多性能指标:
- 夏普比率
- 最大回撤
- 年化收益率
- 卡尔玛比率

### 5. 策略对照报告

生成详细的策略对照分析报告，包括:
- 收益曲线对比图
- 风险指标对比表
- 交易行为分析
- 推荐最优策略组合

## 相关文档

- [CLAUDE.md](../CLAUDE.md) - 项目开发指南
- [API.md](./API.md) - 完整API文档
- [strategy_factory.py](../trading/strategy_factory.py) - 策略工厂源码
- [multi_strategy_manager.py](../trading/multi_strategy_manager.py) - 多策略管理器源码

---

**创建时间**: 2025-01-14
**最后更新**: 2025-01-14
**维护者**: Claude Code
**版本**: v1.0.0
