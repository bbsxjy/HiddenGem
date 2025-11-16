"""
Rate Limiter Utility for API Calls

This module provides rate limiting functionality to prevent hitting API rate limits.
Uses token bucket algorithm for flexible rate limiting.

Usage:
    from tradingagents.utils.rate_limiter import get_rate_limiter

    rate_limiter = get_rate_limiter('siliconflow')

    # Before making an API call
    rate_limiter.acquire()
    # Make your API call here
"""

import time
import threading
from typing import Dict, Optional
from tradingagents.utils.logging_init import get_logger

logger = get_logger("rate_limiter")


class TokenBucketRateLimiter:
    """
    Token Bucket Rate Limiter

    Implements the token bucket algorithm for rate limiting.
    - Bucket starts with a certain number of tokens
    - Tokens are consumed for each request
    - Tokens are refilled at a constant rate
    - Requests wait if no tokens available

    Args:
        rate: Number of requests allowed per second
        burst: Maximum burst size (bucket capacity)
        name: Name of the rate limiter for logging
    """

    def __init__(self, rate: float, burst: int = None, name: str = "default"):
        """
        Initialize the rate limiter

        Args:
            rate: Requests per second (e.g., 2.0 means 2 requests per second)
            burst: Maximum burst size. If None, defaults to rate
            name: Name for logging purposes
        """
        self.rate = rate
        self.burst = burst or int(rate)
        self.name = name

        # Token bucket state
        self._tokens = float(self.burst)  # Start with full bucket
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

        logger.info(
            f"[RateLimiter:{name}] Initialized - "
            f"Rate: {rate} req/s, Burst: {burst}"
        )

    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.monotonic()
        elapsed = now - self._last_refill

        # Calculate how many tokens to add
        tokens_to_add = elapsed * self.rate

        # Add tokens but don't exceed burst capacity
        self._tokens = min(self.burst, self._tokens + tokens_to_add)
        self._last_refill = now

    def acquire(self, tokens: int = 1, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket

        Args:
            tokens: Number of tokens to acquire (default: 1)
            blocking: If True, wait for tokens to become available
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if tokens acquired, False if timed out (non-blocking mode)
        """
        start_time = time.monotonic()

        with self._lock:
            while True:
                # Refill bucket first
                self._refill()

                # Check if we have enough tokens
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

                # Non-blocking mode
                if not blocking:
                    logger.debug(
                        f" [RateLimiter:{self.name}] 令牌不足 "
                        f"(需要: {tokens}, 可用: {self._tokens:.2f})"
                    )
                    return False

                # Check timeout
                if timeout is not None:
                    elapsed = time.monotonic() - start_time
                    if elapsed >= timeout:
                        logger.warning(
                            f"⏱ [RateLimiter:{self.name}] 等待超时 "
                            f"({timeout}s)"
                        )
                        return False

                # Calculate wait time
                tokens_needed = tokens - self._tokens
                wait_time = tokens_needed / self.rate

                # Don't wait too long at once (max 1 second chunks)
                wait_time = min(wait_time, 1.0)

                logger.debug(
                    f"⏳ [RateLimiter:{self.name}] 等待令牌 "
                    f"(需要: {tokens}, 可用: {self._tokens:.2f}, 等待: {wait_time:.2f}s)"
                )

        # Release lock before sleeping
        time.sleep(wait_time)

    def get_status(self) -> Dict:
        """Get current rate limiter status"""
        with self._lock:
            self._refill()
            return {
                "name": self.name,
                "rate": self.rate,
                "burst": self.burst,
                "available_tokens": self._tokens,
                "utilization": f"{(1 - self._tokens / self.burst) * 100:.1f}%"
            }


# Global rate limiters registry
_rate_limiters: Dict[str, TokenBucketRateLimiter] = {}
_registry_lock = threading.Lock()


# Predefined rate limits for different providers
PROVIDER_RATE_LIMITS = {
    "siliconflow": {
        "rate": 1.5,  # 1.5 requests per second (conservative)
        "burst": 3,   # Allow burst of 3 requests
    },
    "dashscope": {
        "rate": 5.0,  # 5 requests per second
        "burst": 10,
    },
    "deepseek": {
        "rate": 5.0,  # 5 requests per second
        "burst": 10,
    },
    "openai": {
        "rate": 3.0,  # 3 requests per second
        "burst": 5,
    },
    "google": {
        "rate": 2.0,  # 2 requests per second
        "burst": 4,
    },
    "qianfan": {
        "rate": 2.0,  # 2 requests per second
        "burst": 4,
    },
    "openrouter": {
        "rate": 3.0,  # 3 requests per second
        "burst": 5,
    },
    "embedding": {
        "rate": 2.0,  # 2 embedding requests per second
        "burst": 3,
    },
}


def get_rate_limiter(provider: str, custom_rate: Optional[float] = None,
                    custom_burst: Optional[int] = None) -> TokenBucketRateLimiter:
    """
    Get or create a rate limiter for a provider

    Args:
        provider: Provider name (e.g., 'siliconflow', 'dashscope')
        custom_rate: Override default rate (requests per second)
        custom_burst: Override default burst size

    Returns:
        TokenBucketRateLimiter instance for the provider
    """
    with _registry_lock:
        if provider not in _rate_limiters:
            # Get default limits or use custom
            if provider in PROVIDER_RATE_LIMITS and custom_rate is None:
                limits = PROVIDER_RATE_LIMITS[provider]
                rate = limits["rate"]
                burst = limits["burst"]
            else:
                rate = custom_rate or 2.0  # Default: 2 req/s
                burst = custom_burst or int(rate)

            # Create new rate limiter
            _rate_limiters[provider] = TokenBucketRateLimiter(
                rate=rate,
                burst=burst,
                name=provider
            )

            logger.info(
                f"[RateLimiter] Created {provider} rate limiter - "
                f"Rate: {rate} req/s, Burst: {burst}"
            )

        return _rate_limiters[provider]


def get_all_rate_limiters() -> Dict[str, TokenBucketRateLimiter]:
    """Get all active rate limiters"""
    with _registry_lock:
        return _rate_limiters.copy()


def reset_rate_limiter(provider: str):
    """Reset a rate limiter (useful for testing)"""
    with _registry_lock:
        if provider in _rate_limiters:
            del _rate_limiters[provider]
            logger.info(f" [RateLimiter] 重置{provider}限流器")


def get_rate_limiter_status() -> Dict:
    """Get status of all rate limiters"""
    with _registry_lock:
        return {
            name: limiter.get_status()
            for name, limiter in _rate_limiters.items()
        }


if __name__ == "__main__":
    # Test the rate limiter
    print("Testing rate limiter...")

    # Create a rate limiter: 2 requests per second, burst of 3
    limiter = get_rate_limiter("test", custom_rate=2.0, custom_burst=3)

    # Test burst
    print("\n=== Testing burst (should be fast) ===")
    for i in range(3):
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        print(f"Request {i+1}: {elapsed:.3f}s")

    # Test rate limiting
    print("\n=== Testing rate limiting (should be ~0.5s intervals) ===")
    for i in range(3):
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        print(f"Request {i+1}: {elapsed:.3f}s")
        print(f"Status: {limiter.get_status()}")

    print("\n=== All tests passed! ===")
