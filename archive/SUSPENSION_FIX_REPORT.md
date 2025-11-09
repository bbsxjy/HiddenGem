# 停牌检测问题修复报告

## 问题描述

风险Agent经常错误地将有历史停牌记录的股票标记为"当前停牌"，例如：
- **300502 (新易盛)**: 实际未停牌，但agent报告"股票停牌中(停牌日:None，复牌日:None)"
- 许多其他股票也有类似的误报

## 根本原因

### 1. API使用错误

**错误用法**: 使用了 `suspend_d` API
- 该API返回**盘中停牌**数据 (intraday suspension)
- 返回字段: `ts_code`, `trade_date`, `suspend_timing`, `suspend_type`
- 这是临时停牌记录，不代表长期停牌状态

**正确用法**: 应该使用 `suspend` API
- 该API返回**长期停牌**数据 (long-term suspension)
- 返回字段: `ts_code`, `suspend_date`, `resume_date`, `ann_date`, `suspend_reason`, `reason_type`

### 2. 判断逻辑错误

**原逻辑**:
```python
df_suspend = self.tushare.get_suspend_d(ts_code=ts_code)
is_suspended = not df_suspend.empty  # ❌ 只要有记录就认为停牌
```

**问题**:
- 没有检查记录是否是历史记录
- 没有检查是否已经复牌
- 导致所有有停牌历史的股票都被标记为"停牌中"

## 修复方案

### 1. 添加正确的API方法 (`tushare_api.py`)

```python
def get_suspend(self, ts_code: Optional[str] = None,
               start_date: Optional[str] = None,
               end_date: Optional[str] = None,
               suspend_type: Optional[str] = None) -> pd.DataFrame:
    """
    Get long-term stock suspension information (长期停复牌信息).

    Returns:
        DataFrame with columns:
        ts_code, suspend_date, resume_date, ann_date,
        suspend_reason, reason_type
    """
```

### 2. 修复判断逻辑 (`risk_agent.py`)

**新逻辑**:
```python
# 1. 改用正确的API
df_suspend = self.tushare.get_suspend(ts_code=ts_code)

# 2. 正确判断是否当前停牌
for _, row in df_suspend.iterrows():
    suspend_date = row['suspend_date']
    resume_date = row['resume_date']

    # 检查停牌是否已开始
    if suspend_date > today:
        continue  # 未来的停牌

    # 检查是否已复牌
    if pd.notna(resume_date) and resume_date <= today:
        continue  # 已经复牌

    # 到这里才是真正的当前停牌
    is_currently_suspended = True
    break
```

### 3. 添加必要的导入

```python
import pandas as pd  # 用于 pd.notna()
```

### 4. 增强停牌原因显示

在 `_create_reasoning()` 方法中添加停牌原因:
```python
reasons.append(
    f"股票停牌中(停牌日:{suspend_date}，复牌日:{resume_date}，"
    f"原因:{suspend_reason})"
)
```

## 测试验证

### 测试用例 1: 300502 (新易盛) - 之前误报停牌

**结果**:
```
是否停牌: False  ✓
状态: 股票正常交易，未停牌
日志: "300502.SZ has suspension history but not currently suspended"
```

- 检测到2条历史停牌记录
- **正确判断为未停牌**
- 修复成功 ✓

### 测试用例 2: 000001 (平安银行) - 对照组

**结果**:
```
是否停牌: False  ✓
状态: 股票正常交易，未停牌
日志: "000001.SZ has suspension history but not currently suspended"
```

- 检测到55条历史停牌记录
- **正确判断为未停牌**
- 对照组正常 ✓

## 修改文件清单

### 新增/修改文件:
1. `backend/core/data/tushare_api.py`
   - 添加 `get_suspend()` 方法
   - 更新 `get_suspend_d()` 文档注释

2. `backend/core/mcp_agents/risk_agent.py`
   - 添加 `import pandas as pd`
   - 修复停牌检测逻辑 (lines 206-276)
   - 更新 `_create_reasoning()` 停牌信息显示 (lines 620-625)

3. `backend/scripts/verify_suspension_api.py` (新增)
   - 验证API行为的测试脚本

4. `backend/scripts/test_suspension_fix.py` (新增)
   - 完整的修复验证测试

### Git提交:
- Commit 1: `a2f8094` - Fix 405 error: Change analyze-all-stream endpoint
- Commit 2: `8796629` - Fix suspension detection: Use correct API and logic

## 影响范围

**影响的功能**:
- 风险Agent的A-share风险分析
- 停牌状态检测和风险评分
- 交易信号生成（停牌股票会被标记为高风险）

**向后兼容性**:
- ✓ 完全兼容，只是修复了错误行为
- ✓ API返回格式保持不变
- ✓ 不影响其他Agent

## 后续建议

### 1. API权限要求
`suspend` API 需要 **Tushare积分2000+**，如果积分不足：
- 可以降级为只检查股票基本信息中的 `list_status` 字段
- 或者使用其他数据源（AkShare）

### 2. 缓存策略
停牌信息变化频率较低，建议：
- 增加缓存时间（当前可能太短）
- 或者改为每日更新一次

### 3. 监控告警
建议添加监控：
- 停牌检测失败率
- API调用错误率
- 误判率统计

## 总结

✅ **问题修复**: 停牌检测不再误报
✅ **API正确**: 使用长期停牌API而非盘中停牌API
✅ **逻辑完善**: 正确判断是否当前停牌
✅ **测试通过**: 300502等股票不再误报停牌

**修复前**: 有历史记录就报"停牌中" ❌
**修复后**: 只有当前实际停牌才报告 ✓
