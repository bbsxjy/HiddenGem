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
