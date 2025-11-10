import { useState, useEffect } from 'react';
import { Card } from '@/components/common/Card';
import { Input } from '@/components/common/Input';
import { Button } from '@/components/common/Button';
import type { Order } from '@/types/order';
import {
  History,
  TrendingUp,
  TrendingDown,
  Search,
  Filter,
  Calendar,
  ArrowUpDown,
} from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function TradeHistory() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSide, setFilterSide] = useState<'all' | 'buy' | 'sell'>('all');
  const [filterStatus, setFilterStatus] = useState<'all' | 'filled' | 'pending' | 'cancelled'>('all');
  const [sortBy, setSortBy] = useState<'time' | 'price' | 'quantity'>('time');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [daysFilter, setDaysFilter] = useState(7);

  // 获取交易历史
  useEffect(() => {
    fetchTradeHistory();
  }, [daysFilter]);

  const fetchTradeHistory = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/orders/history/recent`, {
        params: { days: daysFilter }
      });

      if (response.data.success) {
        const ordersData = response.data.data.orders || [];
        setOrders(ordersData);
        setFilteredOrders(ordersData);
      }
    } catch (error) {
      console.error('获取交易历史失败:', error);
      setOrders([]);
      setFilteredOrders([]);
    } finally {
      setIsLoading(false);
    }
  };

  // 过滤和排序
  useEffect(() => {
    let result = [...orders];

    // 搜索过滤
    if (searchTerm) {
      result = result.filter(order =>
        order.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
        order.name?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // 买卖方向过滤
    if (filterSide !== 'all') {
      result = result.filter(order => order.side === filterSide);
    }

    // 状态过滤
    if (filterStatus !== 'all') {
      result = result.filter(order => order.status === filterStatus);
    }

    // 排序
    result.sort((a, b) => {
      let comparison = 0;

      if (sortBy === 'time') {
        comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      } else if (sortBy === 'price') {
        comparison = (a.avg_filled_price || a.price || 0) - (b.avg_filled_price || b.price || 0);
      } else if (sortBy === 'quantity') {
        comparison = a.quantity - b.quantity;
      }

      return sortOrder === 'asc' ? comparison : -comparison;
    });

    setFilteredOrders(result);
  }, [orders, searchTerm, filterSide, filterStatus, sortBy, sortOrder]);

  // 格式化日期
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // 格式化价格
  const formatPrice = (price: number | undefined) => {
    if (!price) return '-';
    return `¥${price.toFixed(2)}`;
  };

  // 获取状态文字和颜色
  const getStatusInfo = (status: string) => {
    const statusMap: Record<string, { text: string; color: string }> = {
      pending: { text: '待成交', color: 'text-yellow-600 bg-yellow-50' },
      filled: { text: '已成交', color: 'text-profit bg-green-50' },
      cancelled: { text: '已取消', color: 'text-gray-600 bg-gray-50' },
      rejected: { text: '已拒绝', color: 'text-loss bg-red-50' },
    };
    return statusMap[status] || { text: status, color: 'text-gray-600 bg-gray-50' };
  };

  // 切换排序
  const toggleSort = (field: 'time' | 'price' | 'quantity') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
            <History className="text-primary-500" size={32} />
            交易历史
          </h1>
          <p className="text-text-secondary mt-1">
            查看和分析历史交易记录
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button onClick={fetchTradeHistory} disabled={isLoading}>
            刷新数据
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card padding="md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary">总交易数</p>
              <p className="text-2xl font-bold text-text-primary mt-1">
                {filteredOrders.length}
              </p>
            </div>
            <div className="p-3 bg-primary-50 rounded-lg">
              <History size={24} className="text-primary-500" />
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary">买入次数</p>
              <p className="text-2xl font-bold text-profit mt-1">
                {filteredOrders.filter(o => o.side === 'buy').length}
              </p>
            </div>
            <div className="p-3 bg-profit/10 rounded-lg">
              <TrendingUp size={24} className="text-profit" />
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary">卖出次数</p>
              <p className="text-2xl font-bold text-loss mt-1">
                {filteredOrders.filter(o => o.side === 'sell').length}
              </p>
            </div>
            <div className="p-3 bg-loss/10 rounded-lg">
              <TrendingDown size={24} className="text-loss" />
            </div>
          </div>
        </Card>

        <Card padding="md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-text-secondary">成交率</p>
              <p className="text-2xl font-bold text-text-primary mt-1">
                {orders.length > 0
                  ? ((orders.filter(o => o.status === 'filled').length / orders.length) * 100).toFixed(1)
                  : '0'}%
              </p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg">
              <Calendar size={24} className="text-blue-500" />
            </div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card padding="md">
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm font-medium text-text-primary">
            <Filter size={16} />
            筛选条件
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* 搜索 */}
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                搜索股票
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-text-secondary" size={16} />
                <Input
                  placeholder="股票代码或名称"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {/* 买卖方向 */}
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                买卖方向
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={filterSide}
                onChange={(e) => setFilterSide(e.target.value as any)}
              >
                <option value="all">全部</option>
                <option value="buy">买入</option>
                <option value="sell">卖出</option>
              </select>
            </div>

            {/* 订单状态 */}
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                订单状态
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
              >
                <option value="all">全部</option>
                <option value="filled">已成交</option>
                <option value="pending">待成交</option>
                <option value="cancelled">已取消</option>
              </select>
            </div>

            {/* 时间范围 */}
            <div>
              <label className="block text-sm font-medium text-text-primary mb-2">
                时间范围
              </label>
              <select
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={daysFilter}
                onChange={(e) => setDaysFilter(Number(e.target.value))}
              >
                <option value={1}>今天</option>
                <option value={7}>最近7天</option>
                <option value={30}>最近30天</option>
                <option value={90}>最近90天</option>
              </select>
            </div>
          </div>
        </div>
      </Card>

      {/* Trade List */}
      <Card title="交易记录" padding="none">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
              <p className="text-text-secondary">加载中...</p>
            </div>
          </div>
        ) : filteredOrders.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <History className="mx-auto h-16 w-16 text-text-secondary mb-4" />
              <p className="text-text-secondary">暂无交易记录</p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => toggleSort('time')}
                  >
                    <div className="flex items-center gap-1">
                      交易时间
                      {sortBy === 'time' && (
                        <ArrowUpDown size={14} className={sortOrder === 'asc' ? 'rotate-180' : ''} />
                      )}
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                    股票代码
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                    股票名称
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                    方向
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => toggleSort('price')}
                  >
                    <div className="flex items-center gap-1">
                      价格
                      {sortBy === 'price' && (
                        <ArrowUpDown size={14} className={sortOrder === 'asc' ? 'rotate-180' : ''} />
                      )}
                    </div>
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => toggleSort('quantity')}
                  >
                    <div className="flex items-center gap-1">
                      数量
                      {sortBy === 'quantity' && (
                        <ArrowUpDown size={14} className={sortOrder === 'asc' ? 'rotate-180' : ''} />
                      )}
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                    状态
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                    策略
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                    交易原因
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredOrders.map((order) => {
                  const statusInfo = getStatusInfo(order.status);
                  const isBuy = order.side === 'buy';

                  return (
                    <tr key={order.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-primary">
                        {formatDate(order.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-primary-600">
                          {order.symbol}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-primary">
                        {order.name || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {isBuy ? (
                            <>
                              <TrendingUp size={16} className="text-profit" />
                              <span className="text-sm font-medium text-profit">买入</span>
                            </>
                          ) : (
                            <>
                              <TrendingDown size={16} className="text-loss" />
                              <span className="text-sm font-medium text-loss">卖出</span>
                            </>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-text-primary">
                        {formatPrice(order.avg_filled_price || order.price)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-primary">
                        {order.filled_quantity || order.quantity}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusInfo.color}`}>
                          {statusInfo.text}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-text-primary">
                        {order.strategy_name || '-'}
                      </td>
                      <td className="px-6 py-4 max-w-xs">
                        <div className="text-sm text-text-secondary truncate" title={order.reasoning}>
                          {order.reasoning || '无说明'}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
