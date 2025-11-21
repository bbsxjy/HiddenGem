#!/usr/bin/env python3
"""
测试Tushare新闻专用Token配置
验证TUSHARE_NEWS_TOKEN是否正确使用
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

def test_token_configuration():
    """测试Token配置"""
    print("=" * 80)
    print("Tushare Token配置检查")
    print("=" * 80)
    print()

    # 检查环境变量
    general_token = os.getenv('TUSHARE_TOKEN')
    news_token = os.getenv('TUSHARE_NEWS_TOKEN')

    print("[环境变量]")
    print(f"TUSHARE_TOKEN (通用):     {general_token[:20]}... (已配置)" if general_token else "TUSHARE_TOKEN (通用):     未配置")
    print(f"TUSHARE_NEWS_TOKEN (新闻): {news_token[:20]}... (已配置)" if news_token else "TUSHARE_NEWS_TOKEN (新闻): 未配置")
    print()

    # 导入provider函数
    from tradingagents.dataflows.tushare_utils import (
        get_tushare_provider,
        get_tushare_news_provider
    )

    print("[Provider初始化]")

    # 测试通用provider
    print("\n1. 通用Provider (get_tushare_provider):")
    general_provider = get_tushare_provider()
    if general_provider.connected:
        print("   [OK] 连接成功")
    else:
        print("   [FAIL] 连接失败")

    # 测试新闻provider
    print("\n2. 新闻Provider (get_tushare_news_provider):")
    news_provider = get_tushare_news_provider()
    if news_provider.connected:
        print("   [OK] 连接成功")
        if news_token:
            print("   [INFO] 使用专用新闻token")
        else:
            print("   [INFO] 回退到通用token")
    else:
        print("   [FAIL] 连接失败")

    # 测试是否是不同的实例
    print("\n3. Provider实例检查:")
    if news_token and id(general_provider) != id(news_provider):
        print("   [OK] 通用provider和新闻provider是不同实例（符合预期）")
    elif not news_token and id(general_provider) == id(news_provider):
        print("   [OK] 未配置新闻token，使用同一实例（符合预期）")
    else:
        print("   [WARNING] Provider实例状态异常")

    print()

    return general_provider, news_provider

def test_news_api():
    """测试新闻API"""
    print("=" * 80)
    print("新闻API功能测试")
    print("=" * 80)
    print()

    from tradingagents.dataflows.tushare_utils import get_stock_news_tushare
    from datetime import datetime, timedelta

    # 设置日期范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')

    print(f"[测试参数]")
    print(f"日期范围: {start_date} 到 {end_date}")
    print(f"数据来源: eastmoney (东方财富)")
    print()

    print("[开始获取新闻...]")
    try:
        news_df = get_stock_news_tushare(
            symbol=None,
            start_date=start_date,
            end_date=end_date,
            max_news=5
        )

        if not news_df.empty:
            print(f"[SUCCESS] 成功获取 {len(news_df)} 条新闻")
            print()
            print("[新闻示例]")
            for idx, row in news_df.head(3).iterrows():
                print(f"\n{idx + 1}. {row.get('title', '无标题')}")
                print(f"   时间: {row.get('datetime', '无时间')}")
                print(f"   来源: {row.get('source', '未知')}")
                if 'content' in row and row['content']:
                    content = str(row['content'])[:100]
                    print(f"   内容: {content}...")
        else:
            print("[WARNING] 未获取到新闻数据")
            print("可能原因:")
            print("  1. 频率限制：新闻接口有严格的频率限制")
            print("  2. 日期范围内无新闻数据")
            print("  3. Token权限不足")

    except Exception as e:
        print(f"[ERROR] 新闻获取失败: {e}")
        import traceback
        print(traceback.format_exc())

    print()

def main():
    """主函数"""
    print("\n")

    # 测试配置
    general_provider, news_provider = test_token_configuration()

    # 测试API
    if news_provider and news_provider.connected:
        test_news_api()
    else:
        print("[SKIP] 新闻provider未连接，跳过API测试")

    # 总结
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    print()

    news_token = os.getenv('TUSHARE_NEWS_TOKEN')
    if news_token:
        print("[SUCCESS] Tushare新闻专用Token配置成功!")
        print()
        print("配置详情:")
        print(f"  - 通用数据使用: TUSHARE_TOKEN")
        print(f"  - 新闻数据使用: TUSHARE_NEWS_TOKEN")
        print()
        print("Token分离的好处:")
        print("  1. 新闻接口使用专用token，避免频率限制冲突")
        print("  2. 通用数据接口不受影响")
        print("  3. 可以独立管理新闻接口的权限和配额")
    else:
        print("[INFO] 使用通用Token")
        print()
        print("建议:")
        print("  如果有专用新闻token，请在.env中配置:")
        print("  TUSHARE_NEWS_TOKEN=your_news_token_here")

    print()

if __name__ == "__main__":
    main()
