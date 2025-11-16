# HiddenGem 实施计划 v2.0 - 基于开源框架

## 核心理念：站在巨人的肩膀上

**不要重复造轮子！使用成熟的开源项目作为基础。**

## 技术选型对比

### 选项1: FinRL Framework ⭐️⭐️⭐️⭐️⭐️ (强烈推荐)

**优势**：
- ✅ **完整的RL交易框架**：已实现Environment、Agent、Trainer
- ✅ **原生支持PPO/DDPG/SAC**：基于Stable-Baselines3
- ✅ **多市场支持**：A股、美股、加密货币
- ✅ **风险约束**：已有CVaR-PPO实现（正是我们需要的！）
- ✅ **性能指标**：Sharpe、Sortino、MaxDD、Calmar全都有
- ✅ **活跃维护**：GitHub 9k+ stars，持续更新

**劣势**：
- ⚠️ 学习曲线：需要理解FinRL的架构
- ⚠️ 定制性：需要适配我们的TradingAgents信号

**我们需要做的**：
1. 扩展FinRL的State Space，添加TradingAgents信号作为特征
2. 自定义Reward Function，整合我们的风险偏好
3. 集成记忆系统，实现经验回放
4. 适配A股数据源（Tushare）

**工作量**：2-3周（vs 自己实现的12-17周）

---

### 选项2: Backtrader + Stable-Baselines3 ⭐️⭐️⭐️⭐️

**优势**：
- ✅ **Backtrader**：最流行的Python回测框架
- ✅ **灵活性高**：支持各种自定义策略
- ✅ **生态丰富**：大量示例和插件
- ✅ **SB3**：成熟的RL库，支持多种算法

**劣势**：
- ⚠️ 需要自己桥接Backtrader和SB3
- ⚠️ 需要自己实现Gym接口

**工作量**：3-4周

---

### 选项3: 自己实现 ⭐️⭐️

**优势**：
- ✅ 完全控制
- ✅ 定制化

**劣势**：
- ❌ 时间成本高（12-17周）
- ❌ Bug多，需要大量测试
- ❌ 重复造轮子

**工作量**：12-17周

---

## 最终选择：FinRL + TradingAgents

综合考虑，我们选择 **FinRL** 作为基础框架，原因：

1. **FinRL-DeepSeek论文**本身就是基于FinRL实现的
2. 已有CVaR-PPO实现，我们可以直接使用或微调
3. 完整的训练和评估流程，开箱即用
4. 社区活跃，遇到问题容易找到解决方案

## 修订后的实施计划

### Phase 1: 环境准备 (1周)

#### Task 1.1: 安装FinRL

```bash
# 安装FinRL
pip install git+https://github.com/AI4Finance-Foundation/FinRL.git

# 安装依赖
pip install stable-baselines3[extra]
pip install gym
pip install pyfolio
```

#### Task 1.2: 熟悉FinRL架构

**学习资源**：
- FinRL官方文档
- FinRL-DeepSeek论文实现
- 官方示例代码

**关键组件**：
```python
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
from finrl.agents.stablebaselines3.models import DRLAgent
from finrl.meta.preprocessor.yahoodownloader import YahooDownloader
from finrl.meta.preprocessor.preprocessors import FeatureEngineer
```

---

### Phase 2: 集成TradingAgents信号 (2周)

#### Task 2.1: 扩展FinRL的State Space

**文件**: `backend/tradingagents/rl/enhanced_trading_env.py`

```python
from finrl.meta.env_stock_trading.env_stocktrading import StockTradingEnv
import numpy as np

class LLMEnhancedTradingEnv(StockTradingEnv):
    """扩展FinRL环境，添加TradingAgents信号"""

    def __init__(
        self,
        df,
        trading_graph,  # 我们的TradingAgentsGraph
        memory_manager,  # 记忆系统
        **kwargs
    ):
        super().__init__(df, **kwargs)
        self.trading_graph = trading_graph
        self.memory_manager = memory_manager

    def _get_observation(self):
        """重写观察函数，添加LLM信号"""

        # 1. 获取原始FinRL的观察（价格、技术指标等）
        base_obs = super()._get_observation()

        # 2. 获取当前日期和股票代码
        current_date = self.df.iloc[self.current_step]['date']
        symbol = self.df.iloc[self.current_step]['tic']

        # 3. 调用TradingAgents获取LLM信号
        llm_signals = self._get_llm_signals(symbol, current_date)

        # 4. 从记忆系统检索相似案例
        memory_signals = self._get_memory_signals(symbol, current_date)

        # 5. 合并所有信号
        enhanced_obs = np.concatenate([
            base_obs,
            llm_signals,
            memory_signals
        ])

        return enhanced_obs

    def _get_llm_signals(self, symbol, date):
        """获取TradingAgents的LLM信号"""
        # 调用我们已有的TradingAgents系统
        final_state, processed_signal = self.trading_graph.propagate(symbol, date)

        # 提取关键信号
        llm_analysis = final_state.get('llm_analysis', {})

        signals = np.array([
            self._encode_direction(llm_analysis.get('recommended_direction', 'hold')),
            llm_analysis.get('confidence', 0.5),
            llm_analysis.get('risk_score', 0.5),
            self._calculate_agent_agreement(final_state),
        ])

        return signals

    def _get_memory_signals(self, symbol, date):
        """从记忆系统获取信号"""
        # 检索相似历史案例
        similar_episodes = self.memory_manager.retrieve_episodes(
            query_context={'symbol': symbol, 'date': date},
            top_k=5
        )

        if len(similar_episodes) == 0:
            return np.array([0, 0])

        # 统计相似案例的平均收益和成功率
        avg_return = np.mean([ep.outcome.percentage_return for ep in similar_episodes if ep.outcome])
        success_rate = np.mean([1 if ep.success else 0 for ep in similar_episodes])

        return np.array([avg_return, success_rate])

    def _encode_direction(self, direction: str) -> float:
        """编码方向：long=1, hold=0, short=-1"""
        mapping = {'long': 1.0, 'hold': 0.0, 'short': -1.0}
        return mapping.get(direction, 0.0)

    def _calculate_agent_agreement(self, final_state):
        """计算Agent一致性"""
        agent_results = final_state.get('agent_results', {})
        if len(agent_results) == 0:
            return 0.5

        directions = [r['direction'] for r in agent_results.values()]
        from collections import Counter
        counter = Counter(directions)
        most_common_count = counter.most_common(1)[0][1]

        return most_common_count / len(directions)
```

**预计时间**: 5天

#### Task 2.2: 自定义奖励函数

**文件**: `backend/tradingagents/rl/custom_reward.py`

```python
def calculate_reward_with_cvar(
    portfolio_value_change,
    actions,
    turbulence,
    cost,
    cvar_alpha=0.95,
    risk_penalty=0.1
):
    """
    自定义奖励函数（基于FinRL + CVaR约束）

    Args:
        portfolio_value_change: 投资组合价值变化
        actions: 采取的动作
        turbulence: 市场波动率
        cost: 交易成本
        cvar_alpha: CVaR阈值
        risk_penalty: 风险惩罚系数
    """

    # 1. 基础收益奖励
    profit_reward = portfolio_value_change

    # 2. CVaR风险惩罚（关注极端损失）
    cvar_penalty = 0
    if portfolio_value_change < 0:
        # 计算CVaR（最差5%情况的平均损失）
        # 这里需要维护一个滑动窗口的收益率历史
        cvar_penalty = calculate_cvar(portfolio_value_change, alpha=cvar_alpha)

    # 3. 市场波动惩罚
    turbulence_penalty = 0
    if turbulence > 1.5:  # 市场极度波动
        turbulence_penalty = (turbulence - 1.5) * abs(np.sum(actions))

    # 4. 综合奖励
    reward = (
        profit_reward
        - risk_penalty * cvar_penalty
        - turbulence_penalty
        - cost
    )

    return reward
```

**预计时间**: 3天

#### Task 2.3: 数据准备

**文件**: `backend/tradingagents/rl/data_preparation.py`

```python
from finrl.meta.preprocessor.preprocessors import FeatureEngineer, data_split
import pandas as pd

def prepare_data_for_training(
    symbol: str,
    start_date: str,
    end_date: str,
    time_interval: str = '1D'
):
    """准备训练数据"""

    # 1. 使用我们已有的数据接口获取数据
    from tradingagents.dataflows.interface import get_stock_data_by_market

    data = get_stock_data_by_market(symbol, start_date, end_date)

    # 2. 转换为FinRL格式
    df = pd.DataFrame({
        'date': data.index,
        'tic': symbol,
        'close': data['close'],
        'high': data['high'],
        'low': data['low'],
        'open': data['open'],
        'volume': data['volume'],
    })

    # 3. 添加技术指标（使用FinRL的FeatureEngineer）
    fe = FeatureEngineer(
        use_technical_indicator=True,
        tech_indicator_list=[
            'macd', 'rsi_30', 'cci_30', 'dx_30',
            'close_30_sma', 'close_60_sma'
        ],
        use_turbulence=True,
        user_defined_feature=False
    )

    df = fe.preprocess_data(df)

    # 4. 数据分割（训练/验证/测试）
    train = data_split(df, start_date, '2022-12-31')
    val = data_split(df, '2023-01-01', '2023-12-31')
    test = data_split(df, '2024-01-01', end_date)

    return train, val, test
```

**预计时间**: 2天

---

### Phase 3: 训练RL Agent (2周)

#### Task 3.1: 配置训练参数

**文件**: `backend/config/rl_config.py`

```python
RL_CONFIG = {
    # 环境配置
    'initial_amount': 100000,  # 初始资金
    'buy_cost_pct': 0.001,     # 买入手续费0.1%
    'sell_cost_pct': 0.001,    # 卖出手续费0.1%
    'hmax': 100,               # 最大持仓数量
    'discrete_actions': True,   # 使用离散动作空间

    # RL算法配置（PPO）
    'model_name': 'ppo',
    'policy': 'MlpPolicy',
    'learning_rate': 0.0003,
    'n_steps': 2048,
    'batch_size': 64,
    'n_epochs': 10,
    'gamma': 0.99,             # 折扣因子
    'ent_coef': 0.01,          # 熵系数（鼓励探索）

    # CVaR配置
    'cvar_alpha': 0.95,        # CVaR阈值
    'risk_penalty': 0.1,       # 风险惩罚系数

    # 训练配置
    'total_timesteps': 100000,
    'eval_freq': 1000,
    'save_freq': 5000,
}
```

#### Task 3.2: 训练脚本

**文件**: `backend/scripts/train_rl_with_finrl.py`

```python
from finrl.agents.stablebaselines3.models import DRLAgent
from tradingagents.rl.enhanced_trading_env import LLMEnhancedTradingEnv
from tradingagents.rl.data_preparation import prepare_data_for_training
from tradingagents.graph.trading_graph import TradingAgentsGraph
from memory import MemoryManager, MemoryMode
from config.rl_config import RL_CONFIG

def train_rl_agent(symbol: str, start_date: str, end_date: str):
    """训练RL Agent"""

    # 1. 准备数据
    print("📊 准备数据...")
    train_data, val_data, test_data = prepare_data_for_training(
        symbol, start_date, end_date
    )

    # 2. 初始化TradingAgents
    print("🤖 初始化TradingAgents...")
    trading_graph = TradingAgentsGraph()

    # 3. 初始化记忆系统（训练模式：读写）
    print("📚 初始化记忆系统...")
    memory_manager = MemoryManager(
        mode=MemoryMode.TRAINING,
        config=DEFAULT_CONFIG
    )

    # 4. 创建训练环境
    print("🏗️ 创建训练环境...")
    env_train = LLMEnhancedTradingEnv(
        df=train_data,
        trading_graph=trading_graph,
        memory_manager=memory_manager,
        **RL_CONFIG
    )

    # 5. 创建RL Agent（使用FinRL的DRLAgent）
    print("🧠 创建RL Agent...")
    agent = DRLAgent(env=env_train)

    # 6. 训练
    print("🚀 开始训练...")
    model = agent.get_model(
        model_name=RL_CONFIG['model_name'],
        model_kwargs={
            'policy': RL_CONFIG['policy'],
            'learning_rate': RL_CONFIG['learning_rate'],
            'n_steps': RL_CONFIG['n_steps'],
            'batch_size': RL_CONFIG['batch_size'],
            'n_epochs': RL_CONFIG['n_epochs'],
            'gamma': RL_CONFIG['gamma'],
            'ent_coef': RL_CONFIG['ent_coef'],
        }
    )

    trained_model = agent.train_model(
        model=model,
        tb_log_name='ppo_trading',
        total_timesteps=RL_CONFIG['total_timesteps']
    )

    # 7. 保存模型
    print("💾 保存模型...")
    trained_model.save(f"models/rl_agent_{symbol}")

    # 8. 验证集评估
    print("📈 验证集评估...")
    env_val = LLMEnhancedTradingEnv(
        df=val_data,
        trading_graph=trading_graph,
        memory_manager=memory_manager,
        **RL_CONFIG
    )

    val_results = DRLAgent.DRL_prediction(
        model=trained_model,
        environment=env_val
    )

    print(f"✅ 训练完成！验证集收益: {val_results['total_return']:.2%}")

    return trained_model

if __name__ == "__main__":
    train_rl_agent(
        symbol='600519.SH',
        start_date='2018-01-01',
        end_date='2024-12-31'
    )
```

**预计时间**: 5天

#### Task 3.3: 评估和回测

**文件**: `backend/scripts/evaluate_rl_agent.py`

```python
from finrl.plot import backtest_stats, backtest_plot, get_baseline
import pyfolio

def evaluate_rl_agent(model, test_data, symbol):
    """评估RL Agent性能"""

    # 1. 在测试集上运行
    print("📊 测试集评估...")
    env_test = LLMEnhancedTradingEnv(df=test_data, **RL_CONFIG)
    df_account_value, df_actions = DRLAgent.DRL_prediction(
        model=model,
        environment=env_test
    )

    # 2. 计算性能指标
    print("📈 计算性能指标...")
    perf_stats = backtest_stats(
        account_value=df_account_value,
        value_col_name='account_value'
    )

    # 3. 与基准对比（买入持有策略）
    print("📊 基准对比...")
    baseline_df = get_baseline(
        ticker=symbol,
        start=test_data['date'].min(),
        end=test_data['date'].max()
    )

    # 4. 绘制结果
    print("📉 绘制回测曲线...")
    backtest_plot(
        df_account_value,
        baseline_df=baseline_df,
        baseline_ticker=symbol
    )

    # 5. PyFolio详细分析
    print("📊 PyFolio分析...")
    returns = df_account_value['daily_return']
    pyfolio.create_full_tear_sheet(returns)

    return perf_stats
```

**预计时间**: 3天

---

### Phase 4: 部署和监控 (1周)

#### Task 4.1: 模拟交易API

**文件**: `backend/api/rl_trading_router.py`

```python
from fastapi import APIRouter
from stable_baselines3 import PPO

router = APIRouter(prefix="/api/v1/rl", tags=["RL Trading"])

# 加载训练好的模型
rl_model = PPO.load("models/rl_agent_600519.SH")

@router.post("/predict/{symbol}")
async def predict_action(symbol: str):
    """预测下一步动作"""

    # 1. 获取当前状态
    current_state = get_current_state(symbol)

    # 2. RL模型预测
    action, _states = rl_model.predict(current_state, deterministic=True)

    # 3. 解码动作
    decoded_action = decode_action(action)

    return {
        "success": True,
        "data": {
            "symbol": symbol,
            "action": decoded_action['type'],  # BUY/SELL/HOLD
            "size": decoded_action['size'],     # 仓位大小
            "confidence": _states['value_estimate']
        }
    }
```

**预计时间**: 3天

---

## 修订后的时间估算

- **Phase 1 (环境准备)**: 1周
- **Phase 2 (集成TradingAgents)**: 2周
- **Phase 3 (训练RL Agent)**: 2周
- **Phase 4 (部署监控)**: 1周

**总计**: 6周（vs 原计划的12-17周，节省50%+时间）

## 关键优势总结

✅ **使用FinRL后的优势**：
1. 节省10周开发时间
2. 代码质量更高（久经考验）
3. 性能评估更专业（PyFolio集成）
4. 社区支持（遇到问题容易解决）
5. 已有CVaR-PPO实现（正是我们需要的）

✅ **我们的创新点**：
1. TradingAgents的多Agent LLM信号（FinRL原版没有）
2. 双层记忆系统集成（独创）
3. 时间旅行训练与RL训练结合（创新）

## 下一步行动

1. **立即开始**: Phase 1 - 安装FinRL并熟悉架构
2. **阅读资料**:
   - FinRL官方文档
   - FinRL-DeepSeek论文的代码实现
3. **验证可行性**: 运行FinRL官方示例

---

**文档版本**: v2.0
**最后更新**: 2025-01-09
**核心变化**: 从自己实现转向使用FinRL框架，节省50%+开发时间
