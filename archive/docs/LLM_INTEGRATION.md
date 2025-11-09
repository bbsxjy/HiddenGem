# LLM Integration Guide

## 概述

HiddenGem量化交易系统已成功集成LLM（大语言模型）用于智能交易信号分析。系统现在使用AI驱动的决策制定，而不是简单的规则和数学计算。

## 架构变化

### 之前（规则基础）
```
Agents（技术、基本面、市场等）
  ↓
加权投票聚合（简单数学）
  ↓
交易信号
```

### 现在（AI驱动）
```
Agents（技术、基本面、市场等）
  ↓
LLM智能分析（Qwen2.5-7B）
  ↓
交易信号 + 详细推理
  ↓
（失败则降级到规则基础方法）
```

## 关键组件

### 1. LLM服务模块 (`core/utils/llm_service.py`)

**功能：**
- 集成SiliconFlow API（OpenAI兼容）
- 使用Qwen/Qwen2.5-7B-Instruct模型
- 智能分析多个agent的结果
- 返回结构化的交易建议

**主要方法：**
```python
async def analyze_trading_signal(
    symbol: str,
    agent_results: Dict[str, AgentAnalysisResult],
    market_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**返回结果：**
```json
{
  "recommended_direction": "LONG|SHORT|HOLD|CLOSE",
  "confidence": 0.75,
  "reasoning": "详细的决策理由...",
  "risk_assessment": "风险评估...",
  "key_factors": ["关键因素1", "关键因素2", ...],
  "price_targets": {
    "entry": 1850.0,
    "stop_loss": 1750.0,
    "take_profit": 2000.0
  }
}
```

### 2. 修改的Orchestrator (`core/mcp_agents/orchestrator.py`)

**新增方法：**

#### `_generate_signal_with_llm()`
使用LLM分析所有agent结果，生成智能交易信号：
- 综合评估技术面、基本面、市场情绪、政策影响
- 识别信号之间的冲突或一致性
- 提供人类可读的决策理由
- 评估风险并给出应对建议

#### `_generate_signal_rule_based()`
传统的规则基础信号聚合（作为LLM失败时的降级方案）：
- 加权投票机制
- 置信度阈值检查
- Agent一致性验证

### 3. 配置

**环境变量 (`.env`)：**
```bash
# LLM Configuration
LLM_API_KEY=sk-axmtsvynpcrwbvtuaomohsnineuavimmixckakgnnmumnfom
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
LLM_ENABLED=true
LLM_TIMEOUT=30
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000
```

**设置项 (`config/settings.py`)：**
```python
llm_api_key: Optional[str]
llm_base_url: str
llm_model: str
llm_enabled: bool
llm_timeout: int
llm_temperature: float
llm_max_tokens: int
```

## 使用方法

### 1. 通过Orchestrator使用

```python
from core.mcp_agents.orchestrator import MCPOrchestrator

orchestrator = MCPOrchestrator()

# 分析股票并生成信号（自动使用LLM）
signal = await orchestrator.generate_trading_signal(
    symbol="600519.SH",
    save_to_db=True,
    db_session=db_session
)

# 访问LLM分析结果
if signal and signal.metadata.get("analysis_method") == "llm":
    print(f"LLM推理: {signal.metadata['llm_reasoning']}")
    print(f"风险评估: {signal.metadata['risk_assessment']}")
    print(f"关键因素: {signal.metadata['key_factors']}")
```

### 2. 直接使用LLM服务

```python
from core.utils.llm_service import get_llm_service

llm_service = get_llm_service()

# 分析agent结果
result = await llm_service.analyze_trading_signal(
    symbol="600519.SH",
    agent_results=agent_results,
    market_context=None
)

print(f"推荐方向: {result['recommended_direction']}")
print(f"置信度: {result['confidence']:.2%}")
print(f"推理: {result['reasoning']}")
```

### 3. 禁用LLM（使用规则基础方法）

在`.env`中设置：
```bash
LLM_ENABLED=false
```

或在代码中临时禁用：
```python
from config.settings import settings
settings.llm_enabled = False
```

## 测试

运行LLM集成测试：
```bash
cd backend
python scripts/test_llm_integration.py
```

**测试内容：**
- LLM API连接测试
- Agent结果分析测试
- 响应解析验证
- 错误处理测试

**测试结果示例：**
```
Symbol: 600519.SH (贵州茅台)
Recommended Direction: LONG
Confidence: 75.00%

Reasoning:
综合分析显示，多数agent给出long信号，其中TechnicalAnalysisAgent和FundamentalAgent
的置信度较高，分别为0.80和0.70。MarketMonitorAgent也显示市场情绪积极...

Risk Assessment:
主要风险点包括市场整体波动和政策不确定性。风险级别为低...

Key Factors:
1. MACD金叉
2. 均线多头排列
3. ROE高
4. 负债率低
5. 融资余额增长

Price Targets:
  Entry: 1850.0
  Stop Loss: 1750.0
  Take Profit: 2000.0

✓ LLM Integration Test PASSED
```

## LLM分析的优势

### 1. 智能决策
- **之前**：简单加权平均，无法理解上下文
- **现在**：AI理解市场动态，提供深度分析

### 2. 冲突解决
- **之前**：信号冲突时仅看数量多少
- **现在**：LLM权衡各因素重要性，给出合理建议

### 3. 可解释性
- **之前**：只有方向和置信度
- **现在**：详细的决策理由、风险评估、关键因素

### 4. A股特性理解
- LLM理解A股市场特点（涨跌停、T+1、情绪驱动等）
- 考虑政策影响、资金流向、市场情绪

### 5. 自适应性
- **之前**：固定规则，难以适应市场变化
- **现在**：LLM根据情况灵活调整策略

## Prompt工程

系统使用精心设计的prompt来引导LLM：

**Prompt结构：**
1. **角色定义**：专业A股量化交易分析师
2. **Agent结果展示**：格式化展示各agent的分析
3. **市场环境**：当前市场状态（可选）
4. **任务要求**：
   - 综合评估各agent信号
   - 分析信号一致性和冲突
   - 识别关键决策因素
   - 提供操作建议
5. **A股注意事项**：
   - 涨跌停限制
   - T+1交易制度
   - 情绪驱动特点
   - 信号冲突时倾向HOLD

## 容错机制

### 1. LLM失败降级
```python
if settings.llm_enabled:
    try:
        return await self._generate_signal_with_llm(...)
    except Exception as e:
        logger.error(f"LLM failed: {e}, falling back to rule-based")
        return await self._generate_signal_rule_based(...)
```

### 2. 响应解析容错
- 处理JSON解析错误
- 处理缺失字段
- 默认安全值（HOLD, confidence=0.0）

### 3. 超时保护
- 默认30秒超时
- 可配置超时时间

## 性能优化

### 1. 数据简化
```python
def _simplify_analysis(self, analysis: Dict) -> Dict:
    # 只保留关键字段，减少token使用
    essential_keys = ['overall_score', 'valuation', 'rsi', 'macd', ...]
```

### 2. 缓存机制
- Agent结果已缓存（Redis）
- LLM响应可考虑短期缓存

### 3. 并行处理
- Agent分析并行执行
- LLM分析串行（因为需要所有agent结果）

## 成本考虑

**SiliconFlow定价（参考）：**
- Qwen2.5-7B-Instruct: ~¥0.0006/1K tokens
- 平均每次分析：~2000 tokens
- 每次调用成本：~¥0.0012

**优化建议：**
1. 合理设置`LLM_MAX_TOKENS`
2. 精简agent结果数据
3. 批量分析时考虑缓存
4. 非关键场景可禁用LLM

## 未来增强

### 1. Prompt优化
- A/B测试不同prompt
- 加入更多市场上下文
- 优化输出格式

### 2. 模型选择
- 支持多模型切换
- 根据任务选择合适模型
- 本地模型部署选项

### 3. 反馈循环
- 记录LLM建议和实际结果
- 持续优化prompt
- 微调专用模型

### 4. 多轮对话
- Agent与LLM交互式分析
- LLM主动请求更多数据
- 深度推理链（Chain-of-Thought）

## 故障排查

### 问题：LLM API调用失败
**检查：**
1. API key是否正确配置
2. 网络连接是否正常
3. API余额是否充足
4. 查看日志了解具体错误

### 问题：返回结果格式错误
**检查：**
1. 查看LLM原始响应（DEBUG日志）
2. 检查prompt是否清晰
3. 验证模型能力是否匹配

### 问题：置信度总是很低
**检查：**
1. Agent结果是否有效
2. 信号是否严重冲突
3. Prompt是否需要调整

## 总结

✅ **已完成：**
- LLM服务模块集成
- Orchestrator智能分析
- 配置管理
- 测试验证
- 降级机制

🎯 **核心价值：**
- 从规则驱动到AI驱动
- 从简单聚合到智能分析
- 从黑盒到可解释
- 从固定到自适应

🚀 **下一步：**
- 实盘验证LLM效果
- 优化prompt提高准确率
- 收集反馈数据持续改进
- 探索更先进的LLM能力

---

*Generated with HiddenGem Trading System - LLM Integration v1.0*
