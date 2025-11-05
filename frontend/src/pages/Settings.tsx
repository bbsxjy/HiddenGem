import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { checkHealth } from '@/api/health';

export function Settings() {
  // Fetch health status
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: 10000,
  });

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">设置</h1>
        <p className="text-text-secondary mt-1">配置系统参数和偏好设置</p>
      </div>

      {/* System Info */}
      <Card title="系统信息" padding="md">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                后端服务地址
              </label>
              <div className="px-4 py-2 bg-gray-50 rounded-lg font-mono text-sm text-text-primary">
                {apiBaseUrl}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                WebSocket地址
              </label>
              <div className="px-4 py-2 bg-gray-50 rounded-lg font-mono text-sm text-text-primary">
                {wsUrl}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                服务名称
              </label>
              <div className="px-4 py-2 bg-gray-50 rounded-lg text-sm text-text-primary">
                {health?.service || 'N/A'}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                服务版本
              </label>
              <div className="px-4 py-2 bg-gray-50 rounded-lg text-sm text-text-primary">
                {health?.version || 'N/A'}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                运行环境
              </label>
              <div className="px-4 py-2 bg-gray-50 rounded-lg text-sm text-text-primary">
                {health?.environment || 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Trading Settings */}
      <Card title="交易设置" padding="md">
        <div className="space-y-4">
          <div className="p-4 border border-gray-200 rounded-lg">
            <h3 className="font-semibold text-text-primary mb-2">风险控制</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-text-secondary">最大单个仓位:</span>
                <span className="font-semibold text-text-primary ml-2">10%</span>
              </div>
              <div>
                <span className="text-text-secondary">默认止损:</span>
                <span className="font-semibold text-text-primary ml-2">8%</span>
              </div>
              <div>
                <span className="text-text-secondary">默认止盈:</span>
                <span className="font-semibold text-text-primary ml-2">15%</span>
              </div>
            </div>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg">
            <h3 className="font-semibold text-text-primary mb-2">订单设置</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-text-secondary">最小交易单位:</span>
                <span className="font-semibold text-text-primary ml-2">100股</span>
              </div>
              <div>
                <span className="text-text-secondary">默认订单类型:</span>
                <span className="font-semibold text-text-primary ml-2">限价单</span>
              </div>
              <div>
                <span className="text-text-secondary">超时时间:</span>
                <span className="font-semibold text-text-primary ml-2">30秒</span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Data Refresh Settings */}
      <Card title="数据刷新设置" padding="md">
        <div className="space-y-4">
          <div className="p-4 border border-gray-200 rounded-lg">
            <h3 className="font-semibold text-text-primary mb-2">实时数据</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-text-secondary">行情数据:</span>
                <span className="font-semibold text-text-primary ml-2">5秒</span>
              </div>
              <div>
                <span className="text-text-secondary">持仓数据:</span>
                <span className="font-semibold text-text-primary ml-2">10秒</span>
              </div>
              <div>
                <span className="text-text-secondary">订单数据:</span>
                <span className="font-semibold text-text-primary ml-2">5秒</span>
              </div>
            </div>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg">
            <h3 className="font-semibold text-text-primary mb-2">Agent数据</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-text-secondary">状态检查:</span>
                <span className="font-semibold text-text-primary ml-2">15秒</span>
              </div>
              <div>
                <span className="text-text-secondary">交易信号:</span>
                <span className="font-semibold text-text-primary ml-2">10秒</span>
              </div>
              <div>
                <span className="text-text-secondary">策略列表:</span>
                <span className="font-semibold text-text-primary ml-2">20秒</span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* API Documentation */}
      <Card title="API文档" padding="md">
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">
            访问以下地址查看后端API的完整文档：
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <a
              href={`${apiBaseUrl}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-text-primary">Swagger UI</h3>
                  <p className="text-sm text-text-secondary mt-1">
                    交互式API文档
                  </p>
                </div>
                <svg className="w-5 h-5 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </div>
            </a>

            <a
              href={`${apiBaseUrl}/redoc`}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-text-primary">ReDoc</h3>
                  <p className="text-sm text-text-secondary mt-1">
                    详细API文档
                  </p>
                </div>
                <svg className="w-5 h-5 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </div>
            </a>
          </div>
        </div>
      </Card>

      {/* About */}
      <Card title="关于系统" padding="md">
        <div className="space-y-3 text-sm text-text-secondary">
          <p>
            <strong className="text-text-primary">HiddenGem</strong> 是一个基于MCP智能体的A股量化交易系统。
          </p>
          <p>
            系统采用多Agent协同决策架构，整合政策、市场、技术、基本面、情绪、风险等多维度分析，
            为A股市场提供智能化的交易决策支持。
          </p>
          <p>
            前端采用 React + TypeScript + TailwindCSS 构建，后端使用 FastAPI + MCP Agent 框架。
          </p>
          <div className="pt-4 border-t border-gray-200 flex items-center gap-4">
            <span className="text-text-primary font-medium">技术栈:</span>
            <div className="flex gap-2 flex-wrap">
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">React</span>
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">TypeScript</span>
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">TailwindCSS</span>
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">FastAPI</span>
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">MCP</span>
              <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">TimescaleDB</span>
              <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs">Redis</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
