#!/usr/bin/env python3
"""
TTL (Time-To-Live) 缓存模块
提供带有过期时间的缓存装饰器，避免重复的API请求
"""

import time
import pickle
import hashlib
import functools
from pathlib import Path
from typing import Any, Callable, Optional, Dict, Tuple
from datetime import datetime, timedelta
from threading import Lock

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('dataflows.cache')


class TTLCache:
    """带有TTL的内存缓存"""

    def __init__(self, default_ttl: int = 3600):
        """
        初始化TTL缓存

        Args:
            default_ttl: 默认过期时间（秒），默认1小时
        """
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存的值，如果不存在或已过期返回None
        """
        with self._lock:
            if key in self._cache:
                value, expire_time = self._cache[key]
                if time.time() < expire_time:
                    self._hits += 1
                    logger.debug(f"缓存命中: {key[:50]}...")
                    return value
                else:
                    # 过期了，删除
                    del self._cache[key]
                    logger.debug(f"缓存已过期: {key[:50]}...")

            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），如果为None则使用默认值
        """
        if ttl is None:
            ttl = self.default_ttl

        expire_time = time.time() + ttl

        with self._lock:
            self._cache[key] = (value, expire_time)
            logger.debug(f"缓存写入: {key[:50]}... (TTL={ttl}秒)")

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("缓存已清空")

    def cleanup_expired(self):
        """清理所有过期的缓存"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, expire_time) in self._cache.items()
                if current_time >= expire_time
            ]
            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"清理了 {len(expired_keys)} 个过期缓存")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0

            return {
                "cache_size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.2%}",
                "total_requests": total_requests
            }


class DiskCache:
    """磁盘缓存，用于持久化存储"""

    def __init__(self, cache_dir: str = "./cache", default_ttl: int = 86400):
        """
        初始化磁盘缓存

        Args:
            cache_dir: 缓存目录
            default_ttl: 默认过期时间（秒），默认24小时
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用哈希避免文件名过长
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.pkl"

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存的值，如果不存在或已过期返回None
        """
        cache_path = self._get_cache_path(key)

        with self._lock:
            if not cache_path.exists():
                self._misses += 1
                return None

            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)

                value, expire_time = data['value'], data['expire_time']

                if time.time() < expire_time:
                    self._hits += 1
                    logger.debug(f"磁盘缓存命中: {key[:50]}...")
                    return value
                else:
                    # 过期了，删除文件
                    cache_path.unlink()
                    logger.debug(f"磁盘缓存已过期: {key[:50]}...")
                    self._misses += 1
                    return None

            except Exception as e:
                logger.warning(f"读取磁盘缓存失败: {e}")
                self._misses += 1
                return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），如果为None则使用默认值
        """
        if ttl is None:
            ttl = self.default_ttl

        expire_time = time.time() + ttl
        cache_path = self._get_cache_path(key)

        with self._lock:
            try:
                data = {
                    'value': value,
                    'expire_time': expire_time,
                    'created_at': time.time()
                }

                with open(cache_path, 'wb') as f:
                    pickle.dump(data, f)

                logger.debug(f"磁盘缓存写入: {key[:50]}... (TTL={ttl}秒)")

            except Exception as e:
                logger.warning(f"写入磁盘缓存失败: {e}")

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            for cache_file in self.cache_dir.glob("*.pkl"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.warning(f"删除缓存文件失败 {cache_file}: {e}")

            self._hits = 0
            self._misses = 0
            logger.info("磁盘缓存已清空")

    def cleanup_expired(self):
        """清理所有过期的缓存"""
        with self._lock:
            current_time = time.time()
            cleaned = 0

            for cache_file in self.cache_dir.glob("*.pkl"):
                try:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)

                    if current_time >= data['expire_time']:
                        cache_file.unlink()
                        cleaned += 1

                except Exception as e:
                    logger.warning(f"清理缓存文件失败 {cache_file}: {e}")

            if cleaned > 0:
                logger.debug(f"清理了 {cleaned} 个过期的磁盘缓存")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_files = len(list(self.cache_dir.glob("*.pkl")))
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0

            # 计算缓存总大小
            total_size = sum(
                f.stat().st_size for f in self.cache_dir.glob("*.pkl")
            )

            return {
                "cache_files": total_files,
                "cache_size_mb": total_size / (1024 * 1024),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.2%}",
                "total_requests": total_requests
            }


class HybridCache:
    """混合缓存：内存缓存 + 磁盘缓存"""

    def __init__(
        self,
        memory_ttl: int = 3600,  # 内存缓存1小时
        disk_ttl: int = 86400,   # 磁盘缓存24小时
        cache_dir: str = "./cache"
    ):
        """
        初始化混合缓存

        Args:
            memory_ttl: 内存缓存过期时间（秒）
            disk_ttl: 磁盘缓存过期时间（秒）
            cache_dir: 磁盘缓存目录
        """
        self.memory_cache = TTLCache(default_ttl=memory_ttl)
        self.disk_cache = DiskCache(cache_dir=cache_dir, default_ttl=disk_ttl)
        self.memory_ttl = memory_ttl
        self.disk_ttl = disk_ttl

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值（先查内存，再查磁盘）

        Args:
            key: 缓存键

        Returns:
            缓存的值，如果不存在或已过期返回None
        """
        # 先查内存缓存
        value = self.memory_cache.get(key)
        if value is not None:
            return value

        # 内存没有，查磁盘缓存
        value = self.disk_cache.get(key)
        if value is not None:
            # 从磁盘加载到内存
            self.memory_cache.set(key, value, self.memory_ttl)
            return value

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        设置缓存值（同时写入内存和磁盘）

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
        """
        # 写入内存缓存
        self.memory_cache.set(key, value, ttl or self.memory_ttl)

        # 写入磁盘缓存
        self.disk_cache.set(key, value, ttl or self.disk_ttl)

    def clear(self):
        """清空所有缓存"""
        self.memory_cache.clear()
        self.disk_cache.clear()

    def cleanup_expired(self):
        """清理所有过期的缓存"""
        self.memory_cache.cleanup_expired()
        self.disk_cache.cleanup_expired()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "memory": self.memory_cache.get_stats(),
            "disk": self.disk_cache.get_stats()
        }


# 全局缓存实例
_global_cache = HybridCache()


def get_cache() -> HybridCache:
    """获取全局缓存实例"""
    return _global_cache


def ttl_cache(
    ttl: Optional[int] = None,
    cache_key_func: Optional[Callable] = None,
    use_disk: bool = True
):
    """
    TTL 缓存装饰器

    Args:
        ttl: 过期时间（秒），None表示使用默认值
        cache_key_func: 自定义缓存键生成函数
        use_disk: 是否使用磁盘缓存

    Example:
        @ttl_cache(ttl=3600)  # 缓存1小时
        def get_stock_data(symbol: str, date: str):
            # 耗时的数据获取操作
            return data
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                # 默认缓存键：函数名 + 参数
                cache_key = f"{func.__module__}.{func.__name__}:{args}:{sorted(kwargs.items())}"

            # 尝试从缓存获取
            cached_value = _global_cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 缓存未命中，执行函数
            result = func(*args, **kwargs)

            # 写入缓存
            if result is not None:  # 只缓存非None结果
                _global_cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


def cache_stats():
    """打印缓存统计信息"""
    stats = _global_cache.get_stats()

    print("=" * 60)
    print("📊 缓存统计信息")
    print("=" * 60)

    print("\n内存缓存:")
    for key, value in stats['memory'].items():
        print(f"  {key}: {value}")

    print("\n磁盘缓存:")
    for key, value in stats['disk'].items():
        print(f"  {key}: {value}")

    print("=" * 60)


def clear_cache():
    """清空所有缓存"""
    _global_cache.clear()
    logger.info("所有缓存已清空")


def cleanup_expired_cache():
    """清理过期缓存"""
    _global_cache.cleanup_expired()
    logger.info("过期缓存已清理")


if __name__ == "__main__":
    # 测试缓存功能
    import sys

    # Windows UTF-8编码
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # 测试装饰器
    @ttl_cache(ttl=5)  # 5秒过期
    def expensive_operation(x: int) -> int:
        print(f"执行耗时操作: x={x}")
        time.sleep(1)  # 模拟耗时操作
        return x * 2

    print("第一次调用（缓存未命中）:")
    result1 = expensive_operation(10)
    print(f"结果: {result1}\n")

    print("第二次调用（缓存命中）:")
    result2 = expensive_operation(10)
    print(f"结果: {result2}\n")

    print("等待6秒后调用（缓存过期）:")
    time.sleep(6)
    result3 = expensive_operation(10)
    print(f"结果: {result3}\n")

    # 打印统计信息
    cache_stats()
