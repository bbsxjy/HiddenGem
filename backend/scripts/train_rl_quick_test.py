#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Agent Quick Test Training

快速测试训练脚本 - 单只股票，少量步数
用于验证环境和模型配置是否正确
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.train_rl_agent import RLTrainer
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """快速测试主函数"""
    logger.info(" RL Agent快速测试训练")
    logger.info("=" * 60)

    # 创建训练器（仅使用1只股票）
    trainer = RLTrainer(
        symbols=["000001"],  # 仅平安银行
        start_date="2025-01-01",
        end_date="2025-03-31",  # 仅3个月数据
        initial_cash=100000.0,
        model_save_path="models/ppo_trading_agent_test.zip"
    )

    # 快速训练（少量步数）
    try:
        logger.info(" 开始快速训练（测试模式）...")

        model = trainer.train(
            total_timesteps=10000,  # 仅1万步（正式训练建议10万+）
            learning_rate=0.0003,
            n_steps=512,  # 减小步数
            batch_size=64,
            n_epochs=5,  # 减少epoch
            gamma=0.99,
            verbose=1
        )

        logger.info("=" * 60)
        logger.info(" 快速测试完成！")
        logger.info(f" 测试模型保存到: {trainer.model_save_path}")
        logger.info("")
        logger.info(" 下一步:")
        logger.info("   1. 如果测试成功，运行完整训练:")
        logger.info("      python scripts/train_rl_agent.py")
        logger.info("   2. 然后将模型重命名为正式版本:")
        logger.info("      mv models/ppo_trading_agent.zip models/ppo_trading_agent.zip")

        return 0

    except Exception as e:
        logger.error(f" 测试失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
