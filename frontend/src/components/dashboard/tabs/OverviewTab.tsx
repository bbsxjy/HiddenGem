import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { Table } from '@/components/common/Table';
import { getPortfolioSummary, getCurrentPositions, getPortfolioHistory } from '@/api/portfolio';
import { getQuote } from '@/api/market';
import { formatCurrency, formatPercentage, formatProfitLoss, getChangeColor } from '@/utils/format';
import { useSettingsStore } from '@/store/useSettingsStore';
import {
  TrendingUp,
  DollarSign,
  Activity,
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { Position } from '@/types/portfolio';

export function OverviewTab() {
  // Get refresh intervals from settings
  const { dataRefresh } = useSettingsStore();

  // Fetch portfolio summary
  const { data: summary, isLoading: summaryLoading, error: summaryError } = useQuery({
    queryKey: ['portfolio', 'summary'],
    queryFn: getPortfolioSummary,
    refetchInterval: dataRefresh.positionDataInterval * 1000,
  });

  // Fetch current positions
  const { data: positions, isLoading: positionsLoading, error: positionsError } = useQuery({
    queryKey: ['portfolio', 'positions'],
    queryFn: getCurrentPositions,
    refetchInterval: dataRefresh.positionDataInterval * 1000,
  });

  // Fetch portfolio history
  const { data: history, isLoading: historyLoading, error: historyError } = useQuery({
    queryKey: ['portfolio', 'history'],
    queryFn: () => getPortfolioHistory(30),
    refetchInterval: dataRefresh.positionDataInterval * 1000 * 2,
  });

  // Fetch market indices
  const { data: hs300, error: hs300Error } = useQuery({
    queryKey: ['market', 'quote', '000300.SH'],
    queryFn: () => getQuote('000300.SH'),
    refetchInterval: dataRefresh.marketDataInterval * 1000,
  });

  const { data: shIndex, error: shIndexError } = useQuery({
    queryKey: ['market', 'quote', '000001.SH'],
    queryFn: () => getQuote('000001.SH'),
    refetchInterval: dataRefresh.marketDataInterval * 1000,
  });

  const { data: szIndex, error: szIndexError } = useQuery({
    queryKey: ['market', 'quote', '399001.SZ'],
    queryFn: () => getQuote('399001.SZ'),
    refetchInterval: dataRefresh.marketDataInterval * 1000,
  });

  const { data: cybIndex, error: cybIndexError } = useQuery({
    queryKey: ['market', 'quote', '399006.SZ'],
    queryFn: () => getQuote('399006.SZ'),
    refetchInterval: dataRefresh.marketDataInterval * 1000,
  });

  // Log errors to console for debugging
  if (summaryError) console.error('Portfolio Summary Error:', summaryError);
  if (positionsError) console.error('Positions Error:', positionsError);
  if (historyError) console.error('History Error:', historyError);
  if (hs300Error) console.error('HS300 Error:', hs300Error);
  if (shIndexError) console.error('SH Index Error:', shIndexError);
  if (szIndexError) console.error('SZ Index Error:', szIndexError);
  if (cybIndexError) console.error('CYB Index Error:', cybIndexError);

  // Prepare chart data
  const chartData = history?.snapshots.map(snapshot => ({
    date: new Date(snapshot.timestamp).toLocaleDateString('zh-CN'),
    总价值: snapshot.total_value,
    盈亏: snapshot.total_pnl,
  })) || [];

  // Helper function to safely format timestamp
  const formatTimestamp = (timestamp: string | undefined) => {
    if (!timestamp) return '--:--:--';
    try {
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) return '--:--:--';
      return date.toLocaleTimeString('zh-CN');
    } catch {
      return '--:--:--';
    }
  };

  // Helper function to format index data
  const formatIndexChange = (changePercent: number | undefined) => {
    if (changePercent === undefined || changePercent === null) return '+0.00%';
    const sign = changePercent >= 0 ? '+' : '';
    return `${sign}${changePercent.toFixed(2)}%`;
  };

  const getIndexColor = (changePercent: number | undefined) => {
    if (changePercent === undefined || changePercent === null) return 'text-text-secondary';
    if (changePercent > 0) return 'text-profit';
    if (changePercent < 0) return 'text-loss';
    return 'text-text-secondary';
  };

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
    <div className="space-y-4">
      {/* Error Messages */}
      {(summaryError || positionsError || historyError || hs300Error || shIndexError || szIndexError || cybIndexError) && (
        <Card padding="md">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-red-800 mb-2">⚠️ 数据加载错误</h3>
            <div className="text-sm text-red-700 space-y-1">
              {summaryError && <p>• 投资组合概览: {(summaryError as any).message || '网络错误'}</p>}
              {positionsError && <p>• 持仓数据: {(positionsError as any).message || '网络错误'}</p>}
              {historyError && <p>• 历史数据: {(historyError as any).message || '网络错误'}</p>}
              {hs300Error && <p>• 沪深300: {(hs300Error as any).message || '网络错误'}</p>}
              {shIndexError && <p>• 上证指数: {(shIndexError as any).message || '网络错误'}</p>}
              {szIndexError && <p>• 深证成指: {(szIndexError as any).message || '网络错误'}</p>}
              {cybIndexError && <p>• 创业板指: {(cybIndexError as any).message || '网络错误'}</p>}
            </div>
            <p className="text-xs text-red-600 mt-3">
              请检查:
              1. 后端服务是否运行在 {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}
              2. 浏览器控制台查看详细错误
              3. 网络连接是否正常
            </p>
          </div>
        </Card>
      )}

      {/* 投资绩效卡片 - 改为2列布局 */}
      <div>
        <h2 className="text-base font-semibold text-text-primary mb-3">投资绩效</h2>
        {summaryLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loading size="md" text="加载数据..." />
          </div>
        ) : summary ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            <Card title="总资产" padding="sm">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-2xl font-bold text-text-primary">
                    {formatCurrency(summary.total_value)}
                  </div>
                  <div className="text-xs text-text-secondary mt-1">
                    现金: {formatCurrency(summary.cash)}
                  </div>
                </div>
                <DollarSign className="h-6 w-6 text-primary-500" />
              </div>
            </Card>

            <Card title="今日盈亏" padding="sm">
              <div className="flex items-start justify-between">
                <div>
                  <div className={`text-2xl font-bold ${formatProfitLoss(summary.daily_pnl).className}`}>
                    {formatCurrency(summary.daily_pnl)}
                  </div>
                  <div className="text-xs text-text-secondary mt-1">
                    {formatTimestamp(summary.timestamp)}
                  </div>
                </div>
                <Activity className="h-6 w-6 text-primary-500" />
              </div>
            </Card>

            <Card title="累计收益率" padding="sm">
              <div className="flex items-start justify-between">
                <div>
                  <div className={`text-2xl font-bold ${formatProfitLoss(summary.total_pnl_pct).className}`}>
                    {formatPercentage(summary.total_pnl_pct)}
                  </div>
                  <div className={`text-xs font-medium mt-1 ${formatProfitLoss(summary.total_pnl).className}`}>
                    {formatCurrency(summary.total_pnl)}
                  </div>
                </div>
                <TrendingUp className={`h-6 w-6 ${summary.total_pnl >= 0 ? 'text-profit' : 'text-loss'}`} />
              </div>
            </Card>

            <Card title="持仓数量" padding="sm">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-2xl font-bold text-text-primary">
                    {summary.num_positions}
                  </div>
                  <div className="text-xs text-text-secondary mt-1">
                    持仓市值: {formatCurrency(summary.positions_value)}
                  </div>
                </div>
                <Activity className="h-6 w-6 text-primary-500" />
              </div>
            </Card>
          </div>
        ) : (
          <div className="text-center py-8 text-text-secondary">
            暂无投资组合数据
          </div>
        )}
      </div>

      {/* 市场概览和资产走势并排 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 市场概览 */}
        <div className="lg:col-span-1">
          <h2 className="text-base font-semibold text-text-primary mb-3">市场概览</h2>
          <div className="grid grid-cols-1 gap-2">
            <Card title="沪深300" padding="sm">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-lg font-bold text-text-primary">
                    {hs300?.last_price?.toFixed(2) || 'N/A'}
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">实时数据</div>
                </div>
                <div className={`text-sm font-semibold ${getIndexColor(hs300?.change_percent)}`}>
                  {formatIndexChange(hs300?.change_percent)}
                </div>
              </div>
            </Card>

            <Card title="上证指数" padding="sm">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-lg font-bold text-text-primary">
                    {shIndex?.last_price?.toFixed(2) || 'N/A'}
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">实时数据</div>
                </div>
                <div className={`text-sm font-semibold ${getIndexColor(shIndex?.change_percent)}`}>
                  {formatIndexChange(shIndex?.change_percent)}
                </div>
              </div>
            </Card>

            <Card title="深证成指" padding="sm">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-lg font-bold text-text-primary">
                    {szIndex?.last_price?.toFixed(2) || 'N/A'}
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">实时数据</div>
                </div>
                <div className={`text-sm font-semibold ${getIndexColor(szIndex?.change_percent)}`}>
                  {formatIndexChange(szIndex?.change_percent)}
                </div>
              </div>
            </Card>

            <Card title="创业板指" padding="sm">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-lg font-bold text-text-primary">
                    {cybIndex?.last_price?.toFixed(2) || 'N/A'}
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">实时数据</div>
                </div>
                <div className={`text-sm font-semibold ${getIndexColor(cybIndex?.change_percent)}`}>
                  {formatIndexChange(cybIndex?.change_percent)}
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* 资产走势图 */}
        <div className="lg:col-span-2">
          <h2 className="text-base font-semibold text-text-primary mb-3">资产走势（30天）</h2>
          <Card padding="sm">
            {historyLoading ? (
              <div className="h-64 flex items-center justify-center">
                <Loading size="sm" text="加载历史数据..." />
              </div>
            ) : chartData.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="date"
                      stroke="#6b7280"
                      tick={{ fontSize: 10 }}
                    />
                    <YAxis
                      stroke="#6b7280"
                      tick={{ fontSize: 10 }}
                      domain={['auto', 'auto']}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        fontSize: '12px'
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
              <div className="h-64 flex items-center justify-center text-text-secondary">
                暂无历史数据
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Current Positions Table */}
      <div>
        <h2 className="text-base font-semibold text-text-primary mb-3">当前持仓</h2>
        <Card padding="sm">
          {positionsLoading ? (
            <div className="h-48 flex items-center justify-center">
              <Loading size="sm" text="加载持仓数据..." />
            </div>
          ) : positions && positions.length > 0 ? (
            <Table
              columns={positionColumns}
              data={positions}
            />
          ) : (
            <div className="h-48 flex items-center justify-center text-text-secondary">
              暂无持仓
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
