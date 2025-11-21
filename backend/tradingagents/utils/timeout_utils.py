# -*- coding: utf-8 -*-
"""
Timeout Utilities

为 DataFlow API 调用提供超时保护机制，防止长时间阻塞
"""

import logging
from typing import Callable, TypeVar, Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from functools import wraps
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')

# 全局线程池（避免频繁创建销毁线程）
_global_executor = None


def get_executor() -> ThreadPoolExecutor:
    """获取全局线程池实例（懒加载）"""
    global _global_executor
    if _global_executor is None:
        _global_executor = ThreadPoolExecutor(
            max_workers=10,
            thread_name_prefix="timeout_executor"
        )
    return _global_executor


def with_timeout(
    timeout_seconds: int = 30,
    fallback_value: Any = None,
    fallback_factory: Optional[Callable] = None
):
    """
    超时装饰器 - 为函数添加超时保护

    Args:
        timeout_seconds: 超时时间（秒）
        fallback_value: 超时后的fallback值（静态值）
        fallback_factory: 超时后的fallback值工厂函数（动态生成）

    Usage:
        @with_timeout(timeout_seconds=10, fallback_value="默认值")
        def slow_api_call(symbol: str) -> str:
            return some_slow_operation(symbol)

        # 使用 fallback_factory 动态生成fallback值
        @with_timeout(
            timeout_seconds=10,
            fallback_factory=lambda symbol: f"获取{symbol}数据超时"
        )
        def slow_api_call(symbol: str) -> str:
            return some_slow_operation(symbol)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            executor = get_executor()

            try:
                # 提交任务到线程池
                future = executor.submit(func, *args, **kwargs)

                # 等待结果，带超时
                result = future.result(timeout=timeout_seconds)

                duration = time.time() - start_time
                logger.debug(
                    f"✓ {func.__name__} 执行成功，耗时: {duration:.2f}s"
                )

                return result

            except FutureTimeoutError:
                duration = time.time() - start_time
                logger.warning(
                    f"⏰ {func.__name__} 超时（{timeout_seconds}秒），"
                    f"实际耗时: {duration:.2f}s"
                )

                # 尝试取消任务（如果可能）
                future.cancel()

                # 返回 fallback 值
                if fallback_factory is not None:
                    fallback = fallback_factory(*args, **kwargs)
                    logger.info(f"  使用 fallback_factory 生成值")
                    return fallback
                else:
                    logger.info(f"  使用 fallback_value: {fallback_value}")
                    return fallback_value

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"❌ {func.__name__} 执行失败: {e}，耗时: {duration:.2f}s",
                    exc_info=True
                )

                # 发生异常时也返回 fallback 值
                if fallback_factory is not None:
                    fallback = fallback_factory(*args, **kwargs)
                    return fallback
                else:
                    return fallback_value

        return wrapper

    return decorator


def safe_api_call(
    func: Callable[..., T],
    timeout_seconds: int = 30,
    fallback_value: Any = None,
    *args,
    **kwargs
) -> T:
    """
    安全的API调用包装器（函数式调用）

    Args:
        func: 要调用的函数
        timeout_seconds: 超时时间（秒）
        fallback_value: 超时/异常时的fallback值
        *args, **kwargs: 传递给func的参数

    Returns:
        函数结果或fallback值

    Usage:
        result = safe_api_call(
            slow_function,
            timeout_seconds=10,
            fallback_value="默认值",
            arg1="value1",
            arg2="value2"
        )
    """
    start_time = time.time()
    executor = get_executor()

    try:
        future = executor.submit(func, *args, **kwargs)
        result = future.result(timeout=timeout_seconds)

        duration = time.time() - start_time
        logger.debug(f"✓ {func.__name__} 执行成功，耗时: {duration:.2f}s")

        return result

    except FutureTimeoutError:
        duration = time.time() - start_time
        logger.warning(
            f"⏰ {func.__name__} 超时（{timeout_seconds}秒），"
            f"实际耗时: {duration:.2f}s"
        )

        future.cancel()
        return fallback_value

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"❌ {func.__name__} 执行失败: {e}，耗时: {duration:.2f}s",
            exc_info=True
        )

        return fallback_value


def shutdown_executor():
    """关闭全局线程池（仅在程序退出时调用）"""
    global _global_executor
    if _global_executor is not None:
        logger.info("关闭超时控制线程池...")
        _global_executor.shutdown(wait=True, cancel_futures=True)
        _global_executor = None
