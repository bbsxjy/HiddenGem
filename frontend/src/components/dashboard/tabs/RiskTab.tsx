import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { getPortfolioSummary, getCurrentPositions } from '@/api/portfolio';
import { formatCurrency, formatPercentage } from '@/utils/format';
import { Shield, AlertTriangle, TrendingDown, PieChart } from 'lucide-react';

export function RiskTab() {
  // Fetch portfolio summary
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['portfolio', 'summary'],
    queryFn: getPortfolioSummary,
    refetchInterval: 30000,
  });

  // Fetch current positions
  const { data: positions, isLoading: positionsLoading } = useQuery({
    queryKey: ['portfolio', 'positions'],
    queryFn: getCurrentPositions,
    refetchInterval: 30000,
  });

  // Calculate position concentration (top position percentage)
  const topPositionPct = positions && positions.length > 0
    ? Math.max(...positions.map(p => (p.market_value / (summary?.positions_value || 1)) * 100))
    : 0;

  return (
    <div className="space-y-6">
      {/* Risk Overview Cards */}
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-4">风险概览</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card title="持仓数量" padding="md">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-3xl font-bold text-text-primary">
                  {summary?.num_positions || 0}
                </div>
                <div className="text-sm text-text-secondary mt-1">
                  当前持仓股票数
                </div>
              </div>
              <Shield className="h-8 w-8 text-primary-500" />
            </div>
          </Card>

          <Card title="最大单一持仓" padding="md">
            <div className="flex items-start justify-between">
              <div>
                <div className={`text-3xl font-bold ${topPositionPct > 10 ? 'text-risk-high' : 'text-text-primary'}`}>
                  {topPositionPct.toFixed(1)}%
                </div>
                <div className="text-sm text-text-secondary mt-1">
                  {topPositionPct > 10 ? '超过风险阈值' : '风险可控'}
                </div>
              </div>
              <AlertTriangle className={`h-8 w-8 ${topPositionPct > 10 ? 'text-risk-high' : 'text-primary-500'}`} />
            </div>
          </Card>

          <Card title="最大回撤" padding="md">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-3xl font-bold text-text-primary">
                  N/A
                </div>
                <div className="text-sm text-text-secondary mt-1">
                  待计算
                </div>
              </div>
              <TrendingDown className="h-8 w-8 text-primary-500" />
            </div>
          </Card>

          <Card title="波动率" padding="md">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-3xl font-bold text-text-primary">
                  N/A
                </div>
                <div className="text-sm text-text-secondary mt-1">
                  年化波动率
                </div>
              </div>
              <PieChart className="h-8 w-8 text-primary-500" />
            </div>
          </Card>
        </div>
      </div>

      {/* 风险指标详情 */}
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-4">风险指标</h2>
        <Card padding="md">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-text-secondary mb-1">最大回撤</p>
              <p className="text-2xl font-bold text-text-primary">N/A</p>
              <p className="text-xs text-text-secondary mt-1">历史最大回撤幅度</p>
            </div>
            <div>
              <p className="text-sm text-text-secondary mb-1">波动率</p>
              <p className="text-2xl font-bold text-text-primary">N/A</p>
              <p className="text-xs text-text-secondary mt-1">年化收益波动率</p>
            </div>
            <div>
              <p className="text-sm text-text-secondary mb-1">Beta值</p>
              <p className="text-2xl font-bold text-text-primary">N/A</p>
              <p className="text-xs text-text-secondary mt-1">相对市场的系统风险</p>
            </div>
            <div>
              <p className="text-sm text-text-secondary mb-1">集中度风险</p>
              <p className="text-2xl font-bold text-text-primary">
                {topPositionPct > 0 ? `${topPositionPct.toFixed(1)}%` : 'N/A'}
              </p>
              <p className="text-xs text-text-secondary mt-1">最大单一持仓占比</p>
            </div>
          </div>
        </Card>
      </div>

      {/* 组合分析图表 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-4">行业分布</h2>
          <Card padding="md">
            <div className="h-64 flex items-center justify-center text-text-secondary">
              行业分布饼图（待实现）
            </div>
          </Card>
        </div>

        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-4">板块分布</h2>
          <Card padding="md">
            <div className="h-64 flex items-center justify-center text-text-secondary">
              板块分布图（主板、创业板、科创板）
            </div>
          </Card>
        </div>
      </div>

      {/* A股特有风险指标 */}
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-4">A股特有风险</h2>
        <Card padding="md">
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle size={18} className="text-risk-medium" />
                  <h3 className="font-semibold text-text-primary">股权质押风险</h3>
                </div>
                <p className="text-sm text-text-secondary mb-2">
                  监控持仓股票的股权质押比例
                </p>
                <p className="text-xs text-text-secondary">
                  高风险阈值: &gt;50%
                </p>
                <div className="mt-3 text-center py-4 text-text-secondary">
                  待实现
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle size={18} className="text-risk-medium" />
                  <h3 className="font-semibold text-text-primary">限售股解禁</h3>
                </div>
                <p className="text-sm text-text-secondary mb-2">
                  监控未来限售股解禁计划
                </p>
                <p className="text-xs text-text-secondary">
                  关注解禁量占比
                </p>
                <div className="mt-3 text-center py-4 text-text-secondary">
                  待实现
                </div>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle size={18} className="text-risk-medium" />
                  <h3 className="font-semibold text-text-primary">商誉减值风险</h3>
                </div>
                <p className="text-sm text-text-secondary mb-2">
                  监控商誉占总资产比例
                </p>
                <p className="text-xs text-text-secondary">
                  高风险阈值: &gt;30%
                </p>
                <div className="mt-3 text-center py-4 text-text-secondary">
                  待实现
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* 风险提示 */}
      <Card padding="md">
        <div className="flex items-start gap-3">
          <Shield className="h-5 w-5 text-primary-500 mt-0.5" />
          <div>
            <h3 className="font-semibold text-text-primary mb-2">风险管理规则</h3>
            <ul className="text-sm text-text-secondary space-y-1">
              <li>• 最大单一持仓: 不超过投资组合的 10%</li>
              <li>• 最大行业敞口: 不超过投资组合的 30%</li>
              <li>• 默认止损比例: 8%</li>
              <li>• 默认止盈比例: 15%</li>
              <li>• 新建仓位前需检查相关性限制</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
