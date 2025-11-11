import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import axios from 'axios';
import {
  TrendingUp,
  TrendingDown,
  Target,
  CheckCircle,
  XCircle,
  Filter,
  Calendar,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface PredictionHistory {
  id: string;
  symbol: string;
  agent_name: string;
  prediction: 'long' | 'short' | 'hold';
  confidence: number;
  predicted_at: string;
  actual_outcome?: 'correct' | 'incorrect' | 'pending';
  actual_return?: number;
  notes?: string;
}

export function HistoryTab() {
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [timeRange, setTimeRange] = useState<string>('7d');

  // Fetch prediction history
  const { data: historyData, isLoading } = useQuery({
    queryKey: ['agents', 'history', selectedAgent, timeRange],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/v1/agents/predictions/history`, {
        params: {
          agent_name: selectedAgent === 'all' ? undefined : selectedAgent,
          days: timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90,
        },
      });
      return response.data.data || [];
    },
    refetchInterval: 30000,
  });

  // Fetch prediction accuracy stats
  const { data: accuracyStats } = useQuery({
    queryKey: ['agents', 'accuracy', selectedAgent, timeRange],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/v1/agents/predictions/accuracy`, {
        params: {
          agent_name: selectedAgent === 'all' ? undefined : selectedAgent,
          days: timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90,
        },
      });
      return response.data.data || {};
    },
    refetchInterval: 30000,
  });

  const agentNameMap: Record<string, string> = {
    all: '全部Agent',
    technical: '技术分析',
    fundamental: '基本面分析',
    sentiment: '情绪分析',
    policy: '政策分析',
    risk: '风险管理',
  };

  const predictions: PredictionHistory[] = historyData || [];

  const correctPredictions = predictions.filter((p) => p.actual_outcome === 'correct').length;
  const totalCompleted = predictions.filter((p) => p.actual_outcome !== 'pending').length;
  const accuracyRate = totalCompleted > 0 ? (correctPredictions / totalCompleted) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card padding="md">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              <Filter size={16} className="inline mr-1" />
              筛选Agent
            </label>
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="all">全部Agent</option>
              <option value="technical">技术分析</option>
              <option value="fundamental">基本面分析</option>
              <option value="sentiment">情绪分析</option>
              <option value="policy">政策分析</option>
              <option value="risk">风险管理</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-primary mb-2">
              <Calendar size={16} className="inline mr-1" />
              时间范围
            </label>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="7d">最近7天</option>
              <option value="30d">最近30天</option>
              <option value="90d">最近90天</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Accuracy Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-primary-50 rounded-lg">
              <Target size={24} className="text-primary-500" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">总预测数</p>
              <p className="text-2xl font-bold text-text-primary">
                {predictions.length}
              </p>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-green-50 rounded-lg">
              <CheckCircle size={24} className="text-profit" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">正确预测</p>
              <p className="text-2xl font-bold text-profit">
                {correctPredictions}
              </p>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-red-50 rounded-lg">
              <XCircle size={24} className="text-loss" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">错误预测</p>
              <p className="text-2xl font-bold text-loss">
                {predictions.filter((p) => p.actual_outcome === 'incorrect').length}
              </p>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-50 rounded-lg">
              <TrendingUp size={24} className="text-blue-500" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">准确率</p>
              <p className="text-2xl font-bold text-text-primary">
                {accuracyRate.toFixed(1)}%
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Agent Performance Breakdown */}
      {accuracyStats && Object.keys(accuracyStats).length > 0 && (
        <Card title="各Agent表现对比" padding="md">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(accuracyStats).map(([agentName, stats]: [string, any]) => (
              <div
                key={agentName}
                className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
              >
                <h4 className="font-semibold text-text-primary mb-3">
                  {agentNameMap[agentName] || agentName}
                </h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">预测数:</span>
                    <span className="font-medium text-text-primary">{stats.total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">准确率:</span>
                    <span className="font-semibold text-profit">
                      {stats.accuracy ? `${stats.accuracy.toFixed(1)}%` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">平均收益:</span>
                    <span
                      className={`font-semibold ${
                        stats.avg_return >= 0 ? 'text-profit' : 'text-loss'
                      }`}
                    >
                      {stats.avg_return !== undefined
                        ? `${stats.avg_return >= 0 ? '+' : ''}${stats.avg_return.toFixed(2)}%`
                        : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Prediction History Table */}
      <Card title={`预测历史 - ${agentNameMap[selectedAgent]}`} padding="md">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loading size="lg" text="加载历史数据..." />
          </div>
        ) : predictions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                    时间
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                    股票代码
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                    Agent
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                    预测
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                    置信度
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                    实际收益
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-text-secondary uppercase tracking-wider">
                    结果
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {predictions.map((prediction) => (
                  <tr key={prediction.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-text-primary whitespace-nowrap">
                      {new Date(prediction.predicted_at).toLocaleDateString('zh-CN')}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-text-primary">
                      {prediction.symbol}
                    </td>
                    <td className="px-4 py-3 text-sm text-text-secondary">
                      {agentNameMap[prediction.agent_name] || prediction.agent_name}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded font-semibold ${
                          prediction.prediction === 'long'
                            ? 'bg-green-100 text-profit'
                            : prediction.prediction === 'short'
                            ? 'bg-red-100 text-loss'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {prediction.prediction === 'long' && <TrendingUp size={14} />}
                        {prediction.prediction === 'short' && <TrendingDown size={14} />}
                        {prediction.prediction === 'long'
                          ? '看多'
                          : prediction.prediction === 'short'
                          ? '看空'
                          : '持有'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-text-primary">
                      {(prediction.confidence * 100).toFixed(0)}%
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {prediction.actual_return !== undefined ? (
                        <span
                          className={`font-semibold ${
                            prediction.actual_return >= 0 ? 'text-profit' : 'text-loss'
                          }`}
                        >
                          {prediction.actual_return >= 0 ? '+' : ''}
                          {prediction.actual_return.toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-text-secondary">待确认</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {prediction.actual_outcome === 'correct' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-green-100 text-profit font-semibold">
                          <CheckCircle size={14} />
                          正确
                        </span>
                      ) : prediction.actual_outcome === 'incorrect' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-red-100 text-loss font-semibold">
                          <XCircle size={14} />
                          错误
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-gray-100 text-gray-600">
                          进行中
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-text-secondary">
            <Target size={48} className="mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium mb-2">暂无预测历史</p>
            <p className="text-sm">选择不同的Agent或时间范围查看历史数据</p>
          </div>
        )}
      </Card>
    </div>
  );
}
