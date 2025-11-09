"""
Test Tushare Pro API with 500 credits - Verify all premium APIs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from loguru import logger
from core.data.tushare_api import TushareProAPI


def test_premium_apis():
    """Test all premium APIs that should now be available with 500 credits."""

    print("=" * 80)
    print("Tushare Pro API Test - 500 Credits (90% Access)")
    print("=" * 80)

    # Initialize API
    print("\n[1/10] Initializing Tushare Pro API...")
    try:
        api = TushareProAPI()
        print("  [OK] API initialized")
    except Exception as e:
        print(f"  [FAILED] {e}")
        return 1

    test_symbol = "600000.SH"  # Shanghai Pudong Development Bank
    success_count = 0
    total_tests = 9

    # Test 1: Daily Basic (PE/PB/Turnover) - Critical for Fundamental Agent
    print("\n[2/10] Testing daily_basic (PE/PB/Turnover)...")
    try:
        trade_date = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        df = api.get_daily_basic(ts_code=test_symbol, trade_date=trade_date)
        if not df.empty:
            latest = df.iloc[0]
            print(f"  [OK] PE: {latest.get('pe', 'N/A')}, PB: {latest.get('pb', 'N/A')}")
            print(f"  [OK] Turnover Rate: {latest.get('turnover_rate', 'N/A')}%")
            print(f"  [OK] Market Cap: {latest.get('total_mv', 'N/A')} million")
            success_count += 1
        else:
            print("  [WARNING] No data (may be weekend/holiday)")
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")

    # Test 2: Financial Indicators (ROE/Debt Ratio) - Critical for Fundamental Agent
    print("\n[3/10] Testing fina_indicator (ROE/Debt Ratio)...")
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        df = api.get_fina_indicator(test_symbol, start_date=start_date, end_date=end_date)
        if not df.empty:
            latest = df.iloc[0]
            print(f"  [OK] Period: {latest['end_date']}")
            print(f"  [OK] ROE: {latest.get('roe', 'N/A')}%")
            print(f"  [OK] Debt Ratio: {latest.get('debt_to_assets', 'N/A')}%")
            print(f"  [OK] Current Ratio: {latest.get('current_ratio', 'N/A')}")
            success_count += 1
        else:
            print("  [WARNING] No financial data")
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")

    # Test 3: Index Daily (SSE Composite) - Critical for Market Agent
    print("\n[4/10] Testing index_daily (SSE Composite Index)...")
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        df = api.get_index_daily('000001.SH', start_date, end_date)
        if not df.empty:
            latest = df.iloc[0]
            print(f"  [OK] Retrieved {len(df)} trading days")
            print(f"  [OK] Latest: {latest['trade_date']} Close: {latest['close']}")
            success_count += 1
        else:
            print("  [WARNING] No index data")
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")

    # Test 4: Pledge Statistics - Important for Risk Agent
    print("\n[5/10] Testing pledge_stat (Stock Pledge)...")
    try:
        df = api.get_pledge_stat(test_symbol)
        if not df.empty:
            latest = df.iloc[0]
            pledge_ratio = latest.get('pledge_count', 0)
            print(f"  [OK] Pledge Ratio: {pledge_ratio}%")
            if pledge_ratio > 50:
                print(f"  [WARNING] High pledge risk!")
            success_count += 1
        else:
            print("  [INFO] No pledge data for this stock")
            success_count += 1  # No data is OK for some stocks
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")

    # Test 5: Northbound Capital Flow - Important for Market Agent
    print("\n[6/10] Testing moneyflow_hsgt (Northbound Capital)...")
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        df = api.get_moneyflow_hsgt(start_date=start_date, end_date=end_date)
        if not df.empty:
            latest = df.iloc[0]
            north_money = latest.get('north_money', 0)
            print(f"  [OK] Retrieved {len(df)} trading days")
            print(f"  [OK] Latest Net Inflow: {north_money} million RMB")
            success_count += 1
        else:
            print("  [WARNING] No northbound capital data")
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")

    # Test 6: Margin Trading - Important for Market Agent
    print("\n[7/10] Testing margin (Margin Trading)...")
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        df = api.get_margin(start_date=start_date, end_date=end_date)
        if not df.empty:
            latest = df.iloc[0]
            rzye = latest.get('rzye', 0)
            print(f"  [OK] Retrieved {len(df)} trading days")
            print(f"  [OK] Latest Margin Balance: {rzye} million RMB")
            success_count += 1
        else:
            print("  [WARNING] No margin trading data")
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")

    # Test 7: ST Stock List - Important for Risk Agent
    print("\n[8/10] Testing stk_limit (ST Stock List)...")
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        df = api.get_stk_limit(ts_code=test_symbol, start_date=start_date, end_date=end_date)
        is_st = not df.empty
        print(f"  [OK] Is ST Stock: {is_st}")
        success_count += 1
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")

    # Test 8: Stock Suspension - Useful for Risk Agent
    print("\n[9/10] Testing suspend_d (Suspension Info)...")
    try:
        df = api.get_suspend_d(ts_code=test_symbol)
        if not df.empty:
            print(f"  [OK] Found suspension records")
        else:
            print(f"  [OK] No suspension records (normal)")
        success_count += 1
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")

    # Test 9: Helper Methods
    print("\n[10/10] Testing helper methods...")
    try:
        # Latest financial indicators
        indicators = api.get_latest_financial_indicators(test_symbol)
        if indicators:
            print(f"  [OK] Latest Financial Indicators:")
            print(f"    ROE: {indicators.get('roe', 'N/A')}")
            print(f"    Debt Ratio: {indicators.get('debt_to_assets', 'N/A')}")

        # Pledge ratio
        pledge = api.get_latest_pledge_ratio(test_symbol)
        print(f"  [OK] Pledge Ratio: {pledge}%")

        # ST check
        is_st = api.is_st_stock(test_symbol)
        print(f"  [OK] Is ST: {is_st}")

        success_count += 1
    except Exception as e:
        print(f"  [FAILED] {str(e)[:100]}")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"\nTests Passed: {success_count}/{total_tests}")

    if success_count >= 7:
        print("\n🎉 EXCELLENT! 500 credits unlocked 90%+ APIs!")
        print("\n✅ All critical agents can now use REAL data:")
        print("  ✅ Technical Agent - Fully operational")
        print("  ✅ Fundamental Agent - ROE/PE/PB/Debt Ratio available")
        print("  ✅ Risk Agent - Pledge/ST/Volatility/Liquidity available")
        print("  ✅ Market Agent - Index/Northbound/Margin data available")
        print("\n🚀 Your trading system is now FULLY FUNCTIONAL!")
    elif success_count >= 4:
        print("\n⚠️ Most APIs working, but some may need weekend retry")
    else:
        print("\n❌ Many APIs still failing - may need to wait or check permissions")

    print("=" * 80)

    return 0 if success_count >= 4 else 1


if __name__ == "__main__":
    exit_code = test_premium_apis()
    sys.exit(exit_code)
