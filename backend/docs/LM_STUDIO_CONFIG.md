# LM Studio 本地服务器配置指南

## 📋 配置摘要

已成功配置 TradingAgents-CN 使用 LM Studio 本地服务器。

### ✅ 配置更改

在 `.env` 文件中进行了以下更改：

```bash
# LLM提供商 (使用 LM Studio 本地服务器)
LLM_PROVIDER=openai

# LM Studio 服务器地址
BACKEND_URL=http://127.0.0.1:1234/v1

# 模型名称 (两个配置使用同一个模型，因为LM Studio一次只能加载一个)
DEEP_THINK_LLM=Qwen/Qwen3-30B-A3B-Instruct-2507
QUICK_THINK_LLM=Qwen/Qwen3-30B-A3B-Instruct-2507

# API Key (LM Studio 本地服务器不验证，但 LangChain 需要此变量存在)
OPENAI_API_KEY=lm-studio
```

## 🔧 前置条件

### 1. 启动 LM Studio 服务器

确保 LM Studio 已启动并在端口 1234 上运行：

1. 打开 LM Studio
2. 加载模型：`Qwen/Qwen3-30B-A3B-Instruct-2507`
3. 切换到 "Server" 标签页
4. 点击 "Start Server"
5. 确认服务器运行在 `http://127.0.0.1:1234`

### 2. 验证服务器状态

在浏览器中访问：
- http://127.0.0.1:1234/v1/models

应该能看到已加载的模型列表。

## 🧪 测试配置

### 方法 1: 使用测试脚本

```bash
# 激活虚拟环境
cd "D:\Program Files (x86)\CodeRepos\HiddenGem\reference\TradingAgents-CN"
.\venv\Scripts\activate

# 运行测试脚本
python test_lm_studio.py
```

### 方法 2: 使用 curl 测试

```bash
# 测试服务器健康状态
curl http://127.0.0.1:1234/v1/models

# 测试聊天完成
curl http://127.0.0.1:1234/v1/chat/completions ^
  -H "Content-Type: application/json" ^
  -d "{\"model\": \"Qwen/Qwen3-30B-A3B-Instruct-2507\", \"messages\": [{\"role\": \"user\", \"content\": \"你好\"}]}"
```

## 📝 重要说明

### 1. 模型名称匹配

**关键**: 确保 `.env` 中的模型名称与 LM Studio 加载的模型名称**完全一致**。

- 在 LM Studio 中查看已加载的模型名称
- 模型名称可能是：
  - `Qwen/Qwen3-30B-A3B-Instruct-2507` (完整路径)
  - `qwen3-30b-a3b-instruct-2507` (简化名称)
  - 或其他自定义名称

如果模型名称不匹配，调用会失败。

### 2. 单模型限制

由于 LM Studio 一次只能加载一个模型，系统的 `DEEP_THINK_LLM` 和 `QUICK_THINK_LLM` 配置为**同一个模型**。

这意味着：
- ✅ 系统仍然可以正常工作
- ⚠️ 但深度思考和快速思考会使用相同的模型和参数
- 💡 如果需要使用不同模型，需要在分析前手动在 LM Studio 中切换模型

### 3. 性能考虑

使用本地模型的优势：
- ✅ 无需网络连接
- ✅ 无 API 调用限制
- ✅ 数据隐私保护
- ✅ 无需付费

潜在限制：
- ⚠️ 推理速度取决于本地硬件
- ⚠️ 30B 模型需要较大显存 (建议 24GB+ VRAM)
- ⚠️ 单模型配置可能影响某些高级功能

### 4. API 兼容性

LM Studio 提供 OpenAI 兼容的 API，但可能存在细微差异：
- 某些 OpenAI 特有的参数可能不支持
- 响应格式通常兼容，但可能有小差异
- 如遇到问题，检查 LM Studio 的日志

## 🚀 使用示例

### 启动 API 服务器

```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 启动 FastAPI 服务器
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 分析股票

```bash
# 方法 1: 使用 Python 脚本 (假设存在)
python -m tradingagents.cli analyze 000001.SZ

# 方法 2: 通过 API
curl -X POST "http://localhost:8000/api/v1/agents/analyze-all/000001.SZ" ^
  -H "Content-Type: application/json"
```

## 🔍 故障排查

### 问题 1: 连接被拒绝

```
Error: Connection refused to http://127.0.0.1:1234
```

**解决方案**:
1. 确认 LM Studio 服务器已启动
2. 检查端口是否为 1234
3. 尝试访问 http://127.0.0.1:1234/v1/models

### 问题 2: 模型未找到

```
Error: Model 'Qwen/Qwen3-30B-A3B-Instruct-2507' not found
```

**解决方案**:
1. 在 LM Studio 中检查已加载的模型名称
2. 访问 http://127.0.0.1:1234/v1/models 获取准确名称
3. 更新 `.env` 文件中的 `DEEP_THINK_LLM` 和 `QUICK_THINK_LLM`

### 问题 3: 响应超时

```
Error: Request timeout
```

**解决方案**:
1. 检查本地硬件性能（GPU/CPU 使用率）
2. 尝试使用更小的模型
3. 增加超时时间（在 `tradingagents/graph/trading_graph.py` 中调整 `timeout` 参数）

### 问题 4: API Key 错误

```
Error: Invalid API key
```

**解决方案**:
1. 检查 LM Studio 是否要求 API key
2. 在 LM Studio 设置中禁用 API key 验证
3. 或在 `.env` 中设置正确的 API key

## 📚 参考资料

- [LM Studio 官方文档](https://lmstudio.ai/docs)
- [LangChain OpenAI 集成](https://python.langchain.com/docs/integrations/chat/openai)
- [TradingAgents-CN README](./README.md)
- [环境变量示例](./.env.example)

## 🔄 在本地模型和云端服务之间切换

`.env` 文件中已经配置了两种方案，方便快速切换：

### 切换到 LM Studio 本地服务器

```bash
# 在 .env 文件中，确保以下配置未被注释：
LLM_PROVIDER=openai
BACKEND_URL=http://127.0.0.1:1234/v1
DEEP_THINK_LLM=Qwen/Qwen3-30B-A3B-Instruct-2507
QUICK_THINK_LLM=Qwen/Qwen3-30B-A3B-Instruct-2507

# 并注释掉 SiliconFlow 配置：
# LLM_PROVIDER=siliconflow
# BACKEND_URL=https://api.siliconflow.cn/v1
# ...
```

### 切换到 SiliconFlow 云端服务

```bash
# 在 .env 文件中，注释掉 LM Studio 配置：
# LLM_PROVIDER=openai
# BACKEND_URL=http://127.0.0.1:1234/v1
# ...

# 取消注释 SiliconFlow 配置：
LLM_PROVIDER=siliconflow
BACKEND_URL=https://api.siliconflow.cn/v1
DEEP_THINK_LLM=Qwen/Qwen3-30B-A3B-Thinking-2507
QUICK_THINK_LLM=Qwen/Qwen3-30B-A3B-Instruct-2507
# 确保 SILICONFLOW_API_KEY 已配置
```

### 快速切换脚本

你也可以创建批处理脚本快速切换：

**切换到本地 (switch_to_local.bat)**
```batch
@echo off
echo Switching to LM Studio local server...
:: 这里可以添加自动修改.env的逻辑
echo Please manually update .env file to use LM_PROVIDER=openai
pause
```

**切换到云端 (switch_to_cloud.bat)**
```batch
@echo off
echo Switching to SiliconFlow cloud service...
:: 这里可以添加自动修改.env的逻辑
echo Please manually update .env file to use LM_PROVIDER=siliconflow
pause
```

---

**最后更新**: 2025-01-08
**配置环境**: Windows, LM Studio, Qwen3-30B 模型
