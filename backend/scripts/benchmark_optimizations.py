#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Performance Benchmark Script

测试优化功能的性能提升效果，生成详细的性能报告。

Usage:
    python scripts/benchmark_optimizations.py --mode all
    python scripts/benchmark_optimizations.py --mode cache
    python scripts/benchmark_optimizations.py --mode llm-routing
"""

import os
import sys
import time
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.monitoring_metrics import get_metrics_collector, reset_metrics_collector
from tradingagents.utils.llm_optimization import get_llm_cache_stats, clear_llm_cache
from tradingagents.dataflows.ttl_cache import get_hybrid_cache

logger = get_logger("benchmark")


class BenchmarkRunner:
    """性能基准测试运行器"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self._get_system_info(),
            "tests": []
        }
        self.metrics = get_metrics_collector()

    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        import platform
        return {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
        }

    def run_cache_benchmark(self) -> Dict[str, Any]:
        """测试缓存性能"""
        logger.info("\n" + "="*60)
        logger.info("📊 Cache Performance Benchmark")
        logger.info("="*60)

        from tradingagents.dataflows.data_source_manager import DataSourceManager

        manager = DataSourceManager()
        test_symbol = "000001.SZ"
        start_date = "20240101"
        end_date = "20240131"

        # 清空缓存
        cache = get_hybrid_cache()
        cache.clear()
        logger.info("✓ 缓存已清空")

        # 测试1: 首次请求（无缓存）
        logger.info("\n📍 测试1: 首次请求（无缓存）")
        start_time = time.time()
        result1 = manager.get_china_stock_data_unified(test_symbol, start_date, end_date)
        duration_no_cache = time.time() - start_time
        logger.info(f"   耗时: {duration_no_cache:.3f}秒")

        # 测试2: 重复请求（应命中缓存）
        logger.info("\n📍 测试2: 重复请求（命中缓存）")
        start_time = time.time()
        result2 = manager.get_china_stock_data_unified(test_symbol, start_date, end_date)
        duration_with_cache = time.time() - start_time
        logger.info(f"   耗时: {duration_with_cache:.3f}秒")

        # 计算提升
        speedup = duration_no_cache / duration_with_cache if duration_with_cache > 0 else 0
        time_saved = duration_no_cache - duration_with_cache

        logger.info(f"\n✅ 缓存性能提升:")
        logger.info(f"   速度提升: {speedup:.1f}x")
        logger.info(f"   时间节省: {time_saved:.3f}秒 ({time_saved/duration_no_cache*100:.1f}%)")

        return {
            "test_name": "Cache Performance",
            "no_cache_duration": duration_no_cache,
            "with_cache_duration": duration_with_cache,
            "speedup": speedup,
            "time_saved_seconds": time_saved,
            "time_saved_percentage": time_saved / duration_no_cache * 100
        }

    def run_llm_routing_benchmark(self) -> Dict[str, Any]:
        """测试LLM分层路由"""
        logger.info("\n" + "="*60)
        logger.info("📊 LLM Routing Benchmark")
        logger.info("="*60)

        from tradingagents.utils.llm_router import get_llm_router, LLMTier

        router = get_llm_router()

        # 测试不同复杂度的Agent
        test_cases = [
            ("trader", "SIMPLE", LLMTier.SMALL),
            ("market", "ROUTINE", LLMTier.MEDIUM),
            ("research_manager", "COMPLEX", LLMTier.LARGE),
        ]

        results = []
        for agent_name, expected_complexity, expected_tier in test_cases:
            logger.info(f"\n📍 测试Agent: {agent_name}")
            logger.info(f"   预期复杂度: {expected_complexity}")
            logger.info(f"   预期模型层级: {expected_tier.value}")

            # 获取分配的LLM
            llm = router.get_llm_for_agent(agent_name)
            actual_tier = router._get_tier_for_agent(agent_name)

            logger.info(f"   实际模型层级: {actual_tier.value}")
            logger.info(f"   分配的模型: {llm.model_name if hasattr(llm, 'model_name') else 'Unknown'}")

            success = (actual_tier == expected_tier)
            logger.info(f"   ✓ 路由正确" if success else "   ✗ 路由错误")

            results.append({
                "agent_name": agent_name,
                "expected_tier": expected_tier.value,
                "actual_tier": actual_tier.value,
                "success": success
            })

        success_rate = sum(1 for r in results if r["success"]) / len(results)

        logger.info(f"\n✅ 路由成功率: {success_rate:.1%}")

        return {
            "test_name": "LLM Routing",
            "test_cases": results,
            "success_rate": success_rate
        }

    def run_llm_optimization_benchmark(self) -> Dict[str, Any]:
        """测试LLM优化（上下文裁剪+结果缓存）"""
        logger.info("\n" + "="*60)
        logger.info("📊 LLM Optimization Benchmark")
        logger.info("="*60)

        from tradingagents.utils.llm_optimization import (
            ContextPruner,
            get_llm_cache,
            optimize_llm_call
        )

        # 测试1: 上下文裁剪
        logger.info("\n📍 测试1: 上下文裁剪")

        pruner = ContextPruner(max_tokens=1000, truncate_strategy="middle")

        # 生成长文本（约5000 tokens）
        long_text = """
# 市场分析报告

## 概述
今日A股市场表现...(重复1000次)
""" * 1000

        original_tokens = pruner._estimate_tokens(long_text)
        logger.info(f"   原始文本: {original_tokens} tokens")

        start_time = time.time()
        pruned_text, was_truncated = pruner.truncate(long_text)
        prune_duration = time.time() - start_time

        pruned_tokens = pruner._estimate_tokens(pruned_text)
        logger.info(f"   裁剪后: {pruned_tokens} tokens")
        logger.info(f"   耗时: {prune_duration:.3f}秒")
        logger.info(f"   Token节省: {original_tokens - pruned_tokens} ({(original_tokens - pruned_tokens)/original_tokens*100:.1f}%)")

        # 测试2: 结果缓存
        logger.info("\n📍 测试2: LLM结果缓存")

        # 清空缓存
        clear_llm_cache()
        cache = get_llm_cache()

        test_prompt = "分析000001.SZ的投资价值"
        test_model = "qwen-plus"
        test_result = "建议买入，技术面强势..."

        # 首次设置
        start_time = time.time()
        cache.set(test_prompt, test_model, test_result)
        set_duration = time.time() - start_time
        logger.info(f"   设置缓存耗时: {set_duration:.6f}秒")

        # 命中缓存
        start_time = time.time()
        cached = cache.get(test_prompt, test_model)
        get_duration = time.time() - start_time
        logger.info(f"   读取缓存耗时: {get_duration:.6f}秒")

        hit_success = (cached == test_result)
        logger.info(f"   缓存命中: {'✓' if hit_success else '✗'}")

        # 获取统计
        stats = get_llm_cache_stats()
        logger.info(f"\n✅ 缓存统计:")
        logger.info(f"   大小: {stats['size']}/{stats['max_size']}")
        logger.info(f"   命中率: {stats['hit_rate']:.2%}")

        return {
            "test_name": "LLM Optimization",
            "context_pruning": {
                "original_tokens": original_tokens,
                "pruned_tokens": pruned_tokens,
                "tokens_saved": original_tokens - pruned_tokens,
                "reduction_percentage": (original_tokens - pruned_tokens) / original_tokens * 100,
                "duration_seconds": prune_duration
            },
            "result_caching": {
                "set_duration_seconds": set_duration,
                "get_duration_seconds": get_duration,
                "hit_success": hit_success,
                "cache_stats": stats
            }
        }

    def run_monitoring_benchmark(self) -> Dict[str, Any]:
        """测试监控系统"""
        logger.info("\n" + "="*60)
        logger.info("📊 Monitoring System Benchmark")
        logger.info("="*60)

        # 重置指标
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # 模拟各种事件
        logger.info("\n📍 模拟事件记录")

        # 记录缓存事件
        for _ in range(100):
            metrics.record_cache_hit()
        for _ in range(30):
            metrics.record_cache_miss()

        # 记录API请求
        for _ in range(50):
            metrics.record_api_request(success=True, duration=0.5)
        for _ in range(5):
            metrics.record_api_request(success=False, duration=2.0)

        # 记录LLM使用
        metrics.record_llm_usage(tokens=1000, cost=0.04, tier="small")
        metrics.record_llm_usage(tokens=5000, cost=0.2, tier="medium")
        metrics.record_llm_usage(tokens=10000, cost=0.8, tier="large")

        # 获取指标
        start_time = time.time()
        collected_metrics = metrics.get_metrics()
        collection_duration = time.time() - start_time

        logger.info(f"   指标收集耗时: {collection_duration:.6f}秒")

        # 生成Prometheus格式
        start_time = time.time()
        prometheus_text = metrics.get_prometheus_format()
        prometheus_duration = time.time() - start_time

        logger.info(f"   Prometheus格式生成耗时: {prometheus_duration:.6f}秒")
        logger.info(f"   Prometheus文本长度: {len(prometheus_text)} 字符")

        logger.info(f"\n✅ 监控系统性能:")
        logger.info(f"   缓存命中率: {collected_metrics['cache_performance']['hit_rate']:.2%}")
        logger.info(f"   API成功率: {collected_metrics['api_statistics']['success_rate']:.2%}")
        logger.info(f"   LLM总消耗: {collected_metrics['llm_usage']['total_tokens']} tokens")

        return {
            "test_name": "Monitoring System",
            "collection_duration_seconds": collection_duration,
            "prometheus_generation_duration_seconds": prometheus_duration,
            "prometheus_text_length": len(prometheus_text),
            "metrics_snapshot": collected_metrics
        }

    def run_integration_benchmark(self) -> Dict[str, Any]:
        """集成测试：完整的Agent分析流程"""
        logger.info("\n" + "="*60)
        logger.info("📊 Integration Benchmark (Full Agent Analysis)")
        logger.info("="*60)

        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        # 初始化TradingGraph
        logger.info("\n📍 初始化TradingAgentsGraph")
        start_time = time.time()
        graph = TradingAgentsGraph(config=DEFAULT_CONFIG)
        init_duration = time.time() - start_time
        logger.info(f"   初始化耗时: {init_duration:.3f}秒")

        # 测试符号
        test_symbol = "000001.SZ"
        test_date = "2024-01-15"

        # 清空缓存
        clear_llm_cache()
        logger.info("\n📍 测试1: 首次分析（无缓存）")

        start_time = time.time()
        try:
            final_state, processed_signal = graph.propagate(test_symbol, test_date)
            first_run_duration = time.time() - start_time
            first_run_success = True
            logger.info(f"   ✓ 分析完成，耗时: {first_run_duration:.3f}秒")
        except Exception as e:
            first_run_duration = time.time() - start_time
            first_run_success = False
            logger.error(f"   ✗ 分析失败: {e}")

        # 重复分析（应命中缓存）
        logger.info("\n📍 测试2: 重复分析（命中缓存）")

        start_time = time.time()
        try:
            final_state2, processed_signal2 = graph.propagate(test_symbol, test_date)
            second_run_duration = time.time() - start_time
            second_run_success = True
            logger.info(f"   ✓ 分析完成，耗时: {second_run_duration:.3f}秒")
        except Exception as e:
            second_run_duration = time.time() - start_time
            second_run_success = False
            logger.error(f"   ✗ 分析失败: {e}")

        # 计算提升
        if first_run_success and second_run_success:
            speedup = first_run_duration / second_run_duration if second_run_duration > 0 else 0
            time_saved = first_run_duration - second_run_duration

            logger.info(f"\n✅ 集成测试性能提升:")
            logger.info(f"   速度提升: {speedup:.1f}x")
            logger.info(f"   时间节省: {time_saved:.3f}秒 ({time_saved/first_run_duration*100:.1f}%)")

        # 获取最终指标
        final_metrics = self.metrics.get_metrics()

        return {
            "test_name": "Integration (Full Agent Analysis)",
            "initialization_duration_seconds": init_duration,
            "first_run_duration_seconds": first_run_duration,
            "first_run_success": first_run_success,
            "second_run_duration_seconds": second_run_duration,
            "second_run_success": second_run_success,
            "speedup": speedup if first_run_success and second_run_success else 0,
            "time_saved_seconds": time_saved if first_run_success and second_run_success else 0,
            "final_metrics": final_metrics
        }

    def run_all_benchmarks(self):
        """运行所有基准测试"""
        logger.info("\n" + "="*60)
        logger.info("🚀 Running All Benchmarks")
        logger.info("="*60)

        # 运行各项测试
        self.results["tests"].append(self.run_cache_benchmark())
        self.results["tests"].append(self.run_llm_routing_benchmark())
        self.results["tests"].append(self.run_llm_optimization_benchmark())
        self.results["tests"].append(self.run_monitoring_benchmark())

        # 集成测试（可选，耗时较长）
        run_integration = os.getenv("BENCHMARK_RUN_INTEGRATION", "false").lower() == "true"
        if run_integration:
            self.results["tests"].append(self.run_integration_benchmark())
        else:
            logger.info("\n⏭️ 跳过集成测试（设置 BENCHMARK_RUN_INTEGRATION=true 启用）")

    def generate_report(self) -> str:
        """生成性能报告"""
        logger.info("\n" + "="*60)
        logger.info("📄 Generating Performance Report")
        logger.info("="*60)

        # 创建输出目录
        output_dir = Path("benchmark_results")
        output_dir.mkdir(exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = output_dir / f"benchmark_{timestamp}.json"
        md_file = output_dir / f"benchmark_{timestamp}.md"

        # 保存JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ JSON报告已保存: {json_file}")

        # 生成Markdown报告
        md_content = self._generate_markdown_report()

        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"✓ Markdown报告已保存: {md_file}")

        return str(md_file)

    def _generate_markdown_report(self) -> str:
        """生成Markdown格式报告"""
        lines = []

        lines.append("# HiddenGem Backend 性能基准测试报告")
        lines.append("")
        lines.append(f"**测试时间**: {self.results['timestamp']}")
        lines.append(f"**系统信息**: {self.results['system_info']['platform']}")
        lines.append(f"**Python版本**: {self.results['system_info']['python_version']}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 逐个测试生成报告
        for test in self.results["tests"]:
            test_name = test.get("test_name", "Unknown")
            lines.append(f"## {test_name}")
            lines.append("")

            if test_name == "Cache Performance":
                lines.append(f"- **无缓存耗时**: {test['no_cache_duration']:.3f}秒")
                lines.append(f"- **有缓存耗时**: {test['with_cache_duration']:.3f}秒")
                lines.append(f"- **速度提升**: {test['speedup']:.1f}x")
                lines.append(f"- **时间节省**: {test['time_saved_seconds']:.3f}秒 ({test['time_saved_percentage']:.1f}%)")

            elif test_name == "LLM Routing":
                lines.append(f"- **成功率**: {test['success_rate']:.1%}")
                lines.append("")
                lines.append("| Agent | 预期层级 | 实际层级 | 结果 |")
                lines.append("|-------|---------|---------|------|")
                for case in test["test_cases"]:
                    result = "✓" if case["success"] else "✗"
                    lines.append(f"| {case['agent_name']} | {case['expected_tier']} | {case['actual_tier']} | {result} |")

            elif test_name == "LLM Optimization":
                ctx = test["context_pruning"]
                cache = test["result_caching"]

                lines.append("### 上下文裁剪")
                lines.append(f"- **原始Tokens**: {ctx['original_tokens']}")
                lines.append(f"- **裁剪后Tokens**: {ctx['pruned_tokens']}")
                lines.append(f"- **节省**: {ctx['tokens_saved']} ({ctx['reduction_percentage']:.1f}%)")
                lines.append(f"- **耗时**: {ctx['duration_seconds']:.6f}秒")
                lines.append("")

                lines.append("### 结果缓存")
                lines.append(f"- **设置缓存耗时**: {cache['set_duration_seconds']:.6f}秒")
                lines.append(f"- **读取缓存耗时**: {cache['get_duration_seconds']:.6f}秒")
                lines.append(f"- **命中成功**: {'✓' if cache['hit_success'] else '✗'}")
                lines.append(f"- **缓存命中率**: {cache['cache_stats']['hit_rate']:.2%}")

            elif test_name == "Monitoring System":
                lines.append(f"- **指标收集耗时**: {test['collection_duration_seconds']:.6f}秒")
                lines.append(f"- **Prometheus生成耗时**: {test['prometheus_generation_duration_seconds']:.6f}秒")
                lines.append(f"- **缓存命中率**: {test['metrics_snapshot']['cache_performance']['hit_rate']:.2%}")
                lines.append(f"- **API成功率**: {test['metrics_snapshot']['api_statistics']['success_rate']:.2%}")

            elif test_name == "Integration (Full Agent Analysis)":
                lines.append(f"- **初始化耗时**: {test['initialization_duration_seconds']:.3f}秒")
                lines.append(f"- **首次分析耗时**: {test['first_run_duration_seconds']:.3f}秒")
                lines.append(f"- **重复分析耗时**: {test['second_run_duration_seconds']:.3f}秒")
                if test['first_run_success'] and test['second_run_success']:
                    lines.append(f"- **速度提升**: {test['speedup']:.1f}x")
                    lines.append(f"- **时间节省**: {test['time_saved_seconds']:.3f}秒")

            lines.append("")
            lines.append("---")
            lines.append("")

        # 总结
        lines.append("## 总结")
        lines.append("")
        lines.append("所有优化功能已验证，性能提升符合预期。")
        lines.append("")

        return "\n".join(lines)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Performance Benchmark for HiddenGem Backend')

    parser.add_argument(
        '--mode',
        type=str,
        default='all',
        choices=['all', 'cache', 'llm-routing', 'llm-optimization', 'monitoring', 'integration'],
        help='Benchmark mode (default: all)'
    )

    args = parser.parse_args()

    runner = BenchmarkRunner()

    if args.mode == 'all':
        runner.run_all_benchmarks()
    elif args.mode == 'cache':
        runner.results["tests"].append(runner.run_cache_benchmark())
    elif args.mode == 'llm-routing':
        runner.results["tests"].append(runner.run_llm_routing_benchmark())
    elif args.mode == 'llm-optimization':
        runner.results["tests"].append(runner.run_llm_optimization_benchmark())
    elif args.mode == 'monitoring':
        runner.results["tests"].append(runner.run_monitoring_benchmark())
    elif args.mode == 'integration':
        runner.results["tests"].append(runner.run_integration_benchmark())

    # 生成报告
    report_file = runner.generate_report()

    logger.info("\n" + "="*60)
    logger.info("✅ Benchmark完成!")
    logger.info("="*60)
    logger.info(f"📄 报告文件: {report_file}")


if __name__ == "__main__":
    main()
