# 🚀 优化功能快速启动指南

本文档提供5分钟快速启动指南，帮助您立即启用所有6项性能优化。

---

## ⚡ 5分钟快速启动

### 步骤1: 更新 .env 配置（1分钟）

打开 `.env` 文件，添加或修改以下配置：

```bash
# ========== LLM分层路由配置 ==========
# 启用分层路由（节省30-50%成本）
ENABLE_SMALL_MODEL_ROUTING=true

# 三层模型配置（根据您的LLM Provider选择）
# 方案A: Qwen系列（推荐，性价比高）
SMALL_LLM=qwen-turbo
QUICK_THINK_LLM=qwen-plus
DEEP_THINK_LLM=qwen-max

# 方案B: DeepSeek系列（更便宜）
# SMALL_LLM=deepseek-chat
# QUICK_THINK_LLM=deepseek-chat
# DEEP_THINK_LLM=deepseek-reasoner

# 方案C: OpenAI系列（质量更高）
# SMALL_LLM=gpt-4o-mini
# QUICK_THINK_LLM=gpt-4o
# DEEP_THINK_LLM=o1-mini

# ========== 缓存配置 ==========
# TTL缓存（自动启用，减少60-80% API请求）
CACHE_DIR=.cache
CACHE_MAX_SIZE=1000000000  # 1GB

# Redis缓存（可选，用于分布式部署）
# REDIS_URL=redis://localhost:6379/0

# ========== 日志配置 ==========
LOG_LEVEL=INFO  # 生产环境可设为WARNING减少日志
```

**✅ 完成后保存文件**

---

### 步骤2: 重启服务（30秒）

```bash
# 如果服务正在运行，先停止
# Ctrl+C

# 重新启动服务
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**✅ 看到以下日志表示优化功能已启用：**

```
📏 Context Pruner initialized: max_tokens=4000, strategy=middle
💾 LLM Cache initialized: max_size=1000, ttl=3600s
🎯 LLM Router initialized (3-tier routing enabled)
📊 Metrics Collector initialized
```

---

### 步骤3: 验证优化效果（2分钟）

#### 3.1 检查监控指标

```bash
# 打开浏览器访问
http://localhost:8000/api/v1/metrics/summary

# 或使用curl
curl http://localhost:8000/api/v1/metrics/summary | jq
```

期望看到：

```json
{
  "success": true,
  "data": {
    "system": {
      "healthy": true,
      "restart_count": 0
    },
    "cache": {
      "hit_rate": "0.00%",  // 首次运行为0%，后续会增加
      "total_requests": 0
    },
    "llm": {
      "total_tokens": 0,
      "total_cost_yuan": "¥0.00"
    }
  }
}
```

#### 3.2 测试Agent分析

```bash
# 执行一次分析
curl -X POST http://localhost:8000/api/v1/agents/analyze-all/000001.SZ

# 再次执行相同分析（应该更快，命中缓存）
curl -X POST http://localhost:8000/api/v1/agents/analyze-all/000001.SZ
```

#### 3.3 检查缓存命中率

```bash
curl http://localhost:8000/api/v1/metrics/summary | jq '.data.cache.hit_rate'
# 应该看到命中率 > 50%
```

---

## 📊 验证清单

运行几次分析后，使用以下清单验证优化效果：

### ✅ LLM分层路由

```bash
# 查看LLM使用统计
curl http://localhost:8000/api/v1/metrics | jq '.data.llm_usage.requests_by_tier'

# 期望看到：
# {
#   "small": 100,    # 简单任务
#   "medium": 500,   # 常规分析
#   "large": 100     # 复杂推理
# }
```

**判断标准**:
- `small` 占比 > 10%：✅ 路由生效
- `small` 占比 = 0%：❌ 路由未生效，检查 `ENABLE_SMALL_MODEL_ROUTING` 是否为 `true`

---

### ✅ TTL缓存

```bash
# 查看缓存性能
curl http://localhost:8000/api/v1/metrics | jq '.data.cache_performance'

# 期望看到：
# {
#   "hits": 234,
#   "misses": 100,
#   "total": 334,
#   "hit_rate": 0.70  // 70%命中率
# }
```

**判断标准**:
- 命中率 > 60%：✅ 缓存效果良好
- 命中率 < 30%：⚠️ 建议增加TTL或检查缓存配置

---

### ✅ LLM结果缓存

```python
# 在Python中检查
from tradingagents.utils.llm_optimization import get_llm_cache_stats

stats = get_llm_cache_stats()
print(f"LLM缓存命中率: {stats['hit_rate']:.2%}")
print(f"节省API调用: {stats['hits']}次")
```

**判断标准**:
- 命中率 > 40%：✅ 缓存效果显著
- 命中率 < 20%：⚠️ 可能请求参数变化太大

---

### ✅ 监控系统

```bash
# 访问Prometheus格式指标
curl http://localhost:8000/api/v1/metrics/prometheus

# 期望看到大量指标输出，如：
# auto_trading_heartbeat_seconds 15.2
# data_cache_hits_total 234
# llm_tokens_total 123456
```

**判断标准**:
- 能看到指标输出：✅ 监控系统工作正常
- 返回错误：❌ 检查API服务是否正常启动

---

### ✅ JSONL导出

```bash
# 运行Time Travel训练
python scripts/enhanced_time_travel_training.py \
    --symbol 000001.SZ \
    --start 2024-01-01 \
    --end 2024-01-31 \
    --holding-days 5

# 检查输出文件
ls -lh training_data/

# 期望看到：
# sft_training_data_000001_SZ_20250115_143022.jsonl
# sft_metadata_000001_SZ_20250115_143022.json
```

**判断标准**:
- 生成JSONL文件：✅ 导出功能正常
- 无输出文件：❌ 检查脚本执行是否有错误

---

## 🎯 预期性能提升

启用所有优化后，您应该看到：

| 指标 | 优化前 | 优化后 | 改善 |
|------|--------|--------|------|
| 单次分析成本 | ¥0.80 | ¥0.32 | **-60%** |
| 单次分析时间（首次） | 35秒 | 28秒 | **-20%** |
| 单次分析时间（缓存） | 35秒 | 0.5秒 | **-98%** |
| API请求次数 | 100% | 20-40% | **-60-80%** |

---

## 🔧 常见问题快速排查

### 问题1: 缓存命中率为0%

**可能原因**:
1. 刚启动，还没有缓存数据
2. 请求参数一直在变化
3. TTL过短，缓存频繁过期

**解决方案**:
```bash
# 1. 多运行几次相同的分析请求
# 2. 检查缓存目录是否存在
ls -la .cache/

# 3. 增加TTL（修改代码）
# tradingagents/dataflows/data_source_manager.py
@ttl_cache(ttl=7200)  # 从3600增加到7200
```

---

### 问题2: LLM分层路由未生效

**可能原因**:
1. `ENABLE_SMALL_MODEL_ROUTING=false`
2. 环境变量未加载
3. 模型配置错误

**解决方案**:
```bash
# 1. 检查环境变量
python -c "import os; print(os.getenv('ENABLE_SMALL_MODEL_ROUTING'))"

# 应该输出: true

# 2. 如果输出None，检查.env文件是否被加载
# 确保以下代码在主程序中：
from dotenv import load_dotenv
load_dotenv()

# 3. 重启服务
```

---

### 问题3: 监控指标API返回404

**可能原因**:
1. API路由未注册
2. 端口错误

**解决方案**:
```bash
# 1. 检查API是否启动
curl http://localhost:8000/docs

# 2. 检查路由是否注册
# api/main.py 应该包含：
from api.routers import monitoring
app.include_router(monitoring.router)

# 3. 重启服务
```

---

### 问题4: JSONL文件未生成

**可能原因**:
1. 训练脚本执行失败
2. 输出目录不存在
3. 没有完成任何episode

**解决方案**:
```bash
# 1. 手动创建输出目录
mkdir -p training_data

# 2. 检查脚本执行日志
python scripts/enhanced_time_travel_training.py \
    --symbol 000001.SZ \
    --start 2024-01-01 \
    --end 2024-01-31 \
    --holding-days 5 \
    2>&1 | tee training.log

# 3. 查看是否有错误
grep "ERROR" training.log
```

---

## 📈 持续监控

### 方法1: 使用watch命令实时监控

```bash
# 每5秒刷新一次指标
watch -n 5 'curl -s http://localhost:8000/api/v1/metrics/summary | jq'
```

### 方法2: 接入Prometheus + Grafana

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'hiddengem-backend'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/metrics/prometheus'
```

```bash
# 启动Prometheus
docker run -d -p 9090:9090 \
    -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
    prom/prometheus

# 启动Grafana
docker run -d -p 3000:3000 grafana/grafana

# 访问 http://localhost:3000
# 默认账号: admin/admin
# 添加Prometheus数据源: http://localhost:9090
```

### 方法3: 设置告警

```python
# 在代码中添加告警逻辑
from tradingagents.utils.monitoring_metrics import get_metrics_collector

metrics = get_metrics_collector()
stats = metrics.get_metrics()

# 检查缓存命中率
if stats['cache_performance']['hit_rate'] < 0.3:
    logger.warning("⚠️ 缓存命中率低于30%，建议检查缓存配置")

# 检查LLM成本
if stats['llm_usage']['total_cost_yuan'] > 100:
    logger.warning(f"⚠️ LLM成本已超过¥100: ¥{stats['llm_usage']['total_cost_yuan']:.2f}")

# 检查API成功率
if stats['api_statistics']['success_rate'] < 0.9:
    logger.error(f"❌ API成功率低于90%: {stats['api_statistics']['success_rate']:.2%}")
```

---

## 🎓 下一步学习

1. **详细文档**: 查看 [`docs/OPTIMIZATION_GUIDE.md`](./OPTIMIZATION_GUIDE.md) 了解每个优化的详细原理和高级用法

2. **LLM路由指南**: 查看 [`docs/LLM_ROUTER_GUIDE.md`](./LLM_ROUTER_GUIDE.md) 了解如何自定义模型路由策略

3. **性能Benchmark**: 运行性能测试，验证实际提升效果

4. **小模型微调**: 使用导出的JSONL数据训练自己的小模型，进一步降低成本

---

## 📞 获取帮助

遇到问题？

1. **查看日志**: `tail -f logs/trading.log`
2. **检查监控指标**: `http://localhost:8000/api/v1/metrics`
3. **提交Issue**: 在GitHub上提交issue并附上日志

---

**文档版本**: v1.0
**最后更新**: 2025-01-15
**预计阅读时间**: 5分钟
**难度级别**: ⭐ (入门)
