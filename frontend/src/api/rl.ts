/**
 * RL Training and Backtest API Client
 * 提供RL训练和回测相关的API调用
 */

import { apiClient } from './client';

// ====================================================================================
// Types
// ====================================================================================

export type TrainingStatus = 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
export type StockPool = 'hs300' | 'custom';

export interface TrainingConfig {
  // 数据配置
  stock_pool: StockPool;
  custom_symbols?: string[];
  max_stocks: number;

  train_start: string;  // 'YYYY-MM-DD'
  train_end: string;
  val_start: string;
  val_end: string;

  // 环境配置
  initial_cash: number;
  commission_rate: number;
  stamp_duty: number;
  enable_t1: boolean;

  // 训练超参数
  total_timesteps: number;
  learning_rate: number;
  n_steps: number;
  batch_size: number;
  n_epochs: number;
  gamma: number;

  // 系统配置
  use_gpu: boolean;
  model_name?: string;
}

export interface TrainingProgress {
  timesteps: number;
  total_timesteps: number;
  progress_pct: number;

  // 训练指标
  ep_rew_mean?: number;
  ep_len_mean?: number;
  fps?: number;

  // 训练loss
  policy_loss?: number;
  value_loss?: number;
  explained_variance?: number;

  // 评估指标
  eval_reward?: number;
  best_reward?: number;

  // 时间统计
  elapsed_time: number;
  estimated_remaining?: number;
}

export interface TrainingInfo {
  training_id: string;
  status: TrainingStatus;
  config: TrainingConfig;
  progress?: TrainingProgress;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

export interface ModelInfo {
  model_id: string;
  model_name: string;
  model_path: string;
  model_type: 'best' | 'final' | 'checkpoint';

  // 训练信息
  training_id?: string;
  total_timesteps?: number;

  // 性能指标
  final_reward?: number;
  best_reward?: number;
  sharpe_ratio?: number;

  // 文件信息
  file_size: number;
  created_at: string;
  modified_at: string;

  // 配置
  config?: any;
  performance?: any;
}

export interface BacktestRequest {
  model_path: string;
  symbols: string[];
  start_date: string;
  end_date: string;
  initial_capital: number;
  commission_rate?: number;
}

export interface BacktestSummary {
  initial_capital: number;
  final_value: number;
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
}

// ====================================================================================
// API Functions
// ====================================================================================

/**
 * 启动RL模型训练
 */
export async function startTraining(config: TrainingConfig) {
  const response = await apiClient.post('/api/v1/rl/training/start', config);
  return response.data;
}

/**
 * 查询训练状态
 */
export async function getTrainingStatus(trainingId: string) {
  const response = await apiClient.get(`/api/v1/rl/training/status/${trainingId}`);
  return response.data;
}

/**
 * 获取训练进度
 */
export async function getTrainingProgress(trainingId: string) {
  const response = await apiClient.get(`/api/v1/rl/training/progress/${trainingId}`);
  return response.data;
}

/**
 * 停止训练
 */
export async function stopTraining(trainingId: string) {
  const response = await apiClient.post(`/api/v1/rl/training/stop/${trainingId}`);
  return response.data;
}

/**
 * 列出所有训练好的模型
 */
export async function listModels() {
  const response = await apiClient.get('/api/v1/rl/models');
  return response.data;
}

/**
 * 获取模型详情
 */
export async function getModelInfo(modelId: string) {
  const response = await apiClient.get(`/api/v1/rl/models/${modelId}`);
  return response.data;
}

/**
 * 删除模型
 */
export async function deleteModel(modelId: string) {
  const response = await apiClient.delete(`/api/v1/rl/models/${modelId}`);
  return response.data;
}

/**
 * 启动简单回测
 */
export async function startSimpleBacktest(request: BacktestRequest) {
  const response = await apiClient.post('/api/v1/backtest/simple/start', request);
  return response.data;
}

/**
 * 启动QFLib回测
 */
export async function startQFLibBacktest(request: BacktestRequest) {
  const response = await apiClient.post('/api/v1/backtest/qflib/start', request);
  return response.data;
}

/**
 * 查询回测状态
 */
export async function getBacktestStatus(backtestId: string) {
  const response = await apiClient.get(`/api/v1/backtest/qflib/status/${backtestId}`);
  return response.data;
}

/**
 * 获取回测结果
 */
export async function getBacktestResults(backtestId: string) {
  const response = await apiClient.get(`/api/v1/backtest/qflib/results/${backtestId}`);
  return response.data;
}

/**
 * 创建训练配置预设
 */
export function createTrainingPreset(presetName: string): Partial<TrainingConfig> {
  const presets: Record<string, Partial<TrainingConfig>> = {
    'quick_test': {
      stock_pool: 'hs300',
      max_stocks: 10,
      total_timesteps: 10000,
      n_steps: 512,
      batch_size: 32,
      enable_t1: true,
      use_gpu: false,
    },
    'standard_training': {
      stock_pool: 'hs300',
      max_stocks: 50,
      total_timesteps: 500000,
      n_steps: 2048,
      batch_size: 64,
      n_epochs: 10,
      learning_rate: 0.0003,
      gamma: 0.99,
      enable_t1: true,
      use_gpu: true,
    },
    'full_hs300': {
      stock_pool: 'hs300',
      max_stocks: 300,
      total_timesteps: 1000000,
      n_steps: 2048,
      batch_size: 64,
      n_epochs: 10,
      learning_rate: 0.0003,
      gamma: 0.99,
      enable_t1: true,
      use_gpu: true,
    },
  };

  return presets[presetName] || presets['standard_training'];
}

/**
 * 估算训练时间
 */
export function estimateTrainingTime(timesteps: number, useGpu: boolean = false): number {
  // GPU: ~300 FPS, CPU: ~30 FPS
  const fps = useGpu ? 300 : 30;
  return Math.ceil(timesteps / fps); // 返回秒数
}

/**
 * 格式化训练时间
 */
export function formatTrainingTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}秒`;
  } else if (seconds < 3600) {
    return `${Math.ceil(seconds / 60)}分钟`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.ceil((seconds % 3600) / 60);
    return `${hours}小时${minutes}分钟`;
  }
}
