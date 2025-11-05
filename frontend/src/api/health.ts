import { apiClient, extractData } from './client';
import type { ApiResponse } from '@/types/api';

/**
 * Health check response - aligned with backend API_DOCUMENTATION.md
 */
interface HealthResponse {
  status: string;                    // Health status (e.g., 'healthy')
  service: string;                   // Service name
  trading_graph_initialized: boolean; // Whether TradingGraph is initialized
  timestamp: string;                 // Timestamp (ISO 8601 format)
}

/**
 * Check API health
 * GET /health
 *
 * Note: The health endpoint returns data directly without ApiResponse wrapper
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
}
