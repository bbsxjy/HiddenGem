#!/usr/bin/env python3
"""
动态权重计算模块
根据agent的置信度、数据质量、历史表现等因素动态调整权重
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime
import math

from tradingagents.utils.logging_init import get_logger
logger = get_logger("utils.dynamic_weights")


class DynamicWeightCalculator:
    """动态权重计算器"""

    def __init__(self):
        # 基础权重（各agent的默认重要性）
        self.base_weights = {
            'technical': 0.25,      # 技术分析
            'fundamental': 0.30,    # 基本面（默认最重要）
            'sentiment': 0.20,      # 情绪分析
            'news': 0.25,           # 新闻分析
        }

        # 历史表现记录（TODO: 从数据库加载）
        self.historical_performance = {
            'technical': {'correct': 0, 'total': 0, 'accuracy': 0.5},
            'fundamental': {'correct': 0, 'total': 0, 'accuracy': 0.5},
            'sentiment': {'correct': 0, 'total': 0, 'accuracy': 0.5},
            'news': {'correct': 0, 'total': 0, 'accuracy': 0.5},
        }

    def calculate_dynamic_weights(
        self,
        agent_results: Dict[str, Any],
        market_context: Dict[str, Any] = None
    ) -> Dict[str, float]:
        """
        计算动态权重

        Args:
            agent_results: agent分析结果，格式：
                {
                    'technical': {
                        'direction': 'long',
                        'confidence': 0.8,
                        'reasoning': '...',
                        'execution_time_ms': 1500,
                        'is_error': False
                    },
                    ...
                }
            market_context: 市场环境信息（可选）

        Returns:
            动态权重字典，如: {'technical': 0.28, 'fundamental': 0.35, ...}
        """
        logger.info(f" [DynamicWeights] 开始计算动态权重")

        weights = {}

        for agent_name, result in agent_results.items():
            if agent_name not in self.base_weights:
                logger.warning(f" [DynamicWeights] 未知的agent: {agent_name}，跳过")
                continue

            # 计算各个调整因子
            confidence_factor = self._calculate_confidence_factor(result)
            quality_factor = self._calculate_quality_factor(result)
            performance_factor = self._calculate_performance_factor(agent_name)
            context_factor = self._calculate_context_factor(agent_name, market_context)

            # 综合权重 = 基础权重 × 各因子的乘积
            base_weight = self.base_weights[agent_name]
            adjusted_weight = base_weight * confidence_factor * quality_factor * performance_factor * context_factor

            weights[agent_name] = adjusted_weight

            logger.debug(
                f"  [{agent_name}] "
                f"基础={base_weight:.3f}, "
                f"置信度×{confidence_factor:.2f}, "
                f"质量×{quality_factor:.2f}, "
                f"历史×{performance_factor:.2f}, "
                f"环境×{context_factor:.2f} "
                f"→ {adjusted_weight:.3f}"
            )

        # 归一化权重（使总和=1）
        total = sum(weights.values())
        if total > 0:
            normalized_weights = {k: v / total for k, v in weights.items()}
        else:
            # 如果所有权重都是0，回退到平均权重
            logger.warning(f" [DynamicWeights] 所有权重为0，使用平均权重")
            normalized_weights = {k: 1.0 / len(weights) for k in weights.keys()}

        logger.info(f" [DynamicWeights] 归一化权重: {self._format_weights(normalized_weights)}")

        return normalized_weights

    def _calculate_confidence_factor(self, result: Dict[str, Any]) -> float:
        """
        基于agent的置信度计算因子

        置信度越高 → 权重越高
        公式: factor = 0.5 + confidence
        范围: [0.5, 1.5]
        """
        confidence = result.get('confidence', 0.5)

        # 置信度低于0.3的严重惩罚
        if confidence < 0.3:
            factor = 0.3
        # 置信度0.3-0.7正常区间
        elif confidence < 0.7:
            factor = 0.5 + confidence * 0.5
        # 置信度>0.7的奖励
        else:
            factor = 0.5 + confidence

        return factor

    def _calculate_quality_factor(self, result: Dict[str, Any]) -> float:
        """
        基于数据质量计算因子

        考虑因素：
        1. 是否出错 (is_error)
        2. 执行时间 (execution_time_ms)
        3. 推理长度 (reasoning长度)
        4. 是否有具体数据支撑

        范围: [0.2, 1.5]
        """
        # 1. 错误惩罚
        if result.get('is_error', False):
            logger.warning(f" [DynamicWeights] agent出错，质量因子降低到0.2")
            return 0.2

        factor = 1.0

        # 2. 执行时间因子（太快或太慢都不好）
        exec_time = result.get('execution_time_ms', 2000)
        if exec_time < 500:
            # 太快可能是缓存或简单分析
            factor *= 0.9
        elif exec_time > 10000:
            # 太慢可能超时或有问题
            factor *= 0.8

        # 3. 推理质量（基于文本长度和关键词）
        reasoning = result.get('reasoning', '')
        reasoning_length = len(reasoning)

        if reasoning_length < 50:
            # 推理过短，质量存疑
            factor *= 0.7
        elif reasoning_length > 500:
            # 推理详细，质量高
            factor *= 1.2

        # 4. 数据支撑检测（包含具体数字的分析更可靠）
        import re
        has_data = bool(re.search(r'\d+\.?\d*%|\d+\.\d+|PE|PB|ROE|营收|净利润', reasoning))
        if has_data:
            factor *= 1.3
            logger.debug(f"   包含具体数据，质量因子×1.3")

        # 限制范围
        factor = max(0.2, min(1.5, factor))

        return factor

    def _calculate_performance_factor(self, agent_name: str) -> float:
        """
        基于历史表现计算因子

        准确率越高 → 权重越高
        公式: factor = 0.5 + accuracy
        范围: [0.5, 1.5]

        注意：这里需要历史回测数据，当前使用默认值
        """
        performance = self.historical_performance.get(agent_name, {})
        accuracy = performance.get('accuracy', 0.5)

        # 至少要有10次记录才信任历史准确率
        total = performance.get('total', 0)
        if total < 10:
            # 数据不足，使用中性值
            return 1.0

        # 准确率转换为因子
        factor = 0.5 + accuracy

        return factor

    def _calculate_context_factor(
        self,
        agent_name: str,
        market_context: Dict[str, Any]
    ) -> float:
        """
        基于市场环境计算因子

        不同市场环境下，不同agent的重要性不同：
        - 牛市：情绪和新闻更重要
        - 熊市：基本面和风险更重要
        - 震荡市：技术分析更重要
        - 高波动：基本面最重要

        范围: [0.7, 1.3]
        """
        if not market_context:
            return 1.0  # 无市场环境信息，使用中性值

        # 获取市场特征
        volatility = market_context.get('volatility', 'normal')  # low/normal/high
        trend = market_context.get('trend', 'neutral')  # bull/bear/neutral
        risk_level = market_context.get('risk_level', 0.5)  # 0-1

        factor = 1.0

        # 根据波动率调整
        if volatility == 'high':
            # 高波动：基本面最重要，情绪最不重要
            if agent_name == 'fundamental':
                factor *= 1.3
            elif agent_name == 'sentiment':
                factor *= 0.7
        elif volatility == 'low':
            # 低波动：技术分析和情绪更重要
            if agent_name in ['technical', 'sentiment']:
                factor *= 1.2

        # 根据趋势调整
        if trend == 'bull':
            # 牛市：情绪和新闻更重要
            if agent_name in ['sentiment', 'news']:
                factor *= 1.2
            elif agent_name == 'fundamental':
                factor *= 0.9
        elif trend == 'bear':
            # 熊市：基本面和风险更重要
            if agent_name == 'fundamental':
                factor *= 1.3
            elif agent_name == 'sentiment':
                factor *= 0.8

        # 根据风险等级调整
        if risk_level > 0.7:
            # 高风险：基本面最重要
            if agent_name == 'fundamental':
                factor *= 1.2
            elif agent_name == 'sentiment':
                factor *= 0.8

        # 限制范围
        factor = max(0.7, min(1.3, factor))

        return factor

    def calculate_weighted_signal(
        self,
        agent_results: Dict[str, Any],
        market_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        基于动态权重计算加权信号

        Returns:
            {
                'direction': 'long'/'short'/'hold',
                'confidence': 0.85,
                'long_score': 0.65,
                'short_score': 0.35,
                'weights_used': {...},
                'breakdown': {...}
            }
        """
        logger.info(f" [DynamicWeights] 计算加权信号")

        # 1. 计算动态权重
        weights = self.calculate_dynamic_weights(agent_results, market_context)

        # 2. 计算加权分数
        long_score = 0.0
        short_score = 0.0
        hold_score = 0.0

        breakdown = {}

        for agent_name, result in agent_results.items():
            if agent_name not in weights:
                continue

            weight = weights[agent_name]
            direction = result.get('direction', 'hold')
            confidence = result.get('confidence', 0.5)

            # 加权分数 = 权重 × 置信度
            weighted_score = weight * confidence

            if direction == 'long':
                long_score += weighted_score
            elif direction == 'short':
                short_score += weighted_score
            else:  # hold
                hold_score += weighted_score

            breakdown[agent_name] = {
                'direction': direction,
                'confidence': confidence,
                'weight': weight,
                'weighted_score': weighted_score
            }

        # 3. 确定最终方向
        max_score = max(long_score, short_score, hold_score)

        if max_score == long_score:
            final_direction = 'long'
            final_confidence = long_score
        elif max_score == short_score:
            final_direction = 'short'
            final_confidence = short_score
        else:
            final_direction = 'hold'
            final_confidence = hold_score

        result = {
            'direction': final_direction,
            'confidence': round(final_confidence, 3),
            'long_score': round(long_score, 3),
            'short_score': round(short_score, 3),
            'hold_score': round(hold_score, 3),
            'weights_used': {k: round(v, 3) for k, v in weights.items()},
            'breakdown': breakdown
        }

        logger.info(
            f" [DynamicWeights] 加权结果: {final_direction} "
            f"(置信度={final_confidence:.2f}, "
            f"long={long_score:.2f}, short={short_score:.2f})"
        )

        return result

    def _format_weights(self, weights: Dict[str, float]) -> str:
        """格式化权重显示"""
        return ', '.join([f"{k}={v:.3f}" for k, v in weights.items()])

    def update_historical_performance(
        self,
        agent_name: str,
        was_correct: bool
    ):
        """
        更新agent的历史表现

        Args:
            agent_name: agent名称
            was_correct: 本次预测是否正确
        """
        if agent_name not in self.historical_performance:
            self.historical_performance[agent_name] = {
                'correct': 0,
                'total': 0,
                'accuracy': 0.5
            }

        perf = self.historical_performance[agent_name]
        perf['total'] += 1
        if was_correct:
            perf['correct'] += 1

        perf['accuracy'] = perf['correct'] / perf['total']

        logger.info(
            f" [DynamicWeights] 更新{agent_name}表现: "
            f"准确率={perf['accuracy']:.2%} ({perf['correct']}/{perf['total']})"
        )

        # TODO: 保存到数据库


# 全局实例
_dynamic_weight_calculator = None

def get_dynamic_weight_calculator() -> DynamicWeightCalculator:
    """获取全局动态权重计算器实例"""
    global _dynamic_weight_calculator
    if _dynamic_weight_calculator is None:
        _dynamic_weight_calculator = DynamicWeightCalculator()
    return _dynamic_weight_calculator
