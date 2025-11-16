import time
import json

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")

# 导入数据验证模块
from tradingagents.utils.data_validation import (
    validate_state,
    validate_report,
    filter_and_annotate_memories
)


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:

        company_name = state["company_of_interest"]

        #  Safeguard 1: 验证状态一致性
        validation_result = validate_state(state, company_name, "risk_manager_input")
        if not validation_result['is_valid']:
            logger.error(f" [Risk Manager] 状态验证失败: {validation_result['errors']}")

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        #  Bug修复：使用正确的基本面报告
        fundamentals_report = state["fundamentals_report"]  #  修复：原来错误地使用了news_report
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"

        #  Safeguard 2: 验证基本面报告
        fund_validation = validate_report(
            fundamentals_report,
            company_name,
            "risk_manager:fundamentals_report"
        )
        if fund_validation['warnings']:
            logger.warning(f" [Risk Manager] 基本面报告验证警告: {fund_validation['warnings']}")

        # 安全检查：确保memory不为None
        if memory is not None:
            raw_memories = memory.get_memories(curr_situation, n_matches=2)

            #  Safeguard 3: 过滤并标注记忆，防止混淆不同股票的数据
            filtered_memories, past_memory_str = filter_and_annotate_memories(
                raw_memories, company_name
            )

            logger.info(f" [Risk Manager] 使用{len(filtered_memories)}条历史记忆")
        else:
            logger.warning(f" [DEBUG] memory为None，跳过历史记忆检索")
            past_memory_str = ""

        #  Safeguard 4: 提取关键财务指标用于验证
        fund_metrics = fund_validation.get('extracted_metrics', {})
        metrics_summary = ""
        if fund_metrics:
            metrics_summary = "\n**已验证的关键财务指标**（请在决策中引用这些真实数据）:\n"
            if 'pe' in fund_metrics:
                metrics_summary += f"- PE: {fund_metrics['pe']:.1f}倍\n"
            if 'pb' in fund_metrics:
                metrics_summary += f"- PB: {fund_metrics['pb']:.1f}倍\n"
            if 'roe' in fund_metrics:
                metrics_summary += f"- ROE: {fund_metrics['roe']:.1f}%\n"
            if 'eps' in fund_metrics:
                metrics_summary += f"- EPS: {fund_metrics['eps']:.2f}元\n"
            metrics_summary += "\n **重要**：请在分析中引用以上验证过的真实数据，不要编造或假设其他数值。\n"

        prompt = f"""作为风险管理委员会主席和辩论主持人，您的目标是评估三位风险分析师——激进、中性和安全/保守——之间的辩论，并确定交易员的最佳行动方案。您的决策必须产生明确的建议：买入、卖出或持有。只有在有具体论据强烈支持时才选择持有，而不是在所有方面都似乎有效时作为后备选择。力求清晰和果断。

 **当前分析时间点**: {state['trade_date']} ({state.get('trade_date_display', state['trade_date'])})
 **当前分析的股票**: {company_name}
 **重要提醒**: 你正在做 {state['trade_date']} 这一天的决策分析，所有引用的数据和结论必须基于此时间点！

{metrics_summary}

 **数据字段理解警告（避免误读）**：
在分析师报告中，特别是市场分析报告中，请注意区分以下数据类型：
1. **历史最高价/历史最低价**：指股票上市以来的历史极值（可能是几年前的价格）
2. **当日最高价/当日最低价**：仅指当天交易的价格区间
3. **单日振幅**：仅能用当日最高价和当日最低价计算，不能用历史极值

 **严重错误示例**：
-  用"历史最高¥433"和"历史最低¥176"计算出"单日振幅145%"
-  将"历史价格区间"误判为"异常波动"
-  将"接近历史最高"误判为"当日暴涨"

 **正确做法**：
- 仔细阅读报告中的数据标注（"历史" vs "当日"）
- 只用当日数据推断当日市场行为
- 历史数据仅用于长期趋势判断

决策指导原则：
1. **总结关键论点**：提取每位分析师的最强观点，重点关注与背景的相关性。
2. **提供理由**：用辩论中的直接引用和反驳论点支持您的建议。
3. **完善交易员计划**：从交易员的原始计划**{trader_plan}**开始，根据分析师的见解进行调整。
4. **从过去的错误中学习**：使用以下历史案例中的经验教训来改进决策，但**注意区分不同股票的案例，不要将其他股票的具体数据应用到{company_name}**。
5. **数据准确性**：在分析中引用具体数据时，请确保数据来自上述已验证的财务指标或分析师报告，不要编造数据。
6. **时间一致性**：所有数据和分析必须基于 {state['trade_date']} 时间点，不要混淆历史数据和当前数据。
7. **数据语义理解**：正确理解数据字段的含义，避免将"历史数据"误读为"当日数据"。

---

 **历史案例参考**（仅供借鉴经验教训，不是当前数据）：

以下是过去的案例，这些案例中的**具体数值**（如PE、PB、营收、净利润等）**不适用于当前分析**。
你只应该借鉴其中的**决策逻辑、经验教训、风险判断模式**。

 **严重警告**：
- 历史案例中的财务数据与{company_name}在{state['trade_date']}的数据**完全无关**！
- 不要将历史案例中的数值（如"营收下滑12.7%"、"净利润下滑38.4%"等）应用到当前分析！
- 历史案例可能涉及不同的股票、不同的时间点，仅供参考决策思路！

{past_memory_str if past_memory_str else "暂无相关历史案例"}

---

 **当前最新的分析报告**（这才是你应该依据的数据）：

**分析时间**: {state['trade_date']} ({state.get('trade_date_display', state['trade_date'])})
**分析目标**: {company_name}

**市场分析**：
{market_research_report}

**基本面分析**：
{fundamentals_report}

**情绪分析**：
{sentiment_report}

**新闻分析**：
{news_report}

---

交付成果：
- 明确且可操作的建议：买入、卖出或持有。
- 基于辩论和过去反思的详细推理。
- 引用的所有数据必须可追溯到上述**当前最新分析报告**或已验证指标。
- 不要引用历史案例中的具体财务数值。
- 正确理解数据字段含义，避免误读"历史数据"为"当日数据"。

---

**分析师辩论历史：**
{history}

---

专注于可操作的见解和持续改进。建立在过去经验教训的基础上，批判性地评估所有观点，确保每个决策都能带来更好的结果。请用中文撰写所有分析内容和建议。"""

        # 增强的LLM调用，包含错误处理和重试机制
        max_retries = 3
        retry_count = 0
        response_content = ""

        #  将完整的LLM通信记录到文件
        import os
        from pathlib import Path
        from datetime import datetime as dt_module

        # 创建日志目录
        log_dir = Path("llm_debug_logs")
        log_dir.mkdir(exist_ok=True)

        # 生成日志文件名（包含时间戳和股票代码）
        timestamp = dt_module.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"risk_manager_{company_name.replace('.', '_')}_{timestamp}.txt"

        # 写入完整的prompt到独立文件
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write(" [Risk Manager] LLM通信完整记录\n")
            f.write("=" * 100 + "\n")
            f.write(f" 当前分析股票: {company_name}\n")
            f.write(f" 分析时间: {state['trade_date']}\n")
            f.write(f"⏰ 记录时间: {dt_module.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 100 + "\n\n")
            f.write(" REQUEST PROMPT:\n")
            f.write("-" * 100 + "\n")
            f.write(prompt)
            f.write("\n" + "-" * 100 + "\n\n")

        #  同时记录到主日志文件（完整内容）
        logger.info(f"=" * 80)
        logger.info(f" [Risk Manager] LLM REQUEST - 完整PROMPT（已记录到主日志）")
        logger.info(f"=" * 80)
        logger.info(f" 当前分析股票: {company_name}")
        logger.info(f" 分析时间: {state['trade_date']}")
        logger.info(f"-" * 80)
        # 将完整prompt分段记录，避免单行过长
        prompt_lines = prompt.split('\n')
        for line in prompt_lines:
            logger.info(f"PROMPT| {line}")
        logger.info(f"=" * 80)

        logger.info(f" [Risk Manager] LLM通信日志也已记录到独立文件: {log_file}")

        while retry_count < max_retries:
            try:
                logger.info(f" [Risk Manager] 调用LLM生成交易决策 (尝试 {retry_count + 1}/{max_retries})")

                # 添加超时限制
                import asyncio
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(llm.invoke, prompt)
                    try:
                        response = future.result(timeout=300)  # 300秒超时（5分钟）
                    except concurrent.futures.TimeoutError:
                        logger.error(f" [Risk Manager] LLM调用超时 (300秒)")
                        raise Exception("LLM调用超时")

                if response and hasattr(response, 'content') and response.content:
                    response_content = response.content.strip()
                    if len(response_content) > 10:  # 确保响应有实质内容
                        logger.info(f" [Risk Manager] LLM调用成功，生成决策长度: {len(response_content)} 字符")

                        #  将完整的response记录到独立文件
                        with open(log_file, 'a', encoding='utf-8') as f:
                            f.write("\n" + "=" * 100 + "\n")
                            f.write(" RESPONSE CONTENT:\n")
                            f.write("-" * 100 + "\n")
                            f.write(f"响应长度: {len(response_content)} 字符\n")
                            f.write(f"尝试次数: {retry_count + 1}\n")
                            f.write(f"响应时间: {dt_module.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write("-" * 100 + "\n")
                            f.write(response_content)
                            f.write("\n" + "-" * 100 + "\n")
                            f.write("=" * 100 + "\n")

                        #  同时记录到主日志文件（完整内容）
                        logger.info(f"=" * 80)
                        logger.info(f" [Risk Manager] LLM RESPONSE - 完整响应（已记录到主日志）")
                        logger.info(f"=" * 80)
                        logger.info(f"响应长度: {len(response_content)} 字符")
                        logger.info(f"尝试次数: {retry_count + 1}")
                        logger.info(f"-" * 80)
                        # 将完整response分段记录
                        response_lines = response_content.split('\n')
                        for line in response_lines:
                            logger.info(f"RESPONSE| {line}")
                        logger.info(f"=" * 80)

                        logger.info(f" [Risk Manager] LLM响应也已记录到独立文件: {log_file}")

                        break
                    else:
                        logger.warning(f" [Risk Manager] LLM响应内容过短: {len(response_content)} 字符")
                        response_content = ""
                else:
                    logger.warning(f" [Risk Manager] LLM响应为空或无效")
                    response_content = ""

            except Exception as e:
                logger.error(f" [Risk Manager] LLM调用失败 (尝试 {retry_count + 1}): {str(e)}")
                # 记录错误到文件
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n 尝试 {retry_count + 1} 失败: {str(e)}\n")
                response_content = ""

            retry_count += 1
            if retry_count < max_retries and not response_content:
                logger.info(f" [Risk Manager] 等待2秒后重试...")
                time.sleep(2)
        
        # 如果所有重试都失败，生成默认决策
        if not response_content:
            logger.error(f" [Risk Manager] 所有LLM调用尝试失败，使用默认决策")
            response_content = f"""**默认建议：持有**

由于技术原因无法生成详细分析，基于当前市场状况和风险控制原则，建议对{company_name}采取持有策略。

**理由：**
1. 市场信息不足，避免盲目操作
2. 保持现有仓位，等待更明确的市场信号
3. 控制风险，避免在不确定性高的情况下做出激进决策

**建议：**
- 密切关注市场动态和公司基本面变化
- 设置合理的止损和止盈位
- 等待更好的入场或出场时机

注意：此为系统默认建议，建议结合人工分析做出最终决策。"""

        new_risk_debate_state = {
            "judge_decision": response_content,
            "history": risk_debate_state["history"],
            "risky_history": risk_debate_state["risky_history"],
            "safe_history": risk_debate_state["safe_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_risky_response": risk_debate_state["current_risky_response"],
            "current_safe_response": risk_debate_state["current_safe_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        logger.info(f" [Risk Manager] 最终决策生成完成，内容长度: {len(response_content)} 字符")

        #  Safeguard 5: 验证输出的一致性
        output_validation = validate_report(
            response_content,
            company_name,
            "risk_manager:output"
        )
        if not output_validation['is_valid']:
            logger.error(f" [Risk Manager] 输出验证失败: {output_validation['errors']}")
        if output_validation['warnings']:
            logger.warning(f" [Risk Manager] 输出验证警告: {output_validation['warnings']}")

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": response_content,
        }

    return risk_manager_node
