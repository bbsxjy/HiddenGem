"""
Auto Trading Service

管理自动交易的后台服务，支持多策略并行运行
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import threading
import sys
import os

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from scripts.auto_paper_trading import AutoPaperTrader
from trading.strategy_factory import StrategyFactory, StrategyMode
from trading.multi_strategy_manager import MultiStrategyManager
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.market_context import MarketContext
from api.services.realtime_data_service import realtime_data_service
from api.services.trading_service import trading_service  # 导入trading_service

logger = get_logger("auto_trading_service")


class AutoTradingService:
    """自动交易服务单例，支持多策略并行"""

    def __init__(self):
        self.trader: Optional[AutoPaperTrader] = None
        self.strategy_manager: Optional[MultiStrategyManager] = None
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.thread: Optional[threading.Thread] = None
        self.config: Dict = {}
        self.started_at: Optional[datetime] = None

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.running

    async def start(
        self,
        symbols: List[str],
        initial_cash: float = 100000.0,
        check_interval: int = 5,
        use_multi_agent: bool = True,
        strategy_modes: List[str] = None
    ) -> bool:
        """启动自动交易，支持多策略

        Args:
            symbols: 股票列表
            initial_cash: 初始资金
            check_interval: 检查间隔（分钟）
            use_multi_agent: 是否使用Multi-Agent（已废弃，使用strategy_modes）
            strategy_modes: 策略模式列表
        """
        if self.running:
            logger.warning("🔶 自动交易已在运行中")
            return False

        try:
            # 如果没有指定策略，使用默认策略
            if not strategy_modes or len(strategy_modes) == 0:
                strategy_modes = [StrategyMode.RL_LLM]  # 默认使用RL+LLM
                logger.info(f"📊 未指定策略，使用默认: {strategy_modes}")

            logger.info(f"🚀 启动自动交易...")
            logger.info(f"   股票: {symbols}")
            logger.info(f"   初始资金: ¥{initial_cash:,.2f}")
            logger.info(f"   策略模式: {strategy_modes}")

            # 保存配置
            self.config = {
                "symbols": symbols,
                "initial_cash": initial_cash,
                "check_interval": check_interval,
                "use_multi_agent": use_multi_agent,
                "strategy_modes": strategy_modes
            }
            self.started_at = datetime.now()

            # 创建多个策略
            strategies = StrategyFactory.create_multi_strategies(strategy_modes)

            if not strategies:
                logger.error("❌ 未能创建任何策略")
                return False

            # 创建多策略管理器 - 使用trading_service的broker
            self.strategy_manager = MultiStrategyManager(
                strategies=strategies,
                initial_cash=initial_cash,
                shared_broker=trading_service.broker  # 使用共享broker
            )

            logger.info(f"✅ 多策略管理器已创建，共 {len(strategies)} 个策略")
            logger.info(f"✅ 使用全局trading_service broker，交易记录将同步到交易中心")

            # 在后台线程中运行
            self.running = True
            self.thread = threading.Thread(
                target=self._run_trading_loop,
                daemon=True
            )
            self.thread.start()

            logger.info("✅ 自动交易已启动")
            return True

        except Exception as e:
            logger.error(f"❌ 启动自动交易失败: {e}", exc_info=True)
            self.running = False
            return False

    def _run_trading_loop(self):
        """在后台线程中运行交易循环"""
        try:
            logger.info("🔄 交易循环开始")

            import time
            import pandas as pd
            import numpy as np
            from api.services.realtime_data_service import realtime_data_service

            check_interval_seconds = self.config.get("check_interval", 5) * 60

            while self.running:
                # 检查交易时间
                is_trading, time_status = MarketContext.is_trading_time()

                if not is_trading:
                    logger.info(f"⏸️ 非交易时间（{time_status}），跳过本次检查")
                    time.sleep(60)  # 非交易时间每分钟检查一次
                    continue

                logger.info(f"📊 执行交易检查... ({time_status})")

                # 获取股票列表
                symbols = self.config.get("symbols", [])

                # 获取市场价格和历史数据
                market_prices = {}
                stock_data = {}

                for symbol in symbols:
                    try:
                        # 获取实时价格
                        realtime = realtime_data_service.get_realtime_quote(symbol)
                        if realtime and 'price' in realtime and realtime['price'] > 0:
                            market_prices[symbol] = realtime['price']
                            logger.debug(f"✓ [{symbol}] 实时价格: ¥{realtime['price']:.2f}")
                        else:
                            logger.warning(f"⚠️ [{symbol}] 无法获取实时价格，跳过")
                            continue  # 跳过无法获取价格的股票

                        # 获取历史数据（用于RL策略）
                        # 使用 TradingAgents 的统一数据接口
                        hist_data = None

                        try:
                            from tradingagents.dataflows.interface import get_stock_data_dataframe
                            from datetime import datetime, timedelta
                            end_date = datetime.now().strftime('%Y%m%d')
                            start_date = (datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
                            hist_data = get_stock_data_dataframe(symbol, start_date, end_date)

                            if hist_data is not None and not hist_data.empty:
                                stock_data[symbol] = hist_data
                                logger.info(f"✓ [{symbol}] 获取历史数据成功（{len(hist_data)}行）")
                            else:
                                raise ValueError("返回数据为空")

                        except Exception as e1:
                            logger.warning(f"⚠️ [{symbol}] 真实数据获取失败: {e1}")

                            # 创建足够大的模拟数据（至少50行供技术指标计算）
                            current_price = market_prices[symbol]
                            n_rows = 50
                            stock_data[symbol] = pd.DataFrame({
                                'close': [current_price * (1 + np.random.randn() * 0.02) for _ in range(n_rows)],
                                'high': [current_price * (1 + np.random.rand() * 0.03) for _ in range(n_rows)],
                                'low': [current_price * (1 - np.random.rand() * 0.03) for _ in range(n_rows)],
                                'open': [current_price * (1 + np.random.randn() * 0.01) for _ in range(n_rows)],
                                'volume': [1000000 * (1 + np.random.rand()) for _ in range(n_rows)]
                            })
                            logger.warning(f"⚠️ [{symbol}] 使用模拟历史数据（{n_rows}行）")

                    except Exception as e:
                        logger.error(f"❌ [{symbol}] 获取数据失败: {e}")
                        continue  # 跳过失败的股票

                # 对每个股票生成信号并执行
                for symbol in symbols:
                    current_data = stock_data.get(symbol, pd.DataFrame())
                    current_price = market_prices.get(symbol, 15.0)

                    if current_data.empty:
                        logger.warning(f"⚠️ [{symbol}] 数据为空，跳过")
                        continue

                    # 为所有策略生成信号
                    signals = self.strategy_manager.generate_signals(
                        symbol=symbol,
                        current_data=current_data,
                        market_prices=market_prices
                    )

                    # 执行所有策略的信号
                    self.strategy_manager.execute_signals(
                        symbol=symbol,
                        signals=signals,
                        current_price=current_price,
                        market_prices=market_prices
                    )

                # 保存状态到文件
                try:
                    trading_service.save_state()
                    logger.debug("✓ 交易状态已保存")
                except Exception as e:
                    logger.warning(f"⚠️ 保存状态失败: {e}")

                # 等待下次检查
                logger.info(f"⏱️ 等待 {check_interval_seconds} 秒后进行下次检查...")
                time.sleep(check_interval_seconds)

        except Exception as e:
            logger.error(f"❌ 交易循环异常: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info("⏹️ 交易循环结束")

    async def stop(self) -> bool:
        """停止自动交易"""
        if not self.running:
            logger.warning("自动交易未在运行")
            return False

        try:
            logger.info("停止自动交易")

            # 设置停止标志
            self.running = False
            if self.trader:
                self.trader.running = False

            # 等待线程结束（最多10秒）
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=10)

            logger.info("自动交易已停止")
            return True

        except Exception as e:
            logger.error(f"停止自动交易失败: {e}", exc_info=True)
            return False

    def get_status(self) -> Dict:
        """获取当前状态，包含多策略表现数据"""
        if not self.strategy_manager or not self.running:
            return {
                "is_running": False,
                "started_at": None,
                "current_symbols": [],
                "total_trades": 0,
                "current_cash": 0.0,
                "total_assets": 0.0,
                "profit_loss": 0.0,
                "profit_loss_pct": 0.0,
                "next_check_time": None,
                "is_trading_hours": False,
                "strategy_performances": []
            }

        try:
            # 获取多策略表现数据
            performances = self.strategy_manager.get_performances()

            # 计算总体统计（取所有策略的平均值）
            if performances:
                avg_profit_loss = sum(p['profit_loss'] for p in performances) / len(performances)
                avg_profit_loss_pct = sum(p['profit_loss_pct'] for p in performances) / len(performances)
                total_trades = sum(p['total_trades'] for p in performances)
                avg_cash = sum(p['current_cash'] for p in performances) / len(performances)
                avg_assets = sum(p['current_value'] for p in performances) / len(performances)
            else:
                avg_profit_loss = 0.0
                avg_profit_loss_pct = 0.0
                total_trades = 0
                avg_cash = self.config.get("initial_cash", 100000.0)
                avg_assets = avg_cash

            # 检查交易时间
            is_trading_hours, time_status = MarketContext.is_trading_time()
            next_check_time = None

            return {
                "is_running": self.running,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "current_symbols": self.config.get("symbols", []),
                "total_trades": total_trades,
                "current_cash": avg_cash,
                "total_assets": avg_assets,
                "profit_loss": avg_profit_loss,
                "profit_loss_pct": avg_profit_loss_pct,
                "next_check_time": next_check_time,
                "is_trading_hours": is_trading_hours,
                "strategy_performances": performances,  # 多策略表现数据
                "num_strategies": len(performances)
            }

        except Exception as e:
            logger.error(f"❌ 获取状态失败: {e}", exc_info=True)
            return self._get_initializing_status()

    def _get_initializing_status(self) -> Dict:
        """返回初始化中的状态"""
        # 尝试获取交易时段状态
        is_trading_hours = False
        next_check_time = None
        if self.trader and hasattr(self.trader, 'is_trading_hours'):
            try:
                is_trading_hours = self.trader.is_trading_hours()
                if not is_trading_hours and hasattr(self.trader, 'get_next_trading_time'):
                    next_session = self.trader.get_next_trading_time()
                    if next_session:
                        next_check_time = next_session.isoformat()
            except Exception as e:
                logger.debug(f"Could not get trading hours status: {e}")

        return {
            "is_running": self.running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "current_symbols": self.config.get("symbols", []),
            "total_trades": 0,
            "current_cash": self.config.get("initial_cash", 100000.0),
            "total_assets": self.config.get("initial_cash", 100000.0),
            "profit_loss": 0.0,
            "profit_loss_pct": 0.0,
            "next_check_time": next_check_time,
            "is_trading_hours": is_trading_hours
        }

    def get_config(self) -> Dict:
        """获取当前配置"""
        return self.config.copy()

    def get_performance(self) -> Dict:
        """获取交易表现"""
        if not self.trader or not self.running:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "total_loss": 0.0,
                "average_profit": 0.0,
                "average_loss": 0.0,
                "largest_profit": 0.0,
                "largest_loss": 0.0
            }

        broker = self.trader.broker
        orders = broker.orders

        # 统计已成交订单
        filled_orders = [o for o in orders if o.status.value == "FILLED"]

        # 计算盈亏（简化版本）
        total_profit = 0.0
        total_loss = 0.0
        winning_trades = 0
        losing_trades = 0

        # 这里需要更复杂的逻辑来计算每笔交易的盈亏
        # 暂时返回基本统计

        return {
            "total_trades": len(filled_orders),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": (winning_trades / len(filled_orders) * 100) if filled_orders else 0.0,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "average_profit": (total_profit / winning_trades) if winning_trades > 0 else 0.0,
            "average_loss": (total_loss / losing_trades) if losing_trades > 0 else 0.0,
            "largest_profit": 0.0,
            "largest_loss": 0.0
        }

    def get_stock_decisions(self) -> List[Dict]:
        """
        获取实时股票决策状态

        Returns:
            股票决策列表
        """
        if not self.trader or not self.running:
            return []

        symbols = self.config.get("symbols", [])
        decisions = []

        # 获取实时行情数据
        quotes = realtime_data_service.get_batch_quotes(symbols)

        for symbol in symbols:
            quote = quotes.get(symbol)

            if quote:
                # 有实时数据
                # TODO: 从 RL 策略或 Multi-Agent 获取真实决策
                # 目前根据涨跌幅简单判断
                change = quote.get('change', 0)
                price = quote.get('price', 0)

                if change > 2:
                    decision = 'buy'
                    reason = f"涨幅{change:.2f}%，技术面强势"
                    confidence = min(0.6 + change / 20, 0.9)
                elif change < -2:
                    decision = 'sell'
                    reason = f"跌幅{abs(change):.2f}%，技术面转弱"
                    confidence = min(0.6 + abs(change) / 20, 0.9)
                else:
                    decision = 'hold'
                    reason = f"涨跌幅{change:.2f}%，震荡整理"
                    confidence = 0.5

                decisions.append({
                    "symbol": symbol,
                    "name": quote.get('name', symbol),
                    "last_check": datetime.now().isoformat(),
                    "decision": decision,
                    "reason": reason,
                    "price": price,
                    "change": change,
                    "volume": quote.get('volume', 0),
                    "confidence": confidence,
                    "suggested_quantity": self._calculate_quantity(price, decision),
                })
            else:
                # 无实时数据
                decisions.append({
                    "symbol": symbol,
                    "name": symbol,
                    "last_check": datetime.now().isoformat(),
                    "decision": 'hold',
                    "reason": "等待实时行情数据",
                    "confidence": 0.3,
                })

        return decisions

    def _calculate_quantity(self, price: float, decision: str) -> Optional[int]:
        """
        计算建议交易数量

        Args:
            price: 当前价格
            decision: 决策类型

        Returns:
            建议数量（100的倍数）
        """
        if decision == 'hold' or price <= 0:
            return None

        # 获取当前现金
        initial_cash = self.config.get("initial_cash", 100000.0)

        # 最大单个仓位10%
        max_position_value = initial_cash * 0.1

        # 计算数量（取整到100的倍数）
        quantity = int(max_position_value / price / 100) * 100

        return max(100, quantity)  # 至少100股


# 创建全局单例
auto_trading_service = AutoTradingService()

