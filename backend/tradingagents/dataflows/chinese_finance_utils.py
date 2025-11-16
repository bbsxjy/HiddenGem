#!/usr/bin/env python3
"""
中国财经数据聚合工具
由于微博API申请困难且功能受限，采用多源数据聚合的方式
"""

import requests
import json
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
from bs4 import BeautifulSoup
import pandas as pd

# 数据缓存：避免短时间内重复获取相同数据
_social_sentiment_cache = {}
_social_sentiment_cache_ttl = 300  # 缓存5分钟


class ChineseFinanceDataAggregator:
    """中国财经数据聚合器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_stock_sentiment_summary(self, ticker: str, days: int = 7) -> Dict:
        """
        获取股票情绪分析汇总
        整合多个可获取的中国财经数据源
        """
        try:
            # 1. 获取财经新闻情绪
            news_sentiment = self._get_finance_news_sentiment(ticker, days)
            
            # 2. 获取股吧讨论热度 (如果可以获取)
            forum_sentiment = self._get_stock_forum_sentiment(ticker, days)
            
            # 3. 获取财经媒体报道
            media_sentiment = self._get_media_coverage_sentiment(ticker, days)
            
            # 4. 综合分析
            overall_sentiment = self._calculate_overall_sentiment(
                news_sentiment, forum_sentiment, media_sentiment
            )
            
            return {
                'ticker': ticker,
                'analysis_period': f'{days} days',
                'overall_sentiment': overall_sentiment,
                'news_sentiment': news_sentiment,
                'forum_sentiment': forum_sentiment,
                'media_sentiment': media_sentiment,
                'summary': self._generate_sentiment_summary(overall_sentiment),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'ticker': ticker,
                'error': f'数据获取失败: {str(e)}',
                'fallback_message': '由于中国社交媒体API限制，建议使用财经新闻和基本面分析作为主要参考',
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_finance_news_sentiment(self, ticker: str, days: int) -> Dict:
        """获取财经新闻情绪分析"""
        try:
            # 搜索相关新闻标题和内容
            company_name = self._get_company_chinese_name(ticker)
            search_terms = [ticker, company_name] if company_name else [ticker]
            
            news_items = []
            for term in search_terms:
                # 这里可以集成多个新闻源
                items = self._search_finance_news(term, days)
                news_items.extend(items)
            
            # 简单的情绪分析
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            for item in news_items:
                sentiment = self._analyze_text_sentiment(item.get('title', '') + ' ' + item.get('content', ''))
                if sentiment > 0.1:
                    positive_count += 1
                elif sentiment < -0.1:
                    negative_count += 1
                else:
                    neutral_count += 1
            
            total = len(news_items)
            if total == 0:
                return {'sentiment_score': 0, 'confidence': 0, 'news_count': 0}
            
            sentiment_score = (positive_count - negative_count) / total
            
            return {
                'sentiment_score': sentiment_score,
                'positive_ratio': positive_count / total,
                'negative_ratio': negative_count / total,
                'neutral_ratio': neutral_count / total,
                'news_count': total,
                'confidence': min(total / 10, 1.0)  # 新闻数量越多，置信度越高
            }
            
        except Exception as e:
            return {'error': str(e), 'sentiment_score': 0, 'confidence': 0}
    
    def _get_stock_forum_sentiment(self, ticker: str, days: int) -> Dict:
        """获取股票论坛讨论情绪 - 使用AKShare获取东方财富股吧数据"""
        from tradingagents.utils.logging_manager import get_logger
        logger = get_logger('agents')

        try:
            logger.info(f"[股吧情绪] 开始获取 {ticker} 的东方财富股吧评论数据")

            # 使用AKShare获取东方财富股吧评论
            import akshare as ak

            # 清理股票代码格式
            clean_ticker = ticker.replace('.SH', '').replace('.SZ', '').replace('.SS', '')\
                                .replace('.HK', '').replace('.XSHE', '').replace('.XSHG', '')

            logger.info(f"[股吧情绪] 处理后的股票代码: {clean_ticker}")

            # 获取股吧评论数据（带超时保护）
            import threading

            result = [None]
            exception = [None]

            def fetch_comments():
                try:
                    # 尝试获取个股千股千评数据（包含投资者情绪）
                    result[0] = ak.stock_comment_em()
                except Exception as e:
                    exception[0] = e

            # 启动线程
            thread = threading.Thread(target=fetch_comments)
            thread.daemon = True
            thread.start()

            # 等待60秒
            thread.join(timeout=60)

            if thread.is_alive():
                logger.warning(f"[股吧情绪] 获取股吧数据超时（60秒）: {ticker}")
                raise Exception(f"股吧数据获取超时: {ticker}")
            elif exception[0]:
                raise exception[0]
            else:
                comment_df = result[0]

            if comment_df is not None and not comment_df.empty:
                # 查找当前股票的评论数据
                matching_rows = comment_df[comment_df['代码'].astype(str).str.contains(clean_ticker, na=False)]

                if not matching_rows.empty:
                    row = matching_rows.iloc[0]

                    # 解析情绪数据
                    # 东方财富千股千评包含：综合评分、上涨概率、盈利能力等指标
                    sentiment_score = 0.5  # 默认中性
                    discussion_count = 0

                    # 尝试从评分中提取情绪
                    if '综合评分' in row:
                        try:
                            score = float(row['综合评分'])
                            sentiment_score = score / 100  # 假设评分0-100，转换为0-1
                        except:
                            pass

                    logger.info(f"[股吧情绪] 成功获取 {ticker} 的股吧情绪数据，情绪评分: {sentiment_score:.2f}")

                    return {
                        'sentiment_score': sentiment_score,
                        'discussion_count': discussion_count,
                        'hot_topics': [],
                        'note': '数据来源：东方财富股吧（千股千评）',
                        'confidence': 0.7,  # AKShare API数据可信度较高
                        'source': 'eastmoney_guba'
                    }
                else:
                    logger.warning(f"[股吧情绪] 未找到 {ticker} 的股吧评论数据")
                    return {
                        'sentiment_score': 0.5,
                        'discussion_count': 0,
                        'hot_topics': [],
                        'note': '未找到该股票的股吧讨论数据',
                        'confidence': 0,
                        'source': 'eastmoney_guba'
                    }
            else:
                logger.warning(f"[股吧情绪] 股吧评论数据为空")
                return {
                    'sentiment_score': 0.5,
                    'discussion_count': 0,
                    'hot_topics': [],
                    'note': '股吧评论数据暂时不可用',
                    'confidence': 0,
                    'source': 'eastmoney_guba'
                }

        except Exception as e:
            logger.error(f"[股吧情绪] 获取股吧数据失败: {e}")
            return {
                'sentiment_score': 0.5,
                'discussion_count': 0,
                'hot_topics': [],
                'note': f'股票论坛数据获取失败: {str(e)}',
                'confidence': 0,
                'source': 'eastmoney_guba_error'
            }
    
    def _get_media_coverage_sentiment(self, ticker: str, days: int) -> Dict:
        """获取媒体报道情绪 - 整合雪球（Xueqiu）数据"""
        from tradingagents.utils.logging_manager import get_logger
        logger = get_logger('agents')

        try:
            logger.info(f"[媒体情绪] 开始获取 {ticker} 的媒体报道和雪球情绪数据")

            # 🆕 使用AKShare获取雪球情绪数据
            try:
                from tradingagents.dataflows.akshare_utils import get_xueqiu_stock_sentiment
                xueqiu_data = get_xueqiu_stock_sentiment(ticker)

                if xueqiu_data and 'error' not in xueqiu_data:
                    sentiment_score = xueqiu_data.get('sentiment_score', 0.5)
                    confidence = xueqiu_data.get('confidence', 0)
                    follow_count = xueqiu_data.get('follow_count', 0)
                    tweet_count = xueqiu_data.get('tweet_count', 0)

                    logger.info(f"[媒体情绪]  雪球数据获取成功: 情绪={sentiment_score:.2f}, 关注={follow_count}, 讨论={tweet_count}")

                    return {
                        'sentiment_score': sentiment_score,
                        'coverage_count': 1,  # 雪球数据源
                        'confidence': confidence,
                        'source': 'xueqiu',
                        'follow_count': follow_count,
                        'tweet_count': tweet_count,
                        'note': xueqiu_data.get('note', '基于雪球平台数据计算情绪')
                    }
                else:
                    error_msg = xueqiu_data.get('error', '未知错误') if xueqiu_data else '数据为空'
                    logger.warning(f"[媒体情绪]  雪球数据获取失败: {error_msg}")
                    return {'sentiment_score': 0.5, 'coverage_count': 0, 'confidence': 0, 'error': error_msg}

            except Exception as e:
                logger.error(f"[媒体情绪]  雪球数据获取异常: {e}")
                return {'sentiment_score': 0.5, 'coverage_count': 0, 'confidence': 0, 'error': str(e)}

        except Exception as e:
            logger.error(f"[媒体情绪]  整体获取失败: {e}")
            return {'error': str(e), 'sentiment_score': 0.5, 'confidence': 0}
    
    def _search_finance_news(self, search_term: str, days: int) -> List[Dict]:
        """搜索财经新闻 (示例实现)"""
        # 这里可以集成多个新闻源的API或RSS
        # 例如：财联社、新浪财经、东方财富等
        
        # 模拟返回数据结构
        return [
            {
                'title': f'{search_term}相关财经新闻标题',
                'content': '新闻内容摘要...',
                'source': '财联社',
                'publish_time': datetime.now().isoformat(),
                'url': 'https://example.com/news/1'
            }
        ]
    
    def _get_media_coverage(self, ticker: str, days: int) -> List[Dict]:
        """获取媒体报道 (示例实现)"""
        # 可以集成Google News API或其他新闻聚合服务
        return []
    
    def _analyze_text_sentiment(self, text: str) -> float:
        """简单的中文文本情绪分析"""
        if not text:
            return 0
        
        # 简单的关键词情绪分析
        positive_words = ['上涨', '增长', '利好', '看好', '买入', '推荐', '强势', '突破', '创新高']
        negative_words = ['下跌', '下降', '利空', '看空', '卖出', '风险', '跌破', '创新低', '亏损']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count + negative_count == 0:
            return 0
        
        return (positive_count - negative_count) / (positive_count + negative_count)
    
    def _get_company_chinese_name(self, ticker: str) -> Optional[str]:
        """获取公司中文名称"""
        # 简单的映射表，实际可以从数据库或API获取
        name_mapping = {
            'AAPL': '苹果',
            'TSLA': '特斯拉',
            'NVDA': '英伟达',
            'MSFT': '微软',
            'GOOGL': '谷歌',
            'AMZN': '亚马逊'
        }
        return name_mapping.get(ticker.upper())
    
    def _calculate_overall_sentiment(self, news_sentiment: Dict, forum_sentiment: Dict, media_sentiment: Dict) -> Dict:
        """计算综合情绪分析"""
        # 根据各数据源的置信度加权计算
        news_weight = news_sentiment.get('confidence', 0)
        forum_weight = forum_sentiment.get('confidence', 0)
        media_weight = media_sentiment.get('confidence', 0)
        
        total_weight = news_weight + forum_weight + media_weight
        
        if total_weight == 0:
            return {'sentiment_score': 0, 'confidence': 0, 'level': 'neutral'}
        
        weighted_sentiment = (
            news_sentiment.get('sentiment_score', 0) * news_weight +
            forum_sentiment.get('sentiment_score', 0) * forum_weight +
            media_sentiment.get('sentiment_score', 0) * media_weight
        ) / total_weight
        
        # 确定情绪等级
        if weighted_sentiment > 0.3:
            level = 'very_positive'
        elif weighted_sentiment > 0.1:
            level = 'positive'
        elif weighted_sentiment > -0.1:
            level = 'neutral'
        elif weighted_sentiment > -0.3:
            level = 'negative'
        else:
            level = 'very_negative'
        
        return {
            'sentiment_score': weighted_sentiment,
            'confidence': total_weight / 3,  # 平均置信度
            'level': level
        }
    
    def _generate_sentiment_summary(self, overall_sentiment: Dict) -> str:
        """生成情绪分析摘要"""
        level = overall_sentiment.get('level', 'neutral')
        score = overall_sentiment.get('sentiment_score', 0)
        confidence = overall_sentiment.get('confidence', 0)
        
        level_descriptions = {
            'very_positive': '非常积极',
            'positive': '积极',
            'neutral': '中性',
            'negative': '消极',
            'very_negative': '非常消极'
        }
        
        description = level_descriptions.get(level, '中性')
        confidence_level = '高' if confidence > 0.7 else '中' if confidence > 0.3 else '低'
        
        return f"市场情绪: {description} (评分: {score:.2f}, 置信度: {confidence_level})"


def get_chinese_social_sentiment(ticker: str, curr_date: str) -> str:
    """
    获取中国社交媒体情绪分析的主要接口函数
    添加缓存机制，避免短时间内重复获取相同数据
    """
    from ..utils.logging_init import get_logger
    logger = get_logger('agents')

    # 检查缓存
    cache_key = f"{ticker}_{curr_date}"
    current_time = time.time()

    if cache_key in _social_sentiment_cache:
        cached_data, cached_time = _social_sentiment_cache[cache_key]
        if current_time - cached_time < _social_sentiment_cache_ttl:
            logger.info(f" [社交情绪缓存] 使用缓存数据: {ticker}, 缓存时间: {int(current_time - cached_time)}秒前")
            return cached_data

    logger.info(f" [社交情绪] 获取新数据: {ticker}")

    aggregator = ChineseFinanceDataAggregator()

    try:
        # 获取情绪分析数据
        sentiment_data = aggregator.get_stock_sentiment_summary(ticker, days=7)

        # 格式化输出
        if 'error' in sentiment_data:
            result = f"""
中国市场情绪分析报告 - {ticker}
分析日期: {curr_date}

 数据获取限制说明:
{sentiment_data.get('fallback_message', '数据获取遇到技术限制')}

建议:
1. 重点关注财经新闻和基本面分析
2. 参考官方财报和业绩指导
3. 关注行业政策和监管动态
4. 考虑国际市场情绪对中概股的影响

注: 由于中国社交媒体平台API限制，当前主要依赖公开财经数据源进行分析。
"""
        else:
            overall = sentiment_data.get('overall_sentiment', {})
            news = sentiment_data.get('news_sentiment', {})

            result = f"""
中国市场情绪分析报告 - {ticker}
分析日期: {curr_date}
分析周期: {sentiment_data.get('analysis_period', '7天')}

 综合情绪评估:
{sentiment_data.get('summary', '数据不足')}

 财经新闻情绪:
- 情绪评分: {news.get('sentiment_score', 0):.2f}
- 正面新闻比例: {news.get('positive_ratio', 0):.1%}
- 负面新闻比例: {news.get('negative_ratio', 0):.1%}
- 新闻数量: {news.get('news_count', 0)}条

 投资建议:
基于当前可获取的中国市场数据，建议投资者:
1. 密切关注官方财经媒体报道
2. 重视基本面分析和财务数据
3. 考虑政策环境对股价的影响
4. 关注国际市场动态

 数据说明:
由于中国社交媒体平台API获取限制，本分析主要基于公开财经新闻数据。
建议结合其他分析维度进行综合判断。

生成时间: {sentiment_data.get('timestamp', datetime.now().isoformat())}
"""

        # 缓存结果
        _social_sentiment_cache[cache_key] = (result, current_time)
        logger.info(f" [社交情绪缓存] 缓存数据: {ticker}, TTL: {_social_sentiment_cache_ttl}秒")

        return result

    except Exception as e:
        result = f"""
中国市场情绪分析 - {ticker}
分析日期: {curr_date}

 分析失败: {str(e)}

 替代建议:
1. 查看财经新闻网站的相关报道
2. 关注雪球、东方财富等投资社区讨论
3. 参考专业机构的研究报告
4. 重点分析基本面和技术面数据

注: 中国社交媒体数据获取存在技术限制，建议以基本面分析为主。
"""
        # 即使失败也缓存结果，避免重复失败
        _social_sentiment_cache[cache_key] = (result, current_time)
        return result
