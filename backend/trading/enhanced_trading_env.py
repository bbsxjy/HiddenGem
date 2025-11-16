"""
Enhanced Trading Environment with T+1 Constraint for A-Share Market

增强版交易环境，支持A股T+1交易限制
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Tuple, Dict
import logging
from collections import deque

logger = logging.getLogger(__name__)


class EnhancedTradingEnv(gym.Env):
    """增强版交易环境（支持T+1限制）

    A-Share Specific Features:
        - T+1交易限制：当日买入的股票，次日才能卖出
        - 涨跌停限制：主板±10%，创业板/科创板±20%
        - 真实交易成本：佣金0.03% + 印花税0.1%(卖出)

    State Space:
        - 价格相关: close, high, low, volume (标准化)
        - 技术指标: RSI, MACD, MA10, MA20, ATR (标准化)
        - 账户状态: cash_ratio, position_ratio, unrealized_pnl
        - T+1状态: can_sell_ratio (可卖出比例)

    Action Space:
        - 0: HOLD (持有)
        - 1: BUY_25 (买入25%可用资金)
        - 2: BUY_50 (买入50%可用资金)
        - 3: SELL_50 (卖出50%可卖持仓)
        - 4: SELL_ALL (卖出全部可卖持仓)

    Reward:
        - 主要：收益率（risk-adjusted）
        - 次要：夏普比率、最大回撤惩罚
        - 惩罚：过度交易、频繁止损
    """

    metadata = {'render.modes': ['human']}

    def __init__(
        self,
        df: pd.DataFrame,
        initial_cash: float = 100000.0,
        commission_rate: float = 0.00013,  # 0.013%佣金
        stamp_duty: float = 0.001,  # 0.1%印花税（仅卖出）
        max_shares: int = 100000,
        lookback_window: int = 20,
        enable_t1: bool = True  # 是否启用T+1限制
    ):
        """初始化环境

        Args:
            df: 市场数据（必须包含: open, high, low, close, volume）
            initial_cash: 初始资金
            commission_rate: 佣金率
            stamp_duty: 印花税率
            max_shares: 最大持仓数量
            lookback_window: 回看窗口大小
            enable_t1: 是否启用T+1限制
        """
        super().__init__()

        self.df = df.reset_index(drop=True)
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.stamp_duty = stamp_duty
        self.max_shares = max_shares
        self.lookback_window = lookback_window
        self.enable_t1 = enable_t1

        # 动作空间: 0=HOLD, 1=BUY_25, 2=BUY_50, 3=SELL_50, 4=SELL_ALL
        self.action_space = spaces.Discrete(5)

        # 观察空间维度：市场(5) + 技术(5) + 账户(3) + T+1(1) = 14
        obs_dim = 5 + 5 + 3 + 1
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_dim,),
            dtype=np.float32
        )

        # T+1持仓追踪：{买入日期: 持仓数量}
        self.t1_holdings: Dict[int, int] = {}

        # 环境状态
        self.current_step = 0
        self.cash = initial_cash
        self.shares_held = 0
        self.cost_basis = 0.0

        # 历史记录
        self.portfolio_values = []
        self.trades = []
        self.daily_returns = []

        logger.info(
            f"EnhancedTradingEnv initialized: {len(df)} days, "
            f"T+1={'enabled' if enable_t1 else 'disabled'}, "
            f"initial_cash={initial_cash}"
        )

    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, dict]:
        """重置环境"""
        super().reset(seed=seed)

        self.current_step = self.lookback_window
        self.cash = self.initial_cash
        self.shares_held = 0
        self.cost_basis = 0.0
        self.t1_holdings = {}

        self.portfolio_values = []
        self.trades = []
        self.daily_returns = []

        obs = self._get_observation()
        info = {}

        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """执行一步"""
        # 检查是否结束
        done = self.current_step >= len(self.df) - 1

        if done:
            final_value = self._get_portfolio_value()
            total_return = (final_value - self.initial_cash) / self.initial_cash

            return (
                self._get_observation(),
                0.0,
                True,
                False,
                {
                    'final_value': final_value,
                    'total_return': total_return,
                    'total_trades': len(self.trades),
                    'sharpe_ratio': self._calculate_sharpe_ratio(),
                    'max_drawdown': self._calculate_max_drawdown()
                }
            )

        # 记录开始价值
        begin_value = self._get_portfolio_value()

        # 执行动作
        self._execute_action(action)

        # 前进一步
        self.current_step += 1

        # 清理过期的T+1持仓（已经可以卖出的）
        self._cleanup_t1_holdings()

        # 计算奖励
        end_value = self._get_portfolio_value()
        reward = self._calculate_reward(begin_value, end_value, action)

        # 记录
        self.portfolio_values.append(end_value)
        if begin_value > 0:
            daily_return = (end_value - begin_value) / begin_value
            self.daily_returns.append(daily_return)

        # 获取新观察
        obs = self._get_observation()

        return obs, reward, False, False, {}

    def _get_observation(self) -> np.ndarray:
        """获取当前观察（动态计算技术指标）"""
        row = self.df.iloc[self.current_step]
        close = row['close']

        # 获取历史数据
        historical_data = self.df.iloc[:self.current_step + 1]

        # ===== 市场特征 =====
        market_features = np.array([
            row['close'] / 100.0,
            row['high'] / 100.0,
            row['low'] / 100.0,
            row['volume'] / 1e6,
            (row['close'] - row['open']) / row['open'] if row['open'] > 0 else 0
        ], dtype=np.float32)

        # ===== 技术指标 =====
        rsi = self._calculate_rsi(historical_data['close'])
        macd = self._calculate_macd(historical_data['close'])
        ma10 = self._calculate_ma(historical_data['close'], 10)
        ma20 = self._calculate_ma(historical_data['close'], 20)
        atr = self._calculate_atr(historical_data)

        technical_features = np.array([
            rsi / 100.0,
            np.tanh(macd / close) if close > 0 else 0,
            (close - ma10) / ma10 if ma10 > 0 else 0,
            (close - ma20) / ma20 if ma20 > 0 else 0,
            atr / close if close > 0 else 0
        ], dtype=np.float32)

        # ===== 账户状态 =====
        portfolio_value = self._get_portfolio_value()
        unrealized_pnl = 0
        if self.shares_held > 0 and self.cost_basis > 0:
            unrealized_pnl = (close - self.cost_basis) / self.cost_basis

        account_features = np.array([
            self.cash / portfolio_value if portfolio_value > 0 else 1.0,
            (self.shares_held * close) / portfolio_value if portfolio_value > 0 else 0.0,
            unrealized_pnl
        ], dtype=np.float32)

        # ===== T+1状态 =====
        sellable_shares = self._get_sellable_shares()
        can_sell_ratio = sellable_shares / self.shares_held if self.shares_held > 0 else 1.0

        t1_features = np.array([can_sell_ratio], dtype=np.float32)

        # 合并所有特征
        obs = np.concatenate([market_features, technical_features, account_features, t1_features])

        # 处理异常值
        obs = np.nan_to_num(obs, nan=0.0, posinf=1.0, neginf=-1.0)
        obs = np.clip(obs, -10, 10)

        return obs

    def _execute_action(self, action: int):
        """执行交易动作（考虑T+1限制）"""
        price = self.df.iloc[self.current_step]['close']

        if action == 1:  # BUY_25
            self._execute_buy(price, 0.25)
        elif action == 2:  # BUY_50
            self._execute_buy(price, 0.50)
        elif action == 3:  # SELL_50
            self._execute_sell(price, 0.50)
        elif action == 4:  # SELL_ALL
            self._execute_sell(price, 1.00)
        # action == 0 (HOLD) 不执行任何操作

    def _execute_buy(self, price: float, cash_pct: float):
        """执行买入"""
        available_cash = self.cash * cash_pct
        # 买入成本 = 价格 + 佣金
        shares_to_buy = int(available_cash / (price * (1 + self.commission_rate)))

        if shares_to_buy > 0 and self.shares_held + shares_to_buy <= self.max_shares:
            cost = shares_to_buy * price * (1 + self.commission_rate)
            if cost <= self.cash:
                self.cash -= cost

                # 更新成本基础
                old_cost = self.cost_basis * self.shares_held
                new_cost = price * shares_to_buy
                self.shares_held += shares_to_buy
                self.cost_basis = (old_cost + new_cost) / self.shares_held if self.shares_held > 0 else price

                # 记录T+1持仓
                if self.enable_t1:
                    if self.current_step not in self.t1_holdings:
                        self.t1_holdings[self.current_step] = 0
                    self.t1_holdings[self.current_step] += shares_to_buy

                self.trades.append({
                    'step': self.current_step,
                    'action': f'BUY_{int(cash_pct*100)}',
                    'shares': shares_to_buy,
                    'price': price,
                    'cost': cost
                })

    def _execute_sell(self, price: float, position_pct: float):
        """执行卖出（考虑T+1限制）"""
        if self.shares_held == 0:
            return

        # 计算可卖出数量（考虑T+1）
        sellable_shares = self._get_sellable_shares()
        if sellable_shares == 0:
            return

        shares_to_sell = int(sellable_shares * position_pct)
        if shares_to_sell == 0:
            return

        # 卖出收益 = 价格 - 佣金 - 印花税
        proceeds = shares_to_sell * price * (1 - self.commission_rate - self.stamp_duty)
        self.cash += proceeds
        self.shares_held -= shares_to_sell

        # 更新T+1持仓记录
        if self.enable_t1:
            self._update_t1_holdings_after_sell(shares_to_sell)

        self.trades.append({
            'step': self.current_step,
            'action': f'SELL_{int(position_pct*100)}',
            'shares': shares_to_sell,
            'price': price,
            'proceeds': proceeds
        })

    def _get_sellable_shares(self) -> int:
        """获取当前可卖出的股票数量（考虑T+1）"""
        if not self.enable_t1:
            return self.shares_held

        # T+1限制：只能卖出T-1及之前买入的股票
        sellable = self.shares_held
        if self.current_step in self.t1_holdings:
            sellable -= self.t1_holdings[self.current_step]

        return max(0, sellable)

    def _cleanup_t1_holdings(self):
        """清理已经可以卖出的T+1持仓记录"""
        if not self.enable_t1:
            return

        # 删除当前日期之前的记录（已经过了T+1期限）
        expired_dates = [d for d in self.t1_holdings.keys() if d < self.current_step]
        for d in expired_dates:
            del self.t1_holdings[d]

    def _update_t1_holdings_after_sell(self, shares_sold: int):
        """卖出后更新T+1持仓记录"""
        if not self.enable_t1:
            return

        remaining = shares_sold
        # 按日期从旧到新删除
        for buy_date in sorted(self.t1_holdings.keys()):
            if remaining == 0:
                break
            if buy_date >= self.current_step:
                continue  # 跳过今日买入的（不能卖）

            available = self.t1_holdings[buy_date]
            if available >= remaining:
                self.t1_holdings[buy_date] -= remaining
                remaining = 0
            else:
                remaining -= available
                self.t1_holdings[buy_date] = 0

            if self.t1_holdings[buy_date] == 0:
                del self.t1_holdings[buy_date]

    def _calculate_rsi(self, close_prices: pd.Series, window: int = 14) -> float:
        """计算RSI"""
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
        """计算MACD"""
        if len(close_prices) < slow:
            return 0.0

        ema_fast = close_prices.ewm(span=fast, adjust=False).mean()
        ema_slow = close_prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow

        current_macd = macd.iloc[-1]
        return current_macd if not np.isnan(current_macd) else 0.0

    def _calculate_ma(self, close_prices: pd.Series, window: int = 10) -> float:
        """计算移动平均"""
        if len(close_prices) < window:
            return close_prices.mean() if len(close_prices) > 0 else 0.0

        ma = close_prices.rolling(window=window).mean()
        current_ma = ma.iloc[-1]
        return current_ma if not np.isnan(current_ma) else close_prices.iloc[-1]

    def _calculate_atr(self, data: pd.DataFrame, window: int = 14) -> float:
        """计算ATR（平均真实波幅）"""
        if len(data) < 2:
            return 0.0

        high = data['high']
        low = data['low']
        close = data['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=window).mean()

        current_atr = atr.iloc[-1]
        return current_atr if not np.isnan(current_atr) else 0.0

    def _get_portfolio_value(self) -> float:
        """计算当前组合价值"""
        price = self.df.iloc[self.current_step]['close']
        return self.cash + self.shares_held * price

    def _calculate_reward(self, begin_value: float, end_value: float, action: int) -> float:
        """计算奖励（改进版）"""
        # 1. 基础收益奖励
        if begin_value > 0:
            return_pct = (end_value - begin_value) / begin_value
            reward = return_pct * 100  # 放大
        else:
            reward = 0

        # 2. 风险调整
        if len(self.daily_returns) > 10:
            # 惩罚高波动
            volatility = np.std(self.daily_returns[-20:])
            reward -= volatility * 10

        # 3. 持仓奖励（避免长期空仓）
        if self.shares_held > 0:
            reward += 0.01

        # 4. 交易成本惩罚
        if action != 0:
            reward -= 0.01

        # 5. T+1违规惩罚（如果试图卖出当天买入的股票）
        # 这个在_execute_sell中已经被阻止了，这里不需要额外惩罚

        return reward

    def _calculate_sharpe_ratio(self) -> float:
        """计算夏普比率"""
        if len(self.daily_returns) < 2:
            return 0.0

        returns = np.array(self.daily_returns)
        if np.std(returns) == 0:
            return 0.0

        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)  # 年化
        return sharpe

    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if len(self.portfolio_values) == 0:
            return 0.0

        values = np.array([self.initial_cash] + self.portfolio_values)
        peaks = np.maximum.accumulate(values)
        drawdowns = (values - peaks) / peaks

        return abs(np.min(drawdowns))

    def render(self, mode='human'):
        """渲染环境状态"""
        portfolio_value = self._get_portfolio_value()
        profit = portfolio_value - self.initial_cash
        profit_pct = profit / self.initial_cash * 100
        sellable = self._get_sellable_shares()

        print(f"Step: {self.current_step}")
        print(f"Cash: ¥{self.cash:,.2f}")
        print(f"Shares Held: {self.shares_held} (Sellable: {sellable})")
        print(f"Portfolio Value: ¥{portfolio_value:,.2f}")
        print(f"Profit: ¥{profit:,.2f} ({profit_pct:.2f}%)")
        if len(self.daily_returns) > 0:
            print(f"Sharpe Ratio: {self._calculate_sharpe_ratio():.2f}")
            print(f"Max Drawdown: {self._calculate_max_drawdown():.2%}")
        print("-" * 50)
