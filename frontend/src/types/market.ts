// Market data types - aligned with backend API.md

export type BoardType = 'main' | 'chinext' | 'star';

export interface StockInfo {
  symbol: string;
  name: string;
  industry: string;
  area: string;
  listing_date: string;
}

export interface Quote {
  symbol: string;
  last_price: number;  // 最新价
  price: number;       // 价格（兼容）
  open: number;
  high: number;
  low: number;
  volume: number;
  change: number;      // 涨跌额
  change_pct: number;  // 涨跌幅（旧字段，兼容）
  change_percent: number;  // 涨跌幅（新字段）
  timestamp: string;
}

export interface BarData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BarsResponse {
  symbol: string;
  bars: BarData[];
  count: number;
}

export interface TechnicalIndicators {
  symbol: string;
  timestamp: string;
  indicators: {
    rsi: number;
    macd: number;
    macd_signal: number;
    macd_hist: number;
    ma_5: number;
    ma_20: number;
    ma_60: number;
    kdj_k: number;
    kdj_d: number;
    kdj_j: number;
    bb_upper: number;
    bb_middle: number;
    bb_lower: number;
    atr: number;
    adx: number;
  };
  calculated_from_days: number;
}

export interface StockSearchResult {
  query: string;
  results: {
    symbol: string;
    name: string;
    board: BoardType;
    price: number;
    change: number;
    changePercent: number;
    volume: number;
  }[];
  message?: string;
}
