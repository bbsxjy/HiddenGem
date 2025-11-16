"""
Retry Wrapper with Exponential Backoff

This module provides retry logic for API calls with exponential backoff.
Specifically designed to handle rate limiting (429) errors.

Usage:
    from tradingagents.utils.retry_wrapper import with_retry

    @with_retry(provider='siliconflow')
    def my_api_call():
        return client.chat.completions.create(...)
"""

import time
import random
from functools import wraps
from typing import Callable, Optional, Type, Tuple, Any
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.rate_limiter import get_rate_limiter

logger = get_logger("retry_wrapper")


class RateLimitError(Exception):
    """Custom exception for rate limit errors"""
    pass


def is_rate_limit_error(error: Exception) -> bool:
    """
    Check if an error is a rate limit error

    Checks for:
    - HTTP 429 status
    - Rate limit keywords in error message
    - OpenAI RateLimitError
    """
    error_str = str(error).lower()

    # Check for 429 status code
    if '429' in error_str:
        return True

    # Check for rate limit keywords
    rate_limit_keywords = [
        'rate limit',
        'rate_limit',
        'ratelimit',
        'too many requests',
        'tpm limit',
        'rpm limit',
        'quota exceeded',
        'throttle',
        'throttling'
    ]

    if any(keyword in error_str for keyword in rate_limit_keywords):
        return True

    # Check exception type
    error_type = type(error).__name__.lower()
    if 'ratelimit' in error_type:
        return True

    return False


def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable

    Includes:
    - Rate limit errors
    - Connection errors
    - Timeout errors
    - Server errors (5xx)
    """
    error_str = str(error).lower()

    # Rate limit errors
    if is_rate_limit_error(error):
        return True

    # Connection errors
    connection_keywords = [
        'connection',
        'connectionerror',
        'timeout',
        'timeouterror',
    ]
    if any(keyword in error_str for keyword in connection_keywords):
        return True

    # Server errors (5xx)
    server_error_codes = ['500', '502', '503', '504']
    if any(code in error_str for code in server_error_codes):
        return True

    return False


def with_retry(
    provider: str = 'default',
    max_attempts: int = 5,
    initial_delay: float = 2.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    enable_rate_limiter: bool = True,
    retry_on: Optional[Tuple[Type[Exception], ...]] = None,
):
    """
    Decorator for retry logic with exponential backoff and rate limiting

    Args:
        provider: Provider name for rate limiting (e.g., 'siliconflow')
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff (2.0 = double each time)
        jitter: Add random jitter to avoid thundering herd
        enable_rate_limiter: Use rate limiter before each call
        retry_on: Tuple of exception types to retry on (None = auto-detect)

    Example:
        @with_retry(provider='siliconflow', max_attempts=3)
        def call_api():
            return client.chat.completions.create(...)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get rate limiter if enabled
            rate_limiter = get_rate_limiter(provider) if enable_rate_limiter else None

            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    # Apply rate limiting before API call
                    if rate_limiter:
                        rate_limiter.acquire()
                        logger.debug(
                            f" [Retry:{provider}] 获取令牌成功 (attempt {attempt}/{max_attempts})"
                        )

                    # Make the actual API call
                    result = func(*args, **kwargs)

                    # Success!
                    if attempt > 1:
                        logger.info(
                            f" [Retry:{provider}] 重试成功 (attempt {attempt}/{max_attempts})"
                        )

                    return result

                except Exception as e:
                    last_exception = e

                    # Check if we should retry this error
                    should_retry = False

                    if retry_on is not None:
                        # Custom retry exceptions specified
                        should_retry = isinstance(e, retry_on)
                    else:
                        # Auto-detect retryable errors
                        should_retry = is_retryable_error(e)

                    # Log the error
                    error_type = "Rate Limit" if is_rate_limit_error(e) else "API"
                    logger.warning(
                        f" [Retry:{provider}] {error_type}错误 "
                        f"(attempt {attempt}/{max_attempts}): {str(e)[:200]}"
                    )

                    # Don't retry if max attempts reached
                    if attempt >= max_attempts:
                        logger.error(
                            f" [Retry:{provider}] 达到最大重试次数 ({max_attempts}), 放弃重试"
                        )
                        break

                    # Don't retry if not a retryable error
                    if not should_retry:
                        logger.error(
                            f" [Retry:{provider}] 不可重试的错误，立即失败"
                        )
                        break

                    # Calculate backoff delay
                    delay = min(
                        initial_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )

                    # Add jitter to avoid thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.info(
                        f"⏳ [Retry:{provider}] {delay:.2f}秒后重试 "
                        f"(attempt {attempt + 1}/{max_attempts})"
                    )

                    time.sleep(delay)

            # All retries failed
            logger.error(
                f" [Retry:{provider}] 所有重试失败，抛出最后一个异常"
            )
            raise last_exception

        return wrapper
    return decorator


def create_retryable_llm_wrapper(llm: Any, provider: str = 'default') -> Any:
    """
    Create a wrapper around an LLM that adds retry logic to its invoke method

    Args:
        llm: The LLM instance (e.g., ChatOpenAI)
        provider: Provider name for rate limiting

    Returns:
        Wrapped LLM with retry logic
    """
    class RetryableLLM:
        def __init__(self, original_llm, provider_name):
            self._llm = original_llm
            self._provider = provider_name
            # Copy over important class attributes to appear more like the original LLM
            self.__class__.__name__ = f"Retryable{original_llm.__class__.__name__}"

        @property
        def unwrapped(self):
            """Get the original unwrapped LLM"""
            return self._llm

        @property
        def invoke(self):
            """Wrap invoke method with retry logic"""
            @with_retry(provider=self._provider, max_attempts=5, initial_delay=2.0)
            def _invoke(*args, **kwargs):
                return self._llm.invoke(*args, **kwargs)
            return _invoke

        @property
        def ainvoke(self):
            """Wrap async invoke method with retry logic"""
            @with_retry(provider=self._provider, max_attempts=5, initial_delay=2.0)
            async def _ainvoke(*args, **kwargs):
                return await self._llm.ainvoke(*args, **kwargs)
            return _ainvoke

        @property
        def stream(self):
            """Wrap stream method with retry logic"""
            @with_retry(provider=self._provider, max_attempts=5, initial_delay=2.0)
            def _stream(*args, **kwargs):
                return self._llm.stream(*args, **kwargs)
            return _stream

        @property
        def astream(self):
            """Wrap async stream method with retry logic"""
            @with_retry(provider=self._provider, max_attempts=5, initial_delay=2.0)
            async def _astream(*args, **kwargs):
                return self._llm.astream(*args, **kwargs)
            return _astream

        def bind_tools(self, *args, **kwargs):
            """Forward bind_tools to original LLM and return the bound LLM directly"""
            # Bind tools to the original LLM
            bound_llm = self._llm.bind_tools(*args, **kwargs)
            # Don't wrap again - return the bound LLM directly
            # The retry logic is already applied at the invoke level
            return bound_llm

        def bind(self, *args, **kwargs):
            """Forward bind to original LLM"""
            bound_llm = self._llm.bind(*args, **kwargs)
            return bound_llm

        def __or__(self, other):
            """Support LangChain pipe operator (llm | other)"""
            # Forward to original LLM to avoid type checking issues
            return self._llm.__or__(other)

        def __ror__(self, other):
            """Support LangChain reverse pipe operator (other | llm)"""
            # This is called when: prompt | RetryableLLM
            # Forward to original LLM to avoid type checking issues
            return other.__or__(self._llm)

        def __getattr__(self, name):
            """Forward all other attributes to original LLM"""
            return getattr(self._llm, name)

    return RetryableLLM(llm, provider)


if __name__ == "__main__":
    # Test the retry wrapper
    import sys

    print("Testing retry wrapper...")

    # Simulate an API call that fails with rate limit error
    attempt_count = 0

    @with_retry(provider='test', max_attempts=3, initial_delay=1.0)
    def failing_api_call():
        global attempt_count
        attempt_count += 1
        print(f"  API call attempt {attempt_count}")

        if attempt_count < 3:
            raise Exception("Error code: 429 - Rate limit exceeded")

        return "Success!"

    try:
        result = failing_api_call()
        print(f"\n Result: {result}")
        print(f" Total attempts: {attempt_count}")
    except Exception as e:
        print(f"\n Failed: {e}")

    # Test non-retryable error
    print("\n\nTesting non-retryable error...")
    attempt_count = 0

    @with_retry(provider='test', max_attempts=3, initial_delay=1.0)
    def non_retryable_call():
        global attempt_count
        attempt_count += 1
        print(f"  API call attempt {attempt_count}")
        raise ValueError("Invalid parameter")

    try:
        result = non_retryable_call()
    except ValueError as e:
        print(f"\n Correctly failed immediately: {e}")
        print(f" Attempts: {attempt_count} (should be 1)")
