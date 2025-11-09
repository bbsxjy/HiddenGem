import { useState } from 'react';
import { Card } from '@/components/common/Card';
import { Input } from '@/components/common/Input';
import { Button } from '@/components/common/Button';
import { runBacktest } from '@/api/strategies';
import type { BacktestResult } from '@/types/strategy';
import {
  Timer,
  Play,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Calendar,
  DollarSign,
  BarChart3,
  Activity,
} from 'lucide-react';

export function Backtest() {
  const [symbol, setSymbol] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [initialCash, setInitialCash] = useState('100000');
  const [strategyType, setStrategyType] = useState('rl');
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunBacktest = async () => {
    if (!symbol || !startDate || !endDate) {
      alert('请填写所有必需字段');
      return;
    }

    setIsRunning(true);
    setError(null);

    try {
      // 调用后端 API
      const result = await runBacktest(
        strategyType,
        symbol,
        {
          start_date: startDate,
          end_date: endDate,
          initial_capital: parseFloat(initialCash),
        }
      );

      setResults(result);
    } catch (err) {
      console.error('回测失败:', err);
      setError(err instanceof Error ? err.message : '回测失败，请稍后重试');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
            <Timer className="text-primary-500" size={32} />
            回测系统
          </h1>
          <p className="text-text-secondary mt-1">
            使用历史数据测试交易策略的表现，评估风险和收益
          </p>
        </div>
      </div>

      {/* Backtest Configuration */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Configuration Form */}
        <div className="lg:col-span-1">
          <Card title="回测配置" padding="md">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  股票代码 *
                </label>
                <Input
                  placeholder="例如: 600519.SH, NVDA"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  开始日期 *
                </label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  结束日期 *
                </label>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  初始资金 (元)
                </label>
                <Input
                  type="number"
                  placeholder="100000"
                  value={initialCash}
                  onChange={(e) => setInitialCash(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  策略类型
                </label>
                <select
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={strategyType}
                  onChange={(e) => setStrategyType(e.target.value)}
                >
                  <option value="rl">RL Agent策略</option>
                  <option value="technical">技术分析策略</option>
                  <option value="fundamental">基本面策略</option>
                  <option value="multi-agent">多Agent综合策略</option>
                </select>
              </div>

              <Button
                onClick={handleRunBacktest}
                disabled={isRunning}
                className="w-full"
              >
                <Play size={16} className="mr-2" />
                {isRunning ? '运行中...' : '开始回测'}
              </Button>

              <div className="pt-4 border-t border-gray-200">
                <div className="flex items-start gap-2 text-xs text-text-secondary">
                  <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
                  <p>
                    回测结果基于历史数据，不代表未来表现。请谨慎参考。
                  </p>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-2">
          <Card title="回测结果" padding="md">
            {isRunning ? (
              <div className="flex items-center justify-center h-96">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
                  <p className="text-text-secondary">正在运行回测...</p>
                </div>
              </div>
            ) : error ? (
              <div className="flex items-center justify-center h-96">
                <div className="text-center">
                  <AlertCircle className="mx-auto h-16 w-16 text-loss mb-4" />
                  <p className="text-loss font-medium mb-2">回测失败</p>
                  <p className="text-text-secondary text-sm">{error}</p>
                  <Button onClick={handleRunBacktest} className="mt-4">
                    重试
                  </Button>
                </div>
              </div>
            ) : results ? (
              <div className="space-y-6">
                {/* Key Metrics Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gradient-to-br from-profit/10 to-profit/5 p-4 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp size={16} className="text-profit" />
                      <span className="text-xs text-text-secondary">总收益率</span>
                    </div>
                    <p className="text-2xl font-bold text-profit">
                      {results.total_return_pct >= 0 ? '+' : ''}{results.total_return_pct.toFixed(2)}%
                    </p>
                  </div>

                  <div className="bg-gradient-to-br from-blue-50 to-blue-50/50 p-4 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <BarChart3 size={16} className="text-blue-500" />
                      <span className="text-xs text-text-secondary">夏普比率</span>
                    </div>
                    <p className="text-2xl font-bold text-blue-600">
                      {results.sharpe_ratio.toFixed(2)}
                    </p>
                  </div>

                  <div className="bg-gradient-to-br from-loss/10 to-loss/5 p-4 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingDown size={16} className="text-loss" />
                      <span className="text-xs text-text-secondary">最大回撤</span>
                    </div>
                    <p className="text-2xl font-bold text-loss">
                      {results.max_drawdown.toFixed(2)}%
                    </p>
                  </div>

                  <div className="bg-gradient-to-br from-primary-50 to-primary-50/50 p-4 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Activity size={16} className="text-primary-500" />
                      <span className="text-xs text-text-secondary">胜率</span>
                    </div>
                    <p className="text-2xl font-bold text-primary-600">
                      {(results.win_rate * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>

                {/* Detailed Stats */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-text-primary">交易统计</h3>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-text-secondary">总交易次数</span>
                        <span className="font-medium text-text-primary">
                          {results.total_trades}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-text-secondary">平均持仓天数</span>
                        <span className="font-medium text-text-primary">
                          {results.avg_holding_days.toFixed(1)} 天
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-text-secondary">胜率</span>
                        <span className="font-medium text-profit">
                          {(results.win_rate * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-text-primary">资金情况</h3>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-text-secondary">初始资金</span>
                        <span className="font-medium text-text-primary">
                          ¥{results.initial_capital.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-text-secondary">期末资金</span>
                        <span className="font-medium text-profit">
                          ¥{results.final_value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-text-secondary">总盈亏</span>
                        <span className={`font-medium ${results.total_return >= 0 ? 'text-profit' : 'text-loss'}`}>
                          {results.total_return >= 0 ? '+' : ''}¥{results.total_return.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Chart Placeholder */}
                <div className="border-t border-gray-200 pt-6">
                  <h3 className="text-sm font-semibold text-text-primary mb-4">资金曲线</h3>
                  <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center">
                    <p className="text-text-secondary text-sm">
                      图表功能开发中...
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-96">
                <div className="text-center">
                  <Timer className="mx-auto h-16 w-16 text-text-secondary mb-4" />
                  <p className="text-text-secondary">
                    配置回测参数后点击"开始回测"查看结果
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card padding="md">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-primary-50 rounded-lg">
              <Calendar size={20} className="text-primary-500" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-1">
                时间旅行回测
              </h3>
              <p className="text-xs text-text-secondary">
                使用真实历史数据，模拟实盘交易场景，避免未来函数
              </p>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-profit/10 rounded-lg">
              <Activity size={20} className="text-profit" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-1">
                多策略支持
              </h3>
              <p className="text-xs text-text-secondary">
                支持RL Agent、技术分析、基本面等多种策略回测
              </p>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-orange-50 rounded-lg">
              <DollarSign size={20} className="text-orange-500" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-1">
                交易成本计算
              </h3>
              <p className="text-xs text-text-secondary">
                自动计算手续费、印花税、滑点等交易成本
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
