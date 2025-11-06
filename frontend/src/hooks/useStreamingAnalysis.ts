import { useState, useCallback, useRef, useEffect } from 'react';
import { API_CONFIG, API_ENDPOINTS } from '@/config/api.config';
import type { AnalyzeAllResponse, AgentAnalysisResult } from '@/types/agent';

/**
 * SSE Event from backend (actual format from api/main.py)
 */
interface SSEEvent {
  type: 'start' | 'progress' | 'complete' | 'error';
  symbol?: string;
  agent?: string;           // Agent name: technical, fundamental, sentiment, policy, debate, risk, system
  status?: string;          // analyzing, complete, etc.
  message?: string;         // Progress message
  progress?: number;        // Progress percentage (0-100)
  data?: AnalyzeAllResponse; // Final result
  error?: string;
  timestamp: string;
}

interface StreamingAnalysisState {
  agentResults: Record<string, AgentAnalysisResult>;
  progress: string;         // Display format: "3/4" or "75%"
  progressPercent: number;  // Numeric progress (0-100)
  isAnalyzing: boolean;
  finalResult: AnalyzeAllResponse | null;
  error: string | null;
  isLLMAnalyzing: boolean;
  currentAgent: string;     // Currently analyzing agent
  currentMessage: string;   // Current progress message
}

export function useStreamingAnalysis() {
  const [state, setState] = useState<StreamingAnalysisState>({
    agentResults: {},
    progress: '0%',
    progressPercent: 0,
    isAnalyzing: false,
    finalResult: null,
    error: null,
    isLLMAnalyzing: false,
    currentAgent: '',
    currentMessage: '',
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  const startAnalysis = useCallback((symbol: string) => {
    // Reset state
    setState({
      agentResults: {},
      progress: '0%',
      progressPercent: 0,
      isAnalyzing: true,
      finalResult: null,
      error: null,
      isLLMAnalyzing: false,
      currentAgent: '',
      currentMessage: '',
    });

    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Create SSE connection
    const url = `${API_CONFIG.baseURL}${API_ENDPOINTS.agents.analyzeAllStream(symbol)}`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);

        switch (data.type) {
          case 'start':
            console.log(`[SSE] 🚀 分析开始: ${data.symbol}`);
            setState(prev => ({
              ...prev,
              currentMessage: '初始化分析系统...',
            }));
            break;

          case 'progress':
            // Update progress based on agent and message
            const progressPercent = data.progress || 0;
            const progressDisplay = `${progressPercent}%`;

            // Detect if LLM is analyzing (debate, risk, or high progress)
            const isLLMPhase =
              data.agent === 'debate' ||
              data.agent === 'risk' ||
              data.agent === 'system' && progressPercent > 80;

            console.log(`[SSE] 📊 进度更新: [${data.agent}] ${data.message} - ${progressPercent}%`);

            setState(prev => ({
              ...prev,
              progress: progressDisplay,
              progressPercent,
              currentAgent: data.agent || prev.currentAgent,
              currentMessage: data.message || prev.currentMessage,
              isLLMAnalyzing: isLLMPhase,
            }));
            break;

          case 'complete':
            // Final result received
            console.log('[SSE] ✅ 分析完成', data.data);

            // Extract agent results from final data
            const agentResults: Record<string, AgentAnalysisResult> = {};
            if (data.data?.agent_results) {
              Object.entries(data.data.agent_results).forEach(([name, result]) => {
                agentResults[name] = result;
              });
            }

            setState(prev => ({
              ...prev,
              agentResults,
              finalResult: data.data || null,
              isAnalyzing: false,
              isLLMAnalyzing: false,
              progress: '100%',
              progressPercent: 100,
              currentMessage: '分析完成',
            }));
            eventSource.close();
            break;

          case 'error':
            console.error('[SSE] ❌ 错误:', data.error);
            setState(prev => ({
              ...prev,
              error: data.error || 'Unknown error',
              isAnalyzing: false,
              isLLMAnalyzing: false,
            }));
            eventSource.close();
            break;
        }
      } catch (err) {
        console.error('[SSE] 解析事件失败:', err, event.data);
      }
    };

    eventSource.onerror = (err) => {
      console.error('[SSE] 连接错误:', err);
      setState(prev => ({
        ...prev,
        error: 'SSE连接断开或服务器错误',
        isAnalyzing: false,
        isLLMAnalyzing: false,
      }));
      eventSource.close();
    };
  }, []);

  const stopAnalysis = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setState(prev => ({
      ...prev,
      isAnalyzing: false,
      isLLMAnalyzing: false
    }));
  }, []);

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
  };
}
