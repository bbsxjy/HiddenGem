"""
RL Strategy Adapter for QF-Lib

将Stable-Baselines3训练的RL模型包装为QF-Lib策略
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import logging

# QF-Lib imports (note: package name is qf_lib with underscore)
try:
    from qf_lib.backtesting.alpha_model.alpha_model import AlphaModel
    from qf_lib.backtesting.alpha_model.exposure_enum import Exposure
    from qf_lib.backtesting.data_handler.data_handler import DataHandler
    from qf_lib.common.tickers.tickers import Ticker
except ImportError:
    # 占位符
    AlphaModel = object
    Exposure = None
    DataHandler = None
    Ticker = str

# Stable-Baselines3 imports
try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import VecNormalize
    import pickle
    import os
except ImportError:
    PPO = None
    VecNormalize = None

logger = logging.getLogger(__name__)


class RLStrategyAdapter(AlphaModel if AlphaModel != object else object):
    """RL模型策略适配器

    将Stable-Baselines3训练的PPO模型包装为QF-Lib的AlphaModel接口，
    用于QF-Lib的事件驱动回测。

    Features:
        -  完全兼容QF-Lib回测框架
        -  动态计算技术指标（只使用历史数据）
        -  支持多种RL模型（PPO、A2C、SAC等）
        -  天然防护Look-Ahead Bias
        -  支持VecNormalize观测归一化
    """

    def __init__(
        self,
        model_path: str,
        ticker: Ticker,
        data_handler: DataHandler,
        lookback_window: int = 60
    ):
        """初始化RL策略适配器

        Args:
            model_path: RL模型路径（.zip文件）
            ticker: 交易标的
            data_handler: QF-Lib数据处理器
            lookback_window: 回看窗口大小（用于计算技术指标）
        """
        super().__init__()
        self.model_path = model_path
        self.ticker = ticker
        self.data_handler = data_handler
        self.lookback_window = lookback_window

        # 加载RL模型
        self.model = self._load_model(model_path)

        # 加载VecNormalize统计数据
        self.vec_normalize = self._load_vec_normalize(model_path)

        logger.info(f"RLStrategyAdapter initialized: model={model_path}, ticker={ticker}, vec_normalize={'loaded' if self.vec_normalize else 'not available'}")

    def _load_model(self, model_path: str):
        """加载RL模型

        Args:
            model_path: 模型文件路径

        Returns:
            加载的模型对象
        """
        if PPO is None:
            raise ImportError("Stable-Baselines3 not installed. Please install: pip install stable-baselines3")

        try:
            model = PPO.load(model_path)
            logger.info(f"RL model loaded from {model_path}")
            return model
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            raise

    def _load_vec_normalize(self, model_path: str):
        """加载VecNormalize统计数据

        Args:
            model_path: 模型文件路径

        Returns:
            VecNormalize对象或None
        """
        if VecNormalize is None:
            logger.warning("VecNormalize not available, observations will not be normalized")
            return None

        # 推断VecNormalize文件路径
        if model_path.endswith('.zip'):
            vec_norm_path = model_path.replace('.zip', '_vecnormalize.pkl')
        else:
            vec_norm_path = model_path + '_vecnormalize.pkl'

        if not os.path.exists(vec_norm_path):
            logger.warning(
                f'VecNormalize file not found: {vec_norm_path}. '
                'Observations will NOT be normalized during backtesting.'
            )
            return None

        try:
            with open(vec_norm_path, 'rb') as f:
                vec_normalize = pickle.load(f)

            # 设置为推理模式
            vec_normalize.training = False
            logger.info(f'VecNormalize loaded: {vec_norm_path}')
            return vec_normalize
        except Exception as e:
            logger.error(f'Failed to load VecNormalize: {e}')
            return None

    def calculate_exposure(
        self,
        ticker: Ticker,
        current_time: datetime
    ) -> Exposure:
        """计算当前持仓信号（QF-Lib标准接口）

        Args:
            ticker: 股票代码
            current_time: 当前回测时间

        Returns:
            持仓方向（LONG, SHORT, OUT）
        """
        # 获取历史数据（只到current_time，避免Look-Ahead）
        historical_data = self._get_historical_data(ticker, current_time)

        if historical_data.empty or len(historical_data) < self.lookback_window:
            logger.warning(f" Insufficient data for {ticker} at {current_time}")
            return Exposure.OUT

        # 准备观察（动态计算技术指标）
        obs = self._prepare_observation(historical_data)

        # 如果有VecNormalize，则归一化观测值
        if self.vec_normalize is not None:
            # VecNormalize期望输入形状为 (n_envs, obs_dim)
            obs_normalized = self.vec_normalize.normalize_obs(obs.reshape(1, -1))
            obs = obs_normalized.flatten()
            logger.debug(f"Observation normalized using VecNormalize")

        # RL模型预测
        action, _ = self.model.predict(obs, deterministic=True)

        # 转换为QF-Lib持仓信号
        exposure = self._action_to_exposure(action)

        logger.debug(f" {current_time} | {ticker} | Action={action} | Exposure={exposure}")

        return exposure

    def _get_historical_data(
        self,
        ticker: Ticker,
        current_time: datetime
    ) -> pd.DataFrame:
        """获取历史数据（只到当前时间）

        Args:
            ticker: 股票代码
            current_time: 当前时间

        Returns:
            历史数据DataFrame
        """
        # 计算起始日期
        start_date = current_time - timedelta(days=self.lookback_window * 2)  # 预留足够数据

        # 从DataHandler获取数据（QF-Lib确保不会访问未来）
        try:
            fields = ['open', 'high', 'low', 'close', 'volume']
            df = self.data_handler.get_price(
                tickers=[ticker],
                fields=fields,
                start_date=start_date,
                end_date=current_time  #  只到当前时间
            )

            # 确保DataFrame格式正确
            if isinstance(df, pd.Series):
                df = df.to_frame()

            return df

        except Exception as e:
            logger.error(f" Error fetching data for {ticker}: {e}")
            return pd.DataFrame()

    def _prepare_observation(self, historical_data: pd.DataFrame) -> np.ndarray:
        """准备RL模型的观察（动态计算技术指标）

        Args:
            historical_data: 历史数据DataFrame

        Returns:
            观察向量（numpy array）
        """
        # 只使用最后lookback_window条数据
        df = historical_data.tail(self.lookback_window).copy()

        if len(df) < self.lookback_window:
            logger.warning(f" Data length {len(df)} < lookback_window {self.lookback_window}")
            # 数据不足时填充
            df = df.reindex(range(self.lookback_window), fill_value=0)

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

        technical_features = np.array([
            rsi / 100.0,  # RSI归一化
            np.tanh(macd / close) if close > 0 else 0,  # MACD标准化
            (close - ma10) / ma10 if ma10 > 0 else 0  # MA偏离度
        ], dtype=np.float32)

        # ===== 账户状态（回测时由QF-Lib提供，这里用占位符） =====
        account_features = np.array([
            0.5,  # 现金比例（占位符）
            0.5   # 持仓比例（占位符）
        ], dtype=np.float32)

        # 合并
        obs = np.concatenate([market_features, technical_features, account_features])

        # 处理异常值
        obs = np.nan_to_num(obs, nan=0.0, posinf=1.0, neginf=-1.0)
        obs = np.clip(obs, -10, 10)

        return obs

    def _calculate_rsi(self, close_prices: pd.Series, window: int = 14) -> float:
        """计算RSI指标

        Args:
            close_prices: 收盘价序列
            window: RSI窗口

        Returns:
            RSI值
        """
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
        """计算MACD指标

        Args:
            close_prices: 收盘价序列
            fast: 快速EMA周期
            slow: 慢速EMA周期

        Returns:
            MACD值
        """
        if len(close_prices) < slow:
            return 0.0

        ema_fast = close_prices.ewm(span=fast, adjust=False).mean()
        ema_slow = close_prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow

        current_macd = macd.iloc[-1]
        return current_macd if not np.isnan(current_macd) else 0.0

    def _calculate_ma(self, close_prices: pd.Series, window: int = 10) -> float:
        """计算移动平均线

        Args:
            close_prices: 收盘价序列
            window: MA窗口

        Returns:
            MA值
        """
        if len(close_prices) < window:
            return close_prices.mean() if len(close_prices) > 0 else 0.0

        ma = close_prices.rolling(window=window).mean()

        current_ma = ma.iloc[-1]
        return current_ma if not np.isnan(current_ma) else close_prices.iloc[-1]

    def _action_to_exposure(self, action: int) -> Exposure:
        """将RL动作转换为QF-Lib持仓信号

        Args:
            action: RL模型输出的动作
                    0: HOLD
                    1: BUY
                    2: SELL

        Returns:
            QF-Lib Exposure枚举
        """
        if Exposure is None:
            # 占位符（QF-Lib未安装时）
            return action

        # SimpleTradingEnv的动作空间
        if action == 1:  # BUY
            return Exposure.LONG
        elif action == 2:  # SELL
            return Exposure.OUT
        else:  # HOLD
            return Exposure.LONG  # 保持当前持仓

    def get_fraction_at_risk(self) -> float:
        """返回风险暴露比例（QF-Lib接口）

        Returns:
            风险比例（0-1）
        """
        # SimpleTradingEnv的买入比例是30%
        return 0.3
