#!/usr/bin/env python3
"""
财联社新闻API测试脚本
测试多个可能的API接口
"""

import requests
import json
from datetime import datetime

def test_cls_api_v1():
    """
    测试财联社官方API v1
    URL: https://www.cls.cn/nodeapi/telegraphList
    """
    print("\n" + "="*80)
    print("[测试1] 财联社官方API - telegraphList")
    print("="*80)

    url = "https://www.cls.cn/nodeapi/telegraphList"

    # 尝试不同的参数组合
    params_list = [
        {
            "app": "CailianpressWeb",
            "os": "web",
            "sv": "8.4.6",
            "refresh_type": "1",
            "rn": "20"
        },
        {
            "app": "CailianpressWeb",
            "os": "web",
            "sv": "7.7.5",
            "refresh_type": "1",
            "rn": "20"
        }
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.cls.cn/',
        'Accept': 'application/json'
    }

    for idx, params in enumerate(params_list, 1):
        try:
            print(f"\n[尝试 {idx}] 参数: {params}")
            response = requests.get(url, params=params, headers=headers, timeout=10)

            print(f"状态码: {response.status_code}")
            print(f"响应长度: {len(response.text)} bytes")

            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"[成功] 返回JSON数据")
                    print(f"数据键: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")

                    # 尝试提取新闻数据
                    if 'data' in data:
                        if 'roll_data' in data['data']:
                            news_list = data['data']['roll_data']
                            print(f"新闻数量: {len(news_list)}")

                            if news_list:
                                print(f"\n[第一条新闻示例]")
                                first_news = news_list[0]
                                for key in ['ctime', 'title', 'brief', 'content']:
                                    if key in first_news:
                                        value = str(first_news[key])[:100]
                                        print(f"  {key}: {value}")

                                return True, url, params
                except json.JSONDecodeError:
                    print(f"[失败] 无法解析JSON: {response.text[:200]}")
            else:
                print(f"[失败] HTTP {response.status_code}: {response.text[:200]}")

        except Exception as e:
            print(f"[错误] {e}")

    return False, None, None

def test_cls_api_v2():
    """
    测试财联社API v2 (旧版RSS风格)
    URL: https://www.cls.cn/api/sw
    """
    print("\n" + "="*80)
    print("[测试2] 财联社API v2 - RSS风格")
    print("="*80)

    url = "https://www.cls.cn/api/sw"
    params = {
        "app": "CailianpressWeb",
        "os": "web",
        "sv": "7.7.5"
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.cls.cn/'
    }

    try:
        print(f"请求URL: {url}")
        print(f"参数: {params}")
        response = requests.get(url, params=params, headers=headers, timeout=10)

        print(f"状态码: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"响应长度: {len(response.text)} bytes")

        if response.status_code == 200:
            # 尝试JSON解析
            try:
                data = response.json()
                print(f"[成功] 返回JSON数据")
                print(f"数据键: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                print(f"数据预览: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
                return True, url, params
            except json.JSONDecodeError:
                # 尝试RSS解析
                print(f"[尝试] RSS/XML解析")
                try:
                    import feedparser
                    feed = feedparser.parse(response.text)

                    if feed.entries:
                        print(f"[成功] RSS解析成功")
                        print(f"条目数量: {len(feed.entries)}")
                        if feed.entries:
                            print(f"第一条: {feed.entries[0].get('title', 'No title')}")
                        return True, url, params
                    else:
                        print(f"[失败] RSS未返回条目")
                        print(f"响应内容: {response.text[:500]}")
                except Exception as e:
                    print(f"[失败] RSS解析错误: {e}")
                    print(f"响应内容: {response.text[:500]}")
        else:
            print(f"[失败] HTTP {response.status_code}")

    except Exception as e:
        print(f"[错误] {e}")

    return False, None, None

def test_third_party_api():
    """
    测试第三方财联社API
    URL: https://api.98dou.cn/api/hotlist/cls/all
    """
    print("\n" + "="*80)
    print("[测试3] 第三方API - 98dou.cn")
    print("="*80)

    url = "https://api.98dou.cn/api/hotlist/cls/all"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        print(f"请求URL: {url}")
        response = requests.get(url, headers=headers, timeout=10)

        print(f"状态码: {response.status_code}")
        print(f"响应长度: {len(response.text)} bytes")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"[成功] 返回JSON数据")
                print(f"数据键: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")

                # 尝试提取新闻
                if 'data' in data and isinstance(data['data'], list):
                    news_list = data['data']
                    print(f"新闻数量: {len(news_list)}")

                    if news_list:
                        print(f"\n[第一条新闻示例]")
                        first_news = news_list[0]
                        print(f"新闻键: {list(first_news.keys()) if isinstance(first_news, dict) else 'Not a dict'}")
                        for key, value in list(first_news.items())[:5]:
                            print(f"  {key}: {str(value)[:100]}")

                        return True, url, {}
                else:
                    print(f"数据预览: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
            except json.JSONDecodeError:
                print(f"[失败] 无法解析JSON: {response.text[:200]}")
        else:
            print(f"[失败] HTTP {response.status_code}")

    except Exception as e:
        print(f"[错误] {e}")

    return False, None, None

def test_direct_cls_telegraph():
    """
    测试直接访问财联社电报页面
    """
    print("\n" + "="*80)
    print("[测试4] 财联社电报页面")
    print("="*80)

    url = "https://www.cls.cn/telegraph"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    try:
        print(f"请求URL: {url}")
        response = requests.get(url, headers=headers, timeout=10)

        print(f"状态码: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")

        if response.status_code == 200:
            print(f"[成功] 页面访问成功")
            print(f"响应长度: {len(response.text)} bytes")

            # 检查是否包含API URL
            if 'nodeapi/telegraphList' in response.text:
                print(f"[发现] 页面包含 nodeapi/telegraphList API")
            if 'api.cls.cn' in response.text:
                print(f"[发现] 页面包含 api.cls.cn 域名")

        else:
            print(f"[失败] HTTP {response.status_code}")

    except Exception as e:
        print(f"[错误] {e}")

    return False, None, None

def main():
    """主测试函数"""
    print("="*80)
    print("财联社新闻API测试")
    print("="*80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []

    # 测试各个API
    success, url, params = test_cls_api_v1()
    if success:
        results.append(("官方API v1", url, params))

    success, url, params = test_cls_api_v2()
    if success:
        results.append(("官方API v2", url, params))

    success, url, params = test_third_party_api()
    if success:
        results.append(("第三方API", url, params))

    test_direct_cls_telegraph()

    # 汇总结果
    print("\n" + "="*80)
    print("测试汇总")
    print("="*80)

    if results:
        print(f"\n[成功] 找到 {len(results)} 个可用API:")
        for name, url, params in results:
            print(f"\n{name}:")
            print(f"  URL: {url}")
            if params:
                print(f"  参数: {params}")
    else:
        print("\n[失败] 未找到可用的财联社API")
        print("\n可能的原因:")
        print("  1. API接口已变更或需要认证")
        print("  2. 需要sign签名参数")
        print("  3. IP被限制或需要VIP会员")
        print("\n建议:")
        print("  1. 使用第三方财经新闻API（如东方财富、新浪财经）")
        print("  2. 联系财联社官方申请API权限")
        print("  3. 使用网页爬虫（需遵守robots.txt）")

    print()

if __name__ == "__main__":
    main()
