"""
LLM增强的交易环境

这个环境扩展了标准的交易环境，整合了：
1. TradingAgents的LLM分析信号
2. Memory系统的历史案例检索
3. CVaR风险约束的奖励函数

参考FinRL的设计理念，但针对HiddenGem系统进行了定制化。
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import logging

# 导入TradingAgents系统
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.dataflows.interface import get_stock_data_by_market
from tradingagents.utils.logging_init import get_logger

# 导入Memory系统
from memory import MemoryManager, MemoryMode

logger = get_logger("rl_env")


class LLMEnhancedTradingEnv(gym.Env):
    """LLM增强的交易环境

    整合TradingAgents的多Agent分析和Memory系统的历史经验。

    State Space:
        - 市场特征: 价格、成交量、技术指标等
        - LLM信号: TradingAgents的分析结果
        - Memory信号: 历史相似案例的统计信息

    Action Space:
        - 离散动作: [HOLD, BUY_10%, BUY_20%, SELL_10%, SELL_20%, CLOSE_ALL]

    Reward:
        - 收益奖励
        - CVaR风险惩罚
        - 交易成本
    """

    metadata = {'render.modes': ['human']}

    def __init__(
        self,
        df: pd.DataFrame,
        trading_graph: TradingAgentsGraph,
        memory_manager: MemoryManager,
        initial_cash: float = 100000.0,
        buy_cost_pct: float = 0.001,
        sell_cost_pct: float = 0.001,
        hmax: int = 100,  # 最大持仓数量
        reward_scaling: float = 1.0,
        cvar_alpha: float = 0.95,
        risk_penalty_coef: float = 0.1,
        **kwargs
    ):
        """初始化环境

        Args:
            df: 市场数据（OHLCV + 技术指标）
            trading_graph: TradingAgents图
            memory_manager: 记忆管理器
            initial_cash: 初始资金
            buy_cost_pct: 买入成本比例
            sell_cost_pct: 卖出成本比例
            hmax: 最大持仓数量
            reward_scaling: 奖励缩放系数
            cvar_alpha: CVaR阈值
            risk_penalty_coef: 风险惩罚系数
        """
        super().__init__()

        self.df = df
        self.trading_graph = trading_graph
        self.memory_manager = memory_manager

        # 交易参数
        self.initial_cash = initial_cash
        self.buy_cost_pct = buy_cost_pct
        self.sell_cost_pct = sell_cost_pct
        self.hmax = hmax
        self.reward_scaling = reward_scaling

        # 风险参数
        self.cvar_alpha = cvar_alpha
        self.risk_penalty_coef = risk_penalty_coef

        # 环境状态
        self.day = 0
        self.data = self.df.loc[self.day, :]
        self.terminal = False

        # 账户状态
        self.cash = initial_cash
        self.shares_held = 0
        self.cost_basis = 0.0
        self.total_asset = initial_cash

        # 历史记录
        self.asset_memory = [initial_cash]
        self.rewards_memory = []
        self.actions_memory = []
        self.date_memory = [self._get_date()]

        # 定义动作空间（离散）
        # 0: HOLD, 1: BUY 10%, 2: BUY 20%, 3: SELL 10%, 4: SELL 20%, 5: CLOSE ALL
        self.action_space = spaces.Discrete(6)

        # 定义观察空间（将在_get_observation中动态确定维度）
        # 暂时设置一个占位符，实际维度将在第一次observation时确定
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(100,),  # 占位符，稍后更新
            dtype=np.float32
        )

        logger.info(f" LLMEnhancedTradingEnv初始化完成")
        logger.info(f"   数据长度: {len(df)} 天")
        logger.info(f"   初始资金: ¥{initial_cash:,.2f}")
        logger.info(f"   动作空间: {self.action_space}")

    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, dict]:
        """重置环境到初始状态

        Args:
            seed: 随机种子（gymnasium标准参数）
            options: 额外选项（gymnasium标准参数）

        Returns:
            (observation, info): 初始观察和信息字典
        """
        # Set seed for reproducibility
        if seed is not None:
            np.random.seed(seed)

        self.day = 0
        self.data = self.df.loc[self.day, :]
        self.terminal = False

        self.cash = self.initial_cash
        self.shares_held = 0
        self.cost_basis = 0.0
        self.total_asset = self.initial_cash

        self.asset_memory = [self.initial_cash]
        self.rewards_memory = []
        self.actions_memory = []
        self.date_memory = [self._get_date()]

        observation = self._get_observation()
        info = {'day': self.day}

        return observation, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """执行一步交易

        Args:
            action: 动作ID (0-5)

        Returns:
            observation: 新状态
            reward: 奖励
            terminated: 是否正常结束
            truncated: 是否被截断（时间限制等）
            info: 额外信息
        """
        self.terminal = self.day >= len(self.df) - 1

        if self.terminal:
            # Episode结束
            final_asset = self._calculate_total_asset()
            return_pct = (final_asset - self.initial_cash) / self.initial_cash

            logger.info(f" Episode结束")
            logger.info(f"   最终资产: ¥{final_asset:,.2f}")
            logger.info(f"   总收益率: {return_pct:+.2%}")
            logger.info(f"   交易次数: {len(self.actions_memory)}")

            return (
                self._get_observation(),
                0.0,
                True,  # terminated
                False,  # truncated
                {
                    'final_asset': final_asset,
                    'return': return_pct,
                    'trades': len(self.actions_memory)
                }
            )

        # 记录开始状态
        begin_total_asset = self._calculate_total_asset()

        # 执行交易动作
        self._execute_action(action)

        # 前进一天
        self.day += 1
        self.data = self.df.loc[self.day, :]
        self.date_memory.append(self._get_date())

        # 计算新的总资产
        end_total_asset = self._calculate_total_asset()
        self.asset_memory.append(end_total_asset)

        # 计算奖励
        reward = self._calculate_reward(begin_total_asset, end_total_asset, action)
        self.rewards_memory.append(reward)

        # 获取新状态
        observation = self._get_observation()

        return observation, reward, False, False, {}

    def _get_observation(self) -> np.ndarray:
        """获取当前观察（状态）

        整合三部分信息：
        1. 市场基础特征
        2. TradingAgents的LLM信号
        3. Memory系统的历史信号

        Returns:
            状态向量
        """
        # 1. 市场基础特征
        market_features = self._get_market_features()

        # 2. TradingAgents LLM信号
        llm_signals = self._get_llm_signals()

        # 3. Memory历史信号
        memory_signals = self._get_memory_signals()

        # 4. 账户状态
        account_features = self._get_account_features()

        # 合并所有特征
        observation = np.concatenate([
            market_features,
            llm_signals,
            memory_signals,
            account_features
        ]).astype(np.float32)

        # 更新observation_space的形状（仅在第一次）
        if observation.shape[0] != self.observation_space.shape[0]:
            self.observation_space = spaces.Box(
                low=-np.inf,
                high=np.inf,
                shape=observation.shape,
                dtype=np.float32
            )
            logger.info(f"   Observation维度: {observation.shape[0]}")

        return observation

    def _get_market_features(self) -> np.ndarray:
        """获取市场基础特征

        Returns:
            市场特征向量
        """
        features = []

        # 价格特征
        if 'close' in self.data:
            features.append(self.data['close'])
        if 'open' in self.data:
            features.append(self.data['open'])
        if 'high' in self.data:
            features.append(self.data['high'])
        if 'low' in self.data:
            features.append(self.data['low'])

        # 成交量
        if 'volume' in self.data:
            features.append(self.data['volume'])

        # 技术指标（如果有）
        for indicator in ['macd', 'rsi_30', 'cci_30', 'dx_30']:
            if indicator in self.data:
                features.append(self.data[indicator])

        # 归一化（简单归一化，可以改进）
        features = np.array(features, dtype=np.float32)

        return features

    def _get_llm_signals(self) -> np.ndarray:
        """获取TradingAgents的LLM信号

        Returns:
            LLM信号向量 [direction, confidence, risk_score, agreement]
        """
        try:
            # 获取当前股票代码和日期
            symbol = self.df.iloc[0].get('tic', 'UNKNOWN')
            current_date = self._get_date()

            # 调用TradingAgents进行分析
            final_state, processed_signal = self.trading_graph.propagate(
                symbol,
                current_date
            )

            # 提取LLM分析结果
            llm_analysis = final_state.get('llm_analysis', {})

            # 编码方向
            direction_map = {'long': 1.0, 'hold': 0.0, 'short': -1.0}
            direction = direction_map.get(
                llm_analysis.get('recommended_direction', 'hold'),
                0.0
            )

            # 提取其他信号
            confidence = llm_analysis.get('confidence', 0.5)
            risk_score = llm_analysis.get('risk_score', 0.5)

            # 计算Agent一致性
            agent_results = final_state.get('agent_results', {})
            agreement = self._calculate_agent_agreement(agent_results)

            signals = np.array([
                direction,
                confidence,
                risk_score,
                agreement
            ], dtype=np.float32)

            return signals

        except Exception as e:
            logger.warning(f" 获取LLM信号失败: {e}")
            # 返回默认值
            return np.array([0.0, 0.5, 0.5, 0.5], dtype=np.float32)

    def _get_memory_signals(self) -> np.ndarray:
        """从Memory系统获取历史信号

        Returns:
            记忆信号向量 [avg_return, success_rate]
        """
        try:
            # 构建查询上下文
            symbol = self.df.iloc[0].get('tic', 'UNKNOWN')
            current_date = self._get_date()

            query_context = {
                'symbol': symbol,
                'date': current_date,
                'price': self.data.get('close', 0)
            }

            # 检索相似案例
            similar_episodes = self.memory_manager.retrieve_episodes(
                query_context=query_context,
                top_k=5
            )

            if len(similar_episodes) == 0:
                return np.array([0.0, 0.5], dtype=np.float32)

            # 统计相似案例的平均收益和成功率
            returns = []
            successes = []

            for episode in similar_episodes:
                if episode.outcome and episode.outcome.percentage_return is not None:
                    returns.append(episode.outcome.percentage_return)
                    successes.append(1 if episode.success else 0)

            avg_return = np.mean(returns) if len(returns) > 0 else 0.0
            success_rate = np.mean(successes) if len(successes) > 0 else 0.5

            signals = np.array([avg_return, success_rate], dtype=np.float32)

            return signals

        except Exception as e:
            logger.warning(f" 获取记忆信号失败: {e}")
            return np.array([0.0, 0.5], dtype=np.float32)

    def _get_account_features(self) -> np.ndarray:
        """获取账户状态特征

        Returns:
            账户特征向量
        """
        current_price = self.data.get('close', 0)

        # 归一化特征
        cash_ratio = self.cash / self.initial_cash
        position_ratio = (self.shares_held * current_price) / self.initial_cash if current_price > 0 else 0
        total_asset_ratio = self._calculate_total_asset() / self.initial_cash

        # 未实现盈亏比例
        unrealized_pnl_ratio = 0.0
        if self.shares_held > 0 and self.cost_basis > 0:
            unrealized_pnl_ratio = (current_price - self.cost_basis) / self.cost_basis

        features = np.array([
            cash_ratio,
            position_ratio,
            total_asset_ratio,
            unrealized_pnl_ratio,
            self.shares_held / self.hmax if self.hmax > 0 else 0  # 持仓占比
        ], dtype=np.float32)

        return features

    def _execute_action(self, action: int):
        """执行交易动作

        Args:
            action: 动作ID
                0: HOLD
                1: BUY 10%
                2: BUY 20%
                3: SELL 10%
                4: SELL 20%
                5: CLOSE ALL
        """
        self.actions_memory.append(action)

        current_price = self.data.get('close', 0)
        if current_price <= 0:
            return

        if action == 0:
            # HOLD - 不操作
            pass

        elif action in [1, 2]:
            # BUY
            position_pct = 0.1 if action == 1 else 0.2
            amount_to_invest = self.cash * position_pct
            shares_to_buy = int(amount_to_invest / current_price)

            if shares_to_buy > 0:
                cost = shares_to_buy * current_price * (1 + self.buy_cost_pct)

                if cost <= self.cash:
                    # 更新成本基础（加权平均）
                    total_shares = self.shares_held + shares_to_buy
                    self.cost_basis = (
                        (self.cost_basis * self.shares_held + current_price * shares_to_buy)
                        / total_shares
                    )

                    self.shares_held = total_shares
                    self.cash -= cost

                    logger.debug(f"   买入 {shares_to_buy} 股 @ ¥{current_price:.2f}")

        elif action in [3, 4]:
            # SELL
            position_pct = 0.1 if action == 3 else 0.2
            shares_to_sell = int(self.shares_held * position_pct)

            if shares_to_sell > 0:
                proceeds = shares_to_sell * current_price * (1 - self.sell_cost_pct)
                self.shares_held -= shares_to_sell
                self.cash += proceeds

                logger.debug(f"   卖出 {shares_to_sell} 股 @ ¥{current_price:.2f}")

        elif action == 5:
            # CLOSE ALL
            if self.shares_held > 0:
                proceeds = self.shares_held * current_price * (1 - self.sell_cost_pct)
                logger.debug(f"   全部平仓 {self.shares_held} 股 @ ¥{current_price:.2f}")

                self.shares_held = 0
                self.cash += proceeds
                self.cost_basis = 0.0

    def _calculate_total_asset(self) -> float:
        """计算总资产

        Returns:
            总资产价值
        """
        current_price = self.data.get('close', 0)
        return self.cash + self.shares_held * current_price

    def _calculate_reward(
        self,
        begin_total_asset: float,
        end_total_asset: float,
        action: int
    ) -> float:
        """计算奖励（包含CVaR风险惩罚）

        Args:
            begin_total_asset: 期初总资产
            end_total_asset: 期末总资产
            action: 采取的动作

        Returns:
            奖励值
        """
        # 1. 基础收益奖励
        portfolio_return = (end_total_asset - begin_total_asset) / begin_total_asset
        profit_reward = portfolio_return

        # 2. CVaR风险惩罚
        cvar_penalty = 0.0
        if len(self.asset_memory) >= 20:  # 需要足够的历史数据
            returns = np.diff(self.asset_memory[-20:]) / self.asset_memory[-20:-1]
            cvar_penalty = self._calculate_cvar_penalty(returns, self.cvar_alpha)

        # 3. 交易成本（已在执行时扣除，这里不重复）

        # 4. 综合奖励
        reward = (profit_reward - self.risk_penalty_coef * cvar_penalty) * self.reward_scaling

        return reward

    def _calculate_cvar_penalty(self, returns: np.ndarray, alpha: float) -> float:
        """计算CVaR惩罚

        CVaR (Conditional Value at Risk) 关注最差alpha%情况的平均损失

        Args:
            returns: 收益率序列
            alpha: CVaR阈值（如0.95表示关注最差5%）

        Returns:
            CVaR惩罚值
        """
        if len(returns) == 0:
            return 0.0

        # 只关注负收益
        negative_returns = returns[returns < 0]

        if len(negative_returns) == 0:
            return 0.0

        # 排序找到最差的(1-alpha)%
        sorted_returns = np.sort(negative_returns)
        cutoff_index = max(1, int(len(sorted_returns) * (1 - alpha)))
        worst_returns = sorted_returns[:cutoff_index]

        # CVaR = 最差情况的平均损失
        cvar = -np.mean(worst_returns)  # 取负号变为正的惩罚

        return cvar

    def _calculate_agent_agreement(self, agent_results: Dict[str, Any]) -> float:
        """计算Agent之间的一致性

        Args:
            agent_results: Agent分析结果

        Returns:
            一致性得分 (0-1)
        """
        if len(agent_results) == 0:
            return 0.5

        directions = []
        for result in agent_results.values():
            if isinstance(result, dict) and 'direction' in result:
                directions.append(result['direction'])

        if len(directions) == 0:
            return 0.5

        # 统计最多的方向
        from collections import Counter
        counter = Counter(directions)
        most_common_count = counter.most_common(1)[0][1]

        agreement = most_common_count / len(directions)
        return agreement

    def _get_date(self) -> str:
        """获取当前日期

        Returns:
            日期字符串
        """
        if 'date' in self.data:
            return str(self.data['date'])
        return datetime.now().strftime('%Y-%m-%d')

    def render(self, mode='human'):
        """渲染环境（可选）"""
        if mode == 'human':
            print(f"Day: {self.day}, Total Asset: ¥{self._calculate_total_asset():,.2f}")

    def close(self):
        """关闭环境"""
        pass
