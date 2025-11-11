import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { Table } from '@/components/common/Table';
import { getStrategies } from '@/api/strategies';
import { Activity, PlayCircle, PauseCircle } from 'lucide-react';

export function StrategyTab() {
  // Fetch strategies list
  const { data: strategies, isLoading: strategiesLoading } = useQuery({
    queryKey: ['strategies'],
    queryFn: getStrategies,
    refetchInterval: 30000,
  });

  const strategyTypeMap: Record<string, string> = {
    swing_trading: '波段交易',
    trend_following: '趋势跟踪',
  };

  const strategyColumns = [
    {
      header: '策略名称',
      accessor: 'name' as const,
      cell: (value: string) => (
        <span className="font-semibold text-text-primary">{value}</span>
      ),
    },
    {
      header: '类型',
      accessor: 'strategy_type' as const,
      cell: (value: string) => strategyTypeMap[value] || value,
    },
    {
      header: '状态',
      accessor: 'enabled' as const,
      cell: (value: boolean) => (
        <span className={`flex items-center gap-2 ${value ? 'text-profit' : 'text-gray-500'}`}>
          {value ? <PlayCircle size={16} /> : <PauseCircle size={16} />}
          {value ? '已启用' : '已停用'}
        </span>
      ),
    },
    {
      header: '持仓数',
      accessor: 'num_positions' as const,
      cell: (value: number) => value || 0,
    },
    {
      header: '创建时间',
      accessor: 'created_at' as const,
      cell: (value: string) => new Date(value).toLocaleDateString('zh-CN'),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Strategy Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card title="总策略数" padding="md">
          <div className="flex items-start justify-between">
            <div className="text-3xl font-bold text-text-primary">
              {strategies?.length || 0}
            </div>
            <Activity className="h-8 w-8 text-primary-500" />
          </div>
        </Card>

        <Card title="运行中" padding="md">
          <div className="flex items-start justify-between">
            <div className="text-3xl font-bold text-profit">
              {strategies?.filter(s => s.enabled).length || 0}
            </div>
            <PlayCircle className="h-8 w-8 text-profit" />
          </div>
        </Card>

        <Card title="已停用" padding="md">
          <div className="flex items-start justify-between">
            <div className="text-3xl font-bold text-gray-500">
              {strategies?.filter(s => !s.enabled).length || 0}
            </div>
            <PauseCircle className="h-8 w-8 text-gray-500" />
          </div>
        </Card>
      </div>

      {/* Strategies List */}
      <Card title="策略列表" padding="md">
        {strategiesLoading ? (
          <div className="h-96 flex items-center justify-center">
            <Loading size="md" text="加载策略列表..." />
          </div>
        ) : strategies && strategies.length > 0 ? (
          <Table columns={strategyColumns} data={strategies} />
        ) : (
          <div className="h-96 flex items-center justify-center">
            <div className="text-center">
              <Activity className="mx-auto h-12 w-12 text-gray-300 mb-4" />
              <p className="text-text-secondary">暂无策略</p>
              <p className="text-sm text-text-secondary mt-2">
                您可以通过后端API创建新的交易策略
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* Strategy Info */}
      <Card title="策略说明" padding="md">
        <div className="space-y-4">
          <div>
            <h3 className="font-semibold text-text-primary mb-2">波段交易（Swing Trading）</h3>
            <p className="text-sm text-text-secondary">
              利用市场短期波动进行交易，持仓周期通常在几天到几周之间。
              适合捕捉中短期趋势，注重风险收益比和资金管理。
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-text-primary mb-2">趋势跟踪（Trend Following）</h3>
            <p className="text-sm text-text-secondary">
              识别并跟随市场主要趋势方向，持仓周期较长。
              通过技术指标确认趋势，在趋势确立后建仓，趋势反转时离场。
            </p>
          </div>

          <div className="p-4 bg-blue-50 rounded-lg">
            <h4 className="font-semibold text-blue-900 mb-2">注意事项</h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-blue-800">
              <li>策略运行需要确保后端服务正常</li>
              <li>建议先使用模拟交易测试策略</li>
              <li>定期检查策略表现并优化参数</li>
              <li>注意风控参数设置，避免过度亏损</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
