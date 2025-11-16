#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动安装GPU依赖
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """运行命令并显示输出"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"命令: {cmd}\n")

    result = subprocess.run(cmd, shell=True, capture_output=False, text=True)

    if result.returncode != 0:
        print(f"\n 失败: {description}")
        return False
    else:
        print(f"\n 成功: {description}")
        return True

def main():
    print("="*60)
    print("HiddenGem GPU环境依赖安装")
    print("="*60)

    # 获取pip路径
    conda_env = r"C:\ProgramData\miniconda3\envs\hiddengem_gpu"
    pip_path = os.path.join(conda_env, "Scripts", "pip.exe")
    python_path = os.path.join(conda_env, "python.exe")

    print(f"\nPython: {python_path}")
    print(f"Pip: {pip_path}")

    # 检查Python版本
    print("\n" + "="*60)
    print("检查Python版本")
    print("="*60)
    subprocess.run([python_path, "--version"])

    # 安装PyTorch (CUDA 12.1)
    if not run_command(
        f'"{pip_path}" install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121',
        "[1/4] 安装PyTorch GPU版本 (CUDA 12.1)"
    ):
        return 1

    # 安装stable-baselines3
    if not run_command(
        f'"{pip_path}" install stable-baselines3[extra]',
        "[2/4] 安装stable-baselines3"
    ):
        return 1

    # 安装其他依赖
    if not run_command(
        f'"{pip_path}" install gymnasium pandas numpy tushare akshare yfinance',
        "[3/4] 安装其他依赖"
    ):
        return 1

    # 验证GPU
    print("\n" + "="*60)
    print("[4/4] 验证GPU配置")
    print("="*60)

    test_code = """
import torch
print(f'PyTorch版本: {torch.__version__}')
print(f'CUDA可用: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')
else:
    print(' CUDA不可用')
"""

    result = subprocess.run([python_path, "-c", test_code], capture_output=False, text=True)

    if result.returncode == 0:
        print("\n" + "="*60)
        print(" GPU环境安装完成！")
        print("="*60)
        return 0
    else:
        print("\n" + "="*60)
        print(" GPU验证失败")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
