"""
批量删除backend所有Python文件中的emoji

由于Windows GBK编码限制，需要删除所有会在API启动时加载的文件中的emoji
"""

import os
import re
from pathlib import Path

# Emoji pattern
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u27BF"
    "\u2705"
    "\u274C"
    "\u26A0"
    "\u2139"
    "]+",
    flags=re.UNICODE
)

def remove_emojis(text):
    """移除文本中的所有emoji"""
    return EMOJI_PATTERN.sub('', text)

def fix_all_python_files(root_dir):
    """修复目录下所有Python文件中的emoji"""
    root_path = Path(root_dir)
    fixed_count = 0
    total_count = 0

    print(f"Scanning directory: {root_path}")
    print()

    for py_file in root_path.rglob('*.py'):
        # 跳过__pycache__目录
        if '__pycache__' in str(py_file):
            continue

        total_count += 1

        try:
            # 读取文件
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 移除emoji
            fixed_content = remove_emojis(content)

            if content != fixed_content:
                # 写回文件
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)

                print(f"[FIXED] {py_file.relative_to(root_path.parent)}")
                fixed_count += 1

        except Exception as e:
            print(f"[ERROR] {py_file.relative_to(root_path.parent)}: {e}")

    return fixed_count, total_count

def main():
    print("=" * 80)
    print("Remove ALL Emojis from Backend Python Files")
    print("=" * 80)
    print()

    backend_dir = Path(__file__).parent.parent
    fixed, total = fix_all_python_files(backend_dir)

    print()
    print("=" * 80)
    print(f"Scan complete! Fixed {fixed} files out of {total} Python files")
    print("=" * 80)

if __name__ == "__main__":
    main()
