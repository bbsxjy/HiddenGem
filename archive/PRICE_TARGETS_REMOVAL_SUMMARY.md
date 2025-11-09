# Price Targets 移除总结

## 修改时间
2025-11-04

## 修改目的
根据用户要求，移除 LLM 对价格目标（entry、stop_loss、take_profit）的主动建议，让 LLM 专注于分析输入信息，而非给出具体的价格建议。

## 修改内容

### 1. 修复价格获取问题

**文件**: `backend/core/utils/llm_service.py`

**问题**: `_fetch_current_price` 方法使用了错误的 API 参数
- 错误：`get_daily_bars(symbol=symbol, limit=1)` - limit 参数不存在
- 错误：使用了 `await` 但 `get_daily_bars` 是同步方法

**修复**: (第 182-230 行)
```python
async def _fetch_current_price(self, symbol: str) -> Optional[float]:
    # 1. 优先尝试获取实时报价（最快）
    quote = data_source.get_realtime_quote(symbol)
    if quote and 'price' in quote:
        return float(quote['price'])

    # 2. 回退方案：获取最近7天的日线数据
    bars = data_source.get_daily_bars(
        symbol=symbol,
        start_date=(datetime.now() - timedelta(days=7)).strftime('%Y%m%d'),
        end_date=datetime.now().strftime('%Y%m%d')
    )
    return float(bars.iloc[-1]['close'])
```

**结果**:
- ✅ 成功获取 300502 价格: 348.04 元
- ✅ 成功获取 600519 价格: 1429.00 元
- ✅ 成功获取 000001 价格: 11.59 元

### 2. 移除 LLM 提示词中的价格建议要求

**文件**: `backend/core/utils/llm_service.py`

**修改位置**: `_create_analysis_prompt` 方法 (第 337-418 行)

**移除的内容**:
```python
# 移除前
"price_targets": {
  "entry": 建议入场价格数值（必填...）,
  "stop_loss": 建议止损价格数值（必填...）,
  "take_profit": 建议止盈价格数值（必填...）
}
```

**新增的注意事项**:
```python
8. **专注于分析，不要给出具体的价格建议（入场价、止损价、止盈价等）**
9. **推理应基于分析数据和市场信息，而非价格预测**
```

### 3. 修改 LLM 响应解析逻辑

**文件**: `backend/core/utils/llm_service.py`

**修改位置**: `_parse_analysis_response` 方法 (第 594-600 行)

**修改前**:
```python
# Ensure price_targets exists and has valid structure
if "price_targets" not in result or not isinstance(result["price_targets"], dict):
    result["price_targets"] = {}

# Validate price_targets fields are numeric or None
price_targets = result["price_targets"]
for key in ["entry", "stop_loss", "take_profit"]:
    if key in price_targets:
        try:
            price_targets[key] = float(price_targets[key])
        except (ValueError, TypeError):
            logger.warning(f"Invalid price_targets.{key}: {price_targets[key]}, removing")
            del price_targets[key]
```

**修改后**:
```python
# Price targets are no longer required from LLM
# Always set to empty dict (will be calculated elsewhere if needed)
result["price_targets"] = {}
```

### 4. 修改 Orchestrator 中的价格目标处理

**文件**: `backend/core/mcp_agents/orchestrator.py`

**修改 1**: 移除 llm_analysis_data 中的 price_targets (第 220-227 行)
```python
# 修改前
llm_analysis_data = {
    ...
    "price_targets": llm_result.get("price_targets", {}),
    ...
}

# 修改后
llm_analysis_data = {
    ...
    # 移除了 price_targets 字段
    ...
}
```

**修改 2**: 设置信号的价格字段为 None (第 260-281 行)
```python
# 修改前
price_targets = llm_result.get("price_targets", {})
entry_price = price_targets.get("entry")
stop_loss_price = price_targets.get("stop_loss")
take_profit_price = price_targets.get("take_profit")

aggregated_signal = AggregatedSignal(
    entry_price=Decimal(entry_price) if entry_price else None,
    target_price=Decimal(take_profit_price) if take_profit_price else None,
    stop_loss_price=Decimal(stop_loss_price) if stop_loss_price else None,
    ...
)

# 修改后
# Price targets are no longer provided by LLM
entry_price = None
stop_loss_price = None
take_profit_price = None

aggregated_signal = AggregatedSignal(
    entry_price=None,  # No price targets from LLM
    target_price=None,  # No price targets from LLM
    stop_loss_price=None,  # No price targets from LLM
    ...
)
```

## 测试结果

### 测试 1: 价格获取功能
**脚本**: `backend/scripts/test_price_fetch.py`
**结果**: ✅ 全部通过
- 300502: 348.04 元
- 600519: 1429.00 元
- 000001: 11.59 元

### 测试 2: LLM 集成测试
**脚本**: `backend/scripts/test_llm_integration.py`
**结果**: ✅ 全部通过

**LLM 输出示例**:
```json
{
  "recommended_direction": "LONG",
  "confidence": 0.78,
  "reasoning": "技术面、基本面、市场监控和风险管理四个维度均显示多头信号...",
  "risk_assessment": "主要风险点：A股市场T+1限制...",
  "key_factors": [
    "技术指标显示明确多头趋势（MACD金叉、ADX=28.5）",
    "基本面优秀（ROE=25%，负债率仅15%，估值略微低估）",
    "北向资金持续流入且同期融资余额增长，市场情绪积极"
  ]
}
```

**注意**: 没有 `price_targets` 字段，LLM 专注于分析而非价格预测。

## 影响范围

### 保持不变
- 数据模型中的 price targets 字段保留（entry_price, target_price, stop_loss_price）
- 可以在其他地方（如风险管理系统）计算和设置这些值
- Rule-based 聚合方法中的价格计算逻辑保留（如果 agent 提供价格）

### 已修改
- LLM 不再提供价格建议
- Orchestrator 使用 LLM 时，价格字段设为 None
- LLM 分析数据中不包含 price_targets

## 优势

1. **职责清晰**: LLM 专注于信息分析和方向判断，价格目标由专门的风险管理系统计算
2. **更可靠**: 价格目标基于算法计算，而非 LLM 预测
3. **易维护**: 价格逻辑集中管理，不依赖 LLM 输出
4. **符合实践**: LLM 更擅长模式识别和综合分析，而非精确数值预测

## 后续建议

如需设置价格目标，可以在以下位置实现：

1. **风险管理模块** (`backend/core/execution/risk_control.py`)
   - 基于当前价格和波动率计算止损/止盈
   - 考虑 ATR、支撑/阻力位等技术指标

2. **订单管理器** (`backend/core/execution/order_manager.py`)
   - 在创建订单时动态计算价格目标
   - 根据账户风险偏好调整

3. **策略层** (`backend/core/strategy/`)
   - 在策略中定义价格目标计算逻辑
   - 不同策略可以有不同的价格目标算法

## 修改的文件清单

1. `backend/core/utils/llm_service.py` - 修复价格获取，移除价格建议要求
2. `backend/core/mcp_agents/orchestrator.py` - 移除 price_targets 使用
3. `backend/scripts/test_price_fetch.py` - 新增测试脚本
4. `backend/PRICE_TARGETS_REMOVAL_SUMMARY.md` - 本文档
