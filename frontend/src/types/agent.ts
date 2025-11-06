// Agent types - aligned with backend API_DOCUMENTATION.md

/**
 * Available Agent names from backend
 * - technical → TradingAgents internal 'market' agent
 * - fundamental → TradingAgents internal 'fundamentals' agent
 * - sentiment → TradingAgents internal 'sentiment' agent
 * - policy → TradingAgents internal 'news' agent
 */
export type AgentName =
  | 'technical'
  | 'fundamental'
  | 'sentiment'
  | 'policy';

/**
 * Signal direction
 * - long: Bullish/Buy
 * - short: Bearish/Sell
 * - hold: Hold/Neutral
 */
export type SignalDirection = 'long' | 'short' | 'hold';

/**
 * Agent status configuration
 */
export interface AgentStatus {
  name: AgentName;
  enabled: boolean;
  weight: number;
}

/**
 * Legacy interface for backward compatibility
 * @deprecated Use AgentStatus instead
 */
export interface AgentConfig {
  name: AgentName;
  enabled: boolean;
  weight: number;
  timeout?: number;
  cache_ttl?: number;
}

/**
 * Individual agent analysis result
 */
export interface AgentAnalysisResult {
  agent_name: string;        // Agent name
  direction: SignalDirection; // Trading direction
  confidence: number;         // Confidence level (0-1)
  score: number;              // Score (0-1)
  reasoning: string;          // Reasoning summary (first 500 characters)
  is_error: boolean;          // Whether an error occurred
  full_report: string;        // Full analysis report
}

/**
 * Risk analyst feedback
 */
export interface RiskAnalystFeedback {
  position: string;        // 立场：激进/中立/保守
  reasoning: string;       // 推理摘要
  full_analysis: string;   // 完整分析
}

/**
 * LLM comprehensive analysis result
 */
export interface LLMAnalysis {
  recommended_direction: SignalDirection; // Recommended direction
  confidence: number;                     // Confidence level
  reasoning: string;                      // Reasoning process
  risk_assessment: string;                // Risk assessment
  key_factors: string[];                  // Key factors
  risk_score?: number;                    // Risk score (0-1)
  risk_analysts?: {                       // 🆕 Risk analysts feedback
    risky?: RiskAnalystFeedback;          // 激进派分析师
    neutral?: RiskAnalystFeedback;        // 中立派分析师
    safe?: RiskAnalystFeedback;           // 保守派分析师
  };
  risk_manager_decision?: string;         // 🆕 Risk manager final decision
  price_targets?: {                       // Price targets
    entry?: number;
    stop_loss?: number;
    take_profit?: number;
  };
  analysis_timestamp: string;             // Analysis timestamp (ISO 8601)
}

/**
 * Aggregated trading signal from multiple agents
 */
export interface AggregatedSignal {
  direction: SignalDirection;     // Aggregated direction
  confidence: number;             // Aggregated confidence
  position_size: number;          // Recommended position size (0-1)
  num_agreeing_agents: number;    // Number of agreeing agents
  warnings: string[];             // Warning messages
  metadata: {
    analysis_method: string;      // Analysis method (e.g., 'llm')
    agent_count: number;          // Total number of agents involved
    agreeing_agents: number;      // Number of agreeing agents
    total_agents: number;         // Total number of agents
  };
}

/**
 * Complete analysis response from analyze-all endpoint
 */
export interface AnalyzeAllResponse {
  symbol: string;                                      // Stock symbol
  agent_results: Record<AgentName, AgentAnalysisResult>; // Individual agent results
  aggregated_signal: AggregatedSignal;                 // Aggregated signal
  llm_analysis: LLMAnalysis;                           // LLM comprehensive analysis
  signal_rejection_reason: string | null;              // Signal rejection reason (if any)
}

export interface AgentPerformanceResponse {
  message: string;
  agents: AgentName[];
}

// SSE流式API事件类型
export type SSEAnalysisEvent =
  | { type: 'start'; symbol: string; timestamp: string }
  | { type: 'agent_result'; agent_name: string; progress: string; result: {
      direction: SignalDirection | null;
      confidence: number;
      score: number;
      reasoning: string;
      is_error: boolean;
    }; timestamp: string }
  | { type: 'agent_error'; agent_name: string; error: string; timestamp: string }
  | { type: 'llm_start'; message: string; timestamp: string }
  | { type: 'complete'; data: AnalyzeAllResponse; timestamp: string }
  | { type: 'llm_error'; error: string; timestamp: string }
  | { type: 'error'; error: string; timestamp: string };

// ==================== 持仓分析 API 类型 ====================

/**
 * Holdings information for position analysis
 */
export interface HoldingsInfo {
  quantity: number;           // 持仓数量（股）
  avg_price: number;          // 平均买入价（元/美元）
  purchase_date: string;      // 买入日期 (YYYY-MM-DD)
  current_price?: number;     // 当前价格（可选，会自动获取）
}

/**
 * Position analysis request
 */
export interface PositionAnalysisRequest {
  holdings: HoldingsInfo;
  analysis_date?: string;     // 分析日期（可选，默认今天）
}

/**
 * Position action type
 */
export type PositionAction = '卖出' | '持有' | '加仓';

/**
 * Position urgency type
 */
export type PositionUrgency = '立即' | '短期' | '中期' | '长期';

/**
 * Profit/Loss information
 */
export interface ProfitLossInfo {
  current_pnl: number;        // 浮动盈亏（元）
  current_pnl_pct: number;    // 浮动盈亏百分比
  holding_days: number;       // 持仓天数
  cost_price: number;         // 成本价
  current_price: number;      // 当前价
  quantity: number;           // 持仓量
}

/**
 * Position recommendations for different actions
 */
export interface PositionRecommendations {
  sell: {
    should_sell: boolean;
    suggested_price: number | null;
    reason: string;
  };
  hold: {
    should_hold: boolean;
    hold_until: string;
    reason: string;
  };
  add: {
    should_add: boolean;
    suggested_price: number | null;
    suggested_quantity: number | null;
    reason: string;
  };
}

/**
 * Recovery analysis for losing positions
 */
export interface RecoveryAnalysis {
  can_recover: boolean;       // 是否可能回本
  estimated_days: number | null; // 预计回本天数
  probability: number;        // 回本概率（0-1）
  conditions: string;         // 回本条件
}

/**
 * Position analysis result (actual API response structure)
 */
export interface PositionAnalysis {
  // 实际 API 返回的字段
  sell: {
    should_sell: boolean;
    suggested_price: number | null;
    reason: string;
  };
  hold: {
    should_hold: boolean;
    hold_until: string;
    reason: string;
  };
  add: {
    should_add: boolean;
    suggested_price: number | null;
    suggested_quantity: number | null;
    reason: string;
  };
  profit_loss: ProfitLossInfo;

  // 可选字段（API 文档中有，但实际返回可能没有）
  action?: PositionAction;
  urgency?: PositionUrgency;
  reasoning?: string;
  recommendations?: PositionRecommendations;
  recovery_analysis?: RecoveryAnalysis;
  risk_warnings?: string[];
}

/**
 * Complete position analysis response
 */
export interface PositionAnalysisResponse {
  symbol: string;
  analysis_date: string;
  market_analysis: {
    agent_results: Record<AgentName, AgentAnalysisResult>;
    aggregated_signal: AggregatedSignal;
    llm_analysis: LLMAnalysis;
  };
  position_analysis: PositionAnalysis;
}
