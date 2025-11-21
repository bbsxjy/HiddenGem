"""
API层异常处理工具

提供统一的异常处理机制，将内部异常转换为用户友好的HTTP响应
"""

from fastapi import HTTPException
from typing import Callable, Any
import logging
from functools import wraps

# 导入memory相关异常
from tradingagents.agents.utils.memory_exceptions import (
    EmbeddingError,
    EmbeddingServiceUnavailable,
    EmbeddingTextTooLong,
    EmbeddingInvalidInput,
    MemoryDisabled
)

logger = logging.getLogger(__name__)


def handle_memory_exception(e: Exception, operation: str = "操作") -> HTTPException:
    """
    处理memory相关异常，返回用户友好的HTTPException

    Args:
        e: 捕获的异常
        operation: 操作描述（用于日志和错误消息）

    Returns:
        HTTPException with appropriate status code and user-friendly message
    """

    if isinstance(e, MemoryDisabled):
        # Memory功能被禁用 - 503 Service Unavailable
        logger.warning(f"⚠️ [{operation}] Memory功能已禁用")
        return HTTPException(
            status_code=503,
            detail={
                "error": "MEMORY_DISABLED",
                "message": "记忆功能当前不可用",
                "description": "系统记忆功能已被禁用。分析将继续进行，但无法利用历史经验。",
                "suggestion": "检查环境变量 DASHSCOPE_API_KEY 或 OPENAI_API_KEY 是否已配置",
                "impact": "分析结果不会受到历史记忆的影响，可能略微降低准确性"
            }
        )

    elif isinstance(e, EmbeddingServiceUnavailable):
        # Embedding服务不可用 - 503 Service Unavailable
        provider = getattr(e, 'provider', 'unknown')
        reason = getattr(e, 'reason', '')
        logger.error(f"❌ [{operation}] Embedding服务不可用: provider={provider}, reason={reason}")
        return HTTPException(
            status_code=503,
            detail={
                "error": "EMBEDDING_SERVICE_UNAVAILABLE",
                "message": f"向量生成服务暂时不可用 (provider: {provider})",
                "description": f"无法连接到embedding服务。{reason}",
                "suggestion": "请稍后重试，或检查API密钥和网络连接",
                "impact": "分析将在无历史记忆的情况下继续进行"
            }
        )

    elif isinstance(e, EmbeddingTextTooLong):
        # 文本过长（虽然现在有chunking，但仍可能出现） - 400 Bad Request
        text_length = getattr(e, 'text_length', 0)
        max_length = getattr(e, 'max_length', 0)
        logger.warning(f"⚠️ [{operation}] 文本超长: {text_length}/{max_length} 字符")
        return HTTPException(
            status_code=400,
            detail={
                "error": "EMBEDDING_TEXT_TOO_LONG",
                "message": "分析文本过长",
                "description": f"文本长度 ({text_length:,} 字符) 超过了系统限制 ({max_length:,} 字符)",
                "suggestion": "尝试缩短时间范围或减少分析内容",
                "impact": "部分分析内容可能未被完全处理"
            }
        )

    elif isinstance(e, EmbeddingInvalidInput):
        # 输入无效 - 400 Bad Request
        reason = getattr(e, 'reason', '未知原因')
        logger.error(f"❌ [{operation}] 无效输入: {reason}")
        return HTTPException(
            status_code=400,
            detail={
                "error": "EMBEDDING_INVALID_INPUT",
                "message": "输入数据无效",
                "description": f"输入验证失败: {reason}",
                "suggestion": "请检查输入参数的有效性",
                "impact": "无法进行向量生成"
            }
        )

    elif isinstance(e, EmbeddingError):
        # 其他embedding错误（基类） - 500 Internal Server Error
        logger.error(f"❌ [{operation}] Embedding错误: {str(e)}")
        return HTTPException(
            status_code=500,
            detail={
                "error": "EMBEDDING_ERROR",
                "message": "向量生成过程中发生错误",
                "description": str(e),
                "suggestion": "请联系系统管理员或稍后重试",
                "impact": "分析可能在无历史记忆的情况下继续"
            }
        )

    else:
        # 不是memory相关异常，返回None表示需要其他处理
        return None


def with_memory_exception_handling(operation_name: str = "API操作"):
    """
    装饰器：为函数添加memory异常处理

    Args:
        operation_name: 操作名称（用于日志）

    Usage:
        @with_memory_exception_handling("分析股票")
        def analyze_stock(symbol: str):
            # ... 可能抛出memory异常的代码
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except (MemoryDisabled, EmbeddingServiceUnavailable,
                    EmbeddingTextTooLong, EmbeddingInvalidInput, EmbeddingError) as e:
                # 处理memory相关异常
                http_exception = handle_memory_exception(e, operation_name)
                if http_exception:
                    raise http_exception
                else:
                    # 如果返回None，说明不是memory异常，重新抛出
                    raise
            except Exception:
                # 其他异常继续抛出
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except (MemoryDisabled, EmbeddingServiceUnavailable,
                    EmbeddingTextTooLong, EmbeddingInvalidInput, EmbeddingError) as e:
                # 处理memory相关异常
                http_exception = handle_memory_exception(e, operation_name)
                if http_exception:
                    raise http_exception
                else:
                    # 如果返回None，说明不是memory异常，重新抛出
                    raise
            except Exception:
                # 其他异常继续抛出
                raise

        # 根据函数类型返回不同的wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def wrap_trading_graph_call(
    operation: str,
    func: Callable,
    *args,
    **kwargs
) -> Any:
    """
    包装trading_graph调用，添加memory异常处理

    Args:
        operation: 操作描述
        func: 要调用的函数（通常是trading_graph.propagate）
        *args: 函数参数
        **kwargs: 函数关键字参数

    Returns:
        函数返回值

    Raises:
        HTTPException: 如果发生memory相关异常

    Usage:
        try:
            final_state, signal = wrap_trading_graph_call(
                "分析股票600519",
                trading_graph.propagate,
                "600519.SH",
                "2025-11-21"
            )
        except HTTPException as e:
            # 处理用户友好的错误
            pass
    """
    try:
        return func(*args, **kwargs)
    except (MemoryDisabled, EmbeddingServiceUnavailable,
            EmbeddingTextTooLong, EmbeddingInvalidInput, EmbeddingError) as e:
        # 处理memory相关异常
        http_exception = handle_memory_exception(e, operation)
        if http_exception:
            raise http_exception
        else:
            # 理论上不应该到达这里
            raise
    except Exception:
        # 其他异常继续抛出，由调用者处理
        raise
