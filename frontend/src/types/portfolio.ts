// Portfolio types - aligned with backend API.md

export interface Position {
  symbol: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  entry_date: string;
  strategy_name?: string;
}

export interface PortfolioSummary {
  total_value: number;
  cash: number;
  positions_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  daily_pnl: number;
  num_positions: number;
  timestamp: string;
}

export interface PortfolioSnapshot {
  timestamp: string;
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  num_positions: number;
}

export interface PortfolioHistoryResponse {
  snapshots: PortfolioSnapshot[];
  count: number;
}
