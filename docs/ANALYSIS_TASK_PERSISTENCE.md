# 分析任务持久化设计

## 问题描述

当前AI分析功能存在以下问题：
1. 用户点击分析后，页面刷新或切换会丢失所有分析进度和结果
2. AI分析耗时长（5-10分钟），用户体验差
3. 没有历史记录功能，无法查看之前的分析结果

## 解决方案

### 1. 数据模型设计

**AnalysisTask 分析任务模型**：

```python
{
    "task_id": "uuid",              # 任务唯一ID
    "symbol": "000001.SZ",          # 股票代码
    "status": "running",            # 状态: pending, running, completed, failed
    "progress": 75,                 # 进度百分比 (0-100)
    "current_agent": "technical",   # 当前正在分析的agent
    "current_message": "分析中...",  # 当前进度消息

    # 时间信息
    "created_at": "2025-01-16T10:30:00Z",
    "started_at": "2025-01-16T10:30:05Z",
    "completed_at": "2025-01-16T10:35:00Z",

    # 分析结果
    "agent_results": {              # 各个agent的分析结果
        "technical": {...},
        "fundamental": {...},
        "sentiment": {...},
        "policy": {...}
    },
    "aggregated_signal": {...},     # 聚合信号
    "llm_analysis": {...},          # LLM综合分析

    # 错误信息
    "error": null,                  # 错误信息（如果失败）

    # 用户信息（可选）
    "user_id": "user123",           # 用户ID（如果有认证系统）
}
```

### 2. 后端API设计

**新增端点**：

```
POST   /api/v1/analysis/tasks
       创建新的分析任务
       Request: { "symbol": "000001.SZ" }
       Response: { "task_id": "uuid", "symbol": "000001.SZ", "status": "pending" }

GET    /api/v1/analysis/tasks/{task_id}
       获取任务详情和结果
       Response: { AnalysisTask }

GET    /api/v1/analysis/tasks/{task_id}/stream
       SSE流式获取任务进度（替代原来的 /agents/analyze-all/{symbol}/stream）
       Events: start, progress, agent_complete, complete, error

GET    /api/v1/analysis/history
       获取历史分析任务列表（可按symbol筛选）
       Query: ?symbol=000001.SZ&limit=10&status=completed
       Response: { "tasks": [AnalysisTask, ...], "total": 50 }

DELETE /api/v1/analysis/tasks/{task_id}
       删除任务（可选）
```

**改进现有端点**：

```
POST   /api/v1/agents/analyze-all/{symbol}
       改为内部调用新的任务系统，返回task_id
       Response: { "task_id": "uuid", "symbol": "000001.SZ" }
```

### 3. 存储方案

**选项A：内存存储 + Redis（短期，快速实现）**
- 使用Python字典 + Redis缓存
- 优点：实现简单快速
- 缺点：服务器重启后数据丢失
- 适用场景：MVP快速验证

**选项B：MongoDB存储（推荐，长期方案）**
- 使用MongoDB存储所有任务
- 优点：持久化、可查询、可扩展
- 缺点：需要配置MongoDB
- 适用场景：生产环境

**本次实现**：采用**选项A**作为起点，预留扩展到选项B的接口。

### 4. 前端改进

**新增组件**：

```tsx
// 分析历史面板
<AnalysisHistory>
  - 显示最近10条分析记录
  - 点击可查看完整结果
  - 支持按symbol筛选
  - 显示状态标签（运行中/已完成/失败）
</AnalysisHistory>

// 分析任务卡片
<AnalysisTaskCard>
  - 显示任务基本信息（symbol, status, progress）
  - 运行中任务显示进度条
  - 已完成任务显示结果摘要
  - 点击展开查看详细分析
</AnalysisTaskCard>
```

**改进现有流程**：

```typescript
// useStreamingAnalysis hook改进
export function useStreamingAnalysis() {
  // 1. startAnalysis改为先创建任务，返回task_id
  const startAnalysis = async (symbol: string) => {
    const { task_id } = await createAnalysisTask(symbol);
    connectToTaskStream(task_id);
    return task_id;
  };

  // 2. 页面刷新后自动恢复
  useEffect(() => {
    const resumeTask = async () => {
      const runningTasks = await getRunningTasks();
      if (runningTasks.length > 0) {
        connectToTaskStream(runningTasks[0].task_id);
      }
    };
    resumeTask();
  }, []);
}
```

**Market.tsx 改进**：

```tsx
// 添加历史记录侧边栏或下拉菜单
<div className="flex gap-4">
  <div className="flex-1">
    {/* 原有的分析显示区域 */}
  </div>

  <div className="w-80">
    {/* 新增：分析历史面板 */}
    <AnalysisHistory
      symbol={selectedSymbol}
      onSelectTask={(task) => loadTaskResult(task.task_id)}
    />
  </div>
</div>
```

### 5. 用户体验流程

**场景1：正常分析流程**
1. 用户输入股票代码 → 点击"AI分析"
2. 创建新任务 → 返回task_id → 建立SSE连接
3. 实时显示进度 → 各Agent结果逐步显示
4. 分析完成 → 保存到历史记录

**场景2：页面刷新恢复**
1. 用户正在分析中 → 不小心刷新页面
2. 页面加载后 → 自动检测是否有运行中的任务
3. 发现有 → 显示"检测到进行中的分析，正在恢复..."
4. 重新连接SSE → 继续显示进度

**场景3：查看历史记录**
1. 用户点击"历史记录"按钮
2. 侧边栏显示最近10条分析
3. 点击某条历史记录 → 展开显示完整分析结果
4. 可以再次分析同一股票 → 创建新任务

### 6. 实现计划

**Phase 1: 后端基础**（优先）
- [ ] 创建 AnalysisTask 数据模型
- [ ] 实现内存存储管理器（可扩展到MongoDB）
- [ ] 创建 /api/v1/analysis/tasks 路由
- [ ] 修改现有SSE endpoint支持task_id

**Phase 2: 前端基础**
- [ ] 修改 useStreamingAnalysis hook
- [ ] 创建 AnalysisHistory 组件
- [ ] 创建 AnalysisTaskCard 组件
- [ ] 集成到 Market.tsx

**Phase 3: 用户体验优化**
- [ ] 实现页面刷新自动恢复
- [ ] 添加任务状态通知
- [ ] 优化历史记录UI

**Phase 4: 扩展功能**
- [ ] 迁移到MongoDB持久化
- [ ] 添加任务分享功能
- [ ] 导出分析报告

### 7. 技术细节

**任务生命周期管理**：

```python
class AnalysisTaskManager:
    def create_task(self, symbol: str) -> str:
        """创建新任务，返回task_id"""

    def update_progress(self, task_id: str, progress: int, message: str):
        """更新任务进度"""

    def set_agent_result(self, task_id: str, agent: str, result: dict):
        """保存agent分析结果"""

    def complete_task(self, task_id: str, final_result: dict):
        """标记任务完成并保存最终结果"""

    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""

    def get_task(self, task_id: str) -> AnalysisTask:
        """获取任务详情"""

    def get_history(self, symbol: str = None, limit: int = 10) -> List[AnalysisTask]:
        """获取历史任务列表"""
```

**SSE连接管理**：

```python
@router.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """流式返回任务进度"""

    async def event_generator():
        task = task_manager.get_task(task_id)

        # 如果任务已完成，直接返回结果
        if task.status == "completed":
            yield {
                "type": "complete",
                "data": task.to_dict()
            }
            return

        # 订阅任务更新
        async for event in task_manager.subscribe(task_id):
            yield event

    return EventSourceResponse(event_generator())
```

## 下一步

开始实现 Phase 1：后端基础功能。

