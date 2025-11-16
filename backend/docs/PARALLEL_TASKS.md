# HiddenGem 并行开发任务分配

> **更新时间**: 2025-01-09
> **协调者**: Claude Instance #1
> **目标**: 实现完整的RL交易系统（回测 → 模拟交易 → 真实交易）

---

## 任务总览

本文档将RL交易系统的实现拆分为**6个并行任务**，每个任务可由独立的Claude实例完成。

```
整体架构：
┌──────────────┐
│ TradingAgents│  ← 已完成✅（信号生成）
│  + Memory    │
└──────┬───────┘
       │ LLM信号
       ▼
┌──────────────────────────────────────────────────┐
│              RL Decision Engine                   │
│  (Task 1: 基于FinRL实现CVaR-PPO)                 │
└──────────────┬───────────────────────────────────┘
               │ 交易决策
               ▼
       ┌───────┴────────┐
       │                 │
   ┌───▼────┐      ┌────▼────┐
   │Task 2  │      │ Task 3  │
   │回测系统│      │Paper    │
   │        │      │Trading  │
   └────────┘      └────┬────┘
                        │
                ┌───────┴────────┐
                │                 │
           ┌────▼─────┐     ┌────▼────┐
           │ Task 4   │     │ Task 5  │
           │东财模拟盘│     │东财真盘│
           └──────────┘     └─────────┘
                             (谨慎！)
```

---

## 任务分配矩阵

| 任务ID | 任务名称 | 优先级 | 预计时间 | 状态 | 负责Instance | 依赖 |
|--------|---------|--------|---------|------|--------------|------|
| Task 1 | RL引擎集成FinRL | 🔴 P0 | 2周 | 🔄 进行中 | Instance #1 | 无 |
| Task 2 | 回测系统 | 🟠 P1 | 1周 | ⏸️ 待开始 | Instance #2 | Task 1 |
| Task 3 | Paper Trading | 🟠 P1 | 1.5周 | ⏸️ 待开始 | Instance #3 | Task 1 |
| Task 4 | 东财模拟盘 | 🟡 P2 | 1周 | ⏸️ 待开始 | Instance #4 | Task 3 |
| Task 5 | 东财真实盘 | 🔵 P3 | 1周 | ⏸️ 待开始 | Instance #5 | Task 4 ✅ |
| Task 6 | 性能监控 | 🟠 P1 | 1周 | ⏸️ 待开始 | Instance #6 | Task 2, 3 |

**优先级说明**:
- 🔴 **P0 (Critical)**: 阻塞性任务，必须优先完成
- 🟠 **P1 (High)**: 核心功能，尽快完成
- 🟡 **P2 (Medium)**: 重要功能，可并行开发
- 🔵 **P3 (Low)**: 可选功能，充分验证后再实现

---

## Task 1: RL决策引擎（基于FinRL）🔴

**负责人**: Instance #1
**优先级**: P0 (Critical)
**状态**: 🔄 进行中

### 目标
实现基于FinRL的RL决策引擎，整合TradingAgents的LLM信号。

### 详细任务

#### 1.1 扩展FinRL环境 (3天)
**文件**: `backend/tradingagents/rl/llm_enhanced_env.py`

```python
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv

class LLMEnhancedTradingEnv(StockTradingEnv):
    """扩展FinRL环境，添加TradingAgents的LLM信号"""

    def __init__(self, df, trading_graph, memory_manager, **kwargs):
        super().__init__(df, **kwargs)
        self.trading_graph = trading_graph
        self.memory_manager = memory_manager

    def _get_observation(self):
        # 1. FinRL原始观察
        base_obs = super()._get_observation()

        # 2. TradingAgents LLM信号
        llm_signals = self._get_llm_signals()

        # 3. 记忆检索信号
        memory_signals = self._get_memory_signals()

        # 4. 合并
        return np.concatenate([base_obs, llm_signals, memory_signals])
```

**验收标准**:
- [ ] 环境可以正常初始化
- [ ] `_get_observation()` 返回扩展后的状态向量
- [ ] 能够正确调用TradingAgents和Memory系统
- [ ] 通过单元测试

#### 1.2 自定义奖励函数 (2天)
**文件**: `backend/tradingagents/rl/reward_function.py`

```python
def calculate_reward_with_cvar(
    portfolio_value_change,
    actions,
    turbulence,
    cost,
    cvar_alpha=0.95,
    risk_penalty=0.1
):
    """CVaR约束的奖励函数"""
    # 1. 收益奖励
    # 2. CVaR风险惩罚
    # 3. 市场波动惩罚
    # 4. 交易成本
    return reward
```

**验收标准**:
- [ ] 奖励函数考虑收益和风险
- [ ] CVaR惩罚正确计算
- [ ] 通过回测验证奖励合理性

#### 1.3 数据准备 (2天)
**文件**: `backend/tradingagents/rl/data_preparation.py`

```python
def prepare_data_for_training(symbol, start_date, end_date):
    """准备FinRL格式的训练数据"""
    # 1. 获取数据（使用已有接口）
    # 2. 转换为FinRL格式
    # 3. 添加技术指标
    # 4. 数据分割（train/val/test）
    return train, val, test
```

**验收标准**:
- [ ] 数据格式符合FinRL要求
- [ ] 包含必要的技术指标
- [ ] 正确分割训练/验证/测试集

#### 1.4 训练脚本 (3天)
**文件**: `backend/scripts/train_rl_with_finrl.py`

```python
def train_rl_agent(symbol, start_date, end_date):
    """训练RL Agent"""
    # 1. 准备数据
    # 2. 初始化TradingAgents
    # 3. 初始化记忆系统（训练模式）
    # 4. 创建LLMEnhancedTradingEnv
    # 5. 创建PPO模型
    # 6. 训练
    # 7. 保存模型
    # 8. 验证集评估
```

**验收标准**:
- [ ] 训练循环正常运行
- [ ] 可以保存和加载模型
- [ ] 输出训练日志和指标
- [ ] 验证集收益 > 基准（买入持有）

### 接口定义

**输入**:
- 股票代码（symbol）
- 训练时间范围（start_date, end_date）
- 配置参数（RL_CONFIG）

**输出**:
- 训练好的PPO模型（保存在`models/`）
- 训练日志（TensorBoard）
- 验证结果报告（JSON）

**暴露接口**:
```python
# 其他任务可以调用
from tradingagents.rl.llm_enhanced_env import LLMEnhancedTradingEnv
from tradingagents.rl.reward_function import calculate_reward_with_cvar

# 加载训练好的模型
model = PPO.load("models/rl_agent_600519.SH")
```

---

## Task 2: 回测系统 🟠

**负责人**: Instance #2
**优先级**: P1 (High)
**依赖**: Task 1 完成
**状态**: ⏸️ 待开始

### 目标
实现完整的回测系统，支持RL策略和传统策略的性能评估。

### 详细任务

#### 2.1 回测引擎 (3天)
**文件**: `backend/trading/backtester.py`

```python
class Backtester:
    """回测引擎"""

    def __init__(self, strategy, initial_capital=100000):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.portfolio = PortfolioManager(initial_capital)
        self.performance = PerformanceTracker(initial_capital)

    def run(self, data, start_date, end_date):
        """执行回测"""
        for date in trading_days:
            # 1. 获取当前状态
            # 2. 策略决策
            # 3. 模拟交易执行
            # 4. 更新持仓和绩效
            # 5. 记录结果

        return self.generate_report()

    def generate_report(self):
        """生成回测报告"""
        return {
            'total_return': ...,
            'sharpe_ratio': ...,
            'max_drawdown': ...,
            'win_rate': ...,
            'trades': [...],
            'equity_curve': [...]
        }
```

**验收标准**:
- [ ] 支持RL策略和规则策略
- [ ] 正确处理买入/卖出信号
- [ ] 考虑交易成本和滑点
- [ ] 生成详细的回测报告

#### 2.2 性能指标计算 (2天)
**文件**: `backend/trading/metrics.py`

```python
def calculate_sharpe_ratio(returns, risk_free_rate=0.03):
    """夏普比率"""
    pass

def calculate_max_drawdown(equity_curve):
    """最大回撤"""
    pass

def calculate_calmar_ratio(returns, max_drawdown):
    """卡玛比率"""
    pass

def calculate_win_rate(trades):
    """胜率"""
    pass
```

**验收标准**:
- [ ] 实现常见性能指标
- [ ] 与PyFolio结果一致
- [ ] 处理边界情况

#### 2.3 回测报告生成 (2天)
**文件**: `backend/trading/report_generator.py`

```python
class ReportGenerator:
    """回测报告生成器"""

    def generate_html_report(self, backtest_result):
        """生成HTML格式报告"""
        # 1. 绩效摘要
        # 2. 权益曲线图
        # 3. 回撤曲线图
        # 4. 月度收益热力图
        # 5. 交易明细表
        pass

    def generate_json_report(self, backtest_result):
        """生成JSON格式报告"""
        pass
```

**验收标准**:
- [ ] 生成可视化HTML报告
- [ ] 包含关键图表（权益曲线、回撤等）
- [ ] 导出JSON用于API

### 接口定义

**输入**:
- RL模型或策略实例
- 回测数据
- 回测配置

**输出**:
- 回测报告（HTML + JSON）
- 交易记录（DataFrame）
- 绩效指标（dict）

**暴露接口**:
```python
from trading.backtester import Backtester
from trading.metrics import calculate_sharpe_ratio

# 运行回测
backtester = Backtester(strategy=rl_strategy)
result = backtester.run(data, "2020-01-01", "2024-12-31")
```

---

## Task 3: Paper Trading系统 🟠

**负责人**: Instance #3
**优先级**: P1 (High)
**依赖**: Task 1 完成
**状态**: ⏸️ 待开始

### 目标
实现实时模拟交易系统，可以在真实市场环境中测试策略而不动用真实资金。

### 详细任务

#### 3.1 模拟交易引擎 (4天)
**文件**: `backend/trading/paper_trading_engine.py`

```python
class PaperTradingEngine:
    """模拟交易引擎"""

    def __init__(self, rl_agent, config):
        self.rl_agent = rl_agent
        self.portfolio = PortfolioManager(config['initial_cash'])
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager(config)
        self.market_feed = RealTimeMarketFeed()

    async def run(self, symbols):
        """运行模拟交易"""
        while self.is_running:
            for symbol in symbols:
                # 1. 获取实时数据
                current_data = await self.market_feed.get_realtime_data(symbol)

                # 2. 获取LLM信号
                llm_signals = await self._get_llm_signals(symbol)

                # 3. 构建RL状态
                state = self._build_state(symbol, current_data, llm_signals)

                # 4. RL决策
                action = self.rl_agent.predict(state)

                # 5. 生成订单
                order = self._create_order_from_action(symbol, action)

                # 6. 风控检查
                if self.risk_manager.validate_order(order):
                    # 7. 模拟执行
                    self.order_manager.execute_order_simulated(order, current_data['price'])

            await asyncio.sleep(60)  # 每分钟执行一次
```

**验收标准**:
- [ ] 支持实时数据获取
- [ ] 支持多股票并发交易
- [ ] 正确执行RL决策
- [ ] 风控检查正常工作
- [ ] 可以启动/停止/暂停

#### 3.2 实时市场数据源 (3天)
**文件**: `backend/trading/market_data_feed.py`

```python
class RealTimeMarketFeed:
    """实时市场数据源"""

    def __init__(self, provider='tushare'):
        self.provider = provider
        self.cache = {}

    async def get_realtime_data(self, symbol):
        """获取实时行情"""
        # 1. 检查缓存
        # 2. 调用数据源API
        # 3. 更新缓存
        return {
            'symbol': symbol,
            'price': price,
            'volume': volume,
            'timestamp': timestamp
        }

    def subscribe(self, symbols):
        """订阅实时行情（WebSocket）"""
        pass
```

**验收标准**:
- [ ] 支持实时行情获取
- [ ] 支持WebSocket订阅（可选）
- [ ] 数据缓存机制
- [ ] 处理API限流

#### 3.3 模拟订单执行 (2天)
**文件**: `backend/trading/simulated_broker.py`

```python
class SimulatedBroker:
    """模拟券商"""

    def execute_market_order(self, order, current_price):
        """执行市价单"""
        # 1. 模拟成交价（加入滑点）
        # 2. 计算手续费
        # 3. 更新持仓
        # 4. 记录成交
        pass

    def execute_limit_order(self, order, current_price):
        """执行限价单"""
        # 挂单逻辑
        pass
```

**验收标准**:
- [ ] 支持市价单和限价单
- [ ] 模拟滑点和手续费
- [ ] 记录完整的成交历史

#### 3.4 Paper Trading API (2天)
**文件**: `backend/api/routers/paper_trading.py`

```python
@router.post("/paper-trading/start")
async def start_paper_trading(request: StartPaperTradingRequest):
    """启动模拟交易"""
    pass

@router.post("/paper-trading/stop")
async def stop_paper_trading():
    """停止模拟交易"""
    pass

@router.get("/paper-trading/status")
async def get_paper_trading_status():
    """获取模拟交易状态"""
    pass

@router.get("/paper-trading/portfolio")
async def get_portfolio():
    """获取当前持仓"""
    pass
```

**验收标准**:
- [ ] API可以启动/停止模拟交易
- [ ] 可以查询实时状态
- [ ] 可以查询持仓和订单

### 接口定义

**输入**:
- RL模型
- 交易配置（股票列表、初始资金等）
- 风控参数

**输出**:
- 实时持仓状态
- 订单历史
- 实时绩效

**暴露接口**:
```python
from trading.paper_trading_engine import PaperTradingEngine

# 启动模拟交易
engine = PaperTradingEngine(rl_agent, config)
await engine.run(['600519.SH', '300750.SZ'])
```

---

## Task 4: 东方财富模拟盘接入 🟡

**负责人**: Instance #4
**优先级**: P2 (Medium)
**依赖**: Task 3 完成
**状态**: ⏸️ 待开始

### 目标
对接东方财富的模拟盘，使用真实市场环境测试策略。

### 详细任务

#### 4.1 东财模拟盘SDK集成 (3天)
**文件**: `backend/trading/eastmoney_sim_broker.py`

```python
class EastmoneySimulatedBroker:
    """东方财富模拟盘"""

    def __init__(self, account_config):
        # 方案1: 使用easytrader（如果支持模拟盘）
        # 方案2: 直接调用东财API
        # 方案3: 使用Selenium自动化
        pass

    def login(self):
        """登录模拟盘"""
        pass

    def submit_order(self, order):
        """提交订单到模拟盘"""
        pass

    def get_positions(self):
        """获取持仓"""
        pass

    def get_balance(self):
        """获取资金"""
        pass

    def cancel_order(self, order_id):
        """撤单"""
        pass
```

**验收标准**:
- [ ] 可以登录东财模拟盘
- [ ] 可以提交买卖订单
- [ ] 可以查询持仓和资金
- [ ] 可以撤单
- [ ] 错误处理完善

#### 4.2 适配Paper Trading接口 (2天)
**文件**: `backend/trading/adapters/eastmoney_adapter.py`

```python
class EastmoneyAdapter:
    """东财模拟盘适配器"""

    def __init__(self, broker):
        self.broker = broker

    def adapt_order(self, internal_order):
        """转换订单格式"""
        # 内部格式 -> 东财格式
        pass

    def adapt_position(self, eastmoney_position):
        """转换持仓格式"""
        # 东财格式 -> 内部格式
        pass
```

**验收标准**:
- [ ] 订单格式正确转换
- [ ] 持仓格式正确转换
- [ ] 兼容Paper Trading引擎

### 接口定义

**输入**:
- 东财模拟盘账号配置
- 订单请求

**输出**:
- 订单执行结果
- 持仓信息
- 资金信息

**暴露接口**:
```python
from trading.eastmoney_sim_broker import EastmoneySimulatedBroker

# 使用东财模拟盘
broker = EastmoneySimulatedBroker(account_config)
broker.submit_order(order)
```

---

## Task 5: 东方财富真实盘接入 🔵

**负责人**: Instance #5
**优先级**: P3 (Low)
**依赖**: Task 4 完成并充分验证 ✅
**状态**: ⏸️ 待开始

### ⚠️ 重要警告

**此任务涉及真实资金交易，必须满足以下条件才能开始**:
- ✅ Task 4 (模拟盘) 已完成且稳定运行至少1个月
- ✅ 回测收益率 > 20% (年化)
- ✅ 模拟盘收益率 > 15% (至少3个月)
- ✅ 最大回撤 < 10%
- ✅ 胜率 > 60%
- ✅ 通过完整的风控测试
- ✅ 用户明确授权

**建议**:
1. 仅使用小额资金测试（如1000-5000元）
2. 设置严格的单日亏损限制（如2%）
3. 设置严格的总亏损限制（如10%）
4. 设置人工确认机制
5. 保留手动紧急停止功能

### 详细任务

#### 5.1 东财真实盘SDK集成 (3天)
**文件**: `backend/trading/eastmoney_live_broker.py`

```python
class EastmoneyLiveBroker:
    """东方财富真实盘（极度谨慎！）"""

    def __init__(self, account_config, safety_config):
        # 使用easytrader
        from easytrader import use
        self.trader = use('eastmoney')
        self.trader.prepare(account_config)

        # 安全配置
        self.safety_limits = safety_config
        self.daily_loss_limit = safety_config['daily_loss_limit']
        self.total_loss_limit = safety_config['total_loss_limit']
        self.require_confirmation = safety_config.get('require_confirmation', True)

    def submit_order(self, order):
        """提交订单（带安全检查）"""
        # 1. 检查是否触发停损
        if self._check_stop_loss():
            raise Exception("触发停损限制，拒绝交易")

        # 2. 检查订单风控
        if not self._validate_order_safety(order):
            raise Exception("订单未通过风控检查")

        # 3. 人工确认（可选）
        if self.require_confirmation:
            confirmed = self._request_confirmation(order)
            if not confirmed:
                raise Exception("订单未获得人工确认")

        # 4. 提交订单
        result = self.trader.buy(order['symbol'], order['price'], order['amount'])

        # 5. 记录日志
        self._log_order(order, result)

        return result
```

**验收标准**:
- [ ] 可以连接真实盘
- [ ] 安全限制正常工作
- [ ] 人工确认机制可用
- [ ] 紧急停止功能可用
- [ ] 完整的日志记录

#### 5.2 多层风控系统 (2天)
**文件**: `backend/trading/live_risk_control.py`

```python
class LiveRiskControl:
    """真实盘风控（多层防护）"""

    def check_daily_loss(self):
        """检查日内亏损"""
        pass

    def check_total_loss(self):
        """检查总亏损"""
        pass

    def check_position_limit(self):
        """检查仓位限制"""
        pass

    def check_order_size(self):
        """检查单笔订单大小"""
        pass

    def emergency_stop(self):
        """紧急停止所有交易"""
        pass
```

**验收标准**:
- [ ] 所有风控检查正常工作
- [ ] 触发停损时自动停止交易
- [ ] 紧急停止功能经过测试

### 接口定义

**输入**:
- 东财账号配置（真实账号，加密存储）
- 安全配置（停损限制等）
- 订单请求

**输出**:
- 订单执行结果
- 风控状态
- 实时持仓和资金

---

## Task 6: 性能监控与评估 🟠

**负责人**: Instance #6
**优先级**: P1 (High)
**依赖**: Task 2, Task 3
**状态**: ⏸️ 待开始

### 目标
实现实时性能监控和绩效评估系统。

### 详细任务

#### 6.1 实时性能追踪 (3天)
**文件**: `backend/trading/performance_tracker.py`

```python
class RealTimePerformanceTracker:
    """实时绩效追踪"""

    def __init__(self, initial_capital):
        self.initial_capital = initial_capital
        self.equity_curve = []
        self.trades = []
        self.metrics = {}

    def update(self, timestamp, portfolio_value, trades):
        """更新绩效数据"""
        # 1. 更新权益曲线
        # 2. 计算实时指标
        # 3. 检测异常
        pass

    def get_real_time_metrics(self):
        """获取实时指标"""
        return {
            'current_value': ...,
            'total_return': ...,
            'today_return': ...,
            'sharpe_ratio': ...,
            'max_drawdown': ...,
            'win_rate': ...
        }
```

**验收标准**:
- [ ] 实时计算性能指标
- [ ] 支持多种指标（夏普、卡玛、索提诺等）
- [ ] 异常检测和告警

#### 6.2 可视化Dashboard (3天)
**文件**: `backend/api/routers/dashboard.py`

```python
@router.get("/dashboard/metrics")
async def get_dashboard_metrics():
    """获取Dashboard数据"""
    return {
        'equity_curve': [...],
        'drawdown_curve': [...],
        'daily_returns': [...],
        'positions': [...],
        'recent_trades': [...],
        'metrics': {...}
    }
```

**验收标准**:
- [ ] 提供Dashboard API
- [ ] 返回可视化所需的所有数据
- [ ] 性能优化（缓存）

---

## 协作规范

### 1. 代码规范

**目录结构**:
```
backend/
├── tradingagents/
│   └── rl/              # Task 1: RL引擎
│       ├── llm_enhanced_env.py
│       ├── reward_function.py
│       └── data_preparation.py
├── trading/             # Task 2,3,4,5,6: 交易系统
│   ├── backtester.py    # Task 2
│   ├── metrics.py       # Task 2
│   ├── paper_trading_engine.py  # Task 3
│   ├── market_data_feed.py      # Task 3
│   ├── simulated_broker.py      # Task 3
│   ├── eastmoney_sim_broker.py  # Task 4
│   ├── eastmoney_live_broker.py # Task 5
│   └── performance_tracker.py   # Task 6
├── scripts/
│   └── train_rl_with_finrl.py  # Task 1
└── api/routers/
    ├── paper_trading.py  # Task 3
    └── dashboard.py      # Task 6
```

**命名规范**:
- 文件名: `snake_case.py`
- 类名: `PascalCase`
- 函数名: `snake_case()`
- 常量: `UPPER_CASE`

**注释规范**:
```python
def function_name(param1: str, param2: int) -> dict:
    """简短描述

    Args:
        param1: 参数1说明
        param2: 参数2说明

    Returns:
        返回值说明

    Raises:
        Exception: 异常说明
    """
    pass
```

### 2. Git规范

**分支命名**:
- `task-1-rl-engine` (Task 1)
- `task-2-backtesting` (Task 2)
- `task-3-paper-trading` (Task 3)
- `task-4-eastmoney-sim` (Task 4)
- `task-5-eastmoney-live` (Task 5)
- `task-6-monitoring` (Task 6)

**提交规范**:
```bash
# 格式: <type>(task-X): <description>

feat(task-1): 实现LLMEnhancedTradingEnv
fix(task-3): 修复订单执行逻辑
docs(task-2): 添加回测系统文档
test(task-1): 添加RL环境单元测试
```

**提交频率**:
- 每完成一个子任务就提交
- 提交前确保代码可运行
- 提交前运行测试

### 3. 协作流程

**每日同步**:
1. 每个Instance在开始工作前检查`PARALLEL_TASKS.md`
2. 更新自己任务的状态
3. 查看依赖任务的进度
4. 提交每日进度报告

**接口变更通知**:
- 如果需要修改接口，必须在`PARALLEL_TASKS.md`中标注
- 通知依赖该接口的其他Instance

**问题上报**:
- 遇到阻塞问题，在`PARALLEL_TASKS.md`顶部的"问题列表"中记录
- 标注`[BLOCKED]`并说明原因

### 4. 测试规范

**单元测试**:
```python
# tests/test_task_X.py
import pytest

def test_feature_name():
    """测试功能"""
    # Arrange
    # Act
    # Assert
    pass
```

**集成测试**:
- 每个Task完成后进行集成测试
- 确保与依赖模块正常交互

**性能测试**:
- 关键路径进行性能测试
- 记录基准性能指标

---

## 进度追踪

### 状态更新模板

在每个任务下方更新进度：

```markdown
#### 进度更新 (2025-01-XX)

**完成**:
- [x] 子任务1
- [x] 子任务2

**进行中**:
- [ ] 子任务3 (80%)

**遇到问题**:
- 问题描述: XXX
- 解决方案: YYY
- 需要帮助: (是/否)

**预计完成时间**: 2025-01-XX
```

### 问题列表

当前阻塞问题（优先解决）：

| ID | 任务 | 问题描述 | 影响 | 负责人 | 状态 |
|----|------|---------|------|--------|------|
| - | - | - | - | - | - |

---

## 完成标准

### Task 1: RL引擎
- [ ] `LLMEnhancedTradingEnv`可以正常训练
- [ ] 训练脚本可以成功运行
- [ ] 模型在验证集收益 > 买入持有策略
- [ ] 单元测试覆盖率 > 80%

### Task 2: 回测系统
- [ ] 回测引擎可以运行完整回测
- [ ] 生成HTML和JSON报告
- [ ] 性能指标计算正确
- [ ] 与FinRL回测结果一致

### Task 3: Paper Trading
- [ ] 可以启动/停止模拟交易
- [ ] 实时获取市场数据
- [ ] RL决策正常执行
- [ ] API接口完整

### Task 4: 东财模拟盘
- [ ] 可以登录模拟盘
- [ ] 可以提交订单
- [ ] 可以查询持仓
- [ ] 稳定运行1周无错误

### Task 5: 东财真实盘
- [ ] 通过所有安全测试
- [ ] 风控机制正常工作
- [ ] 人工确认机制可用
- [ ] 紧急停止功能可用
- [ ] 用户明确授权 ✅

### Task 6: 性能监控
- [ ] 实时指标计算正确
- [ ] Dashboard API可用
- [ ] 异常告警功能正常
- [ ] 可视化数据完整

---

## 参考资料

### FinRL相关
- [FinRL官方文档](https://finrl.readthedocs.io/)
- [FinRL GitHub](https://github.com/AI4Finance-Foundation/FinRL)
- [FinRL-DeepSeek论文](https://arxiv.org/abs/...)

### A股交易相关
- [easytrader文档](https://github.com/shidenggui/easytrader)
- [Tushare Pro文档](https://tushare.pro/document/2)
- [A股交易规则](https://www.sse.com.cn/)

### 性能评估
- [PyFolio文档](https://github.com/quantopian/pyfolio)
- [QuantStats文档](https://github.com/ranaroussi/quantstats)

---

**文档维护**: 所有Instance共同维护
**最后更新**: 2025-01-09
**版本**: v1.0
