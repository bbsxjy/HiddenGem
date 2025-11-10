import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { checkHealth } from '@/api/health';
import { Play, Square, TrendingUp, TrendingDown, Clock, DollarSign, Activity } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function Settings() {
  const queryClient = useQueryClient();

  // 自动交易配置
  const [symbols, setSymbols] = useState('000001,600519,000858');
  const [initialCash, setInitialCash] = useState(100000);
  const [checkInterval, setCheckInterval] = useState(5);
  const [useMultiAgent, setUseMultiAgent] = useState(true);

  // Fetch health status
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: 10000,
  });

  // Fetch auto trading status
  const { data: autoTradingStatus, isLoading: isStatusLoading } = useQuery({
    queryKey: ['autoTradingStatus'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/api/v1/auto-trading/status`);
      return response.data.data;
    },
    refetchInterval: 3000, // 每3秒刷新状态
  });

  // Start auto trading mutation
  const startMutation = useMutation({
    mutationFn: async () => {
      const symbolList = symbols.split(',').map(s => s.trim()).filter(Boolean);
      const response = await axios.post(`${API_BASE_URL}/api/v1/auto-trading/start`, {
        symbols: symbolList,
        initial_cash: initialCash,
        check_interval: checkInterval,
        use_multi_agent: useMultiAgent,
        strategies: ['rl', 'multi_agent']
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['autoTradingStatus'] });
    },
  });

  // Stop auto trading mutation
  const stopMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${API_BASE_URL}/api/v1/auto-trading/stop`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['autoTradingStatus'] });
    },
  });

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

  const isRunning = autoTradingStatus?.is_running || false;
  const profitLoss = autoTradingStatus?.profit_loss || 0;
  const profitLossPct = autoTradingStatus?.profit_loss_pct || 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">设置</h1>
        <p className="text-text-secondary mt-1">配置系统参数和偏好设置</p>
      </div>

      {/* Auto Trading Control */}
      <Card title="自动交易控制" padding="md">
        <div className="space-y-6">
          {/* Status Display */}
          <div className="p-4 border-2 border-dashed rounded-lg" style={{
            borderColor: isRunning ? '#10b981' : '#d1d5db',
            backgroundColor: isRunning ? '#f0fdf4' : '#f9fafb'
          }}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-profit animate-pulse' : 'bg-gray-400'}`} />
                <h3 className="font-semibold text-text-primary">
                  状态: {isRunning ? '运行中' : '未运行'}
                </h3>
              </div>
              {isRunning && autoTradingStatus?.started_at && (
                <span className="text-xs text-text-secondary">
                  启动于: {new Date(autoTradingStatus.started_at).toLocaleString('zh-CN')}
                </span>
              )}
            </div>

            {isRunning && autoTradingStatus && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white p-3 rounded-lg border border-gray-200">
                  <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                    <DollarSign size={14} />
                    总资产
                  </div>
                  <div className="text-lg font-bold text-text-primary">
                    ¥{autoTradingStatus.total_assets.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>

                <div className="bg-white p-3 rounded-lg border border-gray-200">
                  <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                    {profitLoss >= 0 ? <TrendingUp size={14} className="text-profit" /> : <TrendingDown size={14} className="text-loss" />}
                    盈亏
                  </div>
                  <div className={`text-lg font-bold ${profitLoss >= 0 ? 'text-profit' : 'text-loss'}`}>
                    {profitLoss >= 0 ? '+' : ''}¥{profitLoss.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    <span className="text-sm ml-2">({profitLossPct >= 0 ? '+' : ''}{profitLossPct.toFixed(2)}%)</span>
                  </div>
                </div>

                <div className="bg-white p-3 rounded-lg border border-gray-200">
                  <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                    <Activity size={14} />
                    交易次数
                  </div>
                  <div className="text-lg font-bold text-text-primary">
                    {autoTradingStatus.total_trades}
                  </div>
                </div>

                <div className="bg-white p-3 rounded-lg border border-gray-200">
                  <div className="flex items-center gap-2 text-xs text-text-secondary mb-1">
                    <Clock size={14} />
                    交易时段
                  </div>
                  <div className="text-sm font-semibold text-text-primary">
                    {autoTradingStatus.is_trading_hours ? (
                      <span className="text-profit">进行中</span>
                    ) : (
                      <span className="text-text-secondary">非交易时间</span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {isRunning && autoTradingStatus?.next_check_time && (
              <div className="mt-3 text-xs text-text-secondary">
                下次检查时间: {new Date(autoTradingStatus.next_check_time).toLocaleString('zh-CN')}
              </div>
            )}
          </div>

          {/* Configuration Form */}
          {!isRunning && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    交易股票列表 <span className="text-xs text-text-secondary">(逗号分隔)</span>
                  </label>
                  <Input
                    placeholder="例如: 000001,600519,000858"
                    value={symbols}
                    onChange={(e) => setSymbols(e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    初始资金 (CNY)
                  </label>
                  <Input
                    type="number"
                    placeholder="100000"
                    value={initialCash}
                    onChange={(e) => setInitialCash(Number(e.target.value))}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-primary mb-2">
                    检查间隔 (分钟)
                  </label>
                  <Input
                    type="number"
                    placeholder="5"
                    value={checkInterval}
                    onChange={(e) => setCheckInterval(Number(e.target.value))}
                  />
                </div>

                <div className="flex items-center">
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="w-4 h-4 text-primary-500 border-gray-300 rounded focus:ring-primary-500"
                      checked={useMultiAgent}
                      onChange={(e) => setUseMultiAgent(e.target.checked)}
                    />
                    <span className="ml-2 text-sm font-medium text-text-primary">
                      启用多Agent智能分析
                    </span>
                  </label>
                </div>
              </div>

              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
                <strong>说明：</strong>
                自动交易系统将在中国A股交易时间（9:30-11:30, 13:00-15:00）自动执行交易决策。
                非交易时间系统会等待到下一个交易时段。
              </div>
            </div>
          )}

          {/* Control Buttons */}
          <div className="flex gap-3">
            {!isRunning ? (
              <Button
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending || !symbols.trim()}
                className="flex items-center gap-2"
              >
                <Play size={16} />
                启动自动交易
                {startMutation.isPending && '...'}
              </Button>
            ) : (
              <Button
                onClick={() => stopMutation.mutate()}
                disabled={stopMutation.isPending}
                variant="outline"
                className="flex items-center gap-2 border-red-300 text-red-600 hover:bg-red-50"
              >
                <Square size={16} />
                停止自动交易
                {stopMutation.isPending && '...'}
              </Button>
            )}
          </div>

          {/* Error Messages */}
          {startMutation.isError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
              启动失败: {(startMutation.error as any)?.response?.data?.detail || startMutation.error?.message || '未知错误'}
            </div>
          )}
          {stopMutation.isError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
              停止失败: {(stopMutation.error as any)?.response?.data?.detail || stopMutation.error?.message || '未知错误'}
            </div>
          )}
        </div>
      </Card>

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
