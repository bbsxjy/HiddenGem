#!/usr/bin/env python3
"""
统一新闻分析工具
整合A股、港股、美股等不同市场的新闻获取逻辑到一个工具函数中
让大模型只需要调用一个工具就能获取所有类型股票的新闻数据
"""

import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class UnifiedNewsAnalyzer:
    """统一新闻分析器，整合所有新闻获取逻辑"""
    
    def __init__(self, toolkit):
        """初始化统一新闻分析器
        
        Args:
            toolkit: 包含各种新闻获取工具的工具包
        """
        self.toolkit = toolkit
        
    def get_stock_news_unified(
        self,
        stock_code: str,
        max_news: int = 10,
        model_info: str = "",
        company_name: str = "",
        search_keywords: str = "",
    ) -> str:
        """
        ?????????????????????

        Args:
            stock_code: ????
            max_news: ??????
            model_info: ??????????????
            company_name: ?????????
            search_keywords: ????????/?????

        Returns:
            str: ?????????
        """

        logger.info(f"[统一新闻工具] 开始获取 {stock_code} 的新闻，模型: {model_info}")
        logger.info(f"[统一新闻工具]  当前模型信息: {model_info}")

        # ====== 新增：详细的工具调用日志 ======
        logger.info(f"[工具调用] ========== 统一新闻工具调用开始 ==========")
        logger.info(f"[工具调用] 股票代码: {stock_code}")
        logger.info(f"[工具调用] 最大新闻数: {max_news}")
        logger.info(f"[工具调用] 模型信息: {model_info}")
        # ====== 新增结束 ======

        # 识别股票类型
        stock_type = self._identify_stock_type(stock_code)
        logger.info(f"[统一新闻工具] 股票类型: {stock_type}")
        logger.info(f"[工具调用] 识别的股票类型: {stock_type}")  # 新增

        # 根据股票类型调用相应的获取方法
        if stock_type == "A?":
            result = self._get_a_share_news(
                stock_code,
                max_news,
                model_info,
                company_name=company_name,
                search_keywords=search_keywords,
            )
        elif stock_type == "??":
            result = self._get_hk_share_news(
                stock_code,
                max_news,
                model_info,
                company_name=company_name,
                search_keywords=search_keywords,
            )
        elif stock_type == "??":
            result = self._get_us_share_news(
                stock_code,
                max_news,
                model_info,
                company_name=company_name,
                search_keywords=search_keywords,
            )
        else:
            # ????A???
            result = self._get_a_share_news(
                stock_code,
                max_news,
                model_info,
                company_name=company_name,
                search_keywords=search_keywords,
            )
        # ====== 新增：工具返回结果日志 ======
        logger.info(f"[工具调用] ========== 统一新闻工具调用结束 ==========")
        logger.info(f"[工具调用] 返回结果长度: {len(result)} 字符")
        logger.info(f"[工具调用] 返回结果完整内容:")
        logger.info(f"[工具调用] {result}")
        logger.info(f"[工具调用] ========== 工具调用详情结束 ==========")
        # ====== 新增结束 ======

        # 如果结果为空或过短，记录警告
        if not result or len(result.strip()) < 50:
            logger.warning(f"[统一新闻工具]  返回结果异常短或为空！")
            logger.warning(f"[统一新闻工具]  完整结果内容: '{result}'")

        return result
    
    def _identify_stock_type(self, stock_code: str) -> str:
        """识别股票类型"""
        stock_code = stock_code.upper().strip()
        
        # A股判断
        if re.match(r'^(00|30|60|68)\d{4}$', stock_code):
            return "A股"
        elif re.match(r'^(SZ|SH)\d{6}$', stock_code):
            return "A股"
        
        # 港股判断
        elif re.match(r'^\d{4,5}\.HK$', stock_code):
            return "港股"
        elif re.match(r'^\d{4,5}$', stock_code) and len(stock_code) <= 5:
            return "港股"
        
        # 美股判断
        elif re.match(r'^[A-Z]{1,5}$', stock_code):
            return "美股"
        elif '.' in stock_code and not stock_code.endswith('.HK'):
            return "美股"
        
        # 默认按A股处理
        else:
            return "A股"
    
    def _get_a_share_news(
        self,
        stock_code: str,
        max_news: int,
        model_info: str = "",
        company_name: str = "",
        search_keywords: str = "",
    ) -> str:
        """获取A股新闻"""
        logger.info(f"[统一新闻工具] 获取A股 {stock_code} 新闻")
        
        # 获取当前日期
        curr_date = datetime.now().strftime("%Y-%m-%d")
        
        # 优先级1: 东方财富实时新闻
        try:
            if hasattr(self.toolkit, 'get_realtime_stock_news'):
                logger.info(f"[统一新闻工具] 尝试东方财富实时新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_realtime_stock_news.invoke({"ticker": stock_code, "curr_date": curr_date})

                #  详细记录东方财富返回的内容
                logger.info(f"[统一新闻工具]  东方财富返回类型: {type(result)}")
                logger.info(f"[统一新闻工具]  东方财富返回内容长度: {len(result) if result else 0} 字符")
                if result:
                    logger.info(f"[统一新闻工具]  东方财富返回内容预览 (前500字符): {result[:500]}")
                else:
                    logger.info(f"[统一新闻工具]  东方财富返回None，表示无可用新闻数据")

                # 检查是否为None（表示无新闻数据）
                if result is None:
                    logger.warning(f"[统一新闻工具]  东方财富未获取到新闻数据（None），将尝试其他新闻源")
                elif result and len(result.strip()) > 100:
                    logger.info(f"[统一新闻工具]  东方财富新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "东方财富实时新闻", model_info)
                else:
                    logger.warning(f"[统一新闻工具]  东方财富新闻内容过短")
        except Exception as e:
            logger.warning(f"[统一新闻工具] 东方财富新闻获取失败: {e}")
        
        # 优先级2: Google新闻（中文搜索）
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                logger.info(f"[统一新闻工具] 尝试Google新闻...")
                query = f"{stock_code} 股票 新闻 财报 业绩"
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_google_news.invoke({"query": query, "curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具]  Google新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "Google新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] Google新闻获取失败: {e}")
        
        # 优先级3: OpenAI全球新闻
        try:
            if hasattr(self.toolkit, 'get_global_news_openai'):
                logger.info(f"[统一新闻工具] 尝试OpenAI全球新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_global_news_openai.invoke({"curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具]  OpenAI新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "OpenAI全球新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] OpenAI新闻获取失败: {e}")
        try:
            keywords = self._build_keyword_list(stock_code, company_name, search_keywords)
            tushare_news = self._get_tushare_keyword_news(stock_code, keywords, max_news)
            if tushare_news:
                logger.info(f"[??????]  Tushare????????: {len(tushare_news)}")
                return self._format_news_result(tushare_news, "Tushare????", model_info)
        except Exception as e:
            logger.warning(f"[??????] Tushare??????: {e}")

        
        return """
=== NO_VALID_NEWS_DATA_AVAILABLE ===
状态: 无可用新闻数据
原因: 所有A股新闻源均未返回有效数据（Tushare、财联社、华尔街见闻、Google等均失败）

重要说明:
- 本标记表明确实无法获取任何新闻数据，而非数据存在但为空
- 所有可用的新闻API均已尝试但返回失败或空数据
- 这不是技术错误，而是当前时间段内确实无相关新闻

强制要求:
1. 必须立即停止新闻分析流程
2. 不得基于任何假设、推测或记忆编造新闻相关内容
3. 必须明确告知用户无法提供新闻面评估
4. 建议用户稍后重试或使用其他数据源（技术分析、基本面分析等）

=== NO_VALID_NEWS_DATA_AVAILABLE ===
"""
    
    def _get_hk_share_news(
        self,
        stock_code: str,
        max_news: int,
        model_info: str = "",
        company_name: str = "",
        search_keywords: str = "",
    ) -> str:
        """获取港股新闻"""
        logger.info(f"[统一新闻工具] 获取港股 {stock_code} 新闻")
        
        # 获取当前日期
        curr_date = datetime.now().strftime("%Y-%m-%d")
        
        # 优先级1: Google新闻（港股搜索）
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                logger.info(f"[统一新闻工具] 尝试Google港股新闻...")
                query = f"{stock_code} 港股 香港股票 新闻"
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_google_news.invoke({"query": query, "curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具]  Google港股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "Google港股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] Google港股新闻获取失败: {e}")
        
        # 优先级2: OpenAI全球新闻
        try:
            if hasattr(self.toolkit, 'get_global_news_openai'):
                logger.info(f"[统一新闻工具] 尝试OpenAI港股新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_global_news_openai.invoke({"curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具]  OpenAI港股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "OpenAI港股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] OpenAI港股新闻获取失败: {e}")
        
        # 优先级3: 实时新闻（如果支持港股）
        try:
            if hasattr(self.toolkit, 'get_realtime_stock_news'):
                logger.info(f"[统一新闻工具] 尝试实时港股新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_realtime_stock_news.invoke({"ticker": stock_code, "curr_date": curr_date})
                if result and len(result.strip()) > 100:
                    logger.info(f"[统一新闻工具]  实时港股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "实时港股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] 实时港股新闻获取失败: {e}")
        
        return """
=== NO_VALID_NEWS_DATA_AVAILABLE ===
状态: 无可用新闻数据
原因: 所有港股新闻源均未返回有效数据（Google、OpenAI、实时新闻等均失败）

重要说明:
- 本标记表明确实无法获取任何新闻数据，而非数据存在但为空
- 所有可用的新闻API均已尝试但返回失败或空数据
- 这不是技术错误，而是当前时间段内确实无相关新闻

强制要求:
1. 必须立即停止新闻分析流程
2. 不得基于任何假设、推测或记忆编造新闻相关内容
3. 必须明确告知用户无法提供新闻面评估
4. 建议用户稍后重试或使用其他数据源（技术分析、基本面分析等）

=== NO_VALID_NEWS_DATA_AVAILABLE ===
"""
    
    def _get_us_share_news(
        self,
        stock_code: str,
        max_news: int,
        model_info: str = "",
        company_name: str = "",
        search_keywords: str = "",
    ) -> str:
        """获取美股新闻"""
        logger.info(f"[统一新闻工具] 获取美股 {stock_code} 新闻")
        
        # 获取当前日期
        curr_date = datetime.now().strftime("%Y-%m-%d")
        
        # 优先级1: OpenAI全球新闻
        try:
            if hasattr(self.toolkit, 'get_global_news_openai'):
                logger.info(f"[统一新闻工具] 尝试OpenAI美股新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_global_news_openai.invoke({"curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具]  OpenAI美股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "OpenAI美股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] OpenAI美股新闻获取失败: {e}")
        
        # 优先级2: Google新闻（英文搜索）
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                logger.info(f"[统一新闻工具] 尝试Google美股新闻...")
                query = f"{stock_code} stock news earnings financial"
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_google_news.invoke({"query": query, "curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具]  Google美股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "Google美股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] Google美股新闻获取失败: {e}")
        
        # 优先级3: FinnHub新闻（如果可用）
        try:
            if hasattr(self.toolkit, 'get_finnhub_news'):
                logger.info(f"[统一新闻工具] 尝试FinnHub美股新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_finnhub_news.invoke({"symbol": stock_code, "max_results": min(max_news, 50)})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具]  FinnHub美股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "FinnHub美股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] FinnHub美股新闻获取失败: {e}")
        
        return """
=== NO_VALID_NEWS_DATA_AVAILABLE ===
状态: 无可用新闻数据
原因: 所有美股新闻源均未返回有效数据（OpenAI、Google、FinnHub等均失败）

重要说明:
- 本标记表明确实无法获取任何新闻数据，而非数据存在但为空
- 所有可用的新闻API均已尝试但返回失败或空数据
- 这不是技术错误，而是当前时间段内确实无相关新闻

强制要求:
1. 必须立即停止新闻分析流程
2. 不得基于任何假设、推测或记忆编造新闻相关内容
3. 必须明确告知用户无法提供新闻面评估
4. 建议用户稍后重试或使用其他数据源（技术分析、基本面分析等）

=== NO_VALID_NEWS_DATA_AVAILABLE ===
"""
    
    def _format_news_result(self, news_content: str, source: str, model_info: str = "") -> str:
        """格式化新闻结果"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        #  添加调试日志：打印原始新闻内容
        logger.info(f"[统一新闻工具]  原始新闻内容预览 (前500字符): {news_content[:500]}")
        logger.info(f"[统一新闻工具]  原始内容长度: {len(news_content)} 字符")
        
        # 检测是否为Google/Gemini模型
        is_google_model = any(keyword in model_info.lower() for keyword in ['google', 'gemini', 'gemma'])
        original_length = len(news_content)
        google_control_applied = False
        
        #  添加Google模型检测日志
        if is_google_model:
            logger.info(f"[统一新闻工具]  检测到Google模型，启用特殊处理")
        
        # 对Google模型进行特殊的长度控制
        if is_google_model and len(news_content) > 5000:  # 降低阈值到5000字符
            logger.warning(f"[统一新闻工具]  检测到Google模型，新闻内容过长({len(news_content)}字符)，进行长度控制...")
            
            # 更严格的长度控制策略
            lines = news_content.split('\n')
            important_lines = []
            char_count = 0
            target_length = 3000  # 目标长度设为3000字符
            
            # 第一轮：优先保留包含关键词的重要行
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 检查是否包含重要关键词
                important_keywords = ['股票', '公司', '财报', '业绩', '涨跌', '价格', '市值', '营收', '利润', 
                                    '增长', '下跌', '上涨', '盈利', '亏损', '投资', '分析', '预期', '公告']
                
                is_important = any(keyword in line for keyword in important_keywords)
                
                if is_important and char_count + len(line) < target_length:
                    important_lines.append(line)
                    char_count += len(line)
                elif not is_important and char_count + len(line) < target_length * 0.7:  # 非重要内容更严格限制
                    important_lines.append(line)
                    char_count += len(line)
                
                # 如果已达到目标长度，停止添加
                if char_count >= target_length:
                    break
            
            # 如果提取的重要内容仍然过长，进行进一步截断
            if important_lines:
                processed_content = '\n'.join(important_lines)
                if len(processed_content) > target_length:
                    processed_content = processed_content[:target_length] + "...(内容已智能截断)"
                
                news_content = processed_content
                google_control_applied = True
                logger.info(f"[统一新闻工具]  Google模型智能长度控制完成，从{original_length}字符压缩至{len(news_content)}字符")
            else:
                # 如果没有重要行，直接截断到目标长度
                news_content = news_content[:target_length] + "...(内容已强制截断)"
                google_control_applied = True
                logger.info(f"[统一新闻工具]  Google模型强制截断至{target_length}字符")
        
        # 计算最终的格式化结果长度，确保总长度合理
        base_format_length = 300  # 格式化模板的大概长度
        if is_google_model and (len(news_content) + base_format_length) > 4000:
            # 如果加上格式化后仍然过长，进一步压缩新闻内容
            max_content_length = 3500
            if len(news_content) > max_content_length:
                news_content = news_content[:max_content_length] + "...(已优化长度)"
                google_control_applied = True
                logger.info(f"[统一新闻工具]  Google模型最终长度优化，内容长度: {len(news_content)}字符")
        
        formatted_result = f"""
===  新闻数据来源: {source} ===
获取时间: {timestamp}
数据长度: {len(news_content)} 字符
{f"模型类型: {model_info}" if model_info else ""}
{f" Google模型长度控制已应用 (原长度: {original_length} 字符)" if google_control_applied else ""}

===  新闻内容 ===
{news_content}

===  数据状态 ===
状态: 成功获取
来源: {source}
时间戳: {timestamp}
"""
        return formatted_result.strip()



    def _build_keyword_list(self, stock_code: str, company_name: str, extra_keywords: str) -> list:
        """??????????Tushare??"""
        keywords = []
        seen = set()

        def _add(token: str):
            token = (token or '').strip()
            if not token:
                return
            if token not in seen and len(token) >= 2:
                seen.add(token)
                keywords.append(token)

        _add(stock_code.upper())
        _add(stock_code.lower())
        if '.' in stock_code:
            _add(stock_code.split('.')[0])
        if company_name:
            cleaned = company_name.replace('??????', '').replace('????', '').strip()
            _add(company_name.strip())
            if cleaned:
                _add(cleaned)
        if extra_keywords:
            import re as _re
            for token in _re.split(r'[?,?;\s]+', extra_keywords):
                _add(token)
        return keywords[:12]

    def _get_tushare_keyword_news(self, stock_code: str, keywords: list, max_news: int) -> str:
        """??Tushare????????????"""
        if not keywords:
            return ''
        try:
            from tradingagents.dataflows.tushare_utils import get_stock_news_tushare
        except Exception as exc:
            logger.warning(f"[??????] ??Tushare????: {exc}")
            return ''

        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        news_df = get_stock_news_tushare(
            symbol=stock_code,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            max_news=max(max_news * 4, 120),
        )

        if news_df is None or getattr(news_df, 'empty', True):
            return ''

        try:
            records = news_df.to_dict('records')
        except Exception:
            records = []

        filtered = []
        for row in records:
            text_blob = ' '.join([str(row.get('title', '')), str(row.get('content', '')), str(row.get('channels', ''))])
            if any(keyword in text_blob for keyword in keywords):
                filtered.append(row)

        if not filtered:
            return ''

        def _pick_time(item: dict) -> str:
            for key in ('datetime', 'publish_time', 'pub_time', 'time'):
                if item.get(key):
                    return str(item[key])
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        filtered.sort(key=lambda x: _pick_time(x), reverse=True)
        filtered = filtered[:max_news]

        lines = ['### 近30天Tushare重点新闻']
        for item in filtered:
            pub_time = _pick_time(item)
            title = item.get('title') or '未命名资讯'
            source = item.get('source') or item.get('channels') or '未知来源'
            content = (item.get('content') or '').strip()
            if len(content) > 200:
                content = content[:200] + '...'
            url = item.get('url') or item.get('link') or ''
            entry = f"- [{pub_time}] {title}（{source}）\n  {content or '（内容略）'}"
            if url:
                entry += f"\n  链接: {url}"
            lines.append(entry)

        return "\n".join(lines)
def create_unified_news_tool(toolkit):
    """创建统一新闻工具函数"""
    analyzer = UnifiedNewsAnalyzer(toolkit)
    
    def get_stock_news_unified(
        stock_code: str,
        max_news: int = 100,
        model_info: str = "",
        company_name: str = "",
        search_keywords: str = "",
    ):
        """
        统一新闻获取工具
        
        Args:
            stock_code (str): 股票代码 (支持A股如000001、港股如0700.HK、美股如AAPL)
            max_news (int): 最大新闻数量，默认100
            model_info (str): 当前使用的模型信息，用于特殊处理
        
        Returns:
            str: 格式化的新闻内容
        """
        if not stock_code:
            return " 错误: 未提供股票代码"
        
        return analyzer.get_stock_news_unified(stock_code, max_news, model_info)
    
    # 设置工具属性
    get_stock_news_unified.name = "get_stock_news_unified"
    get_stock_news_unified.description = """
统一新闻获取工具 - 根据股票代码自动获取相应市场的新闻

功能:
- 自动识别股票类型（A股/港股/美股）
- 根据股票类型选择最佳新闻源
- A股: 优先东方财富 -> Google中文 -> OpenAI
- 港股: 优先Google -> OpenAI -> 实时新闻
- 美股: 优先OpenAI -> Google英文 -> FinnHub
- 返回格式化的新闻内容
- 支持Google模型的特殊长度控制
"""
    
    return get_stock_news_unified
