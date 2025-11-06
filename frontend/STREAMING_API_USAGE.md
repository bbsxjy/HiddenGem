# Streaming API 使用指南

## 概述

前端已经集成了后端的 **Server-Sent Events (SSE)** 流式 API，可以实时获取 Agent 分析进度，提供更好的用户体验。

## 架构说明

### 后端 (TradingAgents-CN)

- **接口**: `GET /api/v1/agents/analyze-all-stream/{symbol}`
- **协议**: Server-Sent Events (SSE)
- **响应格式**:

```typescript
{
  type: 'start' | 'progress' | 'complete' | 'error',
  symbol?: string,
  agent?: string,        // technical, fundamental, sentiment, policy, debate, risk, system
  status?: string,       // analyzing, complete, etc.
  message?: string,      // 进度消息
  progress?: number,     // 进度百分比 (0-100)
  data?: AnalyzeAllResponse,  // 最终结果
  error?: string,
  timestamp: string
}
```

### 前端实现

#### 1. API 客户端函数 (`src/api/agents.ts`)

```typescript
import { analyzeWithAllAgentsStream, type StreamCallbacks } from '@/api/agents';

// 使用回调函数方式
const eventSource = analyzeWithAllAgentsStream('NVDA', {
  onStart: (event) => {
    console.log('分析开始:', event.symbol);
  },
  onProgress: (event) => {
    console.log(`[${event.agent}] ${event.message} - ${event.progress}%`);
  },
  onComplete: (data) => {
    console.log('分析完成:', data);
  },
  onError: (error) => {
    console.error('分析失败:', error);
  }
});

// 可以随时取消
eventSource.close();
```

#### 2. React Hook (`src/hooks/useStreamingAnalysis.ts`)

更高级的封装，自动处理状态管理：

```typescript
import { useStreamingAnalysis } from '@/hooks/useStreamingAnalysis';

function MyComponent() {
  const {
    // 状态
    isAnalyzing,          // 是否正在分析
    progress,             // 进度文本 (如 "75%")
    progressPercent,      // 进度数值 (0-100)
    currentAgent,         // 当前执行的 Agent
    currentMessage,       // 当前状态消息
    agentResults,         // 已完成的 Agent 结果
    finalResult,          // 最终完整结果
    error,                // 错误信息
    isLLMAnalyzing,       // 是否在 LLM 分析阶段

    // 操作
    startAnalysis,        // 开始分析
    stopAnalysis,         // 停止分析
  } = useStreamingAnalysis();

  return (
    <div>
      <button onClick={() => startAnalysis('NVDA')}>
        分析 NVDA
      </button>

      {isAnalyzing && (
        <div>
          <progress value={progressPercent} max={100} />
          <p>{currentMessage}</p>
          <p>当前: {currentAgent}</p>
          <button onClick={stopAnalysis}>取消</button>
        </div>
      )}

      {finalResult && (
        <div>分析完成！推荐: {finalResult.llm_analysis.recommended_direction}</div>
      )}
    </div>
  );
}
```

#### 3. 实际应用 (`src/pages/Analysis.tsx`)

完整的 UI 实现，包含：
- ✅ 实时进度条
- ✅ 当前 Agent 显示
- ✅ 状态消息显示
- ✅ 已完成 Agent 卡片
- ✅ 取消分析按钮
- ✅ 最终结果展示

## 工作流程

### 1. 用户发起分析

用户点击"综合分析"按钮 → `startAnalysis(symbol)` 被调用

### 2. 建立 SSE 连接

```
前端: EventSource 连接到 /api/v1/agents/analyze-all-stream/NVDA
后端: 接受连接，开始分析流程
```

### 3. 实时进度更新

后端发送多个 `progress` 事件：

```
{ type: 'progress', agent: 'technical', message: '正在进行技术面分析...', progress: 9 }
{ type: 'progress', agent: 'fundamental', message: '正在进行基本面分析...', progress: 40 }
{ type: 'progress', agent: 'sentiment', message: '正在进行情绪分析...', progress: 50 }
{ type: 'progress', agent: 'policy', message: '正在进行政策新闻分析...', progress: 60 }
{ type: 'progress', agent: 'debate', message: '正在进行投资辩论...', progress: 82 }
{ type: 'progress', agent: 'risk', message: '正在进行风险评估...', progress: 95 }
{ type: 'progress', agent: 'system', message: '正在汇总分析结果...', progress: 95 }
```

前端实时更新 UI：
- 进度条移动
- 显示当前 Agent 名称
- 显示状态消息
- 已完成的 Agent 卡片高亮

### 4. 分析完成

后端发送 `complete` 事件：

```json
{
  "type": "complete",
  "data": {
    "symbol": "NVDA",
    "agent_results": { ... },
    "aggregated_signal": { ... },
    "llm_analysis": { ... }
  },
  "timestamp": "2025-11-06T..."
}
```

前端：
- 关闭 SSE 连接
- 显示完整分析结果
- 更新 UI 为"分析完成"状态

## UI 组件说明

### 进度条

```tsx
<div className="w-full bg-gray-200 rounded-full h-2.5">
  <div
    className="bg-primary-500 h-2.5 rounded-full transition-all"
    style={{ width: `${progressPercent}%` }}
  />
</div>
```

### 状态显示

```tsx
<div className="flex items-center gap-3">
  {isAnalyzing && <Spinner />}
  <div className="flex flex-col">
    <span>{currentMessage || `分析进度: ${progress}`}</span>
    {currentAgent && (
      <span className="text-xs text-gray-500">
        当前: {agentNameMap[currentAgent]}
      </span>
    )}
  </div>
</div>
```

### Agent 名称映射

```typescript
const agentNameMap = {
  'technical': '📈 技术分析',
  'fundamental': '💰 基本面',
  'sentiment': '💬 情绪分析',
  'policy': '📰 政策新闻',
  'debate': '⚖️ 投资辩论',
  'risk': '🛡️ 风险评估',
  'system': '⚙️ 系统',
};
```

## 优势对比

### 旧方式 (非流式)

```typescript
// ❌ 需要等待 30-60 秒
// ❌ 没有进度反馈
// ❌ 用户体验差
const result = await analyzeWithAllAgents('NVDA');
```

**用户看到的**：
- 点击按钮
- 等待... 等待... 等待...（30-60秒）
- 突然显示结果

### 新方式 (流式)

```typescript
// ✅ 实时进度反馈
// ✅ 可随时取消
// ✅ 用户体验好
useStreamingAnalysis();
```

**用户看到的**：
- 点击按钮
- "📈 技术分析中... 9%"
- "💰 基本面分析中... 40%"
- "💬 情绪分析中... 50%"
- "📰 政策新闻分析中... 60%"
- "⚖️ 投资辩论中... 82%"
- "🛡️ 风险评估中... 95%"
- "✅ 分析完成 100%"

## 错误处理

### 连接失败

```typescript
eventSource.onerror = (err) => {
  console.error('SSE连接断开或服务器错误');
  // 自动清理状态
  setIsAnalyzing(false);
  setError('连接失败');
};
```

### 后端错误

```json
{
  "type": "error",
  "error": "分析失败: 股票代码不存在",
  "timestamp": "2025-11-06T..."
}
```

### 用户取消

```typescript
const stopAnalysis = () => {
  eventSource.current?.close();
  setIsAnalyzing(false);
};
```

## 性能优化

### 1. 自动清理

```typescript
useEffect(() => {
  return () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
  };
}, []);
```

### 2. 状态合并

使用单个 `setState` 减少重渲染：

```typescript
setState(prev => ({
  ...prev,
  progress: progressDisplay,
  progressPercent,
  currentAgent: data.agent,
  currentMessage: data.message,
}));
```

### 3. 条件渲染

只在必要时显示 UI 元素：

```tsx
{isAnalyzing && <ProgressBar />}
{finalResult && <Results />}
```

## 浏览器兼容性

**EventSource API 支持**:
- ✅ Chrome 6+
- ✅ Firefox 6+
- ✅ Safari 5+
- ✅ Edge 79+
- ❌ IE (不支持，但可以使用 polyfill)

## 调试技巧

### 1. 查看 SSE 事件

```typescript
eventSource.onmessage = (event) => {
  console.log('[SSE Event]', JSON.parse(event.data));
  // 继续处理...
};
```

### 2. 网络面板

Chrome DevTools → Network → EventStream 类型

### 3. 模拟慢速连接

Chrome DevTools → Network → Throttling → Slow 3G

## 未来增强

- [ ] 支持多个同时分析
- [ ] 分析历史记录
- [ ] 进度可视化增强（动画）
- [ ] 断线重连
- [ ] 离线缓存

## 总结

前端的 streaming 功能已经完全实现并集成到 Analysis 页面中。用户现在可以：

1. ✅ 实时看到分析进度
2. ✅ 知道当前正在执行哪个 Agent
3. ✅ 随时取消分析
4. ✅ 获得流畅的用户体验

相比旧的非流式 API，新实现大大提升了用户体验，特别是在耗时较长的分析任务中。
