import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { Input } from '@/components/common/Input';
import { CandlestickChart } from '@/components/market/CandlestickChart';
import { getQuote, getBars, getTechnicalIndicators, getStockInfo } from '@/api/market';
import { formatProfitLoss, formatPercentage, getChangeColor, detectMarketType } from '@/utils/format';
import { Search, TrendingUp, TrendingDown, Building2, MapPin, Calendar, AlertCircle, RefreshCw } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export function Market() {
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [searchInput, setSearchInput] = useState('');

  // Fetch real-time quote
  const { data: quote, isLoading: quoteLoading, error: quoteError, refetch: refetchQuote } = useQuery({
    queryKey: ['quote', selectedSymbol],
    queryFn: () => getQuote(selectedSymbol),
    enabled: !!selectedSymbol,
    retry: 1,
  });

  // Fetch stock info
  const { data: stockInfo, isLoading: stockInfoLoading, error: stockInfoError, refetch: refetchStockInfo } = useQuery({
    queryKey: ['stockInfo', selectedSymbol],
    queryFn: () => getStockInfo(selectedSymbol),
    enabled: !!selectedSymbol,
    retry: 1,
  });

  // Fetch historical bars
  const { data: barsData, isLoading: barsLoading, error: barsError, refetch: refetchBars } = useQuery({
    queryKey: ['bars', selectedSymbol],
    queryFn: () => getBars(selectedSymbol, { days: 60 }),
    enabled: !!selectedSymbol,
    retry: 1,
  });

  // Fetch technical indicators
  const { data: indicators, isLoading: indicatorsLoading, error: indicatorsError, refetch: refetchIndicators } = useQuery({
    queryKey: ['indicators', selectedSymbol],
    queryFn: () => getTechnicalIndicators(selectedSymbol, 90),
    enabled: !!selectedSymbol,
    retry: 1,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setSelectedSymbol(searchInput.trim());
    }
  };

  const handleRefreshAll = () => {
    refetchQuote();
    refetchStockInfo();
    refetchBars();
    refetchIndicators();
  };

  const isUp = (quote?.change_pct || 0) >= 0;
  const marketType = detectMarketType(selectedSymbol);

  // 判断板块
  const getBoardType = (symbol: string) => {
    if (symbol.startsWith('688')) return { name: '科创板', color: 'bg-orange-100 text-orange-700' };
    if (symbol.startsWith('300')) return { name: '创业板', color: 'bg-purple-100 text-purple-700' };
    return { name: '主板', color: 'bg-blue-100 text-blue-700' };
  };

  // 技术指标评估
  const evaluateRSI = (rsi?: number) => {
    if (!rsi) return { text: 'N/A', color: 'text-gray-500', desc: '' };
    if (rsi > 70) return { text: rsi.toFixed(2), color: 'text-loss', desc: '超买' };
    if (rsi < 30) return { text: rsi.toFixed(2), color: 'text-profit', desc: '超卖' };
    return { text: rsi.toFixed(2), color: 'text-text-primary', desc: '中性' };
  };

  const evaluateMACD = (macd?: number, signal?: number) => {
    if (!macd || !signal) return { text: 'N/A', color: 'text-gray-500', desc: '' };
    const diff = macd - signal;
    if (Math.abs(diff) < 0.01) return { text: macd.toFixed(3), color: 'text-text-primary', desc: '持平' };
    if (diff > 0) return { text: macd.toFixed(3), color: 'text-profit', desc: '金叉' };
    return { text: macd.toFixed(3), color: 'text-loss', desc: '死叉' };
  };

  const evaluateKDJ = (k?: number, d?: number) => {
    if (!k || !d) return { text: 'N/A', color: 'text-gray-500', desc: '' };
    if (k > 80 && d > 80) return { text: k.toFixed(2), color: 'text-loss', desc: '超买' };
    if (k < 20 && d < 20) return { text: k.toFixed(2), color: 'text-profit', desc: '超卖' };
    if (k > d) return { text: k.toFixed(2), color: 'text-profit', desc: '向上' };
    return { text: k.toFixed(2), color: 'text-loss', desc: '向下' };
  };

  const evaluatePrice = (price?: number, ma5?: number, ma20?: number, ma60?: number) => {
    if (!price) return { desc: '暂无数据', color: 'text-gray-500' };
    const positions = [];
    if (ma5 && price > ma5) positions.push('MA5');
    if (ma20 && price > ma20) positions.push('MA20');
    if (ma60 && price > ma60) positions.push('MA60');

    if (positions.length === 3) return { desc: '多头排列', color: 'text-profit' };
    if (positions.length === 0) return { desc: '空头排列', color: 'text-loss' };
    return { desc: `站上${positions.join('/')}`, color: 'text-text-primary' };
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">个股查询</h1>
        <p className="text-text-secondary mt-1">A股市场实时数据和分析</p>
      </div>

      {/* Search Bar */}
      <Card padding="md">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2">
          <div className="flex-1">
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="输入股票代码（如 000001, 600519, 300750）"
              leftIcon={<Search size={18} />}
            />
          </div>
          <button
            type="submit"
            className="px-4 sm:px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium text-sm sm:text-base"
          >
            查询
          </button>
        </form>
      </Card>

      {/* 如果没有选择股票，显示提示 */}
      {!selectedSymbol ? (
        <Card padding="md">
          <div className="text-center py-12">
            <Search className="mx-auto h-16 w-16 text-gray-300 mb-4" />
            <p className="text-lg text-text-primary font-semibold mb-2">请输入股票代码开始查询</p>
            <p className="text-sm text-text-secondary mb-6">
              例如：000001（平安银行）、600519（贵州茅台）、300750（宁德时代）
            </p>

            <div className="max-w-xl mx-auto">
              <p className="text-sm font-medium text-text-secondary mb-3">快速测试：</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {[
                  { code: '000001', name: '平安银行' },
                  { code: '000002', name: '万科A' },
                  { code: '600519', name: '贵州茅台' },
                  { code: '600036', name: '招商银行' },
                  { code: '000858', name: '五粮液' },
                  { code: '300750', name: '宁德时代' },
                ].map(stock => (
                  <button
                    key={stock.code}
                    onClick={() => {
                      setSearchInput(stock.code);
                      setSelectedSymbol(stock.code);
                    }}
                    className="text-left px-3 py-2 bg-white border border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors"
                  >
                    <div className="text-sm font-semibold text-text-primary">{stock.code}</div>
                    <div className="text-xs text-text-secondary">{stock.name}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Card>
      ) : (
        <>
          {/* Stock Info and Quote */}
          <Card padding="md">
            {(quoteError || stockInfoError) && (
              <div className="mb-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="h-5 w-5 text-loss" />
                    <span className="text-sm font-semibold text-red-900">无法获取行情数据</span>
                  </div>
                  <p className="text-xs font-mono text-red-700 bg-red-100 p-2 rounded overflow-x-auto">
                    {quoteError instanceof Error ? quoteError.message : stockInfoError instanceof Error ? stockInfoError.message : '未知错误'}
                  </p>
                  <div className="mt-3">
                    <button
                      onClick={handleRefreshAll}
                      className="text-xs px-3 py-1.5 bg-primary-500 text-white rounded hover:bg-primary-600 transition-colors"
                    >
                      刷新数据
                    </button>
                  </div>
                </div>
              </div>
            )}

            {(quoteLoading || stockInfoLoading) && (
              <div className="mb-4 flex items-center justify-center py-4">
                <Loading size="sm" text="加载行情数据..." />
              </div>
            )}

            {quote && stockInfo && !quoteLoading && !stockInfoLoading ? (
              <>
                {/* 股票基本信息 */}
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-4">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-3">
                      <h2 className="text-xl sm:text-2xl md:text-3xl font-bold text-text-primary">{stockInfo.name}</h2>
                      <span className="text-base sm:text-lg md:text-xl text-text-secondary">{quote.symbol}</span>
                      <span className={`px-2 sm:px-3 py-0.5 sm:py-1 rounded-full text-xs sm:text-sm font-medium ${getBoardType(quote.symbol).color}`}>
                        {getBoardType(quote.symbol).name}
                      </span>
                    </div>
                    {/* 行业信息 - 移动端垂直堆叠 */}
                    <div className="flex flex-col sm:flex-row sm:gap-4 md:gap-6 text-xs sm:text-sm text-text-secondary space-y-1 sm:space-y-0">
                      <div className="flex items-center gap-1">
                        <Building2 size={14} className="sm:hidden" />
                        <Building2 size={16} className="hidden sm:block" />
                        <span>行业: {stockInfo.industry || 'N/A'}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <MapPin size={14} className="sm:hidden" />
                        <MapPin size={16} className="hidden sm:block" />
                        <span>地区: {stockInfo.area || 'N/A'}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar size={14} className="sm:hidden" />
                        <Calendar size={16} className="hidden sm:block" />
                        <span>上市日期: {stockInfo.listing_date || 'N/A'}</span>
                      </div>
                    </div>
                  </div>
                  {/* 价格信息 - 移动端居中，桌面端右对齐 */}
                  <div className="text-center md:text-right">
                    <div className="flex items-center justify-center md:justify-end gap-2">
                      <span className="text-2xl sm:text-3xl md:text-4xl font-bold text-text-primary">
                        ¥{quote.price.toFixed(2)}
                      </span>
                      {isUp ? (
                        <TrendingUp className={`h-6 w-6 sm:h-7 sm:w-7 md:h-8 md:w-8 ${getChangeColor(quote.change_pct, selectedSymbol)}`} />
                      ) : (
                        <TrendingDown className={`h-6 w-6 sm:h-7 sm:w-7 md:h-8 md:w-8 ${getChangeColor(quote.change_pct, selectedSymbol)}`} />
                      )}
                    </div>
                    <div className={`text-lg sm:text-xl font-semibold mt-2 ${getChangeColor(quote.change_pct, selectedSymbol)}`}>
                      {formatPercentage(quote.change_pct)}
                    </div>
                    <div className="text-xs text-text-secondary mt-2">
                      {new Date(quote.timestamp).toLocaleString('zh-CN')}
                    </div>
                    {/* Manual refresh button - 移动端放在价格下方 */}
                    <button
                      onClick={handleRefreshAll}
                      disabled={quoteLoading || stockInfoLoading}
                      className="mt-2 inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded bg-gray-100 hover:bg-gray-200 text-text-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="刷新所有数据"
                    >
                      <RefreshCw size={14} className={quoteLoading || stockInfoLoading ? 'animate-spin' : ''} />
                      <span>刷新数据</span>
                    </button>
                  </div>
                </div>

                {/* 行情数据卡片 - 移动端2列，平板4列 */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                  <Card title="开盘价" padding="md">
                    <div className="text-lg sm:text-xl md:text-2xl font-semibold text-text-primary">
                      ¥{quote.open.toFixed(2)}
                    </div>
                  </Card>

                  <Card title="最高价" padding="md">
                    <div className={`text-lg sm:text-xl md:text-2xl font-semibold ${getChangeColor(quote.high - quote.open, selectedSymbol)}`}>
                      ¥{quote.high.toFixed(2)}
                    </div>
                    <div className="text-[10px] sm:text-xs text-text-secondary mt-1">
                      涨幅 {((quote.high - quote.open) / quote.open * 100).toFixed(2)}%
                    </div>
                  </Card>

                  <Card title="最低价" padding="md">
                    <div className={`text-lg sm:text-xl md:text-2xl font-semibold ${getChangeColor(quote.low - quote.open, selectedSymbol)}`}>
                      ¥{quote.low.toFixed(2)}
                    </div>
                    <div className="text-[10px] sm:text-xs text-text-secondary mt-1">
                      跌幅 {((quote.open - quote.low) / quote.open * 100).toFixed(2)}%
                    </div>
                  </Card>

                  <Card title="成交量" padding="md">
                    <div className="text-lg sm:text-xl md:text-2xl font-semibold text-text-primary">
                      {(quote.volume / 10000).toFixed(2)}万
                    </div>
                    <div className="text-[10px] sm:text-xs text-text-secondary mt-1">
                      振幅 {((quote.high - quote.low) / quote.open * 100).toFixed(2)}%
                    </div>
                  </Card>
                </div>
              </>
            ) : !quoteLoading && !stockInfoLoading && !(quoteError || stockInfoError) ? (
              <div className="text-center py-8">
                <Search className="mx-auto h-12 w-12 text-gray-300 mb-4" />
                <p className="text-text-secondary">暂无股票数据</p>
              </div>
            ) : null}
          </Card>

          {/* Price Chart - 移动端堆叠显示 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
            <Card title="价格走势（60天）" padding="md" className="lg:col-span-2">
              {barsError && (
                <div className="mb-3">
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <AlertCircle className="h-4 w-4 text-loss" />
                      <span className="text-xs font-semibold text-red-900">无法加载K线数据</span>
                    </div>
                    <p className="text-xs text-red-700">
                      {barsError instanceof Error ? barsError.message : '未知错误'}
                    </p>
                    <button
                      onClick={() => refetchBars()}
                      className="text-xs mt-2 px-2 py-1 bg-primary-500 text-white rounded hover:bg-primary-600 transition-colors"
                    >
                      刷新
                    </button>
                  </div>
                </div>
              )}

              {barsLoading && (
                <div className="h-64 sm:h-80 flex items-center justify-center">
                  <Loading size="sm" text="加载K线数据..." />
                </div>
              )}

              {!barsLoading && !barsError && barsData && barsData.bars.length > 0 ? (
                <div className="h-64 sm:h-80 md:h-96">
                  <CandlestickChart data={barsData.bars} />
                </div>
              ) : !barsLoading && !barsError ? (
                <div className="h-64 sm:h-80 flex items-center justify-center text-text-secondary">
                  暂无K线数据
                </div>
              ) : null}
            </Card>

            {/* Volume Chart */}
            <Card title="成交量（最近20天）" padding="md">
              {barsError && (
                <div className="mb-3">
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <AlertCircle className="h-4 w-4 text-loss" />
                      <span className="text-xs font-semibold text-red-900">无法加载成交量数据</span>
                    </div>
                    <p className="text-xs text-red-700">
                      {barsError instanceof Error ? barsError.message : '未知错误'}
                    </p>
                    <button
                      onClick={() => refetchBars()}
                      className="text-xs mt-2 px-2 py-1 bg-primary-500 text-white rounded hover:bg-primary-600 transition-colors"
                    >
                      刷新
                    </button>
                  </div>
                </div>
              )}

              {barsLoading && (
                <div className="h-64 sm:h-80 flex items-center justify-center">
                  <Loading size="sm" text="加载成交量..." />
                </div>
              )}

              {!barsLoading && !barsError && barsData && barsData.bars.length > 0 ? (
                <div className="h-64 sm:h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={barsData.bars.slice(-20)}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="date"
                        stroke="#6b7280"
                        tick={{ fontSize: 10 }}
                        angle={-45}
                        textAnchor="end"
                        height={80}
                      />
                      <YAxis
                        stroke="#6b7280"
                        tick={{ fontSize: 12 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#fff',
                          border: '1px solid #e5e7eb',
                          borderRadius: '8px'
                        }}
                      />
                      <Bar dataKey="volume" fill="#0ea5e9" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : !barsLoading && !barsError ? (
                <div className="h-64 sm:h-80 flex items-center justify-center text-text-secondary">
                  暂无成交量数据
                </div>
              ) : null}
            </Card>
          </div>

          {/* Technical Indicators - 移动端优化网格 */}
          <Card title="技术指标分析" padding="md">
            {indicatorsError && (
              <div className="mb-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <AlertCircle className="h-4 w-4 text-loss" />
                    <span className="text-xs font-semibold text-red-900">无法加载技术指标</span>
                  </div>
                  <p className="text-xs text-red-700">
                    {indicatorsError instanceof Error ? indicatorsError.message : '未知错误'}
                  </p>
                  <button
                    onClick={() => refetchIndicators()}
                    className="text-xs mt-2 px-2 py-1 bg-primary-500 text-white rounded hover:bg-primary-600 transition-colors"
                  >
                    刷新
                  </button>
                </div>
              </div>
            )}

            {indicatorsLoading && (
              <div className="h-64 flex items-center justify-center">
                <Loading size="sm" text="加载技术指标..." />
              </div>
            )}

            {!indicatorsLoading && !indicatorsError && indicators ? (
              <div className="space-y-6">
                {/* 趋势分析 - 移动端2列，平板4列 */}
                <div>
                  <h3 className="text-xs sm:text-sm font-semibold text-text-secondary mb-3">趋势分析</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">当前价格</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        ¥{quote?.price.toFixed(2)}
                      </div>
                      <div className={`text-[10px] sm:text-xs font-medium mt-1 ${evaluatePrice(quote?.price, indicators.indicators.ma_5, indicators.indicators.ma_20, indicators.indicators.ma_60).color}`}>
                        {evaluatePrice(quote?.price, indicators.indicators.ma_5, indicators.indicators.ma_20, indicators.indicators.ma_60).desc}
                      </div>
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">MA5 (5日均线)</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        ¥{indicators.indicators.ma_5?.toFixed(2) || 'N/A'}
                      </div>
                      {quote && indicators.indicators.ma_5 && (
                        <div className={`text-[10px] sm:text-xs font-medium mt-1 ${quote.price > indicators.indicators.ma_5 ? 'text-profit' : 'text-loss'}`}>
                          {quote.price > indicators.indicators.ma_5 ? '价格在上方 ↑' : '价格在下方 ↓'}
                        </div>
                      )}
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">MA20 (20日均线)</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        ¥{indicators.indicators.ma_20?.toFixed(2) || 'N/A'}
                      </div>
                      {quote && indicators.indicators.ma_20 && (
                        <div className={`text-[10px] sm:text-xs font-medium mt-1 ${quote.price > indicators.indicators.ma_20 ? 'text-profit' : 'text-loss'}`}>
                          {quote.price > indicators.indicators.ma_20 ? '价格在上方 ↑' : '价格在下方 ↓'}
                        </div>
                      )}
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">MA60 (60日均线)</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        ¥{indicators.indicators.ma_60?.toFixed(2) || 'N/A'}
                      </div>
                      {quote && indicators.indicators.ma_60 && (
                        <div className={`text-[10px] sm:text-xs font-medium mt-1 ${quote.price > indicators.indicators.ma_60 ? 'text-profit' : 'text-loss'}`}>
                          {quote.price > indicators.indicators.ma_60 ? '价格在上方 ↑' : '价格在下方 ↓'}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* 动量指标 - 移动端2列，平板4列 */}
                <div>
                  <h3 className="text-xs sm:text-sm font-semibold text-text-secondary mb-3">动量指标</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">RSI (相对强弱)</div>
                      <div className={`text-base sm:text-lg font-semibold ${evaluateRSI(indicators.indicators.rsi).color}`}>
                        {evaluateRSI(indicators.indicators.rsi).text}
                      </div>
                      <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                        {evaluateRSI(indicators.indicators.rsi).desc || '标准: 30-70'}
                      </div>
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">MACD</div>
                      <div className={`text-base sm:text-lg font-semibold ${evaluateMACD(indicators.indicators.macd, indicators.indicators.macd_signal).color}`}>
                        {evaluateMACD(indicators.indicators.macd, indicators.indicators.macd_signal).text}
                      </div>
                      <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                        {evaluateMACD(indicators.indicators.macd, indicators.indicators.macd_signal).desc}
                      </div>
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">KDJ_K</div>
                      <div className={`text-base sm:text-lg font-semibold ${evaluateKDJ(indicators.indicators.kdj_k, indicators.indicators.kdj_d).color}`}>
                        {evaluateKDJ(indicators.indicators.kdj_k, indicators.indicators.kdj_d).text}
                      </div>
                      <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                        {evaluateKDJ(indicators.indicators.kdj_k, indicators.indicators.kdj_d).desc}
                      </div>
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">KDJ_D</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        {indicators.indicators.kdj_d?.toFixed(2) || 'N/A'}
                      </div>
                      <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                        标准: 20-80
                      </div>
                    </div>
                  </div>
                </div>

                {/* 布林带 - 移动端2列，平板4列 */}
                <div>
                  <h3 className="text-xs sm:text-sm font-semibold text-text-secondary mb-3">布林带 (波动区间)</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">布林上轨</div>
                      <div className="text-base sm:text-lg font-semibold text-loss">
                        ¥{indicators.indicators.bb_upper?.toFixed(2) || 'N/A'}
                      </div>
                      {quote && indicators.indicators.bb_upper && (
                        <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                          {quote.price > indicators.indicators.bb_upper ? '价格突破上轨' : '压力位'}
                        </div>
                      )}
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">布林中轨</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        ¥{indicators.indicators.bb_middle?.toFixed(2) || 'N/A'}
                      </div>
                      <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                        中轨参考
                      </div>
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">布林下轨</div>
                      <div className="text-base sm:text-lg font-semibold text-profit">
                        ¥{indicators.indicators.bb_lower?.toFixed(2) || 'N/A'}
                      </div>
                      {quote && indicators.indicators.bb_lower && (
                        <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                          {quote.price < indicators.indicators.bb_lower ? '价格跌破下轨' : '支撑位'}
                        </div>
                      )}
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">ATR (真实波幅)</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        {indicators.indicators.atr?.toFixed(3) || 'N/A'}
                      </div>
                      <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                        波动性指标
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : !indicatorsLoading && !indicatorsError ? (
              <div className="h-64 flex items-center justify-center text-text-secondary">
                暂无技术指标数据
              </div>
            ) : null}
          </Card>
        </>
      )}
    </div>
  );
}
