#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空所有MemoryBank数据

使用方法：
1. 先停止后端服务器
2. 运行此脚本: python scripts/clear_memory_bank.py
"""

import os
import shutil
from pathlib import Path

def clear_memory_bank():
    """清空所有memory bank数据"""
    backend_dir = Path(__file__).parent.parent
    memory_db_path = backend_dir / "memory_db"

    if not memory_db_path.exists():
        print("✅ memory_db目录不存在，无需清理")
        return

    print(f"📂 找到memory_db目录: {memory_db_path}")

    # 统计信息
    total_size = 0
    file_count = 0

    for root, dirs, files in os.walk(memory_db_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                total_size += os.path.getsize(file_path)
                file_count += 1
            except:
                pass

    print(f"📊 当前存储:")
    print(f"   - 文件数: {file_count}")
    print(f"   - 总大小: {total_size / 1024 / 1024:.2f} MB")

    # 确认删除
    confirm = input("\n⚠️  确认要删除所有memory bank数据吗？ (yes/no): ")

    if confirm.lower() != 'yes':
        print("❌ 取消删除")
        return

    # 删除目录
    try:
        shutil.rmtree(memory_db_path)
        print("✅ Memory bank已清空")
        print(f"   - 已删除: {memory_db_path}")

        # 重建空目录
        memory_db_path.mkdir(exist_ok=True)
        (memory_db_path / "maxims").mkdir(exist_ok=True)
        (memory_db_path / "episodes").mkdir(exist_ok=True)
        print("✅ 已重建空目录结构")

    except PermissionError as e:
        print(f"❌ 删除失败: {e}")
        print("\n💡 请确保:")
        print("   1. 后端服务器已停止 (uvicorn)")
        print("   2. 没有其他进程占用这些文件")
        print("   3. 以管理员权限运行此脚本")
    except Exception as e:
        print(f"❌ 删除失败: {e}")

if __name__ == "__main__":
    print("="*60)
    print("清空MemoryBank数据")
    print("="*60)
    clear_memory_bank()
