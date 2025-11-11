import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { getPortfolioSummary } from '@/api/portfolio';
import { getAgentsStatus } from '@/api/agents';
import { formatCurrency, formatPercentage, formatProfitLoss } from '@/utils/format';
import {
  TrendingUp,
  DollarSign,
  Activity,
  Brain,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function OverviewTab() {
  const navigate = useNavigate();

  // Fetch portfolio summary
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['portfolio', 'summary'],
    queryFn: getPortfolioSummary,
    refetchInterval: 30000,
  });

  // Fetch agents status
  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ['agents', 'status'],
    queryFn: getAgentsStatus,
    refetchInterval: 30000,
  });

  const enabledAgentsCount = agents?.filter(a => a.enabled).length || 0;
  const totalAgentsCount = agents?.length || 0;

  const agentNameMap: Record<string, string> = {
    technical: '技术分析',
    fundamental: '基本面分析',
    sentiment: '情绪分析',
    policy: '政策分析',
  };

  return (
    <div className="space-y-6">
      {/* 投资绩效卡片 */}
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-4">投资绩效</h2>
        {summaryLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loading size="md" text="加载数据..." />
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

            <Card title="累计收益率" padding="md">
              <div className="flex items-start justify-between">
                <div>
                  <div className={`text-3xl font-bold ${formatProfitLoss(summary.total_pnl_pct).className}`}>
                    {formatPercentage(summary.total_pnl_pct)}
                  </div>
                  <div className={`text-sm font-medium mt-1 ${formatProfitLoss(summary.total_pnl).className}`}>
                    {formatCurrency(summary.total_pnl)}
                  </div>
                </div>
                <TrendingUp className={`h-8 w-8 ${summary.total_pnl >= 0 ? 'text-profit' : 'text-loss'}`} />
              </div>
            </Card>

            <Card title="夏普比率" padding="md">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-3xl font-bold text-text-primary">
                    N/A
                  </div>
                  <div className="text-sm text-text-secondary mt-1">
                    待计算
                  </div>
                </div>
                <Activity className="h-8 w-8 text-primary-500" />
              </div>
            </Card>
          </div>
        ) : (
          <div className="text-center py-8 text-text-secondary">
            暂无投资组合数据
          </div>
        )}
      </div>

      {/* Agent健康状态 */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">Agent健康状态</h2>
          <button
            onClick={() => navigate('/agents')}
            className="text-sm text-primary-500 hover:text-primary-600 font-medium flex items-center gap-1"
          >
            查看详情
            <ArrowRight size={16} />
          </button>
        </div>

        {agentsLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loading size="md" text="加载Agent状态..." />
          </div>
        ) : agents && agents.length > 0 ? (
          <Card padding="md">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Brain className="h-6 w-6 text-primary-500" />
                  <span className="text-sm font-semibold text-text-primary">
                    运行状态: {enabledAgentsCount}/{totalAgentsCount} 在线
                  </span>
                </div>
                <div className="text-sm text-text-secondary">
                  最后更新: {new Date().toLocaleTimeString('zh-CN')}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {agents.map((agent) => (
                  <div
                    key={agent.agent_name}
                    className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg"
                  >
                    {agent.enabled ? (
                      <CheckCircle2 size={16} className="text-profit" />
                    ) : (
                      <AlertCircle size={16} className="text-gray-400" />
                    )}
                    <span className="text-sm text-text-primary">
                      {agentNameMap[agent.agent_name] || agent.agent_name}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        ) : (
          <Card padding="md">
            <div className="text-center py-8 text-text-secondary">
              暂无Agent数据
            </div>
          </Card>
        )}
      </div>

      {/* 市场概览 */}
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-4">市场概览</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card title="沪深300" padding="md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-text-primary">N/A</div>
                <div className="text-sm text-text-secondary mt-1">实时数据</div>
              </div>
              <div className="text-sm font-semibold text-text-secondary">+0.00%</div>
            </div>
          </Card>

          <Card title="上证指数" padding="md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-text-primary">N/A</div>
                <div className="text-sm text-text-secondary mt-1">实时数据</div>
              </div>
              <div className="text-sm font-semibold text-text-secondary">+0.00%</div>
            </div>
          </Card>

          <Card title="深证成指" padding="md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-text-primary">N/A</div>
                <div className="text-sm text-text-secondary mt-1">实时数据</div>
              </div>
              <div className="text-sm font-semibold text-text-secondary">+0.00%</div>
            </div>
          </Card>

          <Card title="创业板指" padding="md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-text-primary">N/A</div>
                <div className="text-sm text-text-secondary mt-1">实时数据</div>
              </div>
              <div className="text-sm font-semibold text-text-secondary">+0.00%</div>
            </div>
          </Card>
        </div>
      </div>

      {/* 今日交易信号 */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">今日交易信号 (Top 3)</h2>
          <button
            onClick={() => navigate('/analysis')}
            className="text-sm text-primary-500 hover:text-primary-600 font-medium flex items-center gap-1"
          >
            查看全部
            <ArrowRight size={16} />
          </button>
        </div>

        <Card padding="md">
          <div className="text-center py-12 text-text-secondary">
            暂无交易信号数据
            <br />
            <span className="text-sm">请前往智能分析页面生成信号</span>
          </div>
        </Card>
      </div>

      {/* 快捷操作 */}
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-4">快捷操作</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card padding="md" className="cursor-pointer hover:shadow-lg transition-shadow">
            <div onClick={() => navigate('/trading')} className="text-center py-4">
              <Activity className="h-8 w-8 text-primary-500 mx-auto mb-2" />
              <h3 className="text-sm font-semibold text-text-primary">快速下单</h3>
              <p className="text-xs text-text-secondary mt-1">手动交易面板</p>
            </div>
          </Card>

          <Card padding="md" className="cursor-pointer hover:shadow-lg transition-shadow">
            <div onClick={() => navigate('/portfolio')} className="text-center py-4">
              <DollarSign className="h-8 w-8 text-primary-500 mx-auto mb-2" />
              <h3 className="text-sm font-semibold text-text-primary">查看最新持仓</h3>
              <p className="text-xs text-text-secondary mt-1">投资组合详情</p>
            </div>
          </Card>

          <Card padding="md" className="cursor-pointer hover:shadow-lg transition-shadow">
            <div onClick={() => navigate('/live-monitor')} className="text-center py-4">
              <Brain className="h-8 w-8 text-primary-500 mx-auto mb-2" />
              <h3 className="text-sm font-semibold text-text-primary">启动自动交易</h3>
              <p className="text-xs text-text-secondary mt-1">实时监控面板</p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
