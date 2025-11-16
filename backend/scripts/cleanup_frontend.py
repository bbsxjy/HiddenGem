#!/usr/bin/env python3
"""
TradingAgents-CN 前端清理脚本

功能：
1. 备份 web/ 和 cli/ 目录
2. 删除 Streamlit 相关文件
3. 清理示例数据
4. 创建 API 目录结构
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import sys

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN} {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}  {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL} {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}  {text}{Colors.ENDC}")

def confirm(question):
    """确认提示"""
    response = input(f"{Colors.WARNING}{question} (y/n): {Colors.ENDC}")
    return response.lower() in ['y', 'yes']

def backup_directory(src_dir, backup_root):
    """备份目录"""
    if not src_dir.exists():
        print_warning(f"{src_dir} 不存在，跳过备份")
        return False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = backup_root / f"{src_dir.name}_{timestamp}"

    try:
        shutil.copytree(src_dir, backup_dir)
        print_success(f"已备份 {src_dir} → {backup_dir}")
        return True
    except Exception as e:
        print_error(f"备份 {src_dir} 失败: {e}")
        return False

def delete_path(path):
    """删除文件或目录"""
    if not path.exists():
        print_warning(f"{path} 不存在，跳过删除")
        return True

    try:
        if path.is_dir():
            shutil.rmtree(path)
            print_success(f"已删除目录: {path}")
        else:
            path.unlink()
            print_success(f"已删除文件: {path}")
        return True
    except Exception as e:
        print_error(f"删除 {path} 失败: {e}")
        return False

def create_directory(path):
    """创建目录"""
    try:
        path.mkdir(parents=True, exist_ok=True)
        print_success(f"已创建目录: {path}")
        return True
    except Exception as e:
        print_error(f"创建目录 {path} 失败: {e}")
        return False

def create_file(path, content=""):
    """创建文件"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print_success(f"已创建文件: {path}")
        return True
    except Exception as e:
        print_error(f"创建文件 {path} 失败: {e}")
        return False

def main():
    """主函数"""
    print_header("TradingAgents-CN 前端清理工具")

    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    print_info(f"项目根目录: {project_root}")

    # 确认操作
    print_warning("\n此操作将删除以下内容：")
    print("  • web/ 目录（Streamlit 应用）")
    print("  • .streamlit/ 目录")
    print("  • start_web.* 启动脚本")
    print("  • cli/ 目录（可选保留）")
    print("  • data/ 目录中的示例数据（可选保留）")

    if not confirm("\n是否继续?"):
        print_info("操作已取消")
        return

    # ===== 阶段1: 备份 =====
    print_header("阶段1: 备份现有文件")

    backup_root = project_root / "backup"
    backup_root.mkdir(exist_ok=True)

    # 备份 web 目录
    web_dir = project_root / "web"
    backup_directory(web_dir, backup_root)

    # 询问是否备份 cli 目录
    cli_dir = project_root / "cli"
    if cli_dir.exists() and confirm("是否备份 cli/ 目录?"):
        backup_directory(cli_dir, backup_root)

    # ===== 阶段2: 删除文件 =====
    print_header("阶段2: 删除前端相关文件")

    # 删除 web 目录
    delete_path(web_dir)

    # 删除 .streamlit 目录
    streamlit_dir = project_root / ".streamlit"
    delete_path(streamlit_dir)

    # 删除启动脚本
    start_scripts = [
        "start_web.py",
        "start_web.bat",
        "start_web.sh",
        "start_web.ps1"
    ]

    for script in start_scripts:
        script_path = project_root / script
        delete_path(script_path)

    # 询问是否删除 cli 目录
    if cli_dir.exists() and confirm("是否删除 cli/ 目录?"):
        delete_path(cli_dir)

    # 询问是否清理 data 目录
    data_dir = project_root / "data" / "analysis_results"
    if data_dir.exists() and confirm("是否清理 data/analysis_results/ 中的示例数据?"):
        delete_path(data_dir)
        # 重新创建空目录
        create_directory(data_dir)

    # ===== 阶段3: 创建 API 目录结构 =====
    print_header("阶段3: 创建 API 目录结构")

    api_root = project_root / "api"

    # 创建目录结构
    directories = [
        api_root,
        api_root / "routers",
        api_root / "models",
        api_root / "services",
        api_root / "websocket",
        api_root / "middleware"
    ]

    for directory in directories:
        create_directory(directory)

    # 创建 __init__.py 文件
    init_files = [
        api_root / "__init__.py",
        api_root / "routers" / "__init__.py",
        api_root / "models" / "__init__.py",
        api_root / "services" / "__init__.py",
        api_root / "websocket" / "__init__.py",
        api_root / "middleware" / "__init__.py"
    ]

    for init_file in init_files:
        create_file(init_file, '"""API 模块"""\n')

    # 创建主应用文件框架
    main_py_content = '''"""
HiddenGem Trading Backend - FastAPI Application

基于 TradingAgents-CN 改造
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# 全局变量
trading_graph: TradingAgentsGraph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global trading_graph

    # 启动时初始化
    logging.info(" 初始化 TradingAgents 系统...")
    trading_graph = TradingAgentsGraph(
        selected_analysts=["market", "social", "news", "fundamentals"],
        config=DEFAULT_CONFIG
    )
    logging.info(" TradingAgents 系统初始化完成")

    yield

    # 关闭时清理
    logging.info(" 关闭 TradingAgents 系统...")

app = FastAPI(
    title="HiddenGem Trading Backend",
    description="基于TradingAgents-CN的智能交易后端",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "HiddenGem Trading Backend",
        "trading_graph_initialized": trading_graph is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

    create_file(api_root / "main.py", main_py_content)

    # ===== 阶段4: 创建测试目录 =====
    print_header("阶段4: 创建测试目录")

    tests_dir = project_root / "tests"
    create_directory(tests_dir)
    create_file(tests_dir / "__init__.py", '"""测试模块"""\n')

    # ===== 完成 =====
    print_header("清理完成！")

    print_info("\n 接下来的步骤：")
    print("  1. 查看 HIDDENGEM_TASKS.md 任务清单")
    print("  2. 阅读 CLAUDE.md 开发指南")
    print("  3. 参考 docs/API.md API 文档")
    print("  4. 开始实施阶段1：FastAPI 接口层搭建")
    print("\n  5. 安装 API 依赖：")
    print("     pip install fastapi uvicorn[standard] websockets")
    print("\n  6. 测试启动：")
    print("     uvicorn api.main:app --reload")
    print("\n  7. 访问 API 文档：")
    print("     http://localhost:8000/docs")

    print_success("\n 项目改造准备就绪！")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
