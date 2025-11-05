# 🚀 HiddenGem 快速启动指南

**完成时间**: 2025-01-15
**当前分支**: `feature/tradingagents-backend`

---

## 📋 准备工作检查清单

- [x] ✅ 后端已清理（删除 Streamlit 前端）
- [x] ✅ 添加了 FastAPI Wrapper
- [x] ✅ 更新了依赖文件 (requirements.txt)
- [x] ✅ 更新了环境变量配置 (.env.example)
- [x] ✅ 前端 API 配置已指向 localhost:8000
- [x] ✅ Git 提交已完成

---

## 🎯 三步启动流程

### 步骤 1: 启动后端服务器 🖥️

#### 1.1 配置环境变量

```bash
# 进入后端目录
cd "D:\Program Files (x86)\CodeRepos\HiddenGem\reference\TradingAgents-CN"

# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API 密钥
# 必需：
#   - DASHSCOPE_API_KEY (阿里云通义千问)
#   - FINNHUB_API_KEY (美股数据)
# 可选：
#   - TUSHARE_TOKEN (A股数据)
```

**最小配置示例** (.env):
```bash
# LLM 配置
LLM_PROVIDER=dashscope
DEEP_THINK_LLM=qwen-plus
QUICK_THINK_LLM=qwen-turbo

# API 密钥（必需）
DASHSCOPE_API_KEY=sk-your-dashscope-key
FINNHUB_API_KEY=your-finnhub-key

# API 服务器
API_HOST=0.0.0.0
API_PORT=8000
```

#### 1.2 安装后端依赖

```bash
# 确保在后端目录
cd "D:\Program Files (x86)\CodeRepos\HiddenGem\reference\TradingAgents-CN"

# 安装依赖（如果尚未安装）
pip install -r requirements.txt

# 或使用国内镜像加速
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 1.3 启动后端服务

```bash
# 方式1: 使用启动脚本（推荐）
python start_api.py

# 方式2: 直接使用 uvicorn
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**成功标志**:
```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              TradingAgents-CN REST API Server                ║
║                                                              ║
║  API Documentation:  http://0.0.0.0:8000/docs               ║
║  Health Check:       http://0.0.0.0:8000/health             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
🚀 初始化 TradingAgents 系统...
✅ TradingAgents 系统初始化完成
INFO:     Application startup complete.
```

#### 1.4 验证后端运行

**新开一个终端**，运行测试脚本：

```bash
cd "D:\Program Files (x86)\CodeRepos\HiddenGem\reference\TradingAgents-CN"
python test_api.py
```

**预期输出**:
```
🚀==========================================================🚀
      TradingAgents-CN 后端 API 测试
🚀==========================================================🚀

============================================================
测试 1/3: 健康检查
============================================================
✅ 健康检查通过!
   状态: healthy
   服务: TradingAgents-CN API
   TradingGraph 已初始化: True

============================================================
测试 2/3: Agent 状态查询
============================================================
✅ Agent 状态查询成功!
   检测到 4 个 Agent:
   🟢 technical: 已启用
   🟢 fundamental: 已启用
   🟢 sentiment: 已启用
   🟢 policy: 已启用

============================================================
测试 3/3: 股票分析接口连通性
============================================================
✅ 股票分析端点: http://localhost:8000/api/v1/agents/analyze-all/NVDA
   接口格式正确，可以接受分析请求

🎉 所有测试通过！后端 API 工作正常。
```

**或手动测试**:
```bash
# 测试健康检查
curl http://localhost:8000/health

# 测试 Agent 状态
curl http://localhost:8000/api/v1/agents/status
```

---

### 步骤 2: 启动前端开发服务器 💻

#### 2.1 安装前端依赖

```bash
# 进入前端目录
cd "D:\Program Files (x86)\CodeRepos\HiddenGem\frontend"

# 安装依赖（如果尚未安装）
npm install
```

#### 2.2 验证前端配置

确认 `.env` 文件配置正确：

```bash
# frontend/.env 应该包含:
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_APP_NAME=HiddenGem Trading System
```

✅ **已配置完成！**

#### 2.3 启动前端服务

```bash
# 确保在前端目录
cd "D:\Program Files (x86)\CodeRepos\HiddenGem\frontend"

# 启动开发服务器
npm run dev
```

**成功标志**:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

---

### 步骤 3: 测试完整流程 🧪

#### 3.1 访问前端

在浏览器打开: **http://localhost:5173**

#### 3.2 执行股票分析测试

1. **导航到 Agents 页面**（或 Trading 页面）

2. **输入股票代码**:
   - 美股示例: `NVDA`, `AAPL`, `TSLA`
   - A股示例: `000001.SZ` (平安银行), `600036.SS` (招商银行)
   - 港股示例: `0700.HK` (腾讯), `9988.HK` (阿里巴巴)

3. **点击"开始分析"按钮**

4. **观察分析过程**:
   - ⏳ 前端显示 Loading 状态（约 30-60 秒）
   - 🔄 后端日志显示分析进度
   - ✅ 前端显示分析结果

#### 3.3 预期结果

**前端显示**:
```
分析完成: NVDA

📊 各 Agent 分析结果:
  🟢 技术分析 (technical): 看涨 (信心度: 75%)
  🟢 基本面分析 (fundamental): 看涨 (信心度: 75%)
  🟡 情绪分析 (sentiment): 持有 (信心度: 75%)
  🟢 政策分析 (policy): 看涨 (信心度: 75%)

💡 综合建议:
  方向: 做多 (long)
  信心度: 85%
  建议仓位: 10%
```

**后端日志**:
```
INFO:     "POST /api/v1/agents/analyze-all/NVDA HTTP/1.1" 200 OK
📊 开始分析: NVDA @ 2025-01-15
... (分析过程日志)
✅ 分析完成
```

---

## 🔍 故障排查

### 问题 1: 后端无法启动

**症状**: `python start_api.py` 报错

**解决方案**:

1. **检查依赖**:
   ```bash
   pip install fastapi uvicorn[standard] python-multipart
   ```

2. **检查环境变量**:
   ```bash
   # 确保 .env 文件存在且包含必需的 API 密钥
   cat .env | grep API_KEY
   ```

3. **查看详细错误**:
   ```bash
   # 使用 uvicorn 直接启动看详细日志
   uvicorn api.main:app --reload --log-level debug
   ```

---

### 问题 2: 前端无法连接后端

**症状**: 前端显示 "Network Error" 或 "Failed to fetch"

**解决方案**:

1. **验证后端运行**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **检查前端配置**:
   ```bash
   cat frontend/.env
   # 应该显示: VITE_API_BASE_URL=http://localhost:8000
   ```

3. **检查 CORS 设置**:
   后端 `api/main.py` 中应包含:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:5173", "http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

4. **重启前端**:
   ```bash
   # Ctrl+C 停止，然后重新启动
   npm run dev
   ```

---

### 问题 3: 股票分析超时

**症状**: 分析超过 2 分钟未返回

**可能原因**:
- LLM API 响应慢
- 网络问题
- API 密钥配额用完

**解决方案**:

1. **检查后端日志**，查看具体错误

2. **验证 API 密钥**:
   ```bash
   # 测试 DashScope API
   curl -H "Authorization: Bearer YOUR_API_KEY" \
        https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
   ```

3. **使用更快的模型**:
   修改 `.env`:
   ```bash
   DEEP_THINK_LLM=qwen-turbo  # 从 qwen-plus 改为 qwen-turbo
   QUICK_THINK_LLM=qwen-turbo
   ```

---

### 问题 4: 分析结果为空

**症状**: API 返回 200 但数据为空或错误

**解决方案**:

1. **检查股票代码格式**:
   - 美股: `AAPL` (不需要后缀)
   - A股: `000001.SZ` (深市) 或 `600036.SS` (沪市)
   - 港股: `0700.HK`

2. **查看后端完整日志**，了解 Agent 执行情况

3. **手动测试单个 Agent**（未实现，需等待后续开发）

---

## 📊 API 文档

### 在线文档

启动后端后访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 核心端点

```
GET  /health                            # 健康检查
GET  /api/v1/agents/status              # Agent 状态
POST /api/v1/agents/analyze-all/{symbol} # 完整分析
```

### 详细文档

参考: `reference/TradingAgents-CN/API_DOCUMENTATION.md`

---

## 📂 项目结构

```
HiddenGem/
├── frontend/                           # React 前端
│   ├── src/
│   │   ├── api/                        # ✅ 已配置连接后端
│   │   │   └── client.ts               # baseURL: http://localhost:8000
│   │   └── config/
│   │       └── api.config.ts           # API 配置
│   ├── .env                            # ✅ 已更新
│   └── package.json
└── reference/
    └── TradingAgents-CN/               # Python 后端
        ├── tradingagents/              # 核心 Agent 库
        ├── api/                        # ✅ FastAPI Wrapper
        │   ├── __init__.py
        │   └── main.py                 # FastAPI 应用 (272行)
        ├── start_api.py                # ✅ 启动脚本
        ├── test_api.py                 # ✅ 测试脚本
        ├── requirements.txt            # ✅ 已添加 fastapi
        ├── .env.example                # ✅ 已添加 API 配置
        └── API_DOCUMENTATION.md        # API 文档
```

---

## 🎉 成功标志

当看到以下情况时，说明一切正常：

- ✅ 后端日志显示: `✅ TradingAgents 系统初始化完成`
- ✅ 测试脚本输出: `🎉 所有测试通过！`
- ✅ 前端页面可以访问: http://localhost:5173
- ✅ 前端可以执行股票分析并显示结果

---

## 📞 需要帮助？

1. **查看 API 文档**: `API_DOCUMENTATION.md`
2. **查看完整报告**: `TRADINGAGENTS_BACKEND_INTEGRATION_REPORT.md`
3. **检查后端日志**: 终端输出
4. **检查浏览器控制台**: F12 → Console

---

## 🔄 Git 状态

**当前分支**: `feature/tradingagents-backend`

**提交历史**:
```bash
0117cdd - feat: 更新前端 API 配置指向 TradingAgents-CN 后端
0e82643 - docs: 添加 TradingAgents-CN 后端对接完成报告

# TradingAgents-CN 仓库:
7035778 - feat: 添加 FastAPI 依赖和 API 配置到环境变量
7d0f213 - docs: 添加精简的 REST API 文档供前端使用
3e42476 - feat: 添加极简 FastAPI wrapper (~240行)
8be480a - chore: 删除 Streamlit 前端和 CLI 工具
```

---

**最后更新**: 2025-01-15
**维护者**: HiddenGem Team
