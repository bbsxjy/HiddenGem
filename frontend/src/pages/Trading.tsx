import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { Input } from '@/components/common/Input';
import { Select } from '@/components/common/Select';
import { Table } from '@/components/common/Table';
import { createOrder, getOrders, cancelOrder, getRecentOrders, getCurrentSignals } from '@/api/orders';
import type { CreateOrderRequest, Order } from '@/types/order';

export function Trading() {
  const queryClient = useQueryClient();
  const [orderForm, setOrderForm] = useState<CreateOrderRequest>({
    symbol: '',
    side: 'buy',
    order_type: 'limit',
    quantity: 100,
    price: undefined,
  });

  // Fetch active orders
  const { data: activeOrders, isLoading: activeOrdersLoading } = useQuery({
    queryKey: ['orders', 'active'],
    queryFn: () => getOrders({ status: 'pending' }),
    refetchInterval: 5000,
  });

  // Fetch recent orders
  const { data: recentOrdersData, isLoading: recentOrdersLoading } = useQuery({
    queryKey: ['orders', 'recent'],
    queryFn: () => getRecentOrders(7),
    refetchInterval: 10000,
  });

  // Fetch current signals
  const { data: signals, isLoading: signalsLoading } = useQuery({
    queryKey: ['signals', 'current'],
    queryFn: () => getCurrentSignals(20),
    refetchInterval: 15000,
  });

  // Create order mutation
  const createOrderMutation = useMutation({
    mutationFn: createOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      // Reset form
      setOrderForm({
        symbol: '',
        side: 'buy',
        order_type: 'limit',
        quantity: 100,
        price: undefined,
      });
      alert('订单创建成功！');
    },
    onError: (error: any) => {
      alert(`订单创建失败: ${error.message}`);
    },
  });

  // Cancel order mutation
  const cancelOrderMutation = useMutation({
    mutationFn: cancelOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      alert('订单已取消');
    },
    onError: (error: any) => {
      alert(`取消订单失败: ${error.message}`);
    },
  });

  const handleSubmitOrder = (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!orderForm.symbol) {
      alert('请输入股票代码');
      return;
    }
    if (orderForm.quantity % 100 !== 0) {
      alert('数量必须是100的倍数');
      return;
    }
    if (orderForm.order_type === 'limit' && !orderForm.price) {
      alert('限价单必须输入价格');
      return;
    }

    createOrderMutation.mutate(orderForm);
  };

  const handleCancelOrder = (orderId: number) => {
    if (window.confirm('确定要取消此订单吗？')) {
      cancelOrderMutation.mutate(orderId);
    }
  };

  // Order table columns
  const orderColumns = [
    {
      header: 'ID',
      accessor: 'id' as const,
      cell: (value: number) => (
        <span className="text-sm font-mono text-text-secondary">{value}</span>
      ),
    },
    {
      header: '股票',
      accessor: 'symbol' as const,
      cell: (value: string) => (
        <span className="font-semibold text-text-primary">{value}</span>
      ),
    },
    {
      header: '方向',
      accessor: 'side' as const,
      cell: (value: string) => (
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          value === 'buy' ? 'bg-profit-light text-profit' : 'bg-loss-light text-loss'
        }`}>
          {value === 'buy' ? '买入' : '卖出'}
        </span>
      ),
    },
    {
      header: '类型',
      accessor: 'order_type' as const,
      cell: (value: string) => value === 'limit' ? '限价' : '市价',
    },
    {
      header: '数量',
      accessor: 'quantity' as const,
      cell: (value: number) => value.toLocaleString(),
    },
    {
      header: '价格',
      accessor: 'price' as const,
      cell: (value?: number) => value ? `¥${value.toFixed(2)}` : 'N/A',
    },
    {
      header: '状态',
      accessor: 'status' as const,
      cell: (value: string) => {
        const statusMap: Record<string, { text: string; color: string }> = {
          pending: { text: '待提交', color: 'bg-yellow-100 text-yellow-700' },
          submitted: { text: '已提交', color: 'bg-blue-100 text-blue-700' },
          partial_filled: { text: '部分成交', color: 'bg-purple-100 text-purple-700' },
          filled: { text: '已成交', color: 'bg-green-100 text-green-700' },
          cancelled: { text: '已取消', color: 'bg-gray-100 text-gray-700' },
          rejected: { text: '已拒绝', color: 'bg-red-100 text-red-700' },
        };
        const status = statusMap[value] || { text: value, color: 'bg-gray-100 text-gray-700' };
        return (
          <span className={`px-2 py-1 rounded text-xs font-medium ${status.color}`}>
            {status.text}
          </span>
        );
      },
    },
    {
      header: '创建时间',
      accessor: 'created_at' as const,
      cell: (value: string) => new Date(value).toLocaleString('zh-CN'),
    },
    {
      header: '操作',
      accessor: 'id' as const,
      cell: (value: number, row: Order) => (
        row.status === 'pending' || row.status === 'submitted' ? (
          <button
            onClick={() => handleCancelOrder(value)}
            className="text-loss hover:text-loss-dark text-sm font-medium"
            disabled={cancelOrderMutation.isPending}
          >
            取消
          </button>
        ) : null
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">交易</h1>
        <p className="text-text-secondary mt-1">执行交易和管理订单</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Order Form */}
        <Card title="创建订单" padding="md">
          <form onSubmit={handleSubmitOrder} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                股票代码
              </label>
              <Input
                value={orderForm.symbol}
                onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value })}
                placeholder="如 000001"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                买卖方向
              </label>
              <Select
                value={orderForm.side}
                onChange={(e) => setOrderForm({ ...orderForm, side: e.target.value as 'buy' | 'sell' })}
                options={[
                  { value: 'buy', label: '买入' },
                  { value: 'sell', label: '卖出' },
                ]}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                订单类型
              </label>
              <Select
                value={orderForm.order_type}
                onChange={(e) => setOrderForm({ ...orderForm, order_type: e.target.value as 'limit' | 'market' })}
                options={[
                  { value: 'limit', label: '限价单' },
                  { value: 'market', label: '市价单' },
                ]}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                数量（必须是100的倍数）
              </label>
              <Input
                type="number"
                value={orderForm.quantity}
                onChange={(e) => setOrderForm({ ...orderForm, quantity: parseInt(e.target.value) || 0 })}
                step="100"
                min="100"
                required
              />
            </div>

            {orderForm.order_type === 'limit' && (
              <div>
                <label className="block text-sm font-medium text-text-primary mb-2">
                  价格
                </label>
                <Input
                  type="number"
                  value={orderForm.price || ''}
                  onChange={(e) => setOrderForm({ ...orderForm, price: parseFloat(e.target.value) || undefined })}
                  step="0.01"
                  placeholder="0.00"
                  required
                />
              </div>
            )}

            <button
              type="submit"
              disabled={createOrderMutation.isPending}
              className="w-full px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {createOrderMutation.isPending ? '提交中...' : '提交订单'}
            </button>
          </form>
        </Card>

        {/* Current Signals */}
        <Card title="交易信号" padding="md" className="lg:col-span-2">
          {signalsLoading ? (
            <div className="h-96 flex items-center justify-center">
              <Loading size="sm" text="加载交易信号..." />
            </div>
          ) : signals && signals.length > 0 ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {signals.map((signal) => (
                <div
                  key={signal.id}
                  className="flex items-start justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-lg font-semibold text-text-primary">
                        {signal.symbol}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        signal.direction === 'buy'
                          ? 'bg-profit-light text-profit'
                          : signal.direction === 'sell'
                          ? 'bg-loss-light text-loss'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {signal.direction === 'buy' ? '买入' : signal.direction === 'sell' ? '卖出' : '持有'}
                      </span>
                      <span className="text-sm text-text-secondary">
                        强度: {(signal.strength * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="text-sm text-text-secondary mb-2">
                      {signal.agent_name} · {signal.reasoning.substring(0, 100)}
                      {signal.reasoning.length > 100 ? '...' : ''}
                    </div>
                    <div className="flex gap-4 text-xs text-text-secondary">
                      <span>入场价: ¥{signal.entry_price.toFixed(2)}</span>
                      {signal.target_price && <span>目标价: ¥{signal.target_price.toFixed(2)}</span>}
                      {signal.stop_loss_price && <span>止损价: ¥{signal.stop_loss_price.toFixed(2)}</span>}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-text-secondary mb-1">
                      {new Date(signal.timestamp).toLocaleString('zh-CN')}
                    </div>
                    {signal.is_executed && (
                      <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">
                        已执行
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-96 flex items-center justify-center text-text-secondary">
              暂无交易信号
            </div>
          )}
        </Card>
      </div>

      {/* Active Orders */}
      <Card title="活跃订单" padding="md">
        {activeOrdersLoading ? (
          <div className="h-64 flex items-center justify-center">
            <Loading size="sm" text="加载订单..." />
          </div>
        ) : activeOrders && activeOrders.length > 0 ? (
          <Table columns={orderColumns} data={activeOrders} />
        ) : (
          <div className="h-64 flex items-center justify-center text-text-secondary">
            暂无活跃订单
          </div>
        )}
      </Card>

      {/* Recent Orders History */}
      <Card title="最近订单（7天）" padding="md">
        {recentOrdersLoading ? (
          <div className="h-64 flex items-center justify-center">
            <Loading size="sm" text="加载订单历史..." />
          </div>
        ) : recentOrdersData && recentOrdersData.orders.length > 0 ? (
          <>
            <div className="mb-4 text-sm text-text-secondary">
              共 {recentOrdersData.count} 条订单
            </div>
            <Table columns={orderColumns} data={recentOrdersData.orders} />
          </>
        ) : (
          <div className="h-64 flex items-center justify-center text-text-secondary">
            暂无订单历史
          </div>
        )}
      </Card>
    </div>
  );
}
