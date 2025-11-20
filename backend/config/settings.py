#!/usr/bin/env python3
"""
集中化配置管理和验证模块
在应用启动时统一验证所有环境变量和API密钥
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class ValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Settings:
    """应用设置"""
    # LLM配置
    llm_provider: str
    deep_think_llm: str
    quick_think_llm: str

    # API密钥
    dashscope_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    siliconflow_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    # 数据源API密钥
    tushare_token: Optional[str] = None
    finnhub_api_key: Optional[str] = None

    # Reddit API (可选)
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: Optional[str] = None

    # 数据库配置
    mongodb_enabled: bool = False
    mongodb_host: str = "localhost"
    mongodb_port: int = 27017
    mongodb_username: str = "admin"
    mongodb_password: str = ""
    mongodb_database: str = "tradingagents"
    mongodb_auth_source: str = "admin"

    redis_enabled: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    # 应用配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # 目录配置
    data_dir: str = "./data"
    cache_dir: str = "./cache"
    results_dir: str = "./results"
    log_level: str = "INFO"

    # 功能开关
    memory_enabled: bool = False
    cost_tracking_enabled: bool = True
    cost_alert_threshold: float = 100.0
    max_usage_records: int = 10000

    # 数据源配置
    default_china_data_source: str = "akshare"
    tushare_enabled: bool = False
    deepseek_enabled: bool = False

    # 其他
    max_workers: Optional[int] = None


class SettingsManager:
    """配置管理器 - 集中加载和验证环境变量"""

    _instance = None
    _settings: Optional[Settings] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置管理器"""
        if self._settings is None:
            self._load_env()

    def _load_env(self):
        """加载环境变量"""
        # 查找 .env 文件
        project_root = Path(__file__).parent.parent
        env_file = project_root / ".env"

        if env_file.exists():
            load_dotenv(env_file, override=True)
        else:
            # 如果没有 .env 文件，发出警告
            import warnings
            warnings.warn(
                f".env file not found at {env_file}. "
                "Using environment variables or defaults.",
                UserWarning
            )

    def load_settings(self) -> Settings:
        """加载配置"""
        if self._settings is not None:
            return self._settings

        self._settings = Settings(
            # LLM配置
            llm_provider=os.getenv("LLM_PROVIDER", "dashscope"),
            deep_think_llm=os.getenv("DEEP_THINK_LLM", "qwen-plus"),
            quick_think_llm=os.getenv("QUICK_THINK_LLM", "qwen-turbo"),

            # API密钥
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            siliconflow_api_key=os.getenv("SILICONFLOW_API_KEY"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),

            # 数据源
            tushare_token=os.getenv("TUSHARE_TOKEN"),
            finnhub_api_key=os.getenv("FINNHUB_API_KEY"),

            # Reddit
            reddit_client_id=os.getenv("REDDIT_CLIENT_ID"),
            reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "TradingAgents-CN/1.0"),

            # 数据库
            mongodb_enabled=self._parse_bool(os.getenv("MONGODB_ENABLED", "false")),
            mongodb_host=os.getenv("MONGODB_HOST", "localhost"),
            mongodb_port=int(os.getenv("MONGODB_PORT", "27017")),
            mongodb_username=os.getenv("MONGODB_USERNAME", "admin"),
            mongodb_password=os.getenv("MONGODB_PASSWORD", ""),
            mongodb_database=os.getenv("MONGODB_DATABASE", "tradingagents"),
            mongodb_auth_source=os.getenv("MONGODB_AUTH_SOURCE", "admin"),

            redis_enabled=self._parse_bool(os.getenv("REDIS_ENABLED", "false")),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_password=os.getenv("REDIS_PASSWORD", ""),
            redis_db=int(os.getenv("REDIS_DB", "0")),

            # API配置
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),

            # 目录配置
            data_dir=os.getenv("TRADINGAGENTS_DATA_DIR", "./data"),
            cache_dir=os.getenv("TRADINGAGENTS_CACHE_DIR", "./cache"),
            results_dir=os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
            log_level=os.getenv("TRADINGAGENTS_LOG_LEVEL", "INFO"),

            # 功能开关
            memory_enabled=self._parse_bool(os.getenv("MEMORY_ENABLED", "false")),
            cost_tracking_enabled=self._parse_bool(os.getenv("ENABLE_COST_TRACKING", "true")),
            cost_alert_threshold=float(os.getenv("COST_ALERT_THRESHOLD", "100.0")),
            max_usage_records=int(os.getenv("MAX_USAGE_RECORDS", "10000")),

            # 数据源配置
            default_china_data_source=os.getenv("DEFAULT_CHINA_DATA_SOURCE", "akshare"),
            tushare_enabled=self._parse_bool(os.getenv("TUSHARE_ENABLED", "false")),
            deepseek_enabled=self._parse_bool(os.getenv("DEEPSEEK_ENABLED", "false")),

            # 其他
            max_workers=int(os.getenv("MAX_WORKERS")) if os.getenv("MAX_WORKERS") else None,
        )

        return self._settings

    @staticmethod
    def _parse_bool(value: str) -> bool:
        """解析布尔值"""
        if isinstance(value, bool):
            return value
        return value.lower() in ("true", "1", "yes", "on")

    def validate(self) -> ValidationResult:
        """验证配置"""
        result = ValidationResult(is_valid=True)
        settings = self.load_settings()

        # 1. 验证必需的LLM Provider配置
        llm_validation = self._validate_llm_provider(settings)
        if not llm_validation[0]:
            result.is_valid = False
            result.errors.extend(llm_validation[1])
        else:
            result.info["llm_provider"] = llm_validation[2]

        # 2. 验证数据源配置
        data_validation = self._validate_data_sources(settings)
        result.warnings.extend(data_validation[0])
        result.info["data_sources"] = data_validation[1]

        # 3. 验证数据库配置
        db_validation = self._validate_databases(settings)
        result.warnings.extend(db_validation[0])
        result.info["databases"] = db_validation[1]

        # 4. 验证目录配置
        dir_validation = self._validate_directories(settings)
        result.warnings.extend(dir_validation[0])
        result.info["directories"] = dir_validation[1]

        # 5. 验证API密钥格式
        key_validation = self._validate_api_keys(settings)
        result.warnings.extend(key_validation[0])
        result.info["api_keys"] = key_validation[1]

        return result

    def _validate_llm_provider(self, settings: Settings) -> Tuple[bool, List[str], Dict[str, Any]]:
        """验证LLM Provider配置"""
        errors = []
        info = {
            "provider": settings.llm_provider,
            "deep_think_model": settings.deep_think_llm,
            "quick_think_model": settings.quick_think_llm,
            "api_key_configured": False
        }

        provider_key_map = {
            "dashscope": settings.dashscope_api_key,
            "openai": settings.openai_api_key,
            "google": settings.google_api_key,
            "anthropic": settings.anthropic_api_key,
            "deepseek": settings.deepseek_api_key,
            "siliconflow": settings.siliconflow_api_key,
            "openrouter": settings.openrouter_api_key,
        }

        # 检查当前provider的API密钥
        api_key = provider_key_map.get(settings.llm_provider.lower())
        if not api_key:
            errors.append(
                f"❌ LLM Provider '{settings.llm_provider}' 未配置API密钥。"
                f"请在 .env 文件中设置相应的API密钥。"
            )
            return False, errors, info

        info["api_key_configured"] = True
        info["api_key_preview"] = f"{api_key[:10]}..." if len(api_key) > 10 else "***"

        return True, [], info

    def _validate_data_sources(self, settings: Settings) -> Tuple[List[str], Dict[str, Any]]:
        """验证数据源配置"""
        warnings = []
        info = {
            "tushare_configured": bool(settings.tushare_token),
            "finnhub_configured": bool(settings.finnhub_api_key),
            "default_china_source": settings.default_china_data_source,
        }

        # A股数据源警告
        if not settings.tushare_token and settings.default_china_data_source == "tushare":
            warnings.append(
                "⚠️  选择了Tushare作为A股数据源，但未配置TUSHARE_TOKEN。"
                "将自动降级到AKShare。"
            )

        # 美股数据源警告
        if not settings.finnhub_api_key:
            warnings.append(
                "⚠️  未配置FINNHUB_API_KEY，美股数据功能可能受限。"
            )

        return warnings, info

    def _validate_databases(self, settings: Settings) -> Tuple[List[str], Dict[str, Any]]:
        """验证数据库配置"""
        warnings = []
        info = {
            "mongodb_enabled": settings.mongodb_enabled,
            "redis_enabled": settings.redis_enabled,
        }

        # MongoDB警告
        if settings.mongodb_enabled:
            if not settings.mongodb_password:
                warnings.append(
                    "⚠️  MongoDB已启用但未设置密码，可能存在安全风险。"
                )
            info["mongodb"] = {
                "host": settings.mongodb_host,
                "port": settings.mongodb_port,
                "database": settings.mongodb_database,
            }

        # Redis警告
        if settings.redis_enabled:
            if not settings.redis_password:
                warnings.append(
                    "⚠️  Redis已启用但未设置密码，可能存在安全风险。"
                )
            info["redis"] = {
                "host": settings.redis_host,
                "port": settings.redis_port,
                "db": settings.redis_db,
            }

        return warnings, info

    def _validate_directories(self, settings: Settings) -> Tuple[List[str], Dict[str, Any]]:
        """验证目录配置"""
        warnings = []
        info = {
            "data_dir": settings.data_dir,
            "cache_dir": settings.cache_dir,
            "results_dir": settings.results_dir,
        }

        # 检查目录是否存在
        for dir_name, dir_path in [
            ("数据目录", settings.data_dir),
            ("缓存目录", settings.cache_dir),
            ("结果目录", settings.results_dir),
        ]:
            if not Path(dir_path).exists():
                warnings.append(
                    f"⚠️  {dir_name} '{dir_path}' 不存在，将在首次使用时自动创建。"
                )

        return warnings, info

    def _validate_api_keys(self, settings: Settings) -> Tuple[List[str], Dict[str, Any]]:
        """验证API密钥格式"""
        warnings = []
        info = {}

        # 验证OpenAI密钥格式
        if settings.openai_api_key:
            if not self._validate_openai_key_format(settings.openai_api_key):
                warnings.append(
                    "⚠️  OPENAI_API_KEY 格式不正确。标准格式：sk-开头，51字符长度。"
                )
                info["openai_key_valid"] = False
            else:
                info["openai_key_valid"] = True

        # 验证DashScope密钥格式
        if settings.dashscope_api_key:
            if not settings.dashscope_api_key.startswith("sk-"):
                warnings.append(
                    "⚠️  DASHSCOPE_API_KEY 格式可能不正确。通常以 sk- 开头。"
                )

        # 验证DeepSeek密钥格式
        if settings.deepseek_api_key:
            if not settings.deepseek_api_key.startswith("sk-"):
                warnings.append(
                    "⚠️  DEEPSEEK_API_KEY 格式可能不正确。通常以 sk- 开头。"
                )

        return warnings, info

    @staticmethod
    def _validate_openai_key_format(api_key: str) -> bool:
        """验证OpenAI API密钥格式"""
        if not api_key or not isinstance(api_key, str):
            return False

        # 检查是否以 'sk-' 开头
        if not api_key.startswith('sk-'):
            return False

        # 检查长度（OpenAI密钥通常为51个字符）
        if len(api_key) != 51:
            return False

        # 检查格式：sk- 后面应该是48个字符的字母数字组合
        pattern = r'^sk-[A-Za-z0-9]{48}$'
        return bool(re.match(pattern, api_key))

    def ensure_directories(self):
        """确保必要的目录存在"""
        settings = self.load_settings()

        directories = [
            settings.data_dir,
            settings.cache_dir,
            settings.results_dir,
            Path(settings.results_dir) / "checkpoints",
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def get_summary(self) -> str:
        """获取配置摘要"""
        settings = self.load_settings()
        validation = self.validate()

        lines = []
        lines.append("=" * 60)
        lines.append("📋 TradingAgents-CN 配置摘要")
        lines.append("=" * 60)

        # 验证状态
        if validation.is_valid:
            lines.append("✅ 配置验证通过")
        else:
            lines.append("❌ 配置验证失败")

        # LLM配置
        lines.append("\n🤖 LLM配置:")
        lines.append(f"  Provider: {settings.llm_provider}")
        lines.append(f"  Deep Think Model: {settings.deep_think_llm}")
        lines.append(f"  Quick Think Model: {settings.quick_think_llm}")

        # 数据源
        lines.append("\n📊 数据源:")
        lines.append(f"  A股数据源: {settings.default_china_data_source}")
        lines.append(f"  Tushare: {'✅' if settings.tushare_token else '❌'}")
        lines.append(f"  Finnhub: {'✅' if settings.finnhub_api_key else '❌'}")

        # 数据库
        lines.append("\n🗄️  数据库:")
        lines.append(f"  MongoDB: {'✅ 已启用' if settings.mongodb_enabled else '❌ 未启用'}")
        lines.append(f"  Redis: {'✅ 已启用' if settings.redis_enabled else '❌ 未启用'}")

        # 功能开关
        lines.append("\n⚙️  功能开关:")
        lines.append(f"  Memory: {'✅ 已启用' if settings.memory_enabled else '❌ 未启用'}")
        lines.append(f"  Cost Tracking: {'✅ 已启用' if settings.cost_tracking_enabled else '❌ 未启用'}")

        # 错误和警告
        if validation.errors:
            lines.append("\n❌ 错误:")
            for error in validation.errors:
                lines.append(f"  {error}")

        if validation.warnings:
            lines.append("\n⚠️  警告:")
            for warning in validation.warnings:
                lines.append(f"  {warning}")

        lines.append("=" * 60)

        return "\n".join(lines)

    def reload(self):
        """重新加载配置"""
        self._settings = None
        self._load_env()
        return self.load_settings()


# 全局单例实例
_settings_manager = SettingsManager()


# 便捷函数
def get_settings() -> Settings:
    """获取配置"""
    return _settings_manager.load_settings()


def validate_settings() -> ValidationResult:
    """验证配置"""
    return _settings_manager.validate()


def print_settings_summary():
    """打印配置摘要"""
    print(_settings_manager.get_summary())


def ensure_directories():
    """确保目录存在"""
    _settings_manager.ensure_directories()


if __name__ == "__main__":
    # 测试配置加载和验证
    import sys

    # 设置Windows控制台UTF-8编码
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("[INFO] 加载配置...")
    settings = get_settings()

    print("\n[INFO] 验证配置...")
    result = validate_settings()

    print("\n" + "=" * 60)
    if result.is_valid:
        print("[OK] 配置验证通过！")
    else:
        print("[ERROR] 配置验证失败！")
        print("\n错误:")
        for error in result.errors:
            print(f"  {error}")

    if result.warnings:
        print("\n警告:")
        for warning in result.warnings:
            print(f"  {warning}")

    print("\n" + _settings_manager.get_summary())
