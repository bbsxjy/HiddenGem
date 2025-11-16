import { apiClient, extractData } from './client';
import { API_ENDPOINTS } from '@/config/api.config';
import type { ApiResponse } from '@/types/api';
import type {
  AgentStatus,
  AgentAnalysisResult,
  AnalyzeAllResponse,
  AgentPerformanceResponse,
  AgentName,
  PositionAnalysisRequest,
  PositionAnalysisResponse,
} from '@/types/agent';

/**
 * Get all agents status
 * GET /api/v1/agents/status
 *
 * Returns the status of all available agents including their
 * enabled state and weight configuration.
 */
export async function getAgentsStatus(): Promise<AgentStatus[]> {
  const response = await apiClient.get<ApiResponse<AgentStatus[]>>(
    API_ENDPOINTS.agents.status
  );
  return extractData(response.data);
}

/**
 * Analyze using a specific agent
 * POST /api/v1/agents/analyze/{agentName}
 *
 * @deprecated This endpoint may not be available in the current backend
 */
export async function analyzeWithAgent(
  agentName: AgentName,
  symbol: string
): Promise<AgentAnalysisResult> {
  const response = await apiClient.post<ApiResponse<AgentAnalysisResult>>(
    API_ENDPOINTS.agents.analyze(agentName),
    { symbol }
  );
  return extractData(response.data);
}

/**
 * Analyze using all agents - Complete stock analysis
 * POST /api/v1/agents/analyze-all/{symbol}
 *
 * This is the core endpoint that runs analysis through all 4 agents:
 * - technical (market analyst)
 * - fundamental (fundamentals analyst)
 * - sentiment (sentiment analyst)
 * - policy (news/policy analyst)
 *
 * The analysis includes:
 * 1. Individual agent results
 * 2. Aggregated trading signal
 * 3. LLM comprehensive analysis
 *
 * @param symbol - Stock symbol (e.g., 'NVDA', '000001.SZ', '600036.SS', '0700.HK')
 * @param analysisDate - Optional analysis date in 'YYYY-MM-DD' format. Defaults to current date.
 * @returns Complete analysis response with agent results and recommendations
 *
 * @example
 * // Analyze NVDA using current date
 * const result = await analyzeWithAllAgents('NVDA');
 *
 * @example
 * // Analyze with specific date
 * const result = await analyzeWithAllAgents('NVDA', '2024-05-10');
 */
export async function analyzeWithAllAgents(
  symbol: string,
  analysisDate?: string
): Promise<AnalyzeAllResponse> {
  const response = await apiClient.post<ApiResponse<AnalyzeAllResponse>>(
    API_ENDPOINTS.agents.analyzeAll(symbol),
    analysisDate ? { analysis_date: analysisDate } : undefined
  );
  return extractData(response.data);
}

/**
 * Get agents performance metrics
 * GET /api/v1/agents/performance
 *
 * @deprecated This endpoint may not be available in the current backend
 */
export async function getAgentsPerformance(): Promise<AgentPerformanceResponse> {
  const response = await apiClient.get<ApiResponse<AgentPerformanceResponse>>(
    API_ENDPOINTS.agents.performance
  );
  return extractData(response.data);
}

/**
 * Analyze position with holdings information
 * POST /api/v1/agents/analyze-position/{symbol}
 *
 * Provides decision recommendations for existing positions:
 * - Whether to sell/hold/add more
 * - Suggested price points
 * - Recovery analysis if position is losing
 * - Risk assessment considering both market and holdings cost
 *
 * @param symbol - Stock symbol (e.g., 'NVDA', '000001.SZ', '600036.SS', '0700.HK')
 * @param request - Position analysis request including holdings info
 * @returns Complete position analysis with decision recommendations
 *
 * @example
 * // Analyze position with holdings
 * const holdings = {
 *   quantity: 1000,
 *   avg_price: 45.50,
 *   purchase_date: "2024-12-01",
 *   current_price: 42.30
 * };
 * const result = await analyzePosition('300502', { holdings });
 */
export async function analyzePosition(
  symbol: string,
  request: PositionAnalysisRequest
): Promise<PositionAnalysisResponse> {
  const response = await apiClient.post<ApiResponse<PositionAnalysisResponse>>(
    API_ENDPOINTS.agents.analyzePosition(symbol),
    request
  );
  return extractData(response.data);
}

/**
 * Streaming API types
 */
export type StreamEventType = 'start' | 'progress' | 'complete' | 'error';

export interface StreamEvent {
  type: StreamEventType;
  symbol?: string;
  agent?: string;
  status?: string;
  message?: string;
  progress?: number;
  data?: AnalyzeAllResponse;
  error?: string;
  timestamp: string;
}

export interface StreamCallbacks {
  onStart?: (event: StreamEvent) => void;
  onProgress?: (event: StreamEvent) => void;
  onComplete?: (data: AnalyzeAllResponse) => void;
  onError?: (error: string) => void;
}

/**
 * Analyze using all agents with streaming updates (Server-Sent Events)
 * GET /api/v1/agents/analyze-all-stream/{symbol}
 *
 * This provides real-time progress updates as each agent completes its analysis.
 * Much better UX than waiting for the entire analysis to complete (30-60 seconds).
 *
 * @param symbol - Stock symbol (e.g., 'NVDA', '000001.SZ', '600036.SS', '0700.HK')
 * @param callbacks - Event callbacks for different stages
 * @param analysisDate - Optional analysis date in 'YYYY-MM-DD' format
 * @returns EventSource instance (can be used to abort the stream)
 *
 * @example
 * ```typescript
 * const eventSource = analyzeWithAllAgentsStream('NVDA', {
 *   onStart: (event) => console.log('Analysis started:', event.symbol),
 *   onProgress: (event) => {
 *     console.log(`[${event.agent}] ${event.message} - ${event.progress}%`);
 *   },
 *   onComplete: (data) => {
 *     console.log('Analysis complete:', data);
 *     // Update UI with final results
 *   },
 *   onError: (error) => console.error('Analysis failed:', error)
 * });
 *
 * // To abort the stream:
 * eventSource.close();
 * ```
 */
export function analyzeWithAllAgentsStream(
  symbol: string,
  callbacks: StreamCallbacks,
  analysisDate?: string
): EventSource {
  const baseUrl = API_ENDPOINTS.agents.analyzeAllStream(symbol).replace('/api/v1', '');
  const fullUrl = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1${baseUrl}${
    analysisDate ? `?analysis_date=${analysisDate}` : ''
  }`;

  const eventSource = new EventSource(fullUrl);

  eventSource.onmessage = (event) => {
    try {
      const data: StreamEvent = JSON.parse(event.data);

      switch (data.type) {
        case 'start':
          callbacks.onStart?.(data);
          break;

        case 'progress':
          callbacks.onProgress?.(data);
          break;

        case 'complete':
          if (data.data) {
            callbacks.onComplete?.(data.data);
          }
          eventSource.close();
          break;

        case 'error':
          callbacks.onError?.(data.error || 'Unknown error');
          eventSource.close();
          break;
      }
    } catch (error) {
      console.error('Failed to parse SSE event:', error);
      callbacks.onError?.('Failed to parse server response');
    }
  };

  eventSource.onerror = (error) => {
    console.error('EventSource error:', error);
    callbacks.onError?.('Connection to server lost');
    eventSource.close();
  };

  return eventSource;
}

/**
 * Task Management APIs
 */

export interface AnalysisTask {
  task_id: string;
  task_type: string;
  symbol: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  result: AnalyzeAllResponse | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  metadata: Record<string, any>;
  progress_messages: Array<{
    progress: number;
    message: string;
    timestamp: string;
  }>;
}

export interface CreateTaskResponse {
  success: boolean;
  task_id: string;
  symbol: string;
  message: string;
  status_url: string;
  timestamp: string;
}

/**
 * Create an analysis task (async version)
 * POST /api/v1/agents/analyze-all-async/{symbol}
 *
 * Creates a background analysis task and returns immediately with a task_id.
 * Use getTaskDetail() or streamTaskProgress() to monitor progress.
 *
 * @param symbol - Stock symbol
 * @param analysisDate - Optional analysis date
 * @returns Task creation response with task_id
 */
export async function createAnalysisTask(
  symbol: string,
  analysisDate?: string
): Promise<CreateTaskResponse> {
  const response = await apiClient.post<CreateTaskResponse>(
    API_ENDPOINTS.agents.analyzeAllAsync(symbol),
    analysisDate ? { trade_date: analysisDate } : undefined
  );
  return response.data;
}

/**
 * Get task detail and result
 * GET /api/v1/agents/tasks/{taskId}
 *
 * @param taskId - Task ID
 * @returns Task detail with status and result
 */
export async function getTaskDetail(taskId: string): Promise<AnalysisTask> {
  const response = await apiClient.get<ApiResponse<AnalysisTask>>(
    API_ENDPOINTS.agents.taskDetail(taskId)
  );
  return extractData(response.data);
}

/**
 * Get task list (history)
 * GET /api/v1/agents/tasks
 *
 * @param options - Filter options
 * @returns List of tasks
 */
export async function getTaskList(options?: {
  status?: string;
  symbol?: string;
  limit?: number;
}): Promise<AnalysisTask[]> {
  const params = new URLSearchParams();
  if (options?.status) params.append('status', options.status);
  if (options?.symbol) params.append('symbol', options.symbol);
  if (options?.limit) params.append('limit', options.limit.toString());

  const url = `${API_ENDPOINTS.agents.taskList}?${params.toString()}`;
  const response = await apiClient.get<ApiResponse<AnalysisTask[]>>(url);
  return extractData(response.data);
}

/**
 * Cancel a task
 * DELETE /api/v1/agents/tasks/{taskId}
 *
 * @param taskId - Task ID
 * @returns Success response
 */
export async function cancelTask(taskId: string): Promise<void> {
  await apiClient.delete(API_ENDPOINTS.agents.taskCancel(taskId));
}

/**
 * Stream task progress via SSE (supports reconnection)
 * GET /api/v1/agents/tasks/{taskId}/stream
 *
 * This allows reconnecting to an existing task after page refresh.
 * It will immediately return the result if the task is already completed.
 *
 * @param taskId - Task ID
 * @param callbacks - Event callbacks
 * @returns EventSource instance
 */
export function streamTaskProgress(
  taskId: string,
  callbacks: StreamCallbacks & {
    onAgentComplete?: (agent: string, result: AgentAnalysisResult) => void;
  }
): EventSource {
  const baseUrl = API_ENDPOINTS.agents.taskStream(taskId).replace('/api/v1', '');
  const fullUrl = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1${baseUrl}`;

  const eventSource = new EventSource(fullUrl);

  eventSource.onmessage = (event) => {
    try {
      const data: StreamEvent & {
        task_id?: string;
        result?: AgentAnalysisResult;
      } = JSON.parse(event.data);

      switch (data.type) {
        case 'start':
          callbacks.onStart?.(data);
          break;

        case 'progress':
          callbacks.onProgress?.(data);
          break;

        case 'complete':
          if (data.data) {
            callbacks.onComplete?.(data.data);
          }
          eventSource.close();
          break;

        case 'error':
          callbacks.onError?.(data.error || 'Unknown error');
          eventSource.close();
          break;
      }
    } catch (error) {
      console.error('Failed to parse SSE event:', error);
      callbacks.onError?.('Failed to parse server response');
    }
  };

  eventSource.onerror = (error) => {
    console.error('EventSource error:', error);
    callbacks.onError?.('Connection to server lost');
    eventSource.close();
  };

  return eventSource;
}
