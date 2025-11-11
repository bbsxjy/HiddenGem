import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/common/Card';
import { Loading } from '@/components/common/Loading';
import { Input } from '@/components/common/Input';
import { Markdown } from '@/components/common/Markdown';
import { CandlestickChart } from '@/components/market/CandlestickChart';
import { getQuote, getBars, getTechnicalIndicators, getStockInfo } from '@/api/market';
import { formatProfitLoss, formatPercentage, getChangeColor, detectMarketType, getDirectionColor } from '@/utils/format';
import { useStreamingAnalysis } from '@/hooks/useStreamingAnalysis';
import { Search, TrendingUp, TrendingDown, Building2, MapPin, Calendar, AlertCircle, RefreshCw, Brain, FileText, X, ChevronDown, ChevronUp, BarChart2, Table } from 'lucide-react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export function Market() {
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [showDeepAnalysis, setShowDeepAnalysis] = useState(false);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [collapseBasicInfo, setCollapseBasicInfo] = useState(false);
  const [collapseCharts, setCollapseCharts] = useState(false);
  const [indicatorViewMode, setIndicatorViewMode] = useState<'table' | 'chart'>('table');

  // Use streaming analysis hook for deep analysis
  const {
    agentResults,
    progress,
    progressPercent,
    currentAgent,
    currentMessage,
    isAnalyzing,
    finalResult,
    error: analysisError,
    isLLMAnalyzing,
    startAnalysis,
    stopAnalysis,
  } = useStreamingAnalysis();

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
    queryFn: async () => {
      const result = await getBars(selectedSymbol, { days: 60 });
      console.log('📊 [Market] Bars API response:', result);
      if (result?.bars && result.bars.length > 0) {
        console.log('📊 [Market] First bar:', result.bars[0]);
        console.log('📊 [Market] Last bar:', result.bars[result.bars.length - 1]);
      }
      return result;
    },
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
      setShowDeepAnalysis(false); // Reset deep analysis when searching new symbol
      setCollapseBasicInfo(false); // Expand basic info for new search
      setCollapseCharts(false); // Expand charts for new search
    }
  };

  const handleDeepAnalysis = () => {
    const symbol = searchInput.trim() || selectedSymbol;
    if (symbol) {
      // Set selected symbol if not already set
      if (!selectedSymbol || selectedSymbol !== symbol) {
        setSelectedSymbol(symbol);
        setSearchInput(symbol);
      }
      setShowDeepAnalysis(true);
      setCollapseBasicInfo(true); // Collapse basic info when showing analysis
      setCollapseCharts(true); // Collapse charts when showing analysis
      startAnalysis(symbol);
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

  // Agent name mapping
  const agentNameMap: Record<string, string> = {
    technical: '技术分析',
    fundamental: '基本面分析',
    sentiment: '情绪分析',
    policy: '政策分析',
  };

  // 判断板块
  const getBoardType = (symbol?: string) => {
    if (!symbol) return { name: '未知', color: 'bg-gray-100 text-gray-700' };
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
          <div className="flex gap-2">
            <button
              type="submit"
              className="flex-1 sm:flex-none px-4 sm:px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium text-sm sm:text-base"
            >
              查询
            </button>
            {searchInput.trim() && (
              <button
                type="button"
                onClick={handleDeepAnalysis}
                disabled={isAnalyzing}
                className="flex-1 sm:flex-none px-4 sm:px-6 py-2 bg-gradient-to-r from-purple-500 to-indigo-500 text-white rounded-lg hover:from-purple-600 hover:to-indigo-600 transition-colors font-medium text-sm sm:text-base disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 justify-center"
              >
                <Brain size={18} />
                <span className="hidden sm:inline">{isAnalyzing ? '分析中...' : 'AI分析'}</span>
                <span className="sm:hidden">{isAnalyzing ? '分析' : 'AI'}</span>
              </button>
            )}
            {isAnalyzing && (
              <button
                type="button"
                onClick={stopAnalysis}
                className="px-3 sm:px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors font-medium text-sm sm:text-base"
              >
                停止
              </button>
            )}
          </div>
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
                {collapseBasicInfo && showDeepAnalysis ? (
                  /* Collapsed View - 简洁版本 */
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <h2 className="text-lg font-bold text-text-primary">{stockInfo.name}</h2>
                            <span className="text-sm text-text-secondary">{quote.symbol}</span>
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getBoardType(quote.symbol).color}`}>
                              {getBoardType(quote.symbol).name}
                            </span>
                          </div>
                          <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                              <span className="text-2xl font-bold text-text-primary">
                                ¥{quote.price != null ? quote.price.toFixed(2) : 'N/A'}
                              </span>
                              {isUp ? (
                                <TrendingUp className={`h-6 w-6 ${getChangeColor(quote.change_pct, selectedSymbol)}`} />
                              ) : (
                                <TrendingDown className={`h-6 w-6 ${getChangeColor(quote.change_pct, selectedSymbol)}`} />
                              )}
                              <span className={`text-lg font-semibold ${getChangeColor(quote.change_pct, selectedSymbol)}`}>
                                {formatPercentage(quote.change_pct)}
                              </span>
                            </div>
                            <div className="flex gap-4 text-sm">
                              <div>
                                <span className="text-text-secondary">开:</span>
                                <span className="font-medium text-text-primary ml-1">
                                  ¥{quote.open != null ? quote.open.toFixed(2) : 'N/A'}
                                </span>
                              </div>
                              <div>
                                <span className="text-text-secondary">高:</span>
                                <span className="font-medium text-profit ml-1">
                                  ¥{quote.high != null ? quote.high.toFixed(2) : 'N/A'}
                                </span>
                              </div>
                              <div>
                                <span className="text-text-secondary">低:</span>
                                <span className="font-medium text-loss ml-1">
                                  ¥{quote.low != null ? quote.low.toFixed(2) : 'N/A'}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => setCollapseBasicInfo(false)}
                        className="px-3 py-1.5 text-sm text-primary-600 hover:text-primary-700 hover:bg-primary-50 rounded transition-colors"
                      >
                        展开详情 ▼
                      </button>
                    </div>
                  </div>
                ) : (
                  /* Full View - 完整版本 */
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
                            ¥{quote.price != null ? quote.price.toFixed(2) : 'N/A'}
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
                          {quote.timestamp ? new Date(quote.timestamp).toLocaleString('zh-CN') : 'N/A'}
                        </div>
                        {/* Manual refresh button - 移动端放在价格下方 */}
                        <div className="flex gap-2 justify-center md:justify-end mt-2">
                          <button
                            onClick={handleRefreshAll}
                            disabled={quoteLoading || stockInfoLoading}
                            className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded bg-gray-100 hover:bg-gray-200 text-text-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title="刷新所有数据"
                          >
                            <RefreshCw size={14} className={quoteLoading || stockInfoLoading ? 'animate-spin' : ''} />
                            <span>刷新数据</span>
                          </button>
                          {showDeepAnalysis && (
                            <button
                              onClick={() => setCollapseBasicInfo(true)}
                              className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded bg-primary-50 hover:bg-primary-100 text-primary-600 transition-colors"
                            >
                              折叠 ▲
                            </button>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* 行情数据卡片 - 移动端2列，平板4列 */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                      <Card title="开盘价" padding="md">
                        <div className="text-lg sm:text-xl md:text-2xl font-semibold text-text-primary">
                          ¥{quote.open != null ? quote.open.toFixed(2) : 'N/A'}
                        </div>
                      </Card>

                      <Card title="最高价" padding="md">
                        <div className={`text-lg sm:text-xl md:text-2xl font-semibold ${quote.high != null && quote.open != null ? getChangeColor(quote.high - quote.open, selectedSymbol) : 'text-text-primary'}`}>
                          ¥{quote.high != null ? quote.high.toFixed(2) : 'N/A'}
                        </div>
                        {quote.high != null && quote.open != null && quote.open !== 0 && (
                          <div className="text-[10px] sm:text-xs text-text-secondary mt-1">
                            涨幅 {((quote.high - quote.open) / quote.open * 100).toFixed(2)}%
                          </div>
                        )}
                      </Card>

                      <Card title="最低价" padding="md">
                        <div className={`text-lg sm:text-xl md:text-2xl font-semibold ${quote.low != null && quote.open != null ? getChangeColor(quote.low - quote.open, selectedSymbol) : 'text-text-primary'}`}>
                          ¥{quote.low != null ? quote.low.toFixed(2) : 'N/A'}
                        </div>
                        {quote.open != null && quote.low != null && quote.open !== 0 && (
                          <div className="text-[10px] sm:text-xs text-text-secondary mt-1">
                            跌幅 {((quote.open - quote.low) / quote.open * 100).toFixed(2)}%
                          </div>
                        )}
                      </Card>

                      <Card title="成交量" padding="md">
                        <div className="text-lg sm:text-xl md:text-2xl font-semibold text-text-primary">
                          {quote.volume != null ? (quote.volume / 10000).toFixed(2) : 'N/A'}万
                        </div>
                        {quote.high != null && quote.low != null && quote.open != null && quote.open !== 0 && (
                          <div className="text-[10px] sm:text-xs text-text-secondary mt-1">
                            振幅 {((quote.high - quote.low) / quote.open * 100).toFixed(2)}%
                          </div>
                        )}
                      </Card>
                    </div>
                  </>
                )}
              </>
            ) : !quoteLoading && !stockInfoLoading && !(quoteError || stockInfoError) ? (
              <div className="text-center py-8">
                <Search className="mx-auto h-12 w-12 text-gray-300 mb-4" />
                <p className="text-text-secondary">暂无股票数据</p>
              </div>
            ) : null}
          </Card>

          {/* Price Chart and Volume - 可折叠 */}
          {collapseCharts && showDeepAnalysis ? (
            /* 折叠视图 - 显示简要标题 */
            <Card padding="md">
              <button
                onClick={() => setCollapseCharts(false)}
                className="w-full flex items-center justify-between text-left hover:bg-gray-50 transition-colors p-2 rounded"
              >
                <div className="flex items-center gap-2">
                  <BarChart2 size={18} className="text-primary-500" />
                  <span className="font-semibold text-text-primary">价格走势与成交量</span>
                  <span className="text-xs text-text-secondary">(已折叠)</span>
                </div>
                <ChevronDown size={18} className="text-text-secondary" />
              </button>
            </Card>
          ) : (
            /* 完整视图 - 显示K线图和成交量 */
            <>
              {showDeepAnalysis && (
                <div className="flex justify-end">
                  <button
                    onClick={() => setCollapseCharts(true)}
                    className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                  >
                    <ChevronUp size={16} />
                    折叠图表
                  </button>
                </div>
              )}
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

              {!barsLoading && !barsError && barsData?.bars?.length > 0 ? (
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

              {!barsLoading && !barsError && barsData?.bars?.length > 0 ? (
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
            </>
          )}

          {/* Technical Indicators - 可折叠，支持表格/图表切换 */}
          {collapseCharts && showDeepAnalysis ? (
            /* 折叠视图 */
            <Card padding="md">
              <button
                onClick={() => setCollapseCharts(false)}
                className="w-full flex items-center justify-between text-left hover:bg-gray-50 transition-colors p-2 rounded"
              >
                <div className="flex items-center gap-2">
                  <BarChart2 size={18} className="text-primary-500" />
                  <span className="font-semibold text-text-primary">技术指标分析</span>
                  <span className="text-xs text-text-secondary">(已折叠)</span>
                </div>
                <ChevronDown size={18} className="text-text-secondary" />
              </button>
            </Card>
          ) : (
            /* 完整视图 - 显示技术指标 */
            <Card
              title={
                <div className="flex items-center justify-between w-full">
                  <span>技术指标分析</span>
                  <div className="flex items-center gap-2">
                    {/* 视图切换按钮 */}
                    <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
                      <button
                        onClick={() => setIndicatorViewMode('table')}
                        className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                          indicatorViewMode === 'table'
                            ? 'bg-white text-primary-600 shadow-sm'
                            : 'text-text-secondary hover:text-text-primary'
                        }`}
                      >
                        <Table size={14} className="inline mr-1" />
                        表格
                      </button>
                      <button
                        onClick={() => setIndicatorViewMode('chart')}
                        className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                          indicatorViewMode === 'chart'
                            ? 'bg-white text-primary-600 shadow-sm'
                            : 'text-text-secondary hover:text-text-primary'
                        }`}
                      >
                        <BarChart2 size={14} className="inline mr-1" />
                        图表
                      </button>
                    </div>
                    {showDeepAnalysis && (
                      <button
                        onClick={() => setCollapseCharts(true)}
                        className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
                      >
                        <ChevronUp size={16} />
                      </button>
                    )}
                  </div>
                </div>
              }
              padding="md"
            >
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
              indicatorViewMode === 'table' ? (
                /* 表格视图 - 原有的卡片展示 */
                <div className="space-y-6">
                {/* 趋势分析 - 移动端2列，平板4列 */}
                <div>
                  <h3 className="text-xs sm:text-sm font-semibold text-text-secondary mb-3">趋势分析</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">当前价格</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        ¥{quote?.price != null ? quote.price.toFixed(2) : 'N/A'}
                      </div>
                      <div className={`text-[10px] sm:text-xs font-medium mt-1 ${evaluatePrice(quote?.price, indicators?.indicators?.ma_5, indicators?.indicators?.ma_20, indicators?.indicators?.ma_60).color}`}>
                        {evaluatePrice(quote?.price, indicators?.indicators?.ma_5, indicators?.indicators?.ma_20, indicators?.indicators?.ma_60).desc}
                      </div>
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">MA5 (5日均线)</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        ¥{indicators?.indicators?.ma_5?.toFixed(2) || 'N/A'}
                      </div>
                      {quote && quote.price != null && indicators?.indicators?.ma_5 != null && (
                        <div className={`text-[10px] sm:text-xs font-medium mt-1 ${quote.price > indicators.indicators.ma_5 ? 'text-profit' : 'text-loss'}`}>
                          {quote.price > indicators.indicators.ma_5 ? '价格在上方 ↑' : '价格在下方 ↓'}
                        </div>
                      )}
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">MA20 (20日均线)</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        ¥{indicators?.indicators?.ma_20?.toFixed(2) || 'N/A'}
                      </div>
                      {quote && quote.price != null && indicators?.indicators?.ma_20 != null && (
                        <div className={`text-[10px] sm:text-xs font-medium mt-1 ${quote.price > indicators.indicators.ma_20 ? 'text-profit' : 'text-loss'}`}>
                          {quote.price > indicators.indicators.ma_20 ? '价格在上方 ↑' : '价格在下方 ↓'}
                        </div>
                      )}
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">MA60 (60日均线)</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        ¥{indicators?.indicators?.ma_60?.toFixed(2) || 'N/A'}
                      </div>
                      {quote && quote.price != null && indicators?.indicators?.ma_60 != null && (
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
                      <div className={`text-base sm:text-lg font-semibold ${evaluateRSI(indicators?.indicators?.rsi).color}`}>
                        {evaluateRSI(indicators?.indicators?.rsi).text}
                      </div>
                      <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                        {evaluateRSI(indicators?.indicators?.rsi).desc || '标准: 30-70'}
                      </div>
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">MACD</div>
                      <div className={`text-base sm:text-lg font-semibold ${evaluateMACD(indicators?.indicators?.macd, indicators?.indicators?.macd_signal).color}`}>
                        {evaluateMACD(indicators?.indicators?.macd, indicators?.indicators?.macd_signal).text}
                      </div>
                      <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                        {evaluateMACD(indicators?.indicators?.macd, indicators?.indicators?.macd_signal).desc}
                      </div>
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">KDJ_K</div>
                      <div className={`text-base sm:text-lg font-semibold ${evaluateKDJ(indicators?.indicators?.kdj_k, indicators?.indicators?.kdj_d).color}`}>
                        {evaluateKDJ(indicators?.indicators?.kdj_k, indicators?.indicators?.kdj_d).text}
                      </div>
                      <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                        {evaluateKDJ(indicators?.indicators?.kdj_k, indicators?.indicators?.kdj_d).desc}
                      </div>
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">KDJ_D</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        {indicators?.indicators?.kdj_d?.toFixed(2) || 'N/A'}
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
                        ¥{indicators?.indicators?.bb_upper?.toFixed(2) || 'N/A'}
                      </div>
                      {quote && quote.price != null && indicators?.indicators?.bb_upper != null && (
                        <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                          {quote.price > indicators.indicators.bb_upper ? '价格突破上轨' : '压力位'}
                        </div>
                      )}
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">布林中轨</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        ¥{indicators?.indicators?.bb_middle?.toFixed(2) || 'N/A'}
                      </div>
                      <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                        中轨参考
                      </div>
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">布林下轨</div>
                      <div className="text-base sm:text-lg font-semibold text-profit">
                        ¥{indicators?.indicators?.bb_lower?.toFixed(2) || 'N/A'}
                      </div>
                      {quote && quote.price != null && indicators?.indicators?.bb_lower != null && (
                        <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                          {quote.price < indicators.indicators.bb_lower ? '价格跌破下轨' : '支撑位'}
                        </div>
                      )}
                    </div>
                    <div className="p-3 sm:p-4 bg-gray-50 rounded-lg">
                      <div className="text-[10px] sm:text-xs text-text-secondary mb-1">ATR (真实波幅)</div>
                      <div className="text-base sm:text-lg font-semibold text-text-primary">
                        {indicators?.indicators?.atr?.toFixed(3) || 'N/A'}
                      </div>
                      <div className="text-[10px] sm:text-xs font-medium mt-1 text-text-secondary">
                        波动性指标
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              ) : (
                /* 图表视图 - 使用图表展示技术指标 */
                <div className="space-y-6">
                  {/* 趋势分析图表 - MA线 */}
                  <div>
                    <h3 className="text-sm font-semibold text-text-primary mb-3">趋势分析 - 均线系统</h3>
                    <div className="h-80">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={[
                          {
                            name: '当前',
                            price: quote?.price || 0,
                            ma5: indicators?.indicators?.ma_5 || 0,
                            ma20: indicators?.indicators?.ma_20 || 0,
                            ma60: indicators?.indicators?.ma_60 || 0,
                          }
                        ]}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="name" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" domain={['dataMin - 5', 'dataMax + 5']} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#fff',
                              border: '1px solid #e5e7eb',
                              borderRadius: '8px'
                            }}
                          />
                          <Legend />
                          <Line type="monotone" dataKey="price" stroke="#3b82f6" strokeWidth={3} name="当前价格" dot={{ r: 6 }} />
                          <Line type="monotone" dataKey="ma5" stroke="#10b981" strokeWidth={2} name="MA5" dot={{ r: 5 }} />
                          <Line type="monotone" dataKey="ma20" stroke="#f59e0b" strokeWidth={2} name="MA20" dot={{ r: 5 }} />
                          <Line type="monotone" dataKey="ma60" stroke="#8b5cf6" strokeWidth={2} name="MA60" dot={{ r: 5 }} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                      <div className="p-3 bg-blue-50 rounded-lg">
                        <div className="text-xs text-blue-600 mb-1">当前价格</div>
                        <div className="text-lg font-bold text-blue-700">¥{quote?.price?.toFixed(2) || 'N/A'}</div>
                      </div>
                      <div className="p-3 bg-green-50 rounded-lg">
                        <div className="text-xs text-green-600 mb-1">MA5</div>
                        <div className="text-lg font-bold text-green-700">¥{indicators?.indicators?.ma_5?.toFixed(2) || 'N/A'}</div>
                      </div>
                      <div className="p-3 bg-orange-50 rounded-lg">
                        <div className="text-xs text-orange-600 mb-1">MA20</div>
                        <div className="text-lg font-bold text-orange-700">¥{indicators?.indicators?.ma_20?.toFixed(2) || 'N/A'}</div>
                      </div>
                      <div className="p-3 bg-purple-50 rounded-lg">
                        <div className="text-xs text-purple-600 mb-1">MA60</div>
                        <div className="text-lg font-bold text-purple-700">¥{indicators?.indicators?.ma_60?.toFixed(2) || 'N/A'}</div>
                      </div>
                    </div>
                  </div>

                  {/* 动量指标图表 */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* RSI */}
                    <div>
                      <h3 className="text-sm font-semibold text-text-primary mb-3">RSI - 相对强弱指标</h3>
                      <div className="h-48">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={[
                            {
                              name: 'RSI',
                              value: indicators?.indicators?.rsi || 0,
                              oversold: 30,
                              overbought: 70,
                            }
                          ]}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis dataKey="name" stroke="#6b7280" />
                            <YAxis domain={[0, 100]} stroke="#6b7280" />
                            <Tooltip />
                            <Bar dataKey="value" fill={
                              (indicators?.indicators?.rsi || 0) > 70 ? '#ef4444' :
                              (indicators?.indicators?.rsi || 0) < 30 ? '#10b981' :
                              '#3b82f6'
                            } />
                            <Line type="monotone" dataKey="oversold" stroke="#10b981" strokeDasharray="5 5" />
                            <Line type="monotone" dataKey="overbought" stroke="#ef4444" strokeDasharray="5 5" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="mt-2 text-center">
                        <span className="text-xs text-text-secondary">当前值: </span>
                        <span className={`text-sm font-bold ${evaluateRSI(indicators?.indicators?.rsi).color}`}>
                          {indicators?.indicators?.rsi?.toFixed(2) || 'N/A'}
                        </span>
                        <span className="text-xs text-text-secondary ml-2">
                          ({evaluateRSI(indicators?.indicators?.rsi).desc})
                        </span>
                      </div>
                    </div>

                    {/* MACD */}
                    <div>
                      <h3 className="text-sm font-semibold text-text-primary mb-3">MACD - 指数平滑异同移动平均线</h3>
                      <div className="h-48">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={[
                            {
                              name: 'MACD',
                              macd: indicators?.indicators?.macd || 0,
                              signal: indicators?.indicators?.macd_signal || 0,
                              histogram: (indicators?.indicators?.macd || 0) - (indicators?.indicators?.macd_signal || 0),
                            }
                          ]}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis dataKey="name" stroke="#6b7280" />
                            <YAxis stroke="#6b7280" />
                            <Tooltip />
                            <Legend />
                            <Line type="monotone" dataKey="macd" stroke="#3b82f6" strokeWidth={2} name="MACD" dot={{ r: 6 }} />
                            <Line type="monotone" dataKey="signal" stroke="#f59e0b" strokeWidth={2} name="Signal" dot={{ r: 6 }} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="mt-2 text-center">
                        <span className="text-xs text-text-secondary">MACD: </span>
                        <span className={`text-sm font-bold ${evaluateMACD(indicators?.indicators?.macd, indicators?.indicators?.macd_signal).color}`}>
                          {indicators?.indicators?.macd?.toFixed(3) || 'N/A'}
                        </span>
                        <span className="text-xs text-text-secondary ml-2">
                          ({evaluateMACD(indicators?.indicators?.macd, indicators?.indicators?.macd_signal).desc})
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* 布林带图表 */}
                  <div>
                    <h3 className="text-sm font-semibold text-text-primary mb-3">布林带 - 波动区间</h3>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={[
                          {
                            name: '布林带',
                            price: quote?.price || 0,
                            upper: indicators?.indicators?.bb_upper || 0,
                            middle: indicators?.indicators?.bb_middle || 0,
                            lower: indicators?.indicators?.bb_lower || 0,
                          }
                        ]}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="name" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" domain={['dataMin - 5', 'dataMax + 5']} />
                          <Tooltip />
                          <Legend />
                          <Line type="monotone" dataKey="upper" stroke="#ef4444" strokeWidth={2} name="上轨" dot={{ r: 5 }} />
                          <Line type="monotone" dataKey="middle" stroke="#3b82f6" strokeWidth={2} name="中轨" dot={{ r: 5 }} />
                          <Line type="monotone" dataKey="lower" stroke="#10b981" strokeWidth={2} name="下轨" dot={{ r: 5 }} />
                          <Line type="monotone" dataKey="price" stroke="#8b5cf6" strokeWidth={3} name="当前价格" dot={{ r: 6 }} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                      <div className="p-3 bg-red-50 rounded-lg">
                        <div className="text-xs text-red-600 mb-1">上轨</div>
                        <div className="text-lg font-bold text-red-700">¥{indicators?.indicators?.bb_upper?.toFixed(2) || 'N/A'}</div>
                      </div>
                      <div className="p-3 bg-blue-50 rounded-lg">
                        <div className="text-xs text-blue-600 mb-1">中轨</div>
                        <div className="text-lg font-bold text-blue-700">¥{indicators?.indicators?.bb_middle?.toFixed(2) || 'N/A'}</div>
                      </div>
                      <div className="p-3 bg-green-50 rounded-lg">
                        <div className="text-xs text-green-600 mb-1">下轨</div>
                        <div className="text-lg font-bold text-green-700">¥{indicators?.indicators?.bb_lower?.toFixed(2) || 'N/A'}</div>
                      </div>
                      <div className="p-3 bg-purple-50 rounded-lg">
                        <div className="text-xs text-purple-600 mb-1">当前价格</div>
                        <div className="text-lg font-bold text-purple-700">¥{quote?.price?.toFixed(2) || 'N/A'}</div>
                      </div>
                    </div>
                  </div>
                </div>
              )
            ) : !indicatorsLoading && !indicatorsError ? (
              <div className="h-64 flex items-center justify-center text-text-secondary">
                暂无技术指标数据
              </div>
            ) : null}
          </Card>
          )}

          {/* Deep Analysis Section */}
          {showDeepAnalysis && (isAnalyzing || Object.keys(agentResults).length > 0 || finalResult) && (
            <Card title={`🤖 AI深度分析 - ${selectedSymbol}`} padding="md">
              <div className="space-y-4">
                {/* Progress indicator with bar */}
                <div className="space-y-2">
                  {/* Progress bar */}
                  <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-primary-500 h-2.5 rounded-full transition-all duration-300 ease-out"
                      style={{ width: `${progressPercent}%` }}
                    ></div>
                  </div>

                  {/* Progress info */}
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0 p-3 sm:p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-center gap-3">
                      {isAnalyzing && (
                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-500"></div>
                      )}
                      <div className="flex flex-col">
                        <span className="text-xs sm:text-sm font-medium text-text-primary">
                          {isLLMAnalyzing
                            ? '🤖 AI智能分析中...'
                            : isAnalyzing
                            ? currentMessage || `分析进度: ${progress}`
                            : '✅ 分析完成'}
                        </span>
                        {currentAgent && isAnalyzing && (
                          <span className="text-xs text-text-secondary mt-0.5">
                            当前: {currentAgent === 'technical' ? '📈 技术分析' :
                                  currentAgent === 'fundamental' ? '💰 基本面' :
                                  currentAgent === 'sentiment' ? '💬 情绪分析' :
                                  currentAgent === 'policy' ? '📰 政策新闻' :
                                  currentAgent === 'debate' ? '⚖️ 投资辩论' :
                                  currentAgent === 'risk' ? '🛡️ 风险评估' :
                                  currentAgent}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-4 pl-8 sm:pl-0">
                      <span className="text-xs text-text-secondary">
                        {Object.values(agentResults).filter(r => !r.is_error).length} / 4 个Agent已完成
                      </span>
                      <span className="text-xs font-semibold text-primary-600">
                        {progressPercent.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Aggregated Signal */}
                {finalResult?.aggregated_signal ? (
                  <div>
                    {/* 综合信号指标 */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <div className="text-xs text-text-secondary mb-1">方向</div>
                        <div className={`text-xl font-semibold ${
                          getDirectionColor(finalResult.aggregated_signal.direction as 'long' | 'short' | 'hold', selectedSymbol)
                        }`}>
                          {finalResult.aggregated_signal.direction === 'long' ? '看多' :
                              finalResult.aggregated_signal.direction === 'short' ? '看空' : '持有'}
                        </div>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <div className="text-xs text-text-secondary mb-1">置信度</div>
                        <div className="text-xl font-semibold text-text-primary">
                          {(finalResult.aggregated_signal.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <div className="text-xs text-text-secondary mb-1">建议仓位</div>
                        <div className="text-xl font-semibold text-text-primary">
                          {(finalResult.aggregated_signal.position_size * 100).toFixed(0)}%
                        </div>
                      </div>
                      <div className="p-4 bg-gray-50 rounded-lg">
                        <div className="text-xs text-text-secondary mb-1">一致Agent数</div>
                        <div className="text-xl font-semibold text-text-primary">
                          {finalResult.aggregated_signal.num_agreeing_agents}
                        </div>
                      </div>
                    </div>

                    {/* Analysis Method Badge */}
                    <div className="mb-6 flex items-center gap-2">
                      <span className="text-xs text-text-secondary">分析方法:</span>
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                          finalResult.aggregated_signal.metadata?.analysis_method === 'llm'
                              ? 'bg-primary-100 text-primary-700'
                              : 'bg-gray-100 text-gray-700'
                      }`}>
                    {finalResult.aggregated_signal.metadata?.analysis_method === 'llm'
                        ? 'AI智能分析'
                        : '规则聚合'}
                  </span>
                    </div>

                    {/* Warnings */}
                    {finalResult.aggregated_signal.warnings && finalResult.aggregated_signal.warnings.length > 0 && (
                      <div className="mb-6 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <div className="flex items-start gap-2">
                          <span className="text-yellow-600 mt-0.5">⚠️</span>
                          <div className="flex-1">
                            <p className="text-xs font-semibold text-yellow-800 mb-1">注意事项</p>
                            <ul className="text-xs text-yellow-700 space-y-0.5">
                              {finalResult.aggregated_signal.warnings.map((warning: string, idx: number) => (
                                <li key={idx}>• {warning}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-6 text-text-secondary">
                    <p className="text-lg font-medium mb-2">分析中……需要5-10分钟左右完成，请耐心等待。</p>
                    {finalResult?.signal_rejection_reason ? (
                      <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg max-w-2xl mx-auto">
                        <p className="text-sm text-yellow-800 font-medium mb-1">原因:</p>
                        <p className="text-sm text-yellow-700">
                          {finalResult.signal_rejection_reason}
                        </p>
                      </div>
                    ) : (
                      <p className="text-sm mt-2"></p>
                    )}
                  </div>
                )}

                {/* Real-time agent results grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                  {/* Show all 4 agents - completed or waiting */}
                  {['technical', 'fundamental', 'sentiment', 'policy'].map((agentName) => {
                    const result = agentResults[agentName];
                    const isCompleted = !!result;
                    const isWaiting = isAnalyzing && !isCompleted;

                    return (
                      <div key={agentName}>
                        <div
                          onClick={() => result?.reasoning && setExpandedAgent(agentName)}
                          className={`p-4 border rounded-lg transition-all ${
                            isCompleted
                              ? result.reasoning
                                ? 'bg-white border-gray-200 cursor-pointer hover:border-primary-300 hover:shadow-md'
                                : 'bg-white border-gray-200'
                              : 'bg-gray-50 border-gray-200'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                              {agentNameMap[agentName] || agentName}
                              {isWaiting && (
                                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-primary-500"></div>
                              )}
                              {result?.reasoning && (
                                <FileText size={12} className="text-primary-500" />
                              )}
                            </h4>
                            {result?.is_error && (
                              <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded">
                                错误
                              </span>
                            )}
                          </div>

                          {isCompleted ? (
                            result.is_error ? (
                              // Show error state
                              <div className="text-center py-4">
                                <p className="text-xs text-red-600 mb-2">分析失败</p>
                                <p className="text-xs text-text-secondary">
                                  该 Agent 未能返回有效结果
                                </p>
                              </div>
                            ) : (
                              // Show result
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-xs text-text-secondary">方向</span>
                                  <span className={`text-sm font-semibold ${
                                    getDirectionColor(result.direction as 'long' | 'short' | 'hold', selectedSymbol)
                                  }`}>
                                    {result.direction === 'long' ? '看多' :
                                     result.direction === 'short' ? '看空' : '持有'}
                                  </span>
                                </div>
                                <div className="flex items-center justify-between">
                                  <span className="text-xs text-text-secondary">置信度</span>
                                  <span className="text-sm font-medium text-text-primary">
                                    {(result.confidence * 100).toFixed(0)}%
                                  </span>
                                </div>
                                <div className="flex items-center justify-between">
                                  <span className="text-xs text-text-secondary">评分</span>
                                  <span className="text-sm font-medium text-text-primary">
                                    {(result.score * 100).toFixed(0)}
                                  </span>
                                </div>
                                {result.reasoning && (
                                  <div className="mt-2 pt-2 border-t border-gray-100">
                                    <p className="text-xs text-text-secondary line-clamp-2">
                                      {result.reasoning}
                                    </p>
                                  </div>
                                )}
                              </div>
                            )
                          ) : (
                            // Show waiting state
                            <div className="text-center py-4">
                              <div className="text-xs text-text-secondary">
                                {isWaiting ? '等待分析...' : '未开始'}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </Card>
          )}

          {/* LLM Analysis */}
          {showDeepAnalysis && finalResult?.llm_analysis && (
            <Card title="🤖 AI综合分析" padding="md">
              <div className="space-y-6">
                {/* 推荐方向和置信度 */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="text-xs text-text-secondary mb-1">推荐方向</div>
                    <div className={`text-xl font-semibold ${
                      getDirectionColor(finalResult.llm_analysis.recommended_direction as 'long' | 'short' | 'hold', selectedSymbol)
                    }`}>
                      {finalResult.llm_analysis.recommended_direction === 'long' ? '看多' :
                       finalResult.llm_analysis.recommended_direction === 'short' ? '看空' : '持有'}
                    </div>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="text-xs text-text-secondary mb-1">置信度</div>
                    <div className="text-xl font-semibold text-text-primary">
                      {(finalResult.llm_analysis.confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="text-xs text-text-secondary mb-1">分析时间</div>
                    <div className="text-sm font-medium text-text-primary">
                      {new Date(finalResult.llm_analysis.analysis_timestamp).toLocaleString('zh-CN')}
                    </div>
                  </div>
                </div>

                {/* 价格目标 */}
                {finalResult.llm_analysis.price_targets &&
                 (finalResult.llm_analysis.price_targets.entry ||
                  finalResult.llm_analysis.price_targets.stop_loss ||
                  finalResult.llm_analysis.price_targets.take_profit) && (
                  <div>
                    <h4 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      💰 价格目标
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {finalResult.llm_analysis.price_targets.entry && (
                        <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                          <div className="flex items-center justify-between mb-2">
                            <div className="text-xs text-blue-600 font-medium">目标价</div>
                            <div className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                              Entry
                            </div>
                          </div>
                          <div className="text-2xl font-bold text-blue-700">
                            ¥{finalResult.llm_analysis.price_targets.entry.toFixed(2)}
                          </div>
                        </div>
                      )}

                      {finalResult.llm_analysis.price_targets.stop_loss && (
                        <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                          <div className="flex items-center justify-between mb-2">
                            <div className="text-xs text-red-600 font-medium">止损价</div>
                            <div className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded">
                              Stop Loss
                            </div>
                          </div>
                          <div className="text-2xl font-bold text-red-700">
                            ¥{finalResult.llm_analysis.price_targets.stop_loss.toFixed(2)}
                          </div>
                          {finalResult.llm_analysis.price_targets.entry && (
                            <div className="text-xs text-red-600 mt-1">
                              {((finalResult.llm_analysis.price_targets.stop_loss / finalResult.llm_analysis.price_targets.entry - 1) * 100).toFixed(1)}%
                            </div>
                          )}
                        </div>
                      )}

                      {finalResult.llm_analysis.price_targets.take_profit && (
                        <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                          <div className="flex items-center justify-between mb-2">
                            <div className="text-xs text-green-600 font-medium">止盈价</div>
                            <div className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded">
                              Take Profit
                            </div>
                          </div>
                          <div className="text-2xl font-bold text-green-700">
                            ¥{finalResult.llm_analysis.price_targets.take_profit.toFixed(2)}
                          </div>
                          {finalResult.llm_analysis.price_targets.entry && (
                            <div className="text-xs text-green-600 mt-1">
                              +{((finalResult.llm_analysis.price_targets.take_profit / finalResult.llm_analysis.price_targets.entry - 1) * 100).toFixed(1)}%
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 分析推理 - 使用 Markdown 渲染 */}
                <div>
                  <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                    <span className="w-2 h-2 bg-primary-500 rounded-full"></span>
                    决策理由
                  </h4>
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                    <Markdown content={finalResult.llm_analysis.signal_processor_summary} />
                  </div>
                </div>

                {/* 风险分析师意见 */}
                {finalResult.llm_analysis.risk_analysts &&
                 Object.keys(finalResult.llm_analysis.risk_analysts).length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                      <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                      风险分析师意见（{Object.keys(finalResult.llm_analysis.risk_analysts).length}位）
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {finalResult.llm_analysis.risk_analysts.risky && (
                        <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <span className="text-lg">🔴</span>
                              <h5 className="text-sm font-semibold text-red-700">
                                激进派
                              </h5>
                            </div>
                            {finalResult.llm_analysis.risk_analysts.risky.direction && (
                              <span className={`text-xs px-2 py-0.5 rounded font-semibold ${
                                finalResult.llm_analysis.risk_analysts.risky.direction === 'long'
                                  ? 'bg-green-100 text-green-700'
                                  : finalResult.llm_analysis.risk_analysts.risky.direction === 'short'
                                  ? 'bg-red-100 text-red-700'
                                  : 'bg-gray-100 text-gray-700'
                              }`}>
                                {finalResult.llm_analysis.risk_analysts.risky.direction === 'long' ? '看多' :
                                 finalResult.llm_analysis.risk_analysts.risky.direction === 'short' ? '看空' : '持有'}
                              </span>
                            )}
                          </div>

                          {finalResult.llm_analysis.risk_analysts.risky.confidence !== undefined && (
                            <div className="mb-2 flex items-center justify-between text-xs">
                              <span className="text-red-600">置信度</span>
                              <span className="font-semibold text-red-700">
                                {(finalResult.llm_analysis.risk_analysts.risky.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                          )}

                          <details className="mt-2">
                            <summary className="text-xs text-red-600 cursor-pointer hover:text-red-700 font-medium mb-2">
                              完整分析 ▼
                            </summary>
                            <div className="mt-2 p-3 bg-white rounded text-xs border border-red-100 max-h-64 overflow-y-auto">
                              <Markdown content={finalResult.llm_analysis.risk_analysts.risky.reasoning || finalResult.llm_analysis.risk_analysts.risky.full_analysis} />
                            </div>
                          </details>
                        </div>
                      )}

                      {finalResult.llm_analysis.risk_analysts.neutral && (
                        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <span className="text-lg">⚪</span>
                              <h5 className="text-sm font-semibold text-gray-700">
                                中立派
                              </h5>
                            </div>
                            {finalResult.llm_analysis.risk_analysts.neutral.direction && (
                              <span className={`text-xs px-2 py-0.5 rounded font-semibold ${
                                finalResult.llm_analysis.risk_analysts.neutral.direction === 'long'
                                  ? 'bg-green-100 text-green-700'
                                  : finalResult.llm_analysis.risk_analysts.neutral.direction === 'short'
                                  ? 'bg-red-100 text-red-700'
                                  : 'bg-gray-100 text-gray-700'
                              }`}>
                                {finalResult.llm_analysis.risk_analysts.neutral.direction === 'long' ? '看多' :
                                 finalResult.llm_analysis.risk_analysts.neutral.direction === 'short' ? '看空' : '持有'}
                              </span>
                            )}
                          </div>

                          {finalResult.llm_analysis.risk_analysts.neutral.confidence !== undefined && (
                            <div className="mb-2 flex items-center justify-between text-xs">
                              <span className="text-gray-600">置信度</span>
                              <span className="font-semibold text-gray-700">
                                {(finalResult.llm_analysis.risk_analysts.neutral.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                          )}

                          <details className="mt-2">
                            <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-700 font-medium mb-2">
                              完整分析 ▼
                            </summary>
                            <div className="mt-2 p-3 bg-white rounded text-xs border border-gray-100 max-h-64 overflow-y-auto">
                              <Markdown content={finalResult.llm_analysis.risk_analysts.neutral.reasoning || finalResult.llm_analysis.risk_analysts.neutral.full_analysis} />
                            </div>
                          </details>
                        </div>
                      )}

                      {finalResult.llm_analysis.risk_analysts.safe && (
                        <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <span className="text-lg">🟢</span>
                              <h5 className="text-sm font-semibold text-green-700">
                                保守派
                              </h5>
                            </div>
                            {finalResult.llm_analysis.risk_analysts.safe.direction && (
                              <span className={`text-xs px-2 py-0.5 rounded font-semibold ${
                                finalResult.llm_analysis.risk_analysts.safe.direction === 'long'
                                  ? 'bg-green-100 text-green-700'
                                  : finalResult.llm_analysis.risk_analysts.safe.direction === 'short'
                                  ? 'bg-red-100 text-red-700'
                                  : 'bg-gray-100 text-gray-700'
                              }`}>
                                {finalResult.llm_analysis.risk_analysts.safe.direction === 'long' ? '看多' :
                                 finalResult.llm_analysis.risk_analysts.safe.direction === 'short' ? '看空' : '持有'}
                              </span>
                            )}
                          </div>

                          {finalResult.llm_analysis.risk_analysts.safe.confidence !== undefined && (
                            <div className="mb-2 flex items-center justify-between text-xs">
                              <span className="text-green-600">置信度</span>
                              <span className="font-semibold text-green-700">
                                {(finalResult.llm_analysis.risk_analysts.safe.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                          )}

                          <details className="mt-2">
                            <summary className="text-xs text-green-600 cursor-pointer hover:text-green-700 font-medium mb-2">
                              完整分析 ▼
                            </summary>
                            <div className="mt-2 p-3 bg-white rounded text-xs border border-green-100 max-h-64 overflow-y-auto">
                              <Markdown content={finalResult.llm_analysis.risk_analysts.safe.reasoning || finalResult.llm_analysis.risk_analysts.safe.full_analysis} />
                            </div>
                          </details>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 风险管理器最终决策 */}
                {finalResult.llm_analysis.risk_manager_decision && (
                  <div>
                    <h4 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                      <span className="w-2 h-2 bg-indigo-500 rounded-full"></span>
                      🛡️ 风险管理器最终决策
                    </h4>
                    <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-200">
                      <Markdown content={finalResult.llm_analysis.risk_manager_decision} />
                    </div>
                  </div>
                )}

                {/* 风险评估 */}
                {finalResult.llm_analysis.risk_assessment &&
                 finalResult.llm_analysis.risk_assessment !== finalResult.llm_analysis.risk_manager_decision && (
                  <div>
                    <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                      <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
                      风险评估
                    </h4>
                    <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-100">
                      <Markdown content={finalResult.llm_analysis.risk_assessment} />
                    </div>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Analysis Error */}
          {showDeepAnalysis && analysisError && (
            <Card title="分析失败" padding="md">
              <div className="text-center text-loss py-8">
                {analysisError}
              </div>
            </Card>
          )}
        </>
      )}

      {/* Agent Full Report Modal */}
      {expandedAgent && (agentResults[expandedAgent] || (finalResult && finalResult.agent_results[expandedAgent])) && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-screen items-center justify-center p-4">
            {/* Backdrop */}
            <div
              className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
              onClick={() => setExpandedAgent(null)}
            ></div>

            {/* Modal */}
            <div className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
              {/* Header */}
              <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
                <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                  <FileText size={20} className="text-primary-500" />
                  {agentNameMap[expandedAgent] || expandedAgent} - 分析详情
                </h2>
                <button
                  onClick={() => setExpandedAgent(null)}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X size={20} className="text-text-secondary" />
                </button>
              </div>

              {/* Content */}
              <div className="px-6 py-4 overflow-y-auto max-h-[calc(90vh-80px)]">
                {(() => {
                  // Try to get full report from agentResults (streaming) or finalResult
                  const fullReport = agentResults[expandedAgent]?.full_report ||
                                    finalResult?.agent_results[expandedAgent]?.full_report;
                  const reasoning = agentResults[expandedAgent]?.reasoning ||
                                   finalResult?.agent_results[expandedAgent]?.reasoning;

                  if (fullReport) {
                    // Show full markdown report
                    return <Markdown content={fullReport} />;
                  } else if (reasoning) {
                    // Show reasoning as fallback
                    return (
                      <div className="space-y-4">
                        <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg">
                          <p className="text-xs text-blue-700 font-medium mb-2">
                            ℹ️ 简要分析理由
                          </p>
                          <p className="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
                            {reasoning}
                          </p>
                        </div>
                        {isAnalyzing && !fullReport && (
                          <div className="text-center py-4">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mx-auto mb-3"></div>
                            <p className="text-sm text-text-secondary">
                              完整报告生成中，请等待分析完成...
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  } else {
                    return (
                      <div className="text-center py-12 text-text-secondary">
                        <p>该Agent未提供详细分析</p>
                      </div>
                    );
                  }
                })()}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
