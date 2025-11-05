import { apiClient, extractData } from './client';
import { API_ENDPOINTS } from '@/config/api.config';
import type {
  Strategy,
  CreateStrategyRequest,
  UpdateStrategyRequest,
  BacktestConfig,
  BacktestResult,
  StrategyStats,
} from '@/types/strategy';

/**
 * Get all strategies
 */
export async function getStrategies(): Promise<Strategy[]> {
  const response = await apiClient.get<Strategy[]>(
    API_ENDPOINTS.strategies.list
  );
  return extractData(response.data);
}

/**
 * Create a new strategy
 */
export async function createStrategy(data: CreateStrategyRequest): Promise<Strategy> {
  const response = await apiClient.post<Strategy>(
    API_ENDPOINTS.strategies.create,
    data
  );
  return extractData(response.data);
}

/**
 * Get strategy details
 */
export async function getStrategyDetail(strategyName: string): Promise<Strategy> {
  const response = await apiClient.get<Strategy>(
    API_ENDPOINTS.strategies.detail(strategyName)
  );
  return extractData(response.data);
}

/**
 * Update strategy
 */
export async function updateStrategy(
  strategyName: string,
  data: UpdateStrategyRequest
): Promise<Strategy> {
  const response = await apiClient.patch<Strategy>(
    API_ENDPOINTS.strategies.update(strategyName),
    data
  );
  return extractData(response.data);
}

/**
 * Delete strategy
 */
export async function deleteStrategy(strategyName: string): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.delete<{ success: boolean; message: string }>(
    API_ENDPOINTS.strategies.delete(strategyName)
  );
  return extractData(response.data);
}

/**
 * Run backtest for a strategy
 */
export async function runBacktest(
  strategyName: string,
  config: BacktestConfig
): Promise<BacktestResult> {
  const response = await apiClient.post<BacktestResult>(
    API_ENDPOINTS.strategies.backtest(strategyName),
    config
  );
  return extractData(response.data);
}

/**
 * Get strategy statistics
 */
export async function getStrategyStats(
  strategyName: string
): Promise<StrategyStats> {
  const response = await apiClient.get<StrategyStats>(
    API_ENDPOINTS.strategies.stats(strategyName)
  );
  return extractData(response.data);
}
