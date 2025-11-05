import { apiClient, extractData } from './client';

interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
}

/**
 * Check API health
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>('/health');
  return extractData(response.data);
}
