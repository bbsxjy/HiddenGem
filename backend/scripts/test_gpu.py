#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试GPU配置
"""

import torch

print("="*60)
print("GPU环境测试")
print("="*60)

print(f"PyTorch版本: {torch.__version__}")
print(f"CUDA可用: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"GPU名称: {torch.cuda.get_device_name(0)}")
    print(f"GPU数量: {torch.cuda.device_count()}")
    print(f"当前GPU: {torch.cuda.current_device()}")
    print(f"GPU显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print("\n GPU环境配置成功！可以开始训练")
else:
    print("\n CUDA不可用，将使用CPU训练")

print("="*60)
