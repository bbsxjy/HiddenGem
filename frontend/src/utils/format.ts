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
