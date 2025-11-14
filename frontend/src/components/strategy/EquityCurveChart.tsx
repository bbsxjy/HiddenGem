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

interface EquityCurvePoint {
  date: string;
  value: number;
  daily_return?: number;
}

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
  // 🔍 调试：检查接收到的原始数据
  console.log('🔍 EquityCurveChart - 接收到的原始数据:', {
    dataLength: data?.length,
    firstPoint: data?.[0],
    lastPoint: data?.[data.length - 1],
    sampleDates: data?.slice(0, 5).map(d => d.date),
    sampleValues: data?.slice(0, 5).map(d => d.value),
    initialCapital,
  });

  // 处理数据：直接使用原始数据，不做复杂转换
  const { chartData, tradePoints, yAxisDomain } = useMemo(() => {
    if (!data || data.length === 0) {
      return { chartData: [], tradePoints: [], yAxisDomain: [initialCapital * 0.9, initialCapital * 1.1] };
    }

    // 简单映射：确保每个点都有必需的字段
    const mappedData = data.map((point) => ({
      date: point.date,  // 保持原始日期格式 "2025-01-02"
      value: point.value, // 账户总价值
      return_pct: ((point.value - initialCapital) / initialCapital) * 100,
    }));

    // 🔍 调试：检查映射后的数据
    console.log('🔍 mappedData sample:', {
      first: mappedData[0],
      last: mappedData[mappedData.length - 1],
      dateType: typeof mappedData[0]?.date,
      valueType: typeof mappedData[0]?.value,
      allDatesUnique: new Set(mappedData.map(d => d.date)).size === mappedData.length,
    });

    // 映射交易点
    const mappedTrades = trades.map((trade) => {
      const matchingPoint = data.find(p => p.date === trade.date);
      if (!matchingPoint) return null;

      return {
        date: trade.date,
        value: matchingPoint.value,
        return_pct: ((matchingPoint.value - initialCapital) / initialCapital) * 100,
        // 交易信息
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
    }).filter(Boolean);

    // 计算Y轴范围
    const values = mappedData.map(d => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.1 || initialCapital * 0.1;
    const domain = [
      Math.max(0, min - padding),
      max + padding
    ];

    // 🔍 调试：Y轴和最终数据
    console.log('🔍 Y-axis and final data:', {
      valueRange: { min, max },
      domain,
      chartDataLength: mappedData.length,
      tradePointsLength: mappedTrades.length,
    });

    return {
      chartData: mappedData,
      tradePoints: mappedTrades,
      yAxisDomain: domain
    };
  }, [data, trades, initialCapital]);

  // 格式化货币
  const formatCurrency = (value: number) => {
    return `¥${value.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`;
  };

  // 格式化收益率
  const formatReturn = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  // 格式化X轴日期显示
  const formatXAxisDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return `${date.getMonth() + 1}/${date.getDate()}`;
    } catch {
      return dateStr;
    }
  };

  // 自定义 Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;

    // 尝试找到交易点数据
    let data = payload[0].payload;
    const tradePayload = payload.find((p: any) => p.payload && p.payload.action);
    if (tradePayload) {
      data = tradePayload.payload;
    }

    const isProfit = data.value >= initialCapital;
    const isTrade = data.action !== undefined;

    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
        <p className="text-sm text-text-secondary mb-2">{data.date}</p>
        <div className="space-y-1">
          <div className="flex justify-between gap-4">
            <span className="text-sm text-text-secondary">资金:</span>
            <span className="text-sm font-medium text-text-primary">
              {formatCurrency(data.value)}
            </span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-sm text-text-secondary">收益率:</span>
            <span className={`text-sm font-medium ${isProfit ? 'text-profit' : 'text-loss'}`}>
              {formatReturn(data.return_pct || 0)}
            </span>
          </div>

          {/* 交易详情 */}
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
  };

  if (chartData.length === 0) {
    return (
      <div className={`${className} flex items-center justify-center h-64 bg-gray-50 rounded-lg`}>
        <p className="text-text-secondary text-sm">暂无资金曲线数据</p>
      </div>
    );
  }

  // 确定线条颜色
  const finalValue = chartData[chartData.length - 1]?.value || initialCapital;
  const lineColor = finalValue >= initialCapital ? '#16a34a' : '#dc2626';

  // 🔍 调试：渲染前的最终检查
  console.log('🔍 Before render:', {
    chartDataLength: chartData.length,
    hasData: chartData.length > 0,
    firstDate: chartData[0]?.date,
    lastDate: chartData[chartData.length - 1]?.date,
    firstValue: chartData[0]?.value,
    lastValue: chartData[chartData.length - 1]?.value,
    lineColor,
    yAxisDomain,
  });

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
            tickFormatter={formatXAxisDate}
          />
          <YAxis
            domain={yAxisDomain}
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
            dot={(props: any) => {
              const { cx, cy, payload } = props;

              // 检查这个日期是否有交易
              const trade = tradePoints.find(t => t.date === payload.date);
              if (!trade) return null;

              const isBuy = trade.action.includes('BUY');
              const color = isBuy ? '#16a34a' : '#dc2626';

              return (
                <g key={`trade-${payload.date}`}>
                  <path
                    d={isBuy
                      ? `M ${cx} ${cy - 8} L ${cx - 6} ${cy + 4} L ${cx + 6} ${cy + 4} Z`
                      : `M ${cx} ${cy + 8} L ${cx - 6} ${cy - 4} L ${cx + 6} ${cy - 4} Z`
                    }
                    fill={color}
                    stroke="#ffffff"
                    strokeWidth={1.5}
                  />
                </g>
              );
            }}
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
