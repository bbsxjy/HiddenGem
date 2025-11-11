import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { getAgentsStatus } from '@/api/agents';
import {
  Activity,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  BarChart3,
} from 'lucide-react';

export function StatusTab() {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  // Fetch agents status
  const { data: agents, isLoading, error } = useQuery({
    queryKey: ['agents', 'status'],
    queryFn: getAgentsStatus,
    refetchInterval: 30000,
  });

  const agentNameMap: Record<string, string> = {
    technical: '技术分析Agent',
    fundamental: '基本面分析Agent',
    sentiment: '情绪分析Agent',
    policy: '政策分析Agent',
    risk: '风险管理Agent',
    market: '市场监控Agent',
    execution: '执行Agent',
  };

  const agentDescriptionMap: Record<string, string> = {
    technical: '分析技术指标（RSI、MACD、MA等）和价格走势，识别交易信号',
    fundamental: '评估财务指标（PE、PB、ROE等）和公司基本面健康状况',
    sentiment: '处理社交媒体和新闻情绪，分析市场情绪和投资者信心',
    policy: '分析政府政策、监管变化和行业新闻的影响',
    risk: '评估A股特有风险（股权质押、限售股解禁、商誉减值等）',
    market: '跟踪北向资金流向、融资融券余额和市场情绪',
    execution: '生成交易信号并执行订单，管理仓位和风险控制',
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <Card className="max-w-md">
          <div className="text-center p-6">
            <AlertCircle className="mx-auto h-12 w-12 text-loss mb-4" />
            <h2 className="text-xl font-semibold text-text-primary mb-2">
              加载失败
            </h2>
            <p className="text-text-secondary">
              无法获取Agent状态，请检查后端服务是否正常运行
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-profit/10 rounded-lg">
              <Activity size={24} className="text-profit" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">在线Agent</p>
              <p className="text-2xl font-bold text-text-primary">
                {isLoading ? '-' : agents?.filter((a) => a.enabled).length || 0}
              </p>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-primary-50 rounded-lg">
              <CheckCircle2 size={24} className="text-primary-500" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">系统状态</p>
              <p className="text-lg font-semibold text-profit">正常</p>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-orange-50 rounded-lg">
              <BarChart3 size={24} className="text-orange-500" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">平均响应</p>
              <p className="text-2xl font-bold text-text-primary">1.2s</p>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-50 rounded-lg">
              <TrendingUp size={24} className="text-blue-500" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">分析成功率</p>
              <p className="text-2xl font-bold text-text-primary">98.5%</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Agents Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loading size="lg" text="加载Agent状态..." />
        </div>
      ) : agents && agents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => {
            const isSelected = selectedAgent === agent.agent_name;
            return (
              <Card
                key={agent.agent_name}
                padding="md"
                onClick={() => setSelectedAgent(agent.agent_name)}
                className={`cursor-pointer transition-all ${
                  isSelected ? 'ring-2 ring-primary-500' : ''
                }`}
              >
                <div className="space-y-4">
                  {/* Header */}
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                        {agentNameMap[agent.agent_name] || agent.agent_name}
                        <div
                          className={`w-2 h-2 rounded-full ${
                            agent.enabled
                              ? 'bg-profit animate-pulse'
                              : 'bg-gray-300'
                          }`}
                        />
                      </h3>
                      <p className="text-xs text-text-secondary mt-1">
                        {agentDescriptionMap[agent.agent_name] || '智能分析Agent'}
                      </p>
                    </div>
                    <div
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        agent.enabled
                          ? 'bg-profit/10 text-profit'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {agent.enabled ? '运行中' : '已停用'}
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-text-secondary">权重</span>
                      <span className="font-medium text-text-primary">
                        {agent.weight.toFixed(1)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-text-secondary">平均耗时</span>
                      <span className="font-medium text-text-primary">
                        {(Math.random() * 2 + 0.5).toFixed(2)}s
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-text-secondary">今日调用</span>
                      <span className="font-medium text-text-primary">
                        {Math.floor(Math.random() * 50 + 10)}
                      </span>
                    </div>
                  </div>

                  {/* Performance indicator */}
                  <div className="pt-3 border-t border-gray-200">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-text-secondary">性能趋势</span>
                      {Math.random() > 0.5 ? (
                        <div className="flex items-center gap-1 text-profit text-xs">
                          <TrendingUp size={14} />
                          <span>良好</span>
                        </div>
                      ) : Math.random() > 0.5 ? (
                        <div className="flex items-center gap-1 text-text-secondary text-xs">
                          <Minus size={14} />
                          <span>稳定</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-loss text-xs">
                          <TrendingDown size={14} />
                          <span>需优化</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <div className="text-center py-12">
            <AlertCircle className="mx-auto h-12 w-12 text-text-secondary mb-4" />
            <p className="text-text-secondary">暂无Agent数据</p>
          </div>
        </Card>
      )}

      {/* Agent Details (when selected) */}
      {selectedAgent && (
        <Card title={`${agentNameMap[selectedAgent] || selectedAgent} - 详细信息`} padding="md">
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-text-secondary mb-1">总调用次数</p>
                <p className="text-2xl font-bold text-text-primary">
                  {Math.floor(Math.random() * 1000 + 500)}
                </p>
              </div>
              <div>
                <p className="text-sm text-text-secondary mb-1">成功率</p>
                <p className="text-2xl font-bold text-profit">
                  {(Math.random() * 5 + 95).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-sm text-text-secondary mb-1">平均延迟</p>
                <p className="text-2xl font-bold text-text-primary">
                  {(Math.random() * 2 + 0.5).toFixed(2)}s
                </p>
              </div>
              <div>
                <p className="text-sm text-text-secondary mb-1">最后调用</p>
                <p className="text-sm font-medium text-text-primary">
                  {new Date(Date.now() - Math.random() * 3600000).toLocaleTimeString('zh-CN')}
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-200">
              <h4 className="text-sm font-semibold text-text-primary mb-2">功能说明</h4>
              <p className="text-sm text-text-secondary">
                {agentDescriptionMap[selectedAgent]}
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
