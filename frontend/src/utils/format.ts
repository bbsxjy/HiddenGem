import { format as dateFnsFormat, formatDistanceToNow, parseISO } from 'date-fns';
import { zhCN } from 'date-fns/locale';

/**
 * Format currency values
 */
export function formatCurrency(value: number, currency: string = 'CNY'): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format percentage values
 */
export function formatPercent(value: number, decimals: number = 2): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format percentage values (alias for formatPercent)
 */
export function formatPercentage(value: number, decimals: number = 2): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format numbers with thousand separators
 */
export function formatNumber(value: number, decimals: number = 2): string {
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format large numbers in Chinese style (10,000 = 1万)
 */
export function formatLargeNumber(value: number, decimals: number = 2): string {
  if (Math.abs(value) >= 100000000) {
    // 亿
    return `${(value / 100000000).toFixed(decimals)}亿`;
  } else if (Math.abs(value) >= 10000) {
    // 万
    return `${(value / 10000).toFixed(decimals)}万`;
  }
  return formatNumber(value, decimals);
}

/**
 * Format date to string
 */
export function formatDate(date: string | Date, formatStr: string = 'yyyy-MM-dd'): string {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  return dateFnsFormat(dateObj, formatStr, { locale: zhCN });
}

/**
 * Format date to relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: string | Date): string {
  const dateObj = typeof date === 'string' ? parseISO(date) : date;
  return formatDistanceToNow(dateObj, { locale: zhCN, addSuffix: true });
}

/**
 * Format datetime
 */
export function formatDateTime(date: string | Date): string {
  return formatDate(date, 'yyyy-MM-dd HH:mm:ss');
}

/**
 * Format time only
 */
export function formatTime(date: string | Date): string {
  return formatDate(date, 'HH:mm:ss');
}

/**
 * Format profit/loss with color indicator
 */
export function formatProfitLoss(value: number, showSign: boolean = true): {
  text: string;
  className: string;
} {
  const sign = value >= 0 ? '+' : '';
  const text = showSign ? `${sign}${formatCurrency(value)}` : formatCurrency(Math.abs(value));
  const className = value >= 0 ? 'text-profit' : 'text-loss';

  return { text, className };
}

/**
 * Format profit/loss percentage
 */
export function formatProfitLossPercent(value: number): {
  text: string;
  className: string;
} {
  const sign = value >= 0 ? '+' : '';
  const text = `${sign}${formatPercent(value)}`;
  const className = value >= 0 ? 'text-profit' : 'text-loss';

  return { text, className };
}

/**
 * Format volume
 */
export function formatVolume(value: number): string {
  return formatLargeNumber(value, 0);
}

/**
 * Format stock symbol with board indicator
 */
export function formatSymbol(symbol: string, name?: string): string {
  if (name) {
    return `${name} (${symbol})`;
  }
  return symbol;
}

/**
 * Shorten text with ellipsis
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
}

/**
 * Market types
 */
export type MarketType = 'a-share' | 'us-market' | 'hk-market';

/**
 * Signal direction
 */
export type SignalDirection = 'long' | 'short' | 'hold';

/**
 * Detect market type from stock symbol
 *
 * @param symbol - Stock symbol (e.g., "000001.SZ", "AAPL", "0700.HK")
 * @returns Market type
 *
 * @example
 * detectMarketType("000001.SZ") // 'a-share'
 * detectMarketType("AAPL") // 'us-market'
 * detectMarketType("0700.HK") // 'hk-market'
 */
export function detectMarketType(symbol?: string): MarketType {
  if (!symbol) return 'a-share'; // Default to A-share

  const upperSymbol = symbol.toUpperCase();

  // A-share: ends with .SZ (Shenzhen) or .SS (Shanghai), or 6-digit numbers
  if (upperSymbol.endsWith('.SZ') || upperSymbol.endsWith('.SS') || /^\d{6}$/.test(symbol)) {
    return 'a-share';
  }

  // Hong Kong: ends with .HK
  if (upperSymbol.endsWith('.HK')) {
    return 'hk-market'; // HK follows A-share convention
  }

  // Default to US market for others (AAPL, NVDA, etc.)
  return 'us-market';
}

/**
 * Get color class for signal direction based on market type
 *
 * A-share (China): long=red, short=green
 * US/Global: long=green, short=red
 *
 * @param direction - Signal direction ('long', 'short', 'hold')
 * @param symbol - Stock symbol to detect market type
 * @returns Tailwind color class
 *
 * @example
 * getDirectionColor('long', '000001.SZ') // 'text-a-share-up' (red)
 * getDirectionColor('long', 'AAPL') // 'text-us-market-up' (green)
 * getDirectionColor('short', '000001.SZ') // 'text-a-share-down' (green)
 */
export function getDirectionColor(direction: SignalDirection, symbol?: string): string {
  const marketType = detectMarketType(symbol);

  if (direction === 'hold') {
    return 'text-gray-600';
  }

  if (marketType === 'a-share' || marketType === 'hk-market') {
    // A-share & HK: long=red (up), short=green (down)
    return direction === 'long' ? 'text-a-share-up' : 'text-a-share-down';
  } else {
    // US/Global: long=green (up), short=red (down)
    return direction === 'long' ? 'text-us-market-up' : 'text-us-market-down';
  }
}

/**
 * Get color class for change value based on market type
 *
 * A-share (China): positive=red, negative=green
 * US/Global: positive=green, negative=red
 *
 * @param value - Change value (positive or negative)
 * @param symbol - Stock symbol to detect market type
 * @returns Tailwind color class
 *
 * @example
 * getChangeColor(5.2, '000001.SZ') // 'text-a-share-up' (red for positive)
 * getChangeColor(-3.1, 'AAPL') // 'text-us-market-down' (red for negative)
 */
export function getChangeColor(value: number, symbol?: string): string {
  if (value === 0) {
    return 'text-gray-600';
  }

  const marketType = detectMarketType(symbol);
  const isPositive = value > 0;

  if (marketType === 'a-share' || marketType === 'hk-market') {
    // A-share & HK: positive=red, negative=green
    return isPositive ? 'text-a-share-up' : 'text-a-share-down';
  } else {
    // US/Global: positive=green, negative=red
    return isPositive ? 'text-us-market-up' : 'text-us-market-down';
  }
}

/**
 * Format profit/loss with market-aware color indicator
 *
 * @param value - Profit/loss value
 * @param showSign - Whether to show +/- sign
 * @param symbol - Stock symbol to detect market type
 */
export function formatProfitLossMarket(
  value: number,
  showSign: boolean = true,
  symbol?: string
): {
  text: string;
  className: string;
} {
  const sign = value >= 0 ? '+' : '';
  const text = showSign ? `${sign}${formatCurrency(value)}` : formatCurrency(Math.abs(value));
  const className = getChangeColor(value, symbol);

  return { text, className };
}

/**
 * Format profit/loss percentage with market-aware color indicator
 *
 * @param value - Profit/loss percentage (0.05 = 5%)
 * @param symbol - Stock symbol to detect market type
 */
export function formatProfitLossPercentMarket(
  value: number,
  symbol?: string
): {
  text: string;
  className: string;
} {
  const sign = value >= 0 ? '+' : '';
  const text = `${sign}${formatPercent(value)}`;
  const className = getChangeColor(value, symbol);

  return { text, className };
}

/**
 * Get color class for buy/sell direction based on market type
 *
 * A-share (China): buy=red, sell=green
 * US/Global: buy=green, sell=red
 *
 * @param side - Trade side ('buy' or 'sell')
 * @param symbol - Stock symbol to detect market type
 * @returns Tailwind color class
 *
 * @example
 * getSideColor('buy', '000001.SZ') // 'text-a-share-up' (red)
 * getSideColor('buy', 'AAPL') // 'text-us-market-up' (green)
 * getSideColor('sell', '000001.SZ') // 'text-a-share-down' (green)
 */
export function getSideColor(side: 'buy' | 'sell', symbol?: string): string {
  const marketType = detectMarketType(symbol);

  if (marketType === 'a-share' || marketType === 'hk-market') {
    // A-share & HK: buy=red, sell=green
    return side === 'buy' ? 'text-a-share-up' : 'text-a-share-down';
  } else {
    // US/Global: buy=green, sell=red
    return side === 'buy' ? 'text-us-market-up' : 'text-us-market-down';
  }
}

/**
 * Get background color class for buy/sell badges based on market type
 *
 * @param side - Trade side ('buy' or 'sell')
 * @param symbol - Stock symbol to detect market type
 * @returns Tailwind background and text color classes
 *
 * @example
 * getSideBadgeColor('buy', '000001.SZ') // 'bg-red-50 text-red-700'
 * getSideBadgeColor('buy', 'AAPL') // 'bg-green-50 text-green-700'
 */
export function getSideBadgeColor(side: 'buy' | 'sell', symbol?: string): string {
  const marketType = detectMarketType(symbol);

  if (marketType === 'a-share' || marketType === 'hk-market') {
    // A-share & HK: buy=red, sell=green
    return side === 'buy' ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700';
  } else {
    // US/Global: buy=green, sell=red
    return side === 'buy' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700';
  }
}
