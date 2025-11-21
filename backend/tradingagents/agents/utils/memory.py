import chromadb
from chromadb.config import Settings
from openai import OpenAI
import dashscope
from dashscope import TextEmbedding
import os
import threading
import hashlib
from typing import Dict, Optional, List

# 导入自定义异常
from .memory_exceptions import (
    EmbeddingError,
    EmbeddingServiceUnavailable,
    EmbeddingTextTooLong,
    EmbeddingInvalidInput,
    MemoryDisabled
)

# 导入统一日志系统
from tradingagents.utils.logging_manager import get_logger
logger = get_logger("agents.utils.memory")


class ChromaDBManager:
    """单例ChromaDB管理器，避免并发创建集合的冲突

    支持持久化和非持久化两种模式：
    - 非持久化：用于TradingAgents内部的短期记忆（会话级）
    - 持久化：用于长期记忆存储（格言库）
    """

    _instance = None
    _lock = threading.Lock()
    _collections: Dict[str, any] = {}
    _client = None
    _persistent_client = None  # 新增：持久化客户端

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ChromaDBManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            try:
                # 自动检测操作系统版本并使用最优配置
                import platform
                system = platform.system()

                if system == "Windows":
                    # 使用改进的Windows 11检测
                    from .chromadb_win11_config import is_windows_11
                    if is_windows_11():
                        # Windows 11 或更新版本，使用优化配置
                        from .chromadb_win11_config import get_win11_chromadb_client
                        self._client = get_win11_chromadb_client()
                        logger.info(f" [ChromaDB] Windows 11优化配置初始化完成 (构建号: {platform.version()})")
                    else:
                        # Windows 10 或更老版本，使用兼容配置
                        from .chromadb_win10_config import get_win10_chromadb_client
                        self._client = get_win10_chromadb_client()
                        logger.info(f" [ChromaDB] Windows 10兼容配置初始化完成")
                else:
                    # 非Windows系统，使用标准配置
                    settings = Settings(
                        allow_reset=True,
                        anonymized_telemetry=False,
                        is_persistent=False
                    )
                    self._client = chromadb.Client(settings)
                    logger.info(f" [ChromaDB] {system}标准配置初始化完成")

                # 初始化持久化客户端（用于长期记忆）
                persist_path = os.getenv('MEMORY_PERSIST_PATH', './memory_db/maxims')
                try:
                    self._persistent_client = chromadb.PersistentClient(path=persist_path)
                    logger.info(f" [ChromaDB] 持久化客户端初始化完成: {persist_path}")
                except Exception as persist_error:
                    logger.warning(f" [ChromaDB] 持久化客户端初始化失败: {persist_error}")
                    self._persistent_client = None

                self._initialized = True
            except Exception as e:
                logger.error(f" [ChromaDB] 初始化失败: {e}")
                # 使用最简单的配置作为备用
                try:
                    settings = Settings(
                        allow_reset=True,
                        anonymized_telemetry=False,  # 关键：禁用遥测
                        is_persistent=False
                    )
                    self._client = chromadb.Client(settings)
                    logger.info(f" [ChromaDB] 使用备用配置初始化完成")
                except Exception as backup_error:
                    # 最后的备用方案
                    self._client = chromadb.Client()
                    logger.warning(f" [ChromaDB] 使用最简配置初始化: {backup_error}")
                self._initialized = True

    def get_or_create_collection(self, name: str, persistent: bool = False):
        """线程安全地获取或创建集合

        Args:
            name: 集合名称
            persistent: 是否使用持久化客户端
                - False（默认）：使用内存客户端（会话级）
                - True：使用持久化客户端（永久存储）
        """
        with self._lock:
            # 为持久化集合使用不同的缓存键
            cache_key = f"{name}_persistent" if persistent else name

            if cache_key in self._collections:
                logger.info(f" [ChromaDB] 使用缓存集合: {cache_key}")
                return self._collections[cache_key]

            # 选择使用哪个客户端
            client = self._persistent_client if persistent else self._client

            if persistent and client is None:
                logger.error(f" [ChromaDB] 持久化客户端不可用，回退到内存客户端")
                client = self._client
                persistent = False  # 回退标记

            try:
                # 尝试获取现有集合
                collection = client.get_collection(name=name)
                logger.info(f" [ChromaDB] 获取{'持久化' if persistent else '内存'}集合: {name}")
            except Exception:
                try:
                    # 创建新集合
                    collection = client.create_collection(name=name)
                    logger.info(f" [ChromaDB] 创建{'持久化' if persistent else '内存'}集合: {name}")
                except Exception as e:
                    # 可能是并发创建，再次尝试获取
                    try:
                        collection = client.get_collection(name=name)
                        logger.info(f" [ChromaDB] 并发创建后获取集合: {name}")
                    except Exception as final_error:
                        logger.error(f" [ChromaDB] 集合操作失败: {name}, 错误: {final_error}")
                        raise final_error

            # 缓存集合
            self._collections[cache_key] = collection
            return collection


class FinancialSituationMemory:
    """财务情况记忆库

    存储粗粒度的"经验格言"，用于快速检索相似情况的建议。
    支持持久化和非持久化两种模式。
    """

    def __init__(self, name, config, persistent: bool = False):
        """初始化记忆库

        Args:
            name: 集合名称
            config: 配置字典
            persistent: 是否持久化
                - False（默认）: 会话级记忆（服务器重启清空）
                - True: 永久存储（用于长期格言库）
        """
        self.name = name
        self.persistent = persistent
        self.config = config
        self.llm_provider = config.get("llm_provider", "openai").lower()

        # 配置向量缓存的长度限制（向量缓存默认启用长度检查）
        self.max_embedding_length = int(os.getenv('MAX_EMBEDDING_CONTENT_LENGTH', '50000'))  # 默认50K字符
        self.enable_embedding_length_check = os.getenv('ENABLE_EMBEDDING_LENGTH_CHECK', 'true').lower() == 'true'  # 向量缓存默认启用

        # 定义各模型的最大token限制（根据官方文档）
        self.model_token_limits = {
            'BAAI/bge-large-zh-v1.5': 512,      # SiliconFlow: 512 tokens
            'Qwen/Qwen3-Embedding-8B': 8192,    # SiliconFlow: 8192 tokens (Qwen3 Embedding)
            'text-embedding-v3': 8192,          # DashScope: 8192 tokens
            'text-embedding-3-small': 8191,     # OpenAI: 8191 tokens
            'nomic-embed-text': 8192,           # Ollama: 8192 tokens
        }

        # 每个token约等于2个中文字符（更保守的估计）
        # 注意：对于SiliconFlow的512 tokens限制，使用2会得到约460字符（留10%余量后）
        # 对于8192 tokens的模型，会得到约14700字符
        self.chars_per_token = 2  # 从3改为2，更保守的估计

        # Embedding结果缓存：避免短时间内重复调用
        self._embedding_cache = {}
        self._embedding_cache_ttl = 300  # 缓存5分钟

        # 根据LLM提供商选择嵌入模型和客户端
        # 初始化降级选项标志
        self.fallback_available = False
        
        if self.llm_provider == "dashscope" or self.llm_provider == "alibaba":
            self.embedding = "text-embedding-v3"
            self.client = None  # DashScope不需要OpenAI客户端

            # 设置DashScope API密钥
            dashscope_key = os.getenv('DASHSCOPE_API_KEY')
            if dashscope_key:
                try:
                    # 尝试导入和初始化DashScope
                    import dashscope
                    from dashscope import TextEmbedding

                    dashscope.api_key = dashscope_key
                    logger.info(f" DashScope API密钥已配置，启用记忆功能")

                    # 可选：测试API连接（简单验证）
                    # 这里不做实际调用，只验证导入和密钥设置

                except ImportError as e:
                    # DashScope包未安装
                    logger.error(f" DashScope包未安装: {e}")
                    self.client = "DISABLED"
                    logger.warning(f" 记忆功能已禁用")

                except Exception as e:
                    # 其他初始化错误
                    logger.error(f" DashScope初始化失败: {e}")
                    self.client = "DISABLED"
                    logger.warning(f" 记忆功能已禁用")
            else:
                # 没有DashScope密钥，禁用记忆功能
                self.client = "DISABLED"
                logger.warning(f" 未找到DASHSCOPE_API_KEY，记忆功能已禁用")
                logger.info(f" 系统将继续运行，但不会保存或检索历史记忆")
        elif self.llm_provider == "siliconflow":
            # SiliconFlow使用OpenAI兼容API
            siliconflow_key = os.getenv('SILICONFLOW_API_KEY')
            if siliconflow_key:
                try:
                    #  读取用户配置的embedding模型，如果没有则使用默认模型
                    custom_embedding_model = os.getenv('EMBEDDING_MODEL')
                    if custom_embedding_model:
                        self.embedding = custom_embedding_model
                        logger.info(f" 使用自定义embedding模型: {self.embedding}")
                    else:
                        # 默认使用 BAAI/bge-large-zh-v1.5
                        self.embedding = "BAAI/bge-large-zh-v1.5"
                        logger.info(f" 使用默认embedding模型: {self.embedding}")

                    # 检查模型是否在token限制配置中
                    if self.embedding not in self.model_token_limits:
                        logger.warning(f" 未知的embedding模型: {self.embedding}，将使用默认token限制8192")
                        self.model_token_limits[self.embedding] = 8192

                    self.client = OpenAI(
                        api_key=siliconflow_key,
                        base_url="https://api.siliconflow.cn/v1",
                        max_retries=0  # 禁用重试，只尝试一次
                    )
                    logger.info(f" SiliconFlow embedding已配置，模型: {self.embedding}, "
                               f"token限制: {self.model_token_limits[self.embedding]}")
                except Exception as e:
                    logger.error(f" SiliconFlow embedding初始化失败: {e}")
                    self.client = "DISABLED"
                    logger.warning(f" SiliconFlow记忆功能已禁用")
            else:
                # 没有SiliconFlow密钥，禁用记忆功能
                self.client = "DISABLED"
                logger.warning(f" 未找到SILICONFLOW_API_KEY，记忆功能已禁用")
                logger.info(f" 系统将继续运行，但不会保存或检索历史记忆")
        elif self.llm_provider == "qianfan":
            # 千帆（文心一言）embedding配置
            # 千帆目前没有独立的embedding API，使用阿里百炼作为降级选项
            dashscope_key = os.getenv('DASHSCOPE_API_KEY')
            if dashscope_key:
                try:
                    # 使用阿里百炼嵌入服务作为千帆的embedding解决方案
                    import dashscope
                    from dashscope import TextEmbedding

                    dashscope.api_key = dashscope_key
                    self.embedding = "text-embedding-v3"
                    self.client = None
                    logger.info(f" 千帆使用阿里百炼嵌入服务")
                except ImportError as e:
                    logger.error(f" DashScope包未安装: {e}")
                    self.client = "DISABLED"
                    logger.warning(f" 千帆记忆功能已禁用")
                except Exception as e:
                    logger.error(f" 千帆嵌入初始化失败: {e}")
                    self.client = "DISABLED"
                    logger.warning(f" 千帆记忆功能已禁用")
            else:
                # 没有DashScope密钥，禁用记忆功能
                self.client = "DISABLED"
                logger.warning(f" 千帆未找到DASHSCOPE_API_KEY，记忆功能已禁用")
                logger.info(f" 系统将继续运行，但不会保存或检索历史记忆")
        elif self.llm_provider == "deepseek":
            # 检查是否强制使用OpenAI嵌入
            force_openai = os.getenv('FORCE_OPENAI_EMBEDDING', 'false').lower() == 'true'

            if not force_openai:
                # 尝试使用阿里百炼嵌入
                dashscope_key = os.getenv('DASHSCOPE_API_KEY')
                if dashscope_key:
                    try:
                        # 测试阿里百炼是否可用
                        import dashscope
                        from dashscope import TextEmbedding

                        dashscope.api_key = dashscope_key
                        # 验证TextEmbedding可用性（不需要实际调用）
                        self.embedding = "text-embedding-v3"
                        self.client = None
                        logger.info(f" DeepSeek使用阿里百炼嵌入服务")
                    except ImportError as e:
                        logger.error(f" DashScope包未安装: {e}")
                        dashscope_key = None  # 强制降级
                    except Exception as e:
                        logger.error(f" 阿里百炼嵌入初始化失败: {e}")
                        dashscope_key = None  # 强制降级
            else:
                dashscope_key = None  # 跳过阿里百炼

            if not dashscope_key or force_openai:
                # 降级到OpenAI嵌入
                self.embedding = "text-embedding-3-small"
                openai_key = os.getenv('OPENAI_API_KEY')
                if openai_key:
                    self.client = OpenAI(
                        api_key=openai_key,
                        base_url=config.get("backend_url", "https://api.openai.com/v1"),
                        max_retries=0  # 禁用重试，只尝试一次
                    )
                    logger.warning(f" DeepSeek回退到OpenAI嵌入服务")
                else:
                    # 最后尝试DeepSeek自己的嵌入
                    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
                    if deepseek_key:
                        try:
                            self.client = OpenAI(
                                api_key=deepseek_key,
                                base_url="https://api.deepseek.com",
                                max_retries=0  # 禁用重试，只尝试一次
                            )
                            logger.info(f" DeepSeek使用自己的嵌入服务")
                        except Exception as e:
                            logger.error(f" DeepSeek嵌入服务不可用: {e}")
                            # 禁用内存功能
                            self.client = "DISABLED"
                            logger.info(f" 内存功能已禁用，系统将继续运行但不保存历史记忆")
                    else:
                        # 禁用内存功能而不是抛出异常
                        self.client = "DISABLED"
                        logger.info(f" 未找到可用的嵌入服务，内存功能已禁用")
        elif self.llm_provider == "google":
            # Google AI使用阿里百炼嵌入（如果可用），否则禁用记忆功能
            dashscope_key = os.getenv('DASHSCOPE_API_KEY')
            openai_key = os.getenv('OPENAI_API_KEY')
            
            if dashscope_key:
                try:
                    # 尝试初始化DashScope
                    import dashscope
                    from dashscope import TextEmbedding

                    self.embedding = "text-embedding-v3"
                    self.client = None
                    dashscope.api_key = dashscope_key
                    
                    # 检查是否有OpenAI密钥作为降级选项
                    if openai_key:
                        logger.info(f" Google AI使用阿里百炼嵌入服务（OpenAI作为降级选项）")
                        self.fallback_available = True
                        self.fallback_client = OpenAI(
                            api_key=openai_key,
                            base_url=config["backend_url"],
                            max_retries=0  # 禁用重试，只尝试一次
                        )
                        self.fallback_embedding = "text-embedding-3-small"
                    else:
                        logger.info(f" Google AI使用阿里百炼嵌入服务（无降级选项）")
                        self.fallback_available = False
                        
                except ImportError as e:
                    logger.error(f" DashScope包未安装: {e}")
                    self.client = "DISABLED"
                    logger.warning(f" Google AI记忆功能已禁用")
                except Exception as e:
                    logger.error(f" DashScope初始化失败: {e}")
                    self.client = "DISABLED"
                    logger.warning(f" Google AI记忆功能已禁用")
            else:
                # 没有DashScope密钥，禁用记忆功能
                self.client = "DISABLED"
                self.fallback_available = False
                logger.warning(f" Google AI未找到DASHSCOPE_API_KEY，记忆功能已禁用")
                logger.info(f" 系统将继续运行，但不会保存或检索历史记忆")
        elif self.llm_provider == "openrouter":
            # OpenRouter支持：优先使用阿里百炼嵌入，否则禁用记忆功能
            dashscope_key = os.getenv('DASHSCOPE_API_KEY')
            if dashscope_key:
                try:
                    # 尝试使用阿里百炼嵌入
                    import dashscope
                    from dashscope import TextEmbedding

                    self.embedding = "text-embedding-v3"
                    self.client = None
                    dashscope.api_key = dashscope_key
                    logger.info(f" OpenRouter使用阿里百炼嵌入服务")
                except ImportError as e:
                    logger.error(f" DashScope包未安装: {e}")
                    self.client = "DISABLED"
                    logger.warning(f" OpenRouter记忆功能已禁用")
                except Exception as e:
                    logger.error(f" DashScope初始化失败: {e}")
                    self.client = "DISABLED"
                    logger.warning(f" OpenRouter记忆功能已禁用")
            else:
                # 没有DashScope密钥，禁用记忆功能
                self.client = "DISABLED"
                logger.warning(f" OpenRouter未找到DASHSCOPE_API_KEY，记忆功能已禁用")
                logger.info(f" 系统将继续运行，但不会保存或检索历史记忆")
        elif config["backend_url"] == "http://localhost:11434/v1":
            self.embedding = "nomic-embed-text"
            self.client = OpenAI(
                base_url=config["backend_url"],
                max_retries=0  # 禁用重试，只尝试一次
            )
        else:
            self.embedding = "text-embedding-3-small"
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                self.client = OpenAI(
                    api_key=openai_key,
                    base_url=config["backend_url"],
                    max_retries=0  # 禁用重试，只尝试一次
                )
            else:
                self.client = "DISABLED"
                logger.warning(f" 未找到OPENAI_API_KEY，记忆功能已禁用")

        # 使用单例ChromaDB管理器
        self.chroma_manager = ChromaDBManager()
        self.situation_collection = self.chroma_manager.get_or_create_collection(
            name=name,
            persistent=persistent
        )

        logger.info(f" [FinancialSituationMemory] 初始化完成: {name} "
                   f"({'持久化' if persistent else '会话级'}记忆)")

    def _get_model_max_chars(self):
        """获取当前模型的最大字符数限制"""
        max_tokens = self.model_token_limits.get(self.embedding, 8192)  # 默认8192 tokens
        max_chars = max_tokens * self.chars_per_token  # 转换为字符数

        # 留10%余量，避免边界情况
        max_chars = int(max_chars * 0.9)

        logger.debug(f" 模型{self.embedding}最大长度: {max_tokens} tokens ≈ {max_chars} 字符")
        return max_chars

    def _smart_text_truncation(self, text, max_length=None):
        """
        智能文本截断，保持语义完整性

        Args:
            text: 输入文本
            max_length: 最大长度（字符数），如果为None则使用模型限制

        Returns:
            (truncated_text, was_truncated)
        """
        if max_length is None:
            max_length = self._get_model_max_chars()

        if len(text) <= max_length:
            return text, False  # 返回原文本和是否截断的标志

        logger.info(f" 文本需要截断：{len(text)} 字符 → {max_length} 字符")

        # 策略1：尝试在句子边界截断
        sentences = text.split('。')
        if len(sentences) > 1:
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence + '。') <= max_length - 50:  # 留50字符余量
                    truncated += sentence + '。'
                else:
                    break
            if len(truncated) > max_length // 2:  # 至少保留一半内容
                logger.info(f" 在句子边界截断，保留{len(truncated)}/{len(text)}字符")
                return truncated, True

        # 策略2：尝试在段落边界截断
        paragraphs = text.split('\n')
        if len(paragraphs) > 1:
            truncated = ""
            for paragraph in paragraphs:
                if len(truncated + paragraph + '\n') <= max_length - 50:
                    truncated += paragraph + '\n'
                else:
                    break
            if len(truncated) > max_length // 2:
                logger.info(f" 在段落边界截断，保留{len(truncated)}/{len(text)}字符")
                return truncated, True

        # 策略3：保留前部分（更重要）
        # 通常分析报告的前面部分包含核心结论
        truncated = text[:max_length - 50] + "\n...[内容已截断]"
        logger.warning(f" 强制截断前{max_length}字符，原长度{len(text)}字符")
        return truncated, True

    def _chunk_and_embed(self, text):
        """
        🆕 将超长文本分块并生成embedding（平均合并策略）

        Args:
            text: 超长文本

        Returns:
            embedding向量（多个chunk的平均向量）
        """
        import numpy as np

        chunk_size = self.max_embedding_length - 100  # 留100字符余量
        overlap = chunk_size // 4  # 25% 重叠以保持上下文连贯性

        # 分块
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # 尝试在句子或段落边界分割
            if end < len(text):
                # 查找最近的句号或换行
                last_period = chunk.rfind('。')
                last_newline = chunk.rfind('\n')
                split_point = max(last_period, last_newline)

                if split_point > chunk_size // 2:  # 至少保留一半内容
                    chunk = chunk[:split_point + 1]
                    end = start + len(chunk)

            chunks.append(chunk)
            start = end - overlap  # 重叠部分

        logger.info(f"📦 文本分块: {len(text)}字符 → {len(chunks)}个块（每块~{chunk_size}字符，重叠{overlap}字符）")

        # 为每个chunk生成embedding
        chunk_embeddings = []
        for i, chunk in enumerate(chunks):
            logger.debug(f"  处理第{i+1}/{len(chunks)}块...")

            # 递归调用get_embedding（但这次chunk不会超过限制）
            # 暂时禁用长度检查以避免无限递归
            original_check = self.enable_embedding_length_check
            self.enable_embedding_length_check = False

            try:
                processed_chunk, _ = self._smart_text_truncation(chunk, self.max_embedding_length)
                embedding = self._generate_embedding_direct(processed_chunk)
                chunk_embeddings.append(embedding)
            finally:
                self.enable_embedding_length_check = original_check

        # 合并所有chunk的embedding（简单平均）
        avg_embedding = np.mean(chunk_embeddings, axis=0)

        logger.info(f"✅ 分块处理完成: {len(chunks)}个块 → 平均embedding（维度{len(avg_embedding)}）")

        # 存储文本处理信息
        self._last_text_info = {
            'original_length': len(text),
            'processed_length': sum(len(c) for c in chunks),
            'was_truncated': False,
            'was_chunked': True,
            'num_chunks': len(chunks),
            'chunk_size': chunk_size,
            'overlap': overlap,
            'provider': self.llm_provider,
            'strategy': 'chunking_with_overlap'
        }

        return avg_embedding.tolist()

    def _generate_embedding_direct(self, text):
        """
        🆕 直接生成embedding（不经过长度检查和缓存）

        内部方法，仅供_chunk_and_embed使用
        """
        try:
            # 根据provider选择实现
            if self.llm_provider == "openai":
                return self.client.embeddings.create(
                    input=text,
                    model="text-embedding-3-large"
                ).data[0].embedding
            elif self.llm_provider == "dashscope":
                # Dashscope embedding实现
                from http import HTTPStatus
                import dashscope

                dashscope.api_key = self.llm_api_key

                resp = dashscope.TextEmbedding.call(
                    model=dashscope.TextEmbedding.Models.text_embedding_v3,
                    input=text
                )

                if resp.status_code == HTTPStatus.OK:
                    return resp.output['embeddings'][0]['embedding']
                else:
                    raise EmbeddingServiceUnavailable(f"Dashscope错误: {resp.message}")
            else:
                raise EmbeddingServiceUnavailable(f"不支持的provider: {self.llm_provider}")

        except Exception as e:
            logger.error(f"生成embedding失败: {e}")
            raise EmbeddingServiceUnavailable(str(e))


    def get_embedding(self, text):
        """Get embedding for a text using the configured provider
        添加缓存机制，避免短时间内重复调用

        Raises:
            MemoryDisabled: 当Memory功能被禁用时
            EmbeddingInvalidInput: 当输入文本无效时
            EmbeddingTextTooLong: 当文本超过长度限制时
            EmbeddingServiceUnavailable: 当embedding服务不可用时
        """
        import hashlib
        import time

        # 检查记忆功能是否被禁用
        if self.client == "DISABLED":
            logger.error("记忆功能已禁用，无法生成embedding")
            raise MemoryDisabled()

        # 验证输入文本
        if not text or not isinstance(text, str):
            reason = "文本为None" if not text else f"文本类型错误: {type(text)}"
            logger.error(f"输入文本无效: {reason}")
            raise EmbeddingInvalidInput(reason)

        text_length = len(text)
        if text_length == 0:
            logger.error("输入文本长度为0")
            raise EmbeddingInvalidInput("文本长度为0")

        # 检查缓存
        cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
        current_time = time.time()

        if cache_key in self._embedding_cache:
            cached_embedding, cached_time = self._embedding_cache[cache_key]
            if current_time - cached_time < self._embedding_cache_ttl:
                logger.debug(f"[Embedding缓存] 使用缓存向量，缓存时间: {int(current_time - cached_time)}秒前")
                return cached_embedding

        logger.debug(f"[Embedding] 生成新向量，文本长度: {text_length}字符")

        # 🆕 检查是否需要分块处理（超过最大长度）
        if self.enable_embedding_length_check and text_length > self.max_embedding_length:
            logger.warning(f"文本过长({text_length:,}字符 > {self.max_embedding_length:,}字符)，启用自动分块处理")
            return self._chunk_and_embed(text)

        #  新增：智能截断文本（根据模型限制）
        processed_text, was_truncated = self._smart_text_truncation(text)

        # 记录文本信息
        if text_length > 1500 or was_truncated:
            logger.info(f" 处理文本: 原始{text_length}字符 → 处理后{len(processed_text)}字符 "
                       f"({'已截断' if was_truncated else '未截断'}), 提供商: {self.llm_provider}")

        # 存储文本处理信息
        self._last_text_info = {
            'original_length': text_length,
            'processed_length': len(processed_text),
            'was_truncated': was_truncated,
            'was_skipped': False,
            'provider': self.llm_provider,
            'embedding_model': self.embedding,
            'strategy': 'smart_truncation' if was_truncated else 'no_truncation'
        }

        if (self.llm_provider == "dashscope" or
            self.llm_provider == "alibaba" or
            self.llm_provider == "qianfan" or
            (self.llm_provider == "google" and self.client is None) or
            (self.llm_provider == "deepseek" and self.client is None) or
            (self.llm_provider == "openrouter" and self.client is None)):
            # 使用阿里百炼的嵌入模型
            try:
                # 导入DashScope模块
                import dashscope
                from dashscope import TextEmbedding

                # 检查DashScope API密钥是否可用
                if not hasattr(dashscope, 'api_key') or not dashscope.api_key:
                    logger.warning(f" DashScope API密钥未设置，记忆功能降级")
                    return [0.0] * 1024  # 返回空向量

                # 尝试调用DashScope API
                response = TextEmbedding.call(
                    model=self.embedding,
                    input=processed_text  # 使用截断后的文本
                )

                # 检查响应状态
                if response.status_code == 200:
                    # 成功获取embedding
                    embedding = response.output['embeddings'][0]['embedding']
                    logger.debug(f" DashScope embedding成功，维度: {len(embedding)}")

                    # 缓存结果
                    self._embedding_cache[cache_key] = (embedding, current_time)
                    logger.debug(f" [Embedding缓存] 缓存向量，TTL: {self._embedding_cache_ttl}秒")

                    return embedding
                else:
                    # API返回错误状态码
                    error_msg = f"{response.code} - {response.message}"
                    
                    # 检查是否为长度限制错误
                    if any(keyword in error_msg.lower() for keyword in ['length', 'token', 'limit', 'exceed']):
                        logger.warning(f" DashScope长度限制: {error_msg}")
                        
                        # 检查是否有降级选项
                        if hasattr(self, 'fallback_available') and self.fallback_available:
                            logger.info(f" 尝试使用OpenAI降级处理长文本")
                            try:
                                response = self.fallback_client.embeddings.create(
                                    model=self.fallback_embedding,
                                    input=processed_text  # 使用截断后的文本
                                )
                                embedding = response.data[0].embedding
                                logger.info(f" OpenAI降级成功，维度: {len(embedding)}")

                                # 缓存结果
                                self._embedding_cache[cache_key] = (embedding, current_time)
                                logger.debug(f" [Embedding缓存] 缓存向量（降级），TTL: {self._embedding_cache_ttl}秒")

                                return embedding
                            except Exception as fallback_error:
                                logger.error(f" OpenAI降级失败: {str(fallback_error)}")
                                logger.info(f" 所有降级选项失败，记忆功能降级")
                                return [0.0] * 1024
                        else:
                            logger.info(f" 无可用降级选项，记忆功能降级")
                            return [0.0] * 1024
                    else:
                        logger.error(f" DashScope API错误: {error_msg}")
                        return [0.0] * 1024  # 返回空向量而不是抛出异常

            except Exception as e:
                error_str = str(e).lower()
                
                # 检查是否为长度限制错误
                if any(keyword in error_str for keyword in ['length', 'token', 'limit', 'exceed', 'too long']):
                    logger.warning(f" DashScope长度限制异常: {str(e)}")
                    
                    # 检查是否有降级选项
                    if hasattr(self, 'fallback_available') and self.fallback_available:
                        logger.info(f" 尝试使用OpenAI降级处理长文本")
                        try:
                            response = self.fallback_client.embeddings.create(
                                model=self.fallback_embedding,
                                input=processed_text  # 使用截断后的文本
                            )
                            embedding = response.data[0].embedding
                            logger.info(f" OpenAI降级成功，维度: {len(embedding)}")

                            # 缓存结果
                            self._embedding_cache[cache_key] = (embedding, current_time)
                            logger.debug(f" [Embedding缓存] 缓存向量（降级），TTL: {self._embedding_cache_ttl}秒")

                            return embedding
                        except Exception as fallback_error:
                            logger.error(f" OpenAI降级失败: {str(fallback_error)}")
                            logger.info(f" 所有降级选项失败，记忆功能降级")
                            return [0.0] * 1024
                    else:
                        logger.info(f" 无可用降级选项，记忆功能降级")
                        return [0.0] * 1024
                elif 'import' in error_str:
                    logger.error(f" DashScope包未安装: {str(e)}")
                elif 'connection' in error_str:
                    logger.error(f" DashScope网络连接错误: {str(e)}")
                elif 'timeout' in error_str:
                    logger.error(f" DashScope请求超时: {str(e)}")
                else:
                    logger.error(f" DashScope embedding异常: {str(e)}")
                
                logger.warning(f" 记忆功能降级，返回空向量")
                return [0.0] * 1024
        else:
            # 使用OpenAI兼容的嵌入模型
            if self.client is None:
                logger.warning(f" 嵌入客户端未初始化，返回空向量")
                return [0.0] * 1024  # 返回空向量
            elif self.client == "DISABLED":
                # 内存功能已禁用，返回空向量
                logger.debug(f" 内存功能已禁用，返回空向量")
                return [0.0] * 1024  # 返回1024维的零向量

            # 尝试调用OpenAI兼容的embedding API
            try:
                response = self.client.embeddings.create(
                    model=self.embedding,
                    input=processed_text  # 使用截断后的文本
                )
                embedding = response.data[0].embedding
                logger.debug(f" {self.llm_provider} embedding成功，维度: {len(embedding)}")

                # 缓存结果
                self._embedding_cache[cache_key] = (embedding, current_time)
                logger.debug(f" [Embedding缓存] 缓存向量，TTL: {self._embedding_cache_ttl}秒")

                return embedding

            except Exception as e:
                error_str = str(e).lower()
                
                # 检查是否为长度限制错误
                length_error_keywords = [
                    'token', 'length', 'too long', 'exceed', 'maximum', 'limit',
                    'context', 'input too large', 'request too large'
                ]
                
                is_length_error = any(keyword in error_str for keyword in length_error_keywords)
                
                if is_length_error:
                    # 长度限制错误：直接降级，不截断重试
                    logger.warning(f" {self.llm_provider}长度限制: {str(e)}")
                    logger.info(f" 为保证分析准确性，不截断文本，记忆功能降级")
                else:
                    # 其他类型的错误
                    if 'attributeerror' in error_str:
                        logger.error(f" {self.llm_provider} API调用错误: {str(e)}")
                    elif 'connectionerror' in error_str or 'connection' in error_str:
                        logger.error(f" {self.llm_provider}网络连接错误: {str(e)}")
                    elif 'timeout' in error_str:
                        logger.error(f" {self.llm_provider}请求超时: {str(e)}")
                    elif 'keyerror' in error_str:
                        logger.error(f" {self.llm_provider}响应格式错误: {str(e)}")
                    else:
                        logger.error(f" {self.llm_provider} embedding异常: {str(e)}")
                
                logger.warning(f" 记忆功能降级，返回空向量")
                return [0.0] * 1024

    def get_embedding_config_status(self):
        """获取向量缓存配置状态"""
        return {
            'enabled': self.enable_embedding_length_check,
            'max_embedding_length': self.max_embedding_length,
            'max_embedding_length_formatted': f"{self.max_embedding_length:,}字符",
            'provider': self.llm_provider,
            'client_status': 'DISABLED' if self.client == "DISABLED" else 'ENABLED'
        }

    def get_last_text_info(self):
        """获取最后处理的文本信息"""
        return getattr(self, '_last_text_info', None)

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice. Parameter is a list of tuples (situation, rec)"""

        situations = []
        advice = []
        ids = []
        embeddings = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        self.situation_collection.add(
            documents=situations,
            metadatas=[{"recommendation": rec} for rec in advice],
            embeddings=embeddings,
            ids=ids,
        )

    def get_memories(self, current_situation, n_matches=1):
        """Find matching recommendations using embeddings with smart truncation handling"""
        
        # 获取当前情况的embedding
        query_embedding = self.get_embedding(current_situation)
        
        # 检查是否为空向量（记忆功能被禁用或出错）
        if all(x == 0.0 for x in query_embedding):
            logger.debug(f" 查询embedding为空向量，返回空结果")
            return []
        
        # 检查是否有足够的数据进行查询
        collection_count = self.situation_collection.count()
        if collection_count == 0:
            logger.debug(f" 记忆库为空，返回空结果")
            return []
        
        # 调整查询数量，不能超过集合中的文档数量
        actual_n_matches = min(n_matches, collection_count)
        
        try:
            # 执行相似度查询
            results = self.situation_collection.query(
                query_embeddings=[query_embedding],
                n_results=actual_n_matches
            )
            
            # 处理查询结果
            memories = []
            if results and 'documents' in results and results['documents']:
                documents = results['documents'][0]
                metadatas = results.get('metadatas', [[]])[0]
                distances = results.get('distances', [[]])[0]
                
                for i, doc in enumerate(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    distance = distances[i] if i < len(distances) else 1.0
                    
                    memory_item = {
                        'situation': doc,
                        'recommendation': metadata.get('recommendation', ''),
                        'similarity': 1.0 - distance,  # 转换为相似度分数
                        'distance': distance
                    }
                    memories.append(memory_item)
                
                # 记录查询信息
                if hasattr(self, '_last_text_info') and self._last_text_info.get('was_truncated'):
                    logger.info(f" 截断文本查询完成，找到{len(memories)}个相关记忆")
                    logger.debug(f" 原文长度: {self._last_text_info['original_length']}, "
                               f"处理后长度: {self._last_text_info['processed_length']}")
                else:
                    logger.debug(f" 记忆查询完成，找到{len(memories)}个相关记忆")
            
            return memories
            
        except Exception as e:
            logger.error(f" 记忆查询失败: {str(e)}")
            return []

    def get_cache_info(self):
        """获取缓存相关信息，用于调试和监控"""
        info = {
            'collection_count': self.situation_collection.count(),
            'client_status': 'enabled' if self.client != "DISABLED" else 'disabled',
            'embedding_model': self.embedding,
            'provider': self.llm_provider
        }
        
        # 添加最后一次文本处理信息
        if hasattr(self, '_last_text_info'):
            info['last_text_processing'] = self._last_text_info
            
        return info


if __name__ == "__main__":
    # Example usage
    matcher = FinancialSituationMemory()

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors 
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            logger.info(f"\nMatch {i}:")
            logger.info(f"Similarity Score: {rec.get('similarity', 0):.2f}")
            logger.info(f"Matched Situation: {rec.get('situation', '')}")
            logger.info(f"Recommendation: {rec.get('recommendation', '')}")

    except Exception as e:
        logger.error(f"Error during recommendation: {str(e)}")
