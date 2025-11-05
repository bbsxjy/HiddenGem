// Application constants

export const APP_NAME = 'HiddenGem Trading System';
export const APP_VERSION = '0.1.0';

// Trading constants
export const TRADING_HOURS = {
  MORNING_START: '09:30',
  MORNING_END: '11:30',
  AFTERNOON_START: '13:00',
  AFTERNOON_END: '15:00',
} as const;

export const TRADING_DAYS_PER_YEAR = 252;

// Board types and limits
export const BOARD_CONFIG = {
  main: {
    name: '主板',
    priceLimit: 0.1,
    minCapital: 0,
    color: '#3b82f6',
  },
  chinext: {
    name: '创业板',
    priceLimit: 0.2,
    minCapital: 100000,
    color: '#8b5cf6',
  },
  star: {
    name: '科创板',
    priceLimit: 0.2,
    minCapital: 500000,
    color: '#f59e0b',
  },
} as const;

// Agent names
export const AGENTS = {
  POLICY: 'policy',
  MARKET: 'market',
  TECHNICAL: 'technical',
  FUNDAMENTAL: 'fundamental',
  SENTIMENT: 'sentiment',
  RISK: 'risk',
  EXECUTION: 'execution',
} as const;

export const AGENT_DISPLAY_NAMES = {
  policy: '政策分析',
  market: '市场监控',
  technical: '技术分析',
  fundamental: '基本面分析',
  sentiment: '情绪分析',
  risk: '风险管理',
  execution: '执行代理',
} as const;

// Risk management
export const RISK_LIMITS = {
  MAX_POSITION_SIZE: 0.1, // 10%
  MAX_SECTOR_EXPOSURE: 0.3, // 30%
  DEFAULT_STOP_LOSS: 0.08, // 8%
  DEFAULT_TAKE_PROFIT: 0.15, // 15%
} as const;

// Order constants
export const ORDER_TYPES = ['market', 'limit'] as const;
export const ORDER_SIDES = ['buy', 'sell'] as const;
export const ORDER_STATUSES = [
  'pending',
  'submitted',
  'partial',
  'filled',
  'cancelled',
  'rejected',
  'expired',
] as const;

// Pagination
export const DEFAULT_PAGE_SIZE = 20;
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;

// Refresh intervals (milliseconds)
export const REFRESH_INTERVALS = {
  MARKET_DATA: 3000, // 3 seconds
  PORTFOLIO: 5000, // 5 seconds
  ORDERS: 2000, // 2 seconds
  AGENTS: 10000, // 10 seconds
} as const;

// Chart time ranges
export const TIME_RANGE_DAYS = {
  '1d': 1,
  '1w': 7,
  '1m': 30,
  '3m': 90,
  '1y': 365,
} as const;

// WebSocket reconnection
export const WS_RECONNECT = {
  MAX_ATTEMPTS: 5,
  INITIAL_DELAY: 1000,
  MAX_DELAY: 30000,
  MULTIPLIER: 2,
} as const;

// API retry configuration
export const API_RETRY = {
  MAX_ATTEMPTS: 3,
  DELAY: 1000,
} as const;

// Local storage keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'hg_auth_token',
  USER_PREFERENCES: 'hg_user_preferences',
  THEME: 'hg_theme',
  SIDEBAR_STATE: 'hg_sidebar_state',
} as const;

// Date formats
export const DATE_FORMATS = {
  DATE: 'yyyy-MM-dd',
  DATETIME: 'yyyy-MM-dd HH:mm:ss',
  TIME: 'HH:mm:ss',
  MONTH: 'yyyy-MM',
  YEAR: 'yyyy',
} as const;

// Error messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: '网络连接失败，请检查网络设置',
  UNAUTHORIZED: '未授权，请重新登录',
  SERVER_ERROR: '服务器错误，请稍后重试',
  INVALID_INPUT: '输入数据无效',
  NOT_FOUND: '请求的资源不存在',
} as const;

// Success messages
export const SUCCESS_MESSAGES = {
  ORDER_CREATED: '订单创建成功',
  ORDER_CANCELLED: '订单取消成功',
  SETTINGS_SAVED: '设置保存成功',
  BACKTEST_STARTED: '回测已开始',
} as const;

// Notification durations (milliseconds)
export const NOTIFICATION_DURATION = {
  SUCCESS: 3000,
  ERROR: 5000,
  WARNING: 4000,
  INFO: 3000,
} as const;
