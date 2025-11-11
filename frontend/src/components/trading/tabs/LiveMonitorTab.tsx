import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { useSettingsStore } from '@/store/useSettingsStore';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  AlertCircle,
  CheckCircle,
  XCircle,
  DollarSign,
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

export function LiveMonitorTab() {
  // Get refresh intervals from settings
  const { dataRefresh } = useSettingsStore();

  // Fetch auto trading status
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
  });

  const isRunning = autoTradingStatus?.is_running || false;
  const isTradingHours = autoTradingStatus?.is_trading_hours || false;
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
      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card padding="md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary mb-1">系统状态</p>
              <p className="text-lg font-bold text-text-primary">
                {isRunning ? '运行中' : '已停止'}
              </p>
            </div>
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${isRunning ? 'bg-green-100' : 'bg-gray-100'}`}>
              {isRunning ? (
                <CheckCircle className="text-profit" size={24} />
              ) : (
                <XCircle className="text-gray-400" size={24} />
              )}
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
      {isRunning && !isTradingHours && autoTradingStatus?.next_check_time && (
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

      {!isRunning && (
        <Card padding="md" className="border-2 border-gray-200 bg-gray-50">
          <div className="flex items-start gap-3">
            <AlertCircle className="text-gray-600 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">自动交易未运行</h3>
              <p className="text-sm text-gray-700">
                前往自动交易Tab启动系统
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Stock Decisions */}
      {isRunning && (
        <Card title="实时股票判断" padding="md">
          <div className="space-y-3">
            {decisions.length === 0 ? (
              <div className="text-center py-8 text-text-secondary">
                <Activity size={48} className="mx-auto mb-3 text-gray-300" />
                <p>等待交易决策...</p>
              </div>
            ) : (
              decisions.map((stock) => (
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
      )}

      {/* Recent Signals */}
      {isRunning && recentSignals && recentSignals.length > 0 && (
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
    </div>
  );
}
