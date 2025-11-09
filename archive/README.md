# HiddenGem Backend - 量化交易系统后端

A-股市场中低频量化交易系统的后端实现，基于MCP (Model Context Protocol) 多Agent架构。

## 功能特性

- **多Agent智能决策系统**：7个专业化MCP agents协同工作
  - TechnicalAnalysisAgent - 技术分析
  - FundamentalAgent - 基本面分析
  - RiskManagerAgent - 风险管理（A股特有风险）
  - MarketMonitorAgent - 市场监控
  - PolicyAnalystAgent - 政策分析
  - SentimentAgent - 情绪分析
  - ExecutionAgent - 执行代理

- **A股市场特性支持**
  - 主板/创业板/科创板分类
  - 涨跌停限制处理
  - 质押率、限售股、商誉等风险指标
  - 印花税和佣金计算

- **数据源集成**
  - Tushare Pro 和 AkShare 双数据源
  - 自动fallback机制
  - 速率限制保护

- **TimescaleDB优化**
  - 时序数据自动分区
  - 数据压缩和保留策略
  - 高性能查询优化

## 快速开始

### 1. 环境要求

- Python 3.11+
- Docker & Docker Compose (推荐)
- PostgreSQL 12+ with TimescaleDB (或使用Docker)
- Redis 6+ (或使用Docker)

### 2. 使用Docker启动（推荐）

```bash
# 启动PostgreSQL + TimescaleDB + Redis
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

**可选工具（GUI）**：

```bash
# 启动 pgAdmin (PostgreSQL GUI) 和 Redis Commander
docker-compose --profile tools up -d

# 访问：
# - pgAdmin: http://localhost:5050 (admin@hiddengem.com / admin)
# - Redis Commander: http://localhost:8081
```

### 3. 安装Python依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入必要的配置
# 特别是 TUSHARE_TOKEN
```

### 5. 初始化数据库

```bash
# 运行数据库初始化脚本
python scripts/init_db.py
```

这将创建所有表，设置TimescaleDB hypertables，并配置压缩/保留策略。

## 项目结构

```
backend/
├── api/                    # FastAPI应用（待实现）
├── config/                 # 配置管理
│   ├── settings.py         # 应用设置
│   ├── database.py         # 数据库配置
│   └── agents_config.py    # Agent配置
├── core/                   # 核心业务逻辑
│   ├── mcp_agents/         # MCP Agents
│   │   ├── base_agent.py
│   │   ├── technical_agent.py
│   │   ├── fundamental_agent.py
│   │   ├── risk_agent.py
│   │   ├── market_agent.py
│   │   ├── policy_agent.py
│   │   ├── sentiment_agent.py
│   │   ├── execution_agent.py
│   │   └── orchestrator.py
│   ├── data/               # 数据处理
│   │   ├── models.py       # Pydantic模型
│   │   └── sources.py      # 数据源集成
│   ├── strategy/           # 策略引擎（待实现）
│   ├── execution/          # 交易执行（待实现）
│   └── utils/              # 工具函数
│       ├── indicators.py   # 技术指标
│       ├── helpers.py      # 辅助函数
│       └── validators.py   # 数据验证
├── database/               # 数据库
│   └── models.py           # SQLAlchemy模型
├── scripts/                # 脚本
│   └── init_db.py          # 数据库初始化
├── tests/                  # 测试（待实现）
├── docker-compose.yml      # Docker配置
├── requirements.txt        # Python依赖
└── .env.example            # 环境变量模板
```

## 核心组件说明

### MCP Agents

所有agents继承自`BaseAgent`，实现`analyze()`方法：

```python
from core.mcp_agents.technical_agent import TechnicalAnalysisAgent

# 创建agent
agent = TechnicalAnalysisAgent(redis_client=redis)

# 执行分析
result = await agent.analyze(symbol="000001")

# 结果包含：
# - direction: long/short/hold/close
# - confidence: 0.0 - 1.0
# - analysis: 详细分析数据
# - reasoning: 可读的理由说明
```

### MCP Orchestrator

协调所有agents，生成聚合信号：

```python
from core.mcp_agents.orchestrator import MCPOrchestrator

orchestrator = MCPOrchestrator(redis_client=redis)

# 注册agents
orchestrator.register_agent(technical_agent)
orchestrator.register_agent(fundamental_agent)
# ... 注册其他agents

# 分析股票，所有agents并行执行
results = await orchestrator.analyze_symbol("000001")

# 生成聚合信号
signal = await orchestrator.generate_trading_signal("000001", results)
```

### 数据源

双数据源自动fallback：

```python
from core.data.sources import data_source

# 获取日线数据（自动尝试Tushare，失败则AkShare）
df = data_source.get_daily_bars("000001", "2024-01-01", "2024-12-31")

# 获取实时行情
quote = data_source.get_realtime_quote("000001")

# 获取财务数据
financials = data_source.get_financial_data("000001")
```

### 技术指标

```python
from core.utils.indicators import TechnicalIndicators

# 计算所有指标
df = TechnicalIndicators.calculate_all_indicators(df)

# 单独计算
rsi = TechnicalIndicators.calculate_rsi(df['close'])
macd, signal, hist = TechnicalIndicators.calculate_macd(df['close'])
```

## 开发状态

✅ **已完成**：
- [x] 核心基础设施（配置、数据库、数据源）
- [x] MCP Agent架构
- [x] 7个Agent实现（3个完整 + 4个占位）
- [x] 技术指标库
- [x] 工具函数和验证器
- [x] Docker开发环境

🚧 **进行中**：
- [ ] 策略引擎（摆动交易、趋势跟踪）
- [ ] FastAPI REST API
- [ ] WebSocket实时推送

📋 **计划中**：
- [ ] 回测引擎
- [ ] 订单执行系统
- [ ] 监控和告警
- [ ] 单元测试和集成测试
- [ ] 完整的PolicyAnalyst、Sentiment、Market agents

## 配置说明

### 环境变量（.env）

```env
# 数据库
DATABASE_URL=postgresql://postgres:password@localhost:5432/hiddengem

# Redis
REDIS_URL=redis://localhost:6379/0

# 数据源
TUSHARE_TOKEN=your_token_here
AKSHARE_ENABLED=true

# 交易
TRADING_MODE=simulation  # or live
MAX_POSITION_PCT=0.10
DEFAULT_STOP_LOSS_PCT=0.08

# 应用
DEBUG=true
LOG_LEVEL=INFO
```

### Agent权重配置

在`config/agents_config.py`中调整：

```python
TECHNICAL_AGENT = AgentConfig(
    weight=0.25,  # 25%权重
    timeout=10,
    cache_ttl=300
)
```

## Docker服务

- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **pgAdmin** (可选): http://localhost:5050
- **Redis Commander** (可选): http://localhost:8081

## 文档

- `CLAUDE.md` - 开发指南和规范
- `TASKS.md` - 任务跟踪
- API文档（启动服务器后）：http://localhost:8000/docs

## License

Proprietary - All rights reserved
