import { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';
import type { BarData } from '@/types/market';

interface IndicatorData {
  time: number;
  value: number;
}

interface CandlestickChartProps {
  data: BarData[];
  height?: number;
  // 叠加指标
  showMA?: boolean;
  showBollingerBands?: boolean;
  maValues?: { ma5?: IndicatorData[]; ma20?: IndicatorData[]; ma60?: IndicatorData[] };
  bbValues?: { upper?: IndicatorData[]; middle?: IndicatorData[]; lower?: IndicatorData[] };
}

export function CandlestickChart({
  data,
  height,
  showMA = false,
  showBollingerBands = false,
  maValues,
  bbValues
}: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candlestickSeriesRef = useRef<any>(null);
  const maSeriesRef = useRef<{ ma5?: any; ma20?: any; ma60?: any }>({});
  const bbSeriesRef = useRef<{ upper?: any; middle?: any; lower?: any }>({});

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return;

    // Use a slight delay to ensure container has been laid out
    const initChart = () => {
      if (!chartContainerRef.current) return;

      // Use container height if height prop not provided
      const chartHeight = height || chartContainerRef.current.clientHeight || 400;

      // Create chart
      const chart = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: chartHeight,
        layout: {
          background: { color: '#ffffff' },
          textColor: '#333',
        },
        grid: {
          vertLines: { color: '#f0f0f0' },
          horzLines: { color: '#f0f0f0' },
        },
        timeScale: {
          borderColor: '#e0e0e0',
          timeVisible: true,
          secondsVisible: false,
        },
        rightPriceScale: {
          borderColor: '#e0e0e0',
        },
        crosshair: {
          mode: 0, // 0 = Normal (free movement), 1 = Magnet
          vertLine: {
            color: '#9598A1',
            width: 1,
            style: 2, // 2 = Dashed
            labelBackgroundColor: '#0ea5e9',
          },
          horzLine: {
            color: '#9598A1',
            width: 1,
            style: 2, // 2 = Dashed
            labelBackgroundColor: '#0ea5e9',
          },
        },
      });

      chartRef.current = chart;

      // Add candlestick series
      // A股颜色：红涨绿跌（与美股相反）
      const candlestickSeries = chart.addCandlestickSeries({
        upColor: '#dc2626',        // 上涨用红色
        downColor: '#16a34a',      // 下跌用绿色
        borderUpColor: '#dc2626',
        borderDownColor: '#16a34a',
        wickUpColor: '#dc2626',
        wickDownColor: '#16a34a',
      });

      candlestickSeriesRef.current = candlestickSeries;

      // Convert data to lightweight-charts format
      const chartData = data
        .map((bar) => {
          // Parse date - handle multiple formats
          let timestamp: number;

          if (typeof bar.date === 'number') {
            // Already a timestamp
            timestamp = bar.date;
          } else if (typeof bar.date === 'string') {
            // Parse date string - ensure proper format
            const parsedDate = new Date(bar.date.replace(/\s+/g, 'T')); // Handle space-separated datetime
            timestamp = parsedDate.getTime();
          } else {
            console.warn('Invalid date type:', typeof bar.date, bar.date);
            return null;
          }

          const timeInSeconds = Math.floor(timestamp / 1000);

          // Validate timestamp and OHLC values
          if (
            isNaN(timestamp) ||
            isNaN(timeInSeconds) ||
            timeInSeconds <= 0 ||
            !bar.open ||
            !bar.high ||
            !bar.low ||
            !bar.close ||
            bar.open <= 0 ||
            bar.high <= 0 ||
            bar.low <= 0 ||
            bar.close <= 0
          ) {
            console.warn('Invalid bar data:', bar, 'timestamp:', timeInSeconds);
            return null;
          }

          return {
            time: timeInSeconds as any, // Unix timestamp in seconds
            open: bar.open,
            high: bar.high,
            low: bar.low,
            close: bar.close,
          };
        })
        .filter((bar): bar is NonNullable<typeof bar> => bar !== null) // Remove invalid entries
        .sort((a, b) => a.time - b.time); // Sort by time ascending

      // Log the final data for debugging
      if (chartData.length > 0) {
        console.log('Chart data sample:', chartData.slice(0, 3), '...', chartData.slice(-3));
      } else {
        console.error('No valid chart data after filtering');
      }

      candlestickSeries.setData(chartData);

      // Add MA lines if enabled
      if (showMA && maValues) {
        if (maValues.ma5 && maValues.ma5.length > 0) {
          const ma5Series = chart.addLineSeries({
            color: '#22c55e',
            lineWidth: 2,
            title: 'MA5',
          });
          ma5Series.setData(maValues.ma5);
          maSeriesRef.current.ma5 = ma5Series;
        }

        if (maValues.ma20 && maValues.ma20.length > 0) {
          const ma20Series = chart.addLineSeries({
            color: '#f59e0b',
            lineWidth: 2,
            title: 'MA20',
          });
          ma20Series.setData(maValues.ma20);
          maSeriesRef.current.ma20 = ma20Series;
        }

        if (maValues.ma60 && maValues.ma60.length > 0) {
          const ma60Series = chart.addLineSeries({
            color: '#8b5cf6',
            lineWidth: 2,
            title: 'MA60',
          });
          ma60Series.setData(maValues.ma60);
          maSeriesRef.current.ma60 = ma60Series;
        }
      }

      // Add Bollinger Bands if enabled
      if (showBollingerBands && bbValues) {
        if (bbValues.upper && bbValues.upper.length > 0) {
          const upperSeries = chart.addLineSeries({
            color: '#ef4444',
            lineWidth: 1,
            lineStyle: 2, // Dashed
            title: 'BB上轨',
          });
          upperSeries.setData(bbValues.upper);
          bbSeriesRef.current.upper = upperSeries;
        }

        if (bbValues.middle && bbValues.middle.length > 0) {
          const middleSeries = chart.addLineSeries({
            color: '#9ca3af',
            lineWidth: 1,
            lineStyle: 2, // Dashed
            title: 'BB中轨',
          });
          middleSeries.setData(bbValues.middle);
          bbSeriesRef.current.middle = middleSeries;
        }

        if (bbValues.lower && bbValues.lower.length > 0) {
          const lowerSeries = chart.addLineSeries({
            color: '#10b981',
            lineWidth: 1,
            lineStyle: 2, // Dashed
            title: 'BB下轨',
          });
          lowerSeries.setData(bbValues.lower);
          bbSeriesRef.current.lower = lowerSeries;
        }
      }

      // Fit content
      chart.timeScale().fitContent();

      // Handle resize
      const handleResize = () => {
        if (chartContainerRef.current) {
          chart.applyOptions({
            width: chartContainerRef.current.clientWidth,
          });
        }
      };

      window.addEventListener('resize', handleResize);

      // Cleanup
      return () => {
        window.removeEventListener('resize', handleResize);
        chart.remove();
        chartRef.current = null;
        candlestickSeriesRef.current = null;
        maSeriesRef.current = {};
        bbSeriesRef.current = {};
      };
    };

    // Use requestAnimationFrame to ensure layout is complete
    const rafId = requestAnimationFrame(initChart);

    return () => {
      cancelAnimationFrame(rafId);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        candlestickSeriesRef.current = null;
        maSeriesRef.current = {};
        bbSeriesRef.current = {};
      }
    };
  }, [data, height, showMA, showBollingerBands, maValues, bbValues]);

  return (
    <div className="relative h-full w-full flex flex-col">
      <div ref={chartContainerRef} className="w-full flex-1" />
      <div className="mt-2 flex flex-wrap items-center justify-center gap-3 text-xs text-text-secondary">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-loss rounded"></div>
          <span>上涨</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-profit rounded"></div>
          <span>下跌</span>
        </div>
        {showMA && (
          <>
            <div className="w-px h-3 bg-gray-300"></div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-green-500"></div>
              <span>MA5</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-orange-500"></div>
              <span>MA20</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-purple-500"></div>
              <span>MA60</span>
            </div>
          </>
        )}
        {showBollingerBands && (
          <>
            <div className="w-px h-3 bg-gray-300"></div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-red-500 border-dashed"></div>
              <span>BB上轨</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-gray-400 border-dashed"></div>
              <span>BB中轨</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-0.5 bg-green-500 border-dashed"></div>
              <span>BB下轨</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
