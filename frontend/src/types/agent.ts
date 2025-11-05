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
 * LLM comprehensive analysis result
 */
export interface LLMAnalysis {
  recommended_direction: SignalDirection; // Recommended direction
  confidence: number;                     // Confidence level
  reasoning: string;                      // Reasoning process
  risk_assessment: string;                // Risk assessment
  key_factors: string[];                  // Key factors
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
