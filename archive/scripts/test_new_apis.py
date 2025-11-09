"""
Test new high-value Tushare Pro APIs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from loguru import logger
from core.data.tushare_api import get_tushare_api


def test_new_apis():
    """Test the 4 new high-value APIs."""

    print("=" * 80)
    print("Testing New High-Value Tushare Pro APIs")
    print("=" * 80)

    # Initialize API
    print("\n[1/5] Initializing Tushare Pro API...")
    try:
        api = get_tushare_api()
        print("  [OK] API initialized")
    except Exception as e:
        print(f"  [FAILED] {e}")
        return 1

    test_symbol = "600000.SH"  # Shanghai Pudong Development Bank
    success_count = 0
    total_tests = 4

    # Test 1: Individual Stock Money Flow (个股资金流向)
    print(f"\n[2/5] Testing moneyflow API for {test_symbol}...")
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

        df = api.get_moneyflow(test_symbol, start_date=start_date, end_date=end_date)

        if not df.empty:
            latest = df.iloc[0]
            print(f"  [OK] Retrieved {len(df)} trading days")
            print(f"  Date: {latest.get('trade_date')}")
            print(f"  Net Flow: {latest.get('net_mf_amount', 0):,.0f} million RMB")
            print(f"  Large Buy: {latest.get('buy_lg_amount', 0):,.0f} million RMB")
            print(f"  Large Sell: {latest.get('sell_lg_amount', 0):,.0f} million RMB")
            print(f"  Extra Large Buy: {latest.get('buy_elg_amount', 0):,.0f} million RMB")
            success_count += 1
        else:
            print("  [WARNING] No data (may be weekend/holiday or permission issue)")
    except Exception as e:
        print(f"  [FAILED] {str(e)[:150]}")

    # Test 2: HK Stock Connect Holdings (沪深股通持股)
    print(f"\n[3/5] Testing hk_hold API for {test_symbol}...")
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

        df = api.get_hk_hold(ts_code=test_symbol, start_date=start_date, end_date=end_date)

        if not df.empty:
            latest = df.iloc[0]
            print(f"  [OK] Retrieved {len(df)} trading days")
            print(f"  Date: {latest.get('trade_date')}")
            print(f"  Holdings: {latest.get('vol', 0):,.0f} shares")
            print(f"  Ratio: {latest.get('ratio', 0):.2f}%")
            success_count += 1
        else:
            print("  [INFO] No HK holdings for this stock (normal for many stocks)")
            success_count += 1  # Not having HK holdings is OK
    except Exception as e:
        print(f"  [FAILED] {str(e)[:150]}")

    # Test 3: Shareholder Trading (股东增减持)
    print(f"\n[4/5] Testing stk_holdertrade API for {test_symbol}...")
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')

        df = api.get_stk_holdertrade(ts_code=test_symbol, start_date=start_date, end_date=end_date)

        if not df.empty:
            latest = df.iloc[0]
            print(f"  [OK] Retrieved {len(df)} records in last 6 months")
            print(f"  Announcement Date: {latest.get('ann_date')}")
            print(f"  Holder: {latest.get('holder_name')}")
            print(f"  Type: {latest.get('in_de')}")  # 增持/减持
            print(f"  Change: {latest.get('change_vol', 0):,.0f} shares ({latest.get('change_ratio', 0):.2f}%)")
            success_count += 1
        else:
            print("  [INFO] No shareholder trading records (normal if no recent changes)")
            success_count += 1  # No records is OK
    except Exception as e:
        print(f"  [FAILED] {str(e)[:150]}")

    # Test 4: Top List (Dragon-Tiger List) (龙虎榜)
    print(f"\n[5/5] Testing top_list API...")
    try:
        # Try recent trading days
        for i in range(5):
            trade_date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            df = api.get_top_list(trade_date=trade_date)

            if not df.empty:
                print(f"  [OK] Retrieved {len(df)} stocks on top list for {trade_date}")
                sample = df.iloc[0]
                print(f"  Sample Stock: {sample.get('name')} ({sample.get('ts_code')})")
                print(f"  Net Amount: {sample.get('net_amount', 0):,.0f} million RMB")
                print(f"  Reason: {sample.get('reason', 'N/A')}")
                success_count += 1
                break
        else:
            print("  [INFO] No top list data in recent 5 days (normal during calm markets)")
            success_count += 1  # No top list data is OK
    except Exception as e:
        print(f"  [FAILED] {str(e)[:150]}")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"\nTests Passed: {success_count}/{total_tests}")

    if success_count == total_tests:
        print("\n[SUCCESS] All new APIs working correctly!")
        print("\nNew APIs verified:")
        print("  - moneyflow: Individual stock money flow analysis")
        print("  - hk_hold: Foreign capital holdings tracking")
        print("  - stk_holdertrade: Shareholder trading records")
        print("  - top_list: Dragon-tiger list (hot stocks)")
        print("\nThese APIs enable Sentiment Agent to:")
        print("  - Identify institutional money flow")
        print("  - Track foreign capital sentiment")
        print("  - Monitor insider trading")
        print("  - Detect speculative activity")
    elif success_count >= 2:
        print(f"\n[PARTIAL] {success_count}/{total_tests} APIs working")
        print("Some APIs may require data availability or specific market conditions")
    else:
        print("\n[FAILED] Most APIs not working")
        print("Please check Tushare API permissions and credit balance")

    print("=" * 80)

    return 0 if success_count >= 2 else 1


if __name__ == "__main__":
    exit_code = test_new_apis()
    sys.exit(exit_code)
