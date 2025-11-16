"""
Fundamental Analysis Strategy

基于基本面分析的价值投资策略
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from .strategy import BaseStrategy
import logging

logger = logging.getLogger(__name__)

# 尝试导入数据接口
try:
    from tradingagents.dataflows.optimized_china_data import OptimizedChinaDataProvider
    DATA_INTERFACE_AVAILABLE = True
except ImportError:
    DATA_INTERFACE_AVAILABLE = False
    logger.warning("OptimizedChinaDataProvider not available")


class FundamentalStrategy(BaseStrategy):
    """基本面价值投资策略

    基于财务指标进行投资决策：
    - PE（市盈率）: 低估值更有吸引力
    - PB（市净率）: 破净股票具有安全边际
    - ROE（净资产收益率）: 衡量盈利能力
    - 债务率: 评估财务风险
    - 净利率: 评估盈利质量

    买入标准（价值投资）:
    - PE < 20（合理估值）
    - PB < 3（估值不高）
    - ROE > 10%（良好盈利能力）
    - 债务率 < 70%（财务风险可控）
    - 基本面评分 >= 6.5 或 估值评分 >= 7.0

    卖出标准:
    - 估值过高（PE > 40 或 PB > 5）
    - ROE < 5%（盈利能力恶化）
    - 债务率 > 80%（财务风险增加）
    - 基本面评分 < 5.0
    """

    def __init__(
        self,
        max_pe: float = 20,
        max_pb: float = 3,
        min_roe: float = 10,
        max_debt_ratio: float = 70,
        min_fundamental_score: float = 6.5,
        min_valuation_score: float = 7.0
    ):
        super().__init__("Fundamental")

        # 买入阈值
        self.max_pe = max_pe
        self.max_pb = max_pb
        self.min_roe = min_roe
        self.max_debt_ratio = max_debt_ratio
        self.min_fundamental_score = min_fundamental_score
        self.min_valuation_score = min_valuation_score

        # 卖出阈值
        self.sell_pe = 40
        self.sell_pb = 5
        self.sell_min_roe = 5
        self.sell_max_debt = 80
        self.sell_min_score = 5.0

        self.has_position = False
        self.data_optimizer = None

        # 初始化数据接口
        if DATA_INTERFACE_AVAILABLE:
            try:
                self.data_optimizer = OptimizedChinaDataProvider()
                logger.info(" OptimizedChinaDataProvider 初始化成功")
            except Exception as e:
                logger.error(f" OptimizedChinaDataProvider 初始化失败: {e}")
                self.data_optimizer = None
        else:
            self.data_optimizer = None

    def generate_signal(
        self,
        symbol: str,
        current_data: pd.DataFrame,
        portfolio_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成基本面分析信号"""

        if self.data_optimizer is None:
            logger.warning(" 数据接口不可用，使用降级策略")
            return self._simple_fallback(current_data, portfolio_state)

        try:
            # 获取当前价格
            current_price = current_data.iloc[-1]['close']

            logger.info(f" [基本面分析] 开始分析 {symbol}")

            # 获取财务指标
            financial_metrics = self._get_financial_metrics(symbol, current_price)

            if not financial_metrics:
                logger.warning(f" 无法获取{symbol}的财务数据")
                return {'action': 'hold', 'reason': '财务数据不可用'}

            # 更新持仓状态
            self.has_position = portfolio_state.get('has_position', False)

            # 生成交易信号
            signal = self._generate_signal_from_metrics(financial_metrics)

            return signal

        except Exception as e:
            logger.error(f" 基本面分析失败: {e}")
            return self._simple_fallback(current_data, portfolio_state)

    def _get_financial_metrics(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """获取财务指标"""
        try:
            # 调用数据优化器获取财务指标
            metrics = self.data_optimizer._estimate_financial_metrics(
                symbol,
                f"¥{current_price:.2f}"
            )

            if metrics:
                logger.info(f" 获取财务指标成功: {symbol}")
                logger.debug(f"   PE={metrics.get('pe', 'N/A')}, PB={metrics.get('pb', 'N/A')}, ROE={metrics.get('roe', 'N/A')}")
                return metrics
            else:
                logger.warning(f" 财务指标返回为空: {symbol}")
                return None

        except Exception as e:
            logger.error(f" 获取财务指标失败: {e}")
            return None

    def _parse_metric_value(self, metric_str: str, default: float = None) -> float:
        """解析指标字符串为数值

        例如:
        - "15.3倍" -> 15.3
        - "12.5%" -> 12.5
        - "N/A" -> default
        """
        if not metric_str or metric_str == "N/A":
            return default

        try:
            # 移除单位并转换
            value_str = metric_str.replace("倍", "").replace("%", "").replace("（估算值）", "").strip()

            # 处理特殊情况
            if "（亏损）" in value_str or "N/A" in value_str:
                return default

            return float(value_str)
        except (ValueError, AttributeError):
            return default

    def _generate_signal_from_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """根据财务指标生成交易信号"""

        # 提取关键指标
        pe = self._parse_metric_value(metrics.get('pe', 'N/A'))
        pb = self._parse_metric_value(metrics.get('pb', 'N/A'))
        roe = self._parse_metric_value(metrics.get('roe', 'N/A'))
        debt_ratio = self._parse_metric_value(metrics.get('debt_ratio', 'N/A'))

        fundamental_score = metrics.get('fundamental_score', 5.0)
        valuation_score = metrics.get('valuation_score', 5.0)
        risk_level = metrics.get('risk_level', '中等')

        reasons = []
        buy_score = 0
        sell_score = 0

        # 1. PE 评估
        if pe is not None:
            if pe < 15:
                buy_score += 2
                reasons.append(f"PE={pe:.1f}倍（低估值）")
            elif pe < self.max_pe:
                buy_score += 1
                reasons.append(f"PE={pe:.1f}倍（合理估值）")
            elif pe > self.sell_pe:
                sell_score += 2
                reasons.append(f"PE={pe:.1f}倍（估值过高）")

        # 2. PB 评估
        if pb is not None:
            if pb < 1.5:
                buy_score += 2
                reasons.append(f"PB={pb:.2f}倍（显著低估）")
            elif pb < self.max_pb:
                buy_score += 1
                reasons.append(f"PB={pb:.2f}倍（估值合理）")
            elif pb > self.sell_pb:
                sell_score += 1
                reasons.append(f"PB={pb:.2f}倍（估值偏高）")

        # 3. ROE 评估（盈利能力）
        if roe is not None:
            if roe > 15:
                buy_score += 2
                reasons.append(f"ROE={roe:.1f}%（优秀盈利能力）")
            elif roe > self.min_roe:
                buy_score += 1
                reasons.append(f"ROE={roe:.1f}%（良好盈利能力）")
            elif roe < self.sell_min_roe:
                sell_score += 2
                reasons.append(f"ROE={roe:.1f}%（盈利能力恶化）")

        # 4. 债务率评估
        if debt_ratio is not None:
            if debt_ratio < 50:
                buy_score += 1
                reasons.append(f"债务率={debt_ratio:.1f}%（财务健康）")
            elif debt_ratio > self.sell_max_debt:
                sell_score += 1
                reasons.append(f"债务率={debt_ratio:.1f}%（财务风险高）")
            elif debt_ratio > self.max_debt_ratio:
                reasons.append(f"债务率={debt_ratio:.1f}%（财务风险较高）")

        # 5. 综合评分
        if fundamental_score >= 8:
            buy_score += 1
            reasons.append(f"基本面评分={fundamental_score:.1f}（优秀）")
        elif fundamental_score >= self.min_fundamental_score:
            buy_score += 0.5
            reasons.append(f"基本面评分={fundamental_score:.1f}（良好）")
        elif fundamental_score < self.sell_min_score:
            sell_score += 1
            reasons.append(f"基本面评分={fundamental_score:.1f}（较差）")

        if valuation_score >= self.min_valuation_score:
            buy_score += 1
            reasons.append(f"估值评分={valuation_score:.1f}（有吸引力）")

        # 6. 风险评估
        if risk_level in ['高', '极高']:
            sell_score += 0.5
            reasons.append(f"风险等级={risk_level}")

        # 决策逻辑
        if not self.has_position:
            # 没有持仓，考虑买入（价值投资需要更高的信心）
            if buy_score >= 4:  # 至少4个买入信号
                return {
                    'action': 'buy',
                    'reason': f'基本面分析 - 买入: ' + ' | '.join(reasons[:3])
                }
        else:
            # 有持仓，考虑卖出
            if sell_score >= 2:  # 2个卖出信号
                return {
                    'action': 'sell',
                    'reason': f'基本面分析 - 卖出: ' + ' | '.join(reasons[:3])
                }

        # 默认持有
        return {
            'action': 'hold',
            'reason': f'基本面分析 - 持有 (买入信号:{buy_score}, 卖出信号:{sell_score}): ' +
                     (' | '.join(reasons[:2]) if reasons else '信号不足')
        }

    def _simple_fallback(
        self,
        current_data: pd.DataFrame,
        portfolio_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """简单的降级策略"""
        self.has_position = portfolio_state.get('has_position', False)

        if not self.has_position:
            return {
                'action': 'buy',
                'reason': 'Fundamental fallback: 初始买入'
            }
        else:
            return {
                'action': 'hold',
                'reason': 'Fundamental fallback: 持有'
            }

    def on_trade(self, trade_info: Dict[str, Any]):
        """交易执行后的回调"""
        side = trade_info.get('side')
        if side == 'buy':
            self.has_position = True
        elif side == 'sell':
            self.has_position = False

    def reset(self):
        """重置策略状态"""
        self.has_position = False
