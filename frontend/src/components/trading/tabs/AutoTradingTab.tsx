import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Play, Square, TrendingUp, TrendingDown, Clock, DollarSign, Activity } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function AutoTradingTab() {
  const queryClient = useQueryClient();

  // 自动交易配置
  const [symbols, setSymbols] = useState('000001,600519,000858');
  const [initialCash, setInitialCash] = useState(100000);
  const [checkInterval, setCheckInterval] = useState(5);
  const [useMultiAgent, setUseMultiAgent] = useState(true);

  // Fetch auto trading status
  const { data: autoTradingStatus } = useQuery({
    queryKey: ['autoTradingStatus'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/v1/auto-trading/status`);
      return response.data.data;
    },
    refetchInterval: 30000,
  });

  // Start auto trading mutation
  const startMutation = useMutation({
    mutationFn: async () => {
      const symbolList = symbols.split(',').map(s => s.trim()).filter(Boolean);
      const response = await axios.post(`${API_BASE_URL}/api/v1/auto-trading/start`, {
        symbols: symbolList,
        initial_cash: initialCash,
        check_interval: checkInterval,
        use_multi_agent: useMultiAgent,
        strategies: ['rl', 'multi_agent']
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['autoTradingStatus'] });
    },
  });

  // Stop auto trading mutation
  const stopMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${API_BASE_URL}/api/v1/auto-trading/stop`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['autoTradingStatus'] });
    },
  });

  const isRunning = autoTradingStatus?.is_running || false;
  const profitLoss = autoTradingStatus?.profit_loss || 0;
  const profitLossPct = autoTradingStatus?.profit_loss_pct || 0;

  return (
    <div className="space-y-6">
      {/* Status Display */}
      <div className="p-4 border-2 border-dashed rounded-lg" style={{
        borderColor: isRunning ? '#10b981' : '#d1d5db',
        backgroundColor: isRunning ? '#f0fdf4' : '#f9fafb'
      }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-profit animate-pulse' : 'bg-gray-400'}`} />
            <h3 className="font-semibold text-text-primary">
              状态: {isRunning ? '运行中' : '未运行'}
            </h3>
          </div>
          {isRunning && autoTradingStatus?.started_at && (
            <span className="text-xs text-text-secondary">
              启动于: {new Date(autoTradingStatus.started_at).toLocaleString('zh-CN')}
            </span>
          )}
        </div>

        {isRunning && autoTradingStatus && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-3 rounded-lg border border-gray-200">
              <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                <DollarSign size={14} />
                总资产
              </div>
              <div className="text-lg font-bold text-text-primary">
                ¥{autoTradingStatus.total_assets.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>

            <div className="bg-white p-3 rounded-lg border border-gray-200">
              <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                {profitLoss >= 0 ? <TrendingUp size={14} className="text-profit" /> : <TrendingDown size={14} className="text-loss" />}
                盈亏
              </div>
              <div className={`text-lg font-bold ${profitLoss >= 0 ? 'text-profit' : 'text-loss'}`}>
                {profitLoss >= 0 ? '+' : ''}¥{profitLoss.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                <span className="text-sm ml-2">({profitLossPct >= 0 ? '+' : ''}{profitLossPct.toFixed(2)}%)</span>
              </div>
            </div>

            <div className="bg-white p-3 rounded-lg border border-gray-200">
              <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                <Activity size={14} />
                交易次数
              </div>
              <div className="text-lg font-bold text-text-primary">
                {autoTradingStatus.total_trades}
              </div>
            </div>

            <div className="bg-white p-3 rounded-lg border border-gray-200">
              <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                <Clock size={14} />
                交易时段
              </div>
              <div className="text-sm font-semibold text-text-primary">
                {autoTradingStatus.is_trading_hours ? (
                  <span className="text-profit">进行中</span>
                ) : (
                  <span className="text-text-secondary">非交易时间</span>
                )}
              </div>
            </div>
          </div>
        )}

        {isRunning && autoTradingStatus?.next_check_time && (
          <div className="mt-3 text-xs text-text-secondary">
            下次检查时间: {new Date(autoTradingStatus.next_check_time).toLocaleString('zh-CN')}
          </div>
        )}
      </div>

      {/* Configuration Form */}
      {!isRunning && (
        <Card title="配置参数" padding="md">
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  交易股票列表 <span className="text-xs text-text-secondary">(逗号分隔)</span>
                </label>
                <Input
                  placeholder="例如: 000001,600519,000858"
                  value={symbols}
                  onChange={(e) => setSymbols(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  初始资金 (CNY)
                </label>
                <Input
                  type="number"
                  placeholder="100000"
                  value={initialCash}
                  onChange={(e) => setInitialCash(Number(e.target.value))}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  检查间隔 (分钟)
                </label>
                <Input
                  type="number"
                  placeholder="5"
                  value={checkInterval}
                  onChange={(e) => setCheckInterval(Number(e.target.value))}
                />
              </div>

              <div className="flex items-center">
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="w-4 h-4 text-primary-500 border-gray-300 rounded focus:ring-primary-500"
                    checked={useMultiAgent}
                    onChange={(e) => setUseMultiAgent(e.target.checked)}
                  />
                  <span className="ml-2 text-sm font-medium text-text-primary">
                    启用多Agent智能分析
                  </span>
                </label>
              </div>
            </div>

            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
              <strong>说明：</strong>
              自动交易系统将在中国A股交易时间（9:30-11:30, 13:00-15:00）自动执行交易决策。
              非交易时间系统会等待到下一个交易时段。系统遵循T+1规则，今天买入的股票明天才能卖出。
            </div>
          </div>
        </Card>
      )}

      {/* Control Buttons */}
      <div className="flex gap-3">
        {!isRunning ? (
          <Button
            onClick={() => startMutation.mutate()}
            disabled={startMutation.isPending || !symbols.trim()}
            className="flex items-center gap-2"
          >
            <Play size={16} />
            启动自动交易
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
            停止自动交易
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

      {/* Strategy Selection */}
      <Card title="策略选择" padding="md">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 border border-gray-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                className="w-4 h-4 text-primary-500 border-gray-300 rounded focus:ring-primary-500"
                defaultChecked
                disabled
              />
              <span className="font-semibold text-text-primary">RL策略</span>
            </div>
            <p className="text-sm text-text-secondary">深度强化学习策略</p>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                className="w-4 h-4 text-primary-500 border-gray-300 rounded focus:ring-primary-500"
                defaultChecked
                disabled
              />
              <span className="font-semibold text-text-primary">Multi-Agent策略</span>
            </div>
            <p className="text-sm text-text-secondary">多Agent智能分析</p>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg bg-gray-50">
            <div className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                className="w-4 h-4 text-primary-500 border-gray-300 rounded focus:ring-primary-500"
                defaultChecked
                checked
                readOnly
              />
              <span className="font-semibold text-text-primary">简化规则策略</span>
            </div>
            <p className="text-sm text-text-secondary">当前使用</p>
          </div>
        </div>
      </Card>

      {/* Risk Control */}
      <Card title="风险控制（T+1制度）" padding="md">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 border border-gray-200 rounded-lg">
            <h3 className="font-semibold text-text-primary mb-3">买入条件（更严格）</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-text-secondary">涨幅阈值:</span>
                <span className="font-semibold text-text-primary">&gt; 3%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">量比要求:</span>
                <span className="font-semibold text-text-primary">&gt; 1.2</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">振幅控制:</span>
                <span className="font-semibold text-text-primary">&lt; 8%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">换手率控制:</span>
                <span className="font-semibold text-text-primary">&lt; 15%</span>
              </div>
            </div>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg">
            <h3 className="font-semibold text-text-primary mb-3">卖出条件（T+1限制）</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-text-secondary">最小持仓天数:</span>
                <span className="font-semibold text-text-primary">1天</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">止损阈值:</span>
                <span className="font-semibold text-loss">-5%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">止盈阈值:</span>
                <span className="font-semibold text-profit">+8%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">单个仓位限制:</span>
                <span className="font-semibold text-text-primary">5%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
          <strong>T+1制度说明：</strong>
          由于A股实行T+1交易制度，今天买入的股票需要明天才能卖出，因此买入条件更加严格，
          止损止盈阈值也相应调整，以降低隔夜持仓风险。
        </div>
      </Card>

      {/* Running History */}
      {isRunning && (
        <Card title="运行历史（最近7天）" padding="md">
          <div className="space-y-2">
            <div className="text-sm text-text-secondary text-center py-8">
              运行历史数据（待实现）
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
