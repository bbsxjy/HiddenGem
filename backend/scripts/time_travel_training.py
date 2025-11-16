"""
时间旅行训练脚本 - Time-Travel Training

核心思想：
AI假装回到历史某一天，基于当时可获得的数据做交易决策，
然后用未来的真实结果评估决策质量，从中学习经验并存储到记忆库。

这是一种离线强化学习（Offline RL）方法，也称为"反事实学习"。

用法：
    python scripts/time_travel_training.py --symbol 600519.SH --start 2020-01-01 --end 2024-12-31
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import argparse
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# 导入核心模块
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.utils.logging_init import get_logger

# 导入记忆系统
from memory import (
    MemoryManager,
    MemoryMode,
    TradingEpisode,
    MarketState,
    AgentAnalysis,
    DecisionChain,
    TradeOutcome,
)

# 导入数据接口
from tradingagents.dataflows.interface import (
    get_stock_data_by_market,
    get_stock_info_by_market,
)

logger = get_logger("time_travel_training")


class TimeTravelTrainer:
    """时间旅行训练器

    通过回溯历史数据，让AI学习从过去的决策中获得的经验。
    """

    def __init__(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        holding_days: int = 5,
        config: Dict[str, Any] = None
    ):
        """初始化训练器

        Args:
            symbol: 股票代码
            start_date: 训练开始日期 (YYYY-MM-DD)
            end_date: 训练结束日期 (YYYY-MM-DD)
            holding_days: 持仓天数（买入后持有N天）
            config: TradingAgents配置
        """
        self.symbol = symbol
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.holding_days = holding_days
        self.config = config or DEFAULT_CONFIG.copy()

        # 初始化TradingGraph
        logger.info(f" 初始化TradingAgents系统...")
        self.trading_graph = TradingAgentsGraph(config=self.config)

        # 初始化记忆系统（训练模式：读写）
        logger.info(f" 初始化记忆系统（训练模式：读写）...")
        self.memory_manager = MemoryManager(
            mode=MemoryMode.TRAINING,  #  训练模式允许写入
            config=self.config
        )

        # 统计信息
        self.total_episodes = 0
        self.successful_episodes = 0
        self.failed_episodes = 0
        self.total_return = 0.0

        logger.info(f" 时间旅行训练器初始化完成")
        logger.info(f"   股票: {symbol}")
        logger.info(f"   时间范围: {start_date} ~ {end_date}")
        logger.info(f"   持仓天数: {holding_days}")

    def get_trading_days(self) -> List[datetime]:
        """获取训练时间范围内的所有交易日

        Returns:
            交易日列表
        """
        logger.info(f" 获取交易日列表...")

        # 获取历史数据（用于确定交易日）
        try:
            data = get_stock_data_by_market(
                symbol=self.symbol,
                start_date=self.start_date.strftime("%Y-%m-%d"),
                end_date=self.end_date.strftime("%Y-%m-%d")
            )

            if data.empty:
                logger.error(f" 无法获取{self.symbol}的历史数据")
                return []

            # 提取交易日
            trading_days = [
                datetime.strptime(str(date)[:10], "%Y-%m-%d")
                for date in data.index
            ]

            logger.info(f" 找到{len(trading_days)}个交易日")
            return trading_days

        except Exception as e:
            logger.error(f" 获取交易日失败: {e}")
            return []

    def simulate_trade(
        self,
        entry_date: datetime,
        processed_signal: Dict[str, Any]
    ) -> Optional[TradeOutcome]:
        """模拟交易执行和结果

        Args:
            entry_date: 入场日期
            processed_signal: SignalProcessor处理后的信号

        Returns:
            交易结果（如果执行了交易）
        """
        action = processed_signal.get('action', '持有')

        # 如果信号是持有，不执行交易
        if action == '持有':
            logger.info(f"   信号: 持有，跳过交易")
            return None

        try:
            # 获取入场价格
            entry_data = get_stock_data_by_market(
                symbol=self.symbol,
                start_date=entry_date.strftime("%Y-%m-%d"),
                end_date=entry_date.strftime("%Y-%m-%d")
            )

            if entry_data.empty:
                logger.warning(f" 无法获取{entry_date}的价格数据")
                return None

            entry_price = float(entry_data['close'].iloc[0])

            # 计算退出日期（持仓N天后）
            exit_date = entry_date + timedelta(days=self.holding_days * 2)  # 考虑非交易日

            # 获取退出价格
            exit_data = get_stock_data_by_market(
                symbol=self.symbol,
                start_date=entry_date.strftime("%Y-%m-%d"),
                end_date=exit_date.strftime("%Y-%m-%d")
            )

            if len(exit_data) < self.holding_days:
                logger.warning(f" 持仓期数据不足，跳过")
                return None

            # 取第N个交易日的收盘价
            actual_exit_date = exit_data.index[self.holding_days - 1]
            exit_price = float(exit_data['close'].iloc[self.holding_days - 1])

            # 计算持仓期间的最大回撤
            high_during = float(exit_data['high'][:self.holding_days].max())
            low_during = float(exit_data['low'][:self.holding_days].min())
            max_drawdown = (low_during - entry_price) / entry_price if entry_price > 0 else 0

            # 计算收益
            if action == '买入':
                pnl = exit_price - entry_price
                pnl_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
            elif action == '卖出':
                # 做空
                pnl = entry_price - exit_price
                pnl_pct = (entry_price - exit_price) / entry_price if entry_price > 0 else 0
            else:
                pnl = 0
                pnl_pct = 0

            outcome = TradeOutcome(
                action=action,
                position_size=0.1,  # 固定仓位10%
                entry_price=entry_price,
                entry_date=entry_date.strftime("%Y-%m-%d"),
                exit_price=exit_price,
                exit_date=str(actual_exit_date)[:10],
                holding_period_days=self.holding_days,
                absolute_return=round(pnl, 2),
                percentage_return=round(pnl_pct, 4),
                max_drawdown_during=round(max_drawdown, 4)
            )

            logger.info(f"   交易: {action} @ ¥{entry_price:.2f} → ¥{exit_price:.2f}")
            logger.info(f"   收益: {pnl_pct:+.2%} (持仓{self.holding_days}天)")

            return outcome

        except Exception as e:
            logger.error(f" 模拟交易失败: {e}", exc_info=True)
            return None

    def extract_market_state(
        self,
        current_date: datetime,
        final_state: Dict[str, Any]
    ) -> MarketState:
        """从final_state中提取市场状态

        Args:
            current_date: 当前日期
            final_state: TradingGraph返回的状态

        Returns:
            MarketState对象
        """
        try:
            # 获取当天的市场数据
            data = get_stock_data_by_market(
                symbol=self.symbol,
                start_date=current_date.strftime("%Y-%m-%d"),
                end_date=current_date.strftime("%Y-%m-%d")
            )

            if data.empty:
                # 降级：创建基础MarketState
                return MarketState(
                    date=current_date.strftime("%Y-%m-%d"),
                    symbol=self.symbol,
                    price=0.0
                )

            # 从数据中提取信息
            row = data.iloc[0]

            return MarketState(
                date=current_date.strftime("%Y-%m-%d"),
                symbol=self.symbol,
                price=float(row.get('close', 0)),
                open=float(row.get('open', 0)) if 'open' in row else None,
                high=float(row.get('high', 0)) if 'high' in row else None,
                low=float(row.get('low', 0)) if 'low' in row else None,
                volume=float(row.get('volume', 0)) if 'volume' in row else None,
                rsi=None,  # TODO: 从技术指标中提取
                macd=None,
                ma_5=None,
                ma_20=None,
                ma_60=None,
                vix=None,
                market_regime=None,  # TODO: 自动检测市场regime
                sector=None
            )

        except Exception as e:
            logger.error(f" 提取市场状态失败: {e}")
            return MarketState(
                date=current_date.strftime("%Y-%m-%d"),
                symbol=self.symbol,
                price=0.0
            )

    def extract_agent_analyses(
        self,
        final_state: Dict[str, Any]
    ) -> Dict[str, AgentAnalysis]:
        """从final_state中提取各个Agent的分析

        Args:
            final_state: TradingGraph返回的状态

        Returns:
            Agent分析字典
        """
        analyses = {}

        # 映射：final_state中的key -> agent_name
        agent_mapping = {
            'market_report': 'market',
            'fundamentals_report': 'fundamentals',
            'sentiment_report': 'sentiment',
            'news_report': 'news'
        }

        for report_key, agent_name in agent_mapping.items():
            report = final_state.get(report_key, '')

            if report:
                analyses[agent_name] = AgentAnalysis(
                    agent_name=agent_name,
                    full_report=report,
                    score=None,  # TODO: 从报告中提取score
                    direction=None,
                    confidence=None,
                    key_points=None,
                    reasoning=report[:500]  # 摘要
                )

        return analyses

    def extract_decision_chain(
        self,
        final_state: Dict[str, Any]
    ) -> DecisionChain:
        """从final_state中提取决策链

        Args:
            final_state: TradingGraph返回的状态

        Returns:
            DecisionChain对象
        """
        debate_state = final_state.get('investment_debate_state', {})
        risk_state = final_state.get('risk_debate_state', {})

        return DecisionChain(
            bull_argument=debate_state.get('bull_history', ''),
            bear_argument=debate_state.get('bear_history', ''),
            investment_debate_conclusion=debate_state.get('judge_decision', ''),
            aggressive_view=risk_state.get('risky_history', ''),
            neutral_view=risk_state.get('neutral_history', ''),
            conservative_view=risk_state.get('safe_history', ''),
            risk_debate_conclusion=risk_state.get('judge_decision', ''),
            final_decision=final_state.get('final_trade_decision', ''),
            final_confidence=None
        )

    def abstract_lesson(
        self,
        outcome: TradeOutcome,
        market_state: MarketState,
        decision_chain: DecisionChain
    ) -> tuple[str, str, bool]:
        """从交易结果中抽象经验教训

        Args:
            outcome: 交易结果
            market_state: 市场状态
            decision_chain: 决策链

        Returns:
            (lesson, key_lesson, success)
        """
        # 判断是否成功
        success = outcome.percentage_return > 0.05  # 收益>5%视为成功

        # 构建教训描述
        if success:
            lesson = f" 成功案例：{outcome.action} @ ¥{outcome.entry_price:.2f}，" \
                    f"持仓{outcome.holding_period_days}天，收益{outcome.percentage_return:.1%}。" \
                    f"市场条件：价格¥{market_state.price:.2f}。" \
                    f"决策理由：{decision_chain.final_decision[:200]}"
        else:
            lesson = f" 失败案例：{outcome.action} @ ¥{outcome.entry_price:.2f}，" \
                    f"持仓{outcome.holding_period_days}天，亏损{outcome.percentage_return:.1%}。" \
                    f"市场条件：价格¥{market_state.price:.2f}。" \
                    f"错误分析：{decision_chain.final_decision[:200]}"

        # 浓缩版（用于embedding检索）
        if success:
            key_lesson = f"{outcome.action}成功：收益{outcome.percentage_return:.1%}，价格¥{market_state.price:.2f}"
        else:
            key_lesson = f"{outcome.action}失败：亏损{outcome.percentage_return:.1%}，价格¥{market_state.price:.2f}"

        return lesson, key_lesson, success

    def train_one_day(self, current_date: datetime) -> bool:
        """训练单个交易日

        Args:
            current_date: 当前日期（假装在这一天）

        Returns:
            是否成功训练
        """
        logger.info(f"\n{'='*60}")
        logger.info(f" 时间旅行到: {current_date.strftime('%Y-%m-%d')}")
        logger.info(f"{'='*60}")

        try:
            # 1⃣ 检索相似历史案例（使用已有记忆）
            logger.info(f" 检索相似历史案例...")

            # TODO: 构建更详细的market_context
            market_context = {
                'symbol': self.symbol,
                'date': current_date.strftime("%Y-%m-%d")
            }

            similar_episodes = self.memory_manager.retrieve_episodes(
                query_context=market_context,
                top_k=3
            )

            logger.info(f"   找到{len(similar_episodes)}个相似历史案例")

            # 2⃣ 执行分析（AI假装在current_date这一天）
            logger.info(f" 执行AI分析...")

            final_state, processed_signal = self.trading_graph.propagate(
                self.symbol,
                current_date.strftime("%Y-%m-%d")
            )

            logger.info(f"   分析完成")

            # 3⃣ 模拟交易执行
            logger.info(f" 模拟交易...")

            outcome = self.simulate_trade(current_date, processed_signal)

            if outcome is None:
                logger.info(f"   无交易发生，跳过")
                return False

            # 4⃣ 抽象经验教训
            logger.info(f" 抽象经验教训...")

            market_state = self.extract_market_state(current_date, final_state)
            agent_analyses = self.extract_agent_analyses(final_state)
            decision_chain = self.extract_decision_chain(final_state)

            lesson, key_lesson, success = self.abstract_lesson(
                outcome, market_state, decision_chain
            )

            logger.info(f"   {lesson[:100]}...")

            # 5⃣ 存储完整Episode到记忆库
            logger.info(f" 存储Episode到记忆库...")

            episode = TradingEpisode(
                episode_id=f"{current_date.strftime('%Y-%m-%d')}_{self.symbol}",
                date=current_date.strftime("%Y-%m-%d"),
                symbol=self.symbol,
                market_state=market_state,
                agent_analyses=agent_analyses,
                decision_chain=decision_chain,
                outcome=outcome,
                lesson=lesson,
                key_lesson=key_lesson,
                success=success,
                created_at=datetime.now().isoformat(),
                mode='training'
            )

            self.memory_manager.add_episode(episode)

            # 6⃣ 抽象为格言（粗粒度记忆）
            logger.info(f" 抽象为格言...")

            situation = f"{self.symbol} @ {current_date.strftime('%Y-%m-%d')}"
            recommendation = key_lesson

            # 根据决策类型，存储到对应的Agent记忆
            if 'bull' in decision_chain.final_decision.lower() or outcome.action == '买入':
                self.memory_manager.add_maxim('bull', situation, recommendation)
            elif 'bear' in decision_chain.final_decision.lower() or outcome.action == '卖出':
                self.memory_manager.add_maxim('bear', situation, recommendation)
            else:
                self.memory_manager.add_maxim('trader', situation, recommendation)

            # 7⃣ 更新统计
            self.total_episodes += 1
            self.total_return += outcome.percentage_return

            if success:
                self.successful_episodes += 1
                logger.info(f" Episode存储成功（盈利）")
            else:
                self.failed_episodes += 1
                logger.info(f" Episode存储成功（亏损）")

            return True

        except Exception as e:
            logger.error(f" 训练失败: {e}", exc_info=True)
            return False

    def run(self):
        """执行完整的时间旅行训练"""
        logger.info(f"\n{'='*60}")
        logger.info(f" 开始时间旅行训练")
        logger.info(f"{'='*60}\n")

        # 获取交易日列表
        trading_days = self.get_trading_days()

        if not trading_days:
            logger.error(f" 没有找到交易日，训练终止")
            return

        # 过滤掉最后N天（需要未来数据来计算收益）
        buffer_days = self.holding_days + 5
        training_days = trading_days[:-buffer_days]

        logger.info(f" 训练统计:")
        logger.info(f"   总交易日: {len(trading_days)}")
        logger.info(f"   可训练日: {len(training_days)}")
        logger.info(f"   保留缓冲: {buffer_days}天\n")

        # 遍历每个交易日进行训练
        for i, current_date in enumerate(training_days, 1):
            logger.info(f"[{i}/{len(training_days)}] 进度: {i/len(training_days):.1%}")

            self.train_one_day(current_date)

            # 每10个episode打印一次统计
            if i % 10 == 0:
                self.print_statistics()

        # 最终统计
        logger.info(f"\n{'='*60}")
        logger.info(f" 训练完成！")
        logger.info(f"{'='*60}\n")

        self.print_statistics()
        self.save_results()

    def print_statistics(self):
        """打印训练统计"""
        if self.total_episodes == 0:
            return

        avg_return = self.total_return / self.total_episodes
        success_rate = self.successful_episodes / self.total_episodes

        logger.info(f"\n 训练统计:")
        logger.info(f"   总Episodes: {self.total_episodes}")
        logger.info(f"   成功: {self.successful_episodes} ({success_rate:.1%})")
        logger.info(f"   失败: {self.failed_episodes} ({1-success_rate:.1%})")
        logger.info(f"   平均收益: {avg_return:+.2%}\n")

    def save_results(self):
        """保存训练结果到JSON"""
        results = {
            'symbol': self.symbol,
            'start_date': self.start_date.strftime("%Y-%m-%d"),
            'end_date': self.end_date.strftime("%Y-%m-%d"),
            'holding_days': self.holding_days,
            'total_episodes': self.total_episodes,
            'successful_episodes': self.successful_episodes,
            'failed_episodes': self.failed_episodes,
            'success_rate': self.successful_episodes / self.total_episodes if self.total_episodes > 0 else 0,
            'average_return': self.total_return / self.total_episodes if self.total_episodes > 0 else 0,
            'timestamp': datetime.now().isoformat()
        }

        # 保存到文件
        output_dir = Path("training_results")
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"time_travel_{self.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f" 训练结果已保存: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='时间旅行训练 - Time-Travel Training')

    parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        help='股票代码，例如：600519.SH（A股）、AAPL（美股）'
    )

    parser.add_argument(
        '--start',
        type=str,
        required=True,
        help='训练开始日期，格式：YYYY-MM-DD'
    )

    parser.add_argument(
        '--end',
        type=str,
        required=True,
        help='训练结束日期，格式：YYYY-MM-DD'
    )

    parser.add_argument(
        '--holding-days',
        type=int,
        default=5,
        help='持仓天数（默认：5）'
    )

    args = parser.parse_args()

    # 创建训练器
    trainer = TimeTravelTrainer(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end,
        holding_days=args.holding_days
    )

    # 执行训练
    trainer.run()


if __name__ == "__main__":
    main()
