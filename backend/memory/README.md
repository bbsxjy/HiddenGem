# HiddenGem 统一记忆系统

统一记忆系统，整合粗粒度记忆（格言库）和细粒度记忆（案例库），支持分析模式（只读）和训练模式（读写）。

## 系统架构

```
Memory System
├── Maxim Memory (粗粒度)        - 抽象的经验格言
│   ├── bull_memory              - 看涨研究员记忆
│   ├── bear_memory              - 看跌研究员记忆
│   ├── trader_memory            - 交易员记忆
│   ├── invest_judge_memory      - 投资判断记忆
│   └── risk_manager_memory      - 风险管理记忆
│
└── Episode Memory (细粒度)      - 完整的交易案例
    ├── MarketState             - 市场状态快照
    ├── AgentAnalysis           - Agent完整分析
    ├── DecisionChain           - 决策链（辩论过程）
    ├── TradeOutcome            - 交易结果
    └── Lesson                  - 抽象的经验教训
```

## 核心特性

### 1. 双层记忆系统

**粗粒度记忆（Maxim Memory）**
- **存储内容**: 抽象的经验格言 `(situation, recommendation)`
- **检索速度**: 快速（向量相似度检索）
- **用途**: 快速参考、实时决策辅助
- **示例**:
  ```python
  situation = "市场恐慌性下跌，VIX达到75，但基本面完好"
  recommendation = "恐慌性下跌 + 基本面完好 = 黄金抄底机会"
  ```

**细粒度记忆（Episode Memory）**
- **存储内容**: 完整的交易案例（包含所有上下文）
- **检索速度**: 较慢（但信息完整）
- **用途**: 深度学习、可复现分析、模式识别
- **包含信息**:
  - 市场状态快照（价格、技术指标、市场环境）
  - 4个Agent的完整分析报告
  - 完整的决策链（Bull vs Bear辩论、风险评估）
  - 实际执行结果和盈亏
  - 抽象的经验教训

### 2. 模式控制（关键特性）

系统强制执行两种模式：

**Analysis Mode（分析模式）** - 🔒 只读
```python
memory_manager = MemoryManager(
    mode=MemoryMode.ANALYSIS,
    config=config
)

# ✅ 允许：检索历史经验
maxims = memory_manager.retrieve_maxims('bull', current_situation)
episodes = memory_manager.retrieve_episodes(market_context)

# 🚫 禁止：写入新经验（会被拒绝）
memory_manager.add_maxim('bull', situation, recommendation)  # 返回 False
memory_manager.add_episode(episode)  # 返回 False
```

**Training Mode（训练模式）** - 读写
```python
memory_manager = MemoryManager(
    mode=MemoryMode.TRAINING,
    config=config
)

# ✅ 允许：检索和写入
maxims = memory_manager.retrieve_maxims('bull', current_situation)
memory_manager.add_maxim('bull', situation, recommendation)  # 成功
memory_manager.add_episode(episode)  # 成功
```

## 使用指南

### 分析模式（当前API使用）

API服务器在启动时自动初始化为分析模式（只读）：

```python
# backend/api/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory_manager

    # 初始化为分析模式（只读）
    memory_manager = MemoryManager(
        mode=MemoryMode.ANALYSIS,  # 🔒 只读
        config=config
    )
```

**检查记忆系统状态**：
```bash
curl http://localhost:8000/api/v1/memory/status
```

响应：
```json
{
  "success": true,
  "data": {
    "mode": "analysis",
    "is_read_only": true,
    "maxim_memory": {
      "bull": {"count": 150, "persistent": true},
      "bear": {"count": 140, "persistent": true},
      "trader": {"count": 200, "persistent": true},
      "invest_judge": {"count": 180, "persistent": true},
      "risk_manager": {"count": 160, "persistent": true}
    },
    "episode_memory": {
      "total_episodes": 350,
      "persist_directory": "./memory_db/episodes"
    }
  }
}
```

### 训练模式（Time-Travel Training）

训练模式用于时间旅行训练，允许AI从历史数据中学习。

**训练脚本示例**（待实现）：

```python
# scripts/time_travel_training.py
from memory import MemoryManager, MemoryMode, TradingEpisode, MarketState
from tradingagents.graph.trading_graph import TradingAgentsGraph
from datetime import datetime, timedelta

# 初始化训练模式记忆系统
memory_manager = MemoryManager(
    mode=MemoryMode.TRAINING,  # 🔓 读写模式
    config=config
)

# 初始化TradingGraph
trading_graph = TradingAgentsGraph(config=config)

# 时间旅行训练循环
start_date = datetime(2020, 1, 1)
end_date = datetime(2024, 12, 31)
current_date = start_date

while current_date <= end_date:
    symbol = "600519.SH"  # 贵州茅台

    # 1️⃣ 检索相似历史案例（使用已有记忆）
    market_context = {
        'market_regime': detect_market_regime(symbol, current_date),
        'vix': get_vix(current_date),
        'rsi': get_rsi(symbol, current_date)
    }

    similar_episodes = memory_manager.retrieve_episodes(
        query_context=market_context,
        top_k=5
    )

    print(f"📚 找到{len(similar_episodes)}个相似历史案例")

    # 2️⃣ 执行分析（AI假装在current_date这一天）
    final_state, processed_signal = trading_graph.propagate(
        symbol,
        current_date.strftime("%Y-%m-%d")
    )

    # 3️⃣ 执行模拟交易
    if processed_signal['action'] == '买入':
        # 执行买入，等待N天后卖出
        entry_price = get_price(symbol, current_date)
        exit_date = current_date + timedelta(days=30)
        exit_price = get_price(symbol, exit_date)

        outcome = TradeOutcome(
            action="BUY",
            entry_price=entry_price,
            exit_price=exit_price,
            percentage_return=(exit_price - entry_price) / entry_price
        )

        # 4️⃣ 抽象经验教训
        if outcome.percentage_return > 0.1:
            lesson = f"成功案例：{市场环境描述} -> 收益{outcome.percentage_return:.1%}"
            success = True
        else:
            lesson = f"失败案例：{市场环境描述} -> 亏损{outcome.percentage_return:.1%}"
            success = False

        # 5️⃣ 存储完整Episode
        episode = TradingEpisode(
            episode_id=f"{current_date.strftime('%Y-%m-%d')}_{symbol}",
            date=current_date.strftime("%Y-%m-%d"),
            symbol=symbol,
            market_state=MarketState(
                date=current_date.strftime("%Y-%m-%d"),
                symbol=symbol,
                price=entry_price,
                # ... 其他市场数据
            ),
            agent_analyses={
                'market': extract_agent_analysis(final_state, 'market'),
                'fundamentals': extract_agent_analysis(final_state, 'fundamentals'),
                # ...
            },
            decision_chain=extract_decision_chain(final_state),
            outcome=outcome,
            lesson=lesson,
            key_lesson=abstract_key_lesson(lesson),  # 浓缩版
            success=success,
            created_at=datetime.now().isoformat(),
            mode='training'
        )

        # ✅ 写入记忆库
        memory_manager.add_episode(episode)

        # 6️⃣ 抽象为格言（粗粒度记忆）
        situation = f"{market_context['market_regime']}, RSI={market_context['rsi']}"
        recommendation = lesson
        memory_manager.add_maxim('bull', situation, recommendation)

        print(f"✅ 存储Episode: {episode.episode_id}, 收益: {outcome.percentage_return:.1%}")

    # 前进到下一个交易日
    current_date = get_next_trading_day(current_date)

print(f"🎓 训练完成！总共学习了{episode_count}个案例")
```

## 数据模型

### TradingEpisode (完整案例)

```python
class TradingEpisode(BaseModel):
    episode_id: str                              # 唯一ID
    date: str                                    # 日期
    symbol: str                                  # 股票代码

    market_state: MarketState                    # 市场状态快照
    agent_analyses: Dict[str, AgentAnalysis]     # Agent分析结果
    decision_chain: DecisionChain                # 决策链
    outcome: Optional[TradeOutcome]              # 交易结果

    lesson: Optional[str]                        # 经验教训
    key_lesson: Optional[str]                    # 浓缩版（用于embedding）
    success: Optional[bool]                      # 是否成功

    created_at: str                              # 创建时间
    mode: str                                    # 'analysis' or 'training'
```

### MarketState (市场状态)

```python
class MarketState(BaseModel):
    date: str
    symbol: str
    price: float

    # 技术指标
    rsi: Optional[float]
    macd: Optional[float]
    ma_5: Optional[float]

    # 市场环境
    vix: Optional[float]
    market_regime: Optional[str]  # bull, bear, sideways, volatile, panic
    sector: Optional[str]
```

## 环境变量配置

```bash
# .env
# 格言库持久化路径
MEMORY_PERSIST_PATH=./memory_db/maxims

# 案例库持久化路径
EPISODE_MEMORY_PATH=./memory_db/episodes

# Embedding模型（用于向量检索）
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

## API接口

### 获取记忆系统状态

```bash
GET /api/v1/memory/status
```

响应：
```json
{
  "success": true,
  "data": {
    "mode": "analysis",
    "is_read_only": true,
    "maxim_memory": {...},
    "episode_memory": {...}
  }
}
```

## 下一步计划

- [ ] 实现时间旅行训练脚本（`scripts/time_travel_training.py`）
- [ ] 整合CVaR-PPO风险约束（借鉴FinRL-DeepSeek）
- [ ] 实现自动经验抽象引擎（从Episode自动生成Maxim）
- [ ] 添加记忆检索质量评估（相似度阈值、多样性）
- [ ] 实现记忆遗忘机制（过期案例降权或删除）

## 技术栈

- **向量数据库**: ChromaDB (持久化)
- **Embedding模型**: Sentence-BERT (paraphrase-multilingual-MiniLM-L12-v2)
- **数据验证**: Pydantic
- **日志系统**: 统一日志框架 (`tradingagents.utils.logging_init`)

## 文件结构

```
backend/memory/
├── __init__.py                  # 模块导出
├── episodic_memory.py           # 细粒度记忆（Episode Bank）
├── memory_manager.py            # 统一管理器（双层记忆 + 模式控制）
└── README.md                    # 本文档

backend/tradingagents/agents/utils/
└── memory.py                    # 粗粒度记忆（已修改为支持持久化）

memory_db/
├── maxims/                      # 格言库持久化目录
│   └── chroma.sqlite3           # ChromaDB数据库
└── episodes/                    # 案例库持久化目录
    └── chroma.sqlite3           # ChromaDB数据库
```

## 常见问题

### Q: 为什么需要两层记忆？

A:
- **粗粒度（Maxim）**: 快速检索、实时决策辅助，类似于"经验法则"
- **细粒度（Episode）**: 深度学习、可复现分析、完整上下文，类似于"案例库"

两者互补：快速决策用Maxim，深度研究用Episode。

### Q: 分析模式为什么要只读？

A: 避免在生产环境中污染记忆库。只有经过验证的训练结果才应该写入记忆。

### Q: 如何确保分析模式不会写入？

A: MemoryManager在初始化时强制指定模式，分析模式下所有写入操作会被拒绝并记录日志。

### Q: 时间旅行训练的核心思想是什么？

A: AI假装回到历史某一天，基于当时的数据做决策，然后用未来的真实结果评估决策质量，从中学习经验。这是一种离线强化学习。

---

**最后更新**: 2025-01-XX
**维护者**: Claude Code
**项目**: HiddenGem Trading System
