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
            logger.error(f'RL signal generation failed: {e}')
            return self._simple_fallback(current_data, portfolio_state)

    def _prepare_observation(self, current_data: pd.DataFrame, portfolio_state: Dict[str, Any]) -> np.ndarray:
        df = current_data.copy()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['ma10'] = df['close'].rolling(window=10).mean()
        df.fillna(0, inplace=True)
        
        latest = df.iloc[-1]
        close = latest['close']
        
        market_features = np.array([
            close / 100.0,
            latest['high'] / 100.0,
            latest['low'] / 100.0,
            latest['volume'] / 1e6,
            (latest['close'] - latest['open']) / latest['open'] if latest['open'] > 0 else 0
        ], dtype=np.float32)
        
        technical_features = np.array([
            latest['rsi'] / 100.0,
            np.tanh(latest['macd'] / close) if close > 0 else 0,
            (latest['close'] - latest['ma10']) / latest['ma10'] if latest['ma10'] > 0 else 0
        ], dtype=np.float32)
        
        cash = portfolio_state.get('cash', 100000)
        total_equity = portfolio_state.get('total_equity', 100000)
        account_features = np.array([
            cash / total_equity if total_equity > 0 else 1.0,
            1.0 - (cash / total_equity) if total_equity > 0 else 0.0
        ], dtype=np.float32)
        
        observation = np.concatenate([market_features, technical_features, account_features])
        observation = np.nan_to_num(observation, nan=0.0, posinf=1.0, neginf=-1.0)
        observation = np.clip(observation, -10, 10)
        
        return observation

    def _action_to_signal(self, action: int) -> Dict[str, Any]:
        action_names = ['HOLD', 'BUY', 'SELL']
        action_name = action_names[int(action)]
        
        if action == 0:
            return {'action': 'hold', 'reason': f'RL: {action_name}'}
        elif action == 1:
            if not self.has_position:
                return {'action': 'buy', 'reason': f'RL: {action_name}'}
            else:
                return {'action': 'hold', 'reason': f'RL: {action_name} but already holding'}
        elif action == 2:
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
        elif side == 'sell':
            self.has_position = False

    def reset(self):
        self.has_position = False
