"""
QF-Lib Backtest Runner (Updated for QF-Lib 4.0.4)

使用 QF-Lib 4.0.4 的 AlphaModel 接口进行回测
"""

from datetime import datetime
from typing import Dict, List, Optional
import logging
import pandas as pd
import numpy as np

# QF-Lib imports for version 4.0.4
try:
    from qf_lib.data_providers.data_provider import DataProvider
    from qf_lib.backtesting.alpha_model.alpha_model import AlphaModel
    from qf_lib.backtesting.alpha_model.exposure_enum import Exposure
    from qf_lib.common.tickers.tickers import Ticker
    from qf_lib.common.utils.dateutils.timer import SettableTimer
    from qf_lib.common.enums.frequency import Frequency
    QF_LIB_AVAILABLE = True
except ImportError as e:
    logging.warning(f"QF-Lib import failed: {e}")
    DataProvider = None
    AlphaModel = None
    Exposure = None
    Ticker = str
    SettableTimer = None
    Frequency = None
    QF_LIB_AVAILABLE = False

from .tushare_data_provider import TushareDataProvider
from .rl_strategy_adapter import RLStrategyAdapter

logger = logging.getLogger(__name__)


class QFLibBacktestRunner:
    """QF-Lib回测运行器（基于QF-Lib 4.0.4）

    使用QF-Lib数据接口进行回测，RL模型生成交易信号。
    由于 BacktestTradingSessionBuilder 在 Windows 上需要额外的 GTK 依赖，
    这里使用简化的回测逻辑，直接模拟交易。

    Features:
        -  使用 RL 模型生成交易信号
        -  QF-Lib 数据接口（防止Look-Ahead Bias）
        -  A股数据支持（通过 Tushare）
        -  详细的性能指标和交易记录
    """

    def __init__(
        self,
        model_path: str,
        tushare_token: str,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 1000000.0,
        commission_rate: float = 0.0003
    ):
        """初始化回测运行器

        Args:
            model_path: RL模型路径
            tushare_token: Tushare API Token
            symbols: 股票代码列表
            start_date: 回测开始日期
            end_date: 回测结束日期
            initial_capital: 初始资金
            commission_rate: 手续费率
        """
        if not QF_LIB_AVAILABLE:
            raise ImportError(
                "QF-Lib not properly installed. Core components missing."
            )

        self.model_path = model_path
        self.tushare_token = tushare_token
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate

        logger.info(f" QFLibBacktestRunner initialized: {len(symbols)} symbols")

    def run(self) -> Dict:
        """运行简化回测

        Returns:
            回测结果字典
        """
        logger.info(" Starting simplified backtest...")

        # 1. 初始化数据提供者
        data_provider = TushareDataProvider(self.tushare_token)

        # 2. 直接使用股票代码字符串（不需要 Ticker 对象）
        tickers = self.symbols  # 使用字符串列表，不使用 QF-Lib Ticker

        # 3. 加载 RL 模型（不使用完整的 AlphaModel 架构）
        try:
            from stable_baselines3 import PPO
            self.rl_model = PPO.load(self.model_path)
            logger.info(f" RL model loaded from {self.model_path}")
        except Exception as e:
            logger.error(f" Failed to load RL model: {e}")
            raise

        # 4. 运行简化回测逻辑
        results = self._run_simple_backtest(data_provider, tickers)

        logger.info(" Backtest completed")
        return results

    def _run_simple_backtest(
        self,
        data_provider: DataProvider,
        tickers: List[Ticker]
    ) -> Dict:
        """运行简化的回测逻辑

        Args:
            data_provider: 数据提供者
            tickers: 股票列表

        Returns:
            回测结果
        """
        logger.info(" Running QF-Lib backtest with RL model signals...")

        # 初始化
        cash = self.initial_capital
        positions = {ticker: 0 for ticker in tickers}  # 持仓数量
        equity_curve = []
        trades = []

        # 获取所有股票的历史数据
        all_data = {}
        for ticker in tickers:
            try:
                df = data_provider.get_price(
                    ticker,
                    fields=['open', 'high', 'low', 'close', 'volume'],
                    start_date=self.start_date,
                    end_date=self.end_date
                )
                if df is not None and len(df) > 0:
                    all_data[ticker] = df
                    logger.info(f"   Loaded {len(df)} bars for {ticker}")
            except Exception as e:
                logger.warning(f"   Failed to load data for {ticker}: {e}")

        if not all_data:
            raise ValueError("No data loaded for any symbols")

        # 获取所有日期的并集
        all_dates = sorted(set().union(*[df.index for df in all_data.values()]))
        logger.info(f" Backtesting {len(all_dates)} trading days")

        # 动作统计（用于调试）
        # EnhancedTradingEnv: 0=HOLD, 1=BUY_25, 2=BUY_50, 3=SELL_50, 4=SELL_ALL
        action_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

        # 逐日回测
        for current_date in all_dates:
            try:
                # 获取当日数据
                current_prices = {}
                for ticker, df in all_data.items():
                    if current_date in df.index:
                        current_prices[ticker] = df.loc[current_date, 'close']

                if not current_prices:
                    continue

                # 计算当前总资产
                portfolio_value = cash
                for ticker, shares in positions.items():
                    if shares > 0 and ticker in current_prices:
                        portfolio_value += shares * current_prices[ticker]

                equity_curve.append({
                    'date': current_date.strftime('%Y-%m-%d'),  # 转换为字符串格式
                    'portfolio_value': portfolio_value,
                    'cash': cash
                })

                # ===== 生成交易信号（使用 RL 模型） =====
                for ticker in tickers:
                    if ticker not in current_prices:
                        continue

                    try:
                        # 准备 RL 模型的观察（使用历史数据 + 真实账户状态）
                        obs = self._prepare_observation(
                            all_data[ticker],
                            current_date,
                            cash=cash,
                            portfolio_value=portfolio_value,
                            current_position=positions[ticker],
                            current_price=current_prices[ticker]
                        )
                        if obs is None:
                            continue

                        # 🔍 DEBUG: Log observation details (first day only)
                        if action_counts[0] + action_counts[1] + action_counts[2] + action_counts[3] + action_counts[4] == 0:
                            logger.info(f"🔍 [DEBUG] First Observation Details:")
                            logger.info(f"   Cash: ¥{cash:,.2f}, Portfolio: ¥{portfolio_value:,.2f}, Position: {positions[ticker]} shares")
                            logger.info(f"   Account Features: cash_ratio={obs[10]:.3f}, position_ratio={obs[11]:.3f}, pnl={obs[12]:.3f}")
                            logger.info(f"   Full Observation (14 features): {obs}")

                        # RL 模型预测动作
                        action, _ = self.rl_model.predict(obs, deterministic=True)
                        original_action = int(action)

                        # 获取当前持仓
                        current_position = positions[ticker]

                        # 🛡️ Action Masking: 防止模型采取无效动作
                        if current_position == 0:
                            # 没有持仓，不能卖出
                            if action == 3 or action == 4:  # SELL_50 or SELL_ALL
                                action = 0  # 强制改为 HOLD
                                logger.debug(f"🛡️ [ACTION MASK] Changed {original_action} -> 0 (HOLD): No position to sell")

                        if cash < portfolio_value * 0.10:  # 现金不足10%
                            # 现金不足，不能买入
                            if action == 1 or action == 2:  # BUY_25 or BUY_50
                                action = 0  # 强制改为 HOLD
                                logger.debug(f"🛡️ [ACTION MASK] Changed {original_action} -> 0 (HOLD): Insufficient cash")

                        # 统计动作（用于调试）
                        action_counts[int(action)] += 1

                        # 🔍 DEBUG: Log action prediction (first 3 actions only)
                        if action_counts[0] + action_counts[1] + action_counts[2] + action_counts[3] + action_counts[4] <= 3:
                            if original_action != action:
                                logger.info(f"🔍 [DEBUG] Model predicted action={original_action} -> MASKED to {int(action)} on {current_date.date()} | Cash: ¥{cash:,.0f}, Position: {positions[ticker]} shares")
                            else:
                                logger.info(f"🔍 [DEBUG] Model predicted action={int(action)} on {current_date.date()} | Cash: ¥{cash:,.0f}, Position: {positions[ticker]} shares")

                        # 转换动作为交易信号
                        # EnhancedTradingEnv: 0=HOLD, 1=BUY_25, 2=BUY_50, 3=SELL_50, 4=SELL_ALL
                        current_price = current_prices[ticker]
                        current_position = positions[ticker]

                        # 根据信号决定交易动作
                        if action == 1:  # BUY_25 - 用25%资金买入
                            if current_position == 0:  # 只在没有持仓时买入
                                position_size = 0.25  # 25% 资金买入
                                max_investment = portfolio_value * position_size
                                shares_to_buy = int(max_investment / current_price / 100) * 100  # A股100股为1手

                                if shares_to_buy > 0:
                                    cost = shares_to_buy * current_price
                                    commission = max(cost * self.commission_rate, 5.0)  # 最低5元
                                    total_cost = cost + commission

                                    if total_cost <= cash:
                                        # 执行买入
                                        cash -= total_cost
                                        positions[ticker] += shares_to_buy

                                        trades.append({
                                            'date': current_date.strftime('%Y-%m-%d'),
                                            'ticker': str(ticker),
                                            'action': 'BUY_25',
                                            'shares': shares_to_buy,
                                            'price': current_price,
                                            'cost': cost,
                                            'commission': commission,
                                            'total_cost': total_cost
                                        })

                                        logger.info(f"✅ BUY_25: {ticker} | {shares_to_buy} shares @ ¥{current_price:.2f} | Cost: ¥{total_cost:,.2f}")

                        elif action == 2:  # BUY_50 - 用50%资金买入
                            if current_position == 0:  # 只在没有持仓时买入
                                position_size = 0.50  # 50% 资金买入
                                max_investment = portfolio_value * position_size
                                shares_to_buy = int(max_investment / current_price / 100) * 100  # A股100股为1手

                                if shares_to_buy > 0:
                                    cost = shares_to_buy * current_price
                                    commission = max(cost * self.commission_rate, 5.0)  # 最低5元
                                    total_cost = cost + commission

                                    if total_cost <= cash:
                                        # 执行买入
                                        cash -= total_cost
                                        positions[ticker] += shares_to_buy

                                        trades.append({
                                            'date': current_date.strftime('%Y-%m-%d'),
                                            'ticker': str(ticker),
                                            'action': 'BUY_50',
                                            'shares': shares_to_buy,
                                            'price': current_price,
                                            'cost': cost,
                                            'commission': commission,
                                            'total_cost': total_cost
                                        })

                                        logger.info(f"✅ BUY_50: {ticker} | {shares_to_buy} shares @ ¥{current_price:.2f} | Cost: ¥{total_cost:,.2f}")

                        elif action == 3 and current_position > 0:  # SELL_50 - 卖出50%持仓
                            shares_to_sell = int(current_position * 0.5 / 100) * 100  # 卖出50%，取整到手
                            if shares_to_sell > 0:
                                revenue = shares_to_sell * current_price
                                commission = max(revenue * self.commission_rate, 5.0)
                                stamp_tax = revenue * 0.001  # A股印花税 0.1%
                                total_revenue = revenue - commission - stamp_tax

                                # 执行卖出
                                cash += total_revenue
                                positions[ticker] -= shares_to_sell

                                trades.append({
                                    'date': current_date.strftime('%Y-%m-%d'),
                                    'ticker': str(ticker),
                                    'action': 'SELL_50',
                                    'shares': shares_to_sell,
                                    'price': current_price,
                                    'revenue': revenue,
                                    'commission': commission,
                                    'stamp_tax': stamp_tax,
                                    'total_revenue': total_revenue
                                })

                                logger.info(f"📤 SELL_50: {ticker} | {shares_to_sell} shares @ ¥{current_price:.2f} | Revenue: ¥{total_revenue:,.2f}")

                        elif action == 4 and current_position > 0:  # SELL_ALL - 全部卖出
                            shares_to_sell = current_position
                            revenue = shares_to_sell * current_price
                            commission = max(revenue * self.commission_rate, 5.0)
                            stamp_tax = revenue * 0.001  # A股印花税 0.1%
                            total_revenue = revenue - commission - stamp_tax

                            # 执行卖出
                            cash += total_revenue
                            positions[ticker] = 0

                            trades.append({
                                'date': current_date.strftime('%Y-%m-%d'),
                                'ticker': str(ticker),
                                'action': 'SELL_ALL',
                                'shares': shares_to_sell,
                                'price': current_price,
                                'revenue': revenue,
                                'commission': commission,
                                'stamp_tax': stamp_tax,
                                'total_revenue': total_revenue
                            })

                            logger.info(f"📤 SELL_ALL: {ticker} | {shares_to_sell} shares @ ¥{current_price:.2f} | Revenue: ¥{total_revenue:,.2f}")

                        # action == 0 (HOLD) 不执行任何操作

                    except Exception as e:
                        logger.error(f"Error generating signal for {ticker} on {current_date}: {e}", exc_info=True)
                        continue

            except Exception as e:
                logger.warning(f"Error on {current_date}: {e}")
                continue

        # 计算性能指标
        equity_df = pd.DataFrame(equity_curve)
        if len(equity_df) == 0:
            raise ValueError("No equity curve data generated")

        # 输出动作统计（调试）
        logger.info(f"📊 Action Statistics:")
        total_actions = sum(action_counts.values())
        if total_actions > 0:
            logger.info(f"   HOLD:     {action_counts[0]} ({action_counts[0]/total_actions*100:.1f}%)")
            logger.info(f"   BUY_25:   {action_counts[1]} ({action_counts[1]/total_actions*100:.1f}%)")
            logger.info(f"   BUY_50:   {action_counts[2]} ({action_counts[2]/total_actions*100:.1f}%)")
            logger.info(f"   SELL_50:  {action_counts[3]} ({action_counts[3]/total_actions*100:.1f}%)")
            logger.info(f"   SELL_ALL: {action_counts[4]} ({action_counts[4]/total_actions*100:.1f}%)")
        else:
            logger.warning(f"⚠️ No actions recorded - RL model may have failed to generate predictions")

        final_value = equity_df['portfolio_value'].iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital
        max_dd = self._calculate_max_drawdown(equity_df['portfolio_value'])

        # 计算夏普比率（假设无风险利率为0，使用日收益率）
        sharpe_ratio = self._calculate_sharpe_ratio(equity_df['portfolio_value'])

        # 计算胜率和平均持仓天数
        win_rate, avg_holding_days = self._calculate_trade_stats(trades)

        # 构造前端期望的结果格式（summary + equity_curve）
        results = {
            'summary': {
                'initial_capital': self.initial_capital,
                'final_value': float(final_value),
                'total_return': float(total_return),
                'total_return_pct': float(total_return * 100),
                'max_drawdown': float(max_dd),
                'max_drawdown_pct': float(max_dd * 100),
                'total_trades': len(trades),
                'sharpe_ratio': float(sharpe_ratio),
                'win_rate': float(win_rate),
                'avg_holding_days': float(avg_holding_days)
            },
            'equity_curve': equity_df.to_dict('records'),
            'trades': trades
        }

        logger.info(f" Final Value: ¥{final_value:,.2f}")
        logger.info(f" Total Return: {total_return*100:.2f}%")
        logger.info(f" Max Drawdown: {max_dd*100:.2f}%")
        logger.info(f" Sharpe Ratio: {sharpe_ratio:.2f}")
        logger.info(f" Win Rate: {win_rate*100:.1f}%")
        logger.info(f" Avg Holding Days: {avg_holding_days:.1f} days")
        logger.info(f" Total Trades: {len(trades)}")

        return results

    def _calculate_max_drawdown(self, equity_series: pd.Series) -> float:
        """计算最大回撤"""
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax
        return float(drawdown.min())

    def _calculate_sharpe_ratio(self, equity_series: pd.Series, risk_free_rate: float = 0.0) -> float:
        """计算夏普比率

        Args:
            equity_series: 资金曲线序列
            risk_free_rate: 无风险利率（年化），默认为0

        Returns:
            夏普比率
        """
        if len(equity_series) < 2:
            return 0.0

        # 计算日收益率
        returns = equity_series.pct_change().dropna()

        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        # 计算年化收益率和波动率（假设252个交易日）
        avg_return = returns.mean() * 252
        std_return = returns.std() * np.sqrt(252)

        # 夏普比率 = (年化收益率 - 无风险利率) / 年化波动率
        sharpe = (avg_return - risk_free_rate) / std_return if std_return > 0 else 0.0

        return sharpe

    def _calculate_trade_stats(self, trades: List[Dict]) -> tuple[float, float]:
        """计算交易统计：胜率和平均持仓天数

        Args:
            trades: 交易记录列表

        Returns:
            (胜率, 平均持仓天数)
        """
        if len(trades) == 0:
            return 0.0, 0.0

        # 统计买入和卖出交易，计算每笔交易的盈亏
        buy_trades = {}  # {ticker: {'date': date, 'price': price, 'shares': shares}}
        profitable_trades = 0
        total_closed_trades = 0
        total_holding_days = 0

        for trade in trades:
            ticker = trade['ticker']
            action = trade['action']

            # 将字符串日期转换为datetime对象（如果需要）
            trade_date = trade['date']
            if isinstance(trade_date, str):
                trade_date = datetime.strptime(trade_date, '%Y-%m-%d')

            if action in ['BUY_25', 'BUY_50']:
                # 记录买入
                if ticker not in buy_trades:
                    buy_trades[ticker] = []
                buy_trades[ticker].append({
                    'date': trade_date,
                    'price': trade['price'],
                    'shares': trade['shares']
                })

            elif action in ['SELL_50', 'SELL_ALL']:
                # 计算卖出盈亏
                if ticker in buy_trades and len(buy_trades[ticker]) > 0:
                    buy_trade = buy_trades[ticker][0]  # FIFO

                    # 计算持仓天数
                    holding_days = (trade_date - buy_trade['date']).days
                    total_holding_days += holding_days

                    # 判断是否盈利
                    if trade['price'] > buy_trade['price']:
                        profitable_trades += 1

                    total_closed_trades += 1

                    # 移除已卖出的买入记录
                    buy_trades[ticker].pop(0)

        # 计算胜率
        win_rate = profitable_trades / total_closed_trades if total_closed_trades > 0 else 0.0

        # 计算平均持仓天数
        avg_holding_days = total_holding_days / total_closed_trades if total_closed_trades > 0 else 0.0

        return win_rate, avg_holding_days

    def _prepare_observation(
        self,
        historical_data: pd.DataFrame,
        current_date: datetime,
        cash: float = 0.0,
        portfolio_value: float = 0.0,
        current_position: int = 0,
        current_price: float = 0.0
    ) -> Optional[np.ndarray]:
        """准备 RL 模型的观察（从历史数据中提取特征）

        Args:
            historical_data: 完整的历史数据 DataFrame
            current_date: 当前日期
            cash: 当前现金
            portfolio_value: 当前总资产价值
            current_position: 当前持仓数量
            current_price: 当前股票价格

        Returns:
            观察向量（numpy array）或 None（数据不足）
        """
        # 只使用到 current_date 为止的数据（避免 Look-Ahead）
        df = historical_data[historical_data.index <= current_date].copy()

        lookback_window = 60  # 需要60天数据来计算技术指标

        if len(df) < lookback_window:
            return None

        # 只使用最后 lookback_window 条数据
        df = df.tail(lookback_window)

        # 获取最新行
        latest_row = df.iloc[-1]

        # ===== 市场特征 =====
        close = latest_row['close']
        open_price = latest_row['open']

        market_features = np.array([
            close / 100.0,  # 标准化价格
            latest_row['high'] / 100.0,
            latest_row['low'] / 100.0,
            latest_row['volume'] / 1e6,  # 标准化成交量
            (close - open_price) / open_price if open_price > 0 else 0  # 涨跌幅
        ], dtype=np.float32)

        # ===== 技术指标（动态计算） =====
        rsi = self._calculate_rsi(df['close'], window=14)
        macd = self._calculate_macd(df['close'], fast=12, slow=26)
        ma10 = self._calculate_ma(df['close'], window=10)
        ma20 = self._calculate_ma(df['close'], window=20)
        atr = self._calculate_atr(df)

        technical_features = np.array([
            rsi / 100.0,  # RSI归一化
            np.tanh(macd / close) if close > 0 else 0,  # MACD标准化
            (close - ma10) / ma10 if ma10 > 0 else 0,  # MA10偏离度
            (close - ma20) / ma20 if ma20 > 0 else 0,  # MA20偏离度
            atr / close if close > 0 else 0  # ATR标准化
        ], dtype=np.float32)

        # ===== 账户状态（使用真实账户数据） =====
        # 计算真实的账户比例
        cash_ratio = cash / portfolio_value if portfolio_value > 0 else 1.0
        position_value = current_position * current_price if current_position > 0 and current_price > 0 else 0.0
        position_ratio = position_value / portfolio_value if portfolio_value > 0 else 0.0

        # 计算未实现盈亏（简化版本，假设成本价等于当前价的90%作为近似）
        # 在实际回测中，这是一个占位符，因为我们没有追踪买入成本价
        unrealized_pnl = 0.0

        account_features = np.array([
            cash_ratio,      # 现金比例
            position_ratio,  # 持仓比例
            unrealized_pnl   # 未实现盈亏（占位符）
        ], dtype=np.float32)

        # ===== T+1状态（A股特有） =====
        # 在回测中，假设所有持仓都可以卖出（简化T+1规则）
        t1_features = np.array([1.0], dtype=np.float32)  # can_sell_ratio

        # 合并所有特征：市场(5) + 技术(5) + 账户(3) + T+1(1) = 14
        obs = np.concatenate([market_features, technical_features, account_features, t1_features])

        # 处理异常值
        obs = np.nan_to_num(obs, nan=0.0, posinf=1.0, neginf=-1.0)
        obs = np.clip(obs, -10, 10)

        return obs

    def _calculate_rsi(self, close_prices: pd.Series, window: int = 14) -> float:
        """计算RSI指标"""
        if len(close_prices) < window + 1:
            return 50.0

        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]
        return current_rsi if not np.isnan(current_rsi) else 50.0

    def _calculate_macd(self, close_prices: pd.Series, fast: int = 12, slow: int = 26) -> float:
        """计算MACD指标"""
        if len(close_prices) < slow:
            return 0.0

        ema_fast = close_prices.ewm(span=fast, adjust=False).mean()
        ema_slow = close_prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow

        current_macd = macd.iloc[-1]
        return current_macd if not np.isnan(current_macd) else 0.0

    def _calculate_ma(self, close_prices: pd.Series, window: int = 10) -> float:
        """计算移动平均线"""
        if len(close_prices) < window:
            return close_prices.mean() if len(close_prices) > 0 else 0.0

        ma = close_prices.rolling(window=window).mean()

        current_ma = ma.iloc[-1]
        return current_ma if not np.isnan(current_ma) else close_prices.iloc[-1]

    def _calculate_atr(self, df: pd.DataFrame, window: int = 14) -> float:
        """计算ATR（Average True Range）指标

        Args:
            df: 包含high, low, close列的DataFrame
            window: ATR计算窗口

        Returns:
            ATR值
        """
        if len(df) < window + 1:
            return 0.0

        # 计算True Range (使用numpy更稳健)
        high = df['high'].values
        low = df['low'].values
        close_prev = np.roll(df['close'].values, 1)  # 前一天收盘价

        # 第一个元素没有前一天收盘价，使用当天收盘价
        close_prev[0] = df['close'].iloc[0]

        # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        tr1 = high - low
        tr2 = np.abs(high - close_prev)
        tr3 = np.abs(low - close_prev)

        true_range = np.maximum(np.maximum(tr1, tr2), tr3)

        # 计算ATR（True Range的移动平均）
        # 转换为Series以便使用rolling
        tr_series = pd.Series(true_range)
        atr = tr_series.rolling(window=window).mean()

        current_atr = atr.iloc[-1]
        return current_atr if not np.isnan(current_atr) else 0.0

    async def run_async(self) -> Dict:
        """异步运行回测"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.run)


# 保持向后兼容的别名（旧名称）
SimpleBacktestRunner = QFLibBacktestRunner

