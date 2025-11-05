// TradingView Lightweight Charts configuration
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const CHART_CONFIG: any = {
  layout: {
    background: { type: 'solid', color: '#ffffff' },
    textColor: '#111827',
  },
  grid: {
    vertLines: { color: '#e5e7eb', style: 0, visible: true },
    horzLines: { color: '#e5e7eb', style: 0, visible: true },
  },
  crosshair: {
    mode: 1,
    vertLine: { visible: true },
    horzLine: { visible: true },
  },
  rightPriceScale: {
    borderColor: '#e5e7eb',
  },
  timeScale: {
    borderColor: '#e5e7eb',
    timeVisible: true,
    secondsVisible: false,
  },
};

// Candlestick series options
export const CANDLESTICK_OPTIONS = {
  upColor: '#16a34a',
  downColor: '#dc2626',
  borderVisible: false,
  wickUpColor: '#16a34a',
  wickDownColor: '#dc2626',
};

// Volume series options
export const VOLUME_OPTIONS = {
  color: '#9ca3af',
  priceFormat: {
    type: 'volume' as const,
  },
  priceScaleId: '',
  scaleMargins: {
    top: 0.8,
    bottom: 0,
  },
};

// Line series options for indicators
export const LINE_OPTIONS = {
  color: '#3b82f6',
  lineWidth: 2,
};

// Recharts default configuration
export const RECHARTS_CONFIG = {
  margin: { top: 5, right: 30, left: 20, bottom: 5 },
  animationDuration: 300,
};

// Color scheme for different chart types
export const CHART_COLORS = {
  profit: '#16a34a',
  loss: '#dc2626',
  neutral: '#6b7280',
  primary: '#0ea5e9',
  secondary: '#8b5cf6',
  warning: '#f59e0b',
  // Board colors
  mainBoard: '#3b82f6',
  chinext: '#8b5cf6',
  star: '#f59e0b',
  // Multi-line colors for comparison
  lines: [
    '#0ea5e9',
    '#8b5cf6',
    '#f59e0b',
    '#10b981',
    '#ef4444',
    '#6366f1',
  ],
};

// Default time ranges
export const TIME_RANGES = [
  { label: '1D', value: '1d', days: 1 },
  { label: '1W', value: '1w', days: 7 },
  { label: '1M', value: '1m', days: 30 },
  { label: '3M', value: '3m', days: 90 },
  { label: '1Y', value: '1y', days: 365 },
  { label: 'All', value: 'all', days: null },
] as const;
