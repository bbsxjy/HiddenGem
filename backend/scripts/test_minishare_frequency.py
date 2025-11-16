"""
测试 MiniShare 数据更新频率和时间戳精度

测试内容：
1. 时间戳格式（秒级 vs 毫秒级）
2. 数据更新频率（多快刷新一次）
3. 同一股票连续请求的数据变化
"""

import minishare as ms
import time
from datetime import datetime
import pandas as pd

# MiniShare Token
MINISHARE_TOKEN = "8iSkc52Xim6EFhTZmr2Ptt3oCFd47GtNy00v0SETk9mDFC5tHCgzrVUneb60d394"

def test_timestamp_precision():
    """测试时间戳精度"""
    print("=" * 80)
    print("测试 1: 时间戳精度测试")
    print("=" * 80)

    api = ms.pro_api(MINISHARE_TOKEN)

    # 获取单只股票数据
    df = api.rt_k_ms(ts_code='000001.SZ')

    if not df.empty:
        print(f"\n返回的字段: {df.columns.tolist()}")
        print(f"\n样本数据（第一行）:")
        print(df.iloc[0].to_dict())

        # 检查是否有时间戳字段
        time_fields = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower()]
        print(f"\n时间相关字段: {time_fields}")

        if time_fields:
            for field in time_fields:
                print(f"\n{field} 的值: {df.iloc[0][field]}")
                print(f"{field} 的类型: {type(df.iloc[0][field])}")

    print("\n" + "=" * 80)


def test_update_frequency():
    """测试数据更新频率"""
    print("\n测试 2: 数据更新频率测试")
    print("=" * 80)
    print("连续请求同一只股票 10 次，间隔 1 秒")
    print("=" * 80)

    api = ms.pro_api(MINISHARE_TOKEN)
    symbol = '000001.SZ'

    results = []

    for i in range(10):
        request_time = datetime.now()

        df = api.rt_k_ms(ts_code=symbol)

        if not df.empty:
            row = df.iloc[0]

            result = {
                'round': i + 1,
                'request_time': request_time.strftime('%H:%M:%S.%f')[:-3],  # 毫秒精度
                'symbol': row.get('symbol', ''),
                'name': row.get('name', ''),
                'close': row.get('close', 0),  # 当前价
                'pct_chg': row.get('pct_chg', 0),  # 涨跌幅
                'vol': row.get('vol', 0),  # 成交量
                'amount': row.get('amount', 0),  # 成交额
            }

            results.append(result)

            print(f"\n第 {i+1} 轮: {request_time.strftime('%H:%M:%S.%f')[:-3]}")
            print(f"  价格: {result['close']:.2f}")
            print(f"  涨跌幅: {result['pct_chg']:+.2f}%")
            print(f"  成交量: {result['vol']}")

        if i < 9:  # 最后一次不等待
            time.sleep(1)

    # 分析结果
    print("\n" + "=" * 80)
    print("数据变化分析:")
    print("=" * 80)

    df_results = pd.DataFrame(results)

    # 检查价格变化
    price_changes = df_results['close'].diff().fillna(0)
    price_changed_count = (price_changes != 0).sum()

    print(f"\n总请求次数: {len(results)}")
    print(f"价格发生变化的次数: {price_changed_count}")
    print(f"价格变化率: {price_changed_count / len(results) * 100:.1f}%")

    # 显示价格变化详情
    if price_changed_count > 0:
        print("\n价格变化详情:")
        for i, change in enumerate(price_changes):
            if change != 0:
                print(f"  第 {i+1} 轮: {df_results.iloc[i]['close']:.2f} (变化 {change:+.2f})")

    # 检查成交量变化
    vol_changes = df_results['vol'].diff().fillna(0)
    vol_changed_count = (vol_changes != 0).sum()

    print(f"\n成交量发生变化的次数: {vol_changed_count}")
    print(f"成交量变化率: {vol_changed_count / len(results) * 100:.1f}%")

    print("\n" + "=" * 80)


def test_multiple_stocks_timestamp():
    """测试多只股票的时间戳"""
    print("\n测试 3: 批量获取多只股票")
    print("=" * 80)

    api = ms.pro_api(MINISHARE_TOKEN)

    # 获取3只股票
    symbols = ['000001.SZ', '600519.SH', '300502.SZ']

    for symbol in symbols:
        df = api.rt_k_ms(ts_code=symbol)

        if not df.empty:
            row = df.iloc[0]

            print(f"\n{symbol} - {row.get('name', '')}:")
            print(f"  价格: {row.get('close', 0):.2f}")
            print(f"  涨跌幅: {row.get('pct_chg', 0):+.2f}%")

            # 查看所有字段
            print(f"  所有字段: {row.to_dict()}")

    print("\n" + "=" * 80)


def test_rapid_requests():
    """测试快速连续请求（无间隔）"""
    print("\n测试 4: 快速连续请求测试（无间隔）")
    print("=" * 80)
    print("连续请求同一只股票 5 次，无间隔")
    print("=" * 80)

    api = ms.pro_api(MINISHARE_TOKEN)
    symbol = '000001.SZ'

    for i in range(5):
        start_time = time.time()
        request_time = datetime.now()

        df = api.rt_k_ms(ts_code=symbol)

        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # 毫秒

        if not df.empty:
            row = df.iloc[0]

            print(f"\n第 {i+1} 次: {request_time.strftime('%H:%M:%S.%f')}")
            print(f"  响应时间: {response_time:.2f} ms")
            print(f"  价格: {row.get('close', 0):.2f}")
            print(f"  涨跌幅: {row.get('pct_chg', 0):+.2f}%")

    print("\n" + "=" * 80)


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("MiniShare 数据频率和时间戳精度测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    try:
        # 测试 1: 时间戳精度
        test_timestamp_precision()

        # 测试 2: 数据更新频率（1秒间隔）
        test_update_frequency()

        # 测试 3: 多只股票
        test_multiple_stocks_timestamp()

        # 测试 4: 快速连续请求
        test_rapid_requests()

        print("\n" + "=" * 80)
        print("测试完成")
        print("=" * 80)

        print("\n结论:")
        print("1. 如果价格在1秒内变化 → 秒级或更高频率数据")
        print("2. 如果价格只在3-5秒后变化 → 3-5秒快照数据")
        print("3. 如果价格很少变化 → 可能是分钟级数据")
        print("4. 查看时间戳字段的格式可判断精度")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
