import { apiClient, extractData } from './client';
import { API_ENDPOINTS } from '@/config/api.config';
import type {
  Quote,
  BarsResponse,
  StockInfo,
  StockSearchResult,
  TechnicalIndicators,
} from '@/types/market';

/**
 * Get real-time quote for a symbol
 */
export async function getQuote(symbol: string): Promise<Quote> {
  const response = await apiClient.get<Quote>(
    API_ENDPOINTS.market.quote(symbol)
  );
  return extractData(response.data);
}

/**
 * Get historical bars (OHLCV) for a symbol
 */
export async function getBars(
  symbol: string,
  params?: {
    start_date?: string;
    end_date?: string;
    days?: number;
  }
): Promise<BarsResponse> {
  const response = await apiClient.get<BarsResponse>(
    API_ENDPOINTS.market.bars(symbol),
    { params }
  );
  return extractData(response.data);
}

/**
 * Get technical indicators for a symbol
 */
export async function getTechnicalIndicators(
  symbol: string,
  days?: number
): Promise<TechnicalIndicators> {
  const response = await apiClient.get<TechnicalIndicators>(
    API_ENDPOINTS.market.indicators(symbol),
    { params: { days } }
  );
  return extractData(response.data);
}

/**
 * Search stocks by query
 */
export async function searchStocks(
  query: string,
  limit?: number
): Promise<StockSearchResult> {
  const response = await apiClient.get<StockSearchResult>(
    API_ENDPOINTS.market.search,
    {
      params: { query, limit },
    }
  );
  return extractData(response.data);
}

/**
 * Get stock basic information
 */
export async function getStockInfo(symbol: string): Promise<StockInfo> {
  const response = await apiClient.get<StockInfo>(
    API_ENDPOINTS.market.info(symbol)
  );
  return extractData(response.data);
}
