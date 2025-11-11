import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { Table } from '@/components/common/Table';
import { getPortfolioSummary, getCurrentPositions, getPortfolioHistory } from '@/api/portfolio';
import { formatCurrency, formatProfitLoss, formatPercentage, getChangeColor } from '@/utils/format';
import { TrendingUp, DollarSign, PieChart, Activity } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { Position } from '@/types/portfolio';

export function PortfolioTab() {
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

  // Fetch portfolio history
  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['portfolio', 'history'],
    queryFn: () => getPortfolioHistory(30),
    refetchInterval: 60000,
  });

  // Prepare chart data
  const chartData = history?.snapshots.map(snapshot => ({
    date: new Date(snapshot.timestamp).toLocaleDateString('zh-CN'),
    总价值: snapshot.total_value,
    盈亏: snapshot.total_pnl,
  })) || [];

  // Prepare positions table data
  const positionColumns = [
    {
      header: '股票代码',
      accessor: 'symbol' as const,
      cell: (value: string) => (
        <span className="font-semibold text-text-primary">{value}</span>
      ),
    },
    {
      header: '数量',
      accessor: 'quantity' as const,
      cell: (value: number) => value.toLocaleString(),
    },
    {
      header: '成本价',
      accessor: 'avg_cost' as const,
      cell: (value: number) => `¥${value.toFixed(2)}`,
    },
    {
      header: '当前价',
      accessor: 'current_price' as const,
      cell: (value: number) => `¥${value.toFixed(2)}`,
    },
    {
      header: '市值',
      accessor: 'market_value' as const,
      cell: (value: number) => formatCurrency(value),
    },
    {
      header: '盈亏',
      accessor: 'unrealized_pnl' as const,
      cell: (value: number, row: Position) => (
        <span className={getChangeColor(value, row.symbol)}>
          {formatCurrency(value)}
        </span>
      ),
    },
    {
      header: '收益率',
      accessor: 'unrealized_pnl_pct' as const,
      cell: (value: number, row: Position) => (
        <span className={getChangeColor(value, row.symbol)}>
          {formatPercentage(value)}
        </span>
      ),
    },
    {
      header: '策略',
      accessor: 'strategy_name' as const,
      cell: (value?: string) => (
        <span className="text-sm text-text-secondary">{value || 'N/A'}</span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Portfolio Summary Cards */}
      {summaryLoading ? (
        <div className="flex items-center justify-center h-32">
          <Loading size="md" text="加载组合数据..." />
        </div>
      ) : summary ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card title="总资产" padding="md">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-3xl font-bold text-text-primary">
                  {formatCurrency(summary.total_value)}
                </div>
                <div className="text-sm text-text-secondary mt-1">
                  现金: {formatCurrency(summary.cash)}
                </div>
              </div>
              <DollarSign className="h-8 w-8 text-primary-500" />
            </div>
          </Card>

          <Card title="持仓市值" padding="md">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-3xl font-bold text-text-primary">
                  {formatCurrency(summary.positions_value)}
                </div>
                <div className="text-sm text-text-secondary mt-1">
                  {summary.num_positions} 个持仓
                </div>
              </div>
              <PieChart className="h-8 w-8 text-primary-500" />
            </div>
          </Card>

          <Card title="总盈亏" padding="md">
            <div className="flex items-start justify-between">
              <div>
                <div className={`text-3xl font-bold ${formatProfitLoss(summary.total_pnl).className}`}>
                  {formatCurrency(summary.total_pnl)}
                </div>
                <div className={`text-sm font-semibold mt-1 ${formatProfitLoss(summary.total_pnl_pct).className}`}>
                  {formatPercentage(summary.total_pnl_pct)}
                </div>
              </div>
              <TrendingUp className={`h-8 w-8 ${summary.total_pnl >= 0 ? 'text-profit' : 'text-loss'}`} />
            </div>
          </Card>

          <Card title="今日盈亏" padding="md">
            <div className="flex items-start justify-between">
              <div>
                <div className={`text-3xl font-bold ${formatProfitLoss(summary.daily_pnl).className}`}>
                  {formatCurrency(summary.daily_pnl)}
                </div>
                <div className="text-sm text-text-secondary mt-1">
                  {new Date(summary.timestamp).toLocaleTimeString('zh-CN')}
                </div>
              </div>
              <Activity className="h-8 w-8 text-primary-500" />
            </div>
          </Card>
        </div>
      ) : null}

      {/* Portfolio History Chart */}
      <Card title="资产走势（30天）" padding="md">
        {historyLoading ? (
          <div className="h-80 flex items-center justify-center">
            <Loading size="sm" text="加载历史数据..." />
          </div>
        ) : chartData.length > 0 ? (
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  stroke="#6b7280"
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  stroke="#6b7280"
                  tick={{ fontSize: 12 }}
                  domain={['auto', 'auto']}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px'
                  }}
                  formatter={(value: number) => formatCurrency(value)}
                />
                <Line
                  type="monotone"
                  dataKey="总价值"
                  stroke="#0ea5e9"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-80 flex items-center justify-center text-text-secondary">
            暂无历史数据
          </div>
        )}
      </Card>

      {/* Current Positions Table */}
      <Card title="当前持仓" padding="md">
        {positionsLoading ? (
          <div className="h-64 flex items-center justify-center">
            <Loading size="sm" text="加载持仓数据..." />
          </div>
        ) : positions && positions.length > 0 ? (
          <Table
            columns={positionColumns}
            data={positions}
          />
        ) : (
          <div className="h-64 flex items-center justify-center text-text-secondary">
            暂无持仓
          </div>
        )}
      </Card>

      {/* 组合分析图表 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="行业分布" padding="md">
          <div className="h-64 flex items-center justify-center text-text-secondary">
            行业分布饼图（待实现）
          </div>
        </Card>

        <Card title="板块分布" padding="md">
          <div className="h-64 flex items-center justify-center text-text-secondary">
            板块分布图（主板、创业板、科创板）
          </div>
        </Card>
      </div>

      {/* 风险指标 */}
      <Card title="风险指标" padding="md">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-text-secondary mb-1">最大回撤</p>
            <p className="text-2xl font-bold text-text-primary">N/A</p>
          </div>
          <div>
            <p className="text-sm text-text-secondary mb-1">波动率</p>
            <p className="text-2xl font-bold text-text-primary">N/A</p>
          </div>
          <div>
            <p className="text-sm text-text-secondary mb-1">Beta值</p>
            <p className="text-2xl font-bold text-text-primary">N/A</p>
          </div>
          <div>
            <p className="text-sm text-text-secondary mb-1">集中度风险</p>
            <p className="text-2xl font-bold text-text-primary">N/A</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
