// Agent types - aligned with backend API.md

export type AgentName =
  | 'technical'
  | 'fundamental'
  | 'risk'
  | 'market'
  | 'policy'
  | 'sentiment'
  | 'execution';

export type SignalDirection = 'long' | 'short' | 'hold' | 'close';

export interface AgentConfig {
  name: AgentName;
  enabled: boolean;
  weight: number;
  timeout: number;
  cache_ttl: number;
}

export interface AgentAnalysisResult {
  agent_name: AgentName;
  symbol: string;
  score: number;
  direction: SignalDirection;
  confidence: number;
  reasoning: string;
  analysis: Record<string, unknown>;
  execution_time_ms: number;
  timestamp: string;
  is_error: boolean;
}

export interface LLMAnalysis {
  recommended_direction: SignalDirection;
  confidence: number;
  reasoning: string;
  risk_assessment: string;
  key_factors: string[];
  price_targets: {
    entry?: number;
    stop_loss?: number;
    take_profit?: number;
  };
  analysis_timestamp: string;
}

export interface AnalyzeAllResponse {
  symbol: string;
  agent_results: Record<AgentName, {
    direction: SignalDirection;
    confidence: number;
    score: number;
    reasoning: string;
    is_error: boolean;
  }>;
  aggregated_signal: {
    direction: SignalDirection;
    confidence: number;
    position_size: number;
    num_agreeing_agents: number;
    warnings?: string[];
    metadata?: {
      analysis_method?: 'llm' | 'rule_based';
      llm_reasoning?: string;
      risk_assessment?: string;
      key_factors?: string[];
      agent_count?: number;
      agreeing_agents?: number;
      total_agents?: number;
      below_threshold?: boolean;
      below_agreement?: boolean;
      min_threshold?: number;
      min_agreement?: number;
    };
  } | null;
  signal_rejection_reason?: string;
  llm_analysis?: LLMAnalysis;  // 新增：即使信号被拒绝也会返回
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
