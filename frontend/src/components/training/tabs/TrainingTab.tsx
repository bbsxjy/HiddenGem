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
  Database,
} from 'lucide-react';
import axios from 'axios';
import { startTraining as startRLTraining, type TrainingConfig } from '@/api/rl';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

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

  // RL Production 专用配置
  const [stockPool, setStockPool] = useState<'hs300' | 'custom'>('hs300');
  const [maxStocks, setMaxStocks] = useState(50);
  const [trainStartDate, setTrainStartDate] = useState('2020-01-01');
  const [trainEndDate, setTrainEndDate] = useState('2023-12-31');
  const [valStartDate, setValStartDate] = useState('2024-01-01');
  const [valEndDate, setValEndDate] = useState('2024-12-31');
  const [totalTimesteps, setTotalTimesteps] = useState(500000);
  const [useGpu, setUseGpu] = useState(true);

  // MemoryBank 专用配置
  const [memoryCapacity, setMemoryCapacity] = useState(1000);
  const [updateFrequency, setUpdateFrequency] = useState<'daily' | 'weekly'>('daily');
  const [similarityThreshold, setSimilarityThreshold] = useState(0.8);

  // Fetch training status
  const { data: trainingStatusData } = useQuery({
    queryKey: ['trainingStatus'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/v1/rl/training/status`);
      return response.data.data as TrainingStatusResponse;
    },
    refetchInterval: 10000,
  });

  const runningTrainingId = trainingStatusData?.trainings?.find(t => t.status === 'running')?.training_id;

  // Fetch training metrics (for charts)
  const { data: metricsData } = useQuery({
    queryKey: ['trainingMetrics', runningTrainingId],
    queryFn: async () => {
      if (!runningTrainingId) return null;
      const response = await axios.get(`${API_BASE_URL}/api/v1/rl/training/metrics/${runningTrainingId}`);
      return response.data.data;
    },
    enabled: !!runningTrainingId,
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
          train_start: trainStartDate,
          train_end: trainEndDate,
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
      } else if (modelType === 'memorybank') {
        // MemoryBank 训练
        const config = {
          symbols: symbols.split(',').map(s => s.trim()).filter(Boolean),
          start_date: trainStartDate,
          end_date: trainEndDate,
          memory_capacity: memoryCapacity,
          update_frequency: updateFrequency,
          similarity_threshold: similarityThreshold,
        };

        const response = await axios.post(`${API_BASE_URL}/api/v1/memorybank/training/start`, config);
        return response.data;
      }

      throw new Error('未知的模型类型');
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
  const progress = runningTraining?.progress?.progress_pct || 0;  // 使用API返回的实际进度
  const currentTimesteps = runningTraining?.progress?.timesteps || 0;
  const runningTotalTimesteps = runningTraining?.config?.total_timesteps || 0;

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
                  训练开始日期
                </label>
                <Input
                  type="date"
                  value={trainStartDate}
                  onChange={(e) => setTrainStartDate(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  训练结束日期
                </label>
                <Input
                  type="date"
                  value={trainEndDate}
                  onChange={(e) => setTrainEndDate(e.target.value)}
                />
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
              训练数据用于模型学习，验证数据用于评估模型性能。训练完成后模型可直接用于回测和实盘交易。
            </div>
          </div>
        );

      case 'memorybank':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                股票代码列表
              </label>
              <Input
                placeholder="例如: 600519,000001,300750 (逗号分隔)"
                value={symbols}
                onChange={(e) => setSymbols(e.target.value)}
              />
              <p className="text-xs text-text-secondary mt-1">
                将为这些股票构建历史记忆库
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  开始日期
                </label>
                <Input
                  type="date"
                  value={trainStartDate}
                  onChange={(e) => setTrainStartDate(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  结束日期
                </label>
                <Input
                  type="date"
                  value={trainEndDate}
                  onChange={(e) => setTrainEndDate(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                记忆库容量: {memoryCapacity}
              </label>
              <input
                type="range"
                min="100"
                max="10000"
                step="100"
                value={memoryCapacity}
                onChange={(e) => setMemoryCapacity(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-text-secondary mt-1">
                <span>100</span>
                <span>1000</span>
                <span>5000</span>
                <span>10000</span>
              </div>
              <p className="text-xs text-text-secondary mt-1">
                记忆库能保存的最大历史案例数量
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                更新频率
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={updateFrequency}
                onChange={(e) => setUpdateFrequency(e.target.value as 'daily' | 'weekly')}
              >
                <option value="daily">每日更新</option>
                <option value="weekly">每周更新</option>
              </select>
              <p className="text-xs text-text-secondary mt-1">
                记忆库的更新和重训练频率
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                相似度阈值: {similarityThreshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0.5"
                max="1.0"
                step="0.05"
                value={similarityThreshold}
                onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-text-secondary mt-1">
                <span>0.5</span>
                <span>0.75</span>
                <span>0.9</span>
                <span>1.0</span>
              </div>
              <p className="text-xs text-text-secondary mt-1">
                案例匹配时的最低相似度要求
              </p>
            </div>

            <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg text-sm text-purple-800">
              <strong>说明：</strong>
              MemoryBank系统将历史市场情况和交易结果存储为案例库，通过相似度匹配找到历史相似场景，
              为当前决策提供参考。系统会根据设定频率自动更新记忆库，确保知识库的时效性。
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
                  {currentTimesteps.toLocaleString()} / {runningTotalTimesteps.toLocaleString()} 步 ({progress.toFixed(1)}%)
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-primary-500 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(progress, 100)}%` }}
                />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-xs text-text-secondary">
                  {runningTraining.progress?.ep_rew_mean !== null && runningTraining.progress?.ep_rew_mean !== undefined
                    ? `奖励: ${runningTraining.progress.ep_rew_mean.toFixed(2)}`
                    : '等待数据...'}
                </span>
                <span className="text-xs text-text-secondary">
                  {runningTraining.progress?.fps
                    ? `速度: ${runningTraining.progress.fps.toFixed(0)} it/s`
                    : ''}
                </span>
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
                  平均奖励
                </div>
                <div className="text-lg font-bold text-text-primary">
                  {runningTraining.progress?.ep_rew_mean !== null && runningTraining.progress?.ep_rew_mean !== undefined
                    ? runningTraining.progress.ep_rew_mean.toFixed(2)
                    : 'N/A'}
                </div>
              </div>

              <div className="bg-white p-3 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <BarChart3 size={14} className="text-primary-500" />
                  已用时间
                </div>
                <div className="text-lg font-bold text-primary-600">
                  {runningTraining.progress?.elapsed_time
                    ? `${Math.floor(runningTraining.progress.elapsed_time / 60)}m ${Math.floor(runningTraining.progress.elapsed_time % 60)}s`
                    : 'N/A'}
                </div>
              </div>

              <div className="bg-white p-3 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <Clock size={14} />
                  预计剩余
                </div>
                <div className="text-lg font-bold text-profit">
                  {runningTraining.progress?.estimated_remaining
                    ? `${Math.floor(runningTraining.progress.estimated_remaining / 60)}m`
                    : 'N/A'}
                </div>
              </div>
            </div>

            {/* Training Charts */}
            {metricsData?.metrics && metricsData.metrics.length > 0 && (
              <div className="space-y-4 mt-6">
                <div className="flex items-center gap-2 text-sm font-medium text-text-primary">
                  <Activity size={16} className="text-primary-500" />
                  训练曲线
                </div>

                {/* Reward Chart */}
                <div className="bg-white p-4 rounded-lg border border-gray-200">
                  <h4 className="text-sm font-medium text-text-secondary mb-3">平均奖励 (Episode Reward)</h4>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={metricsData.metrics}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="timesteps"
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                        tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                      />
                      <YAxis
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#fff',
                          border: '1px solid #e5e7eb',
                          borderRadius: '8px',
                          fontSize: '12px'
                        }}
                        formatter={(value: any) => [value?.toFixed(2), '平均奖励']}
                        labelFormatter={(label) => `步数: ${label.toLocaleString()}`}
                      />
                      <Legend
                        wrapperStyle={{ fontSize: '12px' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="ep_rew_mean"
                        stroke="#0ea5e9"
                        strokeWidth={2}
                        dot={false}
                        name="平均奖励"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Loss Chart */}
                <div className="bg-white p-4 rounded-lg border border-gray-200">
                  <h4 className="text-sm font-medium text-text-secondary mb-3">训练损失 (Training Loss)</h4>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={metricsData.metrics}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="timesteps"
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                        tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                      />
                      <YAxis
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#fff',
                          border: '1px solid #e5e7eb',
                          borderRadius: '8px',
                          fontSize: '12px'
                        }}
                        formatter={(value: any) => [value?.toFixed(6), '']}
                        labelFormatter={(label) => `步数: ${label.toLocaleString()}`}
                      />
                      <Legend
                        wrapperStyle={{ fontSize: '12px' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="policy_loss"
                        stroke="#f59e0b"
                        strokeWidth={2}
                        dot={false}
                        name="Policy Loss"
                      />
                      <Line
                        type="monotone"
                        dataKey="value_loss"
                        stroke="#ef4444"
                        strokeWidth={2}
                        dot={false}
                        name="Value Loss"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Explained Variance Chart */}
                <div className="bg-white p-4 rounded-lg border border-gray-200">
                  <h4 className="text-sm font-medium text-text-secondary mb-3">解释方差 (Explained Variance)</h4>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={metricsData.metrics}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="timesteps"
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                        tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                      />
                      <YAxis
                        stroke="#6b7280"
                        style={{ fontSize: '12px' }}
                        domain={[-1, 1]}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#fff',
                          border: '1px solid #e5e7eb',
                          borderRadius: '8px',
                          fontSize: '12px'
                        }}
                        formatter={(value: any) => [value?.toFixed(4), '解释方差']}
                        labelFormatter={(label) => `步数: ${label.toLocaleString()}`}
                      />
                      <Legend
                        wrapperStyle={{ fontSize: '12px' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="explained_variance"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={false}
                        name="解释方差"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
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
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <button
                    onClick={() => setModelType('rl_production')}
                    className={`p-4 border-2 rounded-lg transition-all ${
                      modelType === 'rl_production'
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-primary-300'
                    }`}
                  >
                    <Brain className={`w-8 h-8 mx-auto mb-2 ${modelType === 'rl_production' ? 'text-primary-500' : 'text-gray-400'}`} />
                    <p className="text-sm font-semibold text-text-primary">深度强化学习</p>
                    <p className="text-xs text-text-secondary mt-1">沪深300/PPO</p>
                  </button>

                  <button
                    onClick={() => setModelType('memorybank')}
                    className={`p-4 border-2 rounded-lg transition-all ${
                      modelType === 'memorybank'
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-primary-300'
                    }`}
                  >
                    <Database className={`w-8 h-8 mx-auto mb-2 ${modelType === 'memorybank' ? 'text-primary-500' : 'text-gray-400'}`} />
                    <p className="text-sm font-semibold text-text-primary">MemoryBank</p>
                    <p className="text-xs text-text-secondary mt-1">案例记忆库</p>
                  </button>
                </div>
              </div>

              {/* 模型特定参数 */}
              <div className="border-t border-gray-200 pt-4">
                <h3 className="text-sm font-semibold text-text-primary mb-4">
                  {modelType === 'rl_production' && '强化学习模型参数'}
                  {modelType === 'memorybank' && 'MemoryBank 参数'}
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
                    深度强化学习
                  </h3>
                  <p className="text-xs text-text-secondary">
                    使用PPO算法训练智能交易策略，自动学习最优买卖时机
                  </p>
                </div>
              </div>
            </Card>

            <Card padding="md">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-purple-50 rounded-lg">
                  <Database size={20} className="text-purple-500" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text-primary mb-1">
                    案例记忆库
                  </h3>
                  <p className="text-xs text-text-secondary">
                    存储历史市场情况和交易结果，通过相似度匹配提供决策参考
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
          </div>
        </>
      )}
    </div>
  );
}
