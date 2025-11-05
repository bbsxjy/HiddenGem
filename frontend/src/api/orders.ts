import { apiClient, extractData } from './client';
import { API_ENDPOINTS } from '@/config/api.config';
import type {
  Order,
  CreateOrderRequest,
  TradingSignal,
  RecentOrdersResponse,
  SignalStatsResponse,
} from '@/types/order';

/**
 * Create a new order
 */
export async function createOrder(orderData: CreateOrderRequest): Promise<Order> {
  const response = await apiClient.post<Order>(
    API_ENDPOINTS.orders.create,
    orderData
  );
  return extractData(response.data);
}

/**
 * Get orders list
 */
export async function getOrders(params?: {
  status?: string;
  limit?: number;
}): Promise<Order[]> {
  const response = await apiClient.get<Order[]>(
    API_ENDPOINTS.orders.list,
    { params }
  );
  return extractData(response.data);
}

/**
 * Get order details
 */
export async function getOrderDetail(orderId: number): Promise<Order> {
  const response = await apiClient.get<Order>(
    API_ENDPOINTS.orders.detail(orderId)
  );
  return extractData(response.data);
}

/**
 * Cancel an order
 */
export async function cancelOrder(orderId: number): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.delete<{ success: boolean; message: string }>(
    API_ENDPOINTS.orders.cancel(orderId)
  );
  return extractData(response.data);
}

/**
 * Get recent order history
 */
export async function getRecentOrders(days?: number): Promise<RecentOrdersResponse> {
  const response = await apiClient.get<RecentOrdersResponse>(
    API_ENDPOINTS.orders.recent,
    { params: { days } }
  );
  return extractData(response.data);
}

/**
 * Get current trading signals
 */
export async function getCurrentSignals(limit?: number): Promise<TradingSignal[]> {
  const response = await apiClient.get<TradingSignal[]>(
    API_ENDPOINTS.signals.current,
    { params: { limit } }
  );
  return extractData(response.data);
}

/**
 * Get signal history
 */
export async function getSignalHistory(params?: {
  days?: number;
  symbol?: string;
}): Promise<TradingSignal[]> {
  const response = await apiClient.get<TradingSignal[]>(
    API_ENDPOINTS.signals.history,
    { params }
  );
  return extractData(response.data);
}

/**
 * Get signal details
 */
export async function getSignalDetail(signalId: number): Promise<TradingSignal> {
  const response = await apiClient.get<TradingSignal>(
    API_ENDPOINTS.signals.detail(signalId)
  );
  return extractData(response.data);
}

/**
 * Get signal statistics
 */
export async function getSignalStats(days?: number): Promise<SignalStatsResponse> {
  const response = await apiClient.get<SignalStatsResponse>(
    API_ENDPOINTS.signals.stats,
    { params: { days } }
  );
  return extractData(response.data);
}
