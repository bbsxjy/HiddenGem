#!/usr/bin/env python3
"""
测试所有新闻API配置
验证API密钥是否正确配置
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

def test_finnhub():
    """测试FinnHub API配置"""
    key = os.getenv('FINNHUB_API_KEY')
    if key and key != 'your_finnhub_api_key_here':
        print("[OK] FinnHub API Key: 已配置")
        print(f"     密钥前缀: {key[:10]}...")

        # 测试API调用
        try:
            import requests
            response = requests.get(
                "https://finnhub.io/api/v1/company-news",
                params={
                    'symbol': 'AAPL',
                    'from': '2025-11-20',
                    'to': '2025-11-21',
                    'token': key
                },
                timeout=10
            )
            if response.status_code == 200:
                print("     API测试: 成功")
                return True
            elif response.status_code == 401:
                print("     API测试: 失败 - 密钥无效")
                return False
            else:
                print(f"     API测试: 失败 - HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"     API测试: 失败 - {e}")
            return False
    else:
        print("[未配置] FinnHub API Key")
        print("     获取地址: https://finnhub.io/")
        return False

def test_alpha_vantage():
    """测试Alpha Vantage API配置"""
    key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if key:
        print("[OK] Alpha Vantage API Key: 已配置")
        print(f"     密钥前缀: {key[:10]}...")

        # 测试API调用
        try:
            import requests
            response = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    'function': 'NEWS_SENTIMENT',
                    'tickers': 'AAPL',
                    'apikey': key
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if 'Error Message' in data:
                    print("     API测试: 失败 - 密钥无效")
                    return False
                else:
                    print("     API测试: 成功")
                    return True
            else:
                print(f"     API测试: 失败 - HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"     API测试: 失败 - {e}")
            return False
    else:
        print("[未配置] Alpha Vantage API Key")
        print("     获取地址: https://www.alphavantage.co/support/#api-key")
        return False

def test_newsapi():
    """测试NewsAPI配置"""
    key = os.getenv('NEWSAPI_KEY')
    if key:
        print("[OK] NewsAPI Key: 已配置")
        print(f"     密钥前缀: {key[:10]}...")

        # 测试API调用
        try:
            import requests
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    'q': 'AAPL',
                    'apiKey': key
                },
                timeout=10
            )
            if response.status_code == 200:
                print("     API测试: 成功")
                return True
            elif response.status_code == 401:
                print("     API测试: 失败 - 密钥无效")
                return False
            else:
                print(f"     API测试: 失败 - HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"     API测试: 失败 - {e}")
            return False
    else:
        print("[未配置] NewsAPI Key")
        print("     获取地址: https://newsapi.org/register")
        return False

def test_akshare():
    """测试AKShare"""
    try:
        import akshare as ak
        print("[OK] AKShare: 已安装")

        # 测试API调用
        try:
            news = ak.stock_news_em(symbol="600036")
            if news is not None and not news.empty:
                print(f"     API测试: 成功 - 获取到{len(news)}条新闻")
                return True
            else:
                print("     API测试: 返回空数据")
                return False
        except Exception as e:
            print(f"     API测试: 失败 - {e}")
            return False
    except ImportError:
        print("[未安装] AKShare")
        print("     安装命令: pip install akshare")
        return False

def test_tushare():
    """测试Tushare配置"""
    token = os.getenv('TUSHARE_TOKEN')
    if token and len(token) > 20:
        print("[OK] Tushare Token: 已配置")
        print(f"     密钥前缀: {token[:20]}...")

        # 测试API调用
        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()

            # 测试获取股票列表
            df = pro.stock_basic(exchange='', list_status='L', limit=10, fields='ts_code,symbol,name')
            if df is not None and not df.empty:
                print(f"     API测试: 成功 - 获取到{len(df)}条数据")
                return True
            else:
                print("     API测试: 返回空数据")
                return False
        except Exception as e:
            print(f"     API测试: 失败 - {e}")
            return False
    else:
        print("[未配置] Tushare Token")
        print("     获取地址: https://tushare.pro/register?reg=tacn")
        return False

def main():
    """主测试函数"""
    print("="*80)
    print("新闻API配置检查")
    print("="*80)
    print()

    results = {}

    print("[1/5] 测试 Tushare (A股数据源)...")
    results['Tushare'] = test_tushare()
    print()

    print("[2/5] 测试 AKShare (中文财经新闻)...")
    results['AKShare'] = test_akshare()
    print()

    print("[3/5] 测试 FinnHub (美股新闻)...")
    results['FinnHub'] = test_finnhub()
    print()

    print("[4/5] 测试 Alpha Vantage (新闻情绪)...")
    results['Alpha Vantage'] = test_alpha_vantage()
    print()

    print("[5/5] 测试 NewsAPI (全球新闻)...")
    results['NewsAPI'] = test_newsapi()
    print()

    # 汇总报告
    print("="*80)
    print("测试汇总")
    print("="*80)
    print()

    configured = [name for name, status in results.items() if status]
    not_configured = [name for name, status in results.items() if not status]

    print(f"配置完成度: {len(configured)}/5")
    print()

    if configured:
        print("[OK] 已配置的API:")
        for api in configured:
            print(f"  - {api}")
        print()

    if not_configured:
        print("[待配置] 未配置的API:")
        for api in not_configured:
            print(f"  - {api}")
        print()

    # 建议
    print("="*80)
    print("建议")
    print("="*80)
    print()

    if len(configured) == 5:
        print("[EXCELLENT] 所有API都已配置！")
    elif results.get('AKShare') and results.get('Tushare'):
        print("[GOOD] 核心API已配置（Tushare + AKShare），可以开始分析A股")
        print()
        print("可选配置：")
        if not results.get('FinnHub'):
            print("  - 配置FinnHub以获取美股新闻")
        if not results.get('Alpha Vantage'):
            print("  - 配置Alpha Vantage以获取新闻情绪分析")
        if not results.get('NewsAPI'):
            print("  - 配置NewsAPI以获取全球新闻聚合")
    else:
        print("[WARNING] 请至少配置以下核心API：")
        if not results.get('Tushare'):
            print("  - Tushare (A股数据源)")
        if not results.get('AKShare'):
            print("  - AKShare (中文财经新闻)")

    print()
    print("详细配置指南请参考: docs/NEWS_API_SETUP.md")
    print()

if __name__ == "__main__":
    main()
