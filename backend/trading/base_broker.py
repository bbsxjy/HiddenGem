"""
Base Broker Interface

券商接口抽象基类 - 定义统一的券商操作接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from .order import Order, OrderStatus


class BaseBroker(ABC):
    """券商接口抽象基类

    所有券商实现（模拟盘、真实盘）都应继承此类
    """

    def __init__(self, account_config: dict):
        """初始化券商接口

        Args:
            account_config: 账号配置字典
                {
                    'account_id': '账号',
                    'password': '密码',
                    'trade_password': '交易密码（可选）',
                    ...
                }
        """
        self.account_config = account_config
        self.is_logged_in = False

    @abstractmethod
    def login(self) -> bool:
        """登录券商

        Returns:
            是否登录成功

        Raises:
            BrokerLoginError: 登录失败
        """
        pass

    @abstractmethod
    def logout(self) -> bool:
        """登出券商

        Returns:
            是否登出成功
        """
        pass

    @abstractmethod
    def submit_order(self, order: Order) -> dict:
        """提交订单

        Args:
            order: 订单对象

        Returns:
            订单提交结果
            {
                'success': True/False,
                'broker_order_id': '券商订单ID',
                'message': '提示信息',
                'timestamp': '提交时间'
            }

        Raises:
            BrokerOrderError: 订单提交失败
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> dict:
        """撤销订单

        Args:
            order_id: 订单ID（内部ID或券商ID）

        Returns:
            撤单结果
            {
                'success': True/False,
                'message': '提示信息'
            }

        Raises:
            BrokerOrderError: 撤单失败
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[dict]:
        """获取持仓列表

        Returns:
            持仓列表
            [
                {
                    'symbol': '股票代码',
                    'quantity': 持仓数量,
                    'avg_price': 持仓均价,
                    'current_price': 当前价格,
                    'market_value': 市值,
                    'unrealized_pnl': 浮动盈亏,
                    ...
                }
            ]
        """
        pass

    @abstractmethod
    def get_balance(self) -> dict:
        """获取资金信息

        Returns:
            资金信息
            {
                'total_assets': 总资产,
                'available_cash': 可用资金,
                'frozen_cash': 冻结资金,
                'market_value': 持仓市值,
                ...
            }
        """
        pass

    @abstractmethod
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[dict]:
        """获取订单列表

        Args:
            status: 订单状态过滤（None表示获取所有订单）

        Returns:
            订单列表
            [
                {
                    'order_id': '订单ID',
                    'symbol': '股票代码',
                    'side': 'buy/sell',
                    'quantity': 数量,
                    'price': 价格,
                    'status': 'pending/filled/cancelled',
                    ...
                }
            ]
        """
        pass

    def validate_order(self, order: Order) -> tuple[bool, str]:
        """验证订单是否合法

        Args:
            order: 订单对象

        Returns:
            (是否合法, 错误信息)
        """
        # 基础验证
        if order.quantity <= 0:
            return False, "订单数量必须大于0"

        if order.quantity % 100 != 0:
            return False, "A股订单必须是100股的整数倍"

        # 子类可以重写此方法添加更多验证
        return True, ""


class BrokerError(Exception):
    """券商操作异常基类"""
    pass


class BrokerLoginError(BrokerError):
    """登录异常"""
    pass


class BrokerOrderError(BrokerError):
    """订单操作异常"""
    pass


class BrokerConnectionError(BrokerError):
    """连接异常"""
    pass
