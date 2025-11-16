#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票代码传递追踪脚本
追踪股票代码在整个系统中的传递路径，定位混淆点
"""

import os
import sys
from datetime import datetime

# 设置Windows控制台编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tradingagents.utils.logging_init import get_logger
logger = get_logger("trace")


def trace_code_flow(symbol: str, trade_date: str):
    """追踪股票代码在系统中的传递"""

    print(f"\n{'='*80}")
    print(f" 股票代码传递追踪")
    print(f"{'='*80}")
    print(f"输入股票代码: {symbol}")
    print(f"交易日期: {trade_date}")
    print(f"{'='*80}\n")

    # 1. 检查初始输入
    print("1⃣ 检查初始输入规范化")
    print("-" * 80)

    from tradingagents.utils.stock_utils import StockUtils
    market_info = StockUtils.get_market_info(symbol)

    print(f" 股票类型识别:")
    print(f"   原始代码: {symbol}")
    print(f"   市场: {market_info['market_name']}")
    print(f"   规范化代码: {market_info.get('normalized_symbol', 'N/A')}")
    print(f"   是否A股: {market_info['is_china']}")
    print(f"   是否港股: {market_info['is_hk']}")
    print(f"   是否美股: {market_info['is_us']}")

    # 2. 检查各个Agent接收到的代码
    print(f"\n2⃣ 检查各个Agent接收的股票代码")
    print("-" * 80)

    # 创建TradingGraph
    print(" 初始化TradingGraph...")
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG

    # 使用默认配置，但关闭记忆以加快速度
    test_config = DEFAULT_CONFIG.copy()
    test_config['memory_enabled'] = False

    try:
        graph = TradingAgentsGraph(
            selected_analysts=["market", "fundamentals"],  # 只测试这两个
            debug=False,
            config=test_config
        )
        print(" TradingGraph初始化成功\n")

        # 创建初始状态
        print(" 创建初始状态...")
        from tradingagents.graph.propagation import Propagator
        propagator = Propagator()
        init_state = propagator.create_initial_state(symbol, trade_date)

        print(f" 初始状态中的股票代码:")
        print(f"   company_of_interest: '{init_state.get('company_of_interest', 'NOT_FOUND')}'")
        print(f"   trade_date: '{init_state.get('trade_date', 'NOT_FOUND')}'")

        # 检查各个Agent节点
        print(f"\n3⃣ 模拟Agent节点接收参数")
        print("-" * 80)

        # 模拟市场分析师
        print("\n 市场分析师 (Market Analyst):")
        print(f"   接收到的ticker: '{init_state['company_of_interest']}'")
        print(f"   接收到的trade_date: '{init_state['trade_date']}'")

        # 检查工具调用
        from tradingagents.dataflows.interface import get_stock_market_data_unified
        print(f"\n   调用统一市场数据工具...")
        try:
            market_data = get_stock_market_data_unified(
                ticker=init_state['company_of_interest'],
                start_date='2025-10-01',
                end_date=trade_date
            )
            print(f"    市场数据获取成功，长度: {len(market_data)} 字符")

            # 检查数据中的股票代码
            if symbol in market_data or symbol.split('.')[0] in market_data:
                print(f"    数据中包含正确的股票代码")
            else:
                print(f"    警告：数据中未找到股票代码 {symbol}")

        except Exception as e:
            print(f"    市场数据获取失败: {e}")

        # 模拟基本面分析师
        print(f"\n 基本面分析师 (Fundamentals Analyst):")
        print(f"   接收到的ticker: '{init_state['company_of_interest']}'")
        print(f"   接收到的trade_date: '{init_state['trade_date']}'")

        # 检查工具调用
        from tradingagents.dataflows.interface import get_stock_fundamentals_unified
        print(f"\n   调用统一基本面数据工具...")
        try:
            fund_data = get_stock_fundamentals_unified(
                ticker=init_state['company_of_interest'],
                start_date='2025-05-01',
                end_date=trade_date,
                curr_date=trade_date
            )
            print(f"    基本面数据获取成功，长度: {len(fund_data)} 字符")

            # 提取关键指标
            if "PE" in fund_data or "市盈率" in fund_data:
                lines = fund_data.split('\n')
                for line in lines:
                    if 'PE' in line or '市盈率' in line or '每股收益' in line:
                        print(f"    {line.strip()}")

            # 检查数据中的股票代码
            if symbol in fund_data or symbol.split('.')[0] in fund_data:
                print(f"    数据中包含正确的股票代码")
            else:
                print(f"    警告：数据中未找到股票代码 {symbol}")

        except Exception as e:
            print(f"    基本面数据获取失败: {e}")

        # 4. 检查状态传递
        print(f"\n4⃣ 检查状态在Agent间的传递")
        print("-" * 80)

        # 检查状态字典中的所有与股票相关的字段
        print("\n 状态字典中的股票相关字段:")
        stock_related_keys = ['company_of_interest', 'ticker', 'symbol', 'stock_code']
        for key in stock_related_keys:
            if key in init_state:
                print(f"   {key}: '{init_state[key]}'")

        # 检查messages中是否有股票代码
        if 'messages' in init_state and init_state['messages']:
            print(f"\n Messages中的内容检查:")
            for i, msg in enumerate(init_state['messages']):
                if hasattr(msg, 'content'):
                    content = str(msg.content)
                    # 检查是否包含其他股票代码
                    if '002027' in content:
                        print(f"    Message {i} 包含错误代码 002027")
                    if symbol.split('.')[0] in content:
                        print(f"    Message {i} 包含正确代码 {symbol.split('.')[0]}")

    except Exception as e:
        print(f"\n 测试过程出错: {e}")
        import traceback
        traceback.print_exc()

    # 5. 潜在混淆点分析
    print(f"\n5⃣ 潜在股票代码混淆点分析")
    print("-" * 80)

    potential_issues = [
        {
            "位置": "propagation.py:create_initial_state",
            "风险": "初始化状态时可能使用了默认值",
            "检查": "确认company_of_interest字段正确设置"
        },
        {
            "位置": "各个Agent的node函数",
            "风险": "从state中读取ticker时字段名错误",
            "检查": "确认使用state['company_of_interest']而非硬编码"
        },
        {
            "位置": "工具调用参数传递",
            "风险": "工具调用时参数名或值传递错误",
            "检查": "确认ticker参数正确传递"
        },
        {
            "位置": "LLM生成内容",
            "风险": "LLM在分析中引用了错误的股票代码",
            "检查": "检查LLM输出中的股票代码"
        },
        {
            "位置": "风险管理器辩论",
            "风险": "风险管理器从历史记忆中引用了错误案例",
            "检查": "检查memory.get_memories()返回的内容"
        }
    ]

    print("\n可能的混淆点:")
    for i, issue in enumerate(potential_issues, 1):
        print(f"\n{i}. {issue['位置']}")
        print(f"   风险: {issue['风险']}")
        print(f"   检查: {issue['检查']}")

    # 6. 总结和建议
    print(f"\n6⃣ Root Cause 总结与Safeguards建议")
    print("-" * 80)

    print("""
 **Root Cause 分析**:

基于追踪结果，股票代码混淆可能发生在以下环节：

1. **记忆系统污染** (最可能)
   - 风险管理器使用的历史记忆(memory)可能包含其他股票的案例
   - 在检索相似案例时，错误地引用了其他股票的数据

2. **LLM幻觉** (次可能)
   - LLM在生成分析时，可能编造了不存在的数据
   - 特别是在缺乏明确数据约束时

3. **状态传递错误** (较少可能)
   - 虽然数据工具层面获取了正确数据，但在Agent间传递时可能混淆

 **建议的Safeguards**:

1. **股票代码一致性检查器**
   ```python
   def validate_stock_code_consistency(state: dict, expected_symbol: str):
       # 检查state中所有报告是否引用了正确的股票代码
       # 检查messages中是否有错误的股票代码
       # 检查LLM输出中的股票代码
   ```

2. **数据来源标注**
   ```python
   # 在每个数据点上标注：数据来源、股票代码、时间戳
   {
       "data": "PE=15.7倍",
       "source": "AKShare",
       "symbol": "300502.SZ",
       "date": "2025-09-30",
       "agent": "fundamentals_analyst"
   }
   ```

3. **Agent输出验证器**
   ```python
   def validate_agent_output(output: str, expected_symbol: str):
       # 确保输出中提到的股票代码与输入一致
       # 提取输出中的所有股票代码
       # 如果发现不一致，标记warning
   ```

4. **记忆隔离策略**
   ```python
   # 检索记忆时，过滤掉不同股票的案例
   # 或者明确标注"这是其他股票的案例，仅供参考"
   ```

5. **结构化输出强制**
   ```python
   # 使用结构化输出（如JSON schema）确保数据格式正确
   # 避免LLM自由文本生成时的数据混淆
   ```

6. **实时数据核验**
   ```python
   # 在风险管理器做决策前，重新验证关键数据点
   # 例如：PE、PB、净利润等关键指标
   ```
    """)

    print(f"\n{'='*80}")
    print(" 追踪完成")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    import sys

    # 从命令行参数获取股票代码
    symbol = sys.argv[1] if len(sys.argv) > 1 else "300502"
    trade_date = sys.argv[2] if len(sys.argv) > 2 else "2025-11-05"

    trace_code_flow(symbol, trade_date)
