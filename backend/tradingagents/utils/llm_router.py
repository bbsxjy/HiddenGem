"""
LLM Router - Multi-tier LLM selection with fallback mechanism

提供三层LLM路由策略:
1. Small models (Qwen-Turbo, Qwen-7B) - 简单分析任务
2. Medium models (Qwen-Plus, GPT-4o-mini) - 常规分析任务
3. Large models (DeepSeek, Claude, GPT-4) - 复杂推理任务

支持自动降级/升级机制，确保任务完成质量。
"""

import os
from typing import Dict, Any, Optional, Literal
from enum import Enum
from langchain_openai import ChatOpenAI

from tradingagents.utils.logging_init import get_logger
logger = get_logger("llm_router")


class LLMTier(str, Enum):
    """LLM模型层级"""
    SMALL = "small"      # 快速简单任务（如数据格式化、模板填充）
    MEDIUM = "medium"    # 常规分析任务（如技术指标分析、基本面报告）
    LARGE = "large"      # 复杂推理任务（如多方辩论、风险决策）


class AgentComplexity(str, Enum):
    """Agent任务复杂度分类"""
    SIMPLE = "simple"       # 简单任务
    ROUTINE = "routine"     # 常规分析
    COMPLEX = "complex"     # 复杂推理


# Agent类型到复杂度的映射
AGENT_COMPLEXITY_MAP: Dict[str, AgentComplexity] = {
    # 分析师 - 常规分析
    "market": AgentComplexity.ROUTINE,
    "fundamentals": AgentComplexity.ROUTINE,
    "social": AgentComplexity.ROUTINE,
    "news": AgentComplexity.ROUTINE,

    # 研究员 - 常规分析（收集观点）
    "bull_researcher": AgentComplexity.ROUTINE,
    "bear_researcher": AgentComplexity.ROUTINE,

    # 风险分析员 - 常规分析
    "risky_analyst": AgentComplexity.ROUTINE,
    "neutral_analyst": AgentComplexity.ROUTINE,
    "safe_analyst": AgentComplexity.ROUTINE,

    # 交易员 - 简单执行
    "trader": AgentComplexity.SIMPLE,

    # 管理者/裁判 - 复杂推理
    "research_manager": AgentComplexity.COMPLEX,
    "risk_manager": AgentComplexity.COMPLEX,
}


class LLMRouter:
    """LLM路由器 - 根据任务复杂度选择合适的模型"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化LLM路由器

        Args:
            config: 配置字典，包含LLM提供商和模型名称
        """
        self.config = config
        self.llm_provider = config.get("llm_provider", "openai").lower()
        self.backend_url = config.get("backend_url", "https://api.openai.com/v1")

        # 从环境变量读取三层模型配置
        self.small_model = os.getenv("SMALL_LLM", config.get("small_llm", "gpt-4o-mini"))
        self.medium_model = os.getenv("MEDIUM_LLM", config.get("quick_think_llm", "gpt-4o-mini"))
        self.large_model = os.getenv("LARGE_LLM", config.get("deep_think_llm", "o4-mini"))

        # 是否启用小模型路由（默认false，保持向后兼容）
        self.enable_small_model_routing = os.getenv("ENABLE_SMALL_MODEL_ROUTING", "false").lower() == "true"

        # 缓存已创建的LLM实例
        self._llm_cache: Dict[str, ChatOpenAI] = {}

        logger.info(f"🤖 LLM Router initialized")
        logger.info(f"   Provider: {self.llm_provider}")
        logger.info(f"   Small model: {self.small_model}")
        logger.info(f"   Medium model: {self.medium_model}")
        logger.info(f"   Large model: {self.large_model}")
        logger.info(f"   Small model routing: {'✅ Enabled' if self.enable_small_model_routing else '❌ Disabled (backward compatible)'}")

    def _create_llm(self, model_name: str, tier: LLMTier) -> ChatOpenAI:
        """
        创建LLM实例

        Args:
            model_name: 模型名称
            tier: 模型层级

        Returns:
            ChatOpenAI实例
        """
        # 使用缓存避免重复创建
        cache_key = f"{tier}_{model_name}"
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]

        # 根据tier设置不同的temperature和max_tokens
        if tier == LLMTier.SMALL:
            temperature = 0.1  # 小模型使用低temperature，更稳定
            max_tokens = 1000  # 限制输出长度
        elif tier == LLMTier.MEDIUM:
            temperature = 0.3
            max_tokens = 2000
        else:  # LARGE
            temperature = 0.7  # 大模型使用高temperature，更有创造性
            max_tokens = 4000

        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=self.backend_url,
            streaming=False
        )

        self._llm_cache[cache_key] = llm
        logger.debug(f"✓ Created LLM: {model_name} (tier={tier}, temp={temperature})")

        return llm

    def get_llm_for_agent(
        self,
        agent_type: str,
        fallback_tier: Optional[LLMTier] = None
    ) -> ChatOpenAI:
        """
        根据Agent类型获取合适的LLM

        Args:
            agent_type: Agent类型 (market, fundamentals, research_manager, etc.)
            fallback_tier: 可选的降级层级（用于重试）

        Returns:
            ChatOpenAI实例
        """
        # 如果未启用小模型路由，使用传统逻辑（向后兼容）
        if not self.enable_small_model_routing:
            complexity = AGENT_COMPLEXITY_MAP.get(agent_type, AgentComplexity.ROUTINE)
            if complexity == AgentComplexity.COMPLEX:
                return self._create_llm(self.large_model, LLMTier.LARGE)
            else:
                return self._create_llm(self.medium_model, LLMTier.MEDIUM)

        # 启用小模型路由后的新逻辑
        complexity = AGENT_COMPLEXITY_MAP.get(agent_type, AgentComplexity.ROUTINE)

        # 如果指定了fallback_tier，使用降级后的tier
        if fallback_tier:
            tier = fallback_tier
            logger.info(f"🔄 [{agent_type}] Using fallback tier: {tier}")
        else:
            # 根据复杂度选择tier
            if complexity == AgentComplexity.SIMPLE:
                tier = LLMTier.SMALL
            elif complexity == AgentComplexity.ROUTINE:
                tier = LLMTier.MEDIUM
            else:  # COMPLEX
                tier = LLMTier.LARGE

        # 根据tier选择模型
        if tier == LLMTier.SMALL:
            model_name = self.small_model
        elif tier == LLMTier.MEDIUM:
            model_name = self.medium_model
        else:  # LARGE
            model_name = self.large_model

        logger.debug(f"📋 [{agent_type}] Routing: complexity={complexity.value}, tier={tier.value}, model={model_name}")

        return self._create_llm(model_name, tier)

    def get_llm_for_complexity(self, complexity: AgentComplexity) -> ChatOpenAI:
        """
        根据任务复杂度直接获取LLM

        Args:
            complexity: 任务复杂度

        Returns:
            ChatOpenAI实例
        """
        if complexity == AgentComplexity.SIMPLE:
            return self._create_llm(self.small_model, LLMTier.SMALL)
        elif complexity == AgentComplexity.ROUTINE:
            return self._create_llm(self.medium_model, LLMTier.MEDIUM)
        else:
            return self._create_llm(self.large_model, LLMTier.LARGE)

    def upgrade_tier(self, current_tier: LLMTier) -> Optional[LLMTier]:
        """
        获取更高一级的tier（用于降级重试）

        Args:
            current_tier: 当前tier

        Returns:
            更高一级的tier，如果已经是最高级则返回None
        """
        if current_tier == LLMTier.SMALL:
            return LLMTier.MEDIUM
        elif current_tier == LLMTier.MEDIUM:
            return LLMTier.LARGE
        else:
            return None  # Already at highest tier

    def get_quick_llm(self) -> ChatOpenAI:
        """
        获取快速LLM（用于简单任务）
        保持向后兼容
        """
        if self.enable_small_model_routing:
            return self._create_llm(self.small_model, LLMTier.SMALL)
        else:
            return self._create_llm(self.medium_model, LLMTier.MEDIUM)

    def get_deep_llm(self) -> ChatOpenAI:
        """
        获取深度思考LLM（用于复杂任务）
        保持向后兼容
        """
        return self._create_llm(self.large_model, LLMTier.LARGE)


# 全局LLM路由器实例（单例）
_global_router: Optional[LLMRouter] = None


def get_llm_router(config: Optional[Dict[str, Any]] = None) -> LLMRouter:
    """
    获取全局LLM路由器实例（单例模式）

    Args:
        config: 配置字典（仅在首次调用时需要）

    Returns:
        LLMRouter实例
    """
    global _global_router

    if _global_router is None:
        if config is None:
            raise ValueError("Config required for first-time router initialization")
        _global_router = LLMRouter(config)

    return _global_router


def reset_llm_router():
    """重置全局路由器（用于测试）"""
    global _global_router
    _global_router = None
