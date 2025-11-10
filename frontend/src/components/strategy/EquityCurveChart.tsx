import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { EquityCurvePoint } from '@/types/strategy';

interface EquityCurveChartProps {
  data: EquityCurvePoint[];
  initialCapital: number;
  className?: string;
}

export function EquityCurveChart({
  data,
  initialCapital,
  className = '',
}: EquityCurveChartProps) {
  // 格式化数据
  const chartData = useMemo(() => {
    return data.map((point) => ({
      date: new Date(point.date).toLocaleDateString('zh-CN', {
        month: 'numeric',
        day: 'numeric',
      }),
      fullDate: point.date,
      value: point.value,
      return_pct: ((point.value - initialCapital) / initialCapital) * 100,
    }));
  }, [data, initialCapital]);

  // 计算最大值和最小值用于Y轴范围
  const { minValue, maxValue } = useMemo(() => {
    if (chartData.length === 0) {
      return { minValue: initialCapital * 0.9, maxValue: initialCapital * 1.1 };
    }

    const values = chartData.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.1 || initialCapital * 0.1;

    return {
      minValue: Math.max(0, min - padding),
      maxValue: max + padding,
    };
  }, [chartData, initialCapital]);

  // 格式化数字为货币
  const formatCurrency = (value: number) => {
    return `¥${value.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`;
  };

  // 格式化收益率
  const formatReturn = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  // 自定义 Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const isProfit = data.value >= initialCapital;

      return (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <p className="text-sm text-text-secondary mb-2">{data.fullDate}</p>
          <div className="space-y-1">
            <div className="flex justify-between gap-4">
              <span className="text-sm text-text-secondary">资金:</span>
              <span className="text-sm font-medium text-text-primary">
                {formatCurrency(data.value)}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-sm text-text-secondary">收益率:</span>
              <span
                className={`text-sm font-medium ${
                  isProfit ? 'text-profit' : 'text-loss'
                }`}
              >
                {formatReturn(data.return_pct)}
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  if (chartData.length === 0) {
    return (
      <div className={`${className} flex items-center justify-center h-64 bg-gray-50 rounded-lg`}>
        <p className="text-text-secondary text-sm">暂无资金曲线数据</p>
      </div>
    );
  }

  // 确定线条颜色（基于最终收益）
  const finalValue = chartData[chartData.length - 1]?.value || initialCapital;
  const lineColor = finalValue >= initialCapital ? '#16a34a' : '#dc2626';

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: '#6b7280' }}
            stroke="#9ca3af"
          />
          <YAxis
            domain={[minValue, maxValue]}
            tick={{ fontSize: 12, fill: '#6b7280' }}
            stroke="#9ca3af"
            tickFormatter={formatCurrency}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
            iconType="line"
          />

          {/* 初始资金参考线 */}
          <ReferenceLine
            y={initialCapital}
            stroke="#9ca3af"
            strokeDasharray="5 5"
            label={{
              value: '初始资金',
              position: 'right',
              fill: '#6b7280',
              fontSize: 11,
            }}
          />

          {/* 资金曲线 */}
          <Line
            type="monotone"
            dataKey="value"
            stroke={lineColor}
            strokeWidth={2}
            dot={false}
            name="账户价值"
            activeDot={{ r: 6, strokeWidth: 0 }}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* 图例说明 */}
      <div className="mt-4 flex items-center justify-center gap-6 text-xs text-text-secondary">
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-profit"></div>
          <span>盈利</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-loss"></div>
          <span>亏损</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-gray-400" style={{ borderTop: '1px dashed #9ca3af' }}></div>
          <span>初始资金</span>
        </div>
      </div>
    </div>
  );
}
