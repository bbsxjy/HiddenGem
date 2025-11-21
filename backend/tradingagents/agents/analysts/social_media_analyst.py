from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json

# 导入统一日志系统和分析模块日志装饰器
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
logger = get_logger("analysts.social_media")

# 导入Google工具调用处理器
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler


def _get_company_name_for_social_media(ticker: str, market_info: dict) -> str:
    """
    为社交媒体分析师获取公司名称

    Args:
        ticker: 股票代码
        market_info: 市场信息字典

    Returns:
        str: 公司名称
    """
    try:
        if market_info['is_china']:
            # 中国A股：使用统一接口获取股票信息
            from tradingagents.dataflows.interface import get_china_stock_info_unified
            stock_info = get_china_stock_info_unified(ticker)

            # 解析股票名称
            if "股票名称:" in stock_info:
                company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
                logger.debug(f" [社交媒体分析师] 从统一接口获取中国股票名称: {ticker} -> {company_name}")
                return company_name
            else:
                logger.warning(f" [社交媒体分析师] 无法从统一接口解析股票名称: {ticker}")
                return f"股票代码{ticker}"

        elif market_info['is_hk']:
            # 港股：使用改进的港股工具
            try:
                from tradingagents.dataflows.improved_hk_utils import get_hk_company_name_improved
                company_name = get_hk_company_name_improved(ticker)
                logger.debug(f" [社交媒体分析师] 使用改进港股工具获取名称: {ticker} -> {company_name}")
                return company_name
            except Exception as e:
                logger.debug(f" [社交媒体分析师] 改进港股工具获取名称失败: {e}")
                # 降级方案：生成友好的默认名称
                clean_ticker = ticker.replace('.HK', '').replace('.hk', '')
                return f"港股{clean_ticker}"

        elif market_info['is_us']:
            # 美股：使用简单映射或返回代码
            us_stock_names = {
                'AAPL': '苹果公司',
                'TSLA': '特斯拉',
                'NVDA': '英伟达',
                'MSFT': '微软',
                'GOOGL': '谷歌',
                'AMZN': '亚马逊',
                'META': 'Meta',
                'NFLX': '奈飞'
            }

            company_name = us_stock_names.get(ticker.upper(), f"美股{ticker}")
            logger.debug(f" [社交媒体分析师] 美股名称映射: {ticker} -> {company_name}")
            return company_name

        else:
            return f"股票{ticker}"

    except Exception as e:
        logger.error(f" [社交媒体分析师] 获取公司名称失败: {e}")
        return f"股票{ticker}"


def create_social_media_analyst(llm, toolkit):
    @log_analyst_module("social_media")
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        
        # 获取股票市场信息
        from tradingagents.utils.stock_utils import StockUtils
        market_info = StockUtils.get_market_info(ticker)
        
        # 获取公司名称
        company_name = _get_company_name_for_social_media(ticker, market_info)
        logger.info(f"[社交媒体分析师] 公司名称: {company_name}")

        if toolkit.config["online_tools"]:
            #  修复：根据市场类型选择合适的新闻工具
            if market_info['is_china']:
                # 中国股票：使用支持中文财经新闻源的工具（解决404问题）
                logger.info(f"[社交媒体分析师] 检测到中国股票 {ticker}，使用中文新闻源")
                tools = [
                    toolkit.get_realtime_stock_news,      # 支持东方财富等中文新闻源
                    toolkit.get_chinese_social_sentiment,  # 雪球、股吧等中文社交媒体
                ]
            else:
                # 美股/港股：使用 OpenAI web search
                logger.info(f"[社交媒体分析师] 检测到海外股票 {ticker}，使用 OpenAI 新闻源")
                tools = [toolkit.get_stock_news_openai]
        else:
            # 优先使用中国社交媒体数据，如果不可用则回退到Reddit
            tools = [
                toolkit.get_chinese_social_sentiment,
                toolkit.get_reddit_stock_info,
            ]

        system_message = (
            """您是一位专业的中国市场社交媒体和投资情绪分析师，负责分析中国投资者对特定股票的讨论和情绪变化。

您的主要职责包括：
1. 分析中国主要财经平台的投资者情绪（如雪球、东方财富股吧等）
2. 监控财经媒体和新闻对股票的报道倾向
3. 识别影响股价的热点事件和市场传言
4. 评估散户与机构投资者的观点差异
5. 分析政策变化对投资者情绪的影响
6. 评估情绪变化对股价的潜在影响

重点关注平台：
- 财经新闻：财联社、新浪财经、东方财富、腾讯财经
- 投资社区：雪球、东方财富股吧、同花顺
- 社交媒体：微博财经大V、知乎投资话题
- 专业分析：各大券商研报、财经自媒体

分析要点：
- 投资者情绪的变化趋势和原因
- 关键意见领袖(KOL)的观点和影响力
- 热点事件对股价预期的影响
- 政策解读和市场预期变化
- 散户情绪与机构观点的差异

 情绪价格影响分析要求：
- 量化投资者情绪强度（乐观/悲观程度）
- 评估情绪变化对短期股价的影响（1-5天）
- 分析散户情绪与股价走势的相关性
- 识别情绪驱动的价格支撑位和阻力位
- 提供基于情绪分析的价格预期调整
- 评估市场情绪对估值的影响程度
- 不允许回复'无法评估情绪影响'或'需要更多数据'

 必须包含：
- 情绪指数评分（1-10分）
- 预期价格波动幅度
- 基于情绪的交易时机建议

请撰写详细的中文分析报告，并在报告末尾附上Markdown表格总结关键发现。
注意：由于中国社交媒体API限制，如果数据获取受限，请明确说明并提供替代分析建议。"""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "您是一位有用的AI助手，与其他助手协作。"
                    "\n"
                    "\n **当前分析目标**："
                    "\n- **股票代码**: {ticker}"
                    "\n- **公司名称**: {company_name}"
                    "\n"
                    "\n **严格约束 - 股票代码与公司名称一致性**："
                    "\n- 您正在分析的股票代码是 {ticker}，公司名称是 {company_name}"
                    "\n- **绝对禁止**: 使用错误的公司名称！如果不确定，请使用'{ticker}'而不是猜测公司名！"
                    "\n- **工具失败时**: 如果工具返回404或错误，明确说明'无法获取数据'，不要凭记忆编造公司信息！"
                    "\n- **数据来源**: 所有分析内容必须基于工具返回的真实数据，不要引用你的知识库中的其他股票！"
                    "\n"
                    "\n使用提供的工具来推进回答问题。"
                    " 如果您无法完全回答，没关系；具有不同工具的其他助手"
                    " 将从您停下的地方继续帮助。执行您能做的以取得进展。"
                    " 如果您或任何其他助手有最终交易提案：**买入/持有/卖出**或可交付成果，"
                    " 请在您的回应前加上最终交易提案：**买入/持有/卖出**，以便团队知道停止。"
                    " 您可以访问以下工具：{tool_names}。\n{system_message}"
                    "供您参考，当前日期是{current_date}。我们要分析的当前公司是{ticker}。请用中文撰写所有分析内容。",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        # 安全地获取工具名称，处理函数和工具对象
        tool_names = []
        for tool in tools:
            if hasattr(tool, 'name'):
                tool_names.append(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))

        prompt = prompt.partial(tool_names=", ".join(tool_names))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)
        prompt = prompt.partial(company_name=company_name)  # 添加公司名称

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        # 使用统一的Google工具调用处理器
        if GoogleToolCallHandler.is_google_model(llm):
            logger.info(f" [社交媒体分析师] 检测到Google模型，使用统一工具调用处理器")
            
            # 创建分析提示词
            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="社交媒体情绪分析",
                specific_requirements="重点关注投资者情绪、社交媒体讨论热度、舆论影响等。"
            )
            
            # 处理Google模型工具调用
            report, messages = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="社交媒体分析师"
            )
        else:
            # 非Google模型的处理逻辑
            logger.debug(f" [DEBUG] 非Google模型 ({llm.__class__.__name__})，使用标准处理逻辑")

            report = ""
            if len(result.tool_calls) == 0:
                # 没有工具调用，直接使用LLM的回复
                logger.warning(f" [社交媒体分析师] LLM没有调用工具，尝试强制执行工具获取数据")

                # 🆕 强制执行工具获取数据（降级方案）
                try:
                    from langchain_core.messages import HumanMessage

                    forced_tool_results = []

                    # 强制调用get_realtime_stock_news
                    logger.info(f" [社交媒体分析师] 强制调用 get_realtime_stock_news")
                    try:
                        news_tool = None
                        for tool in tools:
                            tool_name = getattr(tool, 'name', getattr(tool, '__name__', None))
                            if tool_name == 'get_realtime_stock_news':
                                news_tool = tool
                                break

                        if news_tool:
                            news_result = news_tool.invoke({'ticker': ticker, 'curr_date': current_date})

                            # 检查是否包含无新闻标记
                            if news_result and 'NO_VALID_NEWS_DATA_AVAILABLE' in str(news_result):
                                logger.warning(f" [社交媒体分析师] 检测到无新闻数据标记，跳过新闻数据")
                            elif news_result and len(str(news_result).strip()) > 100:
                                forced_tool_results.append(f"### 实时新闻数据\n{news_result}\n\n")
                                logger.info(f" [社交媒体分析师] 成功获取实时新闻，长度: {len(news_result)}")
                            else:
                                logger.warning(f" [社交媒体分析师] 实时新闻数据为空或过短")
                        else:
                            logger.warning(f" [社交媒体分析师] 未找到get_realtime_stock_news工具")
                    except Exception as e:
                        logger.error(f" [社交媒体分析师] 获取实时新闻失败: {e}")

                    # 强制调用get_chinese_social_sentiment
                    logger.info(f" [社交媒体分析师] 强制调用 get_chinese_social_sentiment")
                    try:
                        sentiment_tool = None
                        for tool in tools:
                            tool_name = getattr(tool, 'name', getattr(tool, '__name__', None))
                            if tool_name == 'get_chinese_social_sentiment':
                                sentiment_tool = tool
                                break

                        if sentiment_tool:
                            sentiment_result = sentiment_tool.invoke({'ticker': ticker, 'curr_date': current_date})
                            forced_tool_results.append(f"### 社交媒体情绪数据\n{sentiment_result}\n\n")
                            logger.info(f" [社交媒体分析师] 成功获取社交媒体情绪，长度: {len(sentiment_result)}")
                        else:
                            logger.warning(f" [社交媒体分析师] 未找到get_chinese_social_sentiment工具")
                    except Exception as e:
                        logger.error(f" [社交媒体分析师] 获取社交媒体情绪失败: {e}")

                    # 如果成功获取到数据，让LLM基于数据生成分析
                    if forced_tool_results:
                        logger.info(f" [社交媒体分析师] 强制工具调用成功，获取到{len(forced_tool_results)}个数据源")

                        tool_data = "\n".join(forced_tool_results)

                        # 构建分析消息
                        analysis_messages = state["messages"] + [result]
                        analysis_instruction = HumanMessage(
                            content=f"""你是社交媒体情绪分析师，正在分析{ticker}（{company_name}）。

以下是我为你获取的真实数据：

{tool_data}

请基于以上真实数据，撰写完整的社交媒体情绪分析报告。

报告必须包含以下内容：
1. **投资者情绪分析**：基于真实数据分析当前投资者的整体情绪倾向
2. **热点事件识别**：从新闻和讨论中识别影响股价的关键事件
3. **舆论影响评估**：评估社交媒体讨论对股价的潜在影响
4. **情绪指数评分**：给出1-10分的情绪指数（必须量化）
5. **价格波动预期**：基于情绪分析预测短期价格波动幅度（必须给出具体百分比）
6. **交易建议**：基于情绪分析提供交易时机建议（买入/持有/卖出）

 重要要求：
- 所有分析必须基于上述真实数据
- 不要说"无法获取数据"，数据已经提供
- 必须给出明确的情绪指数和价格预期
- 报告长度至少800字
- 使用中文撰写

请开始撰写详细的分析报告："""
                        )
                        analysis_messages.append(analysis_instruction)

                        # 生成最终分析
                        final_result = llm.invoke(analysis_messages)
                        report = final_result.content
                        logger.info(f" [社交媒体分析师] 基于强制工具调用生成分析，报告长度: {len(report)}")
                    else:
                        # 如果强制工具调用也失败了，使用LLM的原始回复
                        report = result.content
                        logger.warning(f" [社交媒体分析师] 强制工具调用失败，使用LLM原始回复，长度: {len(report)}")

                except Exception as e:
                    logger.error(f" [社交媒体分析师] 强制工具调用处理失败: {e}", exc_info=True)
                    report = result.content
            else:
                # 有工具调用，执行工具并生成完整分析报告
                logger.info(f" [社交媒体分析师] 检测到工具调用: {[call.get('name', 'unknown') for call in result.tool_calls]}")

                try:
                    # 执行工具调用
                    from langchain_core.messages import ToolMessage, HumanMessage

                    tool_messages = []
                    for tool_call in result.tool_calls:
                        tool_name = tool_call.get('name')
                        tool_args = tool_call.get('args', {})
                        tool_id = tool_call.get('id')

                        logger.info(f" [社交媒体分析师] 执行工具: {tool_name}, 参数: {tool_args}")

                        # 找到对应的工具并执行
                        tool_result = None
                        for tool in tools:
                            # 安全地获取工具名称进行比较
                            current_tool_name = None
                            if hasattr(tool, 'name'):
                                current_tool_name = tool.name
                            elif hasattr(tool, '__name__'):
                                current_tool_name = tool.__name__

                            if current_tool_name == tool_name:
                                try:
                                    tool_result = tool.invoke(tool_args)

                                    # 检查工具返回结果是否包含无新闻标记
                                    if tool_result and 'NO_VALID_NEWS_DATA_AVAILABLE' in str(tool_result):
                                        logger.warning(f" [社交媒体分析师] 工具{tool_name}检测到无新闻数据标记")
                                        tool_result = f"注意：无法获取{ticker}的新闻数据（所有新闻源均失败）。建议基于其他数据源进行分析。"

                                    logger.info(f" [社交媒体分析师] 工具执行成功，结果长度: {len(str(tool_result))}")
                                    break
                                except Exception as tool_error:
                                    logger.error(f" [社交媒体分析师] 工具执行失败: {tool_error}", exc_info=True)
                                    tool_result = f"工具执行失败: {str(tool_error)}"

                        if tool_result is None:
                            tool_result = f"未找到工具: {tool_name}"
                            logger.error(f" [社交媒体分析师] 未找到工具: {tool_name}")

                        # 创建工具消息
                        tool_message = ToolMessage(
                            content=str(tool_result),
                            tool_call_id=tool_id
                        )
                        tool_messages.append(tool_message)

                    # 将工具结果反馈给LLM生成最终分析
                    logger.info(f" [社交媒体分析师] 工具执行完成，共{len(tool_messages)}个工具调用，准备生成最终分析")

                    # 构建完整消息历史
                    analysis_messages = state["messages"] + [result] + tool_messages

                    # 添加分析指令
                    analysis_instruction = HumanMessage(
                        content=f"""请基于上述工具返回的真实数据，为{ticker}（{company_name}）撰写完整的社交媒体情绪分析报告。

报告必须包含以下内容：
1. **投资者情绪分析**：基于真实数据分析当前投资者的整体情绪倾向
2. **热点事件识别**：从新闻和讨论中识别影响股价的关键事件
3. **舆论影响评估**：评估社交媒体讨论对股价的潜在影响
4. **情绪指数评分**：给出1-10分的情绪指数
5. **价格波动预期**：基于情绪分析预测短期价格波动幅度
6. **交易建议**：基于情绪分析提供交易时机建议

 重要提示：
- 所有分析必须基于工具返回的真实数据
- 不要引用记忆中的其他公司信息
- 如果数据不足，明确说明并提供替代建议
- 报告长度至少800字

请开始撰写详细的分析报告（使用中文）："""
                    )
                    analysis_messages.append(analysis_instruction)

                    # 生成最终分析
                    final_result = llm.invoke(analysis_messages)
                    report = final_result.content
                    logger.info(f" [社交媒体分析师] 最终分析生成完成，报告长度: {len(report)}")

                except Exception as e:
                    logger.error(f" [社交媒体分析师] 工具调用处理失败: {e}", exc_info=True)
                    report = f"工具调用处理失败: {str(e)}"

        return {
            "messages": [result],
            "sentiment_report": report,
        }

    return social_media_analyst_node
