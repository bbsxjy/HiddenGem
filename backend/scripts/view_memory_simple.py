# -*- coding: utf-8 -*-
"""
简化版Memory Bank查看工具（直接读取ChromaDB）

Usage:
    python scripts/view_memory_simple.py
"""

import os
import sys
import io
import json
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import chromadb


def print_separator(char='=', length=80):
    """打印分隔线"""
    print(char * length)


def view_episodes():
    """直接读取ChromaDB episodes"""
    print_separator()
    print("Memory Bank - Trading Episodes")
    print_separator()

    try:
        # 连接ChromaDB
        client = chromadb.PersistentClient(path="./memory_db/episodes")
        collection = client.get_or_create_collection(name="trading_episodes")

        # 获取总数
        count = collection.count()
        print(f"\nTotal Episodes: {count}")

        if count == 0:
            print("\n   No episodes found.")
            return

        # 获取所有数据
        results = collection.get()

        print(f"\nShowing all {count} episodes:\n")

        # 解析并显示
        episodes = []
        for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
            ep_data = json.loads(doc)
            episodes.append(ep_data)

            print(f"\n[Episode #{i + 1}]")
            print(f"  ID: {ep_data.get('episode_id', 'N/A')}")
            print(f"  Date: {ep_data.get('date', 'N/A')}")
            print(f"  Symbol: {ep_data.get('symbol', 'N/A')}")

            # Market state
            market = ep_data.get('market_state', {})
            print(f"  Price: {market.get('price', 0):.2f}")

            # Outcome
            outcome = ep_data.get('outcome')
            if outcome:
                action = outcome.get('action', 'N/A')
                entry = outcome.get('entry_price', 0)
                exit_p = outcome.get('exit_price', 0)
                pct_return = outcome.get('percentage_return', 0)

                result_icon = "  " if pct_return > 0 else "  "
                print(f"{result_icon} Action: {action}")
                print(f"  Entry: {entry:.2f} -> Exit: {exit_p:.2f}")
                print(f"  Return: {pct_return:+.2%}")
                print(f"  Holding: {outcome.get('holding_period_days', 0)} days")

            # Lesson
            lesson = ep_data.get('lesson', '')
            if lesson:
                print(f"  Lesson: {lesson[:150]}...")

            success = ep_data.get('success', False)
            print(f"  Status: {'SUCCESS' if success else 'FAILED'}")

        # Statistics
        print_separator()
        print("\nStatistics Summary:")

        successful = sum(1 for ep in episodes if ep.get('success', False))
        total = len(episodes)

        print(f"  Success: {successful}/{total} ({successful/total*100:.1%})" if total > 0 else "  No data")

        # Calculate average return
        total_return = sum(
            ep.get('outcome', {}).get('percentage_return', 0)
            for ep in episodes
            if 'outcome' in ep
        )
        avg_return = total_return / total if total > 0 else 0
        print(f"  Avg Return: {avg_return:+.2%}")

        # Group by symbol
        symbols = {}
        for ep in episodes:
            symbol = ep.get('symbol', 'N/A')
            symbols[symbol] = symbols.get(symbol, 0) + 1

        print(f"\n  Symbols:")
        for symbol, cnt in sorted(symbols.items(), key=lambda x: x[1], reverse=True):
            print(f"    {symbol}: {cnt} episodes")

    except Exception as e:
        print(f"\nError reading episodes: {e}")
        import traceback
        traceback.print_exc()


def view_maxims():
    """读取Maxims"""
    print_separator()
    print("Memory Bank - Maxims (Coarse-grained Experience)")
    print_separator()

    agents = ['bull_memory_persistent', 'bear_memory_persistent', 'trader_memory_persistent',
              'invest_judge_memory_persistent', 'risk_manager_memory_persistent']

    try:
        client = chromadb.PersistentClient(path="./memory_db/maxims")

        for agent_name in agents:
            try:
                collection = client.get_or_create_collection(name=agent_name)
                count = collection.count()

                print(f"\n[{agent_name.upper()}]")
                print(f"  Total maxims: {count}")

                if count > 0:
                    # 显示前3个
                    results = collection.get(limit=3)
                    for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
                        print(f"  Sample #{i+1}: {doc[:100]}...")

            except Exception as e:
                print(f"  Error: {e}")

    except Exception as e:
        print(f"\nError reading maxims: {e}")


def main():
    """主函数"""
    print("\n[Memory Bank Viewer]\n")

    view_episodes()
    print("\n")
    view_maxims()

    print_separator()
    print("\nData Location:")
    print("  Episodes: backend/memory_db/episodes/")
    print("  Maxims: backend/memory_db/maxims/")
    print()


if __name__ == "__main__":
    main()
