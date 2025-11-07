import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Input } from '@/components/common/Input';
import { Loading } from '@/components/common/Loading';
import { analyzePosition } from '@/api/agents';
import { getChangeColor } from '@/utils/format';
import type { HoldingsInfo, PositionAnalysisResponse } from '@/types/agent';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Clock,
  Target,
  Calendar,
  DollarSign,
} from 'lucide-react';

interface PositionAnalysisProps {
  symbol: string;
}

export function PositionAnalysis({ symbol }: PositionAnalysisProps) {
  const [holdings, setHoldings] = useState<HoldingsInfo>({
    quantity: 0,
    avg_price: 0,
    purchase_date: '',
    current_price: undefined,
  });

  const analysisMutation = useMutation({
    mutationFn: () => analyzePosition(symbol, { holdings }),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (holdings.quantity > 0 && holdings.avg_price > 0 && holdings.purchase_date) {
      analysisMutation.mutate();
    }
  };

  const result = analysisMutation.data;

  const getActionColor = (action: string) => {
    switch (action) {
      case '卖出':
        return 'text-loss bg-red-50 border-red-200';
      case '持有':
        return 'text-gray-600 bg-gray-50 border-gray-200';
      case '加仓':
        return 'text-profit bg-green-50 border-green-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case '立即':
        return 'text-red-600 bg-red-100';
      case '短期':
        return 'text-orange-600 bg-orange-100';
      case '中期':
        return 'text-blue-600 bg-blue-100';
      case '长期':
        return 'text-green-600 bg-green-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="space-y-6">
      {/* Holdings Input Form */}
      <Card title="持仓信息" padding="md">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                持仓数量（股）
              </label>
              <Input
                type="number"
                value={holdings.quantity || ''}
                onChange={(e) =>
                  setHoldings({ ...holdings, quantity: parseFloat(e.target.value) || 0 })
                }
                placeholder="1000"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                平均成本价（元）
              </label>
              <Input
                type="number"
                step="0.01"
                value={holdings.avg_price || ''}
                onChange={(e) =>
                  setHoldings({ ...holdings, avg_price: parseFloat(e.target.value) || 0 })
                }
                placeholder="45.50"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                买入日期
              </label>
              <Input
                type="date"
                value={holdings.purchase_date}
                onChange={(e) =>
                  setHoldings({ ...holdings, purchase_date: e.target.value })
                }
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                当前价格（可选）
              </label>
              <Input
                type="number"
                step="0.01"
                value={holdings.current_price || ''}
                onChange={(e) =>
                  setHoldings({
                    ...holdings,
                    current_price: e.target.value ? parseFloat(e.target.value) : undefined,
                  })
                }
                placeholder="42.30"
              />
              <p className="text-xs text-text-secondary mt-1">
                留空则系统自动估算
              </p>
            </div>
          </div>

          <button
            type="submit"
            disabled={analysisMutation.isPending}
            className="w-full px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {analysisMutation.isPending ? '分析中...' : '开始持仓分析'}
          </button>
        </form>

        <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded-lg">
          <p className="text-sm text-blue-800 font-medium mb-2">💡 持仓分析功能</p>
          <div className="text-xs text-blue-700 space-y-1">
            <p>• 根据您的持仓成本和当前市场分析提供决策建议</p>
            <p>• 评估卖出、持有、加仓三个方向的可行性</p>
            <p>• 如果亏损，分析回本可能性和预计时间</p>
          </div>
        </div>
      </Card>

      {/* Loading State */}
      {analysisMutation.isPending && (
        <Card padding="md">
          <div className="flex flex-col items-center justify-center py-12">
            <Loading size="lg" text="正在分析持仓..." />
            <p className="text-sm text-text-secondary mt-4">
              分析大约需要 30-60 秒，请耐心等待
            </p>
          </div>
        </Card>
      )}

      {/* Error State */}
      {analysisMutation.isError && (
        <Card title="分析失败" padding="md">
          <div className="text-center text-loss py-8">
            {analysisMutation.error instanceof Error
              ? analysisMutation.error.message
              : '持仓分析失败，请稍后重试'}
          </div>
        </Card>
      )}

      {/* Analysis Results */}
      {result?.position_analysis && (
        <div className="space-y-6">
          {/* Decision Card - 根据实际返回数据推断决策 */}
          <Card title="决策建议" padding="md">
            <div className="space-y-4">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div className="flex items-center gap-3">
                  {/* 根据 sell/hold/add 推断主要决策 */}
                  {result.position_analysis.sell?.should_sell && (
                    <div className="px-4 py-2 rounded-lg font-bold text-lg border-2 text-loss bg-red-50 border-red-200">
                      卖出
                    </div>
                  )}
                  {result.position_analysis.add?.should_add && (
                    <div className="px-4 py-2 rounded-lg font-bold text-lg border-2 text-profit bg-green-50 border-green-200">
                      加仓
                    </div>
                  )}
                  {result.position_analysis.hold?.should_hold && !result.position_analysis.sell?.should_sell && !result.position_analysis.add?.should_add && (
                    <div className="px-4 py-2 rounded-lg font-bold text-lg border-2 text-gray-600 bg-gray-50 border-gray-200">
                      持有
                    </div>
                  )}
                  {!result.position_analysis.sell?.should_sell && !result.position_analysis.hold?.should_hold && !result.position_analysis.add?.should_add && (
                    <div className="px-4 py-2 rounded-lg font-bold text-lg border-2 text-gray-600 bg-gray-50 border-gray-200">
                      观望
                    </div>
                  )}
                </div>
              </div>

              {/* 显示最相关的建议理由 */}
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                <p className="text-sm text-text-primary leading-relaxed">
                  {result.position_analysis.sell?.should_sell
                    ? result.position_analysis.sell.reason
                    : result.position_analysis.add?.should_add
                    ? result.position_analysis.add.reason
                    : result.position_analysis.hold?.reason || '请根据自身风险承受能力谨慎决策'}
                </p>
              </div>
            </div>
          </Card>

          {/* Profit/Loss Card */}
          <Card title="盈亏情况" padding="md">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <TrendingUp size={14} />
                  <span>浮动盈亏</span>
                </div>
                <div
                  className={`text-xl font-bold ${
                    getChangeColor(result.position_analysis.profit_loss.current_pnl, symbol)
                  }`}
                >
                  ¥{result.position_analysis.profit_loss.current_pnl.toFixed(2)}
                </div>
                <div
                  className={`text-sm ${
                    getChangeColor(result.position_analysis.profit_loss.current_pnl_pct, symbol)
                  }`}
                >
                  {result.position_analysis.profit_loss.current_pnl_pct >= 0 ? '+' : ''}
                  {result.position_analysis.profit_loss.current_pnl_pct.toFixed(2)}%
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <DollarSign size={14} />
                  <span>成本价 / 当前价</span>
                </div>
                <div className="text-lg font-bold text-text-primary">
                  ¥{result.position_analysis.profit_loss.cost_price.toFixed(2)}
                </div>
                <div className="text-sm text-text-secondary">
                  ¥{result.position_analysis.profit_loss.current_price.toFixed(2)}
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <Clock size={14} />
                  <span>持仓天数</span>
                </div>
                <div className="text-xl font-bold text-text-primary">
                  {result.position_analysis.profit_loss.holding_days}
                </div>
                <div className="text-sm text-text-secondary">天</div>
              </div>
            </div>
          </Card>

          {/* Recommendations */}
          <Card title="详细建议" padding="md">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Sell Recommendation */}
              <div className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingDown
                    className={
                      result.position_analysis.sell?.should_sell
                        ? 'text-loss'
                        : 'text-gray-400'
                    }
                  />
                  <h4 className="text-sm font-semibold text-text-primary">卖出建议</h4>
                </div>
                <div className="space-y-2">
                  <div
                    className={`text-xs px-2 py-1 rounded font-medium inline-block ${
                      result.position_analysis.sell?.should_sell
                        ? 'bg-red-100 text-red-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {result.position_analysis.sell?.should_sell
                      ? '建议卖出'
                      : '不建议卖出'}
                  </div>
                  {result.position_analysis.sell?.suggested_price && (
                    <div className="text-sm">
                      <span className="text-text-secondary">建议价格: </span>
                      <span className="font-semibold">
                        ¥{result.position_analysis.sell.suggested_price.toFixed(2)}
                      </span>
                    </div>
                  )}
                  <p className="text-xs text-text-secondary leading-relaxed">
                    {result.position_analysis.sell?.reason || '暂无建议'}
                  </p>
                </div>
              </div>

              {/* Hold Recommendation */}
              <div className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <Minus
                    className={
                      result.position_analysis.hold?.should_hold
                        ? 'text-primary-500'
                        : 'text-gray-400'
                    }
                  />
                  <h4 className="text-sm font-semibold text-text-primary">持有建议</h4>
                </div>
                <div className="space-y-2">
                  <div
                    className={`text-xs px-2 py-1 rounded font-medium inline-block ${
                      result.position_analysis.hold?.should_hold
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {result.position_analysis.hold?.should_hold
                      ? '建议持有'
                      : '不建议持有'}
                  </div>
                  {result.position_analysis.hold?.hold_until && (
                    <div className="text-xs">
                      <span className="text-text-secondary">持有至: </span>
                      <span className="font-semibold">
                        {result.position_analysis.hold.hold_until || '待定'}
                      </span>
                    </div>
                  )}
                  <p className="text-xs text-text-secondary leading-relaxed">
                    {result.position_analysis.hold?.reason || '暂无建议'}
                  </p>
                </div>
              </div>

              {/* Add Recommendation */}
              <div className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp
                    className={
                      result.position_analysis.add?.should_add
                        ? 'text-profit'
                        : 'text-gray-400'
                    }
                  />
                  <h4 className="text-sm font-semibold text-text-primary">加仓建议</h4>
                </div>
                <div className="space-y-2">
                  <div
                    className={`text-xs px-2 py-1 rounded font-medium inline-block ${
                      result.position_analysis.add?.should_add
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {result.position_analysis.add?.should_add
                      ? '建议加仓'
                      : '不建议加仓'}
                  </div>
                  {result.position_analysis.add?.suggested_price && (
                    <div className="text-sm">
                      <span className="text-text-secondary">建议价格: </span>
                      <span className="font-semibold">
                        ¥{result.position_analysis.add.suggested_price.toFixed(2)}
                      </span>
                    </div>
                  )}
                  {result.position_analysis.add?.suggested_quantity && (
                    <div className="text-sm">
                      <span className="text-text-secondary">建议数量: </span>
                      <span className="font-semibold">
                        {result.position_analysis.add.suggested_quantity} 股
                      </span>
                    </div>
                  )}
                  <p className="text-xs text-text-secondary leading-relaxed">
                    {result.position_analysis.add?.reason || '暂无建议'}
                  </p>
                </div>
              </div>
            </div>
          </Card>

          {/* Recovery Analysis - 仅当有该字段时显示 */}
          {result.position_analysis.recovery_analysis && (
            <Card title="回本分析" padding="md">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <Target size={14} />
                  <span>回本可能性</span>
                </div>
                <div
                  className={`text-xl font-bold ${
                    result.position_analysis.recovery_analysis?.can_recover
                      ? 'text-profit'
                      : 'text-loss'
                  }`}
                >
                  {result.position_analysis.recovery_analysis?.can_recover ? '可能回本' : '较难回本'}
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <Calendar size={14} />
                  <span>预计天数</span>
                </div>
                <div className="text-xl font-bold text-text-primary">
                  {result.position_analysis.recovery_analysis?.estimated_days
                    ? `${result.position_analysis.recovery_analysis.estimated_days} 天`
                    : '不确定'}
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                  <TrendingUp size={14} />
                  <span>回本概率</span>
                </div>
                <div className="text-xl font-bold text-text-primary">
                  {((result.position_analysis.recovery_analysis?.probability || 0) * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-100">
              <p className="text-sm text-text-primary">
                <span className="font-semibold">回本条件：</span>
                {result.position_analysis.recovery_analysis?.conditions || '需进一步分析'}
              </p>
            </div>
          </Card>
          )}

          {/* Risk Warnings */}
          {result.position_analysis.risk_warnings && result.position_analysis.risk_warnings.length > 0 && (
            <Card title="风险警告" padding="md">
              <div className="space-y-2">
                {result.position_analysis.risk_warnings.map((warning, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 p-3 bg-red-50 border border-red-100 rounded-lg"
                  >
                    <AlertTriangle size={18} className="text-red-500 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-800">{warning}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
