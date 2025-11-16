# HiddenGem 完整系统实施计划

## 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        HiddenGem 交易系统                          │
└─────────────────────────────────────────────────────────────────┘

输入层 (Data Layer)
├── 市场数据（价格、成交量、技术指标）
├── 基本面数据（财报、估值）
├── 情绪数据（新闻、社交媒体）
└── 宏观数据（政策、经济指标）
         │
         ▼
═══════════════════════════════════════════════════════════════
感知层 (Perception Layer) - ✅ 已完成
═══════════════════════════════════════════════════════════════
         │
TradingAgents Framework (多Agent系统)
├── Market Analyst         → 技术分析信号
├── Fundamentals Analyst   → 基本面信号
├── Sentiment Analyst      → 情绪信号
├── News Analyst          → 新闻信号
├── Bull Researcher       → 看涨观点
├── Bear Researcher       → 看跌观点
└── Risk Manager          → 风险评估
         │
         ├─→ Investment Debate (Bull vs Bear)
         └─→ Risk Debate (Aggressive/Neutral/Conservative)
         │
         ▼
    【LLM综合信号】
    - direction: long/short/hold
    - confidence: 0.0-1.0
    - risk_score: 0.0-1.0
    - key_factors: [...]
    - price_targets: {...}
         │
         ▼
═══════════════════════════════════════════════════════════════
决策层 (Decision Layer) - 🔨 待实现
═══════════════════════════════════════════════════════════════
         │
RL Decision Engine (CVaR-PPO)
├── 输入：
│   ├── TradingAgents信号（LLM signals）
│   ├── 当前持仓状态
│   ├── 市场环境特征
│   └── 历史记忆检索结果
├── 输出：
│   ├── Action: BUY/SELL/HOLD
│   ├── Position Size: 0.0-1.0
│   └── Confidence: 0.0-1.0
└── 约束：
    ├── CVaR风险控制
    ├── 最大仓位限制
    └── 最大回撤限制
         │
         ▼
═══════════════════════════════════════════════════════════════
执行层 (Execution Layer) - 🔨 待实现
═══════════════════════════════════════════════════════════════
         │
Portfolio & Order Management
├── Portfolio Manager
│   ├── 资金管理
│   ├── 持仓管理
│   ├── 风险计算
│   └── 绩效追踪
├── Order Manager
│   ├── 订单生成
│   ├── 订单验证
│   ├── 订单执行
│   └── 订单追踪
└── Risk Controller
    ├── 仓位限制检查
    ├── 止损/止盈执行
    └── 风险指标监控
         │
         ▼
═══════════════════════════════════════════════════════════════
交易接口层 (Trading Interface) - 🔨 待实现
═══════════════════════════════════════════════════════════════
         │
         ├─→ 模拟交易 (Paper Trading)
         │   ├── 模拟市价单
         │   ├── 模拟限价单
         │   └── 实时P&L计算
         │
         └─→ 真实交易 (Live Trading) - 可选
             ├── Eastmoney API
             ├── 券商接口
             └── 风控验证
         │
         ▼
═══════════════════════════════════════════════════════════════
反馈层 (Feedback Layer) - 🔨 待实现
═══════════════════════════════════════════════════════════════
         │
Performance & Learning
├── Performance Tracker
│   ├── 收益率计算
│   ├── 夏普比率
│   ├── 最大回撤
│   └── 胜率统计
├── Reward Calculator (for RL)
│   ├── 收益奖励
│   ├── 风险惩罚
│   ├── CVaR惩罚
│   └── 综合奖励
└── Experience Replay
    ├── 存储Episode
    └── 更新记忆库
         │
         ▼
═══════════════════════════════════════════════════════════════
记忆层 (Memory Layer) - ✅ 已完成
═══════════════════════════════════════════════════════════════

Memory System
├── Maxim Memory (粗粒度)
│   ├── Bull/Bear/Trader/Judge/RiskManager
│   └── 快速检索相似经验
└── Episode Memory (细粒度)
    ├── 完整交易案例
    └── 深度学习素材
```

## 核心设计理念

### 1. LLM作为信号提供者（Signal Provider），而非决策者

借鉴FinRL-DeepSeek论文的核心观点：

```python
# ❌ 错误：LLM直接决策
action = llm.decide(market_data)  # 没有学习循环

# ✅ 正确：LLM提供信号，RL学习如何使用
llm_signals = trading_agents.analyze(market_data)
action = rl_agent.decide(state, llm_signals)  # RL学习最优权重
reward = environment.step(action)
rl_agent.learn(state, action, reward)  # 持续优化
```

**为什么这样设计？**
- LLM擅长理解复杂语义和因果关系
- RL擅长在不确定环境中学习最优策略
- LLM信号提供"方向指引"，RL学习"如何执行"
- RL通过实际交易结果不断优化对LLM信号的使用

### 2. CVaR风险约束

传统RL最大化期望收益，但可能承担极端风险。CVaR-PPO引入风险约束：

```
目标函数 = 最大化(期望收益) - λ * CVaR(α)

其中：
- CVaR(α) = 最差(1-α)%情况下的平均损失
- α = 0.95 表示关注最差5%的情况
- λ = 风险厌恶系数
```

### 3. 两阶段训练策略

```
Phase 1: 离线训练 (Offline Training)
├── 使用时间旅行训练收集经验
├── 在历史数据上训练RL模型
├── 无实际资金风险
└── 快速迭代优化

Phase 2: 在线优化 (Online Tuning)
├── 部署到模拟交易
├── 实时收集新经验
├── 持续学习适应市场变化
└── 渐进式上线真实交易
```

## 任务分解

### Phase 1: RL决策引擎 (4-6周)

#### Task 1.1: 设计状态空间 (State Space)

**文件**: `backend/tradingagents/rl/state_space.py`

```python
class StateSpace:
    """RL Agent的状态空间定义"""

    def __init__(self):
        self.features = {
            # 1. TradingAgents信号 (核心)
            'llm_direction': 'categorical[long, short, hold]',
            'llm_confidence': 'continuous[0, 1]',
            'llm_risk_score': 'continuous[0, 1]',
            'llm_agent_agreement': 'continuous[0, 1]',  # Agent一致性

            # 2. 市场特征
            'price': 'continuous',
            'volume': 'continuous',
            'volatility': 'continuous[0, 1]',
            'trend': 'continuous[-1, 1]',  # -1=下跌, 1=上涨

            # 3. 持仓状态
            'position': 'continuous[-1, 1]',  # -1=满仓空, 1=满仓多
            'unrealized_pnl': 'continuous',
            'holding_days': 'discrete',

            # 4. 风险指标
            'portfolio_volatility': 'continuous[0, 1]',
            'max_drawdown': 'continuous[0, 1]',
            'sharpe_ratio': 'continuous',

            # 5. 记忆检索结果
            'similar_cases_avg_return': 'continuous',
            'similar_cases_success_rate': 'continuous[0, 1]',
        }

    def encode(self, raw_data: dict) -> np.ndarray:
        """将原始数据编码为状态向量"""
        ...
```

**预计时间**: 3天

#### Task 1.2: 设计动作空间 (Action Space)

**文件**: `backend/tradingagents/rl/action_space.py`

```python
class ActionSpace:
    """RL Agent的动作空间定义"""

    def __init__(self, action_type='discrete'):
        if action_type == 'discrete':
            # 离散动作：简单但粗糙
            self.actions = {
                0: ('HOLD', 0.0),
                1: ('BUY', 0.1),   # 买入10%
                2: ('BUY', 0.2),   # 买入20%
                3: ('SELL', 0.1),  # 卖出10%
                4: ('SELL', 0.2),  # 卖出20%
                5: ('CLOSE', 1.0), # 全部平仓
            }
        elif action_type == 'continuous':
            # 连续动作：精细但难训练
            # action[0]: 方向 (-1=卖, 0=持有, 1=买)
            # action[1]: 仓位 (0.0-1.0)
            ...

    def decode(self, action_id: int) -> tuple:
        """解码动作ID为(动作类型, 仓位大小)"""
        ...
```

**预计时间**: 2天

#### Task 1.3: 设计奖励函数 (Reward Function)

**文件**: `backend/tradingagents/rl/reward_function.py`

```python
class RewardFunction:
    """奖励函数设计"""

    def __init__(self, config):
        self.alpha = config.get('cvar_alpha', 0.95)
        self.risk_penalty_coef = config.get('risk_penalty', 0.1)

    def calculate_reward(self, state, action, next_state):
        """计算奖励值"""

        # 1. 收益奖励
        pnl = next_state['unrealized_pnl'] - state['unrealized_pnl']
        profit_reward = pnl / state['portfolio_value']

        # 2. 风险惩罚
        risk_penalty = 0

        # 2.1 CVaR惩罚（关注极端损失）
        if pnl < 0:
            cvar_penalty = self._calculate_cvar_penalty(state, action)
            risk_penalty += cvar_penalty

        # 2.2 最大回撤惩罚
        if next_state['max_drawdown'] > 0.1:  # 超过10%
            risk_penalty += (next_state['max_drawdown'] - 0.1) * 10

        # 2.3 波动率惩罚
        if next_state['portfolio_volatility'] > 0.3:
            risk_penalty += (next_state['portfolio_volatility'] - 0.3) * 5

        # 3. 交易成本
        transaction_cost = self._calculate_cost(action)

        # 4. 综合奖励
        reward = profit_reward - self.risk_penalty_coef * risk_penalty - transaction_cost

        return reward

    def _calculate_cvar_penalty(self, state, action):
        """计算CVaR惩罚项"""
        # CVaR = 最差(1-alpha)%情况的平均损失
        ...
```

**预计时间**: 4天

#### Task 1.4: 实现CVaR-PPO算法

**文件**: `backend/tradingagents/rl/cvar_ppo.py`

```python
class CVaRPPOAgent:
    """CVaR约束的PPO算法"""

    def __init__(self, state_dim, action_dim, config):
        self.alpha = config.get('cvar_alpha', 0.95)
        self.lambda_risk = config.get('lambda_risk', 0.1)

        # PPO核心组件
        self.actor = ActorNetwork(state_dim, action_dim)
        self.critic = CriticNetwork(state_dim)
        self.cvar_critic = CVaRCriticNetwork(state_dim)  # CVaR评估网络

    def select_action(self, state, llm_signals):
        """选择动作（结合LLM信号）"""
        # 将LLM信号作为state的一部分
        enhanced_state = np.concatenate([state, llm_signals])

        # Actor网络输出动作概率分布
        action_probs = self.actor(enhanced_state)

        # 采样动作
        action = np.random.choice(len(action_probs), p=action_probs)

        return action, action_probs[action]

    def update(self, trajectories):
        """更新网络（PPO + CVaR约束）"""

        # 1. 计算Advantage（传统PPO）
        advantages = self._compute_advantages(trajectories)

        # 2. 计算CVaR Advantage（风险约束）
        cvar_advantages = self._compute_cvar_advantages(trajectories)

        # 3. 综合Advantage
        combined_advantages = advantages - self.lambda_risk * cvar_advantages

        # 4. PPO更新（Clip + Trust Region）
        policy_loss = self._ppo_loss(trajectories, combined_advantages)
        value_loss = self._value_loss(trajectories)

        # 5. 反向传播
        total_loss = policy_loss + 0.5 * value_loss
        total_loss.backward()
        self.optimizer.step()

    def _compute_cvar_advantages(self, trajectories):
        """计算CVaR优势函数"""
        # 识别最差(1-alpha)%的轨迹
        # 对这些轨迹施加更高的惩罚
        ...
```

**预计时间**: 10天

#### Task 1.5: 集成TradingAgents信号

**文件**: `backend/tradingagents/rl/signal_integration.py`

```python
class SignalIntegrator:
    """整合TradingAgents信号到RL状态空间"""

    def extract_llm_signals(self, analysis_result: dict) -> dict:
        """从TradingAgents分析结果中提取信号"""

        llm_analysis = analysis_result.get('llm_analysis', {})
        agent_results = analysis_result.get('agent_results', {})

        signals = {
            # 主信号
            'direction': self._encode_direction(llm_analysis['recommended_direction']),
            'confidence': llm_analysis['confidence'],
            'risk_score': llm_analysis.get('risk_score', 0.5),

            # Agent一致性
            'agent_agreement': self._calculate_agreement(agent_results),

            # 价格目标
            'target_price': llm_analysis.get('price_targets', {}).get('entry', 0),
            'stop_loss': llm_analysis.get('price_targets', {}).get('stop_loss', 0),
            'take_profit': llm_analysis.get('price_targets', {}).get('take_profit', 0),

            # 关键因素数量（作为信心的补充指标）
            'num_key_factors': len(llm_analysis.get('key_factors', [])),
        }

        return signals

    def _calculate_agreement(self, agent_results: dict) -> float:
        """计算Agent之间的一致性"""
        directions = [r['direction'] for r in agent_results.values()]

        # 统计最多的方向
        from collections import Counter
        counter = Counter(directions)
        most_common_count = counter.most_common(1)[0][1]

        # 一致性 = 最多方向的数量 / 总数量
        agreement = most_common_count / len(directions)

        return agreement
```

**预计时间**: 3天

---

### Phase 2: 模拟交易系统 (3-4周)

#### Task 2.1: Portfolio Manager (投资组合管理)

**文件**: `backend/trading/portfolio_manager.py`

```python
class PortfolioManager:
    """投资组合管理器"""

    def __init__(self, initial_cash=100000.0):
        self.cash = initial_cash
        self.positions = {}  # {symbol: Position}
        self.order_history = []
        self.trade_history = []

    def get_portfolio_value(self, current_prices: dict) -> float:
        """计算投资组合总价值"""
        # 现金 + 所有持仓市值
        total_value = self.cash

        for symbol, position in self.positions.items():
            if symbol in current_prices:
                total_value += position.quantity * current_prices[symbol]

        return total_value

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)

    def get_available_cash(self) -> float:
        """获取可用现金"""
        return self.cash

    def calculate_metrics(self, current_prices: dict) -> dict:
        """计算投资组合指标"""
        total_value = self.get_portfolio_value(current_prices)

        metrics = {
            'total_value': total_value,
            'cash': self.cash,
            'positions_value': total_value - self.cash,
            'num_positions': len(self.positions),
            'leverage': (total_value - self.cash) / self.cash if self.cash > 0 else 0,
        }

        return metrics
```

**预计时间**: 4天

#### Task 2.2: Order Manager (订单管理)

**文件**: `backend/trading/order_manager.py`

```python
class OrderManager:
    """订单管理器"""

    def create_order(
        self,
        symbol: str,
        action: str,  # BUY/SELL
        quantity: float,
        order_type: str = 'MARKET',  # MARKET/LIMIT
        price: Optional[float] = None
    ) -> Order:
        """创建订单"""

        order = Order(
            order_id=self._generate_order_id(),
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type=order_type,
            price=price,
            status='PENDING',
            created_at=datetime.now()
        )

        # 验证订单
        if not self._validate_order(order):
            order.status = 'REJECTED'
            order.reject_reason = "Validation failed"

        return order

    def execute_order(
        self,
        order: Order,
        market_price: float,
        portfolio: PortfolioManager
    ) -> ExecutionResult:
        """执行订单"""

        if order.status != 'PENDING':
            return ExecutionResult(success=False, message="Order not pending")

        # 市价单
        if order.order_type == 'MARKET':
            execution_price = market_price
        # 限价单
        elif order.order_type == 'LIMIT':
            if order.action == 'BUY' and market_price <= order.price:
                execution_price = order.price
            elif order.action == 'SELL' and market_price >= order.price:
                execution_price = order.price
            else:
                return ExecutionResult(success=False, message="Price not matched")

        # 计算交易成本
        commission = self._calculate_commission(order.quantity, execution_price)
        slippage = self._calculate_slippage(market_price)
        total_cost = commission + slippage

        # 执行交易
        if order.action == 'BUY':
            total_amount = order.quantity * execution_price + total_cost
            if portfolio.cash < total_amount:
                return ExecutionResult(success=False, message="Insufficient cash")

            portfolio.cash -= total_amount
            portfolio.add_position(order.symbol, order.quantity, execution_price)

        elif order.action == 'SELL':
            position = portfolio.get_position(order.symbol)
            if not position or position.quantity < order.quantity:
                return ExecutionResult(success=False, message="Insufficient position")

            total_amount = order.quantity * execution_price - total_cost
            portfolio.cash += total_amount
            portfolio.reduce_position(order.symbol, order.quantity, execution_price)

        # 更新订单状态
        order.status = 'FILLED'
        order.filled_price = execution_price
        order.filled_at = datetime.now()
        order.commission = commission

        return ExecutionResult(success=True, order=order)
```

**预计时间**: 5天

#### Task 2.3: Position Tracker (持仓跟踪)

**文件**: `backend/trading/position_tracker.py`

```python
class Position:
    """持仓信息"""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.quantity = 0.0
        self.avg_price = 0.0
        self.cost_basis = 0.0
        self.realized_pnl = 0.0
        self.trades = []

    def add_shares(self, quantity: float, price: float):
        """增加持仓"""
        total_cost = self.cost_basis + quantity * price
        total_quantity = self.quantity + quantity

        self.avg_price = total_cost / total_quantity if total_quantity > 0 else 0
        self.quantity = total_quantity
        self.cost_basis = total_cost

        self.trades.append({
            'action': 'BUY',
            'quantity': quantity,
            'price': price,
            'timestamp': datetime.now()
        })

    def reduce_shares(self, quantity: float, price: float):
        """减少持仓"""
        if quantity > self.quantity:
            raise ValueError("Cannot reduce more than current quantity")

        # 计算已实现盈亏
        realized_pnl = (price - self.avg_price) * quantity
        self.realized_pnl += realized_pnl

        # 更新持仓
        self.quantity -= quantity
        self.cost_basis -= quantity * self.avg_price

        self.trades.append({
            'action': 'SELL',
            'quantity': quantity,
            'price': price,
            'pnl': realized_pnl,
            'timestamp': datetime.now()
        })

    def get_unrealized_pnl(self, current_price: float) -> float:
        """计算未实现盈亏"""
        if self.quantity == 0:
            return 0.0

        return (current_price - self.avg_price) * self.quantity

    def get_total_pnl(self, current_price: float) -> float:
        """计算总盈亏"""
        return self.realized_pnl + self.get_unrealized_pnl(current_price)
```

**预计时间**: 3天

#### Task 2.4: Performance Tracker (绩效追踪)

**文件**: `backend/trading/performance_tracker.py`

```python
class PerformanceTracker:
    """绩效追踪器"""

    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.equity_curve = []  # [(timestamp, equity)]
        self.returns = []
        self.drawdowns = []

    def update(self, timestamp: datetime, portfolio_value: float):
        """更新绩效数据"""
        self.equity_curve.append((timestamp, portfolio_value))

        # 计算收益率
        if len(self.equity_curve) > 1:
            prev_value = self.equity_curve[-2][1]
            ret = (portfolio_value - prev_value) / prev_value
            self.returns.append(ret)

        # 计算回撤
        peak = max([eq[1] for eq in self.equity_curve])
        drawdown = (portfolio_value - peak) / peak if peak > 0 else 0
        self.drawdowns.append(drawdown)

    def get_metrics(self) -> dict:
        """获取绩效指标"""
        if len(self.equity_curve) == 0:
            return {}

        current_value = self.equity_curve[-1][1]
        total_return = (current_value - self.initial_capital) / self.initial_capital

        # 年化收益率
        days = (self.equity_curve[-1][0] - self.equity_curve[0][0]).days
        years = days / 365.25 if days > 0 else 1
        annualized_return = (1 + total_return) ** (1 / years) - 1

        # 夏普比率
        if len(self.returns) > 0:
            avg_return = np.mean(self.returns)
            std_return = np.std(self.returns)
            sharpe_ratio = avg_return / std_return * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0

        # 最大回撤
        max_drawdown = min(self.drawdowns) if len(self.drawdowns) > 0 else 0

        # 胜率
        winning_trades = sum(1 for r in self.returns if r > 0)
        win_rate = winning_trades / len(self.returns) if len(self.returns) > 0 else 0

        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'num_trades': len(self.returns),
            'current_value': current_value,
        }
```

**预计时间**: 4天

#### Task 2.5: Risk Manager (风险控制)

**文件**: `backend/trading/risk_manager.py`

```python
class RiskManager:
    """风险管理器"""

    def __init__(self, config: dict):
        # 仓位限制
        self.max_position_size = config.get('max_position_size', 0.2)  # 单只股票最大20%
        self.max_portfolio_leverage = config.get('max_leverage', 1.0)  # 最大杠杆1倍

        # 止损/止盈
        self.stop_loss_pct = config.get('stop_loss', 0.08)  # 止损8%
        self.take_profit_pct = config.get('take_profit', 0.15)  # 止盈15%

        # 风险限制
        self.max_drawdown_limit = config.get('max_drawdown', 0.15)  # 最大回撤15%
        self.daily_loss_limit = config.get('daily_loss_limit', 0.05)  # 日亏损5%

    def validate_order(
        self,
        order: Order,
        portfolio: PortfolioManager,
        current_prices: dict
    ) -> tuple[bool, str]:
        """验证订单是否符合风控要求"""

        # 1. 检查仓位限制
        if order.action == 'BUY':
            portfolio_value = portfolio.get_portfolio_value(current_prices)
            order_value = order.quantity * current_prices[order.symbol]
            position_ratio = order_value / portfolio_value

            if position_ratio > self.max_position_size:
                return False, f"Position size {position_ratio:.1%} exceeds limit {self.max_position_size:.1%}"

        # 2. 检查杠杆限制
        # ...

        # 3. 检查资金充足性
        if order.action == 'BUY':
            required_cash = order.quantity * current_prices[order.symbol] * 1.001  # 含手续费
            if portfolio.cash < required_cash:
                return False, "Insufficient cash"

        return True, "OK"

    def check_stop_conditions(
        self,
        position: Position,
        current_price: float
    ) -> Optional[str]:
        """检查止损/止盈条件"""

        if position.quantity == 0:
            return None

        pnl_pct = (current_price - position.avg_price) / position.avg_price

        # 触发止损
        if pnl_pct <= -self.stop_loss_pct:
            return 'STOP_LOSS'

        # 触发止盈
        if pnl_pct >= self.take_profit_pct:
            return 'TAKE_PROFIT'

        return None

    def check_portfolio_risk(
        self,
        portfolio: PortfolioManager,
        performance: PerformanceTracker
    ) -> Optional[str]:
        """检查整体投资组合风险"""

        metrics = performance.get_metrics()

        # 超过最大回撤限制
        if metrics.get('max_drawdown', 0) < -self.max_drawdown_limit:
            return 'MAX_DRAWDOWN_EXCEEDED'

        # 日亏损超限
        if len(performance.returns) > 0:
            today_return = performance.returns[-1]
            if today_return < -self.daily_loss_limit:
                return 'DAILY_LOSS_LIMIT_EXCEEDED'

        return None
```

**预计时间**: 4天

---

### Phase 3: RL训练流程 (3-4周)

#### Task 3.1: 回测环境 (Backtesting Environment)

**文件**: `backend/tradingagents/rl/backtest_env.py`

```python
import gym
from gym import spaces

class TradingEnv(gym.Env):
    """交易环境（符合OpenAI Gym接口）"""

    def __init__(self, data, config):
        super().__init__()

        self.data = data  # 历史数据
        self.config = config

        # 初始化组件
        self.portfolio = PortfolioManager(initial_cash=config['initial_cash'])
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager(config)
        self.performance = PerformanceTracker(config['initial_cash'])

        # 定义状态和动作空间
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(state_dim,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(6)  # 0-5对应不同动作

        # 当前位置
        self.current_step = 0

    def reset(self):
        """重置环境"""
        self.current_step = 0
        self.portfolio = PortfolioManager(initial_cash=self.config['initial_cash'])
        self.performance = PerformanceTracker(self.config['initial_cash'])

        return self._get_observation()

    def step(self, action):
        """执行一步"""
        # 1. 获取当前市场数据
        current_data = self.data.iloc[self.current_step]
        symbol = current_data['symbol']
        current_price = current_data['close']

        # 2. 获取TradingAgents信号
        llm_signals = self._get_llm_signals(symbol, current_data['date'])

        # 3. 解码动作
        action_type, position_size = self.action_space.decode(action)

        # 4. 创建订单
        if action_type == 'BUY':
            quantity = (self.portfolio.cash * position_size) / current_price
            order = self.order_manager.create_order(symbol, 'BUY', quantity)
        elif action_type == 'SELL':
            position = self.portfolio.get_position(symbol)
            if position:
                quantity = position.quantity * position_size
                order = self.order_manager.create_order(symbol, 'SELL', quantity)
            else:
                order = None
        else:  # HOLD
            order = None

        # 5. 风控检查
        if order:
            valid, reason = self.risk_manager.validate_order(
                order, self.portfolio, {symbol: current_price}
            )
            if not valid:
                logger.warning(f"Order rejected: {reason}")
                order = None

        # 6. 执行订单
        if order:
            result = self.order_manager.execute_order(
                order, current_price, self.portfolio
            )

        # 7. 更新绩效
        portfolio_value = self.portfolio.get_portfolio_value({symbol: current_price})
        self.performance.update(current_data['date'], portfolio_value)

        # 8. 计算奖励
        reward = self._calculate_reward()

        # 9. 前进到下一步
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1

        # 10. 获取新状态
        next_state = self._get_observation()

        return next_state, reward, done, {}

    def _get_observation(self):
        """获取当前观察（状态）"""
        current_data = self.data.iloc[self.current_step]
        symbol = current_data['symbol']

        # 构建状态向量
        state = {
            # 市场特征
            'price': current_data['close'],
            'volume': current_data['volume'],
            'volatility': self._calculate_volatility(),

            # 持仓状态
            'position': self._get_position_ratio(symbol),
            'unrealized_pnl': self._get_unrealized_pnl(symbol, current_data['close']),

            # 绩效指标
            'portfolio_value': self.portfolio.get_portfolio_value({symbol: current_data['close']}),
            'max_drawdown': self.performance.get_metrics().get('max_drawdown', 0),
        }

        return self.state_space.encode(state)

    def _get_llm_signals(self, symbol, date):
        """获取TradingAgents信号"""
        # 调用TradingAgents进行分析
        analysis = self.trading_graph.propagate(symbol, date)
        signals = self.signal_integrator.extract_llm_signals(analysis)
        return signals
```

**预计时间**: 7天

#### Task 3.2: RL训练循环

**文件**: `backend/scripts/train_rl_agent.py`

```python
def train_rl_agent(
    symbol: str,
    start_date: str,
    end_date: str,
    config: dict
):
    """训练RL Agent"""

    # 1. 准备数据
    data = get_stock_data_by_market(symbol, start_date, end_date)

    # 2. 创建环境
    env = TradingEnv(data, config)

    # 3. 创建RL Agent
    agent = CVaRPPOAgent(
        state_dim=env.observation_space.shape[0],
        action_dim=env.action_space.n,
        config=config
    )

    # 4. 训练循环
    num_episodes = config.get('num_episodes', 1000)

    for episode in range(num_episodes):
        state = env.reset()
        episode_reward = 0
        trajectories = []

        done = False
        while not done:
            # 选择动作
            action, action_prob = agent.select_action(state, env.llm_signals)

            # 执行动作
            next_state, reward, done, info = env.step(action)

            # 存储轨迹
            trajectories.append({
                'state': state,
                'action': action,
                'reward': reward,
                'next_state': next_state,
                'done': done,
                'action_prob': action_prob,
            })

            episode_reward += reward
            state = next_state

        # 更新Agent
        agent.update(trajectories)

        # 记录
        if episode % 10 == 0:
            metrics = env.performance.get_metrics()
            logger.info(f"Episode {episode}: Reward={episode_reward:.2f}, "
                       f"Return={metrics['total_return']:.2%}, "
                       f"Sharpe={metrics['sharpe_ratio']:.2f}")

        # 保存模型
        if episode % 100 == 0:
            agent.save(f"models/cvar_ppo_episode_{episode}.pth")

    return agent
```

**预计时间**: 5天

#### Task 3.3: 策略评估

**文件**: `backend/scripts/evaluate_rl_agent.py`

```python
def evaluate_rl_agent(
    agent: CVaRPPOAgent,
    test_data,
    config: dict
):
    """评估RL Agent性能"""

    # 创建测试环境
    env = TradingEnv(test_data, config)

    # 运行测试
    state = env.reset()
    done = False

    while not done:
        action, _ = agent.select_action(state, env.llm_signals)
        state, reward, done, info = env.step(action)

    # 获取绩效指标
    metrics = env.performance.get_metrics()

    # 详细报告
    report = {
        'total_return': metrics['total_return'],
        'annualized_return': metrics['annualized_return'],
        'sharpe_ratio': metrics['sharpe_ratio'],
        'max_drawdown': metrics['max_drawdown'],
        'win_rate': metrics['win_rate'],
        'num_trades': metrics['num_trades'],

        # 与买入持有策略对比
        'buy_and_hold_return': ...,
        'alpha': ...,  # 超额收益

        # 风险指标
        'volatility': ...,
        'sortino_ratio': ...,
        'calmar_ratio': ...,
    }

    return report
```

**预计时间**: 3天

---

### Phase 4: 生产部署 (2-3周)

#### Task 4.1: 实时交易接口

**文件**: `backend/trading/live_trading.py`

```python
class LiveTradingEngine:
    """实时交易引擎"""

    def __init__(self, agent, config):
        self.agent = agent
        self.config = config

        # 初始化组件
        self.portfolio = PortfolioManager(config['initial_cash'])
        self.order_manager = OrderManager()
        self.risk_manager = RiskManager(config)
        self.performance = PerformanceTracker(config['initial_cash'])

        # 交易接口（先用模拟）
        self.broker = PaperTradingBroker()

    def run(self, symbols: List[str]):
        """运行实时交易"""

        while True:
            for symbol in symbols:
                # 1. 获取实时数据
                current_data = self._get_realtime_data(symbol)

                # 2. 获取LLM信号
                llm_signals = self._get_llm_signals(symbol)

                # 3. 构建状态
                state = self._build_state(symbol, current_data)

                # 4. RL决策
                action, _ = self.agent.select_action(state, llm_signals)

                # 5. 生成订单
                order = self._create_order_from_action(symbol, action)

                # 6. 风控检查
                if order:
                    valid, reason = self.risk_manager.validate_order(order, self.portfolio, {symbol: current_data['price']})
                    if not valid:
                        logger.warning(f"Order rejected: {reason}")
                        continue

                # 7. 提交订单到broker
                if order:
                    self.broker.submit_order(order)

            # 8. 等待下一个周期
            time.sleep(60)  # 1分钟
```

**预计时间**: 5天

#### Task 4.2: Eastmoney集成（可选）

**文件**: `backend/trading/eastmoney_broker.py`

```python
class EastmoneyBroker:
    """东方财富券商接口"""

    def __init__(self, account_config):
        # 使用easytrader库
        from easytrader import use
        self.trader = use('eastmoney')
        self.trader.prepare(account_config)

    def submit_order(self, order: Order):
        """提交订单"""
        # 转换为easytrader格式
        ...

    def get_positions(self):
        """获取持仓"""
        ...

    def get_balance(self):
        """获取资金"""
        ...
```

**预计时间**: 3天（如果需要）

---

## 总时间估算

- **Phase 1 (RL引擎)**: 4-6周
- **Phase 2 (模拟交易)**: 3-4周
- **Phase 3 (训练流程)**: 3-4周
- **Phase 4 (生产部署)**: 2-3周

**总计**: 12-17周（约3-4个月）

## 技术栈总览

```
Backend:
├── Python 3.11+
├── PyTorch (RL训练)
├── Stable-Baselines3 (PPO基线)
├── OpenAI Gym (环境接口)
├── NumPy & Pandas (数据处理)
├── ChromaDB (记忆存储)
├── FastAPI (API服务)
└── easytrader (券商接口，可选)

Frontend:
├── React + TypeScript
├── TanStack Query (数据获取)
├── Recharts (图表)
└── Tailwind CSS (样式)

Infrastructure:
├── Redis (缓存)
├── MongoDB (持久化)
└── Docker (容器化)
```

## 风险提示

1. **训练时间长**：RL训练可能需要数千个episode，每个episode可能需要几分钟
2. **超参数调优**：PPO有很多超参数需要调优
3. **过拟合风险**：在历史数据上表现好，不代表未来也好
4. **实盘风险**：建议充分模拟交易验证后再上线
5. **市场风险**：任何策略都无法保证盈利

## 建议的开发顺序

1. ✅ **先完成Phase 2（模拟交易）**
   - 这是基础设施，RL训练需要它
   - 可以先用简单规则测试系统
   - 验证数据流和订单流程

2. **再做Phase 1（RL引擎）**
   - 在模拟环境中训练和测试
   - 快速迭代算法

3. **然后Phase 3（训练流程）**
   - 大规模训练
   - 收集训练数据

4. **最后Phase 4（生产部署）**
   - 充分验证后上线
   - 小资金试运行

---

**文档版本**: v1.0
**最后更新**: 2025-01-09
**下一步**: 开始实现Phase 2 - 模拟交易系统
