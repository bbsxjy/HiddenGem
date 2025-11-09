"""
验证停牌API的使用是否正确
测试300502股票的停牌状态
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from core.data.tushare_api import get_tushare_api
from loguru import logger


def test_suspension_api():
    """测试停牌API的使用"""

    try:
        # Initialize Tushare API
        tushare = get_tushare_api()

        # Test symbols
        test_symbols = ['300502', '000001']  # 300502报告有问题，000001作为对照

        for symbol in test_symbols:
            print(f"\n{'='*60}")
            print(f"测试股票: {symbol}")
            print(f"{'='*60}")

            ts_code = tushare._convert_symbol(symbol, to_tushare=True)
            print(f"Tushare格式: {ts_code}")

            # 1. 不带参数查询 - 返回所有历史停牌记录
            print("\n1. 查询停牌记录（不带日期参数）:")
            df_all = tushare.get_suspend_d(ts_code=ts_code)

            if df_all.empty:
                print(f"  无停牌记录")
            else:
                print(f"  共有 {len(df_all)} 条停牌记录:")
                print(f"  返回的列: {df_all.columns.tolist()}")
                print(df_all.head(10))

            # 2. 查询今日停牌 - 检查今天是否停牌
            today = datetime.now().strftime('%Y%m%d')
            print(f"\n2. 查询今日({today})是否停牌:")

            # 方法A: 查询suspend_date=today的记录
            df_today_suspend = tushare.get_suspend_d(ts_code=ts_code, suspend_date=today)
            if not df_today_suspend.empty:
                print(f"  今日有停牌记录:")
                print(df_today_suspend)
            else:
                print(f"  今日没有新的停牌")

            # 3. 分析是否当前停牌
            print(f"\n3. 分析当前停牌状态:")

            if df_all.empty:
                print(f"  状态: 正常交易（无停牌历史）")
            else:
                # 获取最近的停牌记录
                latest = df_all.iloc[0]
                print(f"  最近停牌记录:")
                print(latest)

                # 检查API返回的实际字段
                if 'trade_date' in df_all.columns:
                    # 这是suspend_d API，返回每日停牌时段信息
                    # trade_date: 交易日期
                    # suspend_timing: 停牌时段 (例如: 09:30-10:01)
                    # suspend_type: 停牌类型 (S=盘中停牌)
                    print(f"\n  这是盘中停牌数据(suspend_d)，不是长期停牌数据")
                    print(f"  需要使用 suspend API 获取长期停牌数据")
                else:
                    # 其他格式的停牌数据
                    print(f"  未知的停牌数据格式")

            # 4. 获取股票基本信息
            print(f"\n4. 股票基本信息:")
            stock_basic = tushare.get_stock_basic(ts_code=ts_code)
            if not stock_basic.empty:
                stock = stock_basic.iloc[0]
                print(f"  名称: {stock.get('name', 'N/A')}")
                print(f"  上市状态: {stock.get('list_status', 'N/A')}")
                print(f"  上市日期: {stock.get('list_date', 'N/A')}")

        print(f"\n{'='*60}")
        print("测试完成")
        print(f"{'='*60}")

    except Exception as e:
        logger.exception(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import pandas as pd
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    test_suspension_api()
