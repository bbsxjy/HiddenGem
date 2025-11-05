import { create } from 'zustand';
import type { Quote } from '@/types/market';
import type { Position, PortfolioSummary } from '@/types/portfolio';
import type { Order, TradingSignal } from '@/types/order';
import type { AgentConfig } from '@/types/agent';

interface RealtimeState {
  // Market data
  marketData: Map<string, Quote>;
  setMarketData: (symbol: string, data: Quote) => void;
  updateMarketData: (symbol: string, data: Partial<Quote>) => void;

  // Portfolio
  portfolioSummary: PortfolioSummary | null;
  positions: Position[];
  setPortfolioSummary: (summary: PortfolioSummary) => void;
  setPositions: (positions: Position[]) => void;
  updatePosition: (symbol: string, updates: Partial<Position>) => void;

  // Orders
  activeOrders: Order[];
  setActiveOrders: (orders: Order[]) => void;
  addOrder: (order: Order) => void;
  updateOrder: (orderId: number, updates: Partial<Order>) => void;
  removeOrder: (orderId: number) => void;

  // Signals
  tradingSignals: TradingSignal[];
  setTradingSignals: (signals: TradingSignal[]) => void;
  addTradingSignal: (signal: TradingSignal) => void;
  removeTradingSignal: (signalId: number) => void;

  // Agents
  agents: AgentConfig[];
  setAgents: (agents: AgentConfig[]) => void;
  updateAgent: (agentName: string, updates: Partial<AgentConfig>) => void;

  // Connection status
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;

  // Last update timestamps
  lastUpdate: {
    market: number;
    portfolio: number;
    orders: number;
    signals: number;
    agents: number;
  };
  updateTimestamp: (key: keyof RealtimeState['lastUpdate']) => void;

  // Clear all data
  clearAll: () => void;
}

export const useRealtimeStore = create<RealtimeState>((set) => ({
  // Market data
  marketData: new Map(),
  setMarketData: (symbol, data) =>
    set((state) => {
      const newMap = new Map(state.marketData);
      newMap.set(symbol, data);
      return { marketData: newMap };
    }),
  updateMarketData: (symbol, data) =>
    set((state) => {
      const current = state.marketData.get(symbol);
      if (!current) return state;
      const newMap = new Map(state.marketData);
      newMap.set(symbol, { ...current, ...data });
      return { marketData: newMap };
    }),

  // Portfolio
  portfolioSummary: null,
  positions: [],
  setPortfolioSummary: (summary) => set({ portfolioSummary: summary }),
  setPositions: (positions) => set({ positions }),
  updatePosition: (symbol, updates) =>
    set((state) => ({
      positions: state.positions.map((pos) =>
        pos.symbol === symbol ? { ...pos, ...updates } : pos
      ),
    })),

  // Orders
  activeOrders: [],
  setActiveOrders: (orders) => set({ activeOrders: orders }),
  addOrder: (order) =>
    set((state) => ({ activeOrders: [...state.activeOrders, order] })),
  updateOrder: (orderId, updates) =>
    set((state) => ({
      activeOrders: state.activeOrders.map((order) =>
        order.id === orderId ? { ...order, ...updates } : order
      ),
    })),
  removeOrder: (orderId) =>
    set((state) => ({
      activeOrders: state.activeOrders.filter((order) => order.id !== orderId),
    })),

  // Signals
  tradingSignals: [],
  setTradingSignals: (signals) => set({ tradingSignals: signals }),
  addTradingSignal: (signal) =>
    set((state) => ({ tradingSignals: [...state.tradingSignals, signal] })),
  removeTradingSignal: (signalId) =>
    set((state) => ({
      tradingSignals: state.tradingSignals.filter(
        (signal) => signal.id !== signalId
      ),
    })),

  // Agents
  agents: [],
  setAgents: (agents) => set({ agents }),
  updateAgent: (agentName, updates) =>
    set((state) => ({
      agents: state.agents.map((agent) =>
        agent.name === agentName ? { ...agent, ...updates } : agent
      ),
    })),

  // Connection status
  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),

  // Last update timestamps
  lastUpdate: {
    market: 0,
    portfolio: 0,
    orders: 0,
    signals: 0,
    agents: 0,
  },
  updateTimestamp: (key) =>
    set((state) => ({
      lastUpdate: {
        ...state.lastUpdate,
        [key]: Date.now(),
      },
    })),

  // Clear all data
  clearAll: () =>
    set({
      marketData: new Map(),
      portfolioSummary: null,
      positions: [],
      activeOrders: [],
      tradingSignals: [],
      agents: [],
      lastUpdate: {
        market: 0,
        portfolio: 0,
        orders: 0,
        signals: 0,
        agents: 0,
      },
    }),
}));
