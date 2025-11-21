#!/usr/bin/env python3
"""
测试Tushare积分权限
检查12000积分可以访问哪些接口
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

import tushare as ts
import pandas as pd
from datetime import datetime, timedelta

# 初始化Tushare
token = os.getenv('TUSHARE_TOKEN')
ts.set_token(token)
pro = ts.pro_api()

# 测试接口列表
test_cases = {
    "基础行情数据": [
        {
            "name": "日线行情 (120积分)",
            "func": lambda: pro.daily(ts_code='000001.SZ', start_date='20251101', end_date='20251120'),
            "min_points": 120
        },
        {
            "name": "每日指标 (2000积分)",
            "func": lambda: pro.daily_basic(ts_code='000001.SZ', start_date='20251101', end_date='20251120'),
            "min_points": 2000
        },
    ],
    "财务数据": [
        {
            "name": "资产负债表 (500积分)",
            "func": lambda: pro.balancesheet(ts_code='000001.SZ', period='20240930'),
            "min_points": 500
        },
        {
            "name": "利润表 (500积分)",
            "func": lambda: pro.income(ts_code='000001.SZ', period='20240930'),
            "min_points": 500
        },
        {
            "name": "现金流量表 (500积分)",
            "func": lambda: pro.cashflow(ts_code='000001.SZ', period='20240930'),
            "min_points": 500
        },
    ],
    "市场参考数据": [
        {
            "name": "沪深港通资金流向 (5000积分)",
            "func": lambda: pro.moneyflow_hsgt(trade_date='20251120'),
            "min_points": 5000
        },
        {
            "name": "北向资金持股 (5000积分)",
            "func": lambda: pro.hk_hold(trade_date='20251120'),
            "min_points": 5000
        },
    ],
    "基金数据 (8000积分+)": [
        {
            "name": "ETF基础信息 (8000积分)",
            "func": lambda: pro.fund_basic(market='E', limit=10),
            "min_points": 8000
        },
        {
            "name": "基金净值 (8000积分)",
            "func": lambda: pro.fund_nav(ts_code='510300.SH', start_date='20251101', end_date='20251120'),
            "min_points": 8000
        },
    ],
    "高级数据": [
        {
            "name": "概念板块 (5000积分)",
            "func": lambda: pro.concept(src='ts'),
            "min_points": 5000
        },
        {
            "name": "指数成分 (5000积分)",
            "func": lambda: pro.index_weight(index_code='000001.SH', start_date='20251101', end_date='20251120'),
            "min_points": 5000
        },
        {
            "name": "新闻数据 (5000积分)",
            "func": lambda: pro.news(src='sina', start_date='20251120', end_date='20251121'),
            "min_points": 5000
        },
    ],
}

def test_interface(name: str, func, min_points: int) -> dict:
    """测试单个接口"""
    try:
        result = func()
        if result is not None and not result.empty:
            return {
                "name": name,
                "status": "[OK] 可用",
                "min_points": min_points,
                "rows": len(result),
                "error": None
            }
        else:
            return {
                "name": name,
                "status": "[EMPTY] 返回空数据",
                "min_points": min_points,
                "rows": 0,
                "error": None
            }
    except Exception as e:
        error_msg = str(e)
        if "权限" in error_msg or "积分" in error_msg:
            return {
                "name": name,
                "status": "[DENY] 权限不足",
                "min_points": min_points,
                "rows": 0,
                "error": error_msg
            }
        elif "频次" in error_msg or "分钟" in error_msg or "小时" in error_msg:
            return {
                "name": name,
                "status": "[RATE] 频率限制",
                "min_points": min_points,
                "rows": 0,
                "error": error_msg
            }
        else:
            return {
                "name": name,
                "status": "[ERR] 错误",
                "min_points": min_points,
                "rows": 0,
                "error": error_msg
            }

def main():
    """主测试函数"""
    print("=" * 80)
    print("[Tushare权限测试]")
    print(f"Token: {token[:20]}...")
    print("=" * 80)
    print()

    all_results = []

    for category, tests in test_cases.items():
        print(f"\n{'='*80}")
        print(f"[{category}]")
        print(f"{'='*80}")

        for test in tests:
            print(f"\n测试: {test['name']} (需要{test['min_points']}积分)")
            result = test_interface(test['name'], test['func'], test['min_points'])
            all_results.append(result)

            print(f"  状态: {result['status']}")
            if result['rows'] > 0:
                print(f"  数据行数: {result['rows']}")
            if result['error']:
                print(f"  错误: {result['error'][:100]}")

            # 避免频率限制，每次测试间隔1秒
            import time
            time.sleep(1)

    # 汇总报告
    print(f"\n{'='*80}")
    print("[测试汇总]")
    print(f"{'='*80}")

    available = [r for r in all_results if "[OK]" in r['status']]
    rate_limited = [r for r in all_results if "[RATE]" in r['status']]
    permission_denied = [r for r in all_results if "[DENY]" in r['status']]
    errors = [r for r in all_results if "[ERR]" in r['status']]
    empty = [r for r in all_results if "[EMPTY]" in r['status']]

    print(f"\n[OK] 可用接口: {len(available)}/{len(all_results)}")
    for r in available:
        print(f"  - {r['name']} ({r['min_points']}积分)")

    if rate_limited:
        print(f"\n[RATE] 频率限制接口: {len(rate_limited)}")
        for r in rate_limited:
            print(f"  - {r['name']} ({r['min_points']}积分)")

    if permission_denied:
        print(f"\n[DENY] 权限不足接口: {len(permission_denied)}")
        for r in permission_denied:
            print(f"  - {r['name']} (需要{r['min_points']}积分)")

    if empty:
        print(f"\n[EMPTY] 返回空数据接口: {len(empty)}")
        for r in empty:
            print(f"  - {r['name']} ({r['min_points']}积分)")

    if errors:
        print(f"\n[ERR] 错误接口: {len(errors)}")
        for r in errors:
            print(f"  - {r['name']}: {r['error'][:50]}")

    print(f"\n{'='*80}")
    print("[建议]")
    print(f"{'='*80}")
    print("\n1. 访问 https://tushare.pro/user/token 查看完整权限表")
    print("2. 对于频率限制严格的接口（如新闻），建议使用akshare作为备选")
    print("3. 12000积分主要优势在于调用频次更高，而非接口数量")
    print()

if __name__ == "__main__":
    main()
