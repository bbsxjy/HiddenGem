"""
Trading Service

全局交易服务，管理模拟交易引擎和投资组合
"""

from typing import Optional
from trading.simulated_broker import SimulatedBroker
import json
import os
from datetime import datetime


class TradingService:
    """交易服务单例"""

    _instance: Optional['TradingService'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # 初始化交易组件 - 使用 SimulatedBroker
            self.initial_capital = 100000.0  # 初始资金10万
            self.broker = SimulatedBroker(
                initial_cash=self.initial_capital,
                commission_rate=0.0001,  # 万1佣金
                stamp_duty_rate=0.001,    # 千1印花税
                min_commission=5.0
            )

            # 存储策略配置
            self.strategies = {}

            # 尝试从文件恢复状态
            self._load_state()

            TradingService._initialized = True

    def _load_state(self):
        """从文件恢复broker状态"""
        state_file = "trading_state.json"
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                # 恢复现金
                self.broker.cash = state.get('cash', self.initial_capital)
                self.broker.initial_cash = state.get('initial_cash', self.initial_capital)

                # TODO: 恢复持仓
                # 需要Position类支持从dict恢复

                print(f"✅ 已从文件恢复交易状态 (现金: ¥{self.broker.cash:,.2f})")
            except Exception as e:
                print(f"⚠️ 恢复交易状态失败: {e}")

    def save_state(self):
        """保存broker状态到文件"""
        state_file = "trading_state.json"
        try:
            state = {
                'cash': self.broker.cash,
                'initial_cash': self.broker.initial_cash,
                'saved_at': datetime.now().isoformat(),
                # TODO: 保存持仓
            }

            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            print(f"✅ 交易状态已保存")
        except Exception as e:
            print(f"⚠️ 保存交易状态失败: {e}")

    def reset(self):
        """重置broker到初始状态"""
        self.broker.reset()
        # 删除状态文件
        state_file = "trading_state.json"
        if os.path.exists(state_file):
            os.remove(state_file)
        print(f"✅ 交易状态已重置")

    def get_portfolio_summary(self) -> dict:
        """获取投资组合摘要"""
        balance = self.broker.get_balance()
        return {
            "total_value": balance['total_assets'],
            "cash": balance['cash'],
            "positions_value": balance['market_value'],
            "total_pnl": balance['profit'],
            "total_pnl_percent": balance['profit_pct'] * 100,
            "daily_pnl": 0.0,  # TODO: 需要从历史记录计算
            "daily_pnl_percent": 0.0
        }

    def get_positions(self) -> list:
        """获取当前所有持仓"""
        # 将broker的Position对象转换为前端期望的格式
        positions = []
        for symbol, position in self.broker.positions.items():
            positions.append({
                "symbol": symbol,
                "name": symbol.split('.')[0],  # 简化处理，取代码部分作为名称
                "quantity": position.quantity,
                "avg_cost": position.avg_cost,
                "current_price": position.current_price if position.current_price else position.avg_price,  # 如果没有当前价，使用成本价
                "market_value": position.market_value,
                "cost_basis": position.cost_basis,
                "unrealized_pnl": position.unrealized_pnl,
                "unrealized_pnl_pct": position.unrealized_pnl_pct,
                "today_pnl": 0.0,  # TODO: 需要从历史记录计算
                "today_pnl_pct": 0.0
            })
        return positions

    def get_position(self, symbol: str) -> Optional[dict]:
        """获取单个持仓"""
        if symbol not in self.broker.positions:
            return None

        position = self.broker.positions[symbol]
        return {
            "symbol": symbol,
            "name": symbol.split('.')[0],
            "quantity": position.quantity,
            "avg_cost": position.avg_cost,
            "current_price": position.current_price,
            "market_value": position.market_value,
            "cost_basis": position.cost_basis,
            "unrealized_pnl": position.unrealized_pnl,
            "unrealized_pnl_pct": position.unrealized_pnl_pct,
            "today_pnl": 0.0,
            "today_pnl_pct": 0.0
        }

    def get_portfolio_history(self, days: int = 30) -> list:
        """获取投资组合历史"""
        # TODO: 实现equity_history
        return []

    def get_orders(self, status: Optional[str] = None) -> list:
        """获取订单列表"""
        from trading.order import OrderStatus

        # 使用broker的订单列表
        orders = []
        order_id_counter = 1000

        for order in self.broker.orders:
            # 过滤状态
            if status and order.status.value != status:
                continue

            orders.append({
                "id": order_id_counter,  # 前端期望 id 而不是 order_id
                "symbol": order.symbol,
                "name": order.symbol.split('.')[0],
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "price": order.limit_price,
                "filled_quantity": order.filled_quantity,
                "avg_filled_price": order.filled_price if order.filled_quantity > 0 else None,
                "status": order.status.value,
                "created_at": order.created_time.isoformat() if order.created_time else datetime.now().isoformat(),
                "updated_at": (order.filled_time or order.created_time or datetime.now()).isoformat(),
                "strategy_name": order.strategy_name,  # 策略名称
                "reasoning": order.reasoning  # 交易原因
            })
            order_id_counter += 1

        return orders

    def get_order(self, order_id: int) -> Optional[dict]:
        """获取单个订单"""
        index = order_id - 1000

        if 0 <= index < len(self.broker.orders):
            order = self.broker.orders[index]
            return {
                "id": order_id,  # 前端期望 id 而不是 order_id
                "symbol": order.symbol,
                "name": order.symbol.split('.')[0],
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "price": order.limit_price,
                "filled_quantity": order.filled_quantity,
                "avg_filled_price": order.filled_price if order.filled_quantity > 0 else None,
                "status": order.status.value,
                "created_at": (order.created_time or datetime.now()).isoformat(),
                "updated_at": (order.filled_time or order.created_time or datetime.now()).isoformat(),
                "strategy_name": order.strategy_name,  # 策略名称
                "reasoning": order.reasoning  # 交易原因
            }
        return None

    def create_order(self, order_data: dict) -> dict:
        """创建订单"""
        from trading.order import Order, OrderSide, OrderType

        # 解析订单参数
        symbol = order_data.get("symbol")
        side = OrderSide.BUY if order_data.get("side") == "buy" else OrderSide.SELL
        quantity = order_data.get("quantity")
        order_type = OrderType.LIMIT if order_data.get("order_type") == "limit" else OrderType.MARKET
        limit_price = order_data.get("price")
        strategy_name = order_data.get("strategy_name")  # 策略名称
        reasoning = order_data.get("reasoning")  # 交易原因

        # 创建订单对象
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            strategy_name=strategy_name,
            reasoning=reasoning
        )

        # 提交到broker
        self.broker.submit_order(order)

        # 如果是市价单，立即执行
        if order_type == OrderType.MARKET:
            current_price = order_data.get("current_price", limit_price)
            if current_price:
                self.broker.execute_market_order(order, current_price)

        # 保存状态
        self.save_state()

        # 生成数字ID
        order_id = 1000 + len(self.broker.orders) - 1

        return {
            "id": order_id,  # 前端期望 id 而不是 order_id
            "symbol": order.symbol,
            "name": order.symbol.split('.')[0],
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": order.quantity,
            "price": order.limit_price,
            "filled_quantity": order.filled_quantity or 0,
            "avg_filled_price": order.filled_price,
            "status": order.status.value,
            "created_at": (order.created_time or datetime.now()).isoformat(),
            "updated_at": (order.created_time or datetime.now()).isoformat(),
            "strategy_name": order.strategy_name,  # 策略名称
            "reasoning": order.reasoning  # 交易原因
        }

    def cancel_order(self, order_id: int) -> bool:
        """取消订单"""
        index = order_id - 1000

        if 0 <= index < len(self.broker.orders):
            order_id_str = self.broker.orders[index].order_id
            return self.broker.cancel_order(order_id_str)
        return False


# 全局单例
trading_service = TradingService()
