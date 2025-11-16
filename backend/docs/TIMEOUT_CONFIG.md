# Timeout配置优化

## 问题描述

当LLM API响应慢（网络拥堵、模型推理慢）时，系统会超时，导致分析失败。

## 解决方案

将所有timeout从10分钟增加到5分钟。

## 修改内容

### 1. 后端LLM初始化timeout

**文件**: `tradingagents/graph/trading_graph.py`

**修改**: 将所有LLM提供商的timeout从`600.0`秒增加到`300.0`秒

```python
# 修改前
timeout=600.0  # 600秒超时（10分钟）

# 修改后
timeout=300.0  # 300秒超时（5分钟）
```

影响的LLM提供商：
- OpenAI
- SiliconFlow
- OpenRouter
- Ollama
- Anthropic
- Google AI
- DashScope (阿里百炼)
- DeepSeek
- Custom OpenAI

### 2. Risk Manager LLM调用timeout

**文件**: `tradingagents/agents/managers/risk_manager.py`

**修改**: 增加future.result()的timeout

```python
# 修改前
response = future.result(timeout=600)  # 600秒超时（10分钟）

# 修改后
response = future.result(timeout=300)  # 300秒超时（5分钟）
```

### 3. 前端HTTP请求timeout

**文件**: `frontend/src/config/api.config.ts`

**修改**: 增加longTimeout

```typescript
// 修改前
longTimeout: 360000,  // 6分钟

// 修改后
longTimeout: 300000,  // 5分钟
```

## Timeout配置总览

| 层级 | 组件 | 原timeout | 新timeout | 说明 |
|------|------|-----------|-----------|------|
| 后端 | LLM初始化 | 600秒 (10分钟) | 300秒 (5分钟) | 单次LLM调用超时 |
| 后端 | Risk Manager | 600秒 (10分钟) | 300秒 (5分钟) | Risk Manager的LLM调用 |
| 前端 | HTTP请求 | 360秒 (6分钟) | 300秒 (5分钟) | 长时间操作的HTTP请求 |

## 推荐的Timeout配置策略

### 根据场景选择timeout

1. **网络快 + 模型快** (OpenAI GPT-4, Claude等云服务)
   - LLM timeout: 180秒 (3分钟)
   - 前端 longTimeout: 180秒 (3分钟)

2. **网络一般 + 模型一般** (国内云服务) ⬅️ **当前配置**
   - LLM timeout: 300秒 (5分钟)
   - 前端 longTimeout: 300秒 (5分钟)

3. **网络慢 + 模型慢** (本地模型、网络不稳定)
   - LLM timeout: 600秒 (10分钟)
   - 前端 longTimeout: 600秒 (10分钟)

4. **极端情况** (本地大模型、弱网环境)
   - LLM timeout: 900秒 (15分钟)
   - 前端 longTimeout: 900秒 (15分钟)

### 如何调整timeout

#### 方法1：直接修改代码（已完成）

修改3个文件中的timeout值即可。

#### 方法2：通过环境变量配置（推荐）

未来可以改进为通过环境变量配置：

```bash
# .env
LLM_TIMEOUT=900  # 秒
API_LONG_TIMEOUT=900000  # 毫秒
```

## 注意事项

1. **timeout太短**：
   - ❌ LLM还没生成完就超时
   - ❌ 前端提前放弃等待
   - ❌ 浪费已经完成的计算

2. **timeout太长**：
   - ⚠️ 遇到真正的错误时，要等很久才能知道
   - ⚠️ 用户体验差（长时间没反应）
   - ⚠️ 资源占用时间长

3. **最佳实践**：
   - ✅ 使用**流式API** (SSE) 代替长timeout
   - ✅ 实时显示进度，用户知道系统在工作
   - ✅ 即使超时也能看到中间结果

## 流式API的优势

相比增加timeout，使用流式API是更好的解决方案：

```typescript
// 流式API示例
analyzeWithAllAgentsStream('NVDA', {
  onStart: (event) => console.log('开始分析'),
  onProgress: (event) => {
    console.log(`[${event.agent}] ${event.message} - ${event.progress}%`);
    // 实时更新UI进度条
  },
  onComplete: (data) => {
    console.log('分析完成');
    // 显示最终结果
  },
  onError: (error) => console.error('分析失败:', error)
});
```

**优势**：
- ✅ 不需要担心timeout（始终有数据流）
- ✅ 实时显示进度（用户不会以为卡死）
- ✅ 可以提前看到部分结果
- ✅ 网络断开后可以恢复
- ✅ 更好的用户体验

## 测试建议

### 测试1：正常网络环境

```bash
# 应该在15分钟内完成
curl -X POST http://localhost:8000/api/v1/agents/analyze-all/300502 \
  -H "Content-Type: application/json" \
  -w "\n总耗时: %{time_total}秒\n"
```

### 测试2：慢网络环境

模拟慢网络测试timeout是否生效：

```bash
# 使用tc命令限速（Linux）
sudo tc qdisc add dev eth0 root netem delay 1000ms

# 运行分析
curl -X POST http://localhost:8000/api/v1/agents/analyze-all/300502

# 恢复网络
sudo tc qdisc del dev eth0 root
```

### 测试3：流式API

```bash
# 使用curl测试SSE
curl -N http://localhost:8000/api/v1/agents/analyze-all-stream/300502
```

## 版本信息

- **修改日期**: 2025-11-08
- **修改原因**: LLM API响应慢导致超时
- **修改范围**: 后端LLM、Risk Manager、前端HTTP请求
- **兼容性**: 向后兼容，不影响现有功能

## 相关文件

- `tradingagents/graph/trading_graph.py` - LLM初始化
- `tradingagents/agents/managers/risk_manager.py` - Risk Manager
- `frontend/src/config/api.config.ts` - 前端配置
- `docs/TIMEOUT_CONFIG.md` - 本文档
