/**
 * Memory Bank Types
 * Trading experience storage and management types
 */

export interface Episode {
  episode_id: string;
  date: string;
  symbol: string;
  price: number;
  action?: string | null;
  entry_price?: number | null;
  exit_price?: number | null;
  percentage_return?: number | null;
  holding_period_days?: number | null;
  lesson?: string | null;
  success?: boolean | null;
  market_regime?: string | null;
}

export interface EpisodeDetail {
  episode_id: string;
  date: string;
  symbol: string;
  market_state: Record<string, any>;
  agent_analyses: Record<string, any>;
  decision_chain: Record<string, any>;
  outcome?: Record<string, any> | null;
  lesson?: string | null;
  key_lesson?: string | null;
  success?: boolean | null;
  created_at: string;
  mode: string;
  metadata?: Record<string, any> | null;
}

export interface EpisodeCreate {
  episode_id: string;
  date: string;
  symbol: string;
  market_state: Record<string, any>;
  agent_analyses: Record<string, any>;
  decision_chain: Record<string, any>;
  outcome?: Record<string, any> | null;
  lesson?: string | null;
  key_lesson?: string | null;
  success?: boolean | null;
  mode?: string;
  metadata?: Record<string, any> | null;
}

export interface EpisodeUpdate {
  lesson?: string | null;
  key_lesson?: string | null;
  success?: boolean | null;
  metadata?: Record<string, any> | null;
}

export interface MemoryStatistics {
  total_episodes: number;
  successful_episodes: number;
  failed_episodes: number;
  success_rate: number;
  average_return: number;
  symbols: Record<string, number>;
  date_range: {
    earliest: string;
    latest: string;
  };
}

export interface EpisodesQuery {
  skip?: number;
  limit?: number;
  symbol?: string;
  success?: boolean;
  date_from?: string;
  date_to?: string;
}
