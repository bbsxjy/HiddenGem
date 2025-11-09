import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { Input } from '@/components/common/Input';
import { checkHealth } from '@/api/health';
import { getAgentsStatus } from '@/api/agents';
import {
  Activity,
  Search,
  CheckCircle2,
  AlertCircle,
  Server,
  Cpu,
  ArrowRight,
} from 'lucide-react';

export function Dashboard() {
  const navigate = useNavigate();
  const [quickAnalysisInput, setQuickAnalysisInput] = useState('');

  // Fetch system health
  const { data: health, isLoading: healthLoading, error: healthError } = useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch agents status
  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ['agents', 'status'],
    queryFn: getAgentsStatus,
    refetchInterval: 15000, // Refetch every 15 seconds
  });

  const handleQuickAnalysis = (e: React.FormEvent) => {
    e.preventDefault();
    if (quickAnalysisInput.trim()) {
      navigate('/analysis', { state: { symbol: quickAnalysisInput.trim() } });
    }
  };

  const enabledAgentsCount = agents?.filter(a => a.enabled).length || 0;
  const totalAgentsCount = agents?.length || 0;

  const agentNameMap: Record<string, string> = {
    technical: '技术分析',
    fundamental: '基本面分析',
    sentiment: '情绪分析',
    policy: '政策分析',
  };

  // Show error state for critical failure
  if (healthError) {
    return (
      <div className="flex items-center justify-center h-96">
        <Card className="max-w-md">
          <div className="text-center p-6">
            <AlertCircle className="mx-auto h-12 w-12 text-loss mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              无法连接到后端服务
            </h3>
            <p className="text-text-secondary text-sm mb-4">
              {healthError instanceof Error
                ? healthError.message
                : '请确保后端服务正在运行'}
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">仪表盘</h1>
        <p className="text-text-secondary mt-1">TradingAgents-CN 智能分析系统</p>
      </div>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* System Health */}
        <Card title="系统状态" padding="md">
          {healthLoading ? (
            <div className="h-24 flex items-center justify-center">
              <Loading size="sm" text="检查中..." />
            </div>
          ) : health ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-text-secondary text-sm">服务状态</span>
                <div className="flex items-center gap-2">
                  {health.status === 'healthy' ? (
                    <>
                      <CheckCircle2 size={16} className="text-profit" />
                      <span className="text-sm font-semibold text-profit">正常</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle size={16} className="text-loss" />
                      <span className="text-sm font-semibold text-loss">异常</span>
                    </>
                  )}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-secondary text-sm">TradingGraph</span>
                <div className="flex items-center gap-2">
                  {health.trading_graph_initialized ? (
                    <>
                      <CheckCircle2 size={16} className="text-profit" />
                      <span className="text-sm font-semibold text-profit">已初始化</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle size={16} className="text-loss" />
                      <span className="text-sm font-semibold text-loss">未初始化</span>
                    </>
                  )}
                </div>
              </div>
              <div className="pt-2 border-t border-gray-200">
                <div className="flex items-center gap-2 text-xs text-text-secondary">
                  <Server size={12} />
                  <span>{health.service}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-24 flex items-center justify-center text-text-secondary text-sm">
              暂无数据
            </div>
          )}
        </Card>

        {/* Agents Status */}
        <Card title="Agent 状态" padding="md">
          {agentsLoading ? (
            <div className="h-24 flex items-center justify-center">
              <Loading size="sm" text="加载中..." />
            </div>
          ) : agents && agents.length > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-text-secondary text-sm">运行状态</span>
                <div className="flex items-center gap-2">
                  <Activity size={16} className="text-primary-500" />
                  <span className="text-sm font-semibold text-text-primary">
                    {enabledAgentsCount}/{totalAgentsCount} 在线
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {agents.map((agent) => (
                  <div
                    key={agent.agent_name}
                    className="flex items-center gap-2 p-2 bg-gray-50 rounded"
                  >
                    <div
                      className={`w-2 h-2 rounded-full ${
                        agent.enabled ? 'bg-profit animate-pulse' : 'bg-gray-300'
                      }`}
                    />
                    <span className="text-xs text-text-primary">
                      {agentNameMap[agent.agent_name] || agent.agent_name}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-24 flex items-center justify-center text-text-secondary text-sm">
              暂无 Agent 数据
            </div>
          )}
        </Card>

        {/* System Info */}
        <Card title="系统信息" padding="md">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-text-secondary text-sm">版本</span>
              <span className="text-sm font-semibold text-text-primary">v0.1.0</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-text-secondary text-sm">后端地址</span>
              <span className="text-xs font-mono text-text-secondary">
                {import.meta.env.VITE_API_BASE_URL || 'localhost:8000'}
              </span>
            </div>
            <div className="pt-2 border-t border-gray-200">
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                <Cpu size={12} />
                <span>TradingAgents-CN</span>
              </div>
            </div>
            {health && (
              <div className="text-xs text-text-secondary">
                最后检查: {new Date(health.timestamp).toLocaleTimeString('zh-CN')}
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Quick Analysis */}
      <Card title="快速分析" padding="md">
        <form onSubmit={handleQuickAnalysis} className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Input
              value={quickAnalysisInput}
              onChange={(e) => setQuickAnalysisInput(e.target.value)}
              placeholder="输入股票代码进行分析（如 NVDA, 000001.SZ, 600036.SS）"
              leftIcon={<Search size={18} />}
            />
          </div>
          <button
            type="submit"
            disabled={!quickAnalysisInput.trim()}
            className="px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2 justify-center"
          >
            <span>开始分析</span>
            <ArrowRight size={18} />
          </button>
        </form>
        <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded-lg">
          <p className="text-sm text-blue-800 font-medium mb-2">💡 支持的股票代码格式</p>
          <div className="text-xs text-blue-700 space-y-1">
            <p>• 美股: AAPL, NVDA, TSLA</p>
            <p>• A股: 000001.SZ (深圳), 600036.SS (上海)</p>
            <p>• 港股: 0700.HK, 9988.HK</p>
          </div>
        </div>
      </Card>

      {/* Agent Details */}
      {agents && agents.length > 0 && (
        <Card title="Agent 详细信息" padding="md">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {agents.map((agent) => (
              <div
                key={agent.agent_name}
                className="p-4 border border-gray-200 rounded-lg hover:border-primary-300 transition-colors"
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-text-primary">
                    {agentNameMap[agent.agent_name] || agent.agent_name}
                  </h3>
                  <div
                    className={`w-3 h-3 rounded-full ${
                      agent.enabled ? 'bg-profit animate-pulse' : 'bg-gray-300'
                    }`}
                  />
                </div>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">状态</span>
                    <span className={`font-medium ${agent.enabled ? 'text-profit' : 'text-gray-500'}`}>
                      {agent.enabled ? '运行中' : '已停用'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">权重</span>
                    <span className="font-medium text-text-primary">{agent.weight.toFixed(1)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card padding="md">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-primary-50 rounded-lg">
              <Activity size={24} className="text-primary-500" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-text-primary mb-2">智能分析</h3>
              <p className="text-sm text-text-secondary mb-3">
                基于 4 个专业 AI Agent 的多维度股票分析，包括技术面、基本面、情绪和政策分析。
              </p>
              <button
                onClick={() => navigate('/analysis')}
                className="text-sm text-primary-500 hover:text-primary-600 font-medium flex items-center gap-1"
              >
                前往分析
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-purple-50 rounded-lg">
              <Cpu size={24} className="text-purple-500" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-text-primary mb-2">LLM 驱动</h3>
              <p className="text-sm text-text-secondary mb-3">
                使用大语言模型进行综合分析和决策，提供深入的投资建议和风险评估。
              </p>
              <span className="text-sm text-gray-500 flex items-center gap-1">
                智能决策引擎
              </span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
