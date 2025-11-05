import { apiClient, extractData } from './client';
import { API_ENDPOINTS } from '@/config/api.config';
import type {
  Position,
  PortfolioSummary,
  PortfolioHistoryResponse,
} from '@/types/portfolio';

/**
 * Get portfolio summary
 */
export async function getPortfolioSummary(): Promise<PortfolioSummary> {
  const response = await apiClient.get<PortfolioSummary>(
    API_ENDPOINTS.portfolio.summary
  );
  return extractData(response.data);
}

/**
 * Get current positions
 */
export async function getCurrentPositions(): Promise<Position[]> {
  const response = await apiClient.get<Position[]>(
    API_ENDPOINTS.portfolio.positions
  );
  return extractData(response.data);
}

/**
 * Get position for a specific symbol
 */
export async function getPosition(symbol: string): Promise<Position> {
  const response = await apiClient.get<Position>(
    API_ENDPOINTS.portfolio.position(symbol)
  );
  return extractData(response.data);
}

/**
 * Get portfolio history
 */
export async function getPortfolioHistory(
  days?: number
): Promise<PortfolioHistoryResponse> {
  const response = await apiClient.get<PortfolioHistoryResponse>(
    API_ENDPOINTS.portfolio.history,
    {
      params: { days },
    }
  );
  return extractData(response.data);
}
