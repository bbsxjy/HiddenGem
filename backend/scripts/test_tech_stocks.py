#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
科技股RL Agent训练与回测测试

训练期: 2024-09-01 至 2024-09-30
回测期: 2024-10-01 至 2024-10-31

测试目标：
1. 验证修复后的SimpleTradingEnv（无Look-Ahead）
2. 对比简单回测 vs QF-Lib回测
3. 评估科技股策略性能
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np
import asyncio

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.dataflows.interface import get_stock_data_dataframe
from trading.simple_trading_env import SimpleTradingEnv

# Import stable-baselines3
try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from stable_baselines3.common.monitor import Monitor
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    print(" stable-baselines3 not installed")
    sys.exit(1)

# Import QF-Lib integration
try:
    from qflib_integration import QFLibBacktestRunner
    QFLIB_AVAILABLE = True
except ImportError:
    QFLIB_AVAILABLE = False
    print(" QF-Lib not installed, will skip QF-Lib backtest")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# 科技股列表
TECH_STOCKS = [
    "300750",  # 宁德时代 - 新能源科技
    "300059",  # 东方财富 - 金融科技
    "002475",  # 立讯精密 - 电子制造
    "300124",  # 汇川技术 - 工业自动化
]


def fetch_training_data(symbols: list, start_date: str, end_date: str) -> pd.DataFrame:
    """获取训练数据"""
    logger.info(f" 获取训练数据: {start_date} 至 {end_date}")
    logger.info(f"   股票: {', '.join(symbols)}")

    all_data = []

    for symbol in symbols:
        logger.info(f"   获取 {symbol}...")
        try:
            df = get_stock_data_dataframe(symbol, start_date, end_date)

            if df is not None and len(df) > 0:
                # 验证数据
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                if all(col in df.columns for col in required_cols):
                    # 清理数据
                    df = df.dropna(subset=required_cols)
                    df = df[(df['close'] > 0) & (df['volume'] > 0)]

                    logger.info(f"    {symbol}: {len(df)} 条记录")
                    all_data.append(df)
                else:
                    logger.warning(f"    {symbol}: 缺少必需列")
            else:
                logger.warning(f"    {symbol}: 无数据")

        except Exception as e:
            logger.error(f"    {symbol}: {e}")

    if not all_data:
        raise ValueError(" 无可用训练数据")

    # 合并数据
    combined_df = pd.concat(all_data, ignore_index=True)
    logger.info(f" 训练数据就绪: {len(combined_df)} 条记录")

    return combined_df


def train_model(train_df: pd.DataFrame, model_path: str, total_timesteps: int = 50000):
    """训练RL模型"""
    logger.info(f"\n{'='*60}")
    logger.info(f" 开始训练RL模型")
    logger.info(f"{'='*60}")
    logger.info(f"   训练数据: {len(train_df)} 条")
    logger.info(f"   训练步数: {total_timesteps:,}")
    logger.info(f"   模型路径: {model_path}")

    # 创建环境
    env = SimpleTradingEnv(
        df=train_df,
        initial_cash=100000.0,
        commission_rate=0.0003,
        max_shares=100000,
        lookback_window=10
    )
    env = Monitor(env)

    # 向量化
    vec_env = DummyVecEnv([lambda: env])
    vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=True)

    # 创建PPO模型
    logger.info(f" 初始化PPO模型...")
    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        learning_rate=0.0003,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        verbose=1
    )

    # 训练
    logger.info(f" 训练中...")
    start_time = datetime.now()

    model.learn(total_timesteps=total_timesteps, progress_bar=True)

    elapsed = datetime.now() - start_time
    logger.info(f" 训练完成！耗时: {elapsed}")

    # 保存模型
    logger.info(f" 保存模型...")
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    model.save(model_path)
    vec_env.save(model_path.replace('.zip', '_vecnormalize.pkl'))

    logger.info(f" 模型已保存")

    return model, vec_env


def simple_backtest(model, vec_env, test_df: pd.DataFrame):
    """简单回测（向量化）"""
    logger.info(f"\n{'='*60}")
    logger.info(f" 简单回测（向量化）")
    logger.info(f"{'='*60}")
    logger.info(f"   回测数据: {len(test_df)} 条")

    # 创建测试环境
    test_env = SimpleTradingEnv(
        df=test_df,
        initial_cash=100000.0,
        commission_rate=0.0003,
        max_shares=100000,
        lookback_window=10
    )
    test_env = Monitor(test_env)

    # 向量化
    test_vec_env = DummyVecEnv([lambda: test_env])
    test_vec_env = VecNormalize(test_vec_env, norm_obs=True, norm_reward=False, training=False)

    # 使用训练时的标准化参数
    test_vec_env.obs_rms = vec_env.obs_rms
    test_vec_env.ret_rms = vec_env.ret_rms

    # 运行回测
    obs = test_vec_env.reset()
    done = False
    total_reward = 0
    steps = 0

    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, info = test_vec_env.step(action)
        total_reward += reward[0]
        steps += 1

        if done[0]:
            final_value = info[0].get('final_value', 100000)
            return_pct = info[0].get('return', 0) * 100
            trades = info[0].get('trades', 0)

            logger.info(f"\n 简单回测结果:")
            logger.info(f"   初始资金: ¥100,000")
            logger.info(f"   最终价值: ¥{final_value:,.2f}")
            logger.info(f"   总收益率: {return_pct:.2f}%")
            logger.info(f"   总交易次数: {trades}")
            logger.info(f"   总步数: {steps}")

            return {
                'initial_capital': 100000,
                'final_value': final_value,
                'return_pct': return_pct,
                'total_trades': trades,
                'steps': steps
            }


async def qflib_backtest(model_path: str, symbols: list, start_date: str, end_date: str):
    """QF-Lib回测（事件驱动）"""
    if not QFLIB_AVAILABLE:
        logger.warning(" QF-Lib不可用，跳过QF-Lib回测")
        return None

    logger.info(f"\n{'='*60}")
    logger.info(f" QF-Lib回测（事件驱动，防Look-Ahead）")
    logger.info(f"{'='*60}")
    logger.info(f"   回测期: {start_date} 至 {end_date}")
    logger.info(f"   股票: {', '.join(symbols)}")

    # 获取Tushare Token
    tushare_token = os.getenv('TUSHARE_TOKEN')
    if not tushare_token:
        logger.error(" TUSHARE_TOKEN未配置")
        return None

    try:
        # 创建回测运行器
        runner = QFLibBacktestRunner(
            model_path=model_path,
            tushare_token=tushare_token,
            symbols=[f"{s}.SZ" if s.startswith('3') or s.startswith('0') else f"{s}.SH" for s in symbols],
            start_date=datetime.strptime(start_date, '%Y-%m-%d'),
            end_date=datetime.strptime(end_date, '%Y-%m-%d'),
            initial_capital=100000.0
        )

        # 运行回测
        logger.info(f" 运行QF-Lib回测...")
        results = await runner.run_async()

        logger.info(f"\n QF-Lib回测结果:")
        logger.info(f"   初始资金: ¥{results['summary']['initial_capital']:,.0f}")
        logger.info(f"   最终价值: ¥{results['summary']['final_value']:,.2f}")
        logger.info(f"   总收益率: {results['summary']['total_return']:.2%}")
        logger.info(f"   夏普比率: {results['summary']['sharpe_ratio']:.2f}")
        logger.info(f"   最大回撤: {results['summary']['max_drawdown']:.2%}")
        logger.info(f"   胜率: {results['summary']['win_rate']:.2%}")
        logger.info(f"   总交易次数: {results['summary']['total_trades']}")

        return results

    except Exception as e:
        logger.error(f" QF-Lib回测失败: {e}", exc_info=True)
        return None


def compare_results(simple_result: dict, qflib_result: dict):
    """对比两种回测结果"""
    logger.info(f"\n{'='*60}")
    logger.info(f" 回测结果对比")
    logger.info(f"{'='*60}")

    logger.info(f"\n简单回测 vs QF-Lib回测:")
    logger.info(f"{'指标':<20} {'简单回测':>15} {'QF-Lib回测':>15} {'差异':>15}")
    logger.info(f"{'-'*65}")

    if simple_result and qflib_result:
        # 收益率对比
        simple_return = simple_result['return_pct']
        qflib_return = qflib_result['summary']['total_return'] * 100
        diff_return = qflib_return - simple_return
        logger.info(f"{'总收益率 (%)':<20} {simple_return:>15.2f} {qflib_return:>15.2f} {diff_return:>15.2f}")

        # 交易次数对比
        simple_trades = simple_result['total_trades']
        qflib_trades = qflib_result['summary']['total_trades']
        diff_trades = qflib_trades - simple_trades
        logger.info(f"{'交易次数':<20} {simple_trades:>15} {qflib_trades:>15} {diff_trades:>15}")

        # 夏普比率（仅QF-Lib）
        sharpe = qflib_result['summary']['sharpe_ratio']
        logger.info(f"{'夏普比率':<20} {'-':>15} {sharpe:>15.2f} {'-':>15}")

        # 最大回撤（仅QF-Lib）
        max_dd = qflib_result['summary']['max_drawdown'] * 100
        logger.info(f"{'最大回撤 (%)':<20} {'-':>15} {max_dd:>15.2f} {'-':>15}")

        # 胜率（仅QF-Lib）
        win_rate = qflib_result['summary']['win_rate'] * 100
        logger.info(f"{'胜率 (%)':<20} {'-':>15} {win_rate:>15.2f} {'-':>15}")

        logger.info(f"\n 关键发现:")
        if abs(diff_return) > 5:
            logger.info(f"    收益率差异较大 ({diff_return:.2f}%)，这是正常的")
            logger.info(f"      - 简单回测可能高估（Look-Ahead风险）")
            logger.info(f"      - QF-Lib回测更接近实盘（事件驱动）")
        else:
            logger.info(f"    收益率差异较小 ({diff_return:.2f}%)，策略较为稳健")


async def main():
    """主测试流程"""
    logger.info("=" * 80)
    logger.info(" 科技股RL Agent训练与回测测试")
    logger.info("=" * 80)
    logger.info(f"   训练期: 2024-09-01 至 2024-09-30")
    logger.info(f"   回测期: 2024-10-01 至 2024-10-31")
    logger.info(f"   科技股: {', '.join(TECH_STOCKS)}")
    logger.info("=" * 80)

    model_path = "models/ppo_tech_test.zip"

    # Step 1: 获取训练数据
    try:
        train_df = fetch_training_data(
            symbols=TECH_STOCKS,
            start_date="2024-09-01",
            end_date="2024-09-30"
        )
    except Exception as e:
        logger.error(f" 获取训练数据失败: {e}")
        return 1

    # Step 2: 训练模型
    try:
        model, vec_env = train_model(train_df, model_path, total_timesteps=30000)
    except Exception as e:
        logger.error(f" 训练失败: {e}", exc_info=True)
        return 1

    # Step 3: 获取回测数据
    try:
        test_df = fetch_training_data(
            symbols=TECH_STOCKS,
            start_date="2024-10-01",
            end_date="2024-10-31"
        )
    except Exception as e:
        logger.error(f" 获取回测数据失败: {e}")
        return 1

    # Step 4: 简单回测
    try:
        simple_result = simple_backtest(model, vec_env, test_df)
    except Exception as e:
        logger.error(f" 简单回测失败: {e}", exc_info=True)
        simple_result = None

    # Step 5: QF-Lib回测
    qflib_result = await qflib_backtest(
        model_path=model_path,
        symbols=TECH_STOCKS,
        start_date="2024-10-01",
        end_date="2024-10-31"
    )

    # Step 6: 对比结果
    if simple_result and qflib_result:
        compare_results(simple_result, qflib_result)

    logger.info(f"\n{'='*80}")
    logger.info(f" 测试完成！")
    logger.info(f"{'='*80}")
    logger.info(f" 模型已保存: {model_path}")
    logger.info(f" 简单回测: {'完成' if simple_result else '失败'}")
    logger.info(f" QF-Lib回测: {'完成' if qflib_result else '跳过/失败'}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
