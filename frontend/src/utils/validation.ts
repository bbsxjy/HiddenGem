import { z } from 'zod';

/**
 * Validate stock symbol (A-share format)
 */
export function isValidStockSymbol(symbol: string): boolean {
  // A-share symbol format: 6 digits followed by .SH or .SZ
  const pattern = /^\d{6}\.(SH|SZ)$/;
  return pattern.test(symbol);
}

/**
 * Validate email
 */
export function isValidEmail(email: string): boolean {
  const schema = z.string().email();
  return schema.safeParse(email).success;
}

/**
 * Validate price (must be positive)
 */
export function isValidPrice(price: number): boolean {
  return price > 0 && isFinite(price);
}

/**
 * Validate quantity (must be positive integer, multiple of 100 for A-shares)
 */
export function isValidQuantity(quantity: number): boolean {
  return quantity > 0 && Number.isInteger(quantity) && quantity % 100 === 0;
}

/**
 * Validate date range
 */
export function isValidDateRange(startDate: Date, endDate: Date): boolean {
  return startDate <= endDate;
}

/**
 * Validate percentage (0-1)
 */
export function isValidPercentage(value: number): boolean {
  return value >= 0 && value <= 1;
}

/**
 * Check if board type is valid
 */
export function isValidBoardType(board: string): board is 'main' | 'chinext' | 'star' {
  return ['main', 'chinext', 'star'].includes(board);
}

/**
 * Validate order side
 */
export function isValidOrderSide(side: string): side is 'buy' | 'sell' {
  return ['buy', 'sell'].includes(side);
}

/**
 * Validate order type
 */
export function isValidOrderType(type: string): type is 'market' | 'limit' {
  return ['market', 'limit'].includes(type);
}

/**
 * Check if value is within A-share price limit
 */
export function isWithinPriceLimit(
  currentPrice: number,
  previousClose: number,
  board: 'main' | 'chinext' | 'star'
): boolean {
  const limit = board === 'main' ? 0.1 : 0.2;
  const maxPrice = previousClose * (1 + limit);
  const minPrice = previousClose * (1 - limit);

  return currentPrice >= minPrice && currentPrice <= maxPrice;
}

/**
 * Sanitize user input (prevent XSS)
 */
export function sanitizeInput(input: string): string {
  return input
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
}

/**
 * Validate phone number (Chinese format)
 */
export function isValidPhoneNumber(phone: string): boolean {
  const pattern = /^1[3-9]\d{9}$/;
  return pattern.test(phone);
}

/**
 * Check if string is empty or whitespace
 */
export function isEmpty(str: string): boolean {
  return !str || str.trim().length === 0;
}

/**
 * Validate URL
 */
export function isValidURL(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}
