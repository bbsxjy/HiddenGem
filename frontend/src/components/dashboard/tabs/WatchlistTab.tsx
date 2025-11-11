import { useState } from 'react';
import { Card } from '@/components/common/Card';
import { Input } from '@/components/common/Input';
import { Button } from '@/components/common/Button';
import {
  Star,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  ArrowUpCircle,
  ArrowDownCircle,
} from 'lucide-react';

interface WatchlistItem {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
  volume: number;
  turnoverRate: number;
}

export function WatchlistTab() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([
    // Mock data - 待替换为真实API数据
    {
      symbol: '000001',
      name: '平安银行',
      price: 12.58,
      change: 0.15,
      changePct: 1.21,
      volume: 856231000,
      turnoverRate: 0.42,
    },
    {
      symbol: '600519',
      name: '贵州茅台',
      price: 1635.00,
      change: -8.50,
      changePct: -0.52,
      volume: 123456000,
      turnoverRate: 0.18,
    },
  ]);

  const [newSymbol, setNewSymbol] = useState('');

  const handleAddStock = () => {
    if (!newSymbol.trim()) return;

    // TODO: 实际调用API获取股票信息
    console.log('添加股票:', newSymbol);
    setNewSymbol('');
  };

  const handleRemoveStock = (symbol: string) => {
    setWatchlist(watchlist.filter(item => item.symbol !== symbol));
  };

  const formatVolume = (volume: number) => {
    if (volume >= 100000000) {
      return `${(volume / 100000000).toFixed(2)}亿`;
    } else if (volume >= 10000) {
      return `${(volume / 10000).toFixed(2)}万`;
    }
    return volume.toString();
  };

  const getChangeColor = (change: number) => {
    if (change > 0) return 'text-profit';
    if (change < 0) return 'text-loss';
    return 'text-text-secondary';
  };

  return (
    <div className="space-y-6">
      {/* 添加自选股 */}
      <Card title="添加自选股" padding="md">
        <div className="flex gap-3">
          <div className="flex-1">
            <Input
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              placeholder="输入股票代码（如：000001, 600519）"
              onKeyPress={(e) => e.key === 'Enter' && handleAddStock()}
            />
          </div>
          <Button onClick={handleAddStock}>
            <Plus size={18} className="mr-1" />
            添加
          </Button>
        </div>
      </Card>

      {/* 自选股列表 */}
      <Card title="自选股列表" padding="md">
        {watchlist.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                    股票代码
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                    股票名称
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-text-secondary uppercase tracking-wider">
                    最新价
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-text-secondary uppercase tracking-wider">
                    涨跌额
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-text-secondary uppercase tracking-wider">
                    涨跌幅
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-text-secondary uppercase tracking-wider">
                    成交量
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-text-secondary uppercase tracking-wider">
                    换手率
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-text-secondary uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {watchlist.map((item) => (
                  <tr key={item.symbol} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Star size={16} className="text-yellow-500 fill-yellow-500" />
                        <span className="text-sm font-medium text-primary-600">
                          {item.symbol}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-primary">
                      {item.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <span className={`text-sm font-bold ${getChangeColor(item.change)}`}>
                        ¥{item.price.toFixed(2)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <span className={`text-sm font-medium ${getChangeColor(item.change)}`}>
                        {item.change > 0 ? '+' : ''}{item.change.toFixed(2)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-1">
                        {item.changePct > 0 ? (
                          <TrendingUp size={14} className="text-profit" />
                        ) : item.changePct < 0 ? (
                          <TrendingDown size={14} className="text-loss" />
                        ) : null}
                        <span className={`text-sm font-medium ${getChangeColor(item.change)}`}>
                          {item.changePct > 0 ? '+' : ''}{item.changePct.toFixed(2)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-text-primary">
                      {formatVolume(item.volume)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-text-primary">
                      {item.turnoverRate.toFixed(2)}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => handleRemoveStock(item.symbol)}
                          className="text-loss hover:text-loss/80 transition-colors"
                          title="移除"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-text-secondary">
            <Star size={48} className="mx-auto mb-4 text-gray-300" />
            <p>暂无自选股</p>
            <p className="text-sm mt-2">请在上方添加您关注的股票</p>
          </div>
        )}
      </Card>

      {/* 热点板块 */}
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-4">热点板块</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card title="涨幅榜 Top 5" padding="md">
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <div className="flex items-center gap-2">
                    <ArrowUpCircle size={16} className="text-profit" />
                    <span className="text-sm font-medium text-text-primary">板块{i + 1}</span>
                  </div>
                  <span className="text-sm font-bold text-profit">+{(5 - i * 0.5).toFixed(2)}%</span>
                </div>
              ))}
            </div>
          </Card>

          <Card title="跌幅榜 Top 5" padding="md">
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <div className="flex items-center gap-2">
                    <ArrowDownCircle size={16} className="text-loss" />
                    <span className="text-sm font-medium text-text-primary">板块{i + 1}</span>
                  </div>
                  <span className="text-sm font-bold text-loss">-{(3 - i * 0.3).toFixed(2)}%</span>
                </div>
              ))}
            </div>
          </Card>

          <Card title="成交额榜 Top 5" padding="md">
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <div className="flex items-center gap-2">
                    <Activity size={16} className="text-primary-500" />
                    <span className="text-sm font-medium text-text-primary">板块{i + 1}</span>
                  </div>
                  <span className="text-sm font-medium text-text-primary">
                    {(500 - i * 50)}亿
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* 资金流向 */}
      <div>
        <h2 className="text-lg font-semibold text-text-primary mb-4">资金流向</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card title="北向资金" padding="md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-profit">+125.8亿</div>
                <div className="text-sm text-text-secondary mt-1">净流入</div>
              </div>
              <DollarSign className="h-8 w-8 text-profit" />
            </div>
          </Card>

          <Card title="融资融券余额" padding="md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-text-primary">16,523亿</div>
                <div className="text-sm text-profit mt-1">+2.3%</div>
              </div>
              <Activity className="h-8 w-8 text-primary-500" />
            </div>
          </Card>

          <Card title="大单流向" padding="md">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-loss">-58.9亿</div>
                <div className="text-sm text-text-secondary mt-1">净流出</div>
              </div>
              <TrendingDown className="h-8 w-8 text-loss" />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
