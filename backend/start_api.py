#!/usr/bin/env python3
"""
TradingAgents-CN API 启动脚本
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn

    # 从环境变量读取配置
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              TradingAgents-CN REST API Server                ║
║                                                              ║
║  API Documentation:  http://{host}:{port}/docs
║  Health Check:       http://{host}:{port}/health
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # 启动服务器
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True,  # 开发模式自动重载
        log_level="info"
    )
