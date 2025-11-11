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
} from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface TrainingStatus {
  is_training: boolean;
  model_type?: string;
  current_episode?: number;
  total_episodes?: number;
  current_reward?: number;
  average_reward?: number;
  training_time?: number;
  started_at?: string;
  config?: any;
}

export function TrainingTab() {
  const queryClient = useQueryClient();

  // 训练配置
  const [modelType, setModelType] = useState('rl');
  const [symbols, setSymbols] = useState('000001,600519,000858');
  const [episodes, setEpisodes] = useState(1000);
  const [learningRate, setLearningRate] = useState(0.0001);
  const [batchSize, setBatchSize] = useState(32);
  const [startDate, setStartDate] = useState('2020-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');

  // Fetch training status
  const { data: trainingStatus } = useQuery({
    queryKey: ['trainingStatus'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/v1/training/status`);
      return response.data.data as TrainingStatus;
    },
    refetchInterval: 10000, // 10秒刷新一次
  });

  // Start training mutation
  const startMutation = useMutation({
    mutationFn: async () => {
      const symbolList = symbols.split(',').map(s => s.trim()).filter(Boolean);
      const response = await axios.post(`${API_BASE_URL}/api/v1/training/start`, {
        model_type: modelType,
        symbols: symbolList,
        episodes,
        learning_rate: learningRate,
        batch_size: batchSize,
        start_date: startDate,
        end_date: endDate,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trainingStatus'] });
    },
  });

  // Stop training mutation
  const stopMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${API_BASE_URL}/api/v1/training/stop`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trainingStatus'] });
    },
  });

  const isTraining = trainingStatus?.is_training || false;
  const progress = trainingStatus?.total_episodes
    ? ((trainingStatus.current_episode || 0) / trainingStatus.total_episodes) * 100
    : 0;

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
          {isTraining && trainingStatus?.started_at && (
            <span className="text-xs text-text-secondary">
              启动于: {new Date(trainingStatus.started_at).toLocaleString('zh-CN')}
            </span>
          )}
        </div>

        {isTraining && trainingStatus && (
          <div className="space-y-4">
            {/* Progress Bar */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-text-secondary">训练进度</span>
                <span className="text-sm font-medium text-text-primary">
                  Episode {trainingStatus.current_episode} / {trainingStatus.total_episodes}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-primary-500 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="text-right mt-1">
                <span className="text-xs text-text-secondary">{progress.toFixed(1)}%</span>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white p-3 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <Brain size={14} />
                  模型类型
                </div>
                <div className="text-lg font-bold text-text-primary">
                  {trainingStatus.model_type?.toUpperCase() || 'RL'}
                </div>
              </div>

              <div className="bg-white p-3 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <TrendingUp size={14} className="text-profit" />
                  当前奖励
                </div>
                <div className="text-lg font-bold text-profit">
                  {trainingStatus.current_reward?.toFixed(2) || '0.00'}
                </div>
              </div>

              <div className="bg-white p-3 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <BarChart3 size={14} className="text-primary-500" />
                  平均奖励
                </div>
                <div className="text-lg font-bold text-primary-600">
                  {trainingStatus.average_reward?.toFixed(2) || '0.00'}
                </div>
              </div>

              <div className="bg-white p-3 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <Clock size={14} />
                  训练时间
                </div>
                <div className="text-lg font-bold text-text-primary">
                  {trainingStatus.training_time
                    ? `${Math.floor(trainingStatus.training_time / 60)}m ${Math.floor(trainingStatus.training_time % 60)}s`
                    : '0m 0s'}
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

      {/* 训练时显示监控信息 */}
      {isTraining && (
        <>
          <Card title="训练监控" padding="md">
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-blue-600 bg-blue-50 p-3 rounded-lg">
                <Activity className="animate-pulse" size={16} />
                <span>模型正在训练中，实时数据每10秒更新一次...</span>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="p-4 border border-gray-200 rounded-lg">
                  <h3 className="font-semibold text-text-primary mb-3">训练配置</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-text-secondary">模型类型:</span>
                      <span className="font-medium text-text-primary">
                        {trainingStatus.model_type?.toUpperCase() || 'RL'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">总Episodes:</span>
                      <span className="font-medium text-text-primary">
                        {trainingStatus.total_episodes || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">学习率:</span>
                      <span className="font-medium text-text-primary">
                        {trainingStatus.config?.learning_rate || learningRate}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">批次大小:</span>
                      <span className="font-medium text-text-primary">
                        {trainingStatus.config?.batch_size || batchSize}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-4 border border-gray-200 rounded-lg">
                  <h3 className="font-semibold text-text-primary mb-3">实时指标</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-text-secondary">当前Episode:</span>
                      <span className="font-medium text-text-primary">
                        {trainingStatus.current_episode || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">当前奖励:</span>
                      <span className={`font-medium ${(trainingStatus.current_reward || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>
                        {trainingStatus.current_reward?.toFixed(4) || '0.0000'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">平均奖励:</span>
                      <span className={`font-medium ${(trainingStatus.average_reward || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>
                        {trainingStatus.average_reward?.toFixed(4) || '0.0000'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-secondary">已训练时长:</span>
                      <span className="font-medium text-text-primary">
                        {trainingStatus.training_time
                          ? `${Math.floor(trainingStatus.training_time / 3600)}h ${Math.floor((trainingStatus.training_time % 3600) / 60)}m`
                          : '0h 0m'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </>
      )}

      {/* 停止时显示配置面板 */}
      {!isTraining && (
        <>
          {/* Training Configuration */}
          <Card title="训练配置" padding="md">
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    模型类型
                  </label>
                  <select
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    value={modelType}
                    onChange={(e) => setModelType(e.target.value)}
                  >
                    <option value="rl">深度强化学习 (DQN/PPO)</option>
                    <option value="lstm">LSTM时序预测</option>
                    <option value="transformer">Transformer模型</option>
                    <option value="ensemble">集成模型</option>
                  </select>
                </div>

                <div>
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
                    训练Episodes
                  </label>
                  <Input
                    type="number"
                    placeholder="1000"
                    value={episodes}
                    onChange={(e) => setEpisodes(Number(e.target.value))}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    学习率
                  </label>
                  <Input
                    type="number"
                    step="0.00001"
                    placeholder="0.0001"
                    value={learningRate}
                    onChange={(e) => setLearningRate(Number(e.target.value))}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    批次大小
                  </label>
                  <Input
                    type="number"
                    placeholder="32"
                    value={batchSize}
                    onChange={(e) => setBatchSize(Number(e.target.value))}
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
                    深度强化学习
                  </h3>
                  <p className="text-xs text-text-secondary">
                    使用DQN或PPO算法训练智能交易Agent，通过奖励机制学习最优交易策略
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
