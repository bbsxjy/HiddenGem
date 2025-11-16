"""
Task 4 Integration Test - 东方财富模拟盘功能测试

测试EastmoneySimulatedBroker和EastmoneyAdapter的基本功能
"""

import sys
import time
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

# Mock Order and Position classes (since they're from other tasks)
class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"

@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.MARKET
    limit_price: float = None
    order_id: str = ""
    status: OrderStatus = OrderStatus.PENDING

@dataclass
class Position:
    symbol: str
    quantity: int
    avg_price: float
    current_price: float = 0.0

# Add mock classes to sys.modules to allow imports
import types
order_module = types.ModuleType('trading.order')
order_module.Order = Order
order_module.OrderSide = OrderSide
order_module.OrderType = OrderType
order_module.OrderStatus = OrderStatus
sys.modules['trading.order'] = order_module

position_module = types.ModuleType('trading.position')
position_module.Position = Position
sys.modules['trading.position'] = position_module

# Now import our modules
sys.path.insert(0, '.')
from trading.base_broker import BaseBroker, BrokerLoginError, BrokerOrderError
from trading.eastmoney_sim_broker import EastmoneySimulatedBroker
from trading.adapters.eastmoney_adapter import EastmoneyAdapter

def test_broker_basic():
    """Test 1: Broker Basic Functionality"""
    print("\n=== Test 1: Broker Basic Functionality ===")

    config = {
        'account_id': 'test_user',
        'password': 'test_password',
        'initial_capital': 1000000
    }

    broker = EastmoneySimulatedBroker(config)

    # Test login
    assert broker.login() == True, "Login should succeed"
    assert broker.is_logged_in == True, "Should be logged in"
    assert broker.token is not None, "Token should be set"
    print("[PASS] Login successful")

    # Test get balance
    balance = broker.get_balance()
    assert balance['total_assets'] == 1000000, "Initial capital should be 1M"
    assert balance['available_cash'] == 1000000, "All cash should be available"
    print(f"[PASS] Get balance: {balance['total_assets']}")

    # Test get positions (should be empty initially)
    positions = broker.get_positions()
    assert isinstance(positions, list), "Positions should be a list"
    assert len(positions) == 0, "Initial positions should be empty"
    print("[PASS] Get positions (empty)")

    # Test submit order
    order = Order(
        symbol='600519.SH',
        side=OrderSide.BUY,
        quantity=100,
        order_type=OrderType.MARKET
    )
    result = broker.submit_order(order)
    assert result['success'] == True, "Order submission should succeed"
    assert 'broker_order_id' in result, "Should return broker order ID"
    print(f"[PASS] Submit order: {result['broker_order_id']}")

    # Test cancel order
    order_id = result['broker_order_id']
    cancel_result = broker.cancel_order(order_id)
    assert cancel_result['success'] == True, "Cancel should succeed"
    print(f"[PASS] Cancel order: {order_id}")

    # Test logout
    assert broker.logout() == True, "Logout should succeed"
    assert broker.is_logged_in == False, "Should be logged out"
    print("[PASS] Logout successful")

def test_order_validation():
    """Test 2: Order Validation"""
    print("\n=== Test 2: Order Validation ===")

    config = {'account_id': 'test', 'password': 'test'}
    broker = EastmoneySimulatedBroker(config)
    broker.login()

    # Test invalid quantity (0)
    order = Order(symbol='600519.SH', side=OrderSide.BUY, quantity=0)
    valid, msg = broker.validate_order(order)
    assert valid == False, "Order with quantity 0 should be invalid"
    print(f"[PASS] Reject order with quantity 0: {msg}")

    # Test invalid quantity (not multiple of 100)
    order.quantity = 150
    valid, msg = broker.validate_order(order)
    assert valid == False, "Order quantity must be multiple of 100"
    print(f"[PASS] Reject order with quantity 150: {msg}")

    # Test valid order
    order.quantity = 100
    valid, msg = broker.validate_order(order)
    assert valid == True, "Order with quantity 100 should be valid"
    print(f"[PASS] Accept valid order with quantity 100")

def test_adapter():
    """Test 3: EastmoneyAdapter"""
    print("\n=== Test 3: EastmoneyAdapter ===")

    # Test order conversion (internal -> broker)
    order = Order(
        symbol='600519.SH',
        side=OrderSide.BUY,
        quantity=100,
        order_type=OrderType.MARKET
    )
    broker_order = EastmoneyAdapter.adapt_order_to_broker(order)
    assert broker_order['symbol'] == '600519.SH', "Symbol should match"
    assert broker_order['side'] == 'buy', "Side should be 'buy'"
    assert broker_order['quantity'] == 100, "Quantity should match"
    print("[PASS] Order conversion (internal -> broker)")

    # Test order conversion (broker -> internal)
    broker_order_dict = {
        'order_id': 'EM123',
        'symbol': '000001.SZ',
        'side': 'sell',
        'quantity': 200,
        'order_type': 'limit',
        'status': 'filled'
    }
    internal_order = EastmoneyAdapter.adapt_order_from_broker(broker_order_dict)
    assert internal_order.symbol == '000001.SZ', "Symbol should match"
    assert internal_order.side == OrderSide.SELL, "Side should be SELL"
    assert internal_order.quantity == 200, "Quantity should match"
    assert internal_order.status == OrderStatus.FILLED, "Status should be FILLED"
    print("[PASS] Order conversion (broker -> internal)")

    # Test position conversion
    broker_position = {
        'symbol': '600519.SH',
        'quantity': 100,
        'avg_price': 1500.0,
        'current_price': 1550.0
    }
    position = EastmoneyAdapter.adapt_position_from_broker(broker_position)
    assert position.symbol == '600519.SH', "Symbol should match"
    assert position.quantity == 100, "Quantity should match"
    assert position.avg_price == 1500.0, "Avg price should match"
    print("[PASS] Position conversion (broker -> internal)")

def test_error_handling():
    """Test 4: Error Handling"""
    print("\n=== Test 4: Error Handling ===")

    config = {'account_id': 'test', 'password': 'test'}
    broker = EastmoneySimulatedBroker(config)

    # Test submit order without login
    order = Order(symbol='600519.SH', side=OrderSide.BUY, quantity=100)
    try:
        broker.submit_order(order)
        assert False, "Should raise BrokerOrderError"
    except BrokerOrderError as e:
        assert "Not logged in" in str(e), "Error message should mention not logged in"
        print(f"[PASS] Correctly reject order when not logged in: {e}")

    # Test get positions without login
    try:
        broker.get_positions()
        assert False, "Should raise error"
    except Exception as e:
        print(f"[PASS] Correctly reject get_positions when not logged in")

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Task 4 Integration Test Suite")
    print("东方财富模拟盘功能测试")
    print("=" * 60)

    try:
        test_broker_basic()
        test_order_validation()
        test_adapter()
        test_error_handling()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
