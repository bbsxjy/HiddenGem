"""
Remove All Emojis from Backend Files

修复Windows GBK编码问题：删除所有启动文件中的emoji
"""

import os
import re
from pathlib import Path

# 需要处理的文件
FILES_TO_FIX = [
    "tradingagents/llm_adapters/google_openai_adapter.py",
    "api/routers/agents.py",
    "tradingagents/graph/trading_graph.py",
    "tradingagents/utils/rate_limiter.py",
    "tradingagents/agents/utils/memory.py",  # Added: memory system emojis
]

# Emoji pattern (most common emojis used in logs)
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # 各种表情
    "\U0001F1E0-\U0001F1FF"  # 国旗
    "\U00002600-\U000027BF"  # 杂项符号
    "\U0000FE00-\U0000FE0F"  # 变体选择器
    "\U0001F900-\U0001F9FF"  # 补充符号和象形文字
    "\U0001FA70-\U0001FAFF"  # 符号和象形文字扩展-A
    "\u2600-\u27BF"  # 其他符号
    "\u2705"  # 
    "\u274C"  # 
    "\u26A0"  # 
    "\u2139"  # 
    "]+",
    flags=re.UNICODE
)

def remove_emojis(text):
    """移除文本中的所有emoji"""
    return EMOJI_PATTERN.sub('', text)

def fix_file(file_path):
    """修复单个文件"""
    full_path = Path(__file__).parent.parent / file_path

    if not full_path.exists():
        print(f"[SKIP] File not found: {file_path}")
        return False

    try:
        # 读取文件
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 移除emoji
        fixed_content = remove_emojis(content)

        if content == fixed_content:
            print(f"[OK] No changes needed: {file_path}")
            return False

        # 写回文件
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        print(f"[FIXED] {file_path}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to fix {file_path}: {e}")
        return False

def main():
    print("=" * 80)
    print("Remove Emojis from Backend Files (Fix Windows GBK Encoding)")
    print("=" * 80)
    print()

    fixed_count = 0

    for file_path in FILES_TO_FIX:
        if fix_file(file_path):
            fixed_count += 1

    print()
    print("=" * 80)
    print(f"Done! Fixed {fixed_count} files")
    print("=" * 80)

if __name__ == "__main__":
    main()
