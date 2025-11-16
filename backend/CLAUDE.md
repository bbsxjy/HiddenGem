# TradingAgents-CN Backend CLAUDE.md

This file provides guidance for adapting TradingAgents-CN to work as the backend for the HiddenGem frontend.

## Overall Rules

1. **No Mock Data**: Never use mock data or leave TODO comments. All implementations must be complete and functional.
2. **Follow Specifications**: Strictly follow the rules defined in this document and HIDDENGEM_TASKS.md.
3. **Git Commits**: Before fixing or adding new content, commit previous work using git.
4. **No Server Startup**: Do not start servers - let the user handle server startup.
5. **Use Ultrathink**: Apply careful reasoning for complex implementations.
6. **保护核心模块**: 不要修改 `tradingagents/` 目录下的核心代码，只添加 API 层。

## Project Overview

TradingAgents-CN 是一个基于 LangGraph 的多智能体量化交易系统，包含：
- 7个专业化 Agent（市场、基本面、情绪、新闻、Bull、Bear、风险管理）
- 多轮辩论机制（Bull vs Bear）
- 反思与记忆系统（ChromaDB）
- 多级数据缓存（Redis、MongoDB、文件）
- 支持A股、港股、美股

**改造目标**: 在保留所有核心功能的前提下，添加 FastAPI REST API + WebSocket 接口层，使其能够对接 HiddenGem 前端。

## Technology Stack

**核心框架**（已有）:
- Python 3.11+
- LangGraph for workflow orchestration
- LangChain for LLM integration
- ChromaDB for memory storage
- Redis for caching
- MongoDB for persistent storage

**新增技术栈**:
- FastAPI for REST API
- Uvicorn for ASGI server
- WebSockets for real-time updates
- Pydantic for data validation

**数据源**（已有）:
- Tushare Pro for A-share data
- AkShare for alternative data
- yfinance for US/HK stocks
- Finnhub for US stock data

## Project Structure

```
TradingAgents-CN/
├── tradingagents/               # ✅ 核心模块（不要修改）
│   ├── agents/                  # 7个专业化 Agent
│   │   ├── analysts/            # 分析师（market, fundamentals, news, social）
│   │   ├── researchers/         # 研究员（bull, bear）
│   │   ├── managers/            # 管理者（research_manager, risk_manager）
│   │   ├── trader/              # 交易员
│   │   ├── risk_mgmt/           # 风险管理（aggressive, conservative, neutral）
│   │   └── utils/               # Agent工具（states, memory, google_tool_handler）
│   ├── dataflows/               # 数据层（统一数据接口）
│   │   ├── interface.py         # 统一数据接口（重点使用）
│   │   ├── optimized_china_data.py  # A股优化
│   │   ├── optimized_us_data.py     # 美股优化
│   │   ├── cache_manager.py     # 多级缓存
│   │   └── data_source_manager.py   # 数据源管理
│   ├── graph/                   # LangGraph工作流
│   │   ├── trading_graph.py     # 主工作流（重点包装）
│   │   ├── setup.py             # 图设置
│   │   ├── conditional_logic.py # 条件逻辑
│   │   ├── propagation.py       # 状态传播
│   │   └── reflection.py        # 反思机制
│   ├── utils/                   # 工具函数
│   │   ├── logging_init.py      # 日志初始化
│   │   └── stock_utils.py       # 股票工具
│   └── default_config.py        # 默认配置
├── api/                         # 🆕 新增（FastAPI层）
│   ├── __init__.py
│   ├── main.py                  # FastAPI入口
│   ├── routers/                 # API路由
│   │   ├── __init__.py
│   │   ├── agents.py            # Agent API（核心）
│   │   ├── market.py            # 市场数据API
│   │   ├── portfolio.py         # 投资组合API
│   │   ├── orders.py            # 订单API
│   │   └── strategies.py        # 策略API（可选）
│   ├── models/                  # Pydantic模型
│   │   ├── __init__.py
│   │   ├── requests.py          # 请求模型
│   │   └── responses.py         # 响应模型
│   ├── services/                # 服务层
│   │   ├── __init__.py
│   │   └── agent_service.py     # Agent服务（包装TradingGraph）
│   ├── websocket/               # WebSocket
│   │   ├── __init__.py
│   │   └── manager.py           # 连接管理
│   └── middleware/              # 中间件
│       ├── __init__.py
│       ├── auth.py              # 认证（可选）
│       └── logging.py           # 日志
├── tests/                       # 测试
│   ├── test_api.py              # API测试
│   └── conftest.py              # Pytest配置
├── backup/                      # 备份目录
│   ├── web_streamlit/           # 原Streamlit应用
│   └── cli/                     # 原CLI工具
├── docs/                        # 文档
│   ├── API.md                   # API文档（重要）
│   └── DEPLOYMENT.md            # 部署文档
├── scripts/                     # 脚本
│   ├── cleanup_frontend.py      # 清理脚本
│   └── start_api.sh             # 启动脚本
├── requirements.txt             # Python依赖（原有）
├── requirements_api.txt         # API依赖（新增）
├── .env.example                 # 环境变量示例
├── docker-compose.yml           # Docker配置
├── Dockerfile
├── CLAUDE.md                    # 本文件
└── HIDDENGEM_TASKS.md           # 任务清单（重要）
```

## Key Implementation Guidelines

### 1. Agent API 实现原则

**核心原则**: 包装而不是修改

```python
# ✅ 正确：包装 TradingAgentsGraph
from tradingagents.graph.trading_graph import TradingAgentsGraph

class AgentService:
    def __init__(self, trading_graph: TradingAgentsGraph):
        self.trading_graph = trading_graph

    async def analyze_all_agents(self, symbol: str, trade_date: str):
        # 调用原有逻辑
        final_state, processed_signal = self.trading_graph.propagate(symbol, trade_date)

        # 格式化为前端期望的格式
        return self._format_response(final_state, processed_signal)

# ❌ 错误：修改核心代码
# 不要修改 tradingagents/graph/trading_graph.py
```

### 2. Agent名称映射

前端期望的Agent名称与TradingAgents-CN内部名称不同，需要映射：

```python
AGENT_MAPPING = {
    # 前端名称 -> TradingAgents内部名称
    'technical': 'market',        # 技术分析 -> 市场分析师
    'fundamental': 'fundamentals', # 基本面 -> 基本面分析师
    'sentiment': 'social',         # 情绪 -> 社交媒体分析师
    'market': 'market',            # 市场 -> 市场分析师
    'policy': 'news',              # 政策 -> 新闻分析师
    'risk': 'risk_manager',        # 风险 -> 风险管理器
    'execution': 'trader'          # 执行 -> 交易员
}
```

### 3. 数据层调用

**直接使用 tradingagents.dataflows.interface**:

```python
from tradingagents.dataflows.interface import (
    get_stock_data_by_market,       # 统一数据接口（推荐）
    get_china_stock_data_unified,   # A股数据
    get_china_stock_info_unified,   # A股信息
    get_hk_stock_data_unified,      # 港股数据
)

# 示例：获取股票数据
@router.get("/market/data/{symbol}")
async def get_market_data(symbol: str, start_date: str, end_date: str):
    # 自动识别A股/港股/美股
    data = get_stock_data_by_market(symbol, start_date, end_date)
    return {"success": True, "data": data}
```

### 4. 响应格式规范

**所有API响应必须遵循前端期望的格式**:

```python
# 成功响应
{
    "success": true,
    "data": { ... },
    "message": "操作成功",
    "timestamp": "2025-01-XX..."
}

# 错误响应
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "参数错误",
        "details": { ... }
    },
    "timestamp": "2025-01-XX..."
}
```

### 5. Agent分析结果格式

**参考 frontend/src/types/agent.ts**:

```python
# AgentAnalysisResult
{
    "agent_name": "technical",
    "symbol": "000001.SZ",
    "score": 0.75,
    "direction": "long",  # long | short | hold | close
    "confidence": 0.8,
    "reasoning": "技术面分析显示...",
    "analysis": {
        "full_report": "...",
        "indicators": {...}
    },
    "execution_time_ms": 1500,
    "timestamp": "2025-01-XX...",
    "is_error": false
}

# AnalyzeAllResponse
{
    "symbol": "000001.SZ",
    "agent_results": {
        "technical": {...},
        "fundamental": {...},
        "sentiment": {...},
        "policy": {...}
    },
    "aggregated_signal": {
        "direction": "long",
        "confidence": 0.85,
        "position_size": 0.1,
        "num_agreeing_agents": 3,
        "warnings": [],
        "metadata": {...}
    },
    "signal_rejection_reason": null,
    "llm_analysis": {
        "recommended_direction": "long",
        "confidence": 0.85,
        "reasoning": "综合分析...",
        "risk_assessment": "中等风险",
        "key_factors": ["技术面强势", "基本面稳健"],
        "price_targets": {
            "entry": 15.0,
            "stop_loss": 13.5,
            "take_profit": 17.0
        }
    }
}
```

### 6. 提取分析结果的逻辑

从 `final_state` 中提取各个分析师的报告：

```python
def _format_response(self, final_state: dict, processed_signal: Any) -> dict:
    """从TradingGraph结果中提取并格式化为前端格式"""

    # 提取各个分析师的报告
    agent_results = {
        'technical': self._format_agent_result(
            final_state.get('market_report', ''),
            'technical'
        ),
        'fundamental': self._format_agent_result(
            final_state.get('fundamentals_report', ''),
            'fundamental'
        ),
        'sentiment': self._format_agent_result(
            final_state.get('sentiment_report', ''),
            'sentiment'
        ),
        'policy': self._format_agent_result(
            final_state.get('news_report', ''),
            'policy'
        ),
    }

    # 提取辩论结果作为LLM分析
    debate_state = final_state.get('investment_debate_state', {})
    llm_analysis = {
        "recommended_direction": self._extract_direction(
            debate_state.get('judge_decision', '')
        ),
        "confidence": 0.85,
        "reasoning": debate_state.get('judge_decision', ''),
        "risk_assessment": final_state.get('risk_debate_state', {}).get('judge_decision', ''),
        "key_factors": self._extract_key_factors(final_state),
        "price_targets": {},
        "analysis_timestamp": datetime.now().isoformat()
    }

    # 提取最终决策
    final_decision = final_state.get('final_trade_decision', '')
    aggregated_signal = {
        "direction": self._extract_direction(final_decision),
        "confidence": 0.8,
        "position_size": 0.1,
        "num_agreeing_agents": 3,
        "warnings": [],
        "metadata": {
            "analysis_method": "llm",
            "agent_count": 4
        }
    }

    return {
        "symbol": final_state.get('company_of_interest', ''),
        "agent_results": agent_results,
        "aggregated_signal": aggregated_signal,
        "llm_analysis": llm_analysis
    }

def _extract_direction(self, text: str) -> str:
    """从文本中提取交易方向"""
    text_lower = text.lower()

    buy_keywords = ['买入', '看涨', 'buy', 'long', '建议持有', '积极']
    sell_keywords = ['卖出', '看跌', 'sell', 'short', '减持', '谨慎']

    buy_score = sum(1 for kw in buy_keywords if kw in text_lower)
    sell_score = sum(1 for kw in sell_keywords if kw in text_lower)

    if buy_score > sell_score:
        return 'long'
    elif sell_score > buy_score:
        return 'short'
    else:
        return 'hold'
```

### 7. WebSocket 实现

```python
from fastapi import WebSocket, WebSocketDisconnect
import json
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    async def subscribe(self, websocket: WebSocket, symbol: str):
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = set()
        self.subscriptions[symbol].add(websocket)

    async def send_to_symbol_subscribers(self, symbol: str, message: dict):
        if symbol not in self.subscriptions:
            return

        for connection in self.subscriptions[symbol]:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

# 在 FastAPI 应用中使用
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "subscribe":
                await ws_manager.subscribe(websocket, message["symbol"])
                await websocket.send_json({
                    "type": "subscribed",
                    "symbol": message["symbol"]
                })
            elif message["type"] == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
```

## API Endpoints Overview

### Agent Endpoints (核心)

```
GET    /api/v1/agents/status
POST   /api/v1/agents/{agent_name}/analyze
POST   /api/v1/agents/analyze-all/{symbol}
POST   /api/v1/agents/analyze-all/{symbol}/stream  (SSE)
GET    /api/v1/agents/performance
```

### Market Data Endpoints

```
GET    /api/v1/market/data/{symbol}
GET    /api/v1/market/info/{symbol}
GET    /api/v1/market/search
GET    /api/v1/market/realtime/{symbol}  (WebSocket)
```

### Portfolio Endpoints

```
GET    /api/v1/portfolio/positions
GET    /api/v1/portfolio/summary
GET    /api/v1/portfolio/history
GET    /api/v1/portfolio/performance
```

### Order Endpoints

```
POST   /api/v1/orders/create
GET    /api/v1/orders/list
GET    /api/v1/orders/{order_id}
POST   /api/v1/orders/{order_id}/cancel
```

### WebSocket

```
WS     /ws
```

详细的API文档请参考 `docs/API.md`。

## Development Commands

```bash
# 激活虚拟环境
cd "D:\Program Files (x86)\CodeRepos\HiddenGem\reference\TradingAgents-CN"
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装API依赖
pip install -r requirements_api.txt

# 开发模式启动（自动重载）
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式启动
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

# 运行测试
pytest tests/test_api.py -v

# 访问API文档
# http://localhost:8000/docs  (Swagger UI)
# http://localhost:8000/redoc  (ReDoc)
```

## Environment Variables

创建 `.env` 文件（参考 `.env.example`）：

```bash
# LLM配置
LLM_PROVIDER=dashscope  # dashscope, deepseek, openai, google, etc.
DEEP_THINK_LLM=qwen-plus
QUICK_THINK_LLM=qwen-turbo

# API密钥
DASHSCOPE_API_KEY=your_dashscope_api_key
TUSHARE_TOKEN=your_tushare_token

# 数据库
REDIS_URL=redis://localhost:6379/0
MONGODB_URI=mongodb://localhost:27017/tradingagents

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# CORS配置
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# 日志
LOG_LEVEL=INFO
```

## Testing Strategy

### 1. API测试

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_agents_status():
    response = client.get("/api/v1/agents/status")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7  # 7个Agent

def test_analyze_stock():
    response = client.post("/api/v1/agents/analyze-all/000001.SZ")
    assert response.status_code == 200
    data = response.json()
    assert "symbol" in data
    assert "agent_results" in data
    assert "aggregated_signal" in data
```

### 2. 前后端联调

```bash
# 终端1：启动后端
cd "D:\Program Files (x86)\CodeRepos\HiddenGem\reference\TradingAgents-CN"
uvicorn api.main:app --reload --port 8000

# 终端2：启动前端
cd "D:\Program Files (x86)\CodeRepos\HiddenGem\frontend"
npm run dev

# 浏览器访问: http://localhost:5173
```

## Important Notes

1. **不要修改 tradingagents/ 核心模块**
   - 只添加 API 层，不改动核心逻辑
   - 保持 TradingAgents-CN 的所有功能

2. **确保与前端API匹配**
   - 参考 `frontend/src/api/*.ts` 文件
   - 参考 `frontend/src/types/*.ts` 类型定义
   - 响应格式必须一致

3. **使用现有数据层**
   - 直接使用 `tradingagents.dataflows.interface`
   - 不要重新实现数据获取逻辑
   - 利用现有的多级缓存

4. **Git提交规范**
   ```
   feat(api): 添加 Agent API 路由
   fix(ws): 修复 WebSocket 连接问题
   docs: 更新 API 文档
   chore: 清理前端文件
   test: 添加 API 测试
   refactor(api): 重构 Agent 服务层
   ```

5. **日志规范**
   ```python
   from tradingagents.utils.logging_init import get_logger
   logger = get_logger("api")

   logger.info(f"📊 开始分析: {symbol}")
   logger.debug(f"🔍 [DEBUG] 参数: {params}")
   logger.error(f"❌ 错误: {error}")
   logger.warning(f"⚠️ 警告: {warning}")
   ```

6. **错误处理**
   ```python
   from fastapi import HTTPException

   try:
       result = some_operation()
   except ValueError as e:
       raise HTTPException(status_code=400, detail=str(e))
   except Exception as e:
       logger.error(f"❌ 未知错误: {e}")
       raise HTTPException(status_code=500, detail="内部服务器错误")
   ```

7. **随时可以拾起工作**
   - 查看 `HIDDENGEM_TASKS.md` 的 ✅ 标记
   - 每完成一个任务就打勾并提交
   - Git 提交记录保存进度

## Performance Considerations

1. **Agent分析性能**
   - 单次完整分析约需 30-60秒（7个Agent + 辩论）
   - 使用流式API（SSE）提供实时进度反馈
   - 考虑使用后台任务队列（Celery）处理耗时分析

2. **数据缓存**
   - TradingAgents-CN 已实现多级缓存（Redis、MongoDB、文件）
   - 直接使用即可，无需额外优化

3. **WebSocket连接数**
   - 单个uvicorn worker 可处理约 1000 并发连接
   - 生产环境使用多worker部署

## Deployment

### Docker部署（推荐）

```bash
# 构建镜像
docker build -t hiddengem-backend:latest .

# 运行容器
docker-compose up -d

# 查看日志
docker-compose logs -f api
```

### 生产环境部署

```bash
# 使用 supervisor 管理进程
[program:hiddengem-api]
command=/path/to/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
directory=/path/to/TradingAgents-CN
user=appuser
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/hiddengem/api.log
```

## Troubleshooting

### 1. TradingGraph 初始化失败

```python
# 检查配置
from tradingagents.default_config import DEFAULT_CONFIG
print(DEFAULT_CONFIG)

# 检查LLM Provider
print(os.getenv('LLM_PROVIDER'))
print(os.getenv('DASHSCOPE_API_KEY'))
```

### 2. 前端无法连接

```bash
# 检查CORS配置
curl -H "Origin: http://localhost:5173" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     http://localhost:8000/api/v1/agents/status

# 应该返回 CORS 头
```

### 3. WebSocket连接失败

```bash
# 使用 wscat 测试
npm install -g wscat
wscat -c ws://localhost:8000/ws

# 发送订阅消息
> {"type": "subscribe", "symbol": "000001.SZ"}
```

## Related Documentation

- [任务清单](./HIDDENGEM_TASKS.md) - 详细的改造任务清单
- [API文档](./docs/API.md) - 完整的API接口文档
- [前端API客户端](../../frontend/src/api/) - 前端API调用代码
- [前端类型定义](../../frontend/src/types/) - TypeScript类型定义
- [TradingAgents原始文档](./README.md) - 原始项目文档

---

**最后更新**: 2025-01-XX
**维护者**: Claude Code
**项目**: HiddenGem Trading System
