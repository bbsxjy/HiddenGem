import { API_CONFIG, WS_CHANNELS } from '@/config/api.config';
import { WS_RECONNECT } from '@/utils/constants';

// WebSocket message types based on backend API.md

// Market data messages
export type MarketConnectionMessage = {
  type: 'connection';
  message: string;
  timestamp: string;
};

export type MarketSubscriptionMessage = {
  type: 'subscription';
  subscribed_symbols: string[];
  timestamp: string;
};

export type MarketDataMessage = {
  type: 'market_data';
  symbol: string;
  price: number;
  volume: number;
  timestamp: string;
};

export type MarketSubscribeRequest = {
  action: 'subscribe';
  symbols: string[];
};

export type MarketUnsubscribeRequest = {
  action: 'unsubscribe';
  symbols: string[];
};

// Order messages
export type OrderUpdateMessage = {
  type: 'order_update';
  order_id: number;
  status: string;
  filled_quantity: number;
  avg_filled_price?: number;
  timestamp: string;
};

// Portfolio messages
export type PortfolioUpdateMessage = {
  type: 'portfolio_update';
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  positions: Array<{
    symbol: string;
    quantity: number;
    unrealized_pnl: number;
  }>;
  timestamp: string;
};

// Agent messages
export type AgentAnalysisMessage = {
  type: 'agent_analysis';
  agent: string;
  symbol: string;
  result: {
    direction: string;
    confidence: number;
    reasoning: string;
  };
  timestamp: string;
};

export type WebSocketMessage =
  | MarketConnectionMessage
  | MarketSubscriptionMessage
  | MarketDataMessage
  | OrderUpdateMessage
  | PortfolioUpdateMessage
  | AgentAnalysisMessage;

export type WebSocketCallback<T = WebSocketMessage> = (message: T) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private messageHandlers: Set<WebSocketCallback> = new Set();
  private isIntentionallyClosed = false;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private url: string;

  constructor(url: string) {
    this.url = url;
  }

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.warn('WebSocket is already connected');
      return;
    }

    this.isIntentionallyClosed = false;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isIntentionallyClosed = true;
    this.clearHeartbeat();
    this.clearReconnectTimeout();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Subscribe to messages
   */
  subscribe(callback: WebSocketCallback): void {
    this.messageHandlers.add(callback);
  }

  /**
   * Unsubscribe from messages
   */
  unsubscribe(callback: WebSocketCallback): void {
    this.messageHandlers.delete(callback);
  }

  /**
   * Send message to server
   */
  send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  /**
   * Subscribe to market symbols
   */
  subscribeToSymbols(symbols: string[]): void {
    this.send({
      action: 'subscribe',
      symbols,
    });
  }

  /**
   * Unsubscribe from market symbols
   */
  unsubscribeFromSymbols(symbols: string[]): void {
    this.send({
      action: 'unsubscribe',
      symbols,
    });
  }

  /**
   * Get connection status
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private handleOpen(): void {
    console.log('WebSocket connected to', this.url);
    this.reconnectAttempts = 0;
    this.startHeartbeat();
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const rawMessage = JSON.parse(event.data);

      // Handle heartbeat response
      if (rawMessage.type === 'pong') {
        return;
      }

      const message: WebSocketMessage = rawMessage;

      // Dispatch message to all handlers
      this.messageHandlers.forEach((handler) => handler(message));
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private handleError(error: Event): void {
    console.error('WebSocket error:', error);
  }

  private handleClose(): void {
    console.log('WebSocket closed');
    this.clearHeartbeat();

    if (!this.isIntentionallyClosed) {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= WS_RECONNECT.MAX_ATTEMPTS) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.clearReconnectTimeout();

    const delay = Math.min(
      WS_RECONNECT.INITIAL_DELAY *
        Math.pow(WS_RECONNECT.MULTIPLIER, this.reconnectAttempts),
      WS_RECONNECT.MAX_DELAY
    );

    console.log(
      `Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1}/${
        WS_RECONNECT.MAX_ATTEMPTS
      })`
    );

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  private startHeartbeat(): void {
    this.clearHeartbeat();

    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected()) {
        this.send({ type: 'ping' });
      }
    }, 30000); // Send ping every 30 seconds
  }

  private clearHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
}

// Create singleton instances for each channel
export const marketWebSocket = new WebSocketClient(
  `${API_CONFIG.wsURL}${WS_CHANNELS.market}`
);

export const ordersWebSocket = new WebSocketClient(
  `${API_CONFIG.wsURL}${WS_CHANNELS.orders}`
);

export const portfolioWebSocket = new WebSocketClient(
  `${API_CONFIG.wsURL}${WS_CHANNELS.portfolio}`
);

export const agentsWebSocket = new WebSocketClient(
  `${API_CONFIG.wsURL}${WS_CHANNELS.agents}`
);

// Auto-connect on module load (optional)
// You can manually connect when needed instead
// marketWebSocket.connect();
// ordersWebSocket.connect();
// portfolioWebSocket.connect();
// agentsWebSocket.connect();
