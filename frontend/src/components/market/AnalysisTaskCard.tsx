import React from 'react';
import { Clock, CheckCircle, XCircle, Loader2, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { AnalysisTask } from '@/api/agents';

interface AnalysisTaskCardProps {
  task: AnalysisTask;
  onClick?: () => void;
  isActive?: boolean;
}

/**
 * 分析任务卡片组件
 *
 * 显示单个分析任务的概要信息，包括：
 * - 股票代码
 * - 任务状态（运行中/已完成/失败）
 * - 进度百分比
 * - 创建时间
 * - 分析结果摘要（如果已完成）
 */
export function AnalysisTaskCard({ task, onClick, isActive = false }: AnalysisTaskCardProps) {
  const getStatusIcon = () => {
    switch (task.status) {
      case 'running':
      case 'pending':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
      case 'cancelled':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = () => {
    switch (task.status) {
      case 'pending':
        return '等待中';
      case 'running':
        return '分析中';
      case 'completed':
        return '已完成';
      case 'failed':
        return '失败';
      case 'cancelled':
        return '已取消';
      default:
        return '未知';
    }
  };

  const getStatusColor = () => {
    switch (task.status) {
      case 'running':
      case 'pending':
        return 'bg-blue-100 text-blue-700';
      case 'completed':
        return 'bg-green-100 text-green-700';
      case 'failed':
      case 'cancelled':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const getDirectionIcon = () => {
    if (!task.result?.llm_analysis?.recommended_direction) return null;

    const direction = task.result.llm_analysis.recommended_direction;
    switch (direction) {
      case 'long':
        return <TrendingUp className="w-4 h-4 text-green-500" />;
      case 'short':
        return <TrendingDown className="w-4 h-4 text-red-500" />;
      case 'hold':
        return <Minus className="w-4 h-4 text-gray-500" />;
      default:
        return null;
    }
  };

  const getDirectionText = () => {
    if (!task.result?.llm_analysis?.recommended_direction) return null;

    const direction = task.result.llm_analysis.recommended_direction;
    switch (direction) {
      case 'long':
        return '看多';
      case 'short':
        return '看空';
      case 'hold':
        return '持有';
      default:
        return direction;
    }
  };

  const formatTime = (timestamp: string | null) => {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;

    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div
      className={`
        border rounded-lg p-4 cursor-pointer transition-all
        hover:shadow-md hover:border-blue-300
        ${isActive ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'}
      `}
      onClick={onClick}
    >
      {/* 标题行 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-lg text-gray-800">{task.symbol}</span>
          {getDirectionIcon()}
          {getDirectionText() && (
            <span className="text-sm text-gray-600">{getDirectionText()}</span>
          )}
        </div>
        {getStatusIcon()}
      </div>

      {/* 状态标签和进度 */}
      <div className="flex items-center gap-2 mb-2">
        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor()}`}>
          {getStatusText()}
        </span>
        {(task.status === 'running' || task.status === 'pending') && (
          <span className="text-xs text-gray-500">{task.progress}%</span>
        )}
      </div>

      {/* 进度条 */}
      {(task.status === 'running' || task.status === 'pending') && (
        <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${task.progress}%` }}
          />
        </div>
      )}

      {/* 时间信息 */}
      <div className="flex items-center gap-1 text-xs text-gray-500">
        <Clock className="w-3 h-3" />
        <span>{formatTime(task.created_at)}</span>
      </div>

      {/* 结果摘要（如果已完成） */}
      {task.status === 'completed' && task.result?.llm_analysis && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          <p className="text-xs text-gray-600 line-clamp-2">
            {task.result.llm_analysis.reasoning?.slice(0, 80) || '无分析摘要'}
            {(task.result.llm_analysis.reasoning?.length || 0) > 80 && '...'}
          </p>
        </div>
      )}

      {/* 错误信息 */}
      {task.status === 'failed' && task.error && (
        <div className="mt-2 pt-2 border-t border-red-200">
          <p className="text-xs text-red-600 line-clamp-2">{task.error}</p>
        </div>
      )}
    </div>
  );
}
