import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Card } from '@/components/common/Card';
import { Input } from '@/components/common/Input';
import { useStreamingAnalysis } from '@/hooks/useStreamingAnalysis';
import { Search } from 'lucide-react';

export function Analysis() {
  const location = useLocation();
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [searchInput, setSearchInput] = useState('');

  // Use streaming analysis hook
  const {
    agentResults,
    progress,
    isAnalyzing,
    finalResult,
    error: analysisError,
    isLLMAnalyzing,
    startAnalysis,
    stopAnalysis,
  } = useStreamingAnalysis();

  // Handle incoming symbol from navigation state (e.g., from Dashboard)
  useEffect(() => {
    if (location.state?.symbol) {
      const symbol = location.state.symbol;
      setSearchInput(symbol);
      setSelectedSymbol(symbol);
      startAnalysis(symbol);
      // Clear the state to prevent re-triggering
      window.history.replaceState({}, document.title);
    }
  }, [location.state, startAnalysis]);

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      setSelectedSymbol(searchInput.trim());
      startAnalysis(searchInput.trim());
    }
  };

  // Agent name mapping - aligned with backend API_DOCUMENTATION.md
  const agentNameMap: Record<string, string> = {
    technical: '技术分析',    // TradingAgents internal 'market' agent
    fundamental: '基本面分析', // TradingAgents internal 'fundamentals' agent
    sentiment: '情绪分析',     // TradingAgents internal 'sentiment' agent
    policy: '政策分析',        // TradingAgents internal 'news' agent
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">智能分析</h1>
        <p className="text-text-secondary mt-1">基于4个AI代理的综合股票分析</p>
      </div>

      {/* Analysis Form */}
      <Card padding="md">
        <form onSubmit={handleAnalyze} className="flex flex-col sm:flex-row gap-2">
          <div className="flex-1">
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="输入股票代码进行综合分析（如 000001）"
              leftIcon={<Search size={18} />}
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isAnalyzing}
              className="flex-1 sm:flex-none px-4 sm:px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors font-medium disabled:bg-gray-300 disabled:cursor-not-allowed text-sm sm:text-base"
            >
              <span className="hidden sm:inline">{isAnalyzing ? `分析中... (${progress})` : '综合分析'}</span>
              <span className="sm:hidden">{isAnalyzing ? `${progress}` : '分析'}</span>
            </button>
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

      {/* Analysis Results */}
      {isAnalyzing && (
        <Card title={`实时分析进度 - ${selectedSymbol}`} padding="md">
          <div className="space-y-4">
            {/* Progress indicator */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0 p-3 sm:p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center gap-3">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-500"></div>
                <span className="text-xs sm:text-sm font-medium text-text-primary">
                  {isLLMAnalyzing ? 'AI智能分析中...' : `Agent分析进度: ${progress}`}
                </span>
              </div>
              <span className="text-xs text-text-secondary pl-8 sm:pl-0">
                {Object.keys(agentResults).length} 个Agent已完成
              </span>
            </div>

            {/* Real-time agent results */}
            {Object.keys(agentResults).length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {Object.entries(agentResults).map(([name, result]) => (
                  <div
                    key={name}
                    className="p-3 border border-gray-200 rounded-lg bg-white"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-semibold text-text-primary capitalize">
                        {agentNameMap[name] || name}
                      </h4>
                      {result.is_error && (
                        <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded">
                          错误
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <div className={`text-xs font-semibold ${
                        result.direction === 'long'
                          ? 'text-profit'
                          : result.direction === 'short'
                          ? 'text-loss'
                          : 'text-gray-600'
                      }`}>
                        {result.direction === 'long' ? '看多' :
                         result.direction === 'short' ? '看空' :
                         result.direction === null ? '分析中' : '持有'}
                      </div>
                      <div className="text-xs text-text-secondary">
                        {result.confidence > 0 ? `${(result.confidence * 100).toFixed(0)}%` : '-'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      )}

      {finalResult && (
        <div className="space-y-6">
          {/* LLM Analysis - 优先显示AI分析 */}
          {finalResult.llm_analysis && (
            <Card title="🤖 AI综合分析" padding="md">
              <div className="space-y-6">
                {/* 推荐方向和置信度 */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="text-xs text-text-secondary mb-1">推荐方向</div>
                    <div className={`text-xl font-semibold ${
                      finalResult.llm_analysis.recommended_direction === 'long'
                        ? 'text-profit'
                        : finalResult.llm_analysis.recommended_direction === 'short'
                        ? 'text-loss'
                        : 'text-gray-600'
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

                {/* 分析推理 */}
                <div>
                  <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                    <span className="w-2 h-2 bg-primary-500 rounded-full"></span>
                    决策理由
                  </h4>
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                    <p className="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
                      {finalResult.llm_analysis.reasoning}
                    </p>
                  </div>
                </div>

                {/* 风险评估 */}
                {finalResult.llm_analysis.risk_assessment && (
                  <div>
                    <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                      <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                      风险评估
                    </h4>
                    <div className="p-4 bg-orange-50 rounded-lg border border-orange-100">
                      <p className="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
                        {finalResult.llm_analysis.risk_assessment}
                      </p>
                    </div>
                  </div>
                )}

                {/* 关键决策因素 */}
                {finalResult.llm_analysis.key_factors &&
                 finalResult.llm_analysis.key_factors.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                      关键决策因素
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {finalResult.llm_analysis.key_factors.map((factor, index) => (
                        <div
                          key={index}
                          className="p-3 bg-green-50 rounded-lg border border-green-100"
                        >
                          <div className="flex items-start gap-2">
                            <span className="text-xs font-bold text-green-700 mt-0.5">
                              {index + 1}
                            </span>
                            <span className="text-sm text-text-primary flex-1">
                              {factor}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            </Card>
          )}

          {/* Aggregated Signal */}
          {finalResult.aggregated_signal ? (
            <>
              <Card title="综合分析结果" padding="md">
                {/* 综合信号指标 */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="text-xs text-text-secondary mb-1">方向</div>
                    <div className={`text-xl font-semibold ${
                      finalResult.aggregated_signal.direction === 'long'
                        ? 'text-profit'
                        : finalResult.aggregated_signal.direction === 'short'
                        ? 'text-loss'
                        : 'text-gray-600'
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

                {/* 各Agent分析结果 - 精简显示 */}
                <div className="border-t border-gray-200 pt-4">
                  <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                    各Agent分析
                    <span className="text-[10px] text-text-secondary font-normal">(悬停查看详细理由)</span>
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                    {Object.entries(finalResult.agent_results).map(([name, result]) => (
                      <div
                        key={name}
                        className="group relative p-3 border border-gray-200 rounded-lg hover:border-primary-300 hover:shadow-md transition-all cursor-help"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-xs font-semibold text-text-primary">
                            {agentNameMap[name] || name}
                          </h4>
                          {result.is_error && (
                            <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-[10px]">
                              错误
                            </span>
                          )}
                        </div>
                        <div className="space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-text-secondary">方向</span>
                            <span className={`text-xs font-semibold ${
                              result.direction === 'long'
                                ? 'text-profit'
                                : result.direction === 'short'
                                ? 'text-loss'
                                : 'text-gray-600'
                            }`}>
                              {result.direction === 'long' ? '看多' :
                               result.direction === 'short' ? '看空' : '持有'}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-text-secondary">置信度</span>
                            <span className="text-xs font-medium text-text-primary">
                              {(result.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-text-secondary">评分</span>
                            <span className="text-xs font-medium text-text-primary">
                              {(result.score * 100).toFixed(0)}
                            </span>
                          </div>
                        </div>

                        {/* Hover tooltip */}
                        <div className="absolute left-0 right-0 top-full mt-2 z-10 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none">
                          <div className="bg-gray-900 text-white text-xs p-3 rounded-lg shadow-lg max-w-xs">
                            <div className="font-semibold mb-1 text-gray-300">分析理由：</div>
                            <div className="leading-relaxed">{result.reasoning || '无详细说明'}</div>
                            {/* Arrow */}
                            <div className="absolute bottom-full left-4 w-0 h-0 border-l-4 border-r-4 border-b-4 border-transparent border-b-gray-900"></div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            </>
          ) : (
            <Card title="综合分析结果" padding="md">
              <div className="text-center py-6 text-text-secondary mb-6">
                <p className="text-lg font-medium mb-2">综合信号暂时无法生成</p>
                {finalResult.signal_rejection_reason ? (
                  <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg max-w-2xl mx-auto">
                    <p className="text-sm text-yellow-800 font-medium mb-1">原因:</p>
                    <p className="text-sm text-yellow-700">
                      {finalResult.signal_rejection_reason}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm mt-2">可能是由于Agent响应不足或置信度过低</p>
                )}
                <div className="mt-4 text-xs text-text-secondary space-y-1">
                  <p>💡 提示：信号生成需要满足以下条件：</p>
                  <p>• 至少3个Agent达成一致方向</p>
                  <p>• 综合置信度达到60%以上</p>
                </div>
              </div>

              {/* 各Agent分析结果 - 精简显示 */}
              <div className="border-t border-gray-200 pt-4">
                <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                  各Agent分析
                  <span className="text-[10px] text-text-secondary font-normal">(悬停查看详细理由)</span>
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {Object.entries(finalResult.agent_results).map(([name, result]) => (
                    <div
                      key={name}
                      className="group relative p-3 border border-gray-200 rounded-lg hover:border-primary-300 hover:shadow-md transition-all cursor-help"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-xs font-semibold text-text-primary">
                          {agentNameMap[name] || name}
                        </h4>
                        {result.is_error && (
                          <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-[10px]">
                            错误
                          </span>
                        )}
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-text-secondary">方向</span>
                          <span className={`text-xs font-semibold ${
                            result.direction === 'long'
                              ? 'text-profit'
                              : result.direction === 'short'
                              ? 'text-loss'
                              : 'text-gray-600'
                          }`}>
                            {result.direction === 'long' ? '看多' :
                             result.direction === 'short' ? '看空' : '持有'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-text-secondary">置信度</span>
                          <span className="text-xs font-medium text-text-primary">
                            {(result.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] text-text-secondary">评分</span>
                          <span className="text-xs font-medium text-text-primary">
                            {(result.score * 100).toFixed(0)}
                          </span>
                        </div>
                      </div>

                      {/* Hover tooltip */}
                      <div className="absolute left-0 right-0 top-full mt-2 z-10 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none">
                        <div className="bg-gray-900 text-white text-xs p-3 rounded-lg shadow-lg max-w-xs">
                          <div className="font-semibold mb-1 text-gray-300">分析理由：</div>
                          <div className="leading-relaxed">{result.reasoning || '无详细说明'}</div>
                          {/* Arrow */}
                          <div className="absolute bottom-full left-4 w-0 h-0 border-l-4 border-r-4 border-b-4 border-transparent border-b-gray-900"></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {analysisError && (
        <Card title="分析失败" padding="md">
          <div className="text-center text-loss py-8">
            {analysisError}
          </div>
        </Card>
      )}
    </div>
  );
}
