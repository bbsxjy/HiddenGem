from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage
from datetime import datetime
from typing import Tuple

from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.tools.unified_news_tool import create_unified_news_tool
from tradingagents.utils.stock_utils import StockUtils

logger = get_logger("analysts.news")


def create_news_analyst(llm, toolkit):
    @log_analyst_module("news")
    def news_analyst_node(state):
        start_time = datetime.now()
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        
        logger.info(f"[新闻分析师] 开始分析 {ticker} 的新闻，交易日期: {current_date}")
        session_id = state.get("session_id", "未知会话")
        logger.info(f"[新闻分析师] 会话ID: {session_id}，开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 获取市场信息
        market_info = StockUtils.get_market_info(ticker)
        logger.info(f"[新闻分析师] 股票类型: {market_info['market_name']}")
        
        def _get_company_profile(ticker: str, market_info: dict) -> Tuple[str, str]:
            """根据股票代码获取公司名称和行业提示"""
            company_name = f"股票{ticker}"
            sector_hint = ""
            try:
                if market_info['is_china']:
                    from tradingagents.dataflows.interface import get_china_stock_info_unified
                    stock_info = get_china_stock_info_unified(ticker)
                    if "股票名称:" in stock_info:
                        company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
                        logger.debug(f" [DEBUG] 从统一接口获取中国股票名称: {ticker} -> {company_name}")
                    if "所属行业:" in stock_info:
                        raw = stock_info.split("所属行业:")[1].split("\n")[0].strip()
                        sector_hint = raw or sector_hint
                    elif "行业:" in stock_info:
                        raw = stock_info.split("行业:")[1].split("\n")[0].strip()
                        sector_hint = raw or sector_hint
                    if not sector_hint:
                        sector_hint = "A股综合"
                elif market_info['is_hk']:
                    try:
                        from tradingagents.dataflows.improved_hk_utils import get_hk_company_name_improved
                        company_name = get_hk_company_name_improved(ticker)
                        logger.debug(f" [DEBUG] 使用改进港股工具获取名称: {ticker} -> {company_name}")
                    except Exception as e:
                        logger.debug(f" [DEBUG] 改进港股工具获取名称失败: {e}")
                        clean_ticker = ticker.replace('.HK', '').replace('.hk', '')
                        company_name = f"港股{clean_ticker}"
                    sector_hint = "港股核心板块"
                elif market_info['is_us']:
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
                    sector_hint = "美股行业"
                    logger.debug(f" [DEBUG] 美股名称映射: {ticker} -> {company_name}")
                else:
                    company_name = f"股票{ticker}"
                    sector_hint = market_info.get("market_name", "全球市场")
            except Exception as e:
                logger.error(f" [DEBUG] 获取公司名称失败: {e}")
            if not sector_hint:
                market_prefix = str(ticker)[:3]
                prefix_map = {
                    "000": "深市主板",
                    "001": "深市主板",
                    "002": "中小板",
                    "003": "创业板",
                    "300": "创业板",
                    "600": "沪市主板",
                    "601": "沪市主板",
                    "603": "沪市主板",
                    "605": "沪市主板",
                    "688": "科创板"
                }
                sector_hint = prefix_map.get(market_prefix, market_info.get("market_name", "全球市场"))
            return company_name, sector_hint
        
        company_name, sector_hint = _get_company_profile(ticker, market_info)
        logger.info(f"[新闻分析师] 公司名称: {company_name}")
        logger.info(f"[新闻分析师] 行业/板块提示: {sector_hint}")
        
        unified_news_tool = create_unified_news_tool(toolkit)
        unified_news_tool.name = "get_stock_news_unified"
        
        model_info = ""
        try:
            if hasattr(llm, 'model_name'):
                model_info = f"{llm.__class__.__name__}:{llm.model_name}"
            else:
                model_info = llm.__class__.__name__
        except:
            model_info = "Unknown"
        logger.info(f"[新闻分析师] 模型信息: {model_info}")
        
        def _collect_company_news():
            try:
                search_hint = f"{company_name} {sector_hint} {ticker}"
                news = unified_news_tool(
                    stock_code=ticker,
                    max_news=12,
                    model_info=model_info,
                    company_name=company_name,
                    search_keywords=search_hint,
                )
                if news and 'NO_VALID_NEWS_DATA_AVAILABLE' in news:
                    return "", "NO_DATA"
                if news and len(news.strip()) > 80:
                    return news, "OK"
                if news:
                    return news, "INSUFFICIENT"
                return "", "EMPTY"
            except Exception as exc:
                logger.error(f"[新闻分析师] 获取个股新闻失败: {exc}")
                return "", "ERROR"
        
        def _collect_macro_news():
            macro_blocks = []
            try:
                if hasattr(toolkit, "get_global_news_openai"):
                    logger.info("[新闻分析师] 尝试通过 get_global_news_openai 获取宏观新闻")
                    global_news = toolkit.get_global_news_openai.invoke({
                        "curr_date": current_date,
                        "look_back_days": 7,
                        "limit": 6
                    })
                    if global_news and len(global_news.strip()) > 50:
                        macro_blocks.append(f"【全球宏观】\n{global_news}")
            except Exception as exc:
                logger.warning(f"[新闻分析师] get_global_news_openai 调用失败: {exc}")
            queries = [
                f"{market_info['market_name']} 宏观政策 新闻 {current_date}",
                f"{sector_hint} 行业 景气度 新闻",
                f"{market_info['market_name']} 经济 数据 风险"
            ]
            for query in queries:
                try:
                    if hasattr(toolkit, "get_google_news"):
                        result = toolkit.get_google_news.invoke({"query": query, "curr_date": current_date})
                        if result and len(result.strip()) > 50:
                            macro_blocks.append(f"【{query}】\n{result}")
                except Exception as exc:
                    logger.debug(f"[新闻分析师] get_google_news 查询 {query} 失败: {exc}")
            return "\n\n".join(macro_blocks)
        
        company_news, company_status = _collect_company_news()
        if company_status == "NO_DATA":
            report = f"由于无法获取{ticker}的新闻数据（所有新闻源均失败），本次分析无法提供新闻面评估。请稍后重试或尝试其他数据来源。"
            clean_message = AIMessage(content=report)
            return {
                "messages": [clean_message],
                "news_report": report,
            }
        if company_status == "ERROR":
            report = f"获取{ticker}的个股新闻时出现异常，暂无法提供新闻面分析。建议稍后重试。"
            clean_message = AIMessage(content=report)
            return {
                "messages": [clean_message],
                "news_report": report,
            }
        
        macro_news = _collect_macro_news()
        if not macro_news:
            macro_news = "【宏观数据缺失】当前渠道未检索到足够的宏观/政策新闻，请结合市场公开信息谨慎解读。"
        
        company_context_header = "【个股最新新闻】" if company_news else "【个股新闻不足】"
        company_context_body = company_news if company_news else "统一新闻工具返回的数据不足以构成完整脉络，请重点关注公告、交易所披露及记者调查。"
        analysis_context = f"""
### 宏观政策与行业素材
{macro_news}

### {company_context_header}
{company_context_body}
"""
        data_health = {
            "宏观素材有效": "是" if macro_news else "否",
            "个股素材状态": company_status
        }
        logger.info(f"[新闻分析师] 数据摘要: {data_health}")
        
        system_prompt = (
            "你是一名强调宏观+行业+个股联动的资深中文财经新闻分析师。"
            "需要综合宏观政策、行业趋势以及具体公司新闻，为交易决策提供可操作的洞察。"
            "请确保观点建立在提供的材料上，引用关键数据时间点，禁止凭空编造。"
            "输出需严格使用中文，结构清晰，重点可执行。"
        )
        writing_requirements = f"""
分析目标：{company_name}（{ticker}），所属板块/提示：{sector_hint}，交易日：{current_date}（展示为 {state.get('trade_date_display', current_date)}）

撰写要求：
1. 先总结宏观/政策/行业趋势，指出与{sector_hint}及A股/全球市场联动关系。
2. 梳理个股新闻脉络，区分“过往7-14天”与“最近24小时/实时”影响，强调利多/利空权重。
3. 明确给出可能影响价格的催化剂（政策、供需、业绩、市场情绪等）以及潜在波动区间。
4. 针对A股（若适用）说明监管、盘后公告、北向资金、板块轮动等因素；非A股则聚焦对应市场特性。
5. 至少输出三个要点式的风险/机会对照，包含触发条件与应对建议。
6. 最后使用Markdown表格（列示“时间/事件/影响/交易信号”）总结关键新闻与推演结论。
7. 若某部分数据不足，需在段落内显式澄清数据缺口并给出下一步建议。
"""
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "{system_prompt}\n\n=== 提供的背景材料 ===\n{analysis_context}\n\n=== 写作约束 ===\n{writing_requirements}\n"
                    "结合材料和对话上下文完成分析。禁止输出英文，禁止离题。"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        prompt = prompt.partial(
            system_prompt=system_prompt,
            analysis_context=analysis_context,
            writing_requirements=writing_requirements,
        )
        
        logger.info(f"[新闻分析师] 开始生成报告，宏观素材长度: {len(macro_news)}, 个股素材长度: {len(company_context_body)}")
        chain = prompt | llm
        result = chain.invoke({"messages": state["messages"]})
        report = result.content if hasattr(result, "content") else str(result)
        total_time_taken = (datetime.now() - start_time).total_seconds()
        logger.info(f"[新闻分析师] 新闻分析完成，总耗时: {total_time_taken:.2f}秒，报告长度: {len(report)} 字符")
        
        clean_message = AIMessage(content=report)
        return {
            "messages": [clean_message],
            "news_report": report,
        }

    return news_analyst_node
