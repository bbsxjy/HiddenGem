import { useState, useCallback, useRef, useEffect } from 'react';
import { createAnalysisTask, streamTaskProgress, getTaskDetail, type AnalysisTask } from '@/api/agents';
import type { AnalyzeAllResponse, AgentAnalysisResult } from '@/types/agent';

/**
 * SSE Event from backend
 */
interface SSEEvent {
  type: 'start' | 'progress' | 'agent_complete' | 'complete' | 'error';
  task_id?: string;
  symbol?: string;
  agent?: string;
  status?: string;
  message?: string;
  progress?: number;
  result?: AgentAnalysisResult;
  data?: AnalyzeAllResponse;
  error?: string;
  timestamp: string;
}

const PRIMARY_AGENT_KEYS = ['technical', 'fundamental', 'sentiment', 'policy'] as const;
const PRIMARY_AGENT_SET = new Set(PRIMARY_AGENT_KEYS);
const LLM_PHASE_AGENTS = new Set(['debate', 'risk', 'system']);

const AGENT_KEYWORDS: Record<string, string[]> = {
  technical: ['技术', '技术面', 'technical'],
  fundamental: ['基本', '基本面', 'fundamental'],
  sentiment: ['情绪', 'sentiment'],
  policy: ['政策', 'news', 'policy'],
  debate: ['辩论', 'debate'],
  risk: ['风险', 'risk'],
  system: ['系统', '格式化', '生成', 'report'],
};

type ProgressMessage = {
  progress: number;
  message?: string;
  timestamp: string;
};

const detectAgentFromMessage = (message?: string): string | null => {
  if (!message) {
    return null;
  }

  for (const [agent, keywords] of Object.entries(AGENT_KEYWORDS)) {
    if (keywords.some((keyword) => keyword && message.includes(keyword))) {
      return agent;
    }
  }
  return null;
};

const mergeCompletedPrimaryAgents = (existing: string[], agentKey?: string | null): string[] => {
  if (!agentKey || !PRIMARY_AGENT_SET.has(agentKey)) {
    return existing;
  }
  if (existing.includes(agentKey)) {
    return existing;
  }
  return [...existing, agentKey];
};

const extractCompletedAgentsFromHistory = (messages?: ProgressMessage[]): string[] => {
  if (!messages || messages.length === 0) {
    return [];
  }

  return messages.reduce<string[]>((completed, entry) => {
    const agentKey = detectAgentFromMessage(entry.message);
    if (agentKey && PRIMARY_AGENT_SET.has(agentKey) && !completed.includes(agentKey)) {
      completed.push(agentKey);
    }
    return completed;
  }, []);
};

interface StreamingAnalysisState {
  taskId: string | null;          // 当前任务ID
  agentResults: Record<string, AgentAnalysisResult>;
  progress: string;                // Display format: "3/4" or "75%"
  progressPercent: number;         // Numeric progress (0-100)
  isAnalyzing: boolean;
  finalResult: AnalyzeAllResponse | null;
  error: string | null;
  isLLMAnalyzing: boolean;
  currentAgent: string;            // Currently analyzing agent
  currentMessage: string;          // Current progress message
  completedAgents: string[];       // 已完成的一线Agent
}

const TASK_ID_KEY = 'current_analysis_task_id';

export function useStreamingAnalysis() {
  const [state, setState] = useState<StreamingAnalysisState>({
    taskId: null,
    agentResults: {},
    progress: '0%',
    progressPercent: 0,
    isAnalyzing: false,
    finalResult: null,
    error: null,
    isLLMAnalyzing: false,
    currentAgent: '',
    currentMessage: '',
    completedAgents: [],
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  // 页面加载时，自动恢复未完成的任务
  useEffect(() => {
    const resumeTask = async () => {
      const savedTaskId = localStorage.getItem(TASK_ID_KEY);
      if (!savedTaskId) return;

      try {
        // 检查任务状态
        const task = await getTaskDetail(savedTaskId);

        if (task.status === 'running' || task.status === 'pending') {
          // 任务还在进行中，恢复连接
          console.log(`[Resume] 检测到进行中的任务: ${savedTaskId}, 正在恢复...`);
          const completedHistory = extractCompletedAgentsFromHistory(task.progress_messages as ProgressMessage[]);
          connectToTask(savedTaskId, task.symbol, completedHistory);
        } else if (task.status === 'completed' && task.result) {
          // 任务已完成，直接显示结果
          console.log(`[Resume] 任务已完成: ${savedTaskId}`);
          const completed = PRIMARY_AGENT_KEYS.filter((agent) => task.result?.agent_results?.[agent]);
          setState({
            taskId: savedTaskId,
            agentResults: task.result.agent_results || {},
            progress: '100%',
            progressPercent: 100,
            isAnalyzing: false,
            finalResult: task.result,
            error: null,
            isLLMAnalyzing: false,
            currentAgent: '',
            currentMessage: '分析已完成',
            completedAgents: completed,
          });
          // 清除localStorage
          localStorage.removeItem(TASK_ID_KEY);
        } else {
          // 任务失败或取消，清除
          localStorage.removeItem(TASK_ID_KEY);
        }
      } catch (error) {
        console.error('[Resume] 恢复任务失败:', error);
        localStorage.removeItem(TASK_ID_KEY);
      }
    };

    resumeTask();
  }, []);

  const connectToTask = useCallback((taskId: string, symbol: string, initialCompletedAgents: string[] = []) => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // 保存到localStorage以支持刷新恢复
    localStorage.setItem(TASK_ID_KEY, taskId);

    // 重置状态
    setState(prev => ({
      ...prev,
      taskId,
      agentResults: {},
      progress: '0%',
      progressPercent: 0,
      isAnalyzing: true,
      finalResult: null,
      error: null,
      isLLMAnalyzing: false,
      currentAgent: initialCompletedAgents.at(-1) || '',
      currentMessage: '连接中...',
      completedAgents: initialCompletedAgents,
    }));

    // 连接到task stream
    const eventSource = streamTaskProgress(taskId, {
      onStart: (event) => {
        console.log(`[SSE] 连接成功: ${event.symbol || symbol}`);
        setState(prev => ({
          ...prev,
          currentMessage: '分析系统初始化...',
        }));
      },

      onProgress: (event) => {
        console.log(`[SSE] 进度更新: ${event.progress}% - ${event.message}`);

        const progressPercent = event.progress || 0;
        const messageAgent = detectAgentFromMessage(event.message);

        setState(prev => {
          const currentAgent = event.agent || messageAgent || prev.currentAgent;
          const completedAgents = mergeCompletedPrimaryAgents(prev.completedAgents, messageAgent);
          const isLLMPhase = currentAgent ? (LLM_PHASE_AGENTS.has(currentAgent) && progressPercent >= 80) : prev.isLLMAnalyzing;

          return {
            ...prev,
            progress: `${progressPercent}%`,
            progressPercent,
            currentAgent,
            currentMessage: event.message || prev.currentMessage,
            isLLMAnalyzing: isLLMPhase,
            completedAgents,
          };
        });
      },

      onComplete: (data) => {
        console.log('[SSE] 分析完成', data);

        // 提取agent结果
        const agentResults: Record<string, AgentAnalysisResult> = {};
        if (data?.agent_results) {
          Object.entries(data.agent_results).forEach(([name, result]) => {
            agentResults[name] = result;
          });
        }

        setState(prev => ({
          ...prev,
          agentResults,
          finalResult: data,
          completedAgents: PRIMARY_AGENT_KEYS.filter((agent) => agentResults[agent]),
          isAnalyzing: false,
          isLLMAnalyzing: false,
          progress: '100%',
          progressPercent: 100,
          currentMessage: '分析完成',
        }));

        // 清除localStorage
        localStorage.removeItem(TASK_ID_KEY);
      },

      onError: (error) => {
        console.error('[SSE] 错误:', error);
        setState(prev => ({
          ...prev,
          error,
          isAnalyzing: false,
          isLLMAnalyzing: false,
        }));

        // 清除localStorage
        localStorage.removeItem(TASK_ID_KEY);
      },
    });

    eventSourceRef.current = eventSource;
  }, []);

  const startAnalysis = useCallback(async (symbol: string) => {
    try {
      // 1. 创建任务
      console.log(`[Analysis] 创建分析任务: ${symbol}`);
      const response = await createAnalysisTask(symbol);
      const taskId = response.task_id;

      console.log(`[Analysis] 任务创建成功: ${taskId}`);

      // 2. 连接到task stream
      connectToTask(taskId, symbol);

      return taskId;
    } catch (error) {
      console.error('[Analysis] 创建任务失败:', error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : '创建任务失败',
        isAnalyzing: false,
      }));
      return null;
    }
  }, [connectToTask]);

  const stopAnalysis = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // 清除localStorage
    if (state.taskId) {
      localStorage.removeItem(TASK_ID_KEY);
    }

    setState(prev => ({
      ...prev,
      isAnalyzing: false,
      isLLMAnalyzing: false,
      completedAgents: [],
    }));
  }, [state.taskId]);

  // 加载已完成任务的结果（用于查看历史记录）
  const loadTaskResult = useCallback(async (taskId: string) => {
    try {
      console.log(`[LoadTask] 加载任务结果: ${taskId}`);
      const task = await getTaskDetail(taskId);

      if (task.status === 'completed' && task.result) {
        // 提取agent结果
        const agentResults: Record<string, AgentAnalysisResult> = {};
        if (task.result.agent_results) {
          Object.entries(task.result.agent_results).forEach(([name, result]) => {
            agentResults[name] = result;
          });
        }

        setState({
          taskId,
          agentResults,
          finalResult: task.result,
          isAnalyzing: false,
          isLLMAnalyzing: false,
          progress: '100%',
          progressPercent: 100,
          currentMessage: '分析已完成',
          currentAgent: '',
          error: null,
          completedAgents: PRIMARY_AGENT_KEYS.filter((agent) => agentResults[agent]),
        });

        console.log(`[LoadTask] 任务结果已加载:`, task.result);
      } else if (task.status === 'running' || task.status === 'pending') {
        // 任务还在进行中，连接SSE
        const completedHistory = extractCompletedAgentsFromHistory(task.progress_messages as ProgressMessage[]);
        connectToTask(taskId, task.symbol, completedHistory);
      } else if (task.status === 'failed') {
        const completedHistory = extractCompletedAgentsFromHistory(task.progress_messages as ProgressMessage[]);
        setState({
          taskId,
          agentResults: {},
          finalResult: null,
          isAnalyzing: false,
          isLLMAnalyzing: false,
          progress: '0%',
          progressPercent: 0,
          currentMessage: '分析失败',
          currentAgent: '',
          error: task.error || '分析失败',
          completedAgents: completedHistory,
        });
      }
    } catch (error) {
      console.error('[LoadTask] 加载任务失败:', error);
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : '加载任务失败',
      }));
    }
  }, [connectToTask]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  return {
    ...state,
    startAnalysis,
    stopAnalysis,
    resumeTask: connectToTask,  // 暴露resume函数以便手动恢复
    loadTaskResult,  // 暴露加载函数用于查看历史记录
  };
}
