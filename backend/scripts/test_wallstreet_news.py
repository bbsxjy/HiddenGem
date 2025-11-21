#!/usr/bin/env python3
"""
测试华尔街见闻新闻API集成
验证新闻获取功能是否正常
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_wallstreet_news_direct():
    """直接测试华尔街见闻API"""
    print("=" * 80)
    print("测试1: 直接调用华尔街见闻API")
    print("=" * 80)
    print()

    from tradingagents.dataflows.realtime_news_utils import RealtimeNewsAggregator

    aggregator = RealtimeNewsAggregator()

    # 测试股票代码
    test_tickers = [
        ('600519.SH', '贵州茅台（A股）'),
        ('AAPL', 'Apple（美股）'),
        ('000001.SZ', '平安银行（A股）')
    ]

    for ticker, name in test_tickers:
        print(f"\n{'='*60}")
        print(f"测试股票: {name} ({ticker})")
        print(f"{'='*60}")

        try:
            # 获取最近24小时的新闻
            news_items = aggregator._fetch_wallstreet_news(ticker, hours_back=24)

            if news_items:
                print(f"[SUCCESS] 获取到 {len(news_items)} 条新闻")
                print()

                # 显示前3条新闻
                print("前3条新闻示例:")
                for idx, item in enumerate(news_items[:3], 1):
                    print(f"\n{idx}. {item.title}")
                    print(f"   时间: {item.publish_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   来源: {item.source}")
                    print(f"   相关性: {item.relevance_score:.2f}")
                    print(f"   紧急度: {item.urgency}")
                    print(f"   内容: {item.content[:100]}...")
                    if item.url:
                        print(f"   链接: {item.url}")
            else:
                print(f"[INFO] 未获取到 {ticker} 的相关新闻")
                print("可能原因:")
                print("  1. 最近24小时无相关新闻")
                print("  2. 相关性过滤：新闻中未提及该股票")

        except Exception as e:
            print(f"[ERROR] 测试失败: {e}")
            import traceback
            print(traceback.format_exc())

        print()

def test_integrated_news_flow():
    """测试集成后的新闻聚合流程"""
    print("=" * 80)
    print("测试2: 完整新闻聚合流程（包含华尔街见闻）")
    print("=" * 80)
    print()

    from tradingagents.dataflows.realtime_news_utils import get_realtime_stock_news

    # 测试A股代码
    ticker = "600519.SH"
    curr_date = datetime.now().strftime('%Y-%m-%d')

    print(f"股票代码: {ticker}")
    print(f"日期: {curr_date}")
    print(f"回溯时间: 24小时")
    print()
    print("新闻源优先级:")
    print("  1. Tushare新闻")
    print("  2. 财联社")
    print("  3. 华尔街见闻（新增）")
    print("  4. Google新闻（备选）")
    print()

    try:
        # 调用完整的新闻获取流程
        news_report = get_realtime_stock_news(ticker, curr_date, hours_back=24)

        if news_report and "实时新闻获取失败" not in news_report:
            print("[SUCCESS] 新闻聚合成功！")
            print()
            print("=" * 80)
            print("新闻报告（前500字符）:")
            print("=" * 80)
            print(news_report[:500])
            print("...")
            print()

            # 统计各个新闻源
            sources = {
                'Tushare': news_report.count('来源: eastmoney') + news_report.count('来源: sina'),
                '财联社': news_report.count('来源: 财联社'),
                '华尔街见闻': news_report.count('来源: 华尔街见闻'),
            }

            print("新闻来源统计:")
            for source, count in sources.items():
                if count > 0:
                    print(f"  - {source}: 约{count}条")

        else:
            print("[INFO] 未获取到新闻或出现错误")
            if news_report:
                print("返回信息:")
                print(news_report[:300])

    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        print(traceback.format_exc())

def test_wallstreet_api_raw():
    """测试华尔街见闻原始API响应"""
    print("=" * 80)
    print("测试3: 华尔街见闻原始API响应")
    print("=" * 80)
    print()

    import requests
    import json

    url = "https://api-prod.wallstreetcn.com/apiv1/content/lives"
    params = {
        'channel': 'global-channel',
        'client': 'pc',
        'cursor': '',
        'limit': 5
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://wallstreetcn.com/'
    }

    try:
        print(f"请求URL: {url}")
        print(f"参数: {params}")
        print()

        response = requests.get(url, params=params, headers=headers, timeout=10)

        print(f"状态码: {response.status_code}")
        print(f"响应大小: {len(response.text)} bytes")
        print()

        if response.status_code == 200:
            data = response.json()
            print("[SUCCESS] API调用成功")
            print()

            if data.get('code') == 20000:
                print("API响应码: 20000 (正常)")
                items = data.get('data', {}).get('items', [])
                print(f"返回新闻数量: {len(items)}")
                print()

                if items:
                    print("第一条新闻数据结构:")
                    first_item = items[0]
                    print(f"  - 可用字段: {list(first_item.keys())}")
                    print()
                    print("第一条新闻详情:")
                    print(json.dumps(first_item, indent=2, ensure_ascii=False)[:800])
                    print("...")
            else:
                print(f"API响应码: {data.get('code')} (异常)")
                print(f"错误信息: {data.get('message', '未知')}")
        else:
            print(f"[ERROR] HTTP {response.status_code}")

    except Exception as e:
        print(f"[ERROR] API调用失败: {e}")
        import traceback
        print(traceback.format_exc())

def main():
    """主测试函数"""
    print("\n")
    print("华尔街见闻新闻API集成测试")
    print("=" * 80)
    print()

    # 测试1: 原始API
    test_wallstreet_api_raw()
    print("\n" + "=" * 80 + "\n")

    # 测试2: 直接调用集成方法
    test_wallstreet_news_direct()
    print("\n" + "=" * 80 + "\n")

    # 测试3: 完整流程
    test_integrated_news_flow()

    print()
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    print()
    print("华尔街见闻新闻源特点:")
    print("  1. 实时财经快讯，更新频率高")
    print("  2. 无需API key，完全免费")
    print("  3. 支持中英文财经新闻")
    print("  4. 自动过滤低相关性新闻（相关性 < 0.5）")
    print()
    print("使用方式:")
    print("  from tradingagents.dataflows.realtime_news_utils import get_realtime_stock_news")
    print("  news = get_realtime_stock_news('600519.SH', '2025-11-21', hours_back=24)")
    print()
    print("注意事项:")
    print("  - 华尔街见闻主要是宏观财经新闻，个股相关新闻较少")
    print("  - 建议配合财联社、Tushare等多源使用")
    print("  - 相关性过滤会自动跳过不相关的新闻")
    print()

if __name__ == "__main__":
    main()
