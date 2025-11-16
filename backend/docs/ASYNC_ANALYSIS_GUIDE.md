# 异步AI分析系统使用指南

## 概述

新的异步分析系统允许多个AI分析任务并发执行，每个任务在独立的session中运行，互不阻塞。

## 核心特性

✅ **并发执行**：最多支持10个分析任务同时运行
✅ **独立Session**：每个分析任务独立运行，不会阻塞其他请求
✅ **实时进度**：通过WebSocket或SSE获取实时分析进度
✅ **任务管理**：支持查询、取消、列出任务
✅ **自动清理**：完成的任务1小时后自动清理
✅ **页面刷新友好**：支持SSE流式接口，刷新后可继续接收进度

## 快速开始

### 1. 创建异步分析任务

```bash
# 请求
POST /api/v1/agents/analyze-all-async/600519.SH

# 响应
{
  "success": true,
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "symbol": "600519.SH",
  "message": "Analysis task created successfully",
  "status_url": "/api/v1/agents/tasks/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-01-16T20:00:00"
}
```

### 2. 获取任务进度（3种方式）

#### 方式1: WebSocket订阅（推荐，实时性最好）

```javascript
// 1. 连接WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  // 2. 订阅任务进度
  ws.send(JSON.stringify({
    type: 'subscribe_task',
    task_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case 'task_subscribed':
      console.log('已订阅任务进度');
      break;

    case 'task_progress':
      console.log(`进度: ${message.progress}% - ${message.message}`);
      // 更新UI进度条
      updateProgressBar(message.progress);
      break;

    case 'task_complete':
      console.log('分析完成！', message.result);
      // 显示分析结果
      displayAnalysisResult(message.result);
      break;

    case 'task_error':
      console.error('分析失败:', message.error);
      break;
  }
};
```

#### 方式2: SSE流式接口（推荐，页面刷新友好）

```javascript
// 创建EventSource连接（支持页面刷新后重连）
const eventSource = new EventSource(
  `/api/v1/agents/tasks/${taskId}/stream`
);

eventSource.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'start':
      console.log('连接成功');
      break;

    case 'progress':
      console.log(`进度: ${data.progress}% - ${data.message}`);
      updateProgressBar(data.progress);
      break;

    case 'complete':
      console.log('分析完成！', data.data);
      displayAnalysisResult(data.data);
      eventSource.close();
      break;

    case 'error':
      console.error('分析失败:', data.error);
      eventSource.close();
      break;
  }
});

eventSource.onerror = (error) => {
  console.error('SSE连接错误:', error);
  eventSource.close();
};
```

#### 方式3: 轮询查询（兼容性最好，但效率较低）

```javascript
// 定期查询任务状态
async function pollTaskStatus(taskId) {
  const interval = setInterval(async () => {
    const response = await fetch(`/api/v1/agents/tasks/${taskId}`);
    const { data } = await response.json();

    console.log(`进度: ${data.progress}% - ${data.status}`);

    if (data.status === 'completed') {
      clearInterval(interval);
      console.log('分析完成！', data.result);
      displayAnalysisResult(data.result);
    } else if (data.status === 'failed') {
      clearInterval(interval);
      console.error('分析失败:', data.error);
    }
  }, 2000); // 每2秒查询一次
}

pollTaskStatus('a1b2c3d4-e5f6-7890-abcd-ef1234567890');
```

### 3. 查询任务状态

```bash
# 请求
GET /api/v1/agents/tasks/a1b2c3d4-e5f6-7890-abcd-ef1234567890

# 响应
{
  "success": true,
  "data": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "task_type": "analyze_all",
    "symbol": "600519.SH",
    "status": "running",
    "progress": 45,
    "result": null,
    "error": null,
    "created_at": "2025-01-16T20:00:00",
    "started_at": "2025-01-16T20:00:01",
    "completed_at": null,
    "metadata": {
      "trade_date": "2025-01-16"
    },
    "progress_messages": [
      {
        "progress": 0,
        "message": "开始分析 600519.SH",
        "timestamp": "2025-01-16T20:00:01"
      },
      {
        "progress": 10,
        "message": "准备数据...",
        "timestamp": "2025-01-16T20:00:02"
      },
      {
        "progress": 20,
        "message": "市场分析中...",
        "timestamp": "2025-01-16T20:00:05"
      },
      {
        "progress": 45,
        "message": "分析中...",
        "timestamp": "2025-01-16T20:00:15"
      }
    ]
  },
  "timestamp": "2025-01-16T20:00:20"
}
```

### 4. 取消任务

```bash
# 请求
DELETE /api/v1/agents/tasks/a1b2c3d4-e5f6-7890-abcd-ef1234567890

# 响应
{
  "success": true,
  "message": "Task a1b2c3d4-e5f6-7890-abcd-ef1234567890 cancelled successfully",
  "timestamp": "2025-01-16T20:00:25"
}
```

### 5. 列出任务

```bash
# 列出所有任务
GET /api/v1/agents/tasks

# 过滤运行中的任务
GET /api/v1/agents/tasks?status=running

# 过滤特定股票的任务
GET /api/v1/agents/tasks?symbol=600519.SH

# 限制返回数量
GET /api/v1/agents/tasks?limit=10

# 响应
{
  "success": true,
  "data": [
    {
      "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "task_type": "analyze_all",
      "symbol": "600519.SH",
      "status": "completed",
      "progress": 100,
      "created_at": "2025-01-16T20:00:00",
      "completed_at": "2025-01-16T20:01:30"
    },
    {
      "task_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "task_type": "analyze_all",
      "symbol": "000001.SZ",
      "status": "running",
      "progress": 60,
      "created_at": "2025-01-16T20:01:00",
      "completed_at": null
    }
  ],
  "total": 2,
  "timestamp": "2025-01-16T20:01:40"
}
```

### 6. 获取任务统计

```bash
# 请求
GET /api/v1/agents/tasks/stats

# 响应
{
  "success": true,
  "data": {
    "total_tasks": 15,
    "running_tasks": 3,
    "pending_tasks": 0,
    "completed_tasks": 10,
    "failed_tasks": 1,
    "cancelled_tasks": 1
  },
  "timestamp": "2025-01-16T20:02:00"
}
```

## 前端集成示例

### React + TypeScript完整示例

```typescript
import { useState, useEffect } from 'react';

interface AnalysisProgress {
  taskId: string;
  symbol: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  message: string;
  result?: any;
  error?: string;
}

export function useAsyncAnalysis(symbol: string) {
  const [progress, setProgress] = useState<AnalysisProgress>({
    taskId: '',
    symbol,
    status: 'pending',
    progress: 0,
    message: '准备分析...'
  });

  const startAnalysis = async () => {
    try {
      // 1. 创建分析任务
      const response = await fetch(
        `/api/v1/agents/analyze-all-async/${symbol}`,
        { method: 'POST' }
      );
      const { task_id } = await response.json();

      setProgress(prev => ({
        ...prev,
        taskId: task_id,
        status: 'running'
      }));

      // 2. 使用SSE监听进度
      const eventSource = new EventSource(
        `/api/v1/agents/tasks/${task_id}/stream`
      );

      eventSource.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'progress':
            setProgress(prev => ({
              ...prev,
              progress: data.progress,
              message: data.message
            }));
            break;

          case 'complete':
            setProgress(prev => ({
              ...prev,
              status: 'completed',
              progress: 100,
              result: data.data,
              message: '分析完成'
            }));
            eventSource.close();
            break;

          case 'error':
            setProgress(prev => ({
              ...prev,
              status: 'failed',
              error: data.error,
              message: '分析失败'
            }));
            eventSource.close();
            break;
        }
      });

      eventSource.onerror = () => {
        eventSource.close();
      };

    } catch (error) {
      setProgress(prev => ({
        ...prev,
        status: 'failed',
        error: String(error),
        message: '启动分析失败'
      }));
    }
  };

  const cancelAnalysis = async () => {
    if (progress.taskId && progress.status === 'running') {
      await fetch(`/api/v1/agents/tasks/${progress.taskId}`, {
        method: 'DELETE'
      });
    }
  };

  return {
    progress,
    startAnalysis,
    cancelAnalysis
  };
}

// 使用示例
function AnalysisComponent({ symbol }: { symbol: string }) {
  const { progress, startAnalysis, cancelAnalysis } = useAsyncAnalysis(symbol);

  return (
    <div>
      <button onClick={startAnalysis} disabled={progress.status === 'running'}>
        开始分析
      </button>

      {progress.status === 'running' && (
        <button onClick={cancelAnalysis}>取消</button>
      )}

      <div>
        <progress value={progress.progress} max={100} />
        <span>{progress.progress}%</span>
        <p>{progress.message}</p>
      </div>

      {progress.status === 'completed' && progress.result && (
        <div>
          <h3>分析结果</h3>
          <pre>{JSON.stringify(progress.result, null, 2)}</pre>
        </div>
      )}

      {progress.status === 'failed' && (
        <div className="error">
          错误: {progress.error}
        </div>
      )}
    </div>
  );
}
```

### Vue 3 + TypeScript示例

```vue
<template>
  <div>
    <button @click="startAnalysis" :disabled="isRunning">
      开始分析
    </button>

    <button v-if="isRunning" @click="cancelAnalysis">
      取消
    </button>

    <div class="progress-bar">
      <div
        class="progress-fill"
        :style="{ width: `${progress}%` }"
      ></div>
      <span>{{ progress }}%</span>
      <p>{{ message }}</p>
    </div>

    <div v-if="result">
      <h3>分析结果</h3>
      <pre>{{ JSON.stringify(result, null, 2) }}</pre>
    </div>

    <div v-if="error" class="error">
      错误: {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps<{
  symbol: string;
}>();

const taskId = ref('');
const status = ref<'idle' | 'running' | 'completed' | 'failed'>('idle');
const progress = ref(0);
const message = ref('');
const result = ref<any>(null);
const error = ref('');

const isRunning = computed(() => status.value === 'running');

async function startAnalysis() {
  try {
    // 创建任务
    const response = await fetch(
      `/api/v1/agents/analyze-all-async/${props.symbol}`,
      { method: 'POST' }
    );
    const data = await response.json();

    taskId.value = data.task_id;
    status.value = 'running';

    // SSE监听进度
    const eventSource = new EventSource(
      `/api/v1/agents/tasks/${taskId.value}/stream`
    );

    eventSource.addEventListener('message', (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'progress':
          progress.value = data.progress;
          message.value = data.message;
          break;

        case 'complete':
          status.value = 'completed';
          progress.value = 100;
          result.value = data.data;
          message.value = '分析完成';
          eventSource.close();
          break;

        case 'error':
          status.value = 'failed';
          error.value = data.error;
          message.value = '分析失败';
          eventSource.close();
          break;
      }
    });

  } catch (err) {
    status.value = 'failed';
    error.value = String(err);
  }
}

async function cancelAnalysis() {
  if (taskId.value && isRunning.value) {
    await fetch(`/api/v1/agents/tasks/${taskId.value}`, {
      method: 'DELETE'
    });
  }
}
</script>
```

## API接口对比

### 同步接口 vs 异步接口

| 特性 | 同步接口 | 异步接口 |
|------|----------|----------|
| 端点 | `POST /analyze-all/{symbol}` | `POST /analyze-all-async/{symbol}` |
| 响应时间 | 30-60秒（阻塞） | < 100ms（立即返回） |
| 并发支持 | ❌ 阻塞后端 | ✅ 最多10个并发 |
| 进度查询 | ❌ 不支持 | ✅ WebSocket/SSE/轮询 |
| 页面刷新 | ❌ 丢失进度 | ✅ 可恢复（SSE） |
| 取消任务 | ❌ 不支持 | ✅ 支持 |
| 推荐场景 | 简单测试 | 生产环境 |

## 性能优化建议

### 1. 使用SSE而不是轮询

```javascript
// ❌ 不推荐：轮询（浪费带宽和资源）
setInterval(() => fetch(`/tasks/${taskId}`), 1000);

// ✅ 推荐：SSE（高效、实时）
const eventSource = new EventSource(`/tasks/${taskId}/stream`);
```

### 2. WebSocket适合多任务监控

```javascript
// 如果需要同时监控多个分析任务，使用WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

// 订阅多个任务
taskIds.forEach(taskId => {
  ws.send(JSON.stringify({
    type: 'subscribe_task',
    task_id: taskId
  }));
});
```

### 3. 合理设置并发限制

```python
# backend/api/services/task_manager.py

# 根据服务器配置调整
task_manager.max_concurrent_tasks = 10  # 默认值

# 低配服务器
task_manager.max_concurrent_tasks = 5

# 高配服务器
task_manager.max_concurrent_tasks = 20
```

## 故障排查

### 问题1: 任务卡在pending状态

**原因**：已达到最大并发限制（10个）

**解决**：
```bash
# 查看运行中的任务
GET /api/v1/agents/tasks?status=running

# 取消不需要的任务
DELETE /api/v1/agents/tasks/{task_id}
```

### 问题2: WebSocket连接失败

**检查**：
1. 确认WebSocket端点：`ws://localhost:8000/ws`
2. 检查CORS配置
3. 查看浏览器控制台错误

```javascript
ws.onerror = (error) => {
  console.error('WebSocket错误:', error);
  // 降级到SSE
  useSSEInstead();
};
```

### 问题3: SSE连接中断

**原因**：nginx缓冲或超时

**解决**：
```nginx
# nginx配置
location /api/v1/agents/tasks/ {
    proxy_pass http://backend;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
}
```

## 最佳实践

### ✅ 推荐做法

1. **使用SSE进行进度监控**（页面刷新友好）
2. **合理处理错误**（网络中断、任务失败）
3. **提供取消按钮**（用户体验）
4. **显示详细进度**（progress_messages）
5. **实现重试机制**（失败后重试）

### ❌ 避免做法

1. **不要使用同步接口处理大量请求**（会阻塞）
2. **不要无限制创建任务**（最多10个并发）
3. **不要忘记关闭EventSource/WebSocket**（内存泄漏）
4. **不要在生产环境使用轮询**（效率低）

## 完整示例项目

查看 `backend/examples/async_analysis_demo.html` 获取完整的前端演示代码。

## 技术支持

遇到问题？查看：
- API文档：`http://localhost:8000/docs`
- 日志文件：检查后端控制台输出
- 任务统计：`GET /api/v1/agents/tasks/stats`
