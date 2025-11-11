# 实时监控功能说明

## 修复的问题

### 1. 交易时段判断错误 ✅

**问题**：前端显示"非交易时段"，但实际已经在交易时间（10:30）内

**原因**：`auto_trading_service.py` 的 `_get_initializing_status()` 方法在 broker 未初始化时，硬编码返回 `is_trading_hours = False`

**修复**：
- 修改 `_get_initializing_status()` 方法，即使在初始化阶段也会尝试调用 `trader.is_trading_hours()` 获取真实的交易时段状态
- 文件：`backend/api/services/auto_trading_service.py:213-239`

**代码变更**：
```python
def _get_initializing_status(self) -> Dict:
    """返回初始化中的状态"""
    # 尝试获取交易时段状态
    is_trading_hours = False
    next_check_time = None
    if self.trader and hasattr(self.trader, 'is_trading_hours'):
        try:
            is_trading_hours = self.trader.is_trading_hours()
            if not is_trading_hours and hasattr(self.trader, 'get_next_trading_time'):
                next_session = self.trader.get_next_trading_time()
                if next_session:
                    next_check_time = next_session.isoformat()
        except Exception as e:
            logger.debug(f"Could not get trading hours status: {e}")

    return {
        # ... 其他字段
        "is_trading_hours": is_trading_hours,  # 使用真实的交易时段状态
        "next_check_time": next_check_time,
    }
```

---

### 2. 缺少实时监控页面 ✅

**问题**：用户想看到每只股票的实时交易判断（买/卖/持有），但只有设置页面有控制

**解决方案**：创建了全新的"实时监控"页面

**新增文件**：
1. `frontend/src/pages/LiveMonitor.tsx` - 实时监控页面
2. 修改 `frontend/src/components/layout/navigation.ts` - 添加导航菜单项
3. 修改 `frontend/src/App.tsx` - 添加路由配置

---

## 实时监控页面功能

### 页面路径
访问路径：`/live-monitor`
导航菜单：**实时监控** （位于"交易历史"和"策略管理"之间）

### 主要功能

#### 1. 系统状态概览卡片
- **系统状态**：显示运行中/已停止
- **交易时段**：显示进行中/非交易时间（修复后能正确显示）
- **监控股票**：显示当前监控的股票数量
- **今日交易**：显示今日已完成的交易数量

#### 2. 系统提示
- 如果在非交易时段，显示黄色提示框，告知下次检查时间
- 如果系统未运行，显示灰色提示框，引导用户前往设置页面启动

#### 3. 实时股票判断列表
每只股票显示：
- **股票代码和名称**
- **决策类型**：买入（绿色）/卖出（红色）/持有（灰色）/跳过
- **最后检查时间**：精确到秒
- **决策原因**：为什么做出这个决策
- **置信度**：以进度条显示（0-100%）
- **当前价格**：股票的实时价格（如果有）
- **建议数量**：建议交易的股票数量（如果有）

#### 4. 最近交易信号
显示最近10条交易信号：
- 股票代码
- 信号方向（做多/做空/持有）
- 信号原因
- 触发时间

### 数据刷新频率
- **自动交易状态**：每3秒刷新一次
- **交易信号**：每5秒刷新一次
- **实时响应**：页面自动更新，无需手动刷新

---

## 使用方法

### 1. 启动自动交易
1. 前往 **设置** 页面（`/settings`）
2. 在"自动交易控制"卡片中配置：
   - 交易股票列表（逗号分隔）
   - 初始资金
   - 检查间隔（分钟）
   - 是否启用多Agent分析
3. 点击"启动自动交易"按钮

### 2. 查看实时监控
1. 点击左侧导航栏的 **实时监控**
2. 查看系统状态和交易时段
3. 滚动查看每只股票的实时判断
4. 查看最近的交易信号历史

### 3. 理解决策
每只股票的决策卡片会显示：
- **绿色买入图标** 🔼：系统判断应该买入
- **红色卖出图标** 🔽：系统判断应该卖出
- **灰色持有图标** ➖：系统判断保持当前持仓
- **置信度条**：显示决策的信心程度

---

## 技术架构

### 前端组件
- **React + TypeScript**：类型安全的组件开发
- **TanStack Query**：自动刷新和缓存管理
- **Lucide React**：现代化图标库
- **Tailwind CSS**：响应式样式

### 后端集成
- 调用 `/api/v1/auto-trading/status` 获取实时状态
- 调用 `/api/v1/signals/recent` 获取最近信号
- 支持实时数据轮询和自动刷新

### 状态管理
- 使用 React Query 管理服务器状态
- 自动处理加载、错误和重试逻辑
- 智能缓存和后台更新

---

## 日志示例

系统运行时，您会在后端日志中看到：

```
2025-11-11 10:30:07,112 | scripts.auto_paper_trading | INFO | [CYCLE] Trading Check at 2025-11-11 10:30:07 CST
2025-11-11 10:30:07,113 | scripts.auto_paper_trading | INFO | [300502] Checking...
2025-11-11 10:30:07,113 | scripts.auto_paper_trading | INFO | [300502] Real-time trading requires live market data connection
```

这些信息会被前端实时监控页面以用户友好的方式展示。

---

## 下一步优化建议

1. **实时市场数据连接**
   - 当前显示"等待市场数据连接"
   - 需要集成实时行情数据源（Tushare/AkShare）

2. **WebSocket 实时推送**
   - 替代当前的轮询机制
   - 更低延迟的决策更新

3. **历史决策记录**
   - 保存每次决策的历史记录
   - 支持回溯分析和决策审计

4. **决策详情弹窗**
   - 点击股票卡片查看详细的Agent分析
   - 显示多个Agent的独立判断

5. **性能指标**
   - 显示策略的胜率、盈亏比
   - 可视化每只股票的历史表现

---

**最后更新**：2025-11-11 10:35 CST
**相关提交**：78f957f, d0e1679, 3eaa812
