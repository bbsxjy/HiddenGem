// Order types - aligned with backend API.md

export type OrderType = 'market' | 'limit';
export type OrderSide = 'buy' | 'sell';
export type OrderStatus =
  | 'pending'
  | 'submitted'
  | 'partial_filled'
  | 'filled'
  | 'cancelled'
  | 'rejected';

export interface Order {
  id: number;
  symbol: string;
  name?: string;  // 股票名称
  side: OrderSide;
  order_type: OrderType;
  quantity: number;
  price?: number;
  filled_quantity: number;
  avg_filled_price?: number;
  status: OrderStatus;
  created_at: string;
  filled_at?: string;
  strategy_name?: string;
  reasoning?: string;  // 交易原因
}

export interface CreateOrderRequest {
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  quantity: number;
  price?: number;
  strategy_name?: string;
}

export interface TradingSignal {
  id: number;
  symbol: string;
  direction: 'buy' | 'sell' | 'hold';
  strength: number;
  agent_name: string;
  strategy_name?: string;
  entry_price: number;
  target_price?: number;
  stop_loss_price?: number;
  reasoning: string;
  timestamp: string;
  is_executed: boolean;
}

export interface RecentOrdersResponse {
  orders: Order[];
  count: number;
}

export interface SignalStatsResponse {
  period_days: number;
  total_signals: number;
  executed_signals: number;
  execution_rate: number;
  by_direction: {
    buy: number;
    sell: number;
    hold: number;
  };
  by_agent: Record<string, number>;
}
