"""
Monitoring API Endpoints

提供监控指标的REST API端点：
- /api/v1/metrics - JSON格式指标
- /api/v1/metrics/prometheus - Prometheus文本格式
- /api/v1/health - 健康检查端点
"""

from fastapi import APIRouter, Response
from typing import Dict, Any

from tradingagents.utils.monitoring_metrics import get_metrics_collector
from tradingagents.utils.logging_init import get_logger

logger = get_logger("monitoring_api")

router = APIRouter(prefix="/api/v1", tags=["monitoring"])


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    获取监控指标（JSON格式）

    Returns:
        监控指标字典
    """
    try:
        collector = get_metrics_collector()
        metrics = collector.get_metrics()

        logger.debug("📊 Metrics fetched successfully")

        return {
            "success": True,
            "data": metrics,
            "message": "Metrics retrieved successfully"
        }

    except Exception as e:
        logger.error(f"❌ Failed to fetch metrics: {e}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "METRICS_ERROR",
                "message": str(e)
            }
        }


@router.get("/metrics/prometheus", response_class=Response)
async def get_prometheus_metrics():
    """
    获取Prometheus格式的监控指标

    Returns:
        Prometheus文本格式的指标
    """
    try:
        collector = get_metrics_collector()
        prometheus_text = collector.get_prometheus_format()

        logger.debug("📊 Prometheus metrics generated")

        return Response(
            content=prometheus_text,
            media_type="text/plain; version=0.0.4"
        )

    except Exception as e:
        logger.error(f"❌ Failed to generate Prometheus metrics: {e}", exc_info=True)
        return Response(
            content=f"# ERROR: {str(e)}\n",
            media_type="text/plain"
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康检查端点

    用于Kubernetes/Docker健康探测

    Returns:
        健康状态
    """
    try:
        collector = get_metrics_collector()
        metrics = collector.get_metrics()

        system_health = metrics.get("system_health", {})
        is_healthy = system_health.get("is_healthy", False)

        status_code = 200 if is_healthy else 503

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": metrics.get("timestamp"),
            "details": {
                "heartbeat_seconds": system_health.get("heartbeat_seconds"),
                "restart_count": system_health.get("restart_count"),
            }
        }

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/metrics/reset")
async def reset_metrics() -> Dict[str, Any]:
    """
    重置所有监控指标

    ⚠️  警告：仅用于测试环境，生产环境不应使用

    Returns:
        操作结果
    """
    try:
        collector = get_metrics_collector()
        collector.reset()

        logger.warning("⚠️  All metrics have been reset!")

        return {
            "success": True,
            "message": "All metrics reset successfully"
        }

    except Exception as e:
        logger.error(f"❌ Failed to reset metrics: {e}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "RESET_ERROR",
                "message": str(e)
            }
        }


@router.get("/metrics/summary")
async def get_metrics_summary() -> Dict[str, Any]:
    """
    获取指标摘要（简化版本，用于快速查看）

    Returns:
        指标摘要
    """
    try:
        collector = get_metrics_collector()
        metrics = collector.get_metrics()

        # 提取关键指标
        summary = {
            "system": {
                "healthy": metrics["system_health"]["is_healthy"],
                "restart_count": metrics["system_health"]["restart_count"],
            },
            "cache": {
                "hit_rate": f"{metrics['cache_performance']['hit_rate']:.2%}",
                "total_requests": metrics['cache_performance']['total'],
            },
            "api": {
                "success_rate": f"{metrics['api_statistics']['success_rate']:.2%}",
                "total_requests": metrics['api_statistics']['total_requests'],
            },
            "llm": {
                "total_tokens": metrics['llm_usage']['total_tokens'],
                "total_cost_yuan": f"¥{metrics['llm_usage']['total_cost_yuan']:.2f}",
            },
            "task": {
                "progress": f"{metrics['task_progress']['progress_ratio']:.1%}",
                "completed_steps": metrics['task_progress']['completed_steps'],
            }
        }

        return {
            "success": True,
            "data": summary,
            "timestamp": metrics.get("timestamp")
        }

    except Exception as e:
        logger.error(f"❌ Failed to fetch metrics summary: {e}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "SUMMARY_ERROR",
                "message": str(e)
            }
        }
