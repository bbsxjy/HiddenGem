import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_dir": os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "data"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings - 从环境变量读取，支持SiliconFlow等自定义提供商
    "llm_provider": os.getenv("LLM_PROVIDER", "openai"),

    # 🆕 三层LLM模型配置
    "small_llm": os.getenv("SMALL_LLM", "gpt-4o-mini"),        # 小模型：简单任务（如格式化）
    "quick_think_llm": os.getenv("QUICK_THINK_LLM", "gpt-4o-mini"),  # 中模型：常规分析
    "deep_think_llm": os.getenv("DEEP_THINK_LLM", "o4-mini"),        # 大模型：复杂推理

    # 🆕 小模型路由开关（默认关闭，保持向后兼容）
    "enable_small_model_routing": os.getenv("ENABLE_SMALL_MODEL_ROUTING", "false").lower() == "true",

    "backend_url": os.getenv("BACKEND_URL", "https://api.openai.com/v1"),
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Tool settings - 从环境变量读取，提供默认值
    "online_tools": os.getenv("ONLINE_TOOLS_ENABLED", "false").lower() == "true",
    "online_news": os.getenv("ONLINE_NEWS_ENABLED", "true").lower() == "true", 
    "realtime_data": os.getenv("REALTIME_DATA_ENABLED", "false").lower() == "true",

    # Note: Database and cache configuration is now managed by .env file and config.database_manager
    # No database/cache settings in default config to avoid configuration conflicts
}
