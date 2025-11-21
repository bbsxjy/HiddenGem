#!/usr/bin/env python3
"""
实时新闻数据获取工具
解决新闻滞后性问题
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import os
from dataclasses import dataclass

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

# 新闻数据缓存：避免短时间内重复获取相同数据
_news_cache = {}
_news_cache_ttl = 300  # 缓存5分钟



@dataclass
class NewsItem:
    """新闻项目数据结构"""
    title: str
    content: str
    source: str
    publish_time: datetime
    url: str
    urgency: str  # high, medium, low
    relevance_score: float


class RealtimeNewsAggregator:
    """实时新闻聚合器"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'TradingAgents-CN/1.0'
        }
        
        # API密钥配置
        self.finnhub_key = os.getenv('FINNHUB_API_KEY')
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.newsapi_key = os.getenv('NEWSAPI_KEY')
        
    def get_realtime_stock_news(self, ticker: str, hours_back: int = 6, max_news: int = 10) -> List[NewsItem]:
        """
        获取实时股票新闻
        优先级：专业API > 新闻API > 搜索引擎
        
        Args:
            ticker: 股票代码
            hours_back: 回溯小时数
            max_news: 最大新闻数量，默认10条
        """
        logger.info(f"[新闻聚合器] 开始获取 {ticker} 的实时新闻，回溯时间: {hours_back}小时")
        start_time = datetime.now()
        all_news = []
        
        # 1. FinnHub实时新闻 (最高优先级)
        logger.info(f"[新闻聚合器] 尝试从 FinnHub 获取 {ticker} 的新闻")
        finnhub_start = datetime.now()
        finnhub_news = self._get_finnhub_realtime_news(ticker, hours_back)
        finnhub_time = (datetime.now() - finnhub_start).total_seconds()
        
        if finnhub_news:
            logger.info(f"[新闻聚合器] 成功从 FinnHub 获取 {len(finnhub_news)} 条新闻，耗时: {finnhub_time:.2f}秒")
        else:
            logger.info(f"[新闻聚合器] FinnHub 未返回新闻，耗时: {finnhub_time:.2f}秒")
            
        all_news.extend(finnhub_news)
        
        # 2. Alpha Vantage新闻
        logger.info(f"[新闻聚合器] 尝试从 Alpha Vantage 获取 {ticker} 的新闻")
        av_start = datetime.now()
        av_news = self._get_alpha_vantage_news(ticker, hours_back)
        av_time = (datetime.now() - av_start).total_seconds()
        
        if av_news:
            logger.info(f"[新闻聚合器] 成功从 Alpha Vantage 获取 {len(av_news)} 条新闻，耗时: {av_time:.2f}秒")
        else:
            logger.info(f"[新闻聚合器] Alpha Vantage 未返回新闻，耗时: {av_time:.2f}秒")
            
        all_news.extend(av_news)
        
        # 3. NewsAPI (如果配置了)
        if self.newsapi_key:
            logger.info(f"[新闻聚合器] 尝试从 NewsAPI 获取 {ticker} 的新闻")
            newsapi_start = datetime.now()
            newsapi_news = self._get_newsapi_news(ticker, hours_back)
            newsapi_time = (datetime.now() - newsapi_start).total_seconds()
            
            if newsapi_news:
                logger.info(f"[新闻聚合器] 成功从 NewsAPI 获取 {len(newsapi_news)} 条新闻，耗时: {newsapi_time:.2f}秒")
            else:
                logger.info(f"[新闻聚合器] NewsAPI 未返回新闻，耗时: {newsapi_time:.2f}秒")
                
            all_news.extend(newsapi_news)
        else:
            logger.info(f"[新闻聚合器] NewsAPI 密钥未配置，跳过此新闻源")
        
        # 4. 中文财经新闻源
        logger.info(f"[新闻聚合器] 尝试获取 {ticker} 的中文财经新闻")
        chinese_start = datetime.now()
        chinese_news = self._get_chinese_finance_news(ticker, hours_back)
        chinese_time = (datetime.now() - chinese_start).total_seconds()
        
        if chinese_news:
            logger.info(f"[新闻聚合器] 成功获取 {len(chinese_news)} 条中文财经新闻，耗时: {chinese_time:.2f}秒")
        else:
            logger.info(f"[新闻聚合器] 未获取到中文财经新闻，耗时: {chinese_time:.2f}秒")
            
        all_news.extend(chinese_news)
        
        # 去重和排序
        logger.info(f"[新闻聚合器] 开始对 {len(all_news)} 条新闻进行去重和排序")
        dedup_start = datetime.now()
        unique_news = self._deduplicate_news(all_news)
        sorted_news = sorted(unique_news, key=lambda x: x.publish_time, reverse=True)
        dedup_time = (datetime.now() - dedup_start).total_seconds()
        
        # 记录去重结果
        removed_count = len(all_news) - len(unique_news)
        logger.info(f"[新闻聚合器] 新闻去重完成，移除了 {removed_count} 条重复新闻，剩余 {len(sorted_news)} 条，耗时: {dedup_time:.2f}秒")
        
        # 记录总体情况
        total_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"[新闻聚合器] {ticker} 的新闻聚合完成，总共获取 {len(sorted_news)} 条新闻，总耗时: {total_time:.2f}秒")
        
        # 限制新闻数量为最新的max_news条
        if len(sorted_news) > max_news:
            original_count = len(sorted_news)
            sorted_news = sorted_news[:max_news]
            logger.info(f"[新闻聚合器]  新闻数量限制: 从{original_count}条限制为{max_news}条最新新闻")
        
        # 记录一些新闻标题示例
        if sorted_news:
            sample_titles = [item.title for item in sorted_news[:3]]
            logger.info(f"[新闻聚合器] 新闻标题示例: {', '.join(sample_titles)}")
        
        return sorted_news
    
    def _get_finnhub_realtime_news(self, ticker: str, hours_back: int) -> List[NewsItem]:
        """获取FinnHub实时新闻"""
        if not self.finnhub_key:
            return []
        
        try:
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)
            
            # FinnHub API调用
            url = "https://finnhub.io/api/v1/company-news"
            params = {
                'symbol': ticker,
                'from': start_time.strftime('%Y-%m-%d'),
                'to': end_time.strftime('%Y-%m-%d'),
                'token': self.finnhub_key
            }
            
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            news_data = response.json()
            news_items = []
            
            for item in news_data:
                # 检查新闻时效性
                publish_time = datetime.fromtimestamp(item.get('datetime', 0))
                if publish_time < start_time:
                    continue
                
                # 评估紧急程度
                urgency = self._assess_news_urgency(item.get('headline', ''), item.get('summary', ''))
                
                news_items.append(NewsItem(
                    title=item.get('headline', ''),
                    content=item.get('summary', ''),
                    source=item.get('source', 'FinnHub'),
                    publish_time=publish_time,
                    url=item.get('url', ''),
                    urgency=urgency,
                    relevance_score=self._calculate_relevance(item.get('headline', ''), ticker)
                ))
            
            return news_items
            
        except Exception as e:
            logger.error(f"FinnHub新闻获取失败: {e}")
            return []
    
    def _get_alpha_vantage_news(self, ticker: str, hours_back: int) -> List[NewsItem]:
        """获取Alpha Vantage新闻"""
        if not self.alpha_vantage_key:
            return []
        
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': ticker,
                'apikey': self.alpha_vantage_key,
                'limit': 50
            }
            
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            news_items = []
            
            if 'feed' in data:
                for item in data['feed']:
                    # 解析时间
                    time_str = item.get('time_published', '')
                    try:
                        publish_time = datetime.strptime(time_str, '%Y%m%dT%H%M%S')
                    except:
                        continue
                    
                    # 检查时效性
                    if publish_time < datetime.now() - timedelta(hours=hours_back):
                        continue
                    
                    urgency = self._assess_news_urgency(item.get('title', ''), item.get('summary', ''))
                    
                    news_items.append(NewsItem(
                        title=item.get('title', ''),
                        content=item.get('summary', ''),
                        source=item.get('source', 'Alpha Vantage'),
                        publish_time=publish_time,
                        url=item.get('url', ''),
                        urgency=urgency,
                        relevance_score=self._calculate_relevance(item.get('title', ''), ticker)
                    ))
            
            return news_items
            
        except Exception as e:
            logger.error(f"Alpha Vantage新闻获取失败: {e}")
            return []
    
    def _get_newsapi_news(self, ticker: str, hours_back: int) -> List[NewsItem]:
        """获取NewsAPI新闻"""
        try:
            # 构建搜索查询
            company_names = {
                'AAPL': 'Apple',
                'TSLA': 'Tesla', 
                'NVDA': 'NVIDIA',
                'MSFT': 'Microsoft',
                'GOOGL': 'Google'
            }
            
            query = f"{ticker} OR {company_names.get(ticker, ticker)}"
            
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'language': 'en',
                'sortBy': 'publishedAt',
                'from': (datetime.now() - timedelta(hours=hours_back)).isoformat(),
                'apiKey': self.newsapi_key
            }
            
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            news_items = []
            
            for item in data.get('articles', []):
                # 解析时间
                time_str = item.get('publishedAt', '')
                try:
                    publish_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                except:
                    continue
                
                urgency = self._assess_news_urgency(item.get('title', ''), item.get('description', ''))
                
                news_items.append(NewsItem(
                    title=item.get('title', ''),
                    content=item.get('description', ''),
                    source=item.get('source', {}).get('name', 'NewsAPI'),
                    publish_time=publish_time,
                    url=item.get('url', ''),
                    urgency=urgency,
                    relevance_score=self._calculate_relevance(item.get('title', ''), ticker)
                ))
            
            return news_items
            
        except Exception as e:
            logger.error(f"NewsAPI新闻获取失败: {e}")
            return []
    
    def _get_chinese_finance_news(self, ticker: str, hours_back: int) -> List[NewsItem]:
        """获取中文财经新闻"""
        # 集成中文财经新闻API：使用Tushare新闻接口
        logger.info(f"[中文财经新闻] 开始获取 {ticker} 的中文财经新闻，回溯时间: {hours_back}小时")
        start_time = datetime.now()

        try:
            news_items = []

            # 1. 优先使用Tushare获取新闻
            try:
                logger.info(f"[中文财经新闻] 尝试导入 Tushare 新闻工具")
                from .tushare_utils import get_stock_news_tushare

                # 处理股票代码格式
                # 如果是美股代码，不使用Tushare新闻
                if '.' in ticker and any(suffix in ticker for suffix in ['.US', '.N', '.O', '.NYSE', '.NASDAQ']):
                    logger.info(f"[中文财经新闻] 检测到美股代码 {ticker}，跳过Tushare新闻获取")
                else:
                    # 计算日期范围
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(hours=hours_back)).strftime('%Y-%m-%d')

                    # 获取Tushare新闻
                    logger.info(f"[中文财经新闻] 开始从Tushare获取新闻，日期范围: {start_date} 到 {end_date}")
                    tushare_start_time = datetime.now()
                    news_df = get_stock_news_tushare(
                        symbol=ticker,
                        start_date=start_date,
                        end_date=end_date,
                        max_news=10
                    )

                    if not news_df.empty:
                        logger.info(f"[中文财经新闻] Tushare返回 {len(news_df)} 条新闻数据，开始处理")
                        processed_count = 0
                        skipped_count = 0
                        error_count = 0

                        # 转换为NewsItem格式
                        for _, row in news_df.iterrows():
                            try:
                                # 解析时间
                                time_str = row.get('datetime', '')
                                if time_str:
                                    try:
                                        # Tushare返回的时间格式：YYYY-MM-DD HH:MM:SS
                                        publish_time = datetime.strptime(str(time_str)[:19], '%Y-%m-%d %H:%M:%S')
                                    except:
                                        try:
                                            publish_time = datetime.strptime(str(time_str)[:10], '%Y-%m-%d')
                                        except:
                                            logger.warning(f"[中文财经新闻] 无法解析时间格式: {time_str}，使用当前时间")
                                            publish_time = datetime.now()
                                else:
                                    logger.warning(f"[中文财经新闻] 新闻时间为空，使用当前时间")
                                    publish_time = datetime.now()

                                # 检查时效性
                                if publish_time < datetime.now() - timedelta(hours=hours_back):
                                    skipped_count += 1
                                    continue

                                # 评估紧急程度
                                title = row.get('title', '')
                                content = row.get('content', '')
                                urgency = self._assess_news_urgency(title, content)

                                # 获取新闻来源
                                source = row.get('source', 'Tushare')
                                if source == 'eastmoney':
                                    source = '东方财富'
                                elif source == 'sina':
                                    source = '新浪财经'
                                elif source == '10jqka':
                                    source = '同花顺'

                                news_items.append(NewsItem(
                                    title=title,
                                    content=content,
                                    source=source,
                                    publish_time=publish_time,
                                    url=row.get('channels', ''),
                                    urgency=urgency,
                                    relevance_score=self._calculate_relevance(title, ticker)
                                ))
                                processed_count += 1
                            except Exception as item_e:
                                logger.error(f"[中文财经新闻] 处理Tushare新闻项目失败: {item_e}")
                                error_count += 1
                                continue

                        tushare_time = (datetime.now() - tushare_start_time).total_seconds()
                        logger.info(f"[中文财经新闻] Tushare新闻处理完成，成功: {processed_count}条，跳过: {skipped_count}条，错误: {error_count}条，耗时: {tushare_time:.2f}秒")
            except Exception as ts_e:
                logger.error(f"[中文财经新闻] 获取Tushare新闻失败: {ts_e}")

            # 2. 财联社API新闻 (官方API)
            logger.info(f"[中文财经新闻] 开始获取财联社API新闻")
            cls_start_time = datetime.now()

            try:
                cls_news = self._fetch_cls_news(ticker, hours_back)
                cls_time = (datetime.now() - cls_start_time).total_seconds()

                if cls_news:
                    logger.info(f"[中文财经新闻] 成功从财联社获取 {len(cls_news)} 条新闻，耗时: {cls_time:.2f}秒")
                    news_items.extend(cls_news)
                else:
                    logger.info(f"[中文财经新闻] 财联社未返回相关新闻，耗时: {cls_time:.2f}秒")
            except Exception as cls_e:
                logger.error(f"[中文财经新闻] 获取财联社新闻失败: {cls_e}")

            # 3. 华尔街见闻实时快讯
            logger.info(f"[中文财经新闻] 开始获取华尔街见闻新闻")
            wsj_start_time = datetime.now()

            try:
                wsj_news = self._fetch_wallstreet_news(ticker, hours_back)
                wsj_time = (datetime.now() - wsj_start_time).total_seconds()

                if wsj_news:
                    logger.info(f"[中文财经新闻] 成功从华尔街见闻获取 {len(wsj_news)} 条新闻，耗时: {wsj_time:.2f}秒")
                    news_items.extend(wsj_news)
                else:
                    logger.info(f"[中文财经新闻] 华尔街见闻未返回相关新闻，耗时: {wsj_time:.2f}秒")
            except Exception as wsj_e:
                logger.error(f"[中文财经新闻] 获取华尔街见闻新闻失败: {wsj_e}")

            # 记录中文财经新闻获取总结
            total_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"[中文财经新闻] {ticker} 的中文财经新闻获取完成，总共获取 {len(news_items)} 条新闻，总耗时: {total_time:.2f}秒")

            return news_items

        except Exception as e:
            logger.error(f"[中文财经新闻] 中文财经新闻获取失败: {e}")
            return []

    def _fetch_wallstreet_news(self, ticker: str, hours_back: int) -> List[NewsItem]:
        """
        获取华尔街见闻实时快讯

        API文档:
        - URL: https://api-prod.wallstreetcn.com/apiv1/content/lives
        - 返回JSON格式的财经快讯数据
        - 无需API密钥

        Args:
            ticker: 股票代码
            hours_back: 回溯小时数

        Returns:
            List[NewsItem]: 新闻列表
        """
        logger.info(f"[华尔街见闻] 开始获取新闻，股票: {ticker}，回溯时间: {hours_back}小时")
        start_time = datetime.now()

        try:
            import requests
            import re
            from html import unescape

            # 华尔街见闻API
            url = "https://api-prod.wallstreetcn.com/apiv1/content/lives"
            params = {
                'channel': 'global-channel',
                'client': 'pc',
                'cursor': '',
                'limit': 50  # 获取50条新闻
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://wallstreetcn.com/',
                'Origin': 'https://wallstreetcn.com'
            }

            logger.info(f"[华尔街见闻] 请求API: {url}")
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code != 200:
                logger.warning(f"[华尔街见闻] API返回非200状态码: {response.status_code}")
                return []

            data = response.json()

            # 提取新闻列表
            news_list = []
            if data.get('code') == 20000 and 'data' in data:
                news_list = data['data'].get('items', [])
            elif 'items' in data:
                news_list = data['items']
            elif isinstance(data, list):
                news_list = data

            if not news_list:
                logger.warning(f"[华尔街见闻] API返回数据格式异常或无数据")
                return []

            logger.info(f"[华尔街见闻] 成功获取 {len(news_list)} 条原始新闻")

            # 转换为NewsItem格式
            news_items = []
            processed_count = 0
            skipped_count = 0

            # 计算时间阈值
            time_threshold = datetime.now() - timedelta(hours=hours_back)

            # HTML清理函数
            def clean_html(text: str) -> str:
                if not text:
                    return text
                # 移除HTML标签
                text = re.sub(r'<[^>]+>', '', text)
                # 解码HTML实体
                text = unescape(text)
                # 移除多余的空白
                text = re.sub(r'\s+', ' ', text).strip()
                return text

            for item in news_list:
                try:
                    # 解析时间（尝试多种可能的时间字段）
                    time_fields = ['display_time', 'created_at', 'publish_time', 'updated_at', 'time', 'datetime']
                    publish_time = None

                    for field in time_fields:
                        if field in item and item[field]:
                            time_value = item[field]
                            try:
                                if isinstance(time_value, (int, float)):
                                    # Unix时间戳
                                    if time_value > 1e10:  # 毫秒时间戳
                                        time_value = time_value / 1000
                                    publish_time = datetime.fromtimestamp(time_value)
                                elif isinstance(time_value, str):
                                    # ISO格式时间字符串
                                    if 'T' in time_value:
                                        publish_time = datetime.fromisoformat(time_value.replace('Z', '+00:00'))
                                    else:
                                        publish_time = datetime.strptime(time_value, '%Y-%m-%d %H:%M:%S')
                                break
                            except:
                                continue

                    if not publish_time:
                        logger.warning(f"[华尔街见闻] 新闻缺少有效时间戳，跳过")
                        skipped_count += 1
                        continue

                    # 检查时效性
                    if publish_time < time_threshold:
                        skipped_count += 1
                        continue

                    # 提取内容，尝试多种字段
                    content_fields = ['content_text', 'content', 'text', 'summary', 'description']
                    content = ''
                    for field in content_fields:
                        if field in item and item[field]:
                            content = str(item[field])
                            break

                    if not content:
                        logger.debug(f"[华尔街见闻] 新闻内容为空，跳过")
                        skipped_count += 1
                        continue

                    # 清理HTML标签
                    content = clean_html(content)

                    # 提取标题
                    title = item.get('title', '').strip()
                    if not title:
                        # 如果没有标题，从内容中提取（取第一句话或前50字）
                        sentences = re.split(r'[。！？．]', content)
                        if sentences and len(sentences[0]) <= 50:
                            title = sentences[0].strip()
                        else:
                            title = content[:50].strip() + "..."
                    else:
                        title = clean_html(title)

                    # 提取作者
                    author = ''
                    if item.get('author') and isinstance(item['author'], dict):
                        author = item['author'].get('display_name', '')

                    # 检查相关性
                    relevance_score = self._calculate_relevance(title + ' ' + content, ticker)

                    # 过滤低相关性新闻（相关性 < 0.5 则跳过）
                    if ticker and relevance_score < 0.5:
                        logger.debug(f"[华尔街见闻] 新闻相关性过低 ({relevance_score:.2f})，跳过: {title[:30]}...")
                        skipped_count += 1
                        continue

                    # 评估紧急程度
                    urgency = self._assess_news_urgency(title, content)

                    # 构建URL（如果有ID）
                    news_id = item.get('id', item.get('_id', ''))
                    news_url = f"https://wallstreetcn.com/live/{news_id}" if news_id else ''

                    news_items.append(NewsItem(
                        title=title,
                        content=content,
                        source='华尔街见闻' + (f' - {author}' if author else ''),
                        publish_time=publish_time,
                        url=news_url,
                        urgency=urgency,
                        relevance_score=relevance_score
                    ))
                    processed_count += 1

                except Exception as item_e:
                    logger.error(f"[华尔街见闻] 处理新闻项目失败: {item_e}")
                    skipped_count += 1
                    continue

            total_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"[华尔街见闻] 新闻处理完成，成功: {processed_count}条，跳过: {skipped_count}条，耗时: {total_time:.2f}秒")

            return news_items

        except ImportError:
            logger.error(f"[华尔街见闻] requests库未安装，无法获取新闻")
            return []
        except Exception as e:
            logger.error(f"[华尔街见闻] 获取新闻失败: {e}")
            import traceback
            logger.error(f"[华尔街见闻] 异常堆栈: {traceback.format_exc()}")
            return []

    def _fetch_cls_news(self, ticker: str, hours_back: int) -> List[NewsItem]:
        """
        获取财联社实时新闻（官方API）

        API文档:
        - URL: https://www.cls.cn/nodeapi/telegraphList
        - 返回JSON格式的财经快讯数据
        - 无需API密钥或签名

        Args:
            ticker: 股票代码
            hours_back: 回溯小时数

        Returns:
            List[NewsItem]: 新闻列表
        """
        logger.info(f"[财联社] 开始获取财联社新闻，股票: {ticker}，回溯时间: {hours_back}小时")
        start_time = datetime.now()

        try:
            import requests

            # 财联社官方API
            url = "https://www.cls.cn/nodeapi/telegraphList"
            params = {
                'app': 'CailianpressWeb',
                'os': 'web',
                'sv': '8.4.6',
                'refresh_type': '1',
                'rn': '50'  # 获取50条新闻
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.cls.cn/',
                'Accept': 'application/json'
            }

            logger.info(f"[财联社] 请求API: {url}")
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code != 200:
                logger.warning(f"[财联社] API返回非200状态码: {response.status_code}")
                return []

            data = response.json()

            if 'error' in data and data['error']:
                logger.error(f"[财联社] API返回错误: {data['error']}")
                return []

            if 'data' not in data or 'roll_data' not in data['data']:
                logger.warning(f"[财联社] API返回数据格式异常")
                return []

            news_list = data['data']['roll_data']
            logger.info(f"[财联社] 成功获取 {len(news_list)} 条原始新闻")

            # 转换为NewsItem格式
            news_items = []
            processed_count = 0
            skipped_count = 0

            # 计算时间阈值
            time_threshold = datetime.now() - timedelta(hours=hours_back)

            for item in news_list:
                try:
                    # 解析时间（Unix时间戳）
                    ctime = item.get('ctime', 0)
                    if ctime:
                        publish_time = datetime.fromtimestamp(ctime)
                    else:
                        logger.warning(f"[财联社] 新闻缺少时间戳，跳过")
                        skipped_count += 1
                        continue

                    # 检查时效性
                    if publish_time < time_threshold:
                        skipped_count += 1
                        continue

                    # 提取新闻内容
                    title = item.get('title', '').strip()
                    brief = item.get('brief', '').strip()
                    content = item.get('content', '').strip()

                    # 使用brief或content作为内容（title有时为空）
                    news_content = content if content else brief
                    news_title = title if title else brief[:50]  # 如果标题为空，用简介前50字作为标题

                    if not news_content:
                        logger.debug(f"[财联社] 新闻内容为空，跳过")
                        skipped_count += 1
                        continue

                    # 检查相关性
                    relevance_score = self._calculate_relevance(news_title + ' ' + news_content, ticker)

                    # 过滤低相关性新闻（相关性 < 0.5 则跳过）
                    if ticker and relevance_score < 0.5:
                        logger.debug(f"[财联社] 新闻相关性过低 ({relevance_score:.2f})，跳过: {news_title[:30]}...")
                        skipped_count += 1
                        continue

                    # 评估紧急程度
                    urgency = self._assess_news_urgency(news_title, news_content)

                    # 构建URL（如果有ID）
                    news_id = item.get('id', '')
                    news_url = f"https://www.cls.cn/detail/{news_id}" if news_id else ''

                    news_items.append(NewsItem(
                        title=news_title,
                        content=news_content,
                        source='财联社',
                        publish_time=publish_time,
                        url=news_url,
                        urgency=urgency,
                        relevance_score=relevance_score
                    ))
                    processed_count += 1

                except Exception as item_e:
                    logger.error(f"[财联社] 处理新闻项目失败: {item_e}")
                    skipped_count += 1
                    continue

            total_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"[财联社] 新闻处理完成，成功: {processed_count}条，跳过: {skipped_count}条，耗时: {total_time:.2f}秒")

            return news_items

        except ImportError:
            logger.error(f"[财联社] requests库未安装，无法获取新闻")
            return []
        except Exception as e:
            logger.error(f"[财联社] 获取新闻失败: {e}")
            import traceback
            logger.error(f"[财联社] 异常堆栈: {traceback.format_exc()}")
            return []

    def _parse_rss_feed(self, rss_url: str, ticker: str, hours_back: int) -> List[NewsItem]:
        """解析RSS源"""
        logger.info(f"[RSS解析] 开始解析RSS源: {rss_url}，股票: {ticker}，回溯时间: {hours_back}小时")
        start_time = datetime.now()
        
        try:
            # 实际实现需要使用feedparser库
            # 这里是简化实现，实际项目中应该替换为真实的RSS解析逻辑
            import feedparser
            
            logger.info(f"[RSS解析] 尝试获取RSS源内容")
            feed = feedparser.parse(rss_url)
            
            if not feed or not feed.entries:
                logger.warning(f"[RSS解析] RSS源未返回有效内容")
                return []
            
            logger.info(f"[RSS解析] 成功获取RSS源，包含 {len(feed.entries)} 条条目")
            news_items = []
            processed_count = 0
            skipped_count = 0
            
            for entry in feed.entries:
                try:
                    # 解析时间
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        publish_time = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    else:
                        logger.warning(f"[RSS解析] 条目缺少发布时间，使用当前时间")
                        publish_time = datetime.now()
                    
                    # 检查时效性
                    if publish_time < datetime.now() - timedelta(hours=hours_back):
                        skipped_count += 1
                        continue
                    
                    title = entry.title if hasattr(entry, 'title') else ''
                    content = entry.description if hasattr(entry, 'description') else ''
                    
                    # 检查相关性
                    if ticker.lower() not in title.lower() and ticker.lower() not in content.lower():
                        skipped_count += 1
                        continue
                    
                    # 评估紧急程度
                    urgency = self._assess_news_urgency(title, content)
                    
                    news_items.append(NewsItem(
                        title=title,
                        content=content,
                        source='财联社',
                        publish_time=publish_time,
                        url=entry.link if hasattr(entry, 'link') else '',
                        urgency=urgency,
                        relevance_score=self._calculate_relevance(title, ticker)
                    ))
                    processed_count += 1
                except Exception as e:
                    logger.error(f"[RSS解析] 处理RSS条目失败: {e}")
                    continue
            
            total_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"[RSS解析] RSS源解析完成，成功: {processed_count}条，跳过: {skipped_count}条，耗时: {total_time:.2f}秒")
            return news_items
        except ImportError:
            logger.error(f"[RSS解析] feedparser库未安装，无法解析RSS源")
            return []
        except Exception as e:
            logger.error(f"[RSS解析] 解析RSS源失败: {e}")
            return []
    
    def _assess_news_urgency(self, title: str, content: str) -> str:
        """评估新闻紧急程度"""
        text = (title + ' ' + content).lower()
        
        # 高紧急度关键词
        high_urgency_keywords = [
            'breaking', 'urgent', 'alert', 'emergency', 'halt', 'suspend',
            '突发', '紧急', '暂停', '停牌', '重大'
        ]
        
        # 中等紧急度关键词
        medium_urgency_keywords = [
            'earnings', 'report', 'announce', 'launch', 'merger', 'acquisition',
            '财报', '发布', '宣布', '并购', '收购'
        ]
        
        # 检查高紧急度关键词
        for keyword in high_urgency_keywords:
            if keyword in text:
                logger.debug(f"[紧急度评估] 检测到高紧急度关键词 '{keyword}' 在新闻中: {title[:50]}...")
                return 'high'
        
        # 检查中等紧急度关键词
        for keyword in medium_urgency_keywords:
            if keyword in text:
                logger.debug(f"[紧急度评估] 检测到中等紧急度关键词 '{keyword}' 在新闻中: {title[:50]}...")
                return 'medium'
        
        logger.debug(f"[紧急度评估] 未检测到紧急关键词，评估为低紧急度: {title[:50]}...")
        return 'low'
    
    def _calculate_relevance(self, title: str, ticker: str) -> float:
        """计算新闻相关性分数"""
        text = title.lower()
        ticker_lower = ticker.lower()

        # 基础相关性 - 股票代码直接出现在标题中
        if ticker_lower in text:
            logger.debug(f"[相关性计算] 股票代码 {ticker} 直接出现在标题中，相关性评分: 1.0，标题: {title[:50]}...")
            return 1.0

        # 提取股票代码的纯数字部分（适用于中国股票）
        pure_code = ''.join(filter(str.isdigit, ticker))
        if pure_code and len(pure_code) == 6 and pure_code in text:  # A股代码是6位数字
            logger.debug(f"[相关性计算] 股票代码数字部分 {pure_code} 出现在标题中，相关性评分: 1.0，标题: {title[:50]}...")
            return 1.0

        # 公司名称匹配（美股）
        us_company_names = {
            'aapl': ['apple', 'iphone', 'ipad', 'mac', '苹果'],
            'tsla': ['tesla', 'elon musk', 'electric vehicle', '特斯拉', '马斯克'],
            'nvda': ['nvidia', 'gpu', 'ai chip', '英伟达'],
            'msft': ['microsoft', 'windows', 'azure', '微软'],
            'googl': ['google', 'alphabet', 'search', '谷歌']
        }

        # A股公司名称匹配（常见股票）
        a_share_company_names = {
            '600519': ['茅台', '贵州茅台'],
            '000001': ['平安银行'],
            '600036': ['招商银行', '招行'],
            '601318': ['中国平安', '平安'],
            '000858': ['五粮液'],
            '601288': ['农业银行', '农行'],
            '601398': ['工商银行', '工行'],
            '600000': ['浦发银行', '浦发'],
            '000002': ['万科'],
            '000333': ['美的集团', '美的'],
        }

        # 检查美股公司关键词
        if ticker_lower in us_company_names:
            for name in us_company_names[ticker_lower]:
                if name in text:
                    logger.debug(f"[相关性计算] 检测到公司相关关键词 '{name}' 在标题中，相关性评分: 0.9，标题: {title[:50]}...")
                    return 0.9

        # 检查A股公司关键词
        if pure_code in a_share_company_names:
            for name in a_share_company_names[pure_code]:
                if name in text:
                    logger.debug(f"[相关性计算] 检测到A股公司关键词 '{name}' 在标题中，相关性评分: 0.9，标题: {title[:50]}...")
                    return 0.9

        logger.debug(f"[相关性计算] 未检测到明确相关性，使用默认评分: 0.3，标题: {title[:50]}...")
        return 0.3  # 默认相关性
    
    def _deduplicate_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """去重新闻"""
        logger.info(f"[新闻去重] 开始对 {len(news_items)} 条新闻进行去重处理")
        start_time = datetime.now()
        
        seen_titles = set()
        unique_news = []
        duplicate_count = 0
        short_title_count = 0
        
        for item in news_items:
            # 简单的标题去重
            title_key = item.title.lower().strip()
            
            # 检查标题长度
            if len(title_key) <= 10:
                logger.debug(f"[新闻去重] 跳过标题过短的新闻: '{item.title}'，来源: {item.source}")
                short_title_count += 1
                continue
                
            # 检查是否重复
            if title_key in seen_titles:
                logger.debug(f"[新闻去重] 检测到重复新闻: '{item.title[:50]}...'，来源: {item.source}")
                duplicate_count += 1
                continue
                
            # 添加到结果集
            seen_titles.add(title_key)
            unique_news.append(item)
        
        # 记录去重结果
        time_taken = (datetime.now() - start_time).total_seconds()
        logger.info(f"[新闻去重] 去重完成，原始新闻: {len(news_items)}条，去重后: {len(unique_news)}条，")
        logger.info(f"[新闻去重] 去除重复: {duplicate_count}条，标题过短: {short_title_count}条，耗时: {time_taken:.2f}秒")
        
        return unique_news
    
    def format_news_report(self, news_items: List[NewsItem], ticker: str) -> str:
        """格式化新闻报告"""
        logger.info(f"[新闻报告] 开始为 {ticker} 生成新闻报告")
        start_time = datetime.now()
        
        if not news_items:
            logger.warning(f"[新闻报告] 未获取到 {ticker} 的实时新闻数据")
            return f"未获取到{ticker}的实时新闻数据。"
        
        # 按紧急程度分组
        high_urgency = [n for n in news_items if n.urgency == 'high']
        medium_urgency = [n for n in news_items if n.urgency == 'medium']
        low_urgency = [n for n in news_items if n.urgency == 'low']
        
        # 记录新闻分类情况
        logger.info(f"[新闻报告] {ticker} 新闻分类统计: 高紧急度 {len(high_urgency)}条, 中紧急度 {len(medium_urgency)}条, 低紧急度 {len(low_urgency)}条")
        
        # 记录新闻来源分布
        news_sources = {}
        for item in news_items:
            source = item.source
            if source in news_sources:
                news_sources[source] += 1
            else:
                news_sources[source] = 1
        
        sources_info = ", ".join([f"{source}: {count}条" for source, count in news_sources.items()])
        logger.info(f"[新闻报告] {ticker} 新闻来源分布: {sources_info}")
        
        report = f"# {ticker} 实时新闻分析报告\n\n"
        report += f" 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f" 新闻总数: {len(news_items)}条\n\n"
        
        if high_urgency:
            report += "##  紧急新闻\n\n"
            for news in high_urgency[:3]:  # 最多显示3条
                report += f"### {news.title}\n"
                report += f"**来源**: {news.source} | **时间**: {news.publish_time.strftime('%H:%M')}\n"
                report += f"{news.content}\n\n"
        
        if medium_urgency:
            report += "##  重要新闻\n\n"
            for news in medium_urgency[:5]:  # 最多显示5条
                report += f"### {news.title}\n"
                report += f"**来源**: {news.source} | **时间**: {news.publish_time.strftime('%H:%M')}\n"
                report += f"{news.content}\n\n"
        
        # 添加时效性说明
        latest_news = max(news_items, key=lambda x: x.publish_time)
        time_diff = datetime.now() - latest_news.publish_time
        
        report += f"\n## ⏰ 数据时效性\n"
        report += f"最新新闻发布于: {time_diff.total_seconds() / 60:.0f}分钟前\n"
        
        if time_diff.total_seconds() < 1800:  # 30分钟内
            report += " 数据时效性: 优秀 (30分钟内)\n"
        elif time_diff.total_seconds() < 3600:  # 1小时内
            report += " 数据时效性: 良好 (1小时内)\n"
        else:
            report += " 数据时效性: 一般 (超过1小时)\n"
        
        # 记录报告生成完成信息
        end_time = datetime.now()
        time_taken = (end_time - start_time).total_seconds()
        report_length = len(report)
        
        logger.info(f"[新闻报告] {ticker} 新闻报告生成完成，耗时: {time_taken:.2f}秒，报告长度: {report_length}字符")
        
        # 记录时效性信息
        time_diff_minutes = time_diff.total_seconds() / 60
        logger.info(f"[新闻报告] {ticker} 新闻时效性: 最新新闻发布于 {time_diff_minutes:.1f}分钟前")
        
        return report


def get_realtime_stock_news(ticker: str, curr_date: str, hours_back: int = 6) -> str:
    """
    获取实时股票新闻的主要接口函数
    添加缓存机制，避免短时间内重复获取相同数据
    """
    # 检查缓存
    cache_key = f"{ticker}_{curr_date}_{hours_back}"
    current_time = time.time()

    if cache_key in _news_cache:
        cached_data, cached_time = _news_cache[cache_key]
        if current_time - cached_time < _news_cache_ttl:
            logger.info(f" [新闻缓存] 使用缓存数据: {ticker}, 缓存时间: {int(current_time - cached_time)}秒前")
            return cached_data

    logger.info(f" [新闻分析] 获取新数据: {ticker}")
    logger.info(f"[新闻分析] ========== 函数入口 ==========")
    logger.info(f"[新闻分析] 函数: get_realtime_stock_news")
    logger.info(f"[新闻分析] 参数: ticker={ticker}, curr_date={curr_date}, hours_back={hours_back}")
    logger.info(f"[新闻分析] 开始获取 {ticker} 的实时新闻，日期: {curr_date}, 回溯时间: {hours_back}小时")
    start_total_time = datetime.now()
    logger.info(f"[新闻分析] 开始时间: {start_total_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    
    # 判断股票类型
    logger.info(f"[新闻分析] ========== 步骤1: 股票类型判断 ==========")
    stock_type = "未知"
    is_china_stock = False
    logger.info(f"[新闻分析] 原始ticker: {ticker}")
    
    if '.' in ticker:
        logger.info(f"[新闻分析] 检测到ticker包含点号，进行后缀匹配")
        if any(suffix in ticker for suffix in ['.SH', '.SZ', '.SS', '.XSHE', '.XSHG']):
            stock_type = "A股"
            is_china_stock = True
            logger.info(f"[新闻分析] 匹配到A股后缀，股票类型: {stock_type}")
        elif '.HK' in ticker:
            stock_type = "港股"
            logger.info(f"[新闻分析] 匹配到港股后缀，股票类型: {stock_type}")
        elif any(suffix in ticker for suffix in ['.US', '.N', '.O', '.NYSE', '.NASDAQ']):
            stock_type = "美股"
            logger.info(f"[新闻分析] 匹配到美股后缀，股票类型: {stock_type}")
        else:
            logger.info(f"[新闻分析] 未匹配到已知后缀")
    else:
        logger.info(f"[新闻分析] ticker不包含点号，尝试使用StockUtils判断")
        # 尝试使用StockUtils判断股票类型
        try:
            from tradingagents.utils.stock_utils import StockUtils
            logger.info(f"[新闻分析] 成功导入StockUtils，开始判断股票类型")
            market_info = StockUtils.get_market_info(ticker)
            logger.info(f"[新闻分析] StockUtils返回市场信息: {market_info}")
            if market_info['is_china']:
                stock_type = "A股"
                is_china_stock = True
                logger.info(f"[新闻分析] StockUtils判断为A股")
            elif market_info['is_hk']:
                stock_type = "港股"
                logger.info(f"[新闻分析] StockUtils判断为港股")
            elif market_info['is_us']:
                stock_type = "美股"
                logger.info(f"[新闻分析] StockUtils判断为美股")
        except Exception as e:
            logger.warning(f"[新闻分析] 使用StockUtils判断股票类型失败: {e}")
    
    logger.info(f"[新闻分析] 最终判断结果 - 股票 {ticker} 类型: {stock_type}, 是否A股: {is_china_stock}")
    
    # 对于A股，优先使用Tushare新闻
    if is_china_stock:
        logger.info(f"[新闻分析] ========== 步骤2: A股Tushare新闻获取 ==========")
        logger.info(f"[新闻分析] 检测到A股股票 {ticker}，优先尝试使用Tushare新闻接口")
        try:
            logger.info(f"[新闻分析] 尝试导入 tushare_utils.get_stock_news_tushare")
            from .tushare_utils import get_stock_news_tushare
            logger.info(f"[新闻分析] 成功导入 get_stock_news_tushare 函数")

            # 计算日期范围
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(hours=hours_back)).strftime('%Y-%m-%d')

            logger.info(f"[新闻分析] 准备调用 get_stock_news_tushare(symbol={ticker}, start_date={start_date}, end_date={end_date}, max_news=10)")
            logger.info(f"[新闻分析] 开始从Tushare获取 {ticker} 的新闻数据")
            start_time = datetime.now()
            logger.info(f"[新闻分析] Tushare API调用开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")

            news_df = get_stock_news_tushare(
                symbol=ticker,
                start_date=start_date,
                end_date=end_date,
                max_news=10
            )

            end_time = datetime.now()
            time_taken = (end_time - start_time).total_seconds()
            logger.info(f"[新闻分析] Tushare API调用结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            logger.info(f"[新闻分析] Tushare API调用耗时: {time_taken:.2f}秒")
            logger.info(f"[新闻分析] Tushare API返回数据类型: {type(news_df)}")

            if hasattr(news_df, 'empty'):
                logger.info(f"[新闻分析] Tushare API返回DataFrame，是否为空: {news_df.empty}")
                if not news_df.empty:
                    logger.info(f"[新闻分析] Tushare API返回DataFrame形状: {news_df.shape}")
                    logger.info(f"[新闻分析] Tushare API返回DataFrame列名: {list(news_df.columns) if hasattr(news_df, 'columns') else '无列名'}")
            else:
                logger.info(f"[新闻分析] Tushare API返回数据: {news_df}")

            if not news_df.empty:
                # 构建简单的新闻报告
                news_count = len(news_df)
                logger.info(f"[新闻分析] 成功获取 {news_count} 条Tushare新闻，耗时 {time_taken:.2f} 秒")

                report = f"# {ticker} Tushare新闻报告\n\n"
                report += f" 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                report += f" 新闻总数: {news_count}条\n"
                report += f" 获取耗时: {time_taken:.2f}秒\n\n"

                # 记录一些新闻标题示例
                sample_titles = [row.get('title', '无标题') for _, row in news_df.head(3).iterrows()]
                logger.info(f"[新闻分析] 新闻标题示例: {', '.join(sample_titles)}")

                logger.info(f"[新闻分析] 开始构建新闻报告")
                for idx, (_, row) in enumerate(news_df.iterrows()):
                    if idx < 3:  # 只记录前3条的详细信息
                        logger.info(f"[新闻分析] 第{idx+1}条新闻: 标题={row.get('title', '无标题')}, 时间={row.get('datetime', '无时间')}")

                    # 获取新闻来源
                    source = row.get('source', 'Tushare')
                    if source == 'eastmoney':
                        source = '东方财富'
                    elif source == 'sina':
                        source = '新浪财经'
                    elif source == '10jqka':
                        source = '同花顺'

                    report += f"### {row.get('title', '')}\n"
                    report += f" {row.get('datetime', '')}\n"
                    report += f" 来源: {source}\n\n"
                    report += f"{row.get('content', '无内容')}\n\n"

                total_time_taken = (datetime.now() - start_total_time).total_seconds()
                logger.info(f"[新闻分析] 成功生成 {ticker} 的新闻报告，总耗时 {total_time_taken:.2f} 秒，新闻来源: Tushare")
                logger.info(f"[新闻分析] 报告长度: {len(report)} 字符")
                logger.info(f"[新闻分析] ========== Tushare新闻获取成功，函数即将返回 ==========")

                # 缓存结果
                _news_cache[cache_key] = (report, current_time)
                logger.info(f" [新闻缓存] 缓存数据: {ticker}, TTL: {_news_cache_ttl}秒")

                return report
            else:
                logger.warning(f"[新闻分析] Tushare未获取到 {ticker} 的新闻，耗时 {time_taken:.2f} 秒，尝试使用其他新闻源")
        except Exception as e:
            logger.error(f"[新闻分析] Tushare新闻获取失败: {e}，将尝试其他新闻源")
            logger.error(f"[新闻分析] 异常详情: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"[新闻分析] 异常堆栈: {traceback.format_exc()}")
    else:
        logger.info(f"[新闻分析] ========== 跳过A股Tushare新闻获取 ==========")
        logger.info(f"[新闻分析] 股票类型为 {stock_type}，不是A股，跳过Tushare新闻源")
    
    # 如果不是A股或A股新闻获取失败，使用实时新闻聚合器
    logger.info(f"[新闻分析] ========== 步骤3: 实时新闻聚合器 ==========")
    aggregator = RealtimeNewsAggregator()
    logger.info(f"[新闻分析] 成功创建实时新闻聚合器实例")
    try:
        logger.info(f"[新闻分析] 尝试使用实时新闻聚合器获取 {ticker} 的新闻")
        start_time = datetime.now()
        logger.info(f"[新闻分析] 聚合器调用开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # 获取实时新闻
        news_items = aggregator.get_realtime_stock_news(ticker, hours_back, max_news=10)
        
        end_time = datetime.now()
        time_taken = (end_time - start_time).total_seconds()
        logger.info(f"[新闻分析] 聚合器调用结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        logger.info(f"[新闻分析] 聚合器调用耗时: {time_taken:.2f}秒")
        logger.info(f"[新闻分析] 聚合器返回数据类型: {type(news_items)}")
        logger.info(f"[新闻分析] 聚合器返回数据: {news_items}")
        
        # 如果成功获取到新闻
        if news_items and len(news_items) > 0:
            news_count = len(news_items)
            logger.info(f"[新闻分析] 实时新闻聚合器成功获取 {news_count} 条 {ticker} 的新闻，耗时 {time_taken:.2f} 秒")
            
            # 记录一些新闻标题示例
            sample_titles = [item.title for item in news_items[:3]]
            logger.info(f"[新闻分析] 新闻标题示例: {', '.join(sample_titles)}")
            
            # 格式化报告
            logger.info(f"[新闻分析] 开始格式化新闻报告")
            report = aggregator.format_news_report(news_items, ticker)
            logger.info(f"[新闻分析] 报告格式化完成，长度: {len(report)} 字符")
            
            total_time_taken = (datetime.now() - start_total_time).total_seconds()
            logger.info(f"[新闻分析] 成功生成 {ticker} 的新闻报告，总耗时 {total_time_taken:.2f} 秒，新闻来源: 实时新闻聚合器")
            logger.info(f"[新闻分析] ========== 实时新闻聚合器获取成功，函数即将返回 ==========")

            # 缓存结果
            _news_cache[cache_key] = (report, current_time)
            logger.info(f" [新闻缓存] 缓存数据: {ticker}, TTL: {_news_cache_ttl}秒")

            return report
        else:
            logger.warning(f"[新闻分析] 实时新闻聚合器未获取到 {ticker} 的新闻，耗时 {time_taken:.2f} 秒，尝试使用备用新闻源")
            # 如果没有获取到新闻，继续尝试备用方案
    except Exception as e:
        logger.error(f"[新闻分析] 实时新闻聚合器获取失败: {e}，将尝试备用新闻源")
        logger.error(f"[新闻分析] 异常详情: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"[新闻分析] 异常堆栈: {traceback.format_exc()}")
        # 发生异常时，继续尝试备用方案
    
    # 备用方案1: 对于港股，优先尝试使用Tushare新闻（A股已在前面处理）
    if not is_china_stock and '.HK' in ticker:
        logger.info(f"[新闻分析] 检测到港股代码 {ticker}，尝试使用Tushare新闻")
        try:
            from .tushare_utils import get_stock_news_tushare

            # 计算日期范围
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(hours=hours_back)).strftime('%Y-%m-%d')

            logger.info(f"[新闻分析] 开始从Tushare获取港股 {ticker} 的新闻数据")
            start_time = datetime.now()
            news_df = get_stock_news_tushare(
                symbol=ticker,
                start_date=start_date,
                end_date=end_date,
                max_news=10
            )
            end_time = datetime.now()
            time_taken = (end_time - start_time).total_seconds()

            if not news_df.empty:
                # 构建简单的新闻报告
                news_count = len(news_df)
                logger.info(f"[新闻分析] 成功获取 {news_count} 条Tushare港股新闻，耗时 {time_taken:.2f} 秒")

                report = f"# {ticker} Tushare新闻报告\n\n"
                report += f" 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                report += f" 新闻总数: {news_count}条\n"
                report += f" 获取耗时: {time_taken:.2f}秒\n\n"

                # 记录一些新闻标题示例
                sample_titles = [row.get('title', '无标题') for _, row in news_df.head(3).iterrows()]
                logger.info(f"[新闻分析] 新闻标题示例: {', '.join(sample_titles)}")

                for _, row in news_df.iterrows():
                    # 获取新闻来源
                    source = row.get('source', 'Tushare')
                    if source == 'eastmoney':
                        source = '东方财富'
                    elif source == 'sina':
                        source = '新浪财经'
                    elif source == '10jqka':
                        source = '同花顺'

                    report += f"### {row.get('title', '')}\n"
                    report += f" {row.get('datetime', '')}\n"
                    report += f" 来源: {source}\n\n"
                    report += f"{row.get('content', '无内容')}\n\n"

                logger.info(f"[新闻分析] 成功生成Tushare港股新闻报告")

                # 缓存结果
                _news_cache[cache_key] = (report, current_time)
                logger.info(f" [新闻缓存] 缓存数据: {ticker}, TTL: {_news_cache_ttl}秒")

                return report
            else:
                logger.warning(f"[新闻分析] Tushare未获取到 {ticker} 的港股新闻数据，耗时 {time_taken:.2f} 秒，尝试下一个备用方案")
        except Exception as e:
            logger.error(f"[新闻分析] Tushare新闻获取失败: {e}，将尝试下一个备用方案")
    
    # 备用方案2: 尝试使用Google新闻
    try:
        from tradingagents.dataflows.interface import get_google_news
        
        # 根据股票类型构建搜索查询
        if stock_type == "A股":
            # A股使用中文关键词
            clean_ticker = ticker.replace('.SH', '').replace('.SZ', '').replace('.SS', '')\
                           .replace('.XSHE', '').replace('.XSHG', '')
            search_query = f"{clean_ticker} 股票 公司 财报 新闻"
            logger.info(f"[新闻分析] 开始从Google获取A股 {clean_ticker} 的中文新闻数据，查询: {search_query}")
        elif stock_type == "港股":
            # 港股使用中文关键词
            clean_ticker = ticker.replace('.HK', '')
            search_query = f"{clean_ticker} 港股 公司"
            logger.info(f"[新闻分析] 开始从Google获取港股 {clean_ticker} 的新闻数据，查询: {search_query}")
        else:
            # 美股使用英文关键词
            search_query = f"{ticker} stock news"
            logger.info(f"[新闻分析] 开始从Google获取 {ticker} 的新闻数据，查询: {search_query}")
        
        start_time = datetime.now()
        google_news = get_google_news(search_query, curr_date, 1)
        end_time = datetime.now()
        time_taken = (end_time - start_time).total_seconds()
        
        if google_news and len(google_news.strip()) > 0:
            # 估算获取的新闻数量
            news_lines = google_news.strip().split('\n')
            news_count = sum(1 for line in news_lines if line.startswith('###'))
            
            logger.info(f"[新闻分析] 成功获取 Google 新闻，估计 {news_count} 条新闻，耗时 {time_taken:.2f} 秒")
            
            # 记录一些新闻标题示例
            sample_titles = [line.replace('### ', '') for line in news_lines if line.startswith('### ')][:3]
            if sample_titles:
                logger.info(f"[新闻分析] 新闻标题示例: {', '.join(sample_titles)}")

            logger.info(f"[新闻分析] 成功生成 Google 新闻报告，新闻来源: Google")

            # 缓存结果
            _news_cache[cache_key] = (google_news, current_time)
            logger.info(f" [新闻缓存] 缓存数据: {ticker}, TTL: {_news_cache_ttl}秒")

            return google_news
        else:
            logger.warning(f"[新闻分析] Google 新闻未获取到 {ticker} 的新闻数据，耗时 {time_taken:.2f} 秒")
    except Exception as e:
        logger.error(f"[新闻分析] Google 新闻获取失败: {e}，所有备用方案均已尝试")
    
    # 所有方法都失败，返回None表示无新闻数据
    total_time_taken = (datetime.now() - start_total_time).total_seconds()
    logger.error(f"[新闻分析] {ticker} 的所有新闻获取方法均已失败，总耗时 {total_time_taken:.2f} 秒")

    # 记录详细的失败信息
    failure_details = {
        "股票代码": ticker,
        "股票类型": stock_type,
        "分析日期": curr_date,
        "回溯时间": f"{hours_back}小时",
        "总耗时": f"{total_time_taken:.2f}秒"
    }
    logger.error(f"[新闻分析] 新闻获取失败详情: {failure_details}")
    logger.info(f"[新闻分析] 返回None，表示无可用新闻数据")

    # 缓存None结果，避免短时间内重复失败
    _news_cache[cache_key] = (None, current_time)
    logger.info(f" [新闻缓存] 缓存None结果: {ticker}, TTL: {_news_cache_ttl}秒")

    return None
