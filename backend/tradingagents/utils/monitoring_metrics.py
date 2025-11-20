"""
Monitoring Metrics Module

提供Prometheus风格的监控指标收集和REST API暴露功能。

监控指标包括:
- 系统健康状态（心跳、重启次数）
- 缓存性能（命中率、总请求数）
- API调用统计（成功/失败次数、平均耗时）
- LLM使用统计（token消耗、成本）
- 任务进度（Time Travel训练进度）
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from threading import Lock

from tradingagents.utils.logging_init import get_logger
logger = get_logger("monitoring")


@dataclass
class Counter:
    """简单计数器"""
    name: str
    help: str
    value: int = 0
    labels: Dict[str, str] = field(default_factory=dict)

    def inc(self, amount: int = 1):
        """增加计数"""
        self.value += amount

    def reset(self):
        """重置计数"""
        self.value = 0


@dataclass
class Gauge:
    """简单仪表"""
    name: str
    help: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)

    def set(self, value: float):
        """设置值"""
        self.value = value

    def inc(self, amount: float = 1.0):
        """增加值"""
        self.value += amount

    def dec(self, amount: float = 1.0):
        """减少值"""
        self.value -= amount


@dataclass
class Histogram:
    """简单直方图（用于记录延迟）"""
    name: str
    help: str
    buckets: List[float] = field(default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])
    values: List[float] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)

    def observe(self, value: float):
        """记录观测值"""
        self.values.append(value)

    def get_summary(self) -> Dict[str, float]:
        """获取统计摘要"""
        if not self.values:
            return {"count": 0, "sum": 0, "min": 0, "max": 0, "avg": 0}

        return {
            "count": len(self.values),
            "sum": sum(self.values),
            "min": min(self.values),
            "max": max(self.values),
            "avg": sum(self.values) / len(self.values)
        }


class MetricsCollector:
    """监控指标收集器"""

    def __init__(self):
        """初始化指标收集器"""
        self._lock = Lock()

        # ===== 系统健康指标 =====
        self.heartbeat_status = Gauge(
            name="auto_trading_heartbeat_seconds",
            help="Seconds since last heartbeat from auto trading loop"
        )

        self.restart_count = Counter(
            name="auto_trading_restart_total",
            help="Total number of auto trading loop restarts"
        )

        self.health_status = Gauge(
            name="auto_trading_health_status",
            help="Health status of auto trading (1=healthy, 0=unhealthy)"
        )

        # ===== 缓存性能指标 =====
        self.cache_hits = Counter(
            name="data_cache_hits_total",
            help="Total number of cache hits"
        )

        self.cache_misses = Counter(
            name="data_cache_misses_total",
            help="Total number of cache misses"
        )

        self.cache_hit_rate = Gauge(
            name="data_cache_hit_rate",
            help="Cache hit rate (0.0 to 1.0)"
        )

        # ===== API调用统计 =====
        self.api_requests_total = Counter(
            name="api_requests_total",
            help="Total number of API requests"
        )

        self.api_requests_success = Counter(
            name="api_requests_success_total",
            help="Total number of successful API requests"
        )

        self.api_requests_failure = Counter(
            name="api_requests_failure_total",
            help="Total number of failed API requests"
        )

        self.api_request_duration = Histogram(
            name="api_request_duration_seconds",
            help="API request duration in seconds"
        )

        # ===== LLM使用统计 =====
        self.llm_tokens_total = Counter(
            name="llm_tokens_total",
            help="Total number of LLM tokens consumed"
        )

        self.llm_cost_total = Gauge(
            name="llm_cost_total_yuan",
            help="Total LLM cost in CNY"
        )

        self.llm_requests_by_tier = defaultdict(lambda: Counter(
            name="llm_requests_by_tier_total",
            help="LLM requests by tier (small/medium/large)"
        ))

        # ===== 任务进度指标 =====
        self.task_progress = Gauge(
            name="task_progress_ratio",
            help="Task progress ratio (0.0 to 1.0)"
        )

        self.task_completed_steps = Counter(
            name="task_completed_steps_total",
            help="Total completed steps in current task"
        )

        # ===== 数据源统计 =====
        self.data_source_requests = defaultdict(lambda: Counter(
            name="data_source_requests_total",
            help="Data source requests by provider"
        ))

        self.data_source_failures = defaultdict(lambda: Counter(
            name="data_source_failures_total",
            help="Data source failures by provider"
        ))

        logger.info("📊 Metrics Collector initialized")

    def record_heartbeat(self, last_heartbeat: Optional[datetime]):
        """记录心跳时间"""
        if last_heartbeat:
            elapsed = (datetime.now() - last_heartbeat).total_seconds()
            self.heartbeat_status.set(elapsed)

    def record_restart(self):
        """记录重启事件"""
        with self._lock:
            self.restart_count.inc()

    def record_health(self, is_healthy: bool):
        """记录健康状态"""
        self.health_status.set(1.0 if is_healthy else 0.0)

    def record_cache_hit(self):
        """记录缓存命中"""
        with self._lock:
            self.cache_hits.inc()
            self._update_cache_hit_rate()

    def record_cache_miss(self):
        """记录缓存未命中"""
        with self._lock:
            self.cache_misses.inc()
            self._update_cache_hit_rate()

    def _update_cache_hit_rate(self):
        """更新缓存命中率"""
        total = self.cache_hits.value + self.cache_misses.value
        if total > 0:
            hit_rate = self.cache_hits.value / total
            self.cache_hit_rate.set(hit_rate)

    def record_api_request(self, success: bool, duration: float):
        """记录API请求"""
        with self._lock:
            self.api_requests_total.inc()
            if success:
                self.api_requests_success.inc()
            else:
                self.api_requests_failure.inc()
            self.api_request_duration.observe(duration)

    def record_llm_usage(self, tokens: int, cost: float, tier: str = "medium"):
        """记录LLM使用"""
        with self._lock:
            self.llm_tokens_total.inc(tokens)
            self.llm_cost_total.inc(cost)
            self.llm_requests_by_tier[tier].inc()

    def record_task_progress(self, progress: float, completed_steps: int):
        """记录任务进度"""
        self.task_progress.set(progress)
        self.task_completed_steps.value = completed_steps

    def record_data_source_request(self, provider: str, success: bool):
        """记录数据源请求"""
        with self._lock:
            self.data_source_requests[provider].inc()
            if not success:
                self.data_source_failures[provider].inc()

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取所有指标（REST API格式）

        Returns:
            指标字典
        """
        with self._lock:
            # 计算缓存命中率
            cache_total = self.cache_hits.value + self.cache_misses.value
            cache_hit_rate = (self.cache_hits.value / cache_total) if cache_total > 0 else 0.0

            # 计算API成功率
            api_total = self.api_requests_total.value
            api_success_rate = (self.api_requests_success.value / api_total) if api_total > 0 else 0.0

            return {
                "timestamp": datetime.now().isoformat(),
                "system_health": {
                    "heartbeat_seconds": self.heartbeat_status.value,
                    "restart_count": self.restart_count.value,
                    "is_healthy": self.health_status.value == 1.0,
                },
                "cache_performance": {
                    "hits": self.cache_hits.value,
                    "misses": self.cache_misses.value,
                    "total": cache_total,
                    "hit_rate": cache_hit_rate,
                },
                "api_statistics": {
                    "total_requests": api_total,
                    "successful_requests": self.api_requests_success.value,
                    "failed_requests": self.api_requests_failure.value,
                    "success_rate": api_success_rate,
                    "duration_stats": self.api_request_duration.get_summary(),
                },
                "llm_usage": {
                    "total_tokens": self.llm_tokens_total.value,
                    "total_cost_yuan": self.llm_cost_total.value,
                    "requests_by_tier": {
                        tier: counter.value
                        for tier, counter in self.llm_requests_by_tier.items()
                    },
                },
                "task_progress": {
                    "progress_ratio": self.task_progress.value,
                    "completed_steps": self.task_completed_steps.value,
                },
                "data_sources": {
                    provider: {
                        "total_requests": self.data_source_requests[provider].value,
                        "failed_requests": self.data_source_failures[provider].value,
                    }
                    for provider in self.data_source_requests.keys()
                },
            }

    def get_prometheus_format(self) -> str:
        """
        获取Prometheus文本格式指标

        Returns:
            Prometheus格式的指标文本
        """
        lines = []

        # Helper function to add metric
        def add_metric(metric_type: str, metric):
            lines.append(f"# HELP {metric.name} {metric.help}")
            lines.append(f"# TYPE {metric.name} {metric_type}")
            if hasattr(metric, 'value'):
                lines.append(f"{metric.name} {metric.value}")
            lines.append("")

        # System health
        add_metric("gauge", self.heartbeat_status)
        add_metric("counter", self.restart_count)
        add_metric("gauge", self.health_status)

        # Cache performance
        add_metric("counter", self.cache_hits)
        add_metric("counter", self.cache_misses)
        add_metric("gauge", self.cache_hit_rate)

        # API statistics
        add_metric("counter", self.api_requests_total)
        add_metric("counter", self.api_requests_success)
        add_metric("counter", self.api_requests_failure)

        # Histogram for API duration
        summary = self.api_request_duration.get_summary()
        lines.append(f"# HELP {self.api_request_duration.name} {self.api_request_duration.help}")
        lines.append(f"# TYPE {self.api_request_duration.name} histogram")
        lines.append(f"{self.api_request_duration.name}_count {summary['count']}")
        lines.append(f"{self.api_request_duration.name}_sum {summary['sum']}")
        lines.append("")

        # LLM usage
        add_metric("counter", self.llm_tokens_total)
        add_metric("gauge", self.llm_cost_total)

        for tier, counter in self.llm_requests_by_tier.items():
            lines.append(f"# HELP {counter.name} {counter.help}")
            lines.append(f"# TYPE {counter.name} counter")
            lines.append(f'{counter.name}{{tier="{tier}"}} {counter.value}')
            lines.append("")

        # Task progress
        add_metric("gauge", self.task_progress)
        add_metric("counter", self.task_completed_steps)

        # Data sources
        for provider, counter in self.data_source_requests.items():
            lines.append(f"# HELP {counter.name} {counter.help}")
            lines.append(f"# TYPE {counter.name} counter")
            lines.append(f'{counter.name}{{provider="{provider}"}} {counter.value}')
            lines.append("")

        for provider, counter in self.data_source_failures.items():
            lines.append(f"# HELP {counter.name} {counter.help}")
            lines.append(f"# TYPE {counter.name} counter")
            lines.append(f'{counter.name}{{provider="{provider}"}} {counter.value}')
            lines.append("")

        return "\n".join(lines)

    def reset(self):
        """重置所有指标（用于测试）"""
        with self._lock:
            self.cache_hits.reset()
            self.cache_misses.reset()
            self.api_requests_total.reset()
            self.api_requests_success.reset()
            self.api_requests_failure.reset()
            self.llm_tokens_total.reset()
            self.restart_count.reset()
            self.task_completed_steps.reset()
            self.llm_requests_by_tier.clear()
            self.data_source_requests.clear()
            self.data_source_failures.clear()
            logger.info("📊 All metrics reset")


# 全局指标收集器实例（单例）
_global_metrics: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    获取全局指标收集器实例（单例模式）

    Returns:
        MetricsCollector实例
    """
    global _global_metrics

    if _global_metrics is None:
        _global_metrics = MetricsCollector()

    return _global_metrics


def reset_metrics_collector():
    """重置全局指标收集器（用于测试）"""
    global _global_metrics
    if _global_metrics:
        _global_metrics.reset()
    _global_metrics = None
