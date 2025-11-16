"""
Simple Trading Environment for RL Training

简化版交易环境，用于快速训练 RL 模型
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class SimpleTradingEnv(gym.Env):
    """简化版交易环境

    State Space:
        - 价格相关: close, high, low, volume (标准化)
        - 技术指标: RSI, MACD, MA (标准化)
        - 账户状态: cash_ratio, position_ratio

    Action Space:
        - 0: HOLD (持有)
        - 1: BUY (买入30%可用资金)
        - 2: SELL (卖出50%持仓)

    Reward:
        - 收益率奖励
        - 持仓奖励（避免过度交易）
        - 交易成本惩罚
    """

    metadata = {'render.modes': ['human']}

    def __init__(
        self,
        df: pd.DataFrame,
        initial_cash: float = 100000.0,
        commission_rate: float = 0.0003,
        max_shares: int = 100000,
        lookback_window: int = 10
    ):
        """初始化环境

        Args:
            df: 市场数据（必须包含: close, high, low, volume）
            initial_cash: 初始资金
            commission_rate: 手续费率
            max_shares: 最大持仓数量
            lookback_window: 回看窗口大小
        """
        super().__init__()

        self.df = df.reset_index(drop=True)
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.max_shares = max_shares
        self.lookback_window = lookback_window

        # 动作空间: 0=HOLD, 1=BUY, 2=SELL
        self.action_space = spaces.Discrete(3)

        # 观察空间维度
        obs_dim = 5 + 3 + 2  # 市场特征(5) + 技术指标(3) + 账户状态(2)
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(obs_dim,),
            dtype=np.float32
        )

        # 计算技术指标
        self._calculate_indicators()

        # 环境状态
        self.current_step = 0
        self.cash = initial_cash
        self.shares_held = 0
        self.cost_basis = 0.0

        # 历史记录
        self.portfolio_values = []
        self.trades = []

        logger.info(f"SimpleTradingEnv initialized: {len(df)} days, initial_cash={initial_cash}")

    def _calculate_indicators(self):
        """初始化技术指标列（不预计算，避免Look-Ahead Bias）"""
        # 不再预计算指标，而是在_get_observation中动态计算
        # 这样可以确保只使用截至当前时间点的历史数据
        pass

    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, dict]:
        """重置环境"""
        super().reset(seed=seed)

        self.current_step = self.lookback_window
        self.cash = self.initial_cash
        self.shares_held = 0
        self.cost_basis = 0.0

        self.portfolio_values = []
        self.trades = []

        obs = self._get_observation()
        info = {}

        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """执行一步"""
        # 检查是否结束
        done = self.current_step >= len(self.df) - 1

        if done:
            final_value = self._get_portfolio_value()
            return_pct = (final_value - self.initial_cash) / self.initial_cash

            return (
                self._get_observation(),
                0.0,
                True,
                False,
                {
                    'final_value': final_value,
                    'return': return_pct,
                    'trades': len(self.trades)
                }
            )

        # 记录开始价值
        begin_value = self._get_portfolio_value()

        # 执行动作
        self._execute_action(action)

        # 前进一步
        self.current_step += 1

        # 计算奖励
        end_value = self._get_portfolio_value()
        reward = self._calculate_reward(begin_value, end_value, action)

        # 记录
        self.portfolio_values.append(end_value)

        # 获取新观察
        obs = self._get_observation()

        return obs, reward, False, False, {}

    def _get_observation(self) -> np.ndarray:
        """获取当前观察（动态计算技术指标，避免Look-Ahead Bias）"""
        row = self.df.iloc[self.current_step]
        close = row['close']

        # ===== 动态计算技术指标（只使用历史数据） =====
        # 获取截至当前时间点的历史数据
        historical_data = self.df.iloc[:self.current_step + 1]

        # 计算RSI（使用历史数据）
        rsi_value = self._calculate_rsi(historical_data['close'])

        # 计算MACD（使用历史数据）
        macd_value = self._calculate_macd(historical_data['close'])

        # 计算MA10（使用历史数据）
        ma10_value = self._calculate_ma(historical_data['close'], window=10)

        # ===== 市场特征 (标准化) =====
        market_features = np.array([
            row['close'] / 100.0,  # 标准化价格
            row['high'] / 100.0,
            row['low'] / 100.0,
            row['volume'] / 1e6,  # 标准化成交量
            (row['close'] - row['open']) / row['open'] if row['open'] > 0 else 0  # 涨跌幅
        ], dtype=np.float32)

        # ===== 技术指标 (标准化) =====
        technical_features = np.array([
            rsi_value / 100.0,  # RSI 归一化到 0-1
            np.tanh(macd_value / close) if close > 0 else 0,  # MACD 标准化
            (close - ma10_value) / ma10_value if ma10_value > 0 else 0  # MA偏离度
        ], dtype=np.float32)

        # ===== 账户状态 =====
        portfolio_value = self._get_portfolio_value()
        account_features = np.array([
            self.cash / portfolio_value if portfolio_value > 0 else 1.0,  # 现金比例
            (self.shares_held * close) / portfolio_value if portfolio_value > 0 else 0.0  # 持仓比例
        ], dtype=np.float32)

        # 合并
        obs = np.concatenate([market_features, technical_features, account_features])

        # 处理异常值
        obs = np.nan_to_num(obs, nan=0.0, posinf=1.0, neginf=-1.0)
        obs = np.clip(obs, -10, 10)

        return obs

    def _calculate_rsi(self, close_prices: pd.Series, window: int = 14) -> float:
        """动态计算RSI指标（只使用历史数据）

        Args:
            close_prices: 截至当前时间点的收盘价序列
            window: RSI窗口大小

        Returns:
            当前时间点的RSI值
        """
        if len(close_prices) < window + 1:
            return 50.0  # 数据不足时返回中性值

        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # 返回最后一个值（当前时间点）
        current_rsi = rsi.iloc[-1]
        return current_rsi if not np.isnan(current_rsi) else 50.0

    def _calculate_macd(self, close_prices: pd.Series, fast: int = 12, slow: int = 26) -> float:
        """动态计算MACD指标（只使用历史数据）

        Args:
            close_prices: 截至当前时间点的收盘价序列
            fast: 快速EMA周期
            slow: 慢速EMA周期

        Returns:
            当前时间点的MACD值
        """
        if len(close_prices) < slow:
            return 0.0  # 数据不足时返回0

        ema_fast = close_prices.ewm(span=fast, adjust=False).mean()
        ema_slow = close_prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow

        # 返回最后一个值（当前时间点）
        current_macd = macd.iloc[-1]
        return current_macd if not np.isnan(current_macd) else 0.0

    def _calculate_ma(self, close_prices: pd.Series, window: int = 10) -> float:
        """动态计算移动平均线（只使用历史数据）

        Args:
            close_prices: 截至当前时间点的收盘价序列
            window: MA窗口大小

        Returns:
            当前时间点的MA值
        """
        if len(close_prices) < window:
            # 数据不足时使用平均值
            return close_prices.mean() if len(close_prices) > 0 else 0.0

        ma = close_prices.rolling(window=window).mean()

        # 返回最后一个值（当前时间点）
        current_ma = ma.iloc[-1]
        return current_ma if not np.isnan(current_ma) else close_prices.iloc[-1]

    def _execute_action(self, action: int):
        """执行交易动作"""
        price = self.df.iloc[self.current_step]['close']

        if action == 1:  # BUY
            # 买入30%可用资金
            available_cash = self.cash * 0.3
            shares_to_buy = int(available_cash / (price * (1 + self.commission_rate)))

            if shares_to_buy > 0 and self.shares_held + shares_to_buy <= self.max_shares:
                cost = shares_to_buy * price * (1 + self.commission_rate)
                if cost <= self.cash:
                    self.cash -= cost
                    self.shares_held += shares_to_buy
                    self.cost_basis = (self.cost_basis * (self.shares_held - shares_to_buy) +
                                      cost) / self.shares_held if self.shares_held > 0 else cost

                    self.trades.append({
                        'step': self.current_step,
                        'action': 'BUY',
                        'shares': shares_to_buy,
                        'price': price
                    })

        elif action == 2:  # SELL
            # 卖出50%持仓
            if self.shares_held > 0:
                shares_to_sell = int(self.shares_held * 0.5)
                if shares_to_sell > 0:
                    proceeds = shares_to_sell * price * (1 - self.commission_rate)
                    self.cash += proceeds
                    self.shares_held -= shares_to_sell

                    self.trades.append({
                        'step': self.current_step,
                        'action': 'SELL',
                        'shares': shares_to_sell,
                        'price': price
                    })

    def _get_portfolio_value(self) -> float:
        """计算当前组合价值"""
        price = self.df.iloc[self.current_step]['close']
        return self.cash + self.shares_held * price

    def _calculate_reward(self, begin_value: float, end_value: float, action: int) -> float:
        """计算奖励"""
        # 收益率奖励
        return_pct = (end_value - begin_value) / begin_value if begin_value > 0 else 0
        reward = return_pct * 100  # 放大奖励

        # 持仓奖励（避免空仓）
        if self.shares_held > 0:
            reward += 0.01

        # 交易成本惩罚
        if action != 0:  # 非HOLD动作
            reward -= 0.02

        return reward

    def render(self, mode='human'):
        """渲染环境状态"""
        portfolio_value = self._get_portfolio_value()
        profit = portfolio_value - self.initial_cash
        profit_pct = profit / self.initial_cash * 100

        print(f"Step: {self.current_step}")
        print(f"Cash: {self.cash:.2f}")
        print(f"Shares: {self.shares_held}")
        print(f"Portfolio Value: {portfolio_value:.2f}")
        print(f"Profit: {profit:.2f} ({profit_pct:.2f}%)")
        print("-" * 40)
