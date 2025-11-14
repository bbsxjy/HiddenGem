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
  Scatter,
  ComposedChart,
} from 'recharts';
import type { EquityCurvePoint } from '@/types/strategy';

interface Trade {
  date: string;
  ticker: string;
  action: string;
  shares: number;
  price: number;
  cost?: number;
  revenue?: number;
  commission: number;
  total_cost?: number;
  total_revenue?: number;
}

interface EquityCurveChartProps {
  data: EquityCurvePoint[];
  initialCapital: number;
  trades?: Trade[];
  className?: string;
}

export function EquityCurveChart({
  data,
  initialCapital,
  trades = [],
  className = '',
}: EquityCurveChartProps) {
  // 格式化数据并合并交易点
  const { chartData, tradePoints } = useMemo(() => {
    // 🔍 Debug: 检查原始数据
    console.log('🔍 EquityCurveChart - Raw data:', data);
    console.log('🔍 EquityCurveChart - Trades:', trades);

    const formattedData = data.map((point) => ({
      date: new Date(point.date).toLocaleDateString('zh-CN', {
        month: 'numeric',
        day: 'numeric',
      }),
      fullDate: point.date,
      value: point.value,
      return_pct: ((point.value - initialCapital) / initialCapital) * 100,
    }));

    // 将交易点映射到资金曲线上
    const tradeMarkers = trades.map((trade) => {
      // 找到对应日期的资金值
      const matchingPoint = data.find(p => p.date === trade.date);
      if (!matchingPoint) {
        console.warn(`⚠️ No matching equity point for trade on ${trade.date}`);
        return null;
      }

      const formattedDate = new Date(trade.date).toLocaleDateString('zh-CN', {
        month: 'numeric',
        day: 'numeric',
      });

      return {
        date: formattedDate,
        fullDate: trade.date,
        value: matchingPoint.value,
        return_pct: ((matchingPoint.value - initialCapital) / initialCapital) * 100, // 🆕 添加return_pct
        action: trade.action,
        ticker: trade.ticker,
        shares: trade.shares,
        price: trade.price,
        cost: trade.cost,
        revenue: trade.revenue,
        commission: trade.commission,
        total_cost: trade.total_cost,
        total_revenue: trade.total_revenue,
      };
    }).filter(Boolean); // 过滤掉null值

    console.log('🔍 EquityCurveChart - Formatted chartData:', formattedData);
    console.log('🔍 EquityCurveChart - Trade markers:', tradeMarkers);

    return { chartData: formattedData, tradePoints: tradeMarkers };
  }, [data, trades, initialCapital]);

  // 计算最大值和最小值用于Y轴范围
  const { minValue, maxValue } = useMemo(() => {
    if (chartData.length === 0) {
      return { minValue: initialCapital * 0.9, maxValue: initialCapital * 1.1 };
    }

    const values = chartData.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.1 || initialCapital * 0.1;

    console.log('🔍 Y-axis calculation:', {
      values: values.length,
      min,
      max,
      padding,
      finalMin: Math.max(0, min - padding),
      finalMax: max + padding
    });

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
      // Recharts会返回所有数据点，我们需要找到正确的数据
      // 如果是Scatter点，它会有action字段
      let data = payload[0].payload;

      // 尝试从payload中找到有action的数据（交易点）
      const tradePayload = payload.find((p: any) => p.payload && p.payload.action);
      if (tradePayload) {
        data = tradePayload.payload;
      }

      const isProfit = data.value >= initialCapital;
      const isTrade = data.action !== undefined;

      console.log('🔍 Tooltip data:', data, 'isTrade:', isTrade);

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

            {/* 🆕 交易详情 */}
            {isTrade && (
              <>
                <div className="border-t border-gray-100 my-2"></div>
                <div className="flex justify-between gap-4">
                  <span className="text-sm font-semibold text-text-primary">
                    {data.action.includes('BUY') ? '📈 买入' : '📉 卖出'}
                  </span>
                  <span className="text-sm font-medium text-primary-600">
                    {data.ticker}
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-xs text-text-secondary">价格:</span>
                  <span className="text-xs font-medium text-text-primary">
                    ¥{data.price?.toFixed(2) || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-xs text-text-secondary">数量:</span>
                  <span className="text-xs font-medium text-text-primary">
                    {data.shares?.toLocaleString() || 'N/A'} 股
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-xs text-text-secondary">金额:</span>
                  <span className="text-xs font-medium text-text-primary">
                    {data.total_cost
                      ? `¥${data.total_cost.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
                      : data.total_revenue
                      ? `¥${data.total_revenue.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
                      : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-xs text-text-secondary">手续费:</span>
                  <span className="text-xs text-loss">
                    ¥{data.commission?.toFixed(2) || 'N/A'}
                  </span>
                </div>
              </>
            )}
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
        <ComposedChart
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

          {/* 买卖点标记 */}
          {tradePoints.length > 0 && (
            <Scatter
              data={tradePoints}
              dataKey="value"
              name="交易点"
              shape={(props: any) => {
                const { cx, cy, payload } = props;
                if (!payload || !payload.action) return null;

                const isBuy = payload.action.includes('BUY');
                const color = isBuy ? '#16a34a' : '#dc2626';

                return (
                  <g>
                    {/* 三角形标记 */}
                    <path
                      d={isBuy
                        ? `M ${cx} ${cy - 8} L ${cx - 6} ${cy + 4} L ${cx + 6} ${cy + 4} Z`  // 向上三角
                        : `M ${cx} ${cy + 8} L ${cx - 6} ${cy - 4} L ${cx + 6} ${cy - 4} Z`  // 向下三角
                      }
                      fill={color}
                      stroke="#ffffff"
                      strokeWidth={1.5}
                    />
                  </g>
                );
              }}
            />
          )}
        </ComposedChart>
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
