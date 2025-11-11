import { OverviewTab } from '@/components/dashboard/tabs/OverviewTab';

export function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">仪表盘</h1>
        <p className="text-text-secondary mt-1">TradingAgents-CN 智能分析系统</p>
      </div>

      {/* Overview Content */}
      <OverviewTab />
    </div>
  );
}
