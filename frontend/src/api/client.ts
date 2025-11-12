import axios from 'axios';
import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { API_CONFIG, API_RETRY, NO_RETRY_ENDPOINTS } from '@/config/api.config';
import type { ApiError } from '@/types/api';

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 检查是否是长时间操作，设置更长的timeout
    const isLongOperation = NO_RETRY_ENDPOINTS.some(endpoint =>
      config.url?.includes(endpoint)
    );

    if (isLongOperation) {
      config.timeout = API_CONFIG.longTimeout;
      // 标记为长时间操作，阻止重试
      (config as any)._isLongOperation = true;
    }

    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    // Convert string numbers to actual numbers for market data
    if (response.data && typeof response.data === 'object') {
      response.data = convertNumericFields(response.data);
    }
    return response;
  },
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
      return Promise.reject(error);
    }

    // 检查是否是长时间操作，如果是则不重试
    const isLongOperation = (originalRequest as any)?._isLongOperation;

    // Retry logic for network errors (但不重试长时间操作)
    if (!error.response && originalRequest && !isLongOperation) {
      const retryCount = (originalRequest as any)._retryCount || 0;

      if (retryCount < API_RETRY.attempts) {
        (originalRequest as any)._retryCount = retryCount + 1;

        await new Promise((resolve) =>
          setTimeout(resolve, API_RETRY.delay * Math.pow(2, retryCount))
        );

        return apiClient(originalRequest);
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Convert string numeric fields to actual numbers
 * Handles cases where backend returns Decimal as strings
 */
function convertNumericFields(data: any): any {
  if (data === null || data === undefined) {
    return data;
  }

  // Handle arrays
  if (Array.isArray(data)) {
    return data.map(item => convertNumericFields(item));
  }

  // Handle objects
  if (typeof data === 'object') {
    const converted: any = {};
    for (const key in data) {
      const value = data[key];

      // Fields that should never be converted to numbers
      const dateFields = ['date', 'timestamp', 'created_at', 'updated_at'];

      // Convert string numbers to actual numbers for known numeric fields
      const numericFields = [
        // Quote fields
        'price', 'last_price', 'open', 'high', 'low', 'volume', 'close',
        'change', 'change_pct', 'change_percent',
        // Portfolio fields
        'total_value', 'cash', 'positions_value', 'total_pnl', 'daily_pnl',
        'market_value', 'unrealized_pnl', 'avg_cost', 'current_price',
        'unrealized_pnl_pct', 'num_positions',
        // Trading fields
        'entry_price', 'target_price', 'stop_loss_price', 'confidence',
        'strength', 'score', 'position_size',
        // Technical indicators
        'rsi', 'macd', 'macd_signal', 'macd_hist',
        'ma_5', 'ma_20', 'ma_60',
        'kdj_k', 'kdj_d', 'kdj_j',
        'bb_upper', 'bb_middle', 'bb_lower',
        'atr', 'adx',
        // Count fields
        'count', 'calculated_from_days', 'quantity'
      ];

      // Skip date fields - keep as strings
      if (dateFields.includes(key)) {
        converted[key] = value;
      } else if (numericFields.includes(key) && typeof value === 'string' && !isNaN(Number(value))) {
        converted[key] = Number(value);
      } else if (typeof value === 'object') {
        converted[key] = convertNumericFields(value);
      } else {
        converted[key] = value;
      }
    }
    return converted;
  }

  return data;
}

/**
 * Extract data from API response
 * Backend wraps responses in {success: true, data: ..., timestamp: ...}
 */
export function extractData<T>(response: any): T {
  // If response has a 'data' field and 'success' field, extract data
  if (response && typeof response === 'object' && 'data' in response && 'success' in response) {
    return response.data as T;
  }
  // Otherwise return response directly (for endpoints that don't wrap)
  return response as T;
}

/**
 * Handle API errors
 */
export function handleApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiError>;

    if (axiosError.response?.data) {
      return axiosError.response.data;
    }

    return {
      code: axiosError.code || 'UNKNOWN_ERROR',
      message: axiosError.message || '未知错误',
    };
  }

  return {
    code: 'UNKNOWN_ERROR',
    message: error instanceof Error ? error.message : '未知错误',
  };
}
