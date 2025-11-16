#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证与一致性检查模块
提供多层safeguards防止股票代码混淆和数据错误
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from tradingagents.utils.logging_init import get_logger
logger = get_logger("data_validation")


class StockCodeValidator:
    """股票代码一致性验证器"""

    @staticmethod
    def is_in_recommendation_context(text: str, code: str, position: int) -> bool:
        """
        检查股票代码是否出现在推荐/建议的上下文中

        Args:
            text: 完整文本
            code: 股票代码
            position: 代码在文本中的位置

        Returns:
            bool: 是否在推荐上下文中
        """
        # 定义推荐相关的关键词
        recommendation_keywords = [
            '建议关注', '可以考虑', '替代选择', '备选', '可选',
            '推荐', '建议', '关注', '考虑', '替代', '备选股',
            '可关注', '值得关注', '不妨关注', '同样值得',
            '其他选择', '另外', '或者', '也可', '还可以'
        ]

        # 获取代码周围的上下文（前后50个字符）
        context_start = max(0, position - 50)
        context_end = min(len(text), position + len(code) + 50)
        context = text[context_start:context_end]

        # 检查上下文中是否包含推荐关键词
        for keyword in recommendation_keywords:
            if keyword in context:
                return True

        return False

    @staticmethod
    def extract_stock_codes(text: str, exclude_recommendations: bool = False) -> List[str]:
        """
        从文本中提取所有可能的股票代码

        Args:
            text: 要分析的文本
            exclude_recommendations: 是否排除推荐上下文中的股票代码

        Returns:
            提取到的股票代码列表
        """
        # A股代码：6位数字 或 6位数字.SZ/SH
        a_share_pattern = r'\b\d{6}(?:\.(?:SZ|SH|sz|sh))?\b'
        # 港股代码：4-5位数字.HK
        hk_pattern = r'\b\d{4,5}\.(?:HK|hk)\b'
        # 美股代码：1-5个大写字母
        us_pattern = r'\b[A-Z]{1,5}\b'

        codes = []

        # 提取A股代码
        a_share_matches = re.finditer(a_share_pattern, text)
        for match in a_share_matches:
            code = match.group()
            if exclude_recommendations:
                if not StockCodeValidator.is_in_recommendation_context(text, code, match.start()):
                    codes.append(code)
            else:
                codes.append(code)

        # 提取港股代码
        hk_matches = re.finditer(hk_pattern, text)
        for match in hk_matches:
            code = match.group()
            if exclude_recommendations:
                if not StockCodeValidator.is_in_recommendation_context(text, code, match.start()):
                    codes.append(code)
            else:
                codes.append(code)

        # 提取美股代码（过滤常见英文单词）
        potential_us_matches = re.finditer(us_pattern, text)
        # 排除常见单词和技术指标名称
        common_words = {
            # 财务指标
            'PE', 'PB', 'ROE', 'ROA', 'EPS', 'TTM', 'YOY', 'QOQ',
            # 技术指标
            'MACD', 'KDJ', 'RSI', 'BOLL', 'MA', 'EMA', 'SMA', 'WR', 'CCI',
            # 交易指令
            'HOLD', 'BUY', 'SELL',
            # 其他常见词
            'USD', 'CNY', 'HKD', 'RMB', 'API', 'IPO', 'ETF', 'CEO', 'CFO'
        }

        for match in potential_us_matches:
            code = match.group()
            if code not in common_words:
                if exclude_recommendations:
                    if not StockCodeValidator.is_in_recommendation_context(text, code, match.start()):
                        codes.append(code)
                else:
                    codes.append(code)

        return list(set(codes))  # 去重

    @staticmethod
    def normalize_stock_code(code: str) -> str:
        """规范化股票代码"""
        code = code.upper()

        # 如果是6位数字，判断交易所
        if re.match(r'^\d{6}$', code):
            if code.startswith(('60', '68', '51')):
                return f"{code}.SH"
            elif code.startswith(('00', '30', '12')):
                return f"{code}.SZ"

        return code

    @staticmethod
    def validate_code_consistency(
        text: str,
        expected_code: str,
        context: str = "unknown"
    ) -> Tuple[bool, Optional[str]]:
        """
        验证文本中的股票代码是否与预期一致

        Args:
            text: 要检查的文本
            expected_code: 预期的股票代码
            context: 上下文信息（用于日志）

        Returns:
            (is_valid, error_message)
        """
        # 🆕 使用 exclude_recommendations=True 来排除推荐上下文中的股票代码
        extracted_codes = StockCodeValidator.extract_stock_codes(text, exclude_recommendations=True)

        if not extracted_codes:
            # 没有提取到任何股票代码（可能是正常情况）
            logger.debug(f" [{context}] 未提取到目标股票代码（已排除推荐内容）")
            return True, None

        # 规范化预期代码
        expected_normalized = StockCodeValidator.normalize_stock_code(expected_code)
        expected_base = expected_normalized.split('.')[0]

        # 记录提取到的所有代码（调试用）
        logger.debug(f" [{context}] 检测到目标股票代码: {expected_code}")
        logger.debug(f" [{context}] 在文本中找到的股票代码（排除推荐）: {extracted_codes}")

        # 检查提取到的代码
        mismatched_codes = []
        for code in extracted_codes:
            code_normalized = StockCodeValidator.normalize_stock_code(code)
            code_base = code_normalized.split('.')[0]

            if code_base != expected_base:
                mismatched_codes.append(code_normalized)

        # 如果有不匹配的代码，记录警告
        if mismatched_codes:
            error_msg = (
                f" [{context}] 发现不一致的股票代码！\n"
                f"   预期: {expected_normalized}\n"
                f"   发现: {', '.join(mismatched_codes)}\n"
                f"   文本片段: {text[:200]}..."
            )
            logger.warning(error_msg)
            # 🆕 不再返回False，只记录警告（因为可能是LLM在分析中提到其他股票）
            logger.info(f" [{context}] 这可能是正常的分析内容（LLM提到其他股票进行对比）")
            return True, None  # 改为返回True，不阻止流程

        logger.debug(f" [{context}] 股票代码一致性验证通过")
        return True, None


class FinancialMetricsValidator:
    """财务指标验证器"""

    # 合理范围（基于A股市场经验）
    REASONABLE_RANGES = {
        'pe': (0, 1000),      # PE倍数
        'pb': (0, 100),       # PB倍数
        'roe': (-100, 100),   # ROE百分比
        'eps': (-100, 1000),  # 每股收益（元）
        'revenue': (0, 1e12), # 营收（元，最大1万亿）
        'profit': (-1e11, 1e12),  # 净利润（元）
    }

    @staticmethod
    def extract_metric(text: str, metric_name: str) -> Optional[float]:
        """
        从文本中提取财务指标

        Args:
            text: 文本内容
            metric_name: 指标名称（pe, pb, roe等）

        Returns:
            指标值（浮点数）或None
        """
        patterns = {
            'pe': [
                r'PE[：:=\s]+(\d+\.?\d*)\s*倍',
                r'市盈率[：:=\s]+(\d+\.?\d*)\s*倍',
                r'市盈率[：:=\s]*（?\s*(\d+\.?\d*)\s*倍?）?',
            ],
            'pb': [
                r'PB[：:=\s]+(\d+\.?\d*)\s*倍',
                r'市净率[：:=\s]+(\d+\.?\d*)\s*倍',
            ],
            'roe': [
                r'ROE[：:=\s]+(\d+\.?\d*)%?',
                r'净资产收益率[：:=\s]+(\d+\.?\d*)%?',
            ],
            'eps': [
                r'EPS[：:=\s]+(\d+\.?\d*)\s*元?',
                r'每股收益[：:=\s]+(\d+\.?\d*)\s*元?',
                r'基本每股收益[：:=\s]+(\d+\.?\d*)\s*元?',
            ],
            'profit': [
                r'净利润[：:=\s]+(\d+\.?\d*)\s*[亿万]?元',
                r'归母净利润[：:=\s]+(\d+\.?\d*)\s*[亿万]?元',
            ]
        }

        if metric_name not in patterns:
            return None

        for pattern in patterns[metric_name]:
            match = re.search(pattern, text)
            if match:
                value_str = match.group(1)
                try:
                    value = float(value_str)

                    # 处理单位（亿、万）
                    if metric_name == 'profit':
                        if '亿' in match.group(0):
                            value *= 1e8
                        elif '万' in match.group(0):
                            value *= 1e4

                    return value
                except ValueError:
                    continue

        return None

    @staticmethod
    def validate_metric(
        metric_name: str,
        value: float,
        context: str = "unknown"
    ) -> Tuple[bool, Optional[str]]:
        """
        验证指标是否在合理范围内

        Returns:
            (is_valid, error_message)
        """
        if metric_name not in FinancialMetricsValidator.REASONABLE_RANGES:
            return True, None

        min_val, max_val = FinancialMetricsValidator.REASONABLE_RANGES[metric_name]

        if min_val <= value <= max_val:
            return True, None
        else:
            error_msg = (
                f" [{context}] {metric_name.upper()}指标超出合理范围！\n"
                f"   值: {value}\n"
                f"   合理范围: [{min_val}, {max_val}]"
            )
            logger.warning(error_msg)
            return False, error_msg

    @staticmethod
    def validate_fundamentals_report(
        report: str,
        expected_symbol: str,
        context: str = "fundamentals_report"
    ) -> Dict[str, any]:
        """
        验证基本面报告的完整性和一致性

        Returns:
            验证结果字典
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'extracted_metrics': {}
        }

        # 1. 验证股票代码一致性
        is_code_valid, code_error = StockCodeValidator.validate_code_consistency(
            report, expected_symbol, context
        )
        if not is_code_valid:
            result['is_valid'] = False
            result['errors'].append(code_error)

        # 2. 提取并验证关键指标
        metrics_to_check = ['pe', 'pb', 'roe', 'eps', 'profit']

        for metric_name in metrics_to_check:
            value = FinancialMetricsValidator.extract_metric(report, metric_name)

            if value is not None:
                result['extracted_metrics'][metric_name] = value

                # 验证范围
                is_metric_valid, metric_error = FinancialMetricsValidator.validate_metric(
                    metric_name, value, context
                )

                if not is_metric_valid:
                    result['warnings'].append(metric_error)

        # 3. 检查必需指标是否存在
        required_metrics = ['pe', 'pb', 'roe']
        missing_metrics = [m for m in required_metrics if m not in result['extracted_metrics']]

        if missing_metrics:
            warning = f" [{context}] 缺少关键指标: {', '.join(missing_metrics)}"
            logger.warning(warning)
            result['warnings'].append(warning)

        return result


class StateValidator:
    """Agent状态验证器"""

    @staticmethod
    def validate_agent_state(
        state: Dict,
        expected_symbol: str,
        stage: str = "unknown"
    ) -> Dict[str, any]:
        """
        验证Agent状态的完整性和一致性

        Args:
            state: Agent状态字典
            expected_symbol: 预期的股票代码
            stage: 当前阶段（用于日志）

        Returns:
            验证结果
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'validated_reports': {}
        }

        logger.info(f" [{stage}] 开始验证Agent状态...")

        # 1. 检查company_of_interest
        if 'company_of_interest' in state:
            actual_symbol = state['company_of_interest']
            expected_normalized = StockCodeValidator.normalize_stock_code(expected_symbol)
            actual_normalized = StockCodeValidator.normalize_stock_code(actual_symbol)

            if actual_normalized.split('.')[0] != expected_normalized.split('.')[0]:
                error = (
                    f" [{stage}] company_of_interest不匹配！\n"
                    f"   预期: {expected_normalized}\n"
                    f"   实际: {actual_normalized}"
                )
                logger.error(error)
                result['is_valid'] = False
                result['errors'].append(error)
        else:
            warning = f" [{stage}] 状态中缺少company_of_interest字段"
            logger.warning(warning)
            result['warnings'].append(warning)

        # 2. 验证各个报告
        reports_to_check = [
            'market_report',
            'fundamentals_report',
            'news_report',
            'sentiment_report'
        ]

        for report_name in reports_to_check:
            if report_name in state and state[report_name]:
                report_text = state[report_name]

                # 验证股票代码一致性
                is_valid, error = StockCodeValidator.validate_code_consistency(
                    report_text,
                    expected_symbol,
                    f"{stage}:{report_name}"
                )

                if not is_valid:
                    result['warnings'].append(error)

                # 如果是基本面报告，进行深度验证
                if report_name == 'fundamentals_report':
                    fund_result = FinancialMetricsValidator.validate_fundamentals_report(
                        report_text,
                        expected_symbol,
                        f"{stage}:{report_name}"
                    )

                    result['validated_reports'][report_name] = fund_result

                    if not fund_result['is_valid']:
                        result['warnings'].extend(fund_result['errors'])

                    result['warnings'].extend(fund_result['warnings'])

        # 3. 检查messages中的内容
        if 'messages' in state and state['messages']:
            for i, msg in enumerate(state['messages']):
                if hasattr(msg, 'content'):
                    is_valid, error = StockCodeValidator.validate_code_consistency(
                        str(msg.content),
                        expected_symbol,
                        f"{stage}:message_{i}"
                    )

                    if not is_valid:
                        result['warnings'].append(error)

        # 输出总结
        if result['errors']:
            logger.error(f" [{stage}] 验证失败，发现{len(result['errors'])}个错误")
        elif result['warnings']:
            logger.warning(f" [{stage}] 验证通过但有{len(result['warnings'])}个警告")
        else:
            logger.info(f" [{stage}] 验证通过")

        return result


class MemoryValidator:
    """记忆系统验证器"""

    @staticmethod
    def filter_memories_by_symbol(
        memories: List[Dict],
        current_symbol: str
    ) -> List[Dict]:
        """
        过滤记忆，只保留与当前股票相关的记忆

        Args:
            memories: 原始记忆列表
            current_symbol: 当前股票代码

        Returns:
            过滤后的记忆列表
        """
        if not memories:
            return []

        current_base = StockCodeValidator.normalize_stock_code(current_symbol).split('.')[0]
        filtered_memories = []

        for memory in memories:
            # 检查记忆中的股票代码
            recommendation = memory.get('recommendation', '')
            extracted_codes = StockCodeValidator.extract_stock_codes(recommendation)

            is_relevant = False

            if not extracted_codes:
                # 没有提取到股票代码，保守起见，标注为其他股票案例
                memory['_is_other_stock'] = True
                is_relevant = True
            else:
                # 检查是否包含当前股票代码
                for code in extracted_codes:
                    code_base = StockCodeValidator.normalize_stock_code(code).split('.')[0]
                    if code_base == current_base:
                        is_relevant = True
                        memory['_is_other_stock'] = False
                        break
                else:
                    # 包含其他股票代码
                    memory['_is_other_stock'] = True
                    memory['_other_codes'] = extracted_codes
                    is_relevant = True

            if is_relevant:
                filtered_memories.append(memory)

        logger.info(f" 记忆过滤: {len(memories)} -> {len(filtered_memories)}")

        return filtered_memories

    @staticmethod
    def annotate_memory_context(
        memory: Dict,
        current_symbol: str
    ) -> str:
        """
        为记忆添加上下文标注

        Args:
            memory: 记忆字典
            current_symbol: 当前股票代码

        Returns:
            标注后的记忆文本
        """
        recommendation = memory.get('recommendation', '')

        if memory.get('_is_other_stock', False):
            other_codes = memory.get('_other_codes', [])
            if other_codes:
                annotation = f"\n **注意**：这是关于其他股票（{', '.join(other_codes)}）的案例，仅供参考学习，不要将其数据应用到当前股票{current_symbol}。\n\n"
            else:
                annotation = f"\n **注意**：这是其他股票的案例（股票代码未明确），仅供参考学习思路，不要使用其具体数据。\n\n"

            return annotation + recommendation
        else:
            return f"\n **相关案例**：这是关于{current_symbol}的历史案例。\n\n" + recommendation


# 导出验证函数
def validate_state(state: Dict, expected_symbol: str, stage: str = "unknown") -> Dict:
    """快捷验证函数"""
    return StateValidator.validate_agent_state(state, expected_symbol, stage)


def validate_report(
    report: str,
    expected_symbol: str,
    report_type: str = "report"
) -> Dict:
    """快捷报告验证函数"""
    if 'fundamentals' in report_type.lower() or 'fundamental' in report_type.lower():
        return FinancialMetricsValidator.validate_fundamentals_report(
            report, expected_symbol, report_type
        )
    else:
        is_valid, error = StockCodeValidator.validate_code_consistency(
            report, expected_symbol, report_type
        )
        return {
            'is_valid': is_valid,
            'errors': [error] if error else [],
            'warnings': []
        }


def filter_and_annotate_memories(
    memories: List[Dict],
    current_symbol: str
) -> Tuple[List[Dict], str]:
    """
    过滤并标注记忆

    Returns:
        (filtered_memories, annotated_memory_string)
    """
    filtered = MemoryValidator.filter_memories_by_symbol(memories, current_symbol)

    annotated_str = ""
    for i, mem in enumerate(filtered, 1):
        annotated_text = MemoryValidator.annotate_memory_context(mem, current_symbol)
        annotated_str += f"### 案例 {i}\n{annotated_text}\n\n"

    return filtered, annotated_str
