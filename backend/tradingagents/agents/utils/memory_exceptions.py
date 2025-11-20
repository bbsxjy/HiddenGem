"""
Memory 模块自定义异常
"""


class EmbeddingError(Exception):
    """Embedding 生成失败的基础异常"""
    pass


class EmbeddingServiceUnavailable(EmbeddingError):
    """Embedding 服务不可用"""
    def __init__(self, provider: str, reason: str = ""):
        self.provider = provider
        self.reason = reason
        message = f"Embedding服务不可用 (provider={provider})"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class EmbeddingTextTooLong(EmbeddingError):
    """文本过长，超出模型限制"""
    def __init__(self, text_length: int, max_length: int):
        self.text_length = text_length
        self.max_length = max_length
        message = f"文本过长 ({text_length:,} > {max_length:,} 字符)，无法生成embedding"
        super().__init__(message)


class EmbeddingInvalidInput(EmbeddingError):
    """输入文本无效"""
    def __init__(self, reason: str):
        self.reason = reason
        message = f"输入文本无效: {reason}"
        super().__init__(message)


class MemoryDisabled(EmbeddingError):
    """Memory功能已禁用"""
    def __init__(self):
        message = "Memory功能已被禁用 (MEMORY_ENABLED=false)"
        super().__init__(message)
