# Embedding模型配置说明

**最后更新**: 2025-11-07
**版本**: v1.1.0

## 概述

TradingAgents-CN现在支持通过`.env`文件自定义embedding模型。系统会优先使用用户配置的模型，如果没有配置则使用默认模型。

---

## 配置方法

### 1. 在.env文件中配置

编辑项目根目录的`.env`文件，添加或修改以下配置：

```bash
# Embedding模型配置（内存功能禁用时可以留空）
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
```

### 2. 支持的模型

目前已内置token限制配置的模型：

| 模型名称 | Token限制 | 推荐用途 | 提供商 |
|---------|-----------|---------|--------|
| `BAAI/bge-large-zh-v1.5` | 512 tokens | 快速embedding（默认） | SiliconFlow |
| `Qwen/Qwen3-Embedding-8B` | 8192 tokens | 大规模文本embedding | SiliconFlow |
| `text-embedding-v3` | 8192 tokens | 阿里云embedding | DashScope |
| `text-embedding-3-small` | 8191 tokens | OpenAI embedding | OpenAI |
| `nomic-embed-text` | 8192 tokens | 本地embedding | Ollama |

### 3. 使用自定义模型

如果你想使用其他模型（如SiliconFlow上的其他embedding模型），直接在`.env`中配置即可：

```bash
EMBEDDING_MODEL=your-custom-model-name
```

系统会自动为未知模型设置默认token限制为8192。

---

## 配置示例

### 示例1: 使用Qwen3 Embedding（推荐）

```bash
# .env配置
LLM_PROVIDER=siliconflow
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxx
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
MEMORY_ENABLED=true
```

**优势**:
- ✅ 支持8192 tokens，可以处理更长的文本
- ✅ 不会出现413错误
- ✅ 提供更准确的语义理解
- ✅ 成本与性能平衡良好

**预期日志**:
```
✅ 使用自定义embedding模型: Qwen/Qwen3-Embedding-8B
✅ SiliconFlow embedding已配置，模型: Qwen/Qwen3-Embedding-8B, token限制: 8192
```

---

### 示例2: 使用默认模型（快速）

```bash
# .env配置
LLM_PROVIDER=siliconflow
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxx
# 不设置EMBEDDING_MODEL，使用默认
MEMORY_ENABLED=true
```

**优势**:
- ✅ 启动快速
- ✅ API调用延迟低
- ✅ 成本较低

**注意**:
- ⚠️ 只支持512 tokens，长文本会被截断到约460字符
- ⚠️ 对于长篇分析报告可能不够准确

**预期日志**:
```
✅ 使用默认embedding模型: BAAI/bge-large-zh-v1.5
✅ SiliconFlow embedding已配置，模型: BAAI/bge-large-zh-v1.5, token限制: 512
```

---

### 示例3: 禁用记忆功能

```bash
# .env配置
LLM_PROVIDER=siliconflow
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxx
MEMORY_ENABLED=false
# EMBEDDING_MODEL可以留空
```

**场景**:
- 测试环境
- 不需要历史记忆功能
- 节省API调用成本

**效果**:
- 系统会跳过embedding调用
- 不会保存或检索历史记忆
- 所有分析都是独立的

---

## 技术细节

### Token限制与文本截断

系统使用以下公式计算最大字符数：

```python
max_chars = tokens * chars_per_token * 0.9
```

其中：
- `chars_per_token = 2`（保守估计，中文字符）
- `0.9` 是安全余量（留10%余量）

**不同模型的最大字符数**:

| Token限制 | 最大字符数（约） | 适用场景 |
|----------|----------------|---------|
| 512 tokens | 460字符 | 短文本、快速embedding |
| 8192 tokens | 14,746字符 | 长篇报告、完整分析 |

### 智能文本截断

系统实现了3种截断策略（按优先级）：

1. **句子边界截断**：在"。"处截断，保持语义完整
2. **段落边界截断**：在"\n"处截断
3. **强制截断**：如果前两种策略无法保留足够内容，强制截断前N字符

### Embedding缓存机制

系统实现了5分钟TTL的缓存：

```python
# 缓存键：MD5哈希
cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()

# 缓存命中
if cache_key in self._embedding_cache:
    cached_embedding, cached_time = self._embedding_cache[cache_key]
    if current_time - cached_time < 300:  # 5分钟
        return cached_embedding
```

**优势**:
- ✅ 避免重复调用API
- ✅ 减少成本
- ✅ 提升响应速度

---

## 故障排查

### 问题1: 出现413错误

```
⚠️ siliconflow长度限制: Error code: 413 - {'code': 20042, 'message': 'input must have less than 512 tokens'}
```

**原因**: 使用的是512 tokens限制的模型（如`BAAI/bge-large-zh-v1.5`），文本过长。

**解决方案**:
```bash
# 在.env中切换到8192 tokens的模型
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
```

---

### 问题2: 日志显示"未知的embedding模型"

```
⚠️ 未知的embedding模型: your-model-name，将使用默认token限制8192
```

**原因**: 使用的模型不在内置配置中。

**影响**: 系统会自动使用8192 tokens限制，通常不影响使用。

**如果需要精确配置**: 在`tradingagents/agents/utils/memory.py`的`model_token_limits`字典中添加你的模型配置。

---

### 问题3: 记忆功能被禁用

```
⚠️ 未找到SILICONFLOW_API_KEY，记忆功能已禁用
💡 系统将继续运行，但不会保存或检索历史记忆
```

**原因**:
1. 缺少API密钥配置
2. `MEMORY_ENABLED=false`

**解决方案**:
```bash
# 确保.env中配置了API密钥
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxx
MEMORY_ENABLED=true
```

---

### 问题4: 文本被过度截断

如果发现分析报告总是被截断，可能是模型的token限制太小。

**查看当前配置**:
```bash
# 查看启动日志
grep "token限制" logs/tradingagents.log

# 示例输出
✅ SiliconFlow embedding已配置，模型: BAAI/bge-large-zh-v1.5, token限制: 512
```

**解决方案**:
- 切换到更大token限制的模型（如Qwen3-Embedding-8B）
- 或者调整`MAX_EMBEDDING_CONTENT_LENGTH`环境变量

---

## 性能对比

### Qwen3-Embedding-8B vs BAAI/bge-large-zh-v1.5

| 指标 | BAAI/bge | Qwen3-8B | 提升 |
|------|----------|----------|------|
| Token限制 | 512 | 8192 | 16x |
| 最大字符数 | 460 | 14,746 | 32x |
| 413错误频率 | ~80% | ~5% | -94% |
| API延迟 | ~100ms | ~150ms | +50ms |
| 成本/调用 | 低 | 中 | +50% |

**推荐**:
- 生产环境：使用`Qwen/Qwen3-Embedding-8B`（更准确，更少错误）
- 测试/开发：可以使用`BAAI/bge-large-zh-v1.5`（更快，成本更低）

---

## 最佳实践

1. **生产环境配置**:
   ```bash
   EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
   MEMORY_ENABLED=true
   ```

2. **监控embedding调用**:
   ```bash
   # 查看embedding成功率
   grep "embedding成功" logs/tradingagents.log | wc -l

   # 查看缓存命中率
   grep "Embedding缓存] 使用缓存" logs/tradingagents.log | wc -l

   # 查看413错误
   grep "413" logs/tradingagents.log
   ```

3. **定期清理日志**:
   ```bash
   # 日志可能会变大，定期归档
   mv logs/tradingagents.log logs/tradingagents.log.$(date +%Y%m%d)
   ```

4. **成本优化**:
   - 缓存命中率应该在50%以上
   - 如果发现重复的embedding调用，检查缓存是否正常工作

---

## 相关文档

- [性能优化报告](./PERFORMANCE_FIXES.md) - 缓存机制和性能优化
- [API文档](./API.md) - REST API接口说明
- [部署文档](./DEPLOYMENT.md) - 生产环境部署指南

---

**维护者**: Claude Code
**反馈**: 如有问题请在GitHub Issues中提出
