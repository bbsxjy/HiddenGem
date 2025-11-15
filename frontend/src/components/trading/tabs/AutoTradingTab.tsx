import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { Loading } from '@/components/common/Loading';
import { useSettingsStore } from '@/store/useSettingsStore';
import { getStrategies } from '@/api/strategies';
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
  Edit,
  Save,
  X,
  BarChart3,
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

interface RiskParams {
  // 买入条件
  buyPriceChangeMin: number;      // 涨幅阈值 (%)
  buyVolumeRatioMin: number;      // 量比要求
  buyAmplitudeMax: number;        // 振幅控制 (%)
  buyTurnoverRateMax: number;     // 换手率控制 (%)
  // 卖出条件
  minHoldingDays: number;         // 最小持仓天数
  stopLossPct: number;            // 止损阈值 (%)
  takeProfitPct: number;          // 止盈阈值 (%)
  maxPositionPct: number;         // 单个仓位限制 (%)
}

export function AutoTradingTab() {
  const queryClient = useQueryClient();

  // Get refresh intervals and risk settings from settings store
  const { dataRefresh, riskControl } = useSettingsStore();

  // 自动交易配置
  const [symbols, setSymbols] = useState('000001,600519,000858');
  const [initialCash, setInitialCash] = useState(100000);
  const [checkInterval, setCheckInterval] = useState(5);
  const [useMultiAgent, setUseMultiAgent] = useState(true);

  // 策略选择 - 改为预定义的5种策略模式
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);

  // 预定义的5种策略模式
  const strategyModes = [
    {
      id: 'rl_only',
      name: '单RL模型',
      description: '纯强化学习决策，基于历史数据训练的PPO模型',
      icon: '🤖',
      color: 'blue',
      components: ['RL'],
    },
    {
      id: 'llm_agent_only',
      name: '单LLM Agent',
      description: '多Agent智能分析系统，7个专业分析师协同决策',
      icon: '🧠',
      color: 'purple',
      components: ['LLM Agent'],
    },
    {
      id: 'llm_memory',
      name: 'LLM + Memory Bank',
      description: 'LLM分析结合历史案例记忆库，从相似场景中学习',
      icon: '💾',
      color: 'green',
      components: ['LLM Agent', 'Memory Bank'],
    },
    {
      id: 'rl_llm',
      name: 'RL + LLM',
      description: '强化学习与LLM双重验证，提高决策准确性',
      icon: '🔄',
      color: 'orange',
      components: ['RL', 'LLM Agent'],
    },
    {
      id: 'rl_llm_memory',
      name: 'RL + LLM + Memory',
      description: '完整系统：强化学习 + LLM分析 + 历史案例，三重保障',
      icon: '⭐',
      color: 'red',
      components: ['RL', 'LLM Agent', 'Memory Bank'],
    },
  ];

  // 风险控制参数
  const [isEditingRisk, setIsEditingRisk] = useState(false);
  const [riskParams, setRiskParams] = useState<RiskParams>({
    buyPriceChangeMin: 3,
    buyVolumeRatioMin: 1.2,
    buyAmplitudeMax: 8,
    buyTurnoverRateMax: 15,
    minHoldingDays: 1,
    stopLossPct: riskControl.defaultStopLossPct || 5,
    takeProfitPct: riskControl.defaultTakeProfitPct || 8,
    maxPositionPct: riskControl.maxPositionPct || 5,
  });

  const { data: autoTradingStatus } = useQuery({
    queryKey: ['autoTradingStatus'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/v1/auto-trading/status`);
      return response.data.data;
    },
    refetchInterval: dataRefresh.marketDataInterval * 1000,
  });

  // Fetch stock decisions (real-time)
  const { data: stockDecisions } = useQuery({
    queryKey: ['stockDecisions'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/v1/auto-trading/decisions`);
      return response.data.data || [];
    },
    refetchInterval: dataRefresh.marketDataInterval * 1000,
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
    refetchInterval: dataRefresh.signalInterval * 1000,
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
        strategy_modes: selectedStrategies, // 传递选择的策略模式IDs
        risk_params: riskParams,
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

  // Toggle strategy selection
  const toggleStrategy = (strategyName: string) => {
    setSelectedStrategies(prev => {
      if (prev.includes(strategyName)) {
        return prev.filter(s => s !== strategyName);
      } else {
        return [...prev, strategyName];
      }
    });
  };

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
            disabled={startMutation.isPending || !symbols.trim() || selectedStrategies.length === 0}
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
          {/* 多策略对照面板 - 仅在选择多个策略时显示 */}
          {autoTradingStatus?.strategy_performances && autoTradingStatus.strategy_performances.length > 1 && (
            <Card title="策略表现对照" padding="md">
              <div className="space-y-4">
                <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg text-sm text-purple-800">
                  <strong>对照模式：</strong>
                  当前运行 {autoTradingStatus.strategy_performances.length} 个策略进行性能对照测试
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                  {autoTradingStatus.strategy_performances.map((perf: any) => {
                    const mode = strategyModes.find(m => m.id === perf.strategy_id);
                    const profitLoss = perf.profit_loss || 0;
                    const profitLossPct = perf.profit_loss_pct || 0;

                    return (
                      <Card key={perf.strategy_id} padding="md" className="border-2">
                        <div className="flex items-start gap-3 mb-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl ${
                            mode ? `bg-${mode.color}-100 text-${mode.color}-600` : 'bg-gray-100'
                          }`}>
                            {mode?.icon || '📊'}
                          </div>
                          <div className="flex-1">
                            <h4 className="font-semibold text-text-primary">{mode?.name || perf.strategy_id}</h4>
                            <p className="text-xs text-text-secondary">{mode?.description}</p>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-text-secondary">盈亏</span>
                            <span className={`text-lg font-bold ${profitLoss >= 0 ? 'text-profit' : 'text-loss'}`}>
                              {profitLoss >= 0 ? '+' : ''}¥{profitLoss.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </span>
                          </div>

                          <div className="flex justify-between items-center">
                            <span className="text-sm text-text-secondary">收益率</span>
                            <span className={`text-base font-semibold ${profitLossPct >= 0 ? 'text-profit' : 'text-loss'}`}>
                              {profitLossPct >= 0 ? '+' : ''}{profitLossPct.toFixed(2)}%
                            </span>
                          </div>

                          <div className="flex justify-between items-center">
                            <span className="text-sm text-text-secondary">交易次数</span>
                            <span className="text-base font-semibold text-text-primary">
                              {perf.total_trades || 0}
                            </span>
                          </div>

                          <div className="flex justify-between items-center">
                            <span className="text-sm text-text-secondary">胜率</span>
                            <span className="text-base font-semibold text-text-primary">
                              {perf.win_rate ? `${perf.win_rate.toFixed(1)}%` : 'N/A'}
                            </span>
                          </div>

                          <div className="flex justify-between items-center">
                            <span className="text-sm text-text-secondary">当前持仓</span>
                            <span className="text-base font-semibold text-text-primary">
                              {perf.num_positions || 0}
                            </span>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>

                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center gap-2 text-sm text-blue-800 mb-2">
                    <BarChart3 size={16} />
                    <strong>综合排名</strong>
                  </div>
                  <div className="space-y-1">
                    {[...autoTradingStatus.strategy_performances]
                      .sort((a, b) => (b.profit_loss_pct || 0) - (a.profit_loss_pct || 0))
                      .map((perf: any, index: number) => {
                        const mode = strategyModes.find(m => m.id === perf.strategy_id);
                        const medals = ['🥇', '🥈', '🥉'];

                        return (
                          <div key={perf.strategy_id} className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-2">
                              <span className="text-base">{medals[index] || `${index + 1}.`}</span>
                              <span className="font-medium text-text-primary">{mode?.name || perf.strategy_id}</span>
                            </div>
                            <span className={`font-semibold ${(perf.profit_loss_pct || 0) >= 0 ? 'text-profit' : 'text-loss'}`}>
                              {(perf.profit_loss_pct || 0) >= 0 ? '+' : ''}{(perf.profit_loss_pct || 0).toFixed(2)}%
                            </span>
                          </div>
                        );
                      })}
                  </div>
                </div>
              </div>
            </Card>
          )}

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
          <Card title="策略模式选择" padding="md">
            <div className="space-y-4">
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                <strong>提示：</strong>
                可以选择单个策略模式运行，也可以选择多个策略同时运行进行对照测试。
                多策略模式下，系统会为每个策略独立统计表现指标。
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {strategyModes.map((mode) => {
                  const isSelected = selectedStrategies.includes(mode.id);
                  const colorClasses = {
                    blue: 'border-blue-500 bg-blue-50',
                    purple: 'border-purple-500 bg-purple-50',
                    green: 'border-green-500 bg-green-50',
                    orange: 'border-orange-500 bg-orange-50',
                    red: 'border-red-500 bg-red-50',
                  };
                  const iconColorClasses = {
                    blue: 'bg-blue-100 text-blue-600',
                    purple: 'bg-purple-100 text-purple-600',
                    green: 'bg-green-100 text-green-600',
                    orange: 'bg-orange-100 text-orange-600',
                    red: 'bg-red-100 text-red-600',
                  };

                  return (
                    <div
                      key={mode.id}
                      className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                        isSelected
                          ? colorClasses[mode.color]
                          : 'border-gray-200 hover:border-gray-300 bg-white'
                      }`}
                      onClick={() => toggleStrategy(mode.id)}
                    >
                      <div className="flex items-start gap-3 mb-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl ${
                          isSelected ? iconColorClasses[mode.color] : 'bg-gray-100'
                        }`}>
                          {mode.icon}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              className="w-4 h-4 text-primary-500 border-gray-300 rounded focus:ring-primary-500"
                              checked={isSelected}
                              onChange={() => {}} // Handled by parent div onClick
                            />
                            <span className="font-semibold text-text-primary">{mode.name}</span>
                          </div>
                        </div>
                      </div>
                      <p className="text-xs text-text-secondary mb-2">
                        {mode.description}
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {mode.components.map((comp) => (
                          <span
                            key={comp}
                            className="px-2 py-0.5 bg-white border border-gray-200 rounded text-xs text-text-secondary"
                          >
                            {comp}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
                <strong>已选择 {selectedStrategies.length} 个策略模式</strong>
                {selectedStrategies.length > 1 && (
                  <span className="ml-2">
                    - 将同时运行并进行性能对照
                  </span>
                )}
                {selectedStrategies.length === 0 && (
                  <span className="ml-2 text-green-700">
                    - 请至少选择一个策略模式
                  </span>
                )}
              </div>
            </div>
          </Card>

          {/* Risk Control */}
          <Card
            title="风险控制（T+1制度）"
            padding="md"
            headerAction={
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsEditingRisk(!isEditingRisk)}
              >
                {isEditingRisk ? (
                  <>
                    <X size={14} className="mr-1" />
                    取消
                  </>
                ) : (
                  <>
                    <Edit size={14} className="mr-1" />
                    编辑
                  </>
                )}
              </Button>
            }
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 border border-gray-200 rounded-lg">
                <h3 className="font-semibold text-text-primary mb-3">买入条件</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">涨幅阈值 (%):</span>
                    {isEditingRisk ? (
                      <Input
                        type="number"
                        className="w-24 text-right"
                        value={riskParams.buyPriceChangeMin}
                        onChange={(e) => setRiskParams({ ...riskParams, buyPriceChangeMin: Number(e.target.value) })}
                        min={0}
                        max={20}
                        step={0.1}
                      />
                    ) : (
                      <span className="font-semibold text-text-primary">&gt; {riskParams.buyPriceChangeMin}%</span>
                    )}
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">量比要求:</span>
                    {isEditingRisk ? (
                      <Input
                        type="number"
                        className="w-24 text-right"
                        value={riskParams.buyVolumeRatioMin}
                        onChange={(e) => setRiskParams({ ...riskParams, buyVolumeRatioMin: Number(e.target.value) })}
                        min={0.5}
                        max={5}
                        step={0.1}
                      />
                    ) : (
                      <span className="font-semibold text-text-primary">&gt; {riskParams.buyVolumeRatioMin}</span>
                    )}
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">振幅控制 (%):</span>
                    {isEditingRisk ? (
                      <Input
                        type="number"
                        className="w-24 text-right"
                        value={riskParams.buyAmplitudeMax}
                        onChange={(e) => setRiskParams({ ...riskParams, buyAmplitudeMax: Number(e.target.value) })}
                        min={1}
                        max={20}
                        step={0.1}
                      />
                    ) : (
                      <span className="font-semibold text-text-primary">&lt; {riskParams.buyAmplitudeMax}%</span>
                    )}
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">换手率控制 (%):</span>
                    {isEditingRisk ? (
                      <Input
                        type="number"
                        className="w-24 text-right"
                        value={riskParams.buyTurnoverRateMax}
                        onChange={(e) => setRiskParams({ ...riskParams, buyTurnoverRateMax: Number(e.target.value) })}
                        min={1}
                        max={50}
                        step={0.5}
                      />
                    ) : (
                      <span className="font-semibold text-text-primary">&lt; {riskParams.buyTurnoverRateMax}%</span>
                    )}
                  </div>
                </div>
              </div>

              <div className="p-4 border border-gray-200 rounded-lg">
                <h3 className="font-semibold text-text-primary mb-3">卖出条件</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">最小持仓天数:</span>
                    {isEditingRisk ? (
                      <Input
                        type="number"
                        className="w-24 text-right"
                        value={riskParams.minHoldingDays}
                        onChange={(e) => setRiskParams({ ...riskParams, minHoldingDays: Number(e.target.value) })}
                        min={1}
                        max={30}
                      />
                    ) : (
                      <span className="font-semibold text-text-primary">{riskParams.minHoldingDays}天</span>
                    )}
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">止损阈值 (%):</span>
                    {isEditingRisk ? (
                      <Input
                        type="number"
                        className="w-24 text-right"
                        value={riskParams.stopLossPct}
                        onChange={(e) => setRiskParams({ ...riskParams, stopLossPct: Number(e.target.value) })}
                        min={1}
                        max={50}
                        step={0.5}
                      />
                    ) : (
                      <span className="font-semibold text-loss">-{riskParams.stopLossPct}%</span>
                    )}
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">止盈阈值 (%):</span>
                    {isEditingRisk ? (
                      <Input
                        type="number"
                        className="w-24 text-right"
                        value={riskParams.takeProfitPct}
                        onChange={(e) => setRiskParams({ ...riskParams, takeProfitPct: Number(e.target.value) })}
                        min={1}
                        max={100}
                        step={0.5}
                      />
                    ) : (
                      <span className="font-semibold text-profit">+{riskParams.takeProfitPct}%</span>
                    )}
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-text-secondary">单个仓位限制 (%):</span>
                    {isEditingRisk ? (
                      <Input
                        type="number"
                        className="w-24 text-right"
                        value={riskParams.maxPositionPct}
                        onChange={(e) => setRiskParams({ ...riskParams, maxPositionPct: Number(e.target.value) })}
                        min={1}
                        max={100}
                        step={0.5}
                      />
                    ) : (
                      <span className="font-semibold text-text-primary">{riskParams.maxPositionPct}%</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {isEditingRisk && (
              <div className="mt-4 flex justify-end gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setRiskParams({
                      buyPriceChangeMin: 3,
                      buyVolumeRatioMin: 1.2,
                      buyAmplitudeMax: 8,
                      buyTurnoverRateMax: 15,
                      minHoldingDays: 1,
                      stopLossPct: riskControl.defaultStopLossPct || 5,
                      takeProfitPct: riskControl.defaultTakeProfitPct || 8,
                      maxPositionPct: riskControl.maxPositionPct || 5,
                    });
                    setIsEditingRisk(false);
                  }}
                >
                  恢复默认
                </Button>
                <Button
                  size="sm"
                  onClick={() => setIsEditingRisk(false)}
                >
                  <Save size={14} className="mr-1" />
                  保存
                </Button>
              </div>
            )}

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
