export const API_CONFIG = {
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  wsURL: import.meta.env.VITE_WS_URL || 'ws://localhost:8000',
  timeout: 30000,  // 默认30秒（普通请求）
  longTimeout: 360000,  // 长时间操作：360秒=6分钟（Agent分析）
  retryAttempts: 3,
  retryDelay: 1000,
} as const;

export const API_RETRY = {
  attempts: API_CONFIG.retryAttempts,
  delay: API_CONFIG.retryDelay,
} as const;

// 长时间操作不重试的endpoint列表
export const NO_RETRY_ENDPOINTS = [
  '/api/v1/agents/analyze-all',  // Agent分析可能需要5分钟
  '/api/v1/strategies/backtest',  // 回测可能需要很长时间
] as const;

export const API_ENDPOINTS = {
  // Strategy endpoints - aligned with backend API.md
  strategies: {
    list: '/api/v1/strategies/',
    create: '/api/v1/strategies/',
    detail: (strategyName: string) => `/api/v1/strategies/${strategyName}`,
    update: (strategyName: string) => `/api/v1/strategies/${strategyName}`,
    delete: (strategyName: string) => `/api/v1/strategies/${strategyName}`,
    backtest: (strategyName: string) => `/api/v1/strategies/${strategyName}/backtest`,
    stats: (strategyName: string) => `/api/v1/strategies/${strategyName}/stats`,
  },
  // Market endpoints - aligned with backend API.md
  market: {
    quote: (symbol: string) => `/api/v1/market/quote/${symbol}`,
    bars: (symbol: string) => `/api/v1/market/bars/${symbol}`,
    indicators: (symbol: string) => `/api/v1/market/indicators/${symbol}`,
    search: '/api/v1/market/search',
    info: (symbol: string) => `/api/v1/market/info/${symbol}`,
  },
  // Portfolio endpoints - aligned with backend API.md
  portfolio: {
    summary: '/api/v1/portfolio/summary',
    positions: '/api/v1/portfolio/positions',
    position: (symbol: string) => `/api/v1/portfolio/positions/${symbol}`,
    history: '/api/v1/portfolio/history',
  },
  // Order endpoints - aligned with backend API.md
  orders: {
    create: '/api/v1/orders/',
    list: '/api/v1/orders/',
    detail: (orderId: number) => `/api/v1/orders/${orderId}`,
    cancel: (orderId: number) => `/api/v1/orders/${orderId}`,
    recent: '/api/v1/orders/history/recent',
  },
  // Agent endpoints - aligned with backend API.md
  agents: {
    status: '/api/v1/agents/status',
    analyze: (agentName: string) => `/api/v1/agents/analyze/${agentName}`,
    analyzeAll: (symbol: string) => `/api/v1/agents/analyze-all/${symbol}`,
    analyzeAllStream: (symbol: string) => `/api/v1/agents/analyze-all-stream/${symbol}`,  // 新增：流式API
    performance: '/api/v1/agents/performance',
  },
  // Signal endpoints - aligned with backend API.md
  signals: {
    current: '/api/v1/signals/current',
    history: '/api/v1/signals/history',
    detail: (signalId: number) => `/api/v1/signals/${signalId}`,
    stats: '/api/v1/signals/stats/summary',
  },
} as const;

export const WS_CHANNELS = {
  market: '/ws/market',
  orders: '/ws/orders',
  portfolio: '/ws/portfolio',
  agents: '/ws/agents',
} as const;
