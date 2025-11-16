# -*- coding: utf-8 -*-
"""
Memory Bank查看工具

查看训练过程中存储的交易经验：
1. Episodes（详细案例）- 完整的交易记录和分析
2. Maxims（经验格言）- 抽象的投资原则

Usage:
    python scripts/view_memory_bank.py --type episodes --limit 10
    python scripts/view_memory_bank.py --type maxims --agent bull
    python scripts/view_memory_bank.py --type all
"""

import os
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from pathlib import Path
import argparse
import json
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Import memory system
from memory import (
    MemoryManager,
    MemoryMode,
)

# Import default config
from tradingagents.default_config import DEFAULT_CONFIG


def print_separator(char='=', length=80):
    """打印分隔线"""
    print(char * length)


def format_episode(episode: Dict[str, Any], index: int) -> str:
    """格式化Episode显示"""
    lines = []

    lines.append(f"\n Episode #{index + 1}: {episode.get('episode_id', 'N/A')}")
    lines.append(f"    日期: {episode.get('date', 'N/A')}")
    lines.append(f"    股票: {episode.get('symbol', 'N/A')}")

    # 市场状态
    market = episode.get('market_state', {})
    if market:
        lines.append(f"    价格: {market.get('price', 0):.2f}")
        if 'volume' in market and market['volume']:
            lines.append(f"    成交量: {market['volume']:.0f}")

    # 交易结果
    outcome = episode.get('outcome', {})
    if outcome:
        action = outcome.get('action', 'N/A')
        entry = outcome.get('entry_price', 0)
        exit_price = outcome.get('exit_price', 0)
        pct_return = outcome.get('percentage_return', 0)

        # 根据收益显示不同颜色标记
        result_icon = "" if pct_return > 0 else ""

        lines.append(f"   {result_icon} 操作: {action}")
        lines.append(f"    入场价: {entry:.2f} -> 出场价: {exit_price:.2f}")
        lines.append(f"    收益: {pct_return:+.2%}")
        lines.append(f"   ⏱ 持仓: {outcome.get('holding_period_days', 0)} 天")

    # 经验总结
    lesson = episode.get('lesson', '')
    if lesson:
        lines.append(f"    经验总结:")
        # 截取前200个字符避免过长
        lines.append(f"      {lesson[:200]}...")

    # 成功标记
    success = episode.get('success', False)
    lines.append(f"   {' 状态: 成功' if success else ' 状态: 失败'}")

    return '\n'.join(lines)


def format_maxim(maxim: Dict[str, Any], agent: str, index: int) -> str:
    """格式化Maxim显示"""
    lines = []

    lines.append(f"\n Maxim #{index + 1} ({agent.upper()})")
    lines.append(f"    情境: {maxim.get('situation', 'N/A')[:100]}...")
    lines.append(f"    建议: {maxim.get('recommendation', 'N/A')[:100]}...")

    return '\n'.join(lines)


def view_episodes(memory_manager: MemoryManager, limit: int = 10):
    """查看Episodes（详细案例）"""
    print_separator()
    print(" 查看 Memory Bank - Episodes (详细交易案例)")
    print_separator()

    try:
        # 获取所有episodes
        all_episodes = memory_manager.episode_memory.get_all_episodes()

        if not all_episodes:
            print("\n 未找到任何Episodes记录")
            return

        total = len(all_episodes)
        print(f"\n 总Episodes数量: {total}")
        print(f" 显示前 {min(limit, total)} 条记录\n")

        # 按日期排序（最新的在前）
        sorted_episodes = sorted(
            all_episodes,
            key=lambda x: x.get('date', ''),
            reverse=True
        )

        # 显示episodes
        for i, episode in enumerate(sorted_episodes[:limit]):
            print(format_episode(episode, i))

        # 统计信息
        print_separator()
        print("\n 统计摘要:")

        successful = sum(1 for ep in all_episodes if ep.get('success', False))
        failed = total - successful

        print(f"    成功: {successful} ({successful/total*100:.1f}%)")
        print(f"    失败: {failed} ({failed/total*100:.1f}%)")

        # 计算平均收益
        total_return = sum(
            ep.get('outcome', {}).get('percentage_return', 0)
            for ep in all_episodes
            if 'outcome' in ep
        )
        avg_return = total_return / total if total > 0 else 0
        print(f"    平均收益: {avg_return:+.2%}")

        # 按股票分组
        symbols = {}
        for ep in all_episodes:
            symbol = ep.get('symbol', 'N/A')
            symbols[symbol] = symbols.get(symbol, 0) + 1

        print(f"\n    涉及股票:")
        for symbol, count in sorted(symbols.items(), key=lambda x: x[1], reverse=True):
            print(f"      {symbol}: {count} episodes")

    except Exception as e:
        print(f"\n 读取Episodes时出错: {e}")


def view_maxims(memory_manager: MemoryManager, agent: str = None, limit: int = 10):
    """查看Maxims（经验格言）"""
    print_separator()
    print(" 查看 Memory Bank - Maxims (经验格言)")
    print_separator()

    agents_to_check = [agent] if agent else ['bull', 'bear', 'trader', 'invest_judge', 'risk_manager']

    for agent_name in agents_to_check:
        print(f"\n Agent: {agent_name.upper()}")
        print("-" * 80)

        try:
            maxim_memory = memory_manager.maxim_memory.get(agent_name)

            if not maxim_memory:
                print(f"    未找到 {agent_name} 的记忆库")
                continue

            # 获取所有maxims
            # 注意：FinancialSituationMemory没有直接get_all方法，需要通过其他方式
            # 这里我们暂时使用一个workaround
            print(f"    {agent_name} 格言库已初始化")
            print(f"    存储路径: memory_db/maxims/{agent_name}_memory_persistent/")

        except Exception as e:
            print(f"    读取 {agent_name} 格言时出错: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='查看Memory Bank内容')

    parser.add_argument(
        '--type',
        type=str,
        choices=['episodes', 'maxims', 'all'],
        default='all',
        help='查看类型：episodes（详细案例）, maxims（格言）, all（全部）'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='显示记录数量限制（默认10）'
    )

    parser.add_argument(
        '--agent',
        type=str,
        choices=['bull', 'bear', 'trader', 'invest_judge', 'risk_manager'],
        help='查看特定Agent的格言（仅在--type=maxims时有效）'
    )

    args = parser.parse_args()

    # 初始化Memory Manager（analysis模式，只读）
    print("\n 初始化Memory Bank (只读模式)...")
    memory_manager = MemoryManager(
        mode=MemoryMode.ANALYSIS,
        config=DEFAULT_CONFIG
    )

    # 根据类型查看
    if args.type in ['episodes', 'all']:
        view_episodes(memory_manager, args.limit)

    if args.type in ['maxims', 'all']:
        view_maxims(memory_manager, args.agent, args.limit)

    print_separator()
    print("\n 查看完成！")
    print(f"\n 数据存储位置:")
    print(f"   Episodes: backend/memory_db/episodes/")
    print(f"   Maxims: backend/memory_db/maxims/")
    print()


if __name__ == "__main__":
    main()
