import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { getPortfolioSummary } from '@/api/portfolio';
import { getCurrentSignals, getOrders } from '@/api/orders';
import { getAgentsStatus } from '@/api/agents';
import { formatCurrency, formatProfitLoss } from '@/utils/format';
import { Activity, TrendingUp, ShoppingCart, Zap } from 'lucide-react';

export function Dashboard() {
  // Fetch portfolio summary
  const { data: portfolio, isLoading: portfolioLoading, error: portfolioError } = useQuery({
    queryKey: ['portfolio', 'summary'],
    queryFn: getPortfolioSummary,
    refetchInterval: 5000, // Refetch every 5 seconds
  });

  // Fetch current trading signals
  const { data: signals, isLoading: signalsLoading } = useQuery({
    queryKey: ['signals', 'current'],
    queryFn: () => getCurrentSignals(10),
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  // Fetch agents status
  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ['agents', 'status'],
    queryFn: getAgentsStatus,
    refetchInterval: 15000, // Refetch every 15 seconds
  });

  // Fetch active orders (pending + submitted)
  const { data: activeOrders } = useQuery({
    queryKey: ['orders', 'active'],
    queryFn: () => getOrders({ status: 'pending,submitted' }),
    refetchInterval: 5000, // Refetch every 5 seconds
  });

  // Show loading state
  if (portfolioLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loading size="lg" text="加载仪表盘数据..." />
      </div>
    );
  }

  // Show error state
  if (portfolioError) {
    return (
      <div className="flex items-center justify-center h-96">
        <Card className="max-w-md">
          <div className="text-center p-6">
            <Activity className="mx-auto h-12 w-12 text-loss mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              无法连接到后端服务
            </h3>
            <p className="text-text-secondary text-sm mb-4">
              {portfolioError instanceof Error
                ? portfolioError.message
                : '请确保后端服务正在运行在 http://localhost:8000'}
            </p>
            <div className="text-xs text-text-secondary bg-gray-100 p-3 rounded">
              <p className="font-mono">后端地址: {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}</p>
              <p className="mt-2">检查项:</p>
              <ul className="list-disc list-inside text-left mt-1">
                <li>后端服务是否已启动</li>
                <li>CORS是否正确配置</li>
                <li>网络连接是否正常</li>
              </ul>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  const activeOrdersCount = activeOrders?.length || 0;
  const enabledAgentsCount = agents?.filter(a => a.enabled).length || 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">仪表盘</h1>
        <p className="text-text-secondary mt-1">实时监控您的交易系统</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card title="投资组合价值" padding="md">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-3xl font-bold text-text-primary">
                {portfolio ? formatCurrency(portfolio.total_value) : '¥0.00'}
              </div>
              <div className="text-sm text-text-secondary mt-1">
                今日盈亏: {' '}
                <span className={formatProfitLoss(portfolio?.daily_pnl || 0).className}>
                  {portfolio ? formatCurrency(portfolio.daily_pnl) : '+¥0.00'}
                </span>
              </div>
            </div>
            <TrendingUp className="h-8 w-8 text-primary-500" />
          </div>
        </Card>

        <Card title="持仓数量" padding="md">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-3xl font-bold text-text-primary">
                {portfolio?.num_positions || 0}
              </div>
              <div className="text-sm text-text-secondary mt-1">
                持仓市值: {portfolio ? formatCurrency(portfolio.positions_value) : '¥0.00'}
              </div>
            </div>
            <ShoppingCart className="h-8 w-8 text-primary-500" />
          </div>
        </Card>

        <Card title="活跃订单" padding="md">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-3xl font-bold text-text-primary">
                {activeOrdersCount}
              </div>
              <div className="text-sm text-text-secondary mt-1">待执行订单</div>
            </div>
            <Activity className="h-8 w-8 text-primary-500" />
          </div>
        </Card>

        <Card title="交易信号" padding="md">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-3xl font-bold text-text-primary">
                {signals?.length || 0}
              </div>
              <div className="text-sm text-text-secondary mt-1">
                活跃Agent: {enabledAgentsCount}
              </div>
            </div>
            <Zap className="h-8 w-8 text-primary-500" />
          </div>
        </Card>
      </div>

      {/* Portfolio Performance & Recent Signals */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="投资组合表现" padding="md">
          {portfolio ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center py-2 border-b border-gray-200">
                <span className="text-text-secondary">总资产</span>
                <span className="font-semibold text-text-primary">
                  {formatCurrency(portfolio.total_value)}
                </span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-gray-200">
                <span className="text-text-secondary">现金</span>
                <span className="font-semibold text-text-primary">
                  {formatCurrency(portfolio.cash)}
                </span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-gray-200">
                <span className="text-text-secondary">总盈亏</span>
                <span className={`font-semibold ${formatProfitLoss(portfolio.total_pnl).className}`}>
                  {formatCurrency(portfolio.total_pnl)} ({(portfolio.total_pnl_pct * 100).toFixed(2)}%)
                </span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-text-secondary">更新时间</span>
                <span className="text-sm text-text-secondary">
                  {new Date(portfolio.timestamp).toLocaleString('zh-CN')}
                </span>
              </div>
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-text-secondary">
              暂无数据
            </div>
          )}
        </Card>

        <Card title="最近交易信号" padding="md">
          {signalsLoading ? (
            <div className="h-64 flex items-center justify-center">
              <Loading size="sm" text="加载信号..." />
            </div>
          ) : signals && signals.length > 0 ? (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {signals.slice(0, 5).map((signal) => (
                <div
                  key={signal.id}
                  className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-text-primary">
                        {signal.symbol}
                      </span>
                      <span
                        className={`text-xs px-2 py-1 rounded ${
                          signal.direction === 'buy'
                            ? 'bg-profit-light text-profit'
                            : signal.direction === 'sell'
                            ? 'bg-loss-light text-loss'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {signal.direction === 'buy' ? '买入' :
                         signal.direction === 'sell' ? '卖出' : '持有'}
                      </span>
                    </div>
                    <div className="text-xs text-text-secondary mt-1">
                      {signal.agent_name} · 强度: {(signal.strength * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-text-primary">
                      ¥{signal.entry_price.toFixed(2)}
                    </div>
                    <div className="text-xs text-text-secondary">
                      {new Date(signal.timestamp).toLocaleTimeString('zh-CN')}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-64 flex items-center justify-center text-text-secondary">
              暂无交易信号
            </div>
          )}
        </Card>
      </div>

      {/* Agents Status */}
      <Card title="Agent 状态" padding="md">
        {agentsLoading ? (
          <div className="h-32 flex items-center justify-center">
            <Loading size="sm" text="加载Agent状态..." />
          </div>
        ) : agents && agents.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            {agents.map((agent) => (
              <div
                key={agent.name}
                className="text-center p-3 border border-gray-200 rounded-lg"
              >
                <div
                  className={`w-3 h-3 rounded-full mx-auto mb-2 ${
                    agent.enabled ? 'bg-profit animate-pulse' : 'bg-gray-300'
                  }`}
                />
                <div className="text-sm font-medium text-text-primary capitalize">
                  {agent.name}
                </div>
                <div className="text-xs text-text-secondary mt-1">
                  {agent.enabled ? '运行中' : '已停用'}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="h-32 flex items-center justify-center text-text-secondary">
            暂无Agent数据
          </div>
        )}
      </Card>
    </div>
  );
}
