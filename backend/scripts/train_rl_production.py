#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Production RL Training Script for HiddenGem

完整的生产级RL训练脚本
- 使用沪深300成分股
- 严格的训练/验证/测试分割
- T+1交易限制
- Walk-Forward验证
- 详细的性能报告

训练周期：
- 训练集: 2020-01-01 ~ 2022-12-31 (3年)
- 验证集: 2023-01-01 ~ 2023-12-31 (1年)
- 测试集: 2024-01-01 ~ 2024-11-12 (11个月)
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
import json
from typing import List, Dict, Tuple
import tushare as ts

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trading.enhanced_trading_env import EnhancedTradingEnv
from tradingagents.dataflows.interface import get_stock_data_dataframe

# Import stable-baselines3
try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback, BaseCallback
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    print(" stable-baselines3 not installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('train_rl_production.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ====================================================================================
# 配置参数
# ====================================================================================

CONFIG = {
    # 数据参数
    "train_start": "2020-01-01",
    "train_end":   "2024-06-30",
    "val_start":   "2024-07-01",
    "val_end":     "2024-12-31",
    "test_start":  "2025-01-01",
    "test_end":    "2025-11-12",

    # 股票池
    'use_hs300': True,  # 使用沪深300
    'max_stocks': 50,   # 训练时最多使用的股票数量（避免过多）

    # 环境参数
    'initial_cash': 100000.0,
    'commission_rate': 0.00013,
    'stamp_duty': 0.001,
    'enable_t1': True,

    # 训练参数
    'total_timesteps': 500000,  # 总训练步数
    'n_steps': 2048,
    'batch_size': 64,
    'n_epochs': 5,
    'learning_rate': 0.0003,
    'gamma': 0.995,

    # 保存路径
    'model_dir': 'models/production',
    'data_cache_dir': 'data_cache',
    'results_dir': 'results'
}


# ====================================================================================
# Progress Callback
# ====================================================================================

class ProgressCallback(BaseCallback):
    """Callback to save training progress to JSON file for API consumption"""

    def __init__(self, progress_file: str, total_timesteps: int, update_freq: int = 1000, verbose=0):
        super().__init__(verbose)
        self.progress_file = progress_file
        self.metrics_history_file = progress_file.replace('training_progress.json', 'metrics_history.json')
        self.total_timesteps = total_timesteps
        self.update_freq = update_freq
        self.start_time = None
        self.metrics_history = []  # 保存历史指标

    def _on_training_start(self) -> None:
        """Called before training starts"""
        import time
        self.start_time = time.time()
        self._save_progress()

    def _on_step(self) -> bool:
        """Called after each step"""
        if self.num_timesteps % self.update_freq == 0:
            self._save_progress()
        return True

    def _save_progress(self):
        """Save current progress to JSON file"""
        import time
        elapsed = time.time() - self.start_time if self.start_time else 0
        progress_pct = (self.num_timesteps / self.total_timesteps * 100) if self.total_timesteps > 0 else 0

        # 计算预估剩余时间
        if self.num_timesteps > 0 and elapsed > 0:
            time_per_step = elapsed / self.num_timesteps
            remaining_steps = self.total_timesteps - self.num_timesteps
            estimated_remaining = time_per_step * remaining_steps
        else:
            estimated_remaining = None

        # 从训练日志中提取指标
        ep_rew_mean = None
        ep_len_mean = None
        fps = None
        policy_loss = None
        value_loss = None
        explained_variance = None

        if hasattr(self.model, 'ep_info_buffer') and len(self.model.ep_info_buffer) > 0:
            ep_rew_mean = np.mean([ep_info['r'] for ep_info in self.model.ep_info_buffer])
            ep_len_mean = np.mean([ep_info['l'] for ep_info in self.model.ep_info_buffer])

        if hasattr(self, 'locals') and 'fps' in self.locals:
            fps = self.locals.get('fps')

        # PPO特定的loss指标
        if hasattr(self.model, 'logger') and hasattr(self.model.logger, 'name_to_value'):
            log_data = self.model.logger.name_to_value
            policy_loss = log_data.get('train/policy_gradient_loss')
            value_loss = log_data.get('train/value_loss')
            explained_variance = log_data.get('train/explained_variance')

        progress_data = {
            'timesteps': self.num_timesteps,
            'total_timesteps': self.total_timesteps,
            'progress_pct': round(progress_pct, 2),
            'elapsed_time': round(elapsed, 2),
            'estimated_remaining': round(estimated_remaining, 2) if estimated_remaining else None,
            'ep_rew_mean': round(float(ep_rew_mean), 4) if ep_rew_mean is not None else None,
            'ep_len_mean': round(float(ep_len_mean), 2) if ep_len_mean is not None else None,
            'fps': round(float(fps), 2) if fps is not None else None,
            'policy_loss': round(float(policy_loss), 6) if policy_loss is not None else None,
            'value_loss': round(float(value_loss), 6) if value_loss is not None else None,
            'explained_variance': round(float(explained_variance), 4) if explained_variance is not None else None,
            'last_update': datetime.now().isoformat()
        }

        try:
            # 写入当前进度文件
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)

            # 保存到历史记录
            metrics_point = {
                'timesteps': self.num_timesteps,
                'ep_rew_mean': progress_data['ep_rew_mean'],
                'ep_len_mean': progress_data['ep_len_mean'],
                'policy_loss': progress_data['policy_loss'],
                'value_loss': progress_data['value_loss'],
                'explained_variance': progress_data['explained_variance'],
                'fps': progress_data['fps'],
                'timestamp': progress_data['last_update']
            }
            self.metrics_history.append(metrics_point)

            # 写入历史文件（只保留最近500个数据点）
            history_to_save = self.metrics_history[-500:]
            with open(self.metrics_history_file, 'w') as f:
                json.dump(history_to_save, f, indent=2)

        except Exception as e:
            logger.warning(f"Failed to save progress file: {e}")


# ====================================================================================
# 辅助函数
# ====================================================================================

def get_hs300_stocks() -> List[str]:
    """获取沪深300成分股列表"""
    logger.info("获取沪深300成分股...")

    try:
        # 使用Tushare获取
        ts_token = os.getenv('TUSHARE_TOKEN')
        if not ts_token:
            raise ValueError("TUSHARE_TOKEN not configured")

        ts.set_token(ts_token)
        pro = ts.pro_api()

        # 获取沪深300成分
        df = pro.index_weight(index_code='399300.SZ')  # 沪深300
        stocks = df['con_code'].unique().tolist()

        # 转换格式：从"000001.SZ"格式提取代码
        stocks = [s.split('.')[0] for s in stocks]

        logger.info(f"获取到 {len(stocks)} 只沪深300成分股")
        return stocks

    except Exception as e:
        logger.error(f"获取沪深300成分股失败: {e}")
        # 如果失败，使用一些常见的蓝筹股作为备选
        logger.warning("使用备选股票列表")
        return [
            '000001',  # 平安银行
            '000002',  # 万科A
            '000063',  # 中兴通讯
            '000066',  # 中国长城
            '000333',  # 美的集团
            '000651',  # 格力电器
            '000858',  # 五粮液
            '600000',  # 浦发银行
            '600036',  # 招商银行
            '600519',  # 贵州茅台
            '600887',  # 伊利股份
            '601318',  # 中国平安
            '601398',  # 工商银行
            '601857',  # 中国石油
            '601988',  # 中国银行
        ]


def download_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """下载单只股票数据"""
    try:
        df = get_stock_data_dataframe(symbol, start_date, end_date)

        if df is None or len(df) == 0:
            return None

        # 验证必需列
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            return None

        # 清洗数据
        df = df.dropna(subset=required_cols)
        df = df[(df['close'] > 0) & (df['volume'] > 0)]

        # 至少需要30天数据（计算技术指标需要）
        if len(df) < 30:
            return None

        return df

    except Exception as e:
        logger.debug(f"下载 {symbol} 数据失败: {e}")
        return None


def prepare_training_data(
    stocks: List[str],
    start_date: str,
    end_date: str,
    cache_file: str = None
) -> List[Tuple[str, pd.DataFrame]]:
    """准备训练数据

    Returns:
        List of (symbol, dataframe) tuples
    """
    logger.info(f"准备数据: {start_date} 至 {end_date}")
    logger.info(f"股票数量: {len(stocks)}")

    # 检查缓存（已禁用以避免大JSON文件问题）
    # if cache_file and os.path.exists(cache_file):
    #     logger.info(f"从缓存加载: {cache_file}")
    #     with open(cache_file, 'r') as f:
    #         cache = json.load(f)
    #     # 重建dataframe
    #     stock_data = []
    #     for item in cache:
    #         df = pd.DataFrame(item['data'])
    #         stock_data.append((item['symbol'], df))
    #     logger.info(f"从缓存加载了 {len(stock_data)} 只股票")
    #     return stock_data

    # 下载数据
    stock_data = []
    failed = []

    for i, symbol in enumerate(stocks, 1):
        logger.info(f"[{i}/{len(stocks)}] 下载 {symbol}...")
        df = download_stock_data(symbol, start_date, end_date)

        if df is not None:
            stock_data.append((symbol, df))
            logger.info(f"   {symbol}: {len(df)} 条记录")
        else:
            failed.append(symbol)
            logger.warning(f"   {symbol}: 下载失败")

    logger.info(f"\n成功: {len(stock_data)}, 失败: {len(failed)}")

    if len(stock_data) == 0:
        raise ValueError("没有成功下载任何股票数据")

    # 保存缓存（跳过，避免大JSON文件问题）
    # if cache_file:
    #     os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    #     cache = []
    #     for symbol, df in stock_data:
    #         cache.append({
    #             'symbol': symbol,
    #             'data': df.to_dict('records')
    #         })
    #     with open(cache_file, 'w') as f:
    #         json.dump(cache, f)
    #     logger.info(f"数据已缓存: {cache_file}")
    logger.info(f"数据准备完成（已禁用缓存以避免大文件问题）")

    return stock_data


def create_combined_env(stock_data: List[Tuple[str, pd.DataFrame]], **env_kwargs):
    """创建组合环境（多只股票随机选择）"""
    # 随机选择一只股票
    import random
    symbol, df = random.choice(stock_data)

    env = EnhancedTradingEnv(df=df, **env_kwargs)
    env = Monitor(env)

    return env


def train_model(
    train_data: List[Tuple[str, pd.DataFrame]],
    val_data: List[Tuple[str, pd.DataFrame]],
    config: Dict
) -> Tuple[PPO, VecNormalize]:
    """训练RL模型"""
    logger.info("\n" + "="*80)
    logger.info("开始训练RL模型")
    logger.info("="*80)

    # 环境参数
    env_kwargs = {
        'initial_cash': config['initial_cash'],
        'commission_rate': config['commission_rate'],
        'stamp_duty': config['stamp_duty'],
        'enable_t1': config['enable_t1']
    }

    # 创建训练环境
    logger.info(f"创建训练环境 (T+1={'启用' if config['enable_t1'] else '禁用'})...")
    train_env = DummyVecEnv([
        lambda: create_combined_env(train_data, **env_kwargs)
    ])
    train_env = VecNormalize(train_env, norm_obs=True, norm_reward=True)

    # 创建验证环境
    logger.info("创建验证环境...")
    eval_env = DummyVecEnv([
        lambda: create_combined_env(val_data, **env_kwargs)
    ])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, training=False)
    eval_env.obs_rms = train_env.obs_rms
    eval_env.ret_rms = train_env.ret_rms

    # 创建回调
    os.makedirs(config['model_dir'], exist_ok=True)

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=config['model_dir'],
        log_path=config['model_dir'],
        eval_freq=10000,
        deterministic=True,
        render=False
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path=config['model_dir'],
        name_prefix='rl_model'
    )

    # Progress callback for API consumption
    progress_file = os.path.join(config['model_dir'], 'training_progress.json')
    progress_callback = ProgressCallback(
        progress_file=progress_file,
        total_timesteps=config['total_timesteps'],
        update_freq=2000  # Update every 2000 steps
    )

    # 创建PPO模型
    logger.info("初始化PPO模型...")

    # 检测GPU
    import torch
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"使用设备: {device}")
    if device == 'cuda':
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    model = PPO(
        policy="MlpPolicy",
        env=train_env,
        learning_rate=config['learning_rate'],
        n_steps=config['n_steps'],
        batch_size=config['batch_size'],
        n_epochs=config['n_epochs'],
        gamma=config['gamma'],
        verbose=1,
        device=device,  # 显式指定设备
        tensorboard_log=f"{config['model_dir']}/tensorboard/"
    )

    # 训练
    logger.info(f"\n开始训练 ({config['total_timesteps']:,} steps)...")
    logger.info(f"训练数据: {len(train_data)} 只股票")
    logger.info(f"验证数据: {len(val_data)} 只股票")

    start_time = datetime.now()

    model.learn(
        total_timesteps=config['total_timesteps'],
        callback=[eval_callback, checkpoint_callback, progress_callback],
        progress_bar=True
    )

    elapsed = datetime.now() - start_time
    logger.info(f"\n 训练完成！耗时: {elapsed}")

    # 保存最终模型
    final_model_path = f"{config['model_dir']}/final_model.zip"
    model.save(final_model_path)
    train_env.save(f"{config['model_dir']}/final_vecnormalize.pkl")

    logger.info(f"模型已保存: {final_model_path}")

    return model, train_env


def evaluate_model(
    model: PPO,
    vec_normalize: VecNormalize,
    test_data: List[Tuple[str, pd.DataFrame]],
    config: Dict
) -> Dict:
    """评估模型"""
    logger.info("\n" + "="*80)
    logger.info("评估模型性能")
    logger.info("="*80)

    env_kwargs = {
        'initial_cash': config['initial_cash'],
        'commission_rate': config['commission_rate'],
        'stamp_duty': config['stamp_duty'],
        'enable_t1': config['enable_t1']
    }

    results = []

    for symbol, df in test_data[:10]:  # 测试前10只股票
        logger.info(f"\n测试 {symbol}...")

        # 创建测试环境
        test_env = EnhancedTradingEnv(df=df, **env_kwargs)
        test_env = Monitor(test_env)

        test_vec_env = DummyVecEnv([lambda: test_env])
        test_vec_env = VecNormalize(
            test_vec_env,
            norm_obs=True,
            norm_reward=False,
            training=False
        )
        test_vec_env.obs_rms = vec_normalize.obs_rms
        test_vec_env.ret_rms = vec_normalize.ret_rms

        # 运行回测
        obs = test_vec_env.reset()
        done = False

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, info = test_vec_env.step(action)

            if done[0]:
                result = info[0]
                results.append({
                    'symbol': symbol,
                    'final_value': result.get('final_value', config['initial_cash']),
                    'total_return': result.get('total_return', 0),
                    'total_trades': result.get('total_trades', 0),
                    'sharpe_ratio': result.get('sharpe_ratio', 0),
                    'max_drawdown': result.get('max_drawdown', 0)
                })

                logger.info(f"  收益率: {result.get('total_return', 0)*100:.2f}%")
                logger.info(f"  夏普比率: {result.get('sharpe_ratio', 0):.2f}")
                logger.info(f"  最大回撤: {result.get('max_drawdown', 0)*100:.2f}%")
                logger.info(f"  交易次数: {result.get('total_trades', 0)}")

    # 汇总统计
    summary = {
        'avg_return': np.mean([r['total_return'] for r in results]),
        'median_return': np.median([r['total_return'] for r in results]),
        'win_rate': sum(1 for r in results if r['total_return'] > 0) / len(results),
        'avg_sharpe': np.mean([r['sharpe_ratio'] for r in results]),
        'avg_max_drawdown': np.mean([r['max_drawdown'] for r in results]),
        'total_tests': len(results)
    }

    logger.info("\n" + "="*80)
    logger.info("测试集汇总统计")
    logger.info("="*80)
    logger.info(f"测试股票数: {summary['total_tests']}")
    logger.info(f"平均收益率: {summary['avg_return']*100:.2f}%")
    logger.info(f"中位数收益率: {summary['median_return']*100:.2f}%")
    logger.info(f"胜率: {summary['win_rate']*100:.1f}%")
    logger.info(f"平均夏普比率: {summary['avg_sharpe']:.2f}")
    logger.info(f"平均最大回撤: {summary['avg_max_drawdown']*100:.2f}%")

    # 保存结果
    os.makedirs(config['results_dir'], exist_ok=True)
    results_file = f"{config['results_dir']}/test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(results_file, 'w') as f:
        json.dump({
            'summary': summary,
            'details': results,
            'config': config
        }, f, indent=2)

    logger.info(f"\n结果已保存: {results_file}")

    return summary


# ====================================================================================
# 主流程
# ====================================================================================

def main():
    """主训练流程"""
    logger.info("="*80)
    logger.info("HiddenGem Production RL Training")
    logger.info("="*80)
    logger.info(f"训练期: {CONFIG['train_start']} ~ {CONFIG['train_end']}")
    logger.info(f"验证期: {CONFIG['val_start']} ~ {CONFIG['val_end']}")
    logger.info(f"测试期: {CONFIG['test_start']} ~ {CONFIG['test_end']}")
    logger.info(f"T+1限制: {'启用' if CONFIG['enable_t1'] else '禁用'}")
    logger.info("="*80)

    # Step 1: 获取股票池
    logger.info("\n[Step 1/5] 获取股票池...")
    if CONFIG['use_hs300']:
        all_stocks = get_hs300_stocks()
        # 限制数量（训练时太多股票会很慢）
        stocks = all_stocks[:CONFIG['max_stocks']]
        logger.info(f"使用前 {len(stocks)} 只沪深300成分股")
    else:
        # 使用默认列表
        stocks = get_hs300_stocks()
        stocks = stocks[:CONFIG['max_stocks']]

    # Step 2: 准备训练数据
    logger.info("\n[Step 2/5] 准备训练数据...")
    train_cache = f"{CONFIG['data_cache_dir']}/train_data.json"
    train_data = prepare_training_data(
        stocks,
        CONFIG['train_start'],
        CONFIG['train_end'],
        cache_file=train_cache
    )

    # Step 3: 准备验证数据
    logger.info("\n[Step 3/5] 准备验证数据...")
    val_cache = f"{CONFIG['data_cache_dir']}/val_data.json"
    val_data = prepare_training_data(
        stocks,
        CONFIG['val_start'],
        CONFIG['val_end'],
        cache_file=val_cache
    )

    # Step 4: 训练模型
    logger.info("\n[Step 4/5] 训练模型...")
    model, vec_normalize = train_model(train_data, val_data, CONFIG)

    # Step 5: 测试模型
    logger.info("\n[Step 5/5] 准备测试数据并评估...")
    test_cache = f"{CONFIG['data_cache_dir']}/test_data.json"
    test_data = prepare_training_data(
        stocks,
        CONFIG['test_start'],
        CONFIG['test_end'],
        cache_file=test_cache
    )

    summary = evaluate_model(model, vec_normalize, test_data, CONFIG)

    # 最终报告
    logger.info("\n" + "="*80)
    logger.info("训练完成！")
    logger.info("="*80)
    logger.info(f"模型目录: {CONFIG['model_dir']}")
    logger.info(f"结果目录: {CONFIG['results_dir']}")
    logger.info("\n下一步：")
    logger.info("1. 查看TensorBoard: tensorboard --logdir={}/tensorboard/".format(CONFIG['model_dir']))
    logger.info("2. 检查测试结果是否达到预期")
    logger.info("3. 如果满意，开始纸上交易")
    logger.info("="*80)

    return 0


def run_training(config: Dict) -> Dict:
    """
    运行RL训练（可被API调用）

    Args:
        config: 训练配置字典，包含以下键：
            - train_start, train_end: 训练日期
            - val_start, val_end: 验证日期
            - use_hs300, custom_symbols, max_stocks: 股票池配置
            - initial_cash, commission_rate, stamp_duty, enable_t1: 环境参数
            - total_timesteps, learning_rate, n_steps, batch_size: 训练参数
            - use_gpu: 是否使用GPU
            - model_name, model_dir: 模型保存路径

    Returns:
        训练结果字典
    """
    # 合并配置
    final_config = CONFIG.copy()
    final_config.update(config)

    logger.info("="*80)
    logger.info("HiddenGem Production RL Training (API Mode)")
    logger.info("="*80)
    logger.info(f"训练期: {final_config['train_start']} ~ {final_config['train_end']}")
    logger.info(f"验证期: {final_config['val_start']} ~ {final_config['val_end']}")
    logger.info(f"T+1限制: {'启用' if final_config['enable_t1'] else '禁用'}")
    logger.info(f"GPU: {'启用' if final_config.get('use_gpu', False) else '禁用'}")
    logger.info("="*80)

    # 创建模型目录
    os.makedirs(final_config['model_dir'], exist_ok=True)

    # 保存配置
    config_file = os.path.join(final_config['model_dir'], 'config.json')
    with open(config_file, 'w') as f:
        json.dump(final_config, f, indent=2, default=str)
    logger.info(f"配置已保存: {config_file}")

    # Step 1: 获取股票池
    logger.info("\n[Step 1/5] 获取股票池...")
    if final_config.get('use_hs300', True):
        all_stocks = get_hs300_stocks()
        stocks = all_stocks[:final_config.get('max_stocks', 50)]
        logger.info(f"使用前 {len(stocks)} 只沪深300成分股")
    elif final_config.get('custom_symbols'):
        stocks = final_config['custom_symbols']
        logger.info(f"使用自定义股票池: {len(stocks)} 只股票")
    else:
        raise ValueError("必须指定 use_hs300=True 或提供 custom_symbols")

    # Step 2: 准备训练数据
    logger.info("\n[Step 2/5] 准备训练数据...")
    train_cache = os.path.join(final_config.get('data_cache_dir', 'data_cache'), 'train_data.json')
    os.makedirs(os.path.dirname(train_cache), exist_ok=True)
    train_data = prepare_training_data(
        stocks,
        final_config['train_start'],
        final_config['train_end'],
        cache_file=train_cache
    )

    # Step 3: 准备验证数据
    logger.info("\n[Step 3/5] 准备验证数据...")
    val_cache = os.path.join(final_config.get('data_cache_dir', 'data_cache'), 'val_data.json')
    val_data = prepare_training_data(
        stocks,
        final_config['val_start'],
        final_config['val_end'],
        cache_file=val_cache
    )

    # Step 4: 训练模型
    logger.info("\n[Step 4/5] 训练模型...")
    model, vec_normalize = train_model(train_data, val_data, final_config)

    # Step 5: 评估（如果提供测试集）
    summary = {}
    if final_config.get('test_start') and final_config.get('test_end'):
        logger.info("\n[Step 5/5] 准备测试数据并评估...")
        test_cache = os.path.join(final_config.get('data_cache_dir', 'data_cache'), 'test_data.json')
        test_data = prepare_training_data(
            stocks,
            final_config['test_start'],
            final_config['test_end'],
            cache_file=test_cache
        )
        summary = evaluate_model(model, vec_normalize, test_data, final_config)

    # 最终报告
    logger.info("\n" + "="*80)
    logger.info("训练完成！")
    logger.info("="*80)
    logger.info(f"模型目录: {final_config['model_dir']}")

    return {
        'model_dir': final_config['model_dir'],
        'config': final_config,
        'summary': summary,
        'success': True
    }


if __name__ == "__main__":
    sys.exit(main())
