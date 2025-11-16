# Timeout 配置修改记录

## 📋 修改摘要

为支持本地LLM推理（如LM Studio），已将所有关键的timeout设置从60秒增加到600秒（10分钟）。

**修改日期**: 2025-01-08
**原因**: 本地模型推理速度较慢，需要更长的超时时间

## ✅ 修改详情

### 1. LLM初始化超时 - `tradingagents/graph/trading_graph.py`

修改了所有LLM provider的初始化timeout配置，从默认的60秒增加到600秒：

#### 1.1 OpenAI Provider (行73-83)
```python
# 用于 LM Studio 本地服务器
self.deep_thinking_llm = ChatOpenAI(
    model=self.config["deep_think_llm"],
    base_url=self.config["backend_url"],
    timeout=600.0  # 600秒超时（10分钟）- 本地模型推理较慢
)
self.quick_thinking_llm = ChatOpenAI(
    model=self.config["quick_think_llm"],
    base_url=self.config["backend_url"],
    timeout=600.0  # 600秒超时（10分钟）- 本地模型推理较慢
)
```

#### 1.2 SiliconFlow Provider (行97-114)
```python
base_deep_llm = ChatOpenAI(
    ...
    timeout=600.0  # 从 60.0 增加到 600.0
)
base_quick_llm = ChatOpenAI(
    ...
    timeout=600.0  # 从 60.0 增加到 600.0
)
```

#### 1.3 OpenRouter Provider (行129-140)
```python
self.deep_thinking_llm = ChatOpenAI(
    ...
    timeout=600.0  # 新增
)
self.quick_thinking_llm = ChatOpenAI(
    ...
    timeout=600.0  # 新增
)
```

#### 1.4 Ollama Provider (行142-151)
```python
self.deep_thinking_llm = ChatOpenAI(
    ...
    timeout=600.0  # 新增
)
self.quick_thinking_llm = ChatOpenAI(
    ...
    timeout=600.0  # 新增
)
```

#### 1.5 Anthropic Provider (行153-162)
```python
self.deep_thinking_llm = ChatAnthropic(
    ...
    timeout=600.0  # 新增
)
self.quick_thinking_llm = ChatAnthropic(
    ...
    timeout=600.0  # 新增
)
```

#### 1.6 Google Provider (行170-185)
```python
self.deep_thinking_llm = ChatGoogleOpenAI(
    ...
    timeout=600.0  # 新增
)
self.quick_thinking_llm = ChatGoogleOpenAI(
    ...
    timeout=600.0  # 新增
)
```

#### 1.7 DashScope Provider (行194-205)
```python
self.deep_thinking_llm = ChatDashScopeOpenAI(
    ...
    timeout=600.0  # 新增
)
self.quick_thinking_llm = ChatDashScopeOpenAI(
    ...
    timeout=600.0  # 新增
)
```

#### 1.8 DeepSeek Provider (行219-234)
```python
self.deep_thinking_llm = ChatDeepSeek(
    ...
    timeout=600.0  # 新增
)
self.quick_thinking_llm = ChatDeepSeek(
    ...
    timeout=600.0  # 新增
)
```

#### 1.9 Custom OpenAI Provider (行250-265)
```python
self.deep_thinking_llm = create_openai_compatible_llm(
    ...
    timeout=600.0  # 新增
)
self.quick_thinking_llm = create_openai_compatible_llm(
    ...
    timeout=600.0  # 新增
)
```

#### 1.10 Qianfan Provider (行273-286)
```python
self.deep_thinking_llm = create_openai_compatible_llm(
    ...
    timeout=600.0  # 新增
)
self.quick_thinking_llm = create_openai_compatible_llm(
    ...
    timeout=600.0  # 新增
)
```

### 2. Risk Manager超时 - `tradingagents/agents/managers/risk_manager.py`

#### 2.1 LLM调用超时 (行217-220)
```python
# 从 60秒 增加到 600秒
response = future.result(timeout=600)  # 600秒超时（10分钟）
```

### 3. API流式处理超时 - `api/main.py`

#### 3.1 流式响应总超时 (行1137)
```python
# 从 600 (60秒) 增加到 6000 (600秒)
max_empty_count = 6000  # 600秒超时（0.1s * 6000）
```

#### 3.2 后台线程等待超时 (行1258)
```python
# 从 5秒 增加到 30秒
thread.join(timeout=30)
```

## 📊 修改统计

| 文件 | 修改项数 | 说明 |
|------|---------|------|
| `tradingagents/graph/trading_graph.py` | 20处 | 所有LLM provider的timeout配置 |
| `tradingagents/agents/managers/risk_manager.py` | 2处 | Risk Manager的LLM调用timeout |
| `api/main.py` | 2处 | 流式API的超时配置 |
| **总计** | **24处** | |

## 🔍 未修改的Timeout

以下timeout设置**未修改**，因为它们是数据层的超时，与LLM推理无关：

- `tradingagents/dataflows/akshare_utils.py` - 数据获取timeout (30-60秒)
- `tradingagents/dataflows/chinese_finance_utils.py` - 线程等待timeout (60秒)
- `tradingagents/dataflows/db_cache_manager.py` - Redis连接timeout (5秒)
- `tradingagents/dataflows/googlenews_utils.py` - HTTP请求timeout (10-30秒)
- `tradingagents/dataflows/hk_stock_utils.py` - 请求timeout (60秒)

这些timeout保持原值是合理的，因为：
1. 数据库连接不应需要600秒
2. HTTP请求不应需要600秒
3. 这些是数据获取的超时，不是LLM推理的超时

## 💡 使用建议

### 本地模型 (LM Studio, Ollama)
- ✅ 600秒timeout足够使用
- 💡 如果模型特别大（>70B），可能需要进一步增加

### 云端API (OpenAI, DeepSeek等)
- ✅ 600秒timeout远超所需
- 💡 云端API通常在5-30秒内完成，600秒是保守配置

### 调整Timeout的方法

如需修改timeout，只需在对应的LLM初始化处修改`timeout`参数：

```python
# 示例：修改为300秒（5分钟）
self.deep_thinking_llm = ChatOpenAI(
    ...
    timeout=300.0
)
```

## ⚠️ 注意事项

1. **内存管理**: 长时间运行可能占用较多内存，注意监控
2. **并发限制**: 多个请求同时运行时，总等待时间会更长
3. **错误重试**: 部分provider有重试机制，实际总时间可能更长
4. **网络问题**: 网络不稳定时，可能仍会触发timeout

## 🧪 测试建议

测试timeout配置是否生效：

```python
# 使用测试脚本验证
python test_lm_studio.py

# 运行完整分析测试timeout
python -m tradingagents.cli analyze 000001.SZ
```

## 📚 相关文档

- [LM Studio配置指南](./LM_STUDIO_CONFIG.md)
- [环境变量配置](./.env.example)
- [API文档](./API.md)

---

**最后更新**: 2025-01-08
**影响范围**: 所有LLM调用
**兼容性**: 向后兼容，不影响现有功能
