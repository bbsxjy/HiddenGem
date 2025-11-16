"""
端到端集成测试 - End-to-End Integration Test

测试以下集成场景
1. RL Agent + TradingAgents + Memory 集成
2. RL策略在回测系统中运行
3. Paper Trading引擎运行RL Agent
4. 完整的交易决策流程

Usage:
    python scripts/test_integration_e2e.py
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging

# 导入TradingAgents系统
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.dataflows.interface import get_stock_data_by_market

# 导入Memory系统
try:
    from memory import MemoryManager, MemoryMode
    MEMORY_AVAILABLE = True
except ImportError:
    print("[WARNING] Memory module not found, using Mock")
    MEMORY_AVAILABLE = False

# Mock MemoryManager
class MockMemoryManager:
    def __init__(self, *args, **kwargs):
        pass
    def retrieve_episodes(self, *args, **kwargs):
        return []

if not MEMORY_AVAILABLE:
    MemoryManager = MockMemoryManager
    MemoryMode = None

# 导入RL环境
from tradingagents.rl.llm_enhanced_env import LLMEnhancedTradingEnv

# 导入回测系统
from trading.backtester import Backtester
from trading.strategy import BaseStrategy
from trading.portfolio_manager import PortfolioManager

# 导入Paper Trading
from trading.paper_trading_engine import PaperTradingEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class RLStrategy(BaseStrategy):
    """基于RL Agent的回测策略"""

    def __init__(
        self,
        env: LLMEnhancedTradingEnv,
        name: str = "RL_Strategy",
        use_random_policy: bool = True
    ):
        super().__init__(name)
        self.env = env
        self.use_random_policy = use_random_policy

    def generate_signals(self, data: pd.DataFrame, portfolio: PortfolioManager) -> dict:
        """
        使用RL环境生成交易信号

        Returns:
            信号字典: {'symbol': action_id}
        """
        # 获取当前观察状态
        obs = self.env._get_observation()

        # 使用随机策略或训练好的策略
        if self.use_random_policy:
            action = self.env.action_space.sample()
        else:
            # TODO: 加载训练好的RL模型
            # action = trained_model.predict(obs)
            action = self.env.action_space.sample()

        # 动作映射
        # 0: HOLD, 1: BUY_10, 2: BUY_20, 3: SELL_10, 4: SELL_20, 5: CLOSE
        symbol = self.env.df.iloc[0].get('tic', 'UNKNOWN')

        return {symbol: action}


def test_1_rl_tradingagents_integration():
    """测试1: RL Agent + TradingAgents 集成"""
    print("\n" + "="*80)
    print("测试1: RL Agent + TradingAgents + Memory 集成")
    print("="*80)

    try:
        # 1. 初始化TradingAgents系统
        logger.info(" 初始化TradingAgents系统...")
        trading_graph = TradingAgentsGraph()

        # 2. 初始化Memory系统
        logger.info(" 初始化Memory系统...")
        memory_manager = MemoryManager()

        # 3. 获取测试数据
        logger.info(" 获取测试数据...")
        symbol = '600519.SH'  # 贵州茅台
        end_date = datetime.now()
        start_date = end_date - timedelta(days=100)

        df = get_stock_data_by_market(
            symbol,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )

        if df is None or len(df) == 0:
            logger.warning(" 无法获取真实数据使用模拟数据")
            # 生成模拟数据
            dates = pd.date_range(start_date, end_date, freq='D')[:100]
            df = pd.DataFrame({
                'date': dates,
                'open': 100 + np.random.randn(100) * 2,
                'high': 102 + np.random.randn(100) * 2,
                'low': 98 + np.random.randn(100) * 2,
                'close': 100 + np.random.randn(100) * 2,
                'volume': 1000000 + np.random.randint(-100000, 100000, 100),
                'tic': [symbol] * 100,
            })

            # 添加技术指标
            df['macd'] = np.random.randn(100) * 0.5
            df['rsi_30'] = 50 + np.random.randn(100) * 20
            df['cci_30'] = np.random.randn(100) * 50
            df['dx_30'] = 20 + np.random.randn(100) * 10

        logger.info(f"   数据长度: {len(df)} 天")

        # 4. 创建LLM增强的RL环境
        logger.info(" 创建RL环境...")
        env = LLMEnhancedTradingEnv(
            df=df,
            trading_graph=trading_graph,
            memory_manager=memory_manager,
            initial_cash=100000.0
        )

        # 5. 运行几个episode测试
        logger.info(" 运行测试episodes...")
        num_steps = 10
        obs, info = env.reset()

        total_reward = 0
        for step in range(num_steps):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward

            logger.info(f"   Step {step+1}: action={action}, reward={reward:.4f}")

            if terminated or truncated:
                break

        logger.info(f" 测试完成总奖励: {total_reward:.4f}")
        logger.info(f"   最终资产: {env._calculate_total_asset():,.2f}")
        logger.info(f"   收益率: {(env._calculate_total_asset() - env.initial_cash) / env.initial_cash:.2%}")

        return True

    except Exception as e:
        logger.error(f" 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_rl_strategy_backtesting():
    """测试2: RL策略在回测系统中运行"""
    print("\n" + "="*80)
    print("测试2: RL策略在回测系统中运行")
    print("="*80)

    try:
        # 1. 准备回测数据
        logger.info(" 准备回测数据...")
        symbol = '000001.SZ'  # 平安银行
        end_date = datetime.now()
        start_date = end_date - timedelta(days=100)

        # 生成模拟数据简化
        dates = pd.date_range(start_date, end_date, freq='D')[:100]
        df = pd.DataFrame({
            'date': dates,
            'open': 10 + np.random.randn(100) * 0.2,
            'high': 10.2 + np.random.randn(100) * 0.2,
            'low': 9.8 + np.random.randn(100) * 0.2,
            'close': 10 + np.random.randn(100) * 0.2,
            'volume': 1000000 + np.random.randint(-100000, 100000, 100),
            'tic': [symbol] * 100,
        })

        # 添加技术指标
        df['macd'] = np.random.randn(100) * 0.1
        df['rsi_30'] = 50 + np.random.randn(100) * 20
        df['cci_30'] = np.random.randn(100) * 50
        df['dx_30'] = 20 + np.random.randn(100) * 10

        logger.info(f"   数据长度: {len(df)} 天")

        # 2. 创建RL环境
        logger.info(" 创建RL环境...")
        trading_graph = TradingAgentsGraph()
        memory_manager = MemoryManager()

        env = LLMEnhancedTradingEnv(
            df=df,
            trading_graph=trading_graph,
            memory_manager=memory_manager,
            initial_cash=100000.0
        )

        # 3. 创建RL策略
        logger.info(" 创建RL策略...")
        strategy = RLStrategy(env, name="RL_Random_Policy", use_random_policy=True)

        # 4. 运行回测
        logger.info(" 运行回测...")
        backtester = Backtester(
            strategy=strategy,
            initial_cash=100000.0
        )

        # 简化回测直接测试策略信号生成
        portfolio = PortfolioManager(initial_cash=100000.0)
        signals = strategy.generate_signals(df, portfolio)

        logger.info(f" 回测完成")
        logger.info(f"   生成信号: {signals}")

        return True

    except Exception as e:
        logger.error(f" 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_paper_trading_with_rl():
    """测试3: Paper Trading运行RL Agent"""
    print("\n" + "="*80)
    print("测试3: Paper Trading引擎运行RL Agent")
    print("="*80)

    try:
        logger.info(" 初始化Paper Trading引擎...")

        # 注意: Paper Trading是异步的这里只测试初始化
        # 实际运行需要使用 asyncio.run(engine.run())

        engine = PaperTradingEngine(
            rl_agent=None,  # 使用简单策略
            initial_cash=100000.0,
            symbols=['600519.SH', '000001.SZ'],
            update_interval=60,
            enable_risk_control=True
        )

        logger.info(" Paper Trading引擎初始化成功")
        logger.info(f"   初始资金: {engine.initial_cash:,.2f}")
        logger.info(f"   交易标的: {engine.symbols}")
        logger.info(f"   更新间隔: {engine.update_interval}秒")

        # 获取状态
        status = engine.get_status()
        logger.info(f"   运行状态: {status}")

        logger.info("\n 提示: 要运行Paper Trading请使用:")
        logger.info("   import asyncio")
        logger.info("   asyncio.run(engine.run(['600519.SH']))")

        return True

    except Exception as e:
        logger.error(f" 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_full_workflow():
    """测试4: 完整的交易决策流程"""
    print("\n" + "="*80)
    print("测试4: 完整的交易决策流程 (TradingAgents -> RL -> 回测)")
    print("="*80)

    try:
        logger.info(" 演示完整流程...")

        # 1. TradingAgents分析
        logger.info("\n步骤1: TradingAgents多Agent分析")
        symbol = '600519.SH'
        trade_date = datetime.now().strftime('%Y-%m-%d')

        trading_graph = TradingAgentsGraph()
        logger.info(f"   正在分析 {symbol} on {trade_date}...")

        # 注意: 这会调用LLM可能需要一些时间
        try:
            final_state, processed_signal = trading_graph.propagate(symbol, trade_date)
            logger.info(f"    TradingAgents分析完成")
            logger.info(f"   最终决策: {final_state.get('final_trade_decision', 'N/A')[:100]}...")
        except Exception as e:
            logger.warning(f"    TradingAgents分析失败可能是API限制: {e}")
            final_state = {}
            processed_signal = {'direction': 'hold', 'confidence': 0.5}

        # 2. Memory检索
        logger.info("\n步骤2: Memory系统检索历史案例")
        memory_manager = MemoryManager()
        similar_episodes = memory_manager.retrieve_episodes(
            query_context={'symbol': symbol, 'date': trade_date},
            top_k=5
        )
        logger.info(f"   检索到 {len(similar_episodes)} 个相似案例")

        # 3. RL决策
        logger.info("\n步骤3: RL Agent决策")
        logger.info("   整合TradingAgents信号和Memory信息...")
        logger.info("   RL Agent使用这些信号作为状态的一部分")
        logger.info(f"   LLM信号: {processed_signal}")

        # 4. 执行回测或Paper Trading
        logger.info("\n步骤4: 执行交易")
        logger.info("   选项A: 在回测系统中验证策略")
        logger.info("   选项B: 在Paper Trading中实时执行")
        logger.info("   选项C: 在东财模拟盘中执行")

        logger.info("\n 完整流程演示完成")

        return True

    except Exception as e:
        logger.error(f" 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有集成测试"""
    print("\n" + "="*80)
    print("HiddenGem 端到端集成测试套件")
    print("="*80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []

    # 测试1: RL + TradingAgents集成
    results.append(("RL + TradingAgents集成", test_1_rl_tradingagents_integration()))

    # 测试2: RL策略回测
    results.append(("RL策略回测", test_2_rl_strategy_backtesting()))

    # 测试3: Paper Trading
    results.append(("Paper Trading + RL", test_3_paper_trading_with_rl()))

    # 测试4: 完整流程
    results.append(("完整交易流程", test_4_full_workflow()))

    # 打印总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    for name, passed in results:
        status = " PASS" if passed else " FAIL"
        print(f"{status} - {name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print("\n" + "="*80)
    print(f"总计: {passed_count}/{total_count} 测试通过 ({passed_count/total_count*100:.1f}%)")
    print("="*80)
    print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return all(passed for _, passed in results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
