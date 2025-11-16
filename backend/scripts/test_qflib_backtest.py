"""
Test QF-Lib Backtest API Endpoint

测试 POST /api/v1/backtest/qflib/start 端点
"""

import requests
import json
from datetime import date, datetime

# API endpoint
BASE_URL = "http://192.168.31.147:8001"
ENDPOINT = f"{BASE_URL}/api/v1/backtest/qflib/start"

# Test request
request_data = {
    "model_path": "D:/Program Files (x86)/CodeRepos/HiddenGem/backend/models/ppo_trading_agent.zip",
    "symbols": ["000001.SZ", "600519.SH"],  # 平安银行 + 贵州茅台
    "start_date": "2024-01-01",
    "end_date": "2024-03-01",
    "initial_capital": 1000000.0,
    "commission_rate": 0.0003
}

print("=" * 80)
print("Testing QF-Lib Backtest API")
print("=" * 80)
print(f"\nEndpoint: {ENDPOINT}")
print(f"\nRequest Data:")
print(json.dumps(request_data, indent=2, ensure_ascii=False))
print("\n" + "=" * 80)

try:
    print("\nSending POST request...")
    response = requests.post(
        ENDPOINT,
        json=request_data,
        timeout=300  # 5 minutes timeout
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"\nResponse Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")

    print(f"\nResponse Body:")
    if response.headers.get('content-type', '').startswith('application/json'):
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result.get('success'):
            print("\n" + "=" * 80)
            print("Backtest Results Summary:")
            print("=" * 80)
            data = result.get('data', {})
            print(f"Initial Capital: ¥{data.get('initial_capital', 0):,.2f}")
            print(f"Final Value: ¥{data.get('final_value', 0):,.2f}")
            print(f"Total Return: {data.get('total_return_pct', 0):.2f}%")
            print(f"Max Drawdown: {data.get('max_drawdown_pct', 0):.2f}%")
            print(f"Number of Trades: {data.get('num_trades', 0)}")
    else:
        print(response.text)

    print("\n" + "=" * 80)
    if response.status_code == 200:
        print(" Test PASSED!")
    else:
        print(f" Test FAILED! Status Code: {response.status_code}")
    print("=" * 80)

except requests.exceptions.Timeout:
    print("\n Request timed out (exceeded 5 minutes)")
except requests.exceptions.ConnectionError:
    print("\n Connection error - Is the server running?")
    print(f"   Make sure server is running at {BASE_URL}")
except Exception as e:
    print(f"\n Error: {e}")
    import traceback
    traceback.print_exc()
