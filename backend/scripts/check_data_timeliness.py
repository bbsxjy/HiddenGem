#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据时效性诊断脚本
检查当前系统获取的财报数据是哪个时期的
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

from tradingagents.dataflows.optimized_china_data import OptimizedChinaDataProvider
from tradingagents.dataflows.akshare_utils import get_akshare_provider
from tradingagents.utils.logging_init import get_logger

logger = get_logger("data_check")


def check_data_timeliness(symbol: str = "002027.SZ"):
    """检查指定股票的数据时效性"""

    print(f"\n{'='*60}")
    print(f" 数据时效性诊断报告")
    print(f"{'='*60}")
    print(f"股票代码: {symbol}")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # 1. 检查AKShare财务数据
    print("1⃣ 检查AKShare财务数据时间范围...")
    print("-" * 60)

    try:
        akshare_provider = get_akshare_provider()

        if akshare_provider.connected:
            # 移除后缀
            clean_symbol = symbol.split('.')[0]

            # 获取财务数据
            financial_data = akshare_provider.get_financial_data(clean_symbol)

            if financial_data:
                # 检查主要财务指标的时间范围
                main_indicators = financial_data.get('main_indicators')

                if main_indicators is not None and not main_indicators.empty:
                    print("\n 主要财务指标数据可用")
                    print(f"   数据列: {list(main_indicators.columns)}")

                    # 显示最新数据期间
                    if len(main_indicators.columns) > 2:
                        latest_col = main_indicators.columns[2]
                        print(f"\n    最新数据期间: {latest_col}")

                        # 显示部分指标
                        print(f"\n   关键指标预览:")
                        for idx, row in main_indicators.head(10).iterrows():
                            indicator_name = row['指标']
                            value = row[latest_col]
                            if value != '--' and str(value) != 'nan':
                                print(f"      {indicator_name}: {value}")
                    else:
                        print("    数据列不足")
                else:
                    print("    主要财务指标为空")

                # 检查资产负债表
                balance_sheet = financial_data.get('balance_sheet', [])
                if balance_sheet is not None and not balance_sheet.empty:
                    print(f"\n 资产负债表数据可用 (共{len(balance_sheet)}条)")
                    print(f"   数据列: {list(balance_sheet.columns)[:5]}...")

                # 检查利润表
                income_statement = financial_data.get('income_statement', [])
                if income_statement is not None and not income_statement.empty:
                    print(f"\n 利润表数据可用 (共{len(income_statement)}条)")
                    print(f"   数据列: {list(income_statement.columns)[:5]}...")

                # 检查现金流量表
                cash_flow = financial_data.get('cash_flow', [])
                if cash_flow is not None and not cash_flow.empty:
                    print(f"\n 现金流量表数据可用 (共{len(cash_flow)}条)")
                    print(f"   数据列: {list(cash_flow.columns)[:5]}...")

            else:
                print("    未获取到财务数据")
        else:
            print("    AKShare未连接")

    except Exception as e:
        print(f"    检查失败: {e}")
        import traceback
        traceback.print_exc()

    # 2. 检查OptimizedChinaDataProvider生成的报告
    print(f"\n2⃣ 检查OptimizedChinaDataProvider生成的基本面报告...")
    print("-" * 60)

    try:
        analyzer = OptimizedChinaDataProvider()

        # 获取股票数据（简化版，只用于生成报告）
        stock_data = f"股票名称: 测试\n当前价格: ¥100.00"

        # 生成基本面报告
        report = analyzer._generate_fundamentals_report(symbol.split('.')[0], stock_data)

        print("\n 基本面报告生成成功")

        # 提取数据说明部分
        if "数据说明" in report:
            lines = report.split('\n')
            for i, line in enumerate(lines):
                if "数据说明" in line:
                    print(f"\n   {line}")
                    if i + 1 < len(lines):
                        print(f"   {lines[i + 1]}")
                    break

        # 提取财务指标部分
        if "##  财务指标" in report:
            lines = report.split('\n')
            in_financial_section = False
            count = 0
            for line in lines:
                if "##  财务指标" in line:
                    in_financial_section = True
                    print(f"\n   {line}")
                elif in_financial_section:
                    if line.strip().startswith('-'):
                        print(f"   {line}")
                        count += 1
                        if count >= 5:  # 只显示前5个指标
                            break
                    elif line.strip().startswith('##'):
                        break

    except Exception as e:
        print(f"    检查失败: {e}")
        import traceback
        traceback.print_exc()

    # 3. 总结
    print(f"\n3⃣ 时效性总结")
    print("-" * 60)
    print("""
财报数据时效性说明：

1. 年报数据：
   - 2024年年报通常在2025年3-4月发布
   - 这是最新的完整年度财报数据

2. 季报数据：
   - 2025年Q1（1-3月）→ 4月底发布
   - 2025年Q2（4-6月）→ 7月底发布
   - 2025年Q3（7-9月）→ 10月底发布
   - 2025年Q4（10-12月）→ 次年1月底发布

3. 当前时间（2025年11月）：
   -  应该有：2024年年报 + 2025年Q1/Q2/Q3季报
   -  不应该有：2025年Q4季报（要到2026年1月）、2025年年报（要到2026年3-4月）

4. 建议：
   - 如果分析中使用了"2024年数据"，这是合理的（最新年报）
   - 应该同时参考2025年Q3季报数据（如果可用）
   - 风险管理器不应该将"使用最新可得数据"误判为"使用过期数据"
    """)

    print(f"\n{'='*60}")
    print(" 诊断完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import sys

    # 从命令行参数获取股票代码，默认为002027.SZ（新易盛）
    symbol = sys.argv[1] if len(sys.argv) > 1 else "002027.SZ"

    check_data_timeliness(symbol)
