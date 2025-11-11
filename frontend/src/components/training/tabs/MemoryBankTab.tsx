import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { Input } from '@/components/common/Input';
import { Button } from '@/components/common/Button';
import {
  getEpisodes,
  getEpisodeDetail,
  getStatistics,
  deleteEpisode,
  updateEpisode,
} from '@/api/memory';
import type { Episode, EpisodeDetail, EpisodeUpdate } from '@/types/memory';
import {
  Database,
  Search,
  TrendingUp,
  TrendingDown,
  Calendar,
  DollarSign,
  BarChart3,
  Eye,
  Edit2,
  Trash2,
  Filter,
  X,
  Activity,
  PieChart,
} from 'lucide-react';

export function MemoryBankTab() {
  const queryClient = useQueryClient();
  const [searchSymbol, setSearchSymbol] = useState('');
  const [filterSuccess, setFilterSuccess] = useState<boolean | undefined>(undefined);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [selectedEpisode, setSelectedEpisode] = useState<string | null>(null);
  const [editingEpisode, setEditingEpisode] = useState<EpisodeDetail | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Fetch statistics
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['memory', 'statistics'],
    queryFn: getStatistics,
  });

  // Fetch episodes with filters
  const { data: episodes, isLoading: episodesLoading, refetch } = useQuery({
    queryKey: ['memory', 'episodes', { searchSymbol, filterSuccess, dateFrom, dateTo }],
    queryFn: () =>
      getEpisodes({
        symbol: searchSymbol || undefined,
        success: filterSuccess,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: 100,
      }),
  });

  // Fetch episode detail
  const { data: episodeDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['memory', 'episode', selectedEpisode],
    queryFn: () => getEpisodeDetail(selectedEpisode!),
    enabled: !!selectedEpisode,
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteEpisode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory'] });
      setSelectedEpisode(null);
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, update }: { id: string; update: EpisodeUpdate }) =>
      updateEpisode(id, update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory'] });
      setEditingEpisode(null);
      setSelectedEpisode(null);
    },
  });

  const handleDelete = (episodeId: string) => {
    if (window.confirm('确定要删除这个经验记录吗？')) {
      deleteMutation.mutate(episodeId);
    }
  };

  const handleUpdate = () => {
    if (!editingEpisode) return;

    updateMutation.mutate({
      id: editingEpisode.episode_id,
      update: {
        lesson: editingEpisode.lesson,
        key_lesson: editingEpisode.key_lesson,
        success: editingEpisode.success,
      },
    });
  };

  const clearFilters = () => {
    setSearchSymbol('');
    setFilterSuccess(undefined);
    setDateFrom('');
    setDateTo('');
  };

  // Process chart data
  const chartData = useMemo(() => {
    if (!episodes || episodes.length === 0) {
      return { dailyActivity: [], cumulativeReturns: [] };
    }

    // Sort episodes by date
    const sortedEpisodes = [...episodes].sort((a, b) =>
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    // Daily trading activity (buy/sell count per day)
    const dailyActivityMap = new Map<string, { date: string; buys: number; sells: number; holds: number }>();

    sortedEpisodes.forEach(ep => {
      const existing = dailyActivityMap.get(ep.date) || { date: ep.date, buys: 0, sells: 0, holds: 0 };

      if (ep.action === 'buy' || ep.action === '买入') {
        existing.buys += 1;
      } else if (ep.action === 'sell' || ep.action === '卖出') {
        existing.sells += 1;
      } else {
        existing.holds += 1;
      }

      dailyActivityMap.set(ep.date, existing);
    });

    const dailyActivity = Array.from(dailyActivityMap.values());

    // Cumulative returns over time
    let cumulativeReturn = 0;
    const cumulativeReturns = sortedEpisodes
      .filter(ep => ep.percentage_return !== null && ep.percentage_return !== undefined)
      .map(ep => {
        cumulativeReturn += (ep.percentage_return || 0);
        return {
          date: ep.date,
          cumulativeReturn: cumulativeReturn * 100, // Convert to percentage
          singleReturn: (ep.percentage_return || 0) * 100,
          symbol: ep.symbol,
        };
      });

    return { dailyActivity, cumulativeReturns };
  }, [episodes]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text-primary">Memory Bank</h1>
          <p className="text-text-secondary mt-1">交易经验库 - 查看和管理历史交易经验</p>
        </div>
        <Database className="w-8 h-8 text-primary-500" />
      </div>

      {/* Statistics Cards */}
      {statsLoading ? (
        <Loading />
      ) : stats ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">总Episodes</p>
                <p className="text-2xl font-bold text-text-primary mt-1">
                  {stats.total_episodes}
                </p>
              </div>
              <BarChart3 className="w-8 h-8 text-primary-500" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">成功率</p>
                <p className="text-2xl font-bold text-profit mt-1">
                  {(stats.success_rate * 100).toFixed(1)}%
                </p>
                <p className="text-xs text-text-secondary mt-1">
                  {stats.successful_episodes} 成功 / {stats.failed_episodes} 失败
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-profit" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">平均收益</p>
                <p
                  className={`text-2xl font-bold mt-1 ${
                    stats.average_return >= 0 ? 'text-profit' : 'text-loss'
                  }`}
                >
                  {stats.average_return >= 0 ? '+' : ''}
                  {(stats.average_return * 100).toFixed(2)}%
                </p>
              </div>
              <DollarSign
                className={`w-8 h-8 ${stats.average_return >= 0 ? 'text-profit' : 'text-loss'}`}
              />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-text-secondary">日期范围</p>
                <p className="text-sm font-medium text-text-primary mt-1">
                  {stats.date_range.earliest}
                </p>
                <p className="text-sm font-medium text-text-primary">
                  至 {stats.date_range.latest}
                </p>
              </div>
              <Calendar className="w-8 h-8 text-primary-500" />
            </div>
          </Card>
        </div>
      ) : null}

      {/* Charts Section */}
      {episodes && episodes.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Daily Trading Activity Chart */}
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-5 h-5 text-primary-500" />
              <h2 className="text-lg font-semibold text-text-primary">每日交易活动</h2>
            </div>
            {chartData.dailyActivity.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData.dailyActivity}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    stroke="#6b7280"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      return `${date.getMonth() + 1}/${date.getDate()}`;
                    }}
                  />
                  <YAxis stroke="#6b7280" tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                    }}
                    labelFormatter={(value) => `日期: ${value}`}
                  />
                  <Legend />
                  <Bar dataKey="buys" fill="#10b981" name="买入" />
                  <Bar dataKey="sells" fill="#ef4444" name="卖出" />
                  {chartData.dailyActivity.some(d => d.holds > 0) && (
                    <Bar dataKey="holds" fill="#6b7280" name="持有" />
                  )}
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-8 text-text-secondary">
                <Activity className="w-12 h-12 mx-auto mb-2 opacity-30" />
                <p>暂无交易活动数据</p>
              </div>
            )}
          </Card>

          {/* Cumulative Returns Chart */}
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <PieChart className="w-5 h-5 text-primary-500" />
              <h2 className="text-lg font-semibold text-text-primary">累计收益走势</h2>
            </div>
            {chartData.cumulativeReturns.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData.cumulativeReturns}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    stroke="#6b7280"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => {
                      const date = new Date(value);
                      return `${date.getMonth() + 1}/${date.getDate()}`;
                    }}
                  />
                  <YAxis
                    stroke="#6b7280"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `${value.toFixed(1)}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                    }}
                    labelFormatter={(value) => `日期: ${value}`}
                    formatter={(value: any, name: string) => {
                      const num = typeof value === 'number' ? value : parseFloat(value);
                      return [
                        `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`,
                        name === 'cumulativeReturn' ? '累计收益' : '单次收益',
                      ];
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="cumulativeReturn"
                    stroke="#0ea5e9"
                    strokeWidth={2}
                    dot={{ fill: '#0ea5e9', r: 4 }}
                    name="累计收益"
                  />
                  <Line
                    type="monotone"
                    dataKey="singleReturn"
                    stroke="#8b5cf6"
                    strokeWidth={1}
                    dot={{ fill: '#8b5cf6', r: 2 }}
                    name="单次收益"
                    strokeDasharray="5 5"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-8 text-text-secondary">
                <PieChart className="w-12 h-12 mx-auto mb-2 opacity-30" />
                <p>暂无收益数据</p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
            <Filter className="w-5 h-5" />
            筛选条件
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            {showFilters ? '收起' : '展开'}
          </Button>
        </div>

        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                股票代码
              </label>
              <Input
                type="text"
                placeholder="000001.SZ"
                value={searchSymbol}
                onChange={(e) => setSearchSymbol(e.target.value)}
                icon={<Search className="w-4 h-4" />}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                成功状态
              </label>
              <select
                className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                value={filterSuccess === undefined ? '' : filterSuccess.toString()}
                onChange={(e) =>
                  setFilterSuccess(
                    e.target.value === '' ? undefined : e.target.value === 'true'
                  )
                }
              >
                <option value="">全部</option>
                <option value="true">成功</option>
                <option value="false">失败</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                起始日期
              </label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                结束日期
              </label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
          </div>
        )}

        {showFilters && (searchSymbol || filterSuccess !== undefined || dateFrom || dateTo) && (
          <div className="mt-4 flex justify-end">
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <X className="w-4 h-4 mr-2" />
              清空筛选
            </Button>
          </div>
        )}
      </Card>

      {/* Episodes Table */}
      <Card className="p-4">
        <h2 className="text-lg font-semibold text-text-primary mb-4">
          Episodes 列表 ({episodes?.length || 0})
        </h2>

        {episodesLoading ? (
          <Loading />
        ) : episodes && episodes.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                    日期
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                    股票
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                    价格
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-text-secondary">
                    操作
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                    收益
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                    持仓天数
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-text-secondary">
                    状态
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody>
                {episodes.map((episode) => (
                  <tr
                    key={episode.episode_id}
                    className="border-b border-border hover:bg-surface-hover transition-colors"
                  >
                    <td className="py-3 px-4 text-sm text-text-primary">{episode.date}</td>
                    <td className="py-3 px-4 text-sm font-medium text-text-primary">
                      {episode.symbol}
                    </td>
                    <td className="py-3 px-4 text-sm text-text-primary text-right">
                      ¥{episode.price.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-sm text-center">
                      <span
                        className={`inline-block px-2 py-1 rounded text-xs ${
                          episode.action === 'buy' || episode.action === '买入'
                            ? 'bg-profit/10 text-profit'
                            : episode.action === 'sell' || episode.action === '卖出'
                            ? 'bg-loss/10 text-loss'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {episode.action || '-'}
                      </span>
                    </td>
                    <td
                      className={`py-3 px-4 text-sm font-medium text-right ${
                        (episode.percentage_return || 0) >= 0 ? 'text-profit' : 'text-loss'
                      }`}
                    >
                      {episode.percentage_return !== null &&
                      episode.percentage_return !== undefined
                        ? `${episode.percentage_return >= 0 ? '+' : ''}${(
                            episode.percentage_return * 100
                          ).toFixed(2)}%`
                        : '-'}
                    </td>
                    <td className="py-3 px-4 text-sm text-text-primary text-right">
                      {episode.holding_period_days || '-'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {episode.success !== null && episode.success !== undefined ? (
                        <span
                          className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                            episode.success
                              ? 'bg-profit/10 text-profit'
                              : 'bg-loss/10 text-loss'
                          }`}
                        >
                          {episode.success ? '成功' : '失败'}
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setSelectedEpisode(episode.episode_id)}
                          className="p-1 hover:bg-surface-hover rounded transition-colors"
                          title="查看详情"
                        >
                          <Eye className="w-4 h-4 text-primary-500" />
                        </button>
                        <button
                          onClick={() => handleDelete(episode.episode_id)}
                          className="p-1 hover:bg-surface-hover rounded transition-colors"
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4 text-loss" />
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
            <Database className="w-16 h-16 mx-auto mb-4 opacity-30" />
            <p>暂无Episodes记录</p>
          </div>
        )}
      </Card>

      {/* Episode Detail Modal */}
      {selectedEpisode && episodeDetail && !detailLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-text-primary">Episode 详情</h2>
                <button
                  onClick={() => setSelectedEpisode(null)}
                  className="p-2 hover:bg-surface-hover rounded transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="space-y-6">
                {/* Basic Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-text-secondary">Episode ID</p>
                    <p className="text-lg font-medium text-text-primary mt-1">
                      {episodeDetail.episode_id}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-text-secondary">日期</p>
                    <p className="text-lg font-medium text-text-primary mt-1">
                      {episodeDetail.date}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-text-secondary">股票代码</p>
                    <p className="text-lg font-medium text-text-primary mt-1">
                      {episodeDetail.symbol}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-text-secondary">模式</p>
                    <p className="text-lg font-medium text-text-primary mt-1">
                      {episodeDetail.mode}
                    </p>
                  </div>
                </div>

                {/* Outcome */}
                {episodeDetail.outcome && (
                  <div className="border border-border rounded-lg p-4">
                    <h3 className="font-semibold text-text-primary mb-3">交易结果</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-text-secondary">操作</p>
                        <p className="font-medium text-text-primary mt-1">
                          {episodeDetail.outcome.action || '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-text-secondary">入场价</p>
                        <p className="font-medium text-text-primary mt-1">
                          {episodeDetail.outcome.entry_price
                            ? `¥${episodeDetail.outcome.entry_price.toFixed(2)}`
                            : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-text-secondary">出场价</p>
                        <p className="font-medium text-text-primary mt-1">
                          {episodeDetail.outcome.exit_price
                            ? `¥${episodeDetail.outcome.exit_price.toFixed(2)}`
                            : '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-text-secondary">收益率</p>
                        <p
                          className={`font-medium mt-1 ${
                            (episodeDetail.outcome.percentage_return || 0) >= 0
                              ? 'text-profit'
                              : 'text-loss'
                          }`}
                        >
                          {episodeDetail.outcome.percentage_return !== null &&
                          episodeDetail.outcome.percentage_return !== undefined
                            ? `${episodeDetail.outcome.percentage_return >= 0 ? '+' : ''}${(
                                episodeDetail.outcome.percentage_return * 100
                              ).toFixed(2)}%`
                            : '-'}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Lesson */}
                {episodeDetail.lesson && (
                  <div className="border border-border rounded-lg p-4">
                    <h3 className="font-semibold text-text-primary mb-4">经验总结</h3>
                    <div className="prose prose-sm max-w-none text-text-primary">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {episodeDetail.lesson}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  <Button
                    variant="primary"
                    onClick={() => {
                      setEditingEpisode(episodeDetail);
                      setSelectedEpisode(null);
                    }}
                  >
                    <Edit2 className="w-4 h-4 mr-2" />
                    编辑
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => {
                      handleDelete(episodeDetail.episode_id);
                    }}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    删除
                  </Button>
                  <Button variant="ghost" onClick={() => setSelectedEpisode(null)}>
                    关闭
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingEpisode && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-text-primary">编辑 Episode</h2>
                <button
                  onClick={() => setEditingEpisode(null)}
                  className="p-2 hover:bg-surface-hover rounded transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    经验总结
                  </label>
                  <textarea
                    className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    rows={6}
                    value={editingEpisode.lesson || ''}
                    onChange={(e) =>
                      setEditingEpisode({ ...editingEpisode, lesson: e.target.value })
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    关键经验
                  </label>
                  <Input
                    type="text"
                    value={editingEpisode.key_lesson || ''}
                    onChange={(e) =>
                      setEditingEpisode({ ...editingEpisode, key_lesson: e.target.value })
                    }
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    成功状态
                  </label>
                  <select
                    className="w-full px-3 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                    value={
                      editingEpisode.success === null ? '' : editingEpisode.success.toString()
                    }
                    onChange={(e) =>
                      setEditingEpisode({
                        ...editingEpisode,
                        success: e.target.value === '' ? null : e.target.value === 'true',
                      })
                    }
                  >
                    <option value="">未设置</option>
                    <option value="true">成功</option>
                    <option value="false">失败</option>
                  </select>
                </div>

                <div className="flex gap-3 pt-4">
                  <Button
                    variant="primary"
                    onClick={handleUpdate}
                    disabled={updateMutation.isPending}
                  >
                    {updateMutation.isPending ? '保存中...' : '保存'}
                  </Button>
                  <Button variant="ghost" onClick={() => setEditingEpisode(null)}>
                    取消
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
