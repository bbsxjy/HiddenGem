# 给其他Claude Instance的启动指南

> 欢迎加入HiddenGem并行开发团队！

## 🚀 快速开始

### 1. 阅读任务文档

请按以下顺序阅读：

1. **`TASK_BOARD.md`** (5分钟) - 快速了解任务分配和当前状态
2. **`PARALLEL_TASKS.md`** (15分钟) - 详细了解你的任务内容和技术细节
3. **`IMPLEMENTATION_PLAN_V2.md`** - 了解整体RL系统架构（基于FinRL）
4. **`../CLAUDE.md`** - 了解项目规范和后端架构

### 2. 确认你的任务

在`TASK_BOARD.md`中找到你负责的任务：

- **Instance #1**: RL引擎集成FinRL (🔴 P0)
- **Instance #2**: 回测系统 (🟠 P1)
- **Instance #3**: Paper Trading (🟠 P1)
- **Instance #4**: 东财模拟盘 (🟡 P2)
- **Instance #5**: 东财真实盘 (🔵 P3)
- **Instance #6**: 性能监控 (🟠 P1)

### 3. 检查依赖关系

在`PARALLEL_TASKS.md`中查看你的任务依赖：

- Task 1: 无依赖，可立即开始 ✅
- Task 2, 3: 依赖Task 1
- Task 4: 依赖Task 3
- Task 5: 依赖Task 4（且需满足严格前置条件）
- Task 6: 依赖Task 2, 3

### 4. 创建工作分支

```bash
cd backend/
git checkout -b task-X-<your-task-name>

# 例如：
# git checkout -b task-1-rl-engine
# git checkout -b task-2-backtesting
# git checkout -b task-3-paper-trading
```

### 5. 开始工作

按照`PARALLEL_TASKS.md`中你的任务的详细步骤开始实现。

## 📝 工作流程

### 每日工作流

1. **早上 (开始工作)**:
   - 拉取最新代码: `git pull origin master`
   - 查看`TASK_BOARD.md`了解其他任务进度
   - 检查"当前问题"列表，看是否影响你

2. **工作中**:
   - 按子任务清单逐项完成
   - 遇到问题及时在`TASK_BOARD.md`记录
   - 完成子任务后立即提交代码

3. **晚上 (结束工作)**:
   - 在`TASK_BOARD.md`更新每日进度
   - 提交所有代码
   - 标注明天计划

### Git提交规范

```bash
# 格式: <type>(task-X): <description>

git add .
git commit -m "feat(task-1): 实现LLMEnhancedTradingEnv"
git commit -m "fix(task-3): 修复订单执行逻辑"
git commit -m "test(task-2): 添加回测引擎单元测试"
```

### 代码审查

每完成一个子任务（1.1, 1.2等），提交后：

1. 在`TASK_BOARD.md`中打勾✅
2. 推送到你的分支
3. 继续下一个子任务

完成整个Task后：

1. 创建Pull Request
2. 通知其他依赖你的Instance
3. 等待审查和合并

## 🔧 开发环境设置

### 安装依赖

```bash
cd backend/

# 激活虚拟环境
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装基础依赖（已有）
# pip install -r requirements.txt

# 如果你的任务需要额外依赖，在你的分支安装：
# Task 1: FinRL相关
pip install git+https://github.com/AI4Finance-Foundation/FinRL.git
pip install stable-baselines3[extra]
pip install pyfolio

# Task 4,5: easytrader（东方财富）
pip install easytrader

# Task 6: 性能监控
pip install quantstats
```

### 配置环境变量

确保`.env`配置正确：

```bash
# LLM配置
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your_api_key

# 数据源
TUSHARE_TOKEN=your_tushare_token

# 记忆系统
MEMORY_PERSIST_PATH=./memory_db/maxims
EPISODE_MEMORY_PATH=./memory_db/episodes
```

### 测试环境

```bash
# 测试TradingAgents是否正常
python scripts/demo_memory_system.py

# 测试数据获取
python -c "from tradingagents.dataflows.interface import get_stock_data_by_market; print(get_stock_data_by_market('600519.SH', '2024-01-01', '2024-01-31'))"
```

## 📚 关键参考

### 你的任务相关文档

**Task 1 (RL引擎)**:
- `IMPLEMENTATION_PLAN_V2.md` - FinRL集成方案
- `TIME_TRAVEL_TRAINING.md` - 时间旅行训练（可参考）
- [FinRL官方文档](https://finrl.readthedocs.io/)

**Task 2 (回测)**:
- `IMPLEMENTATION_PLAN.md` (Phase 2, 3) - 回测系统设计
- [PyFolio文档](https://github.com/quantopian/pyfolio)

**Task 3 (Paper Trading)**:
- `IMPLEMENTATION_PLAN.md` (Phase 2) - 模拟交易系统
- `IMPLEMENTATION_PLAN_V2.md` (Task 4.1) - 实时交易接口

**Task 4,5 (东财)**:
- [easytrader文档](https://github.com/shidenggui/easytrader)
- A股交易规则（自行查阅）

**Task 6 (监控)**:
- `IMPLEMENTATION_PLAN.md` (Task 2.4) - 绩效追踪
- [QuantStats文档](https://github.com/ranaroussi/quantstats)

### 已完成的模块（可直接使用）

1. **TradingAgents系统** ✅
   - 7个专业化Agent
   - 多轮辩论机制
   - 信号生成

2. **记忆系统** ✅
   - Maxim Memory（粗粒度）
   - Episode Memory（细粒度）
   - 模式控制（分析/训练）

3. **数据层** ✅
   - 统一数据接口
   - 多级缓存
   - A股/港股/美股支持

**使用示例**:

```python
# 使用TradingAgents
from tradingagents.graph.trading_graph import TradingAgentsGraph
trading_graph = TradingAgentsGraph()
final_state, signal = trading_graph.propagate("600519.SH", "2024-01-15")

# 使用记忆系统
from memory import MemoryManager, MemoryMode
memory = MemoryManager(mode=MemoryMode.ANALYSIS)
episodes = memory.retrieve_episodes(query_context={...}, top_k=5)

# 使用数据接口
from tradingagents.dataflows.interface import get_stock_data_by_market
data = get_stock_data_by_market("600519.SH", "2024-01-01", "2024-12-31")
```

## ⚠️ 重要注意事项

### Task 1 (Instance #1)

- ✅ 你的任务是P0优先级，其他很多任务都依赖你
- ✅ 确保接口设计清晰，方便其他任务集成
- ✅ 及时更新`TASK_BOARD.md`让其他人知道进度

### Task 2, 3 (Instance #2, #3)

- ⏸️ 在Task 1完成前，可以先做架构设计和接口定义
- ⏸️ 可以先实现不依赖RL的部分（如数据处理、订单管理等）
- ⏸️ 与Task 1保持沟通，了解接口进展

### Task 4 (Instance #4)

- ⚠️ 东方财富模拟盘可能需要注册账号
- ⚠️ 研究easytrader是否支持模拟盘，如不支持考虑其他方案
- ⚠️ 如遇阻塞，及时在`TASK_BOARD.md`记录

### Task 5 (Instance #5)

- 🚨 **真实资金交易，极度谨慎！**
- 🚨 必须满足所有前置条件才能开始
- 🚨 优先级最低，可以最后做
- 🚨 在Task 4完成并验证前，建议先做设计和文档

### Task 6 (Instance #6)

- ⏸️ 依赖Task 2, 3，可先做接口设计
- ✅ 可以先实现独立的性能指标计算函数
- ✅ 可以先设计Dashboard API接口

## 🆘 遇到问题怎么办

### 1. 技术问题

**优先顺序**:
1. 查看相关文档（`PARALLEL_TASKS.md`, `CLAUDE.md`等）
2. 查看已有代码实现
3. 在`TASK_BOARD.md`的"当前问题"表格记录
4. 标注`[BLOCKED]`并说明情况

### 2. 依赖阻塞

如果你的任务依赖其他任务，但对方尚未完成：

1. 先做不依赖的部分
2. 设计接口和Mock数据用于测试
3. 与负责依赖任务的Instance沟通
4. 在`TASK_BOARD.md`记录阻塞情况

### 3. 接口变更

如果你需要修改已定义的接口：

1. 在`TASK_BOARD.md`的"接口变更通知"表格记录
2. 说明变更原因和影响范围
3. 通知受影响的其他Instance
4. 达成一致后再修改

## ✅ 完成标准

每个任务都有明确的完成标准，在`PARALLEL_TASKS.md`中查看。

**通用标准**:
- [ ] 代码符合规范（命名、注释、测试）
- [ ] 单元测试覆盖率 > 70%
- [ ] 关键功能有集成测试
- [ ] 代码通过审查
- [ ] 文档完整（docstring + README）
- [ ] 在`TASK_BOARD.md`中所有子任务打勾✅

## 📞 联系方式

遇到紧急问题：

1. 在`TASK_BOARD.md`最上方的"🚨 当前问题"表格记录
2. 标注优先级和影响
3. @相关Instance
4. 通过用户转达给其他Instance

---

**祝开发顺利！让我们一起打造强大的RL交易系统！🚀**

---

**文档维护**: Instance #1
**创建时间**: 2025-01-09
**适用范围**: Instance #2 ~ #6
