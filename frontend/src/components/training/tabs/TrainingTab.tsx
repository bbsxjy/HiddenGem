import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import {
  Play,
  Square,
  Brain,
  TrendingUp,
  Clock,
  Activity,
  AlertCircle,
  CheckCircle,
  BarChart3,
  Zap,
  Layers,
  Network,
  Rocket,
} from 'lucide-react';
import axios from 'axios';
import { startTraining as startRLTraining, type TrainingConfig } from '@/api/rl';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface TrainingInfo {
  training_id: string;
  status: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  config?: {
    stock_pool: string;
    max_stocks: number;
    total_timesteps: number;
    model_name?: string;
  };
}

interface TrainingStatusResponse {
  trainings: TrainingInfo[];
  total: number;
  running: number;
  completed: number;
  failed: number;
}

export function TrainingTab() {
  const queryClient = useQueryClient();

  // 通用配置
  const [modelType, setModelType] = useState('rl_production');
  const [symbols, setSymbols] = useState('000001,600519,000858');
  const [startDate, setStartDate] = useState('2020-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');

  // RL Production 专用配置
  const [stockPool, setStockPool] = useState<'hs300' | 'custom'>('hs300');
  const [maxStocks, setMaxStocks] = useState(50);
  const [valStartDate, setValStartDate] = useState('2024-01-01');
  const [valEndDate, setValEndDate] = useState('2024-12-31');
  const [totalTimesteps, setTotalTimesteps] = useState(500000);
  const [useGpu, setUseGpu] = useState(true);

  // RL模型参数
  const [rlEpisodes, setRlEpisodes] = useState(1000);
  const [rlLearningRate, setRlLearningRate] = useState(0.0001);
  const [rlBatchSize, setRlBatchSize] = useState(32);
  const [rlGamma, setRlGamma] = useState(0.99);
  const [rlEpsilon, setRlEpsilon] = useState(0.1);
  const [rlBufferSize, setRlBufferSize] = useState(10000);

  // LSTM模型参数
  const [lstmEpochs, setLstmEpochs] = useState(100);
  const [lstmLearningRate, setLstmLearningRate] = useState(0.001);
  const [lstmBatchSize, setLstmBatchSize] = useState(64);
  const [lstmHiddenUnits, setLstmHiddenUnits] = useState(128);
  const [lstmLookback, setLstmLookback] = useState(60);
  const [lstmDropout, setLstmDropout] = useState(0.2);
  const [lstmBidirectional, setLstmBidirectional] = useState(true);

  // Transformer模型参数
  const [transformerEpochs, setTransformerEpochs] = useState(50);
  const [transformerLearningRate, setTransformerLearningRate] = useState(0.0001);
  const [transformerBatchSize, setTransformerBatchSize] = useState(32);
  const [transformerHeads, setTransformerHeads] = useState(8);
  const [transformerLayers, setTransformerLayers] = useState(6);
  const [transformerDimFeedforward, setTransformerDimFeedforward] = useState(2048);
  const [transformerDropout, setTransformerDropout] = useState(0.1);

  // 集成模型参数
  const [ensembleModels, setEnsembleModels] = useState<string[]>(['rl', 'lstm']);
  const [ensembleMethod, setEnsembleMethod] = useState('voting');
  const [rlWeight, setRlWeight] = useState(0.5);
  const [lstmWeight, setLstmWeight] = useState(0.5);

  // Fetch training status
  const { data: trainingStatusData } = useQuery({
    queryKey: ['trainingStatus'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/v1/rl/training/status`);
      return response.data.data as TrainingStatusResponse;
    },
    refetchInterval: 10000,
  });

  // Start training mutation
  const startMutation = useMutation({
    mutationFn: async () => {
      // 如果是RL Production模式，使用新的RL训练API
      if (modelType === 'rl_production') {
        const config: TrainingConfig = {
          stock_pool: stockPool,
          custom_symbols: stockPool === 'custom' ? symbols.split(',').map(s => s.trim()).filter(Boolean) : undefined,
          max_stocks: maxStocks,
          train_start: startDate,
          train_end: endDate,
          val_start: valStartDate,
          val_end: valEndDate,
          initial_cash: 100000,
          commission_rate: 0.0003,
          stamp_duty: 0.001,
          enable_t1: true,
          total_timesteps: totalTimesteps,
          learning_rate: 0.0003,
          n_steps: 2048,
          batch_size: 64,
          n_epochs: 10,
          gamma: 0.99,
          use_gpu: useGpu,
        };

        const response = await startRLTraining(config);
        return response;
      }

      // 原有的训练逻辑
      const symbolList = symbols.split(',').map(s => s.trim()).filter(Boolean);

      let config: any = {
        model_type: modelType,
        symbols: symbolList,
        start_date: startDate,
        end_date: endDate,
      };

      // 根据模型类型添加特定参数
      if (modelType === 'rl') {
        config = {
          ...config,
          episodes: rlEpisodes,
          learning_rate: rlLearningRate,
          batch_size: rlBatchSize,
          gamma: rlGamma,
          epsilon: rlEpsilon,
          buffer_size: rlBufferSize,
        };
      } else if (modelType === 'lstm') {
        config = {
          ...config,
          epochs: lstmEpochs,
          learning_rate: lstmLearningRate,
          batch_size: lstmBatchSize,
          hidden_units: lstmHiddenUnits,
          lookback: lstmLookback,
          dropout: lstmDropout,
          bidirectional: lstmBidirectional,
        };
      } else if (modelType === 'transformer') {
        config = {
          ...config,
          epochs: transformerEpochs,
          learning_rate: transformerLearningRate,
          batch_size: transformerBatchSize,
          num_heads: transformerHeads,
          num_layers: transformerLayers,
          dim_feedforward: transformerDimFeedforward,
          dropout: transformerDropout,
        };
      } else if (modelType === 'ensemble') {
        config = {
          ...config,
          sub_models: ensembleModels,
          ensemble_method: ensembleMethod,
          weights: {
            rl: rlWeight,
            lstm: lstmWeight,
          },
        };
      }

      const response = await axios.post(`${API_BASE_URL}/api/v1/training/start`, config);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trainingStatus'] });
    },
  });

  // Stop training mutation
  const stopMutation = useMutation({
    mutationFn: async () => {
      // Find the running training
      const currentRunning = trainingStatusData?.trainings?.find(t => t.status === 'running');
      if (currentRunning) {
        const response = await axios.post(`${API_BASE_URL}/api/v1/rl/training/stop/${currentRunning.training_id}`);
        return response.data;
      }
      throw new Error('No running training to stop');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trainingStatus'] });
    },
  });

  const isTraining = (trainingStatusData?.running || 0) > 0;
  const runningTraining = trainingStatusData?.trainings?.find(t => t.status === 'running');
  const progress = runningTraining?.config?.total_timesteps
    ? 50  // Since we don't have current timesteps, show 50% as placeholder
    : 0;

  // 渲染模型特定参数配置
  const renderModelConfig = () => {
    switch (modelType) {
      case 'rl_production':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                股票池选择
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={stockPool}
                onChange={(e) => setStockPool(e.target.value as 'hs300' | 'custom')}
              >
                <option value="hs300">沪深300 (推荐)</option>
                <option value="custom">自定义股票列表</option>
              </select>
            </div>

            {stockPool === 'custom' && (
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  股票代码列表
                </label>
                <Input
                  placeholder="例如: 600519,000001,300750 (逗号分隔)"
                  value={symbols}
                  onChange={(e) => setSymbols(e.target.value)}
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                最大股票数量: {maxStocks}
              </label>
              <input
                type="range"
                min="10"
                max="300"
                step="10"
                value={maxStocks}
                onChange={(e) => setMaxStocks(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-text-secondary mt-1">
                <span>10</span>
                <span>50</span>
                <span>100</span>
                <span>300</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  验证开始日期
                </label>
                <Input
                  type="date"
                  value={valStartDate}
                  onChange={(e) => setValStartDate(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  验证结束日期
                </label>
                <Input
                  type="date"
                  value={valEndDate}
                  onChange={(e) => setValEndDate(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                总训练步数: {totalTimesteps.toLocaleString()}
              </label>
              <input
                type="range"
                min="10000"
                max="2000000"
                step="10000"
                value={totalTimesteps}
                onChange={(e) => setTotalTimesteps(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-text-secondary mt-1">
                <span>1万</span>
                <span>50万</span>
                <span>100万</span>
                <span>200万</span>
              </div>
            </div>

            <div>
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="w-4 h-4 text-primary-500 border-gray-300 rounded focus:ring-primary-500"
                  checked={useGpu}
                  onChange={(e) => setUseGpu(e.target.checked)}
                />
                <span className="ml-2 text-sm font-medium text-text-primary">
                  使用GPU加速训练
                </span>
              </label>
              <p className="text-xs text-text-secondary mt-1 ml-6">
                GPU训练速度约为CPU的10倍以上
              </p>
            </div>

            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
              <strong>说明：</strong>
              这是生产级RL训练系统，支持沪深300和自定义股票池，包含T+1限制、手续费和印花税等真实市场约束。
              训练完成后模型可直接用于回测和实盘交易。
            </div>
          </div>
        );

      case 'rl':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Episodes 数量
              </label>
              <Input
                type="number"
                placeholder="1000"
                value={rlEpisodes}
                onChange={(e) => setRlEpisodes(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">训练的总轮数</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                学习率 (Learning Rate)
              </label>
              <Input
                type="number"
                step="0.00001"
                placeholder="0.0001"
                value={rlLearningRate}
                onChange={(e) => setRlLearningRate(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">神经网络的学习速度</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                批次大小 (Batch Size)
              </label>
              <Input
                type="number"
                placeholder="32"
                value={rlBatchSize}
                onChange={(e) => setRlBatchSize(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">每次训练的样本数量</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                折扣因子 (Gamma)
              </label>
              <Input
                type="number"
                step="0.01"
                placeholder="0.99"
                value={rlGamma}
                onChange={(e) => setRlGamma(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">未来奖励的折扣率 (0-1)</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                探索率 (Epsilon)
              </label>
              <Input
                type="number"
                step="0.01"
                placeholder="0.1"
                value={rlEpsilon}
                onChange={(e) => setRlEpsilon(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">探索vs利用的平衡 (0-1)</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                经验回放缓冲区大小
              </label>
              <Input
                type="number"
                placeholder="10000"
                value={rlBufferSize}
                onChange={(e) => setRlBufferSize(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">存储的历史经验数量</p>
            </div>
          </div>
        );

      case 'lstm':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                训练轮数 (Epochs)
              </label>
              <Input
                type="number"
                placeholder="100"
                value={lstmEpochs}
                onChange={(e) => setLstmEpochs(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">遍历全部数据的次数</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                学习率
              </label>
              <Input
                type="number"
                step="0.0001"
                placeholder="0.001"
                value={lstmLearningRate}
                onChange={(e) => setLstmLearningRate(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">优化器的学习速度</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                批次大小
              </label>
              <Input
                type="number"
                placeholder="64"
                value={lstmBatchSize}
                onChange={(e) => setLstmBatchSize(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">每批训练的样本数</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                隐藏单元数
              </label>
              <Input
                type="number"
                placeholder="128"
                value={lstmHiddenUnits}
                onChange={(e) => setLstmHiddenUnits(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">LSTM层的神经元数量</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                时间步长 (Lookback)
              </label>
              <Input
                type="number"
                placeholder="60"
                value={lstmLookback}
                onChange={(e) => setLstmLookback(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">输入序列的历史天数</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Dropout率
              </label>
              <Input
                type="number"
                step="0.1"
                placeholder="0.2"
                value={lstmDropout}
                onChange={(e) => setLstmDropout(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">防止过拟合 (0-1)</p>
            </div>

            <div className="md:col-span-2">
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="w-4 h-4 text-primary-500 border-gray-300 rounded focus:ring-primary-500"
                  checked={lstmBidirectional}
                  onChange={(e) => setLstmBidirectional(e.target.checked)}
                />
                <span className="ml-2 text-sm font-medium text-text-primary">
                  使用双向LSTM
                </span>
              </label>
              <p className="text-xs text-text-secondary mt-1 ml-6">
                同时从前向后和从后向前学习序列特征
              </p>
            </div>
          </div>
        );

      case 'transformer':
        return (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                训练轮数 (Epochs)
              </label>
              <Input
                type="number"
                placeholder="50"
                value={transformerEpochs}
                onChange={(e) => setTransformerEpochs(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">训练迭代次数</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                学习率
              </label>
              <Input
                type="number"
                step="0.00001"
                placeholder="0.0001"
                value={transformerLearningRate}
                onChange={(e) => setTransformerLearningRate(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">优化器的学习速度</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                批次大小
              </label>
              <Input
                type="number"
                placeholder="32"
                value={transformerBatchSize}
                onChange={(e) => setTransformerBatchSize(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">每批处理的样本数</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                注意力头数 (Attention Heads)
              </label>
              <Input
                type="number"
                placeholder="8"
                value={transformerHeads}
                onChange={(e) => setTransformerHeads(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">多头注意力机制的头数</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                编码器层数
              </label>
              <Input
                type="number"
                placeholder="6"
                value={transformerLayers}
                onChange={(e) => setTransformerLayers(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">Transformer编码器的层数</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                前馈网络维度
              </label>
              <Input
                type="number"
                placeholder="2048"
                value={transformerDimFeedforward}
                onChange={(e) => setTransformerDimFeedforward(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">FFN层的隐藏维度</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                Dropout率
              </label>
              <Input
                type="number"
                step="0.1"
                placeholder="0.1"
                value={transformerDropout}
                onChange={(e) => setTransformerDropout(Number(e.target.value))}
              />
              <p className="text-xs text-text-secondary mt-1">防止过拟合</p>
            </div>
          </div>
        );

      case 'ensemble':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-3">
                选择子模型
              </label>
              <div className="space-y-2">
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="w-4 h-4 text-primary-500 border-gray-300 rounded focus:ring-primary-500"
                    checked={ensembleModels.includes('rl')}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setEnsembleModels([...ensembleModels, 'rl']);
                      } else {
                        setEnsembleModels(ensembleModels.filter(m => m !== 'rl'));
                      }
                    }}
                  />
                  <span className="ml-2 text-sm text-text-primary">深度强化学习 (RL)</span>
                </label>

                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="w-4 h-4 text-primary-500 border-gray-300 rounded focus:ring-primary-500"
                    checked={ensembleModels.includes('lstm')}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setEnsembleModels([...ensembleModels, 'lstm']);
                      } else {
                        setEnsembleModels(ensembleModels.filter(m => m !== 'lstm'));
                      }
                    }}
                  />
                  <span className="ml-2 text-sm text-text-primary">LSTM时序预测</span>
                </label>

                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="w-4 h-4 text-primary-500 border-gray-300 rounded focus:ring-primary-500"
                    checked={ensembleModels.includes('transformer')}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setEnsembleModels([...ensembleModels, 'transformer']);
                      } else {
                        setEnsembleModels(ensembleModels.filter(m => m !== 'transformer'));
                      }
                    }}
                  />
                  <span className="ml-2 text-sm text-text-primary">Transformer模型</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                集成方法
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={ensembleMethod}
                onChange={(e) => setEnsembleMethod(e.target.value)}
              >
                <option value="voting">投票法 (Voting)</option>
                <option value="averaging">平均法 (Averaging)</option>
                <option value="weighted">加权平均 (Weighted)</option>
                <option value="stacking">堆叠法 (Stacking)</option>
              </select>
              <p className="text-xs text-text-secondary mt-1">子模型预测结果的组合方式</p>
            </div>

            {ensembleMethod === 'weighted' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    RL模型权重
                  </label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    placeholder="0.5"
                    value={rlWeight}
                    onChange={(e) => setRlWeight(Number(e.target.value))}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    LSTM模型权重
                  </label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    placeholder="0.5"
                    value={lstmWeight}
                    onChange={(e) => setLstmWeight(Number(e.target.value))}
                  />
                </div>
              </div>
            )}

            <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg text-sm text-purple-800">
              <strong>提示：</strong>
              集成模型将组合多个子模型的预测结果，通常能获得更好的性能和鲁棒性。
              请确保已训练好各个子模型。
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Status Display */}
      <div className="p-4 border-2 border-dashed rounded-lg" style={{
        borderColor: isTraining ? '#0ea5e9' : '#d1d5db',
        backgroundColor: isTraining ? '#f0f9ff' : '#f9fafb'
      }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${isTraining ? 'bg-primary-500 animate-pulse' : 'bg-gray-400'}`} />
            <h3 className="font-semibold text-text-primary">
              训练状态: {isTraining ? '训练中' : '未启动'}
            </h3>
          </div>
          {isTraining && runningTraining?.started_at && (
            <span className="text-xs text-text-secondary">
              启动于: {new Date(runningTraining.started_at).toLocaleString('zh-CN')}
            </span>
          )}
        </div>

        {isTraining && runningTraining && (
          <div className="space-y-4">
            {/* Progress Bar */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-text-secondary">训练进度</span>
                <span className="text-sm font-medium text-text-primary">
                  目标步数: {runningTraining.config?.total_timesteps?.toLocaleString() || 'N/A'}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-primary-500 h-3 rounded-full transition-all duration-500 animate-pulse"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="text-right mt-1">
                <span className="text-xs text-text-secondary">训练中...</span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white p-3 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <Brain size={14} />
                  训练ID
                </div>
                <div className="text-sm font-bold text-text-primary truncate">
                  {runningTraining.training_id}
                </div>
              </div>

              <div className="bg-white p-3 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <TrendingUp size={14} className="text-profit" />
                  股票池
                </div>
                <div className="text-lg font-bold text-text-primary">
                  {runningTraining.config?.stock_pool?.toUpperCase() || 'N/A'}
                </div>
              </div>

              <div className="bg-white p-3 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <BarChart3 size={14} className="text-primary-500" />
                  最大股票数
                </div>
                <div className="text-lg font-bold text-primary-600">
                  {runningTraining.config?.max_stocks || 'N/A'}
                </div>
              </div>

              <div className="bg-white p-3 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <Clock size={14} />
                  状态
                </div>
                <div className="text-lg font-bold text-profit">
                  {runningTraining.status}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Control Buttons */}
      <div className="flex gap-3">
        {!isTraining ? (
          <Button
            onClick={() => startMutation.mutate()}
            disabled={startMutation.isPending || !symbols.trim()}
            className="flex items-center gap-2"
          >
            <Play size={16} />
            启动训练
            {startMutation.isPending && '...'}
          </Button>
        ) : (
          <Button
            onClick={() => stopMutation.mutate()}
            disabled={stopMutation.isPending}
            variant="outline"
            className="flex items-center gap-2 border-red-300 text-red-600 hover:bg-red-50"
          >
            <Square size={16} />
            停止训练
            {stopMutation.isPending && '...'}
          </Button>
        )}
      </div>

      {/* Error Messages */}
      {startMutation.isError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
          启动失败: {(startMutation.error as any)?.response?.data?.detail || startMutation.error?.message || '未知错误'}
        </div>
      )}
      {stopMutation.isError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
          停止失败: {(stopMutation.error as any)?.response?.data?.detail || stopMutation.error?.message || '未知错误'}
        </div>
      )}

      {/* 停止时显示配置面板 */}
      {!isTraining && (
        <>
          {/* Training Configuration */}
          <Card title="训练配置" padding="md">
            <div className="space-y-6">
              {/* 模型类型选择 */}
              <div>
                <label className="block text-sm font-medium text-text-primary mb-3">
                  选择模型类型
                </label>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                  <button
                    onClick={() => setModelType('rl_production')}
                    className={`p-4 border-2 rounded-lg transition-all ${
                      modelType === 'rl_production'
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-primary-300'
                    }`}
                  >
                    <Rocket className={`w-8 h-8 mx-auto mb-2 ${modelType === 'rl_production' ? 'text-primary-500' : 'text-gray-400'}`} />
                    <p className="text-sm font-semibold text-text-primary">RL生产版</p>
                    <p className="text-xs text-text-secondary mt-1">沪深300/PPO</p>
                  </button>

                  <button
                    onClick={() => setModelType('rl')}
                    className={`p-4 border-2 rounded-lg transition-all ${
                      modelType === 'rl'
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-primary-300'
                    }`}
                  >
                    <Brain className={`w-8 h-8 mx-auto mb-2 ${modelType === 'rl' ? 'text-primary-500' : 'text-gray-400'}`} />
                    <p className="text-sm font-semibold text-text-primary">深度强化学习</p>
                    <p className="text-xs text-text-secondary mt-1">DQN/PPO</p>
                  </button>

                  <button
                    onClick={() => setModelType('lstm')}
                    className={`p-4 border-2 rounded-lg transition-all ${
                      modelType === 'lstm'
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-primary-300'
                    }`}
                  >
                    <Activity className={`w-8 h-8 mx-auto mb-2 ${modelType === 'lstm' ? 'text-primary-500' : 'text-gray-400'}`} />
                    <p className="text-sm font-semibold text-text-primary">LSTM</p>
                    <p className="text-xs text-text-secondary mt-1">时序预测</p>
                  </button>

                  <button
                    onClick={() => setModelType('transformer')}
                    className={`p-4 border-2 rounded-lg transition-all ${
                      modelType === 'transformer'
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-primary-300'
                    }`}
                  >
                    <Network className={`w-8 h-8 mx-auto mb-2 ${modelType === 'transformer' ? 'text-primary-500' : 'text-gray-400'}`} />
                    <p className="text-sm font-semibold text-text-primary">Transformer</p>
                    <p className="text-xs text-text-secondary mt-1">注意力机制</p>
                  </button>

                  <button
                    onClick={() => setModelType('ensemble')}
                    className={`p-4 border-2 rounded-lg transition-all ${
                      modelType === 'ensemble'
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-primary-300'
                    }`}
                  >
                    <Layers className={`w-8 h-8 mx-auto mb-2 ${modelType === 'ensemble' ? 'text-primary-500' : 'text-gray-400'}`} />
                    <p className="text-sm font-semibold text-text-primary">集成模型</p>
                    <p className="text-xs text-text-secondary mt-1">多模型融合</p>
                  </button>
                </div>
              </div>

              {/* 通用配置 */}
              {modelType !== 'rl_production' && (
                <div className="border-t border-gray-200 pt-4">
                  <h3 className="text-sm font-semibold text-text-primary mb-4">通用配置</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="md:col-span-2">
                      <label className="block text-sm font-medium text-text-primary mb-2">
                        训练股票列表 <span className="text-xs text-text-secondary">(逗号分隔)</span>
                      </label>
                      <Input
                        placeholder="例如: 000001,600519,000858"
                        value={symbols}
                        onChange={(e) => setSymbols(e.target.value)}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">
                        训练数据起始日期
                      </label>
                      <Input
                        type="date"
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">
                        训练数据结束日期
                      </label>
                      <Input
                        type="date"
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* 模型特定参数 */}
              <div className="border-t border-gray-200 pt-4">
                <h3 className="text-sm font-semibold text-text-primary mb-4">
                  {modelType === 'rl_production' && 'RL生产版配置'}
                  {modelType === 'rl' && 'RL模型参数'}
                  {modelType === 'lstm' && 'LSTM模型参数'}
                  {modelType === 'transformer' && 'Transformer模型参数'}
                  {modelType === 'ensemble' && '集成模型参数'}
                </h3>
                {renderModelConfig()}
              </div>

              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                <strong>说明：</strong>
                训练过程将使用历史数据训练AI模型，训练完成后模型将保存到Memory Bank供实际交易使用。
                建议使用至少2-3年的历史数据进行训练以获得更好的模型性能。
              </div>
            </div>
          </Card>

          {/* Info Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card padding="md">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-primary-50 rounded-lg">
                  <Brain size={20} className="text-primary-500" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text-primary mb-1">
                    多种模型支持
                  </h3>
                  <p className="text-xs text-text-secondary">
                    支持RL、LSTM、Transformer等多种深度学习模型，每种模型有专属的参数配置
                  </p>
                </div>
              </div>
            </Card>

            <Card padding="md">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-profit/10 rounded-lg">
                  <Zap size={20} className="text-profit" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text-primary mb-1">
                    GPU加速训练
                  </h3>
                  <p className="text-xs text-text-secondary">
                    支持CUDA加速，大幅缩短训练时间，提升训练效率
                  </p>
                </div>
              </div>
            </Card>

            <Card padding="md">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-orange-50 rounded-lg">
                  <CheckCircle size={20} className="text-orange-500" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text-primary mb-1">
                    自动保存模型
                  </h3>
                  <p className="text-xs text-text-secondary">
                    训练过程中自动保存最优模型检查点，避免训练进度丢失
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
