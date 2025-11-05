import { useState, useCallback, useRef, useEffect } from 'react';
import { API_CONFIG, API_ENDPOINTS } from '@/config/api.config';
import type { AnalyzeAllResponse, SSEAnalysisEvent } from '@/types/agent';

interface StreamingAnalysisState {
  agentResults: Record<string, {
    direction: string | null;
    confidence: number;
    score: number;
    reasoning: string;
    is_error: boolean;
  }>;
  progress: string;
  isAnalyzing: boolean;
  finalResult: AnalyzeAllResponse | null;
  error: string | null;
  isLLMAnalyzing: boolean;
}

export function useStreamingAnalysis() {
  const [state, setState] = useState<StreamingAnalysisState>({
    agentResults: {},
    progress: '0/0',
    isAnalyzing: false,
    finalResult: null,
    error: null,
    isLLMAnalyzing: false,
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  const startAnalysis = useCallback((symbol: string) => {
    // Reset state
    setState({
      agentResults: {},
      progress: '0/0',
      isAnalyzing: true,
      finalResult: null,
      error: null,
      isLLMAnalyzing: false,
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
        const data: SSEAnalysisEvent = JSON.parse(event.data);

        switch (data.type) {
          case 'start':
            console.log(`[SSE] 分析开始: ${data.symbol}`);
            break;

          case 'agent_result':
            // Update agent results
            setState(prev => ({
              ...prev,
              agentResults: {
                ...prev.agentResults,
                [data.agent_name]: data.result
              },
              progress: data.progress
            }));
            console.log(`[SSE] Agent完成: ${data.agent_name} - ${data.progress}`);
            break;

          case 'agent_error':
            console.error(`[SSE] Agent错误 ${data.agent_name}:`, data.error);
            break;

          case 'llm_start':
            setState(prev => ({ ...prev, isLLMAnalyzing: true }));
            console.log('[SSE] LLM分析开始...');
            break;

          case 'complete':
            // Final result received
            setState(prev => ({
              ...prev,
              finalResult: data.data,
              isAnalyzing: false,
              isLLMAnalyzing: false
            }));
            console.log('[SSE] 分析完成');
            eventSource.close();
            break;

          case 'llm_error':
            setState(prev => ({
              ...prev,
              error: `LLM分析错误: ${data.error}`,
              isAnalyzing: false,
              isLLMAnalyzing: false
            }));
            eventSource.close();
            break;

          case 'error':
            setState(prev => ({
              ...prev,
              error: data.error,
              isAnalyzing: false,
              isLLMAnalyzing: false
            }));
            eventSource.close();
            break;
        }
      } catch (err) {
        console.error('[SSE] 解析事件失败:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('[SSE] 连接错误:', err);
      setState(prev => ({
        ...prev,
        error: 'SSE连接断开',
        isAnalyzing: false,
        isLLMAnalyzing: false
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
