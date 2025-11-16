"""
Strategy Base Class

策略基类 - 定义策略接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import pandas as pd


class BaseStrategy(ABC):
    """策略基类

    所有策略（RL策略、规则策略等）都应继承此类
    """

    def __init__(self, name: str = "BaseStrategy"):
        """初始化策略

        Args:
            name: 策略名称
        """
        self.name = name

    @abstractmethod
    def generate_signal(
        self,
        symbol: str,
        current_data: pd.DataFrame,
        portfolio_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成交易信号

        Args:
            symbol: 股票代码
            current_data: 当前数据（包含历史数据）
            portfolio_state: 当前投资组合状态

        Returns:
            交易信号字典：
            {
                'action': 'buy' | 'sell' | 'hold',
                'quantity': int,  # 交易数量（可选）
                'price': float,   # 目标价格（可选，用于限价单）
                'reason': str     # 交易原因（可选）
            }
        """
        pass

    @abstractmethod
    def on_trade(self, trade_info: Dict[str, Any]):
        """交易执行后的回调

        Args:
            trade_info: 交易信息
        """
        pass

    def reset(self):
        """重置策略状态（用于回测）"""
        pass


class BuyAndHoldStrategy(BaseStrategy):
    """买入持有策略（基准策略）"""

    def __init__(self):
        super().__init__("BuyAndHold")
        self.has_bought = False

    def generate_signal(
        self,
        symbol: str,
        current_data: pd.DataFrame,
        portfolio_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成信号：第一天买入，之后一直持有"""
        # 如果还没买入，则买入
        if not self.has_bought:
            return {
                'action': 'buy',
                'reason': 'Initial buy for buy-and-hold'
            }
        else:
            return {
                'action': 'hold',
                'reason': 'Holding position'
            }

    def on_trade(self, trade_info: Dict[str, Any]):
        """记录买入状态"""
        if trade_info.get('side') == 'buy':
            self.has_bought = True

    def reset(self):
        """重置状态"""
        self.has_bought = False
