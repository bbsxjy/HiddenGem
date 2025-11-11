import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// 风险控制设置
export interface RiskControlSettings {
  maxPositionPct: number;        // 最大单个仓位比例 (%)
  maxSectorExposurePct: number;  // 最大板块暴露比例 (%)
  defaultStopLossPct: number;    // 默认止损比例 (%)
  defaultTakeProfitPct: number;  // 默认止盈比例 (%)
}

// 订单设置
export interface OrderSettings {
  minTradingUnit: number;        // 最小交易单位 (股)
  defaultOrderType: 'limit' | 'market';  // 默认订单类型
  orderTimeoutSeconds: number;   // 订单超时时间 (秒)
}

// 数据刷新设置
export interface DataRefreshSettings {
  marketDataInterval: number;    // 行情数据刷新间隔 (秒)
  positionDataInterval: number;  // 持仓数据刷新间隔 (秒)
  orderDataInterval: number;     // 订单数据刷新间隔 (秒)
  agentStatusInterval: number;   // Agent状态刷新间隔 (秒)
  signalInterval: number;        // 交易信号刷新间隔 (秒)
  strategyListInterval: number;  // 策略列表刷新间隔 (秒)
}

interface SettingsState {
  // 设置数据
  riskControl: RiskControlSettings;
  orderSettings: OrderSettings;
  dataRefresh: DataRefreshSettings;

  // 更新方法
  updateRiskControl: (settings: Partial<RiskControlSettings>) => void;
  updateOrderSettings: (settings: Partial<OrderSettings>) => void;
  updateDataRefresh: (settings: Partial<DataRefreshSettings>) => void;

  // 重置方法
  resetRiskControl: () => void;
  resetOrderSettings: () => void;
  resetDataRefresh: () => void;
  resetAllSettings: () => void;
}

// 默认设置
const DEFAULT_RISK_CONTROL: RiskControlSettings = {
  maxPositionPct: 10,           // 10%
  maxSectorExposurePct: 30,     // 30%
  defaultStopLossPct: 8,        // 8%
  defaultTakeProfitPct: 15,     // 15%
};

const DEFAULT_ORDER_SETTINGS: OrderSettings = {
  minTradingUnit: 100,          // 100股
  defaultOrderType: 'limit',    // 限价单
  orderTimeoutSeconds: 30,      // 30秒
};

const DEFAULT_DATA_REFRESH: DataRefreshSettings = {
  marketDataInterval: 30,       // 30秒
  positionDataInterval: 30,     // 30秒
  orderDataInterval: 30,        // 30秒
  agentStatusInterval: 30,      // 30秒
  signalInterval: 30,           // 30秒
  strategyListInterval: 30,     // 30秒
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      // 初始设置
      riskControl: DEFAULT_RISK_CONTROL,
      orderSettings: DEFAULT_ORDER_SETTINGS,
      dataRefresh: DEFAULT_DATA_REFRESH,

      // 更新方法
      updateRiskControl: (settings) =>
        set((state) => ({
          riskControl: { ...state.riskControl, ...settings },
        })),

      updateOrderSettings: (settings) =>
        set((state) => ({
          orderSettings: { ...state.orderSettings, ...settings },
        })),

      updateDataRefresh: (settings) =>
        set((state) => ({
          dataRefresh: { ...state.dataRefresh, ...settings },
        })),

      // 重置方法
      resetRiskControl: () =>
        set({ riskControl: DEFAULT_RISK_CONTROL }),

      resetOrderSettings: () =>
        set({ orderSettings: DEFAULT_ORDER_SETTINGS }),

      resetDataRefresh: () =>
        set({ dataRefresh: DEFAULT_DATA_REFRESH }),

      resetAllSettings: () =>
        set({
          riskControl: DEFAULT_RISK_CONTROL,
          orderSettings: DEFAULT_ORDER_SETTINGS,
          dataRefresh: DEFAULT_DATA_REFRESH,
        }),
    }),
    {
      name: 'settings-storage',
      version: 1,
    }
  )
);
