import { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';
import type { BarData } from '@/types/market';

interface CandlestickChartProps {
  data: BarData[];
  height?: number;
}

export function CandlestickChart({ data, height }: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candlestickSeriesRef = useRef<any>(null);

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
      }
    };
  }, [data, height]);

  return (
    <div className="relative h-full w-full flex flex-col">
      <div ref={chartContainerRef} className="w-full flex-1" />
      <div className="mt-2 flex items-center justify-center gap-4 text-xs text-text-secondary">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-loss rounded"></div>
          <span>上涨</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-profit rounded"></div>
          <span>下跌</span>
        </div>
      </div>
    </div>
  );
}
