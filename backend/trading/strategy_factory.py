"""
Strategy Factory

创建和管理不同的策略组合模式
"""

from typing import Dict, List, Any
import logging
from .strategy import BaseStrategy
from .rl_strategy import RLStrategy
from .multi_agent_strategy import MultiAgentStrategy

logger = logging.getLogger(__name__)


class StrategyMode:
    """策略模式定义"""

    # 5种预定义策略模式
    RL_ONLY = "rl_only"
    LLM_AGENT_ONLY = "llm_agent_only"
    LLM_MEMORY = "llm_memory"
    RL_LLM = "rl_llm"
    RL_LLM_MEMORY = "rl_llm_memory"

    @classmethod
    def get_all_modes(cls) -> List[str]:
        """获取所有策略模式"""
        return [
            cls.RL_ONLY,
            cls.LLM_AGENT_ONLY,
            cls.LLM_MEMORY,
            cls.RL_LLM,
            cls.RL_LLM_MEMORY,
        ]

    @classmethod
    def get_mode_info(cls, mode_id: str) -> Dict[str, Any]:
        """获取策略模式信息"""
        mode_info = {
            cls.RL_ONLY: {
                "name": "单RL模型",
                "description": "纯强化学习决策，基于历史数据训练的PPO模型",
                "components": ["RL"],
                "use_rl": True,
                "use_llm": False,
                "use_memory": False,
            },
            cls.LLM_AGENT_ONLY: {
                "name": "单LLM Agent",
                "description": "多Agent智能分析系统，7个专业分析师协同决策",
                "components": ["LLM Agent"],
                "use_rl": False,
                "use_llm": True,
                "use_memory": False,
            },
            cls.LLM_MEMORY: {
                "name": "LLM + Memory Bank",
                "description": "LLM分析结合历史案例记忆库，从相似场景中学习",
                "components": ["LLM Agent", "Memory Bank"],
                "use_rl": False,
                "use_llm": True,
                "use_memory": True,
            },
            cls.RL_LLM: {
                "name": "RL + LLM",
                "description": "强化学习与LLM双重验证，提高决策准确性",
                "components": ["RL", "LLM Agent"],
                "use_rl": True,
                "use_llm": True,
                "use_memory": False,
            },
            cls.RL_LLM_MEMORY: {
                "name": "RL + LLM + Memory",
                "description": "完整系统：强化学习 + LLM分析 + 历史案例，三重保障",
                "components": ["RL", "LLM Agent", "Memory Bank"],
                "use_rl": True,
                "use_llm": True,
                "use_memory": True,
            },
        }
        return mode_info.get(mode_id, {})


class CombinedStrategy(BaseStrategy):
    """组合策略

    根据策略模式配置，组合不同的策略进行决策
    """

    def __init__(
        self,
        mode_id: str,
        rl_model_path: str = "models/production/final_model.zip"
    ):
        """初始化组合策略

        Args:
            mode_id: 策略模式ID
            rl_model_path: RL模型路径
        """
        mode_info = StrategyMode.get_mode_info(mode_id)
        super().__init__(mode_info.get("name", mode_id))

        self.mode_id = mode_id
        self.mode_info = mode_info
        self.has_position = False

        # 初始化子策略
        self.rl_strategy = None
        self.llm_strategy = None

        if mode_info.get("use_rl", False):
            try:
                self.rl_strategy = RLStrategy(model_path=rl_model_path)
                logger.info(f"✓ [{self.name}] RL策略已加载")
            except Exception as e:
                logger.error(f"✗ [{self.name}] RL策略加载失败: {e}")
                self.rl_strategy = None

        if mode_info.get("use_llm", False):
            try:
                self.llm_strategy = MultiAgentStrategy()
                logger.info(f"✓ [{self.name}] LLM Agent策略已加载")
            except Exception as e:
                logger.error(f"✗ [{self.name}] LLM Agent策略加载失败: {e}", exc_info=True)
                self.llm_strategy = None

        # TODO: 如果需要Memory Bank，在这里初始化
        if mode_info.get("use_memory", False):
            logger.info(f"ℹ [{self.name}] Memory Bank功能待实现")

    def generate_signal(
        self,
        symbol: str,
        current_data,
        portfolio_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成交易信号

        根据策略模式，组合不同策略的决策
        """
        self.has_position = portfolio_state.get('has_position', False)

        # 收集各个策略的信号
        signals = []

        # 记录哪些策略被调用
        available_strategies = []
        if self.rl_strategy:
            available_strategies.append("RL")
        if self.llm_strategy:
            available_strategies.append("LLM")

        logger.info(f"📊 [{self.name}] {symbol} - 可用策略: {available_strategies}")

        # RL策略信号
        if self.rl_strategy:
            try:
                rl_signal = self.rl_strategy.generate_signal(symbol, current_data, portfolio_state)
                signals.append({
                    "strategy": "RL",
                    "signal": rl_signal,
                    "weight": 1.0
                })
                logger.info(f"  ✓ RL信号: {rl_signal.get('action')} - {rl_signal.get('reason', '')[:50]}")
            except Exception as e:
                logger.error(f"✗ [{self.name}] RL策略生成信号失败: {e}")

        # LLM Agent策略信号
        if self.llm_strategy:
            try:
                llm_signal = self.llm_strategy.generate_signal(symbol, current_data, portfolio_state)
                signals.append({
                    "strategy": "LLM Agent",
                    "signal": llm_signal,
                    "weight": 1.0
                })
                logger.info(f"  ✓ LLM信号: {llm_signal.get('action')} - {llm_signal.get('reason', '')[:50]}")
            except Exception as e:
                logger.error(f"✗ [{self.name}] LLM策略生成信号失败: {e}", exc_info=True)

        # 如果没有任何信号，返回hold
        if not signals:
            logger.warning(f"⚠️ [{self.name}] {symbol} - 无可用信号，返回hold")
            return {
                'action': 'hold',
                'reason': f'[{self.name}] 无可用策略'
            }

        # 单一策略模式：直接返回
        if len(signals) == 1:
            signal = signals[0]["signal"]
            signal['reason'] = f'[{self.name}] {signal.get("reason", "")}'
            logger.info(f"  → 单策略决策: {signal['action']}")
            return signal

        # 多策略组合：使用投票机制
        logger.info(f"  → 开始多策略投票 ({len(signals)}个信号)")
        return self._combine_signals(signals)

    def _combine_signals(self, signals: List[Dict]) -> Dict[str, Any]:
        """组合多个策略的信号

        使用加权投票机制
        """
        # 统计各个action的权重
        action_weights = {
            'buy': 0.0,
            'sell': 0.0,
            'hold': 0.0
        }

        reasons = []

        for sig in signals:
            strategy_name = sig["strategy"]
            signal = sig["signal"]
            weight = sig["weight"]
            action = signal.get('action', 'hold')

            action_weights[action] += weight
            reasons.append(f"{strategy_name}:{action}")

        # 选择权重最高的action
        final_action = max(action_weights, key=action_weights.get)

        logger.info(f"  → 投票结果: {action_weights}")
        logger.info(f"  → 最终决策: {final_action}")

        # 生成最终信号
        return {
            'action': final_action,
            'reason': f'[{self.name}] 组合决策({", ".join(reasons)}) -> {final_action}',
            'confidence': action_weights[final_action] / len(signals),  # 归一化置信度
            'details': {
                'vote_results': action_weights,
                'component_signals': [s["signal"] for s in signals]
            }
        }

    def on_trade(self, trade_info: Dict[str, Any]):
        """交易执行后的回调"""
        side = trade_info.get('side')
        if side == 'buy':
            self.has_position = True
        elif side == 'sell':
            self.has_position = False

        # 传递给子策略
        if self.rl_strategy:
            self.rl_strategy.on_trade(trade_info)
        if self.llm_strategy:
            self.llm_strategy.on_trade(trade_info)

    def reset(self):
        """重置策略状态"""
        self.has_position = False
        if self.rl_strategy:
            self.rl_strategy.reset()
        if self.llm_strategy:
            self.llm_strategy.reset()


class StrategyFactory:
    """策略工厂

    创建和管理策略实例
    """

    @staticmethod
    def create_strategy(
        mode_id: str,
        rl_model_path: str = "models/production/final_model.zip"
    ) -> BaseStrategy:
        """创建策略实例

        Args:
            mode_id: 策略模式ID
            rl_model_path: RL模型路径

        Returns:
            策略实例
        """
        if mode_id not in StrategyMode.get_all_modes():
            logger.warning(f"⚠ 未知的策略模式: {mode_id}，使用默认RL策略")
            mode_id = StrategyMode.RL_ONLY

        logger.info(f"📊 创建策略: {StrategyMode.get_mode_info(mode_id)['name']}")

        return CombinedStrategy(
            mode_id=mode_id,
            rl_model_path=rl_model_path
        )

    @staticmethod
    def create_multi_strategies(
        mode_ids: List[str],
        rl_model_path: str = "models/production/final_model.zip"
    ) -> Dict[str, BaseStrategy]:
        """创建多个策略实例

        Args:
            mode_ids: 策略模式ID列表
            rl_model_path: RL模型路径

        Returns:
            策略字典 {mode_id: strategy}
        """
        strategies = {}

        for mode_id in mode_ids:
            try:
                strategy = StrategyFactory.create_strategy(mode_id, rl_model_path)
                strategies[mode_id] = strategy
            except Exception as e:
                logger.error(f"✗ 创建策略 {mode_id} 失败: {e}")

        logger.info(f"✓ 成功创建 {len(strategies)} 个策略")
        return strategies
