// Strategy types - aligned with backend API.md

export type StrategyType = 'swing_trading' | 'trend_following';

export interface Strategy {
  name: string;
  strategy_type: StrategyType;
  enabled: boolean;
  symbols: string[];
  max_positions: number;
  position_size: number;
  stop_loss_pct: number;
  take_profit_pct: number;
  num_positions: number;
  params: Record<string, unknown>;
  created_at: string;
}

export interface StrategyStats {
  total_return: number;
  total_return_pct: number;
  annual_return_pct: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  num_trades: number;
}

export interface BacktestConfig {
  start_date: string;
  end_date: string;
  initial_capital: number;
  symbols?: string[];
}

export interface BacktestResult {
  strategy_name: string;
  symbol: string;  // 后端返回的股票代码
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_value: number;  // 后端返回 final_value 而不是 final_capital
  total_return: number;
  total_return_pct: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;  // 后端返回 total_trades 而不是 num_trades
  avg_holding_days: number;  // 后端返回的平均持仓天数
  annual_return_pct?: number;  // 可选字段，后端当前未返回
}

export interface CreateStrategyRequest {
  name: string;
  strategy_type: StrategyType;
  enabled: boolean;
  symbols: string[];
  max_positions: number;
  position_size: number;
  stop_loss_pct: number;
  take_profit_pct: number;
  params?: Record<string, unknown>;
}

export interface UpdateStrategyRequest {
  enabled?: boolean;
  symbols?: string[];
  max_positions?: number;
  params?: Record<string, unknown>;
}

export interface StrategyParameter {
  key: string;
  label: string;
  type: 'number' | 'string' | 'boolean' | 'select';
  value: unknown;
  default: unknown;
  min?: number;
  max?: number;
  step?: number;
  options?: { label: string; value: unknown }[];
  description?: string;
}
