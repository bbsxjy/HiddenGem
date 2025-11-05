import { apiClient, extractData } from './client';
import { API_ENDPOINTS } from '@/config/api.config';
import type {
  AgentConfig,
  AgentAnalysisResult,
  AnalyzeAllResponse,
  AgentPerformanceResponse,
  AgentName,
} from '@/types/agent';

/**
 * Get all agents status
 */
export async function getAgentsStatus(): Promise<AgentConfig[]> {
  const response = await apiClient.get<AgentConfig[]>(
    API_ENDPOINTS.agents.status
  );
  return extractData(response.data);
}

/**
 * Analyze using a specific agent
 */
export async function analyzeWithAgent(
  agentName: AgentName,
  symbol: string
): Promise<AgentAnalysisResult> {
  const response = await apiClient.post<AgentAnalysisResult>(
    API_ENDPOINTS.agents.analyze(agentName),
    { symbol }
  );
  return extractData(response.data);
}

/**
 * Analyze using all agents
 */
export async function analyzeWithAllAgents(
  symbol: string
): Promise<AnalyzeAllResponse> {
  const response = await apiClient.post<AnalyzeAllResponse>(
    API_ENDPOINTS.agents.analyzeAll(symbol)
  );
  return extractData(response.data);
}

/**
 * Get agents performance metrics
 */
export async function getAgentsPerformance(): Promise<AgentPerformanceResponse> {
  const response = await apiClient.get<AgentPerformanceResponse>(
    API_ENDPOINTS.agents.performance
  );
  return extractData(response.data);
}
