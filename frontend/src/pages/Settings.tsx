import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Input } from '@/components/common/Input';
import { checkHealth } from '@/api/health';
import { useSettingsStore } from '@/store/useSettingsStore';
import { Settings as SettingsIcon, Server, Database, RefreshCw, BookOpen, Info, Save, RotateCcw } from 'lucide-react';

export function Settings() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

  // Fetch health status
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: 30000,
  });

  // Settings store
  const {
    riskControl,
    orderSettings,
    dataRefresh,
    updateRiskControl,
    updateOrderSettings,
    updateDataRefresh,
    resetRiskControl,
    resetOrderSettings,
    resetDataRefresh,
  } = useSettingsStore();

  // Local state for editing
  const [isEditingRisk, setIsEditingRisk] = useState(false);
  const [isEditingOrder, setIsEditingOrder] = useState(false);
  const [isEditingRefresh, setIsEditingRefresh] = useState(false);

  const [editedRisk, setEditedRisk] = useState(riskControl);
  const [editedOrder, setEditedOrder] = useState(orderSettings);
  const [editedRefresh, setEditedRefresh] = useState(dataRefresh);

  // Save handlers
  const handleSaveRisk = () => {
    updateRiskControl(editedRisk);
    setIsEditingRisk(false);
  };

  const handleSaveOrder = () => {
    updateOrderSettings(editedOrder);
    setIsEditingOrder(false);
  };

  const handleSaveRefresh = () => {
    updateDataRefresh(editedRefresh);
    setIsEditingRefresh(false);
  };

  // Reset handlers
  const handleResetRisk = () => {
    resetRiskControl();
    setEditedRisk(riskControl);
    setIsEditingRisk(false);
  };

  const handleResetOrder = () => {
    resetOrderSettings();
    setEditedOrder(orderSettings);
    setIsEditingOrder(false);
  };

  const handleResetRefresh = () => {
    resetDataRefresh();
    setEditedRefresh(dataRefresh);
    setIsEditingRefresh(false);
  };

  // Cancel handlers
  const handleCancelRisk = () => {
    setEditedRisk(riskControl);
    setIsEditingRisk(false);
  };

  const handleCancelOrder = () => {
    setEditedOrder(orderSettings);
    setIsEditingOrder(false);
  };

  const handleCancelRefresh = () => {
    setEditedRefresh(dataRefresh);
    setIsEditingRefresh(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
          <SettingsIcon className="text-primary-500" size={32} />
          系统设置
        </h1>
        <p className="text-text-secondary mt-1">配置系统参数和查看系统信息</p>
      </div>

      {/* System Info */}
      <Card title={<div className="flex items-center gap-2"><Server size={18} />系统信息</div>} padding="md">
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

      {/* Risk Control Settings */}
      <Card
        title={<div className="flex items-center gap-2"><Database size={18} />风险控制设置</div>}
        padding="md"
        extra={
          <div className="flex gap-2">
            {!isEditingRisk ? (
              <Button size="sm" variant="outline" onClick={() => setIsEditingRisk(true)}>
                编辑
              </Button>
            ) : (
              <>
                <Button size="sm" variant="outline" onClick={handleCancelRisk}>
                  取消
                </Button>
                <Button size="sm" variant="outline" onClick={handleResetRisk}>
                  <RotateCcw size={14} className="mr-1" />
                  重置
                </Button>
                <Button size="sm" onClick={handleSaveRisk}>
                  <Save size={14} className="mr-1" />
                  保存
                </Button>
              </>
            )}
          </div>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              最大单个仓位 (%)
            </label>
            {isEditingRisk ? (
              <Input
                type="number"
                value={editedRisk.maxPositionPct}
                onChange={(e) => setEditedRisk({ ...editedRisk, maxPositionPct: Number(e.target.value) })}
                min={1}
                max={100}
              />
            ) : (
              <div className="px-4 py-2 bg-gray-50 rounded-lg text-sm text-text-primary font-semibold">
                {riskControl.maxPositionPct}%
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              最大板块暴露 (%)
            </label>
            {isEditingRisk ? (
              <Input
                type="number"
                value={editedRisk.maxSectorExposurePct}
                onChange={(e) => setEditedRisk({ ...editedRisk, maxSectorExposurePct: Number(e.target.value) })}
                min={1}
                max={100}
              />
            ) : (
              <div className="px-4 py-2 bg-gray-50 rounded-lg text-sm text-text-primary font-semibold">
                {riskControl.maxSectorExposurePct}%
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              默认止损 (%)
            </label>
            {isEditingRisk ? (
              <Input
                type="number"
                value={editedRisk.defaultStopLossPct}
                onChange={(e) => setEditedRisk({ ...editedRisk, defaultStopLossPct: Number(e.target.value) })}
                min={1}
                max={50}
              />
            ) : (
              <div className="px-4 py-2 bg-gray-50 rounded-lg text-sm text-text-primary font-semibold">
                {riskControl.defaultStopLossPct}%
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              默认止盈 (%)
            </label>
            {isEditingRisk ? (
              <Input
                type="number"
                value={editedRisk.defaultTakeProfitPct}
                onChange={(e) => setEditedRisk({ ...editedRisk, defaultTakeProfitPct: Number(e.target.value) })}
                min={1}
                max={100}
              />
            ) : (
              <div className="px-4 py-2 bg-gray-50 rounded-lg text-sm text-text-primary font-semibold">
                {riskControl.defaultTakeProfitPct}%
              </div>
            )}
          </div>
        </div>

        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
          <strong>说明：</strong>
          风险控制参数会应用于所有自动交易和手动交易。请根据您的风险承受能力合理设置。
        </div>
      </Card>

      {/* Order Settings */}
      <Card
        title={<div className="flex items-center gap-2"><Database size={18} />订单设置</div>}
        padding="md"
        extra={
          <div className="flex gap-2">
            {!isEditingOrder ? (
              <Button size="sm" variant="outline" onClick={() => setIsEditingOrder(true)}>
                编辑
              </Button>
            ) : (
              <>
                <Button size="sm" variant="outline" onClick={handleCancelOrder}>
                  取消
                </Button>
                <Button size="sm" variant="outline" onClick={handleResetOrder}>
                  <RotateCcw size={14} className="mr-1" />
                  重置
                </Button>
                <Button size="sm" onClick={handleSaveOrder}>
                  <Save size={14} className="mr-1" />
                  保存
                </Button>
              </>
            )}
          </div>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              最小交易单位 (股)
            </label>
            {isEditingOrder ? (
              <Input
                type="number"
                value={editedOrder.minTradingUnit}
                onChange={(e) => setEditedOrder({ ...editedOrder, minTradingUnit: Number(e.target.value) })}
                min={100}
                step={100}
              />
            ) : (
              <div className="px-4 py-2 bg-gray-50 rounded-lg text-sm text-text-primary font-semibold">
                {orderSettings.minTradingUnit}股
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              默认订单类型
            </label>
            {isEditingOrder ? (
              <select
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                value={editedOrder.defaultOrderType}
                onChange={(e) => setEditedOrder({ ...editedOrder, defaultOrderType: e.target.value as 'limit' | 'market' })}
              >
                <option value="limit">限价单</option>
                <option value="market">市价单</option>
              </select>
            ) : (
              <div className="px-4 py-2 bg-gray-50 rounded-lg text-sm text-text-primary font-semibold">
                {orderSettings.defaultOrderType === 'limit' ? '限价单' : '市价单'}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              订单超时时间 (秒)
            </label>
            {isEditingOrder ? (
              <Input
                type="number"
                value={editedOrder.orderTimeoutSeconds}
                onChange={(e) => setEditedOrder({ ...editedOrder, orderTimeoutSeconds: Number(e.target.value) })}
                min={10}
                max={300}
              />
            ) : (
              <div className="px-4 py-2 bg-gray-50 rounded-lg text-sm text-text-primary font-semibold">
                {orderSettings.orderTimeoutSeconds}秒
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Data Refresh Settings */}
      <Card
        title={<div className="flex items-center gap-2"><RefreshCw size={18} />数据刷新设置</div>}
        padding="md"
        extra={
          <div className="flex gap-2">
            {!isEditingRefresh ? (
              <Button size="sm" variant="outline" onClick={() => setIsEditingRefresh(true)}>
                编辑
              </Button>
            ) : (
              <>
                <Button size="sm" variant="outline" onClick={handleCancelRefresh}>
                  取消
                </Button>
                <Button size="sm" variant="outline" onClick={handleResetRefresh}>
                  <RotateCcw size={14} className="mr-1" />
                  重置
                </Button>
                <Button size="sm" onClick={handleSaveRefresh}>
                  <Save size={14} className="mr-1" />
                  保存
                </Button>
              </>
            )}
          </div>
        }
      >
        <div className="space-y-4">
          <div>
            <h3 className="font-semibold text-text-primary mb-3">实时数据</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-text-secondary mb-1">行情数据 (秒)</label>
                {isEditingRefresh ? (
                  <Input
                    type="number"
                    value={editedRefresh.marketDataInterval}
                    onChange={(e) => setEditedRefresh({ ...editedRefresh, marketDataInterval: Number(e.target.value) })}
                    min={5}
                    max={300}
                  />
                ) : (
                  <div className="px-3 py-2 bg-gray-50 rounded text-sm font-semibold">{dataRefresh.marketDataInterval}秒</div>
                )}
              </div>

              <div>
                <label className="block text-xs text-text-secondary mb-1">持仓数据 (秒)</label>
                {isEditingRefresh ? (
                  <Input
                    type="number"
                    value={editedRefresh.positionDataInterval}
                    onChange={(e) => setEditedRefresh({ ...editedRefresh, positionDataInterval: Number(e.target.value) })}
                    min={5}
                    max={300}
                  />
                ) : (
                  <div className="px-3 py-2 bg-gray-50 rounded text-sm font-semibold">{dataRefresh.positionDataInterval}秒</div>
                )}
              </div>

              <div>
                <label className="block text-xs text-text-secondary mb-1">订单数据 (秒)</label>
                {isEditingRefresh ? (
                  <Input
                    type="number"
                    value={editedRefresh.orderDataInterval}
                    onChange={(e) => setEditedRefresh({ ...editedRefresh, orderDataInterval: Number(e.target.value) })}
                    min={5}
                    max={300}
                  />
                ) : (
                  <div className="px-3 py-2 bg-gray-50 rounded text-sm font-semibold">{dataRefresh.orderDataInterval}秒</div>
                )}
              </div>
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-text-primary mb-3">Agent数据</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-text-secondary mb-1">状态检查 (秒)</label>
                {isEditingRefresh ? (
                  <Input
                    type="number"
                    value={editedRefresh.agentStatusInterval}
                    onChange={(e) => setEditedRefresh({ ...editedRefresh, agentStatusInterval: Number(e.target.value) })}
                    min={5}
                    max={300}
                  />
                ) : (
                  <div className="px-3 py-2 bg-gray-50 rounded text-sm font-semibold">{dataRefresh.agentStatusInterval}秒</div>
                )}
              </div>

              <div>
                <label className="block text-xs text-text-secondary mb-1">交易信号 (秒)</label>
                {isEditingRefresh ? (
                  <Input
                    type="number"
                    value={editedRefresh.signalInterval}
                    onChange={(e) => setEditedRefresh({ ...editedRefresh, signalInterval: Number(e.target.value) })}
                    min={5}
                    max={300}
                  />
                ) : (
                  <div className="px-3 py-2 bg-gray-50 rounded text-sm font-semibold">{dataRefresh.signalInterval}秒</div>
                )}
              </div>

              <div>
                <label className="block text-xs text-text-secondary mb-1">策略列表 (秒)</label>
                {isEditingRefresh ? (
                  <Input
                    type="number"
                    value={editedRefresh.strategyListInterval}
                    onChange={(e) => setEditedRefresh({ ...editedRefresh, strategyListInterval: Number(e.target.value) })}
                    min={5}
                    max={300}
                  />
                ) : (
                  <div className="px-3 py-2 bg-gray-50 rounded text-sm font-semibold">{dataRefresh.strategyListInterval}秒</div>
                )}
              </div>
            </div>
          </div>

          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
            <strong>说明：</strong>
            数据刷新间隔默认为30秒，与数据源更新频率保持一致。过短的刷新间隔可能导致API请求过于频繁。
          </div>
        </div>
      </Card>

      {/* API Documentation */}
      <Card title={<div className="flex items-center gap-2"><BookOpen size={18} />API文档</div>} padding="md">
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
      <Card title={<div className="flex items-center gap-2"><Info size={18} />关于系统</div>} padding="md">
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
