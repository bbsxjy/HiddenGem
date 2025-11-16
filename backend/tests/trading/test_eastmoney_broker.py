"""
Unit tests for Eastmoney Simulated Broker

测试东方财富模拟盘券商接口
"""

import pytest
from datetime import datetime
from trading.eastmoney_sim_broker import EastmoneySimulatedBroker
from trading.adapters.eastmoney_adapter import EastmoneyAdapter
from trading.order import Order, OrderSide, OrderType, OrderStatus
from trading.position import Position


class TestEastmoneySimulatedBroker:
    """测试EastmoneySimulatedBroker类"""

    @pytest.fixture
    def broker_config(self):
        """测试配置"""
        return {
            'account_id': 'test_account',
            'password': 'test_password',
            'initial_capital': 1000000
        }

    @pytest.fixture
    def broker(self, broker_config):
        """创建broker实例"""
        return EastmoneySimulatedBroker(broker_config)

    def test_broker_initialization(self, broker, broker_config):
        """测试broker初始化"""
        assert broker.account_config == broker_config
        assert not broker.is_logged_in
        assert broker.token is None
        assert broker.user_id is None

    def test_login(self, broker):
        """测试登录功能"""
        # 注意：当前使用模拟登录
        result = broker.login()

        assert result is True
        assert broker.is_logged_in
        assert broker.token is not None
        assert broker.user_id is not None

    def test_logout(self, broker):
        """测试登出功能"""
        # 先登录
        broker.login()
        assert broker.is_logged_in

        # 登出
        result = broker.logout()
        assert result is True
        assert not broker.is_logged_in
        assert broker.token is None

    def test_submit_order_without_login(self, broker):
        """测试未登录时提交订单应该失败"""
        from trading.base_broker import BrokerOrderError

        order = Order(
            symbol='600519.SH',
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )

        with pytest.raises(BrokerOrderError, match="Not logged in"):
            broker.submit_order(order)

    def test_submit_order(self, broker):
        """测试提交订单"""
        broker.login()

        order = Order(
            symbol='600519.SH',
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )

        result = broker.submit_order(order)

        assert result['success'] is True
        assert 'broker_order_id' in result
        assert 'timestamp' in result

    def test_validate_order_invalid_quantity(self, broker):
        """测试订单验证 - 无效数量"""
        # 数量为0
        order = Order(
            symbol='600519.SH',
            side=OrderSide.BUY,
            quantity=0,
            order_type=OrderType.MARKET
        )
        valid, error_msg = broker.validate_order(order)
        assert not valid
        assert "必须大于0" in error_msg

        # 数量不是100的整数倍
        order.quantity = 150
        valid, error_msg = broker.validate_order(order)
        assert not valid
        assert "100股的整数倍" in error_msg

    def test_validate_order_valid(self, broker):
        """测试订单验证 - 有效订单"""
        order = Order(
            symbol='600519.SH',
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        valid, error_msg = broker.validate_order(order)
        assert valid
        assert error_msg == ""

    def test_get_balance(self, broker):
        """测试获取资金信息"""
        broker.login()

        balance = broker.get_balance()

        assert 'total_assets' in balance
        assert 'available_cash' in balance
        assert balance['total_assets'] == 1000000  # 初始资金

    def test_get_positions(self, broker):
        """测试获取持仓"""
        broker.login()

        positions = broker.get_positions()

        assert isinstance(positions, list)
        # 初始持仓应该为空
        assert len(positions) == 0

    def test_get_orders(self, broker):
        """测试获取订单列表"""
        broker.login()

        orders = broker.get_orders()

        assert isinstance(orders, list)

    def test_cancel_order(self, broker):
        """测试撤单"""
        broker.login()

        # 先提交一个订单
        order = Order(
            symbol='600519.SH',
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=1500.0
        )
        submit_result = broker.submit_order(order)
        broker_order_id = submit_result['broker_order_id']

        # 撤单
        cancel_result = broker.cancel_order(broker_order_id)

        assert cancel_result['success'] is True


class TestEastmoneyAdapter:
    """测试EastmoneyAdapter类"""

    def test_adapt_order_to_broker(self):
        """测试转换Order到券商格式"""
        order = Order(
            symbol='600519.SH',
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )

        broker_order = EastmoneyAdapter.adapt_order_to_broker(order)

        assert broker_order['symbol'] == '600519.SH'
        assert broker_order['side'] == 'buy'
        assert broker_order['quantity'] == 100
        assert broker_order['order_type'] == 'market'

    def test_adapt_order_from_broker(self):
        """测试从券商格式转换Order"""
        broker_order = {
            'order_id': 'TEST001',
            'symbol': '600519.SH',
            'side': 'buy',
            'quantity': 100,
            'order_type': 'market',
            'status': 'filled',
            'filled_quantity': 100,
            'filled_price': 1500.0,
            'commission': 5.0
        }

        order = EastmoneyAdapter.adapt_order_from_broker(broker_order)

        assert order.symbol == '600519.SH'
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        assert order.status == OrderStatus.FILLED

    def test_adapt_position_from_broker(self):
        """测试从券商格式转换Position"""
        broker_position = {
            'symbol': '600519.SH',
            'quantity': 100,
            'avg_price': 1500.0,
            'current_price': 1550.0
        }

        position = EastmoneyAdapter.adapt_position_from_broker(broker_position)

        assert position.symbol == '600519.SH'
        assert position.quantity == 100
        assert position.avg_price == 1500.0
        assert position.current_price == 1550.0

    def test_adapt_position_to_broker(self):
        """测试转换Position到券商格式"""
        position = Position(
            symbol='600519.SH',
            quantity=100,
            avg_price=1500.0,
            current_price=1550.0
        )

        broker_position = EastmoneyAdapter.adapt_position_to_broker(position)

        assert broker_position['symbol'] == '600519.SH'
        assert broker_position['quantity'] == 100
        assert broker_position['market_value'] == 155000.0  # 100 * 1550

    def test_batch_adapt_positions(self):
        """测试批量转换持仓"""
        broker_positions = [
            {
                'symbol': '600519.SH',
                'quantity': 100,
                'avg_price': 1500.0,
                'current_price': 1550.0
            },
            {
                'symbol': '000001.SZ',
                'quantity': 200,
                'avg_price': 15.0,
                'current_price': 16.0
            }
        ]

        positions = EastmoneyAdapter.batch_adapt_positions(broker_positions)

        assert len(positions) == 2
        assert isinstance(positions[0], Position)
        assert positions[0].symbol == '600519.SH'
        assert positions[1].symbol == '000001.SZ'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
