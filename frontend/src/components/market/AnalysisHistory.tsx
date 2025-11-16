import React, { useState, useEffect } from 'react';
import { History, RefreshCw, X, Loader2 } from 'lucide-react';
import { getTaskList, type AnalysisTask } from '@/api/agents';
import { AnalysisTaskCard } from './AnalysisTaskCard';

interface AnalysisHistoryProps {
  currentSymbol?: string;
  onSelectTask?: (task: AnalysisTask) => void;
  currentTaskId?: string | null;
}

/**
 * 分析历史记录组件
 *
 * 显示历史分析任务列表，支持：
 * - 查看所有历史任务
 * - 按股票代码筛选
 * - 按状态筛选
 * - 点击查看任务详情
 * - 刷新列表
 */
export function AnalysisHistory({
  currentSymbol,
  onSelectTask,
  currentTaskId,
}: AnalysisHistoryProps) {
  const [tasks, setTasks] = useState<AnalysisTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [showOnlyCurrentSymbol, setShowOnlyCurrentSymbol] = useState(false);

  const fetchTasks = async () => {
    setLoading(true);
    setError(null);

    try {
      const options: any = { limit: 20 };

      if (filterStatus !== 'all') {
        options.status = filterStatus;
      }

      if (showOnlyCurrentSymbol && currentSymbol) {
        options.symbol = currentSymbol;
      }

      const taskList = await getTaskList(options);
      setTasks(taskList);
    } catch (err) {
      console.error('获取任务列表失败:', err);
      setError(err instanceof Error ? err.message : '获取任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    fetchTasks();
  }, [filterStatus, showOnlyCurrentSymbol, currentSymbol]);

  // 自动刷新运行中的任务
  useEffect(() => {
    const hasRunningTasks = tasks.some(
      (t) => t.status === 'running' || t.status === 'pending'
    );

    if (!hasRunningTasks) return;

    const interval = setInterval(() => {
      fetchTasks();
    }, 5000); // 每5秒刷新一次

    return () => clearInterval(interval);
  }, [tasks]);

  const runningTasks = tasks.filter((t) => t.status === 'running' || t.status === 'pending');
  const completedTasks = tasks.filter((t) => t.status === 'completed');
  const failedTasks = tasks.filter((t) => t.status === 'failed' || t.status === 'cancelled');

  return (
    <div className="flex flex-col h-full bg-gray-50 rounded-lg border border-gray-200">
      {/* 标题栏 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white rounded-t-lg">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-gray-600" />
          <h3 className="font-semibold text-gray-800">分析历史</h3>
          {tasks.length > 0 && (
            <span className="text-xs text-gray-500">({tasks.length})</span>
          )}
        </div>
        <button
          onClick={fetchTasks}
          disabled={loading}
          className="p-1.5 rounded hover:bg-gray-100 transition-colors disabled:opacity-50"
          title="刷新列表"
        >
          <RefreshCw className={`w-4 h-4 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* 筛选选项 */}
      <div className="p-3 border-b border-gray-200 bg-white space-y-2">
        {/* 状态筛选 */}
        <div className="flex gap-2 flex-wrap">
          {[
            { value: 'all', label: '全部' },
            { value: 'running', label: '进行中' },
            { value: 'completed', label: '已完成' },
            { value: 'failed', label: '失败' },
          ].map((option) => (
            <button
              key={option.value}
              onClick={() => setFilterStatus(option.value)}
              className={`
                px-3 py-1 rounded text-xs font-medium transition-colors
                ${
                  filterStatus === option.value
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }
              `}
            >
              {option.label}
            </button>
          ))}
        </div>

        {/* 当前股票筛选 */}
        {currentSymbol && (
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={showOnlyCurrentSymbol}
              onChange={(e) => setShowOnlyCurrentSymbol(e.target.checked)}
              className="rounded border-gray-300"
            />
            <span>仅显示 {currentSymbol}</span>
          </label>
        )}
      </div>

      {/* 任务列表 */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {loading && tasks.length === 0 ? (
          <div className="flex items-center justify-center h-32">
            <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-32 text-center">
            <X className="w-8 h-8 text-red-400 mb-2" />
            <p className="text-sm text-red-600">{error}</p>
            <button
              onClick={fetchTasks}
              className="mt-2 text-xs text-blue-600 hover:underline"
            >
              重试
            </button>
          </div>
        ) : tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-center">
            <History className="w-8 h-8 text-gray-300 mb-2" />
            <p className="text-sm text-gray-500">暂无分析记录</p>
          </div>
        ) : (
          <>
            {/* 运行中的任务 */}
            {runningTasks.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 mb-2 flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  运行中 ({runningTasks.length})
                </h4>
                <div className="space-y-2">
                  {runningTasks.map((task) => (
                    <AnalysisTaskCard
                      key={task.task_id}
                      task={task}
                      onClick={() => onSelectTask?.(task)}
                      isActive={task.task_id === currentTaskId}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* 已完成的任务 */}
            {completedTasks.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 mb-2">
                  已完成 ({completedTasks.length})
                </h4>
                <div className="space-y-2">
                  {completedTasks.map((task) => (
                    <AnalysisTaskCard
                      key={task.task_id}
                      task={task}
                      onClick={() => onSelectTask?.(task)}
                      isActive={task.task_id === currentTaskId}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* 失败的任务 */}
            {failedTasks.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 mb-2">
                  失败 ({failedTasks.length})
                </h4>
                <div className="space-y-2">
                  {failedTasks.map((task) => (
                    <AnalysisTaskCard
                      key={task.task_id}
                      task={task}
                      onClick={() => onSelectTask?.(task)}
                      isActive={task.task_id === currentTaskId}
                    />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
