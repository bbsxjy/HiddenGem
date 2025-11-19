# -*- coding: utf-8 -*-
"""RL Strategy - Reinforcement Learning Trading Strategy"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from .strategy import BaseStrategy
import logging
import os

logger = logging.getLogger(__name__)

try:
    from stable_baselines3 import PPO
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    logger.warning('stable-baselines3 not available')


class RLStrategy(BaseStrategy):
    """RL Strategy using pre-trained PPO model"""

    def __init__(self, model_path: str = 'models/production/final_model.zip'):
        super().__init__('RL')

        self.model_path = model_path
        self.model = None
        self.has_position = False
        self.entry_price = 0.0  # 记录买入价格用于计算未实现盈亏
        
        if SB3_AVAILABLE and os.path.exists(model_path):
            try:
                self.model = PPO.load(model_path)
                logger.info(f'RL model loaded: {model_path}')
            except Exception as e:
                logger.error(f'Failed to load RL model: {e}')
                self.model = None
        else:
            if not SB3_AVAILABLE:
                logger.warning('stable-baselines3 not installed')
            elif not os.path.exists(model_path):
                logger.warning(f'Model file not found: {model_path}')

    def generate_signal(self, symbol: str, current_data: pd.DataFrame, portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        if self.model is None:
            logger.warning('RL model not available, using fallback')
            return self._simple_fallback(current_data, portfolio_state)

        try:
            self.has_position = portfolio_state.get('has_position', False)
            observation = self._prepare_observation(current_data, portfolio_state)
            action, _states = self.model.predict(observation, deterministic=True)
            signal = self._action_to_signal(action)
            return signal
        except Exception as e:
            logger.error(f'RL signal generation failed: {e}', exc_info=True)
            return self._simple_fallback(current_data, portfolio_state)

    def _prepare_observation(self, current_data: pd.DataFrame, portfolio_state: Dict[str, Any]) -> np.ndarray:
        """准备观察空间，匹配训练环境的14维"""
        df = current_data.copy()

        # 检查数据行数
        if len(df) < 30:
            logger.warning(f"数据行数不足（{len(df)}行），建议至少30行以保证技术指标准确性")

        # 计算技术指标
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26

        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()

        # ATR (Average True Range)
        df['high_low'] = df['high'] - df['low']
        df['high_close'] = np.abs(df['high'] - df['close'].shift())
        df['low_close'] = np.abs(df['low'] - df['close'].shift())
        df['true_range'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
        df['atr'] = df['true_range'].rolling(window=14).mean()

        df.fillna(0, inplace=True)

        # 确保有数据
        if len(df) == 0:
            raise ValueError("DataFrame为空，无法生成观察")

        latest = df.iloc[-1]
        close = latest['close']

        # ===== 市场特征 (5维) =====
        market_features = np.array([
            close / 100.0,
            latest['high'] / 100.0,
            latest['low'] / 100.0,
            latest['volume'] / 1e6,
            (latest['close'] - latest['open']) / latest['open'] if latest['open'] > 0 else 0
        ], dtype=np.float32)

        # ===== 技术指标 (5维) =====
        technical_features = np.array([
            latest['rsi'] / 100.0,
            np.tanh(latest['macd'] / close) if close > 0 else 0,
            (close - latest['ma10']) / latest['ma10'] if latest['ma10'] > 0 else 0,
            (close - latest['ma20']) / latest['ma20'] if latest['ma20'] > 0 else 0,
            latest['atr'] / close if close > 0 else 0
        ], dtype=np.float32)

        # ===== 账户状态 (3维) =====
        cash = portfolio_state.get('cash', 100000)
        total_equity = portfolio_state.get('total_equity', 100000)

        # 计算未实现盈亏
        unrealized_pnl = 0.0
        if self.has_position and hasattr(self, 'entry_price') and self.entry_price > 0:
            unrealized_pnl = (close - self.entry_price) / self.entry_price

        account_features = np.array([
            cash / total_equity if total_equity > 0 else 1.0,
            1.0 - (cash / total_equity) if total_equity > 0 else 0.0,
            unrealized_pnl
        ], dtype=np.float32)

        # ===== T+1状态 (1维) =====
        # 简化版本：如果有持仓就是可以卖出的（实际应用中需要跟踪买入日期）
        can_sell_ratio = 1.0 if self.has_position else 0.0
        t1_features = np.array([can_sell_ratio], dtype=np.float32)

        # ===== 组合观察 (14维) =====
        observation = np.concatenate([
            market_features,     # 5维
            technical_features,  # 5维
            account_features,    # 3维
            t1_features         # 1维
        ])

        observation = np.nan_to_num(observation, nan=0.0, posinf=1.0, neginf=-1.0)
        observation = np.clip(observation, -10, 10)

        return observation

    def _action_to_signal(self, action: int) -> Dict[str, Any]:
        """将 RL action 转换为交易信号

        Args:
            action: PPO 模型输出的动作（可能是 int, numpy array, list 等）

        Returns:
            交易信号字典

        Action空间（enhanced_trading_env）：
            0: HOLD
            1: BUY_25 (买入25%)
            2: BUY_50 (买入50%)
            3: SELL_50 (卖出50%)
            4: SELL_ALL (卖出全部)
        """
        action_names = ['HOLD', 'BUY_25', 'BUY_50', 'SELL_50', 'SELL_ALL']

        # 安全地转换action为整数并进行边界检查
        try:
            # 处理 numpy array
            if hasattr(action, 'item'):
                action_int = int(action.item())
            # 处理 list 或 tuple
            elif isinstance(action, (list, tuple)):
                if len(action) > 0:
                    action_int = int(action[0])
                else:
                    logger.warning('Empty action list/tuple, defaulting to HOLD')
                    action_int = 0
            # 直接转换
            else:
                action_int = int(action)

            # 边界检查
            if action_int < 0 or action_int >= len(action_names):
                logger.warning(f'Invalid action value: {action_int}, defaulting to HOLD')
                action_int = 0

            action_name = action_names[action_int]

        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f'Failed to convert action to int: {action} (type: {type(action)}), error: {e}')
            action_int = 0
            action_name = 'HOLD'

        # HOLD
        if action_int == 0:
            return {'action': 'hold', 'reason': f'RL: {action_name}'}

        # BUY_25 or BUY_50
        elif action_int in [1, 2]:
            if not self.has_position:
                return {'action': 'buy', 'reason': f'RL: {action_name}'}
            else:
                return {'action': 'hold', 'reason': f'RL: {action_name} but already holding'}

        # SELL_50 or SELL_ALL
        elif action_int in [3, 4]:
            if self.has_position:
                return {'action': 'sell', 'reason': f'RL: {action_name}'}
            else:
                return {'action': 'hold', 'reason': f'RL: {action_name} but no position'}

        else:
            return {'action': 'hold', 'reason': 'RL: Unknown action'}

    def _simple_fallback(self, current_data: pd.DataFrame, portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        self.has_position = portfolio_state.get('has_position', False)
        if not self.has_position:
            return {'action': 'buy', 'reason': 'RL fallback: initial buy'}
        else:
            return {'action': 'hold', 'reason': 'RL fallback: hold'}

    def on_trade(self, trade_info: Dict[str, Any]):
        side = trade_info.get('side')
        if side == 'buy':
            self.has_position = True
            # 记录买入价格
            self.entry_price = trade_info.get('price', 0.0)
        elif side == 'sell':
            self.has_position = False
            self.entry_price = 0.0

    def reset(self):
        self.has_position = False
        self.entry_price = 0.0
