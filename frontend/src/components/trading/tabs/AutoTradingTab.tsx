import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import {
  Play,
  Square,
  TrendingUp,
  TrendingDown,
  Clock,
  DollarSign,
  Activity,
  Minus,
  AlertCircle,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface StockDecision {
  symbol: string;
  name?: string;
  last_check: string;
  decision: 'buy' | 'sell' | 'hold' | 'skip';
  reason: string;
  price?: number;
  change?: number;
  volume?: number;
  suggested_quantity?: number;
  confidence?: number;
}

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

  // Fetch stock decisions (real-time)
  const { data: stockDecisions } = useQuery({
    queryKey: ['stockDecisions'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/v1/auto-trading/decisions`);
      return response.data.data || [];
    },
    refetchInterval: 30000,
    enabled: autoTradingStatus?.is_running || false,
  });

  // Fetch recent trading signals
  const { data: recentSignals } = useQuery({
    queryKey: ['recentSignals'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/v1/signals/recent`, {
        params: { limit: 20 }
      });
      return response.data.data || [];
    },
    refetchInterval: 30000,
    enabled: autoTradingStatus?.is_running || false,
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
  const isTradingHours = autoTradingStatus?.is_trading_hours || false;
  const profitLoss = autoTradingStatus?.profit_loss || 0;
  const profitLossPct = autoTradingStatus?.profit_loss_pct || 0;
  const decisions = stockDecisions || [];

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'buy':
        return <TrendingUp className="text-profit" size={20} />;
      case 'sell':
        return <TrendingDown className="text-loss" size={20} />;
      case 'hold':
        return <Minus className="text-gray-500" size={20} />;
      default:
        return <Activity className="text-gray-400" size={20} />;
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'buy':
        return 'text-profit bg-green-50 border-green-200';
      case 'sell':
        return 'text-loss bg-red-50 border-red-200';
      case 'hold':
        return 'text-gray-600 bg-gray-50 border-gray-200';
      default:
        return 'text-gray-500 bg-gray-50 border-gray-200';
    }
  };

  const getDecisionText = (decision: string) => {
    switch (decision) {
      case 'buy':
        return '买入';
      case 'sell':
        return '卖出';
      case 'hold':
        return '持有';
      case 'skip':
        return '跳过';
      default:
        return '未知';
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

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

      {/* 运行时显示实时监控 */}
      {isRunning && (
        <>
          {/* Status Overview */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card padding="md">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-secondary mb-1">系统状态</p>
                  <p className="text-lg font-bold text-text-primary">
                    运行中
                  </p>
                </div>
                <div className="w-12 h-12 rounded-full flex items-center justify-center bg-green-100">
                  <CheckCircle className="text-profit" size={24} />
                </div>
              </div>
            </Card>

            <Card padding="md">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-secondary mb-1">交易时段</p>
                  <p className="text-lg font-bold text-text-primary">
                    {isTradingHours ? '进行中' : '非交易时间'}
                  </p>
                </div>
                <div className={`w-12 h-12 rounded-full flex items-center justify-center ${isTradingHours ? 'bg-green-100' : 'bg-gray-100'}`}>
                  <Clock className={isTradingHours ? 'text-profit' : 'text-gray-400'} size={24} />
                </div>
              </div>
            </Card>

            <Card padding="md">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-secondary mb-1">监控股票</p>
                  <p className="text-lg font-bold text-text-primary">
                    {autoTradingStatus?.current_symbols?.length || 0}
                  </p>
                </div>
                <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                  <Activity className="text-primary-500" size={24} />
                </div>
              </div>
            </Card>

            <Card padding="md">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-text-secondary mb-1">今日交易</p>
                  <p className="text-lg font-bold text-text-primary">
                    {autoTradingStatus?.total_trades || 0}
                  </p>
                </div>
                <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
                  <DollarSign className="text-purple-600" size={24} />
                </div>
              </div>
            </Card>
          </div>

          {/* System Alert */}
          {!isTradingHours && autoTradingStatus?.next_check_time && (
            <Card padding="md" className="border-2 border-yellow-200 bg-yellow-50">
              <div className="flex items-start gap-3">
                <AlertCircle className="text-yellow-600 flex-shrink-0 mt-0.5" size={20} />
                <div>
                  <h3 className="font-semibold text-yellow-900 mb-1">等待下一个交易时段</h3>
                  <p className="text-sm text-yellow-800">
                    下次检查时间: {new Date(autoTradingStatus.next_check_time).toLocaleString('zh-CN')}
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Stock Decisions */}
          <Card title="实时股票判断" padding="md">
            <div className="space-y-3">
              {decisions.length === 0 ? (
                <div className="text-center py-8 text-text-secondary">
                  <Activity size={48} className="mx-auto mb-3 text-gray-300" />
                  <p>等待交易决策...</p>
                </div>
              ) : (
                decisions.map((stock: StockDecision) => (
                  <div
                    key={stock.symbol}
                    className="p-4 border rounded-lg hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        {getDecisionIcon(stock.decision)}
                        <div>
                          <h3 className="font-semibold text-text-primary">
                            {stock.symbol}
                            {stock.name && stock.name !== stock.symbol && (
                              <span className="text-sm text-text-secondary ml-2">{stock.name}</span>
                            )}
                          </h3>
                          <p className="text-xs text-text-secondary">
                            最后检查: {formatTime(stock.last_check)}
                          </p>
                        </div>
                      </div>
                      <div className={`px-3 py-1 rounded-full border text-sm font-semibold ${getDecisionColor(stock.decision)}`}>
                        {getDecisionText(stock.decision)}
                      </div>
                    </div>

                    <div className="pl-8">
                      <p className="text-sm text-text-secondary mb-2">
                        <span className="font-medium">决策原因：</span>
                        {stock.reason}
                      </p>

                      {stock.price && (
                        <div className="flex items-center gap-4 mb-2 text-sm">
                          <div>
                            <span className="text-text-secondary">当前价格：</span>
                            <span className="font-semibold text-text-primary ml-1">¥{stock.price.toFixed(2)}</span>
                          </div>
                          {stock.change !== undefined && (
                            <div>
                              <span className="text-text-secondary">涨跌幅：</span>
                              <span className={`font-semibold ml-1 ${stock.change >= 0 ? 'text-profit' : 'text-loss'}`}>
                                {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                              </span>
                            </div>
                          )}
                          {stock.volume && (
                            <div>
                              <span className="text-text-secondary">成交量：</span>
                              <span className="font-medium text-text-primary ml-1">
                                {(stock.volume / 10000).toFixed(2)}万
                              </span>
                            </div>
                          )}
                        </div>
                      )}

                      {stock.confidence !== undefined && (
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-sm text-text-secondary">置信度：</span>
                          <div className="flex-1 max-w-xs bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-primary-500 h-2 rounded-full"
                              style={{ width: `${stock.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium text-text-primary">
                            {(stock.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}

                      {stock.suggested_quantity && (
                        <p className="text-sm text-text-secondary">
                          <span className="font-medium">建议数量：</span>
                          {stock.suggested_quantity}股
                          <span className="ml-2 text-xs">
                            (约 ¥{(stock.suggested_quantity * (stock.price || 0)).toFixed(0)})
                          </span>
                        </p>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>

          {/* Recent Signals */}
          {recentSignals && recentSignals.length > 0 && (
            <Card title="最近交易信号" padding="md">
              <div className="space-y-2">
                {recentSignals.slice(0, 10).map((signal: any, index: number) => (
                  <div
                    key={index}
                    className="p-3 border-l-4 rounded bg-gray-50"
                    style={{
                      borderColor: signal.direction === 'long' ? '#10b981' : signal.direction === 'short' ? '#ef4444' : '#6b7280'
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-semibold text-text-primary mr-2">{signal.symbol}</span>
                        <span className={`text-sm ${signal.direction === 'long' ? 'text-profit' : signal.direction === 'short' ? 'text-loss' : 'text-gray-600'}`}>
                          {signal.direction === 'long' ? '做多' : signal.direction === 'short' ? '做空' : '持有'}
                        </span>
                      </div>
                      <span className="text-xs text-text-secondary">
                        {new Date(signal.timestamp).toLocaleString('zh-CN')}
                      </span>
                    </div>
                    {signal.reasoning && (
                      <p className="text-sm text-text-secondary mt-1">{signal.reasoning}</p>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      {/* 停止时显示配置面板 */}
      {!isRunning && (
        <>
          {/* Configuration Form */}
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
        </>
      )}
    </div>
  );
}
