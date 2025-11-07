import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Card } from '@/components/common/Card';
import { Input } from '@/components/common/Input';
import { Markdown } from '@/components/common/Markdown';
import { useStreamingAnalysis } from '@/hooks/useStreamingAnalysis';
import { PositionAnalysis } from '@/components/agents/PositionAnalysis';
import { getDirectionColor } from '@/utils/format';
import { Search, TrendingUp, Briefcase, FileText, X } from 'lucide-react';

type AnalysisMode = 'market' | 'position';

export function Analysis() {
  const location = useLocation();
  const [mode, setMode] = useState<AnalysisMode>('market');
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  // Use streaming analysis hook
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

  // Handle incoming symbol from navigation state (e.g., from Dashboard)
  useEffect(() => {
    if (location.state?.symbol) {
      const symbol = location.state.symbol;
      setSearchInput(symbol);
      setSelectedSymbol(symbol);
      if (mode === 'market') {
        startAnalysis(symbol);
      }
      // Clear the state to prevent re-triggering
      window.history.replaceState({}, document.title);
    }
  }, [location.state, startAnalysis, mode]);

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

      {/* Mode Selector */}
      <div className="flex gap-2 border-b border-gray-200">
        <button
          onClick={() => setMode('market')}
          className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors border-b-2 ${
            mode === 'market'
              ? 'text-primary-500 border-primary-500'
              : 'text-text-secondary border-transparent hover:text-text-primary'
          }`}
        >
          <TrendingUp size={18} />
          市场分析
        </button>
        <button
          onClick={() => setMode('position')}
          className={`flex items-center gap-2 px-4 py-3 font-medium transition-colors border-b-2 ${
            mode === 'position'
              ? 'text-primary-500 border-primary-500'
              : 'text-text-secondary border-transparent hover:text-text-primary'
          }`}
        >
          <Briefcase size={18} />
          持仓分析
        </button>
      </div>

      {/* Market Analysis Mode */}
      {mode === 'market' && (
        <>
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

          {/* Real-time Analysis Results */}
          {(isAnalyzing || Object.keys(agentResults).length > 0) && (
            <Card title={`实时分析 - ${selectedSymbol}`} padding="md">
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
                        {Object.keys(agentResults).length} / 4 个Agent已完成
                      </span>
                      <span className="text-xs font-semibold text-primary-600">
                        {progressPercent.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
                {/* Aggregated Signal */}
                {finalResult?.aggregated_signal ? (
                    <Card title="综合分析结果" padding="md">
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
                    </Card>
                ) : (
                    <Card title="综合分析结果" padding="md">
                      <div className="text-center py-6 text-text-secondary">
                        <p className="text-lg font-medium mb-2">综合信号暂时无法生成</p>
                        {finalResult?.signal_rejection_reason ? (
                            <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg max-w-2xl mx-auto">
                              <p className="text-sm text-yellow-800 font-medium mb-1">原因:</p>
                              <p className="text-sm text-yellow-700">
                                {finalResult.signal_rejection_reason}
                              </p>
                            </div>
                        ) : (
                            <p className="text-sm mt-2">可能是由于Agent响应不足或置信度过低</p>
                        )}
                      </div>
                    </Card>
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

          {/* Analysis Results (rest of the content - keeping the same as before) */}
          {finalResult && (
            <div className="space-y-6">
              {/* LLM Analysis - AI综合分析  */}
              {finalResult && finalResult.llm_analysis && (
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

                    {/* 分析推理 - 使用 Markdown 渲染 */}
                    <div>
                      <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                        <span className="w-2 h-2 bg-primary-500 rounded-full"></span>
                        决策理由
                      </h4>
                      <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                        <Markdown content={finalResult.llm_analysis.reasoning} />
                      </div>
                    </div>

                    {/* 🆕 风险分析师意见 (risky/safe/neutral) */}
                    {finalResult.llm_analysis.risk_analysts &&
                     Object.keys(finalResult.llm_analysis.risk_analysts).length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                          <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
                          风险分析师意见
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          {finalResult.llm_analysis.risk_analysts.risky && (
                            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-lg">🔴</span>
                                <h5 className="text-sm font-semibold text-red-700">
                                  激进派
                                </h5>
                              </div>
                              <p className="text-xs text-text-primary leading-relaxed">
                                {finalResult.llm_analysis.risk_analysts.risky.reasoning}
                              </p>
                              {finalResult.llm_analysis.risk_analysts.risky.full_analysis && (
                                <details className="mt-2">
                                  <summary className="text-xs text-red-600 cursor-pointer hover:text-red-700">
                                    查看完整分析
                                  </summary>
                                  <div className="mt-2 p-2 bg-white rounded text-xs">
                                    <Markdown content={finalResult.llm_analysis.risk_analysts.risky.full_analysis} />
                                  </div>
                                </details>
                              )}
                            </div>
                          )}

                          {finalResult.llm_analysis.risk_analysts.neutral && (
                            <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-lg">⚪</span>
                                <h5 className="text-sm font-semibold text-gray-700">
                                  中立派
                                </h5>
                              </div>
                              <p className="text-xs text-text-primary leading-relaxed">
                                {finalResult.llm_analysis.risk_analysts.neutral.reasoning}
                              </p>
                              {finalResult.llm_analysis.risk_analysts.neutral.full_analysis && (
                                <details className="mt-2">
                                  <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-700">
                                    查看完整分析
                                  </summary>
                                  <div className="mt-2 p-2 bg-white rounded text-xs">
                                    <Markdown content={finalResult.llm_analysis.risk_analysts.neutral.full_analysis} />
                                  </div>
                                </details>
                              )}
                            </div>
                          )}

                          {finalResult.llm_analysis.risk_analysts.safe && (
                            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                              <div className="flex items-center gap-2 mb-2">
                                <span className="text-lg">🟢</span>
                                <h5 className="text-sm font-semibold text-green-700">
                                  保守派
                                </h5>
                              </div>
                              <p className="text-xs text-text-primary leading-relaxed">
                                {finalResult.llm_analysis.risk_analysts.safe.reasoning}
                              </p>
                              {finalResult.llm_analysis.risk_analysts.safe.full_analysis && (
                                <details className="mt-2">
                                  <summary className="text-xs text-green-600 cursor-pointer hover:text-green-700">
                                    查看完整分析
                                  </summary>
                                  <div className="mt-2 p-2 bg-white rounded text-xs">
                                    <Markdown content={finalResult.llm_analysis.risk_analysts.safe.full_analysis} />
                                  </div>
                                </details>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* 🆕 风险管理器最终决策 */}
                    {finalResult.llm_analysis.risk_manager_decision && (
                      <div>
                        <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
                          <span className="w-2 h-2 bg-indigo-500 rounded-full"></span>
                          风险管理器最终决策
                        </h4>
                        <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-100">
                          <Markdown content={finalResult.llm_analysis.risk_manager_decision} />
                        </div>
                      </div>
                    )}
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
        </>
      )}

      {/* Position Analysis Mode */}
      {mode === 'position' && (
        <>
          {/* Stock Symbol Input */}
          <Card padding="md">
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="flex-1">
                <Input
                  value={selectedSymbol}
                  onChange={(e) => setSelectedSymbol(e.target.value)}
                  placeholder="输入股票代码（如 300502）"
                  leftIcon={<Search size={18} />}
                />
              </div>
            </div>
          </Card>

          {/* Position Analysis Component */}
          {selectedSymbol && <PositionAnalysis symbol={selectedSymbol} />}

          {!selectedSymbol && (
            <Card padding="md">
              <div className="text-center py-12 text-text-secondary">
                <Briefcase size={48} className="mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium mb-2">请输入股票代码</p>
                <p className="text-sm">输入您持有的股票代码以开始持仓分析</p>
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
                  // Try to get full report from finalResult first, fallback to agentResults
                  const fullReport = finalResult?.agent_results[expandedAgent]?.full_report;
                  const reasoning = agentResults[expandedAgent]?.reasoning ||
                                   finalResult?.agent_results[expandedAgent]?.reasoning;

                  if (fullReport) {
                    // Show full markdown report
                    return <Markdown content={fullReport} />;
                  } else if (reasoning) {
                    // Show reasoning as fallback (during streaming or if full_report not available)
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
                        {isAnalyzing && (
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
