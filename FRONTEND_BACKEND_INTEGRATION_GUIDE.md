# Frontend-Backend Integration Guide

**完成时间**: 2025-11-09
**状态**: ✅ 前后端配置已对齐

---

## 📊 集成状态概览

### 后端（Backend）✅
- **位置**: `backend/api/`
- **框架**: FastAPI + WebSocket
- **端口**: 8000
- **已实现端点**:
  - `/api/v1/agents/status` - Agent状态
  - `/api/v1/agents/analyze-all/{symbol}` - 多Agent分析（核心功能）
  - `/api/v1/market/data/{symbol}` - 市场数据
  - `/ws` - WebSocket实时推送
  - `/health` - 健康检查
  - `/docs` - API文档（Swagger UI）

### 前端（Frontend）✅
- **位置**: `frontend/`
- **框架**: React + Vite + TypeScript
- **端口**: 5173（开发模式）
- **API配置**: 已对齐后端实现
- **环境变量**: `.env` 已配置为后端地址

### 配置对齐情况 ✅
- ✅ Agent分析端点：`/api/v1/agents/analyze-all/{symbol}`
- ✅ 市场数据端点：`/api/v1/market/data/{symbol}` (含别名)
- ✅ 超时配置：5分钟 longTimeout for Agent分析
- ✅ 重试策略：长时间操作不重试
- ✅ CORS配置：后端允许 localhost:5173 和 localhost:3000

---

## 🚀 启动步骤

### 1. 启动后端 API Server

**方法1：使用启动脚本（推荐）**
```bash
cd backend
python start_api.py
```

**方法2：直接使用uvicorn**
```bash
cd backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**验证后端启动成功**：
- 访问健康检查: http://localhost:8000/health
- 访问API文档: http://localhost:8000/docs
- 应该看到：
  ```json
  {
    "status": "healthy",
    "timestamp": "2025-11-09T...",
    "version": "0.1.0"
  }
  ```

### 2. 启动前端开发服务器

```bash
cd frontend
npm run dev
```

**验证前端启动成功**：
- 访问: http://localhost:5173
- 应该看到 HiddenGem Trading System 主界面

---

## 🧪 测试集成

### 测试1: 健康检查

**使用curl**:
```bash
curl http://localhost:8000/health
```

**预期响应**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-09T...",
  "version": "0.1.0"
}
```

### 测试2: Agent状态查询

**使用curl**:
```bash
curl http://localhost:8000/api/v1/agents/status
```

**预期响应**:
```json
{
  "success": true,
  "data": [
    {
      "agent_name": "market",
      "enabled": true,
      "weight": 1.0,
      "status": "active"
    },
    // ... 其他agents
  ]
}
```

### 测试3: 市场数据查询

**使用curl**:
```bash
# A股示例
curl "http://localhost:8000/api/v1/market/data/600519.SH?limit=5"

# 美股示例
curl "http://localhost:8000/api/v1/market/data/NVDA?limit=5"
```

**预期响应**:
```json
{
  "success": true,
  "symbol": "600519.SH",
  "data": [
    {
      "date": "2025-11-09",
      "open": 1650.0,
      "high": 1680.0,
      "low": 1640.0,
      "close": 1670.0,
      "volume": 1234567
    }
    // ... 更多数据
  ],
  "count": 5
}
```

### 测试4: 多Agent分析（核心功能）

**注意**: 此请求可能需要30-60秒，因为要运行7个Agent + 辩论机制

**使用curl**:
```bash
# A股示例 - 贵州茅台
curl -X POST "http://localhost:8000/api/v1/agents/analyze-all/600519.SH"

# 美股示例 - NVIDIA
curl -X POST "http://localhost:8000/api/v1/agents/analyze-all/NVDA"
```

**预期响应结构**:
```json
{
  "success": true,
  "data": {
    "symbol": "600519.SH",
    "agent_results": {
      "technical": {
        "agent_name": "technical",
        "score": 0.75,
        "direction": "long",
        "confidence": 0.8,
        "reasoning": "技术面分析...",
        "analysis": {
          "full_report": "详细分析报告...",
          "indicators": {...}
        }
      },
      "fundamental": {...},
      "sentiment": {...},
      "policy": {...}
    },
    "aggregated_signal": {
      "direction": "long",
      "confidence": 0.85,
      "position_size": 0.1,
      "num_agreeing_agents": 3,
      "warnings": []
    },
    "llm_analysis": {
      "recommended_direction": "long",
      "confidence": 0.85,
      "reasoning": "综合分析显示...",
      "risk_assessment": "中等风险",
      "key_factors": ["技术面强势", "基本面稳健"],
      "price_targets": {
        "entry": 1650.0,
        "stop_loss": 1550.0,
        "take_profit": 1800.0
      }
    }
  },
  "timestamp": "2025-11-09T..."
}
```

### 测试5: WebSocket连接

**使用wscat**（需要先安装：`npm install -g wscat`）:
```bash
wscat -c ws://localhost:8000/ws
```

**发送订阅消息**:
```json
{"type": "subscribe", "symbol": "600519.SH"}
```

**预期响应**:
```json
{"type": "welcome", "message": "Connected to HiddenGem API", "timestamp": "..."}
{"type": "subscribed", "symbol": "600519.SH"}
```

**发送心跳**:
```json
{"type": "ping"}
```

**预期响应**:
```json
{"type": "pong", "timestamp": "..."}
```

---

## 🎯 前端UI测试

### 1. 打开前端界面

访问: http://localhost:5173

### 2. 测试Agent分析功能

1. 在搜索框输入股票代码（如 `600519.SH` 或 `NVDA`）
2. 点击"分析"按钮
3. 应该看到：
   - Loading 状态（显示进度）
   - 30-60秒后显示分析结果
   - 包含4个Agent的分析结果（technical, fundamental, sentiment, policy）
   - 显示综合信号和LLM分析

### 3. 测试市场数据功能

1. 查看股票K线图
2. 应该显示从后端获取的OHLCV数据
3. 数据应该是实时的（非mock数据）

### 4. 检查Network请求

打开浏览器开发者工具 (F12) -> Network标签：

**应该看到的请求**:
- `http://localhost:8000/api/v1/agents/analyze-all/600519.SH` - POST请求
- `http://localhost:8000/api/v1/market/data/600519.SH` - GET请求
- `ws://localhost:8000/ws` - WebSocket连接

**检查响应**:
- 状态码应该是 200
- 响应格式应该与上面的预期响应匹配
- 无CORS错误

---

## 🔍 故障排查

### 问题1: CORS错误

**症状**:
```
Access to XMLHttpRequest at 'http://localhost:8000/...' from origin 'http://localhost:5173'
has been blocked by CORS policy
```

**解决方案**:
1. 检查后端CORS配置（`backend/api/main.py` 第56-64行）
2. 确认 `http://localhost:5173` 在允许的origins列表中
3. 重启后端服务器

### 问题2: 连接超时

**症状**:
```
timeout of 30000ms exceeded
```

**解决方案**:
1. 检查后端是否正在运行：`curl http://localhost:8000/health`
2. 检查前端环境变量：`frontend/.env` 中的 `VITE_API_BASE_URL`
3. 确认防火墙未阻止8000端口

### 问题3: Agent分析超时

**症状**:
```
timeout of 300000ms exceeded (5分钟超时)
```

**原因**: Agent分析确实需要很长时间（30-60秒）

**解决方案**:
1. 这是正常的，前端已配置5分钟超时
2. 如果经常超时，可以：
   - 检查后端日志是否有错误
   - 验证LLM API密钥是否正确（`backend/.env`）
   - 考虑使用流式API（`/api/v1/agents/analyze-all-stream/{symbol}`）

### 问题4: WebSocket连接失败

**症状**:
```
WebSocket connection to 'ws://localhost:8000/ws' failed
```

**解决方案**:
1. 确认后端支持WebSocket（`backend/api/main.py` 第113-188行）
2. 检查前端WebSocket URL配置（`frontend/.env` 中的 `VITE_WS_URL`）
3. 使用wscat测试WebSocket是否工作：`wscat -c ws://localhost:8000/ws`

### 问题5: 返回数据格式错误

**症状**:
```
TypeError: Cannot read property 'agent_results' of undefined
```

**解决方案**:
1. 检查后端响应格式是否正确
2. 查看浏览器Network标签中的实际响应
3. 确认响应包含 `success: true` 和 `data` 字段
4. 检查 `frontend/src/api/client.ts` 中的 `extractData` 函数

---

## 📝 环境变量配置

### 后端环境变量 (`backend/.env`)

```env
# LLM配置
LLM_PROVIDER=dashscope
DEEP_THINK_LLM=qwen-plus
QUICK_THINK_LLM=qwen-turbo
DASHSCOPE_API_KEY=your_api_key_here

# 数据源
TUSHARE_TOKEN=your_tushare_token_here

# API配置
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# 数据库（可选）
REDIS_URL=redis://localhost:6379/0
MONGODB_URI=mongodb://localhost:27017/tradingagents
```

### 前端环境变量 (`frontend/.env`)

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_NAME=HiddenGem Trading System
```

**如果后端运行在其他机器上**，修改IP地址：
```env
VITE_API_BASE_URL=http://192.168.31.147:8000
VITE_WS_URL=ws://192.168.31.147:8000
```

---

## 🎉 验收标准

### 后端验收
- [x] FastAPI服务可以启动（端口8000）
- [x] 健康检查端点正常（`/health`）
- [x] Agent状态端点正常（`/api/v1/agents/status`）
- [x] 市场数据端点正常（`/api/v1/market/data/{symbol}`）
- [x] Agent分析端点正常（`/api/v1/agents/analyze-all/{symbol}`）
- [x] WebSocket端点正常（`/ws`）
- [x] API文档可访问（`/docs`）

### 前端验收
- [x] 开发服务器可以启动（端口5173）
- [x] API配置已对齐后端
- [x] 超时配置正确（5分钟）
- [x] 环境变量配置正确

### 集成验收
- [ ] 前端可以连接到后端
- [ ] Agent分析功能正常工作（需要用户测试）
- [ ] 市场数据显示正常（需要用户测试）
- [ ] WebSocket连接正常（需要用户测试）
- [ ] 无CORS错误
- [ ] 响应数据格式正确

---

## 📚 相关文档

- **后端API文档**: http://localhost:8000/docs （后端启动后访问）
- **前端CLAUDE.md**: `frontend/CLAUDE.md`
- **后端实施报告**: `backend/docs/IMPLEMENTATION_REPORT.md`
- **API配置**: `frontend/src/config/api.config.ts`
- **Agent API客户端**: `frontend/src/api/agents.ts`
- **Market API客户端**: `frontend/src/api/market.ts`

---

## 🚀 下一步

1. **立即测试**: 按照上面的步骤启动前后端，测试基本功能
2. **前端UI开发**: 根据API响应完善前端UI展示
3. **添加更多端点**: Portfolio、Orders、Strategies等
4. **性能优化**: 添加缓存、流式API等
5. **部署准备**: Docker容器化、生产环境配置

---

**报告生成时间**: 2025-11-09
**实施人**: Claude Code
**项目**: HiddenGem Trading System
