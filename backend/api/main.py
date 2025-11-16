"""
FastAPI Main Application

提供REST API + WebSocket接口给HiddenGem前端
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import logging
import json
from datetime import datetime

# 导入路由
from api.routers import agents, market, portfolio, orders, signals, strategies, auto_trading, backtest, rl_training, memorybank_training
from api.routes import memory

# 导入WebSocket管理器
from api.websocket import ConnectionManager

# 导入任务管理器
from api.services.task_manager import task_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# 创建WebSocket连接管理器
ws_manager = ConnectionManager()


# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭时的处理"""
    # 启动
    logger.info("[STARTUP] HiddenGem API starting...")
    logger.info(f"[STARTUP] Environment: {os.getenv('ENVIRONMENT', 'development')}")

    # 注入WebSocket管理器到TaskManager
    task_manager.set_ws_manager(ws_manager)
    logger.info("[STARTUP] Injected WebSocket manager into TaskManager")

    yield

    # 关闭
    logger.info("[SHUTDOWN] HiddenGem API shutting down...")


# 创建FastAPI应用
app = FastAPI(
    title="HiddenGem Trading API",
    description="REST API + WebSocket for HiddenGem Quantitative Trading System",
    version="0.1.0",
    lifespan=lifespan
)

# CORS配置
cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://192.168.31.147:5173,http://192.168.31.147:5188"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"[ERROR] Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
                "details": {}
            },
            "timestamp": datetime.now().isoformat()
        }
    )


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0"
    }


@app.get("/")
async def root():
    """根端点"""
    return {
        "name": "HiddenGem Trading API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


# 注册路由
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["signals"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
app.include_router(auto_trading.router, prefix="/api/v1/auto-trading", tags=["auto-trading"])
app.include_router(backtest.router)  # backtest路由已包含prefix
app.include_router(rl_training.router)  # RL训练路由已包含prefix
app.include_router(memorybank_training.router)  # MemoryBank训练路由已包含prefix
app.include_router(memory.router, prefix="/api/v1")


# WebSocket端点
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket端点

    客户端可以通过此端点：
    1. 订阅股票实时数据
    2. 订阅任务进度更新
    3. 接收Agent分析进度更新
    4. 接收系统通知

    消息格式：
    {
        "type": "subscribe|unsubscribe|subscribe_task|unsubscribe_task|ping",
        "symbol": "600519.SH",  # subscribe/unsubscribe时需要
        "task_id": "uuid",  # subscribe_task/unsubscribe_task时需要
        "data": {}  # 可选
    }
    """
    await ws_manager.connect(websocket)

    try:
        # 发送欢迎消息
        await ws_manager.send_personal_message({
            "type": "welcome",
            "message": "Connected to HiddenGem API",
            "timestamp": datetime.now().isoformat()
        }, websocket)

        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")

            if msg_type == "subscribe":
                # 订阅股票
                symbol = message.get("symbol")
                if symbol:
                    await ws_manager.subscribe(websocket, symbol)

            elif msg_type == "unsubscribe":
                # 取消订阅股票
                symbol = message.get("symbol")
                if symbol:
                    await ws_manager.unsubscribe(websocket, symbol)

            elif msg_type == "subscribe_task":
                # 订阅任务进度
                task_id = message.get("task_id")
                if task_id:
                    await ws_manager.subscribe_task(websocket, task_id)
                else:
                    await ws_manager.send_personal_message({
                        "type": "error",
                        "message": "Missing task_id for subscribe_task",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)

            elif msg_type == "unsubscribe_task":
                # 取消订阅任务
                task_id = message.get("task_id")
                if task_id:
                    await ws_manager.unsubscribe_task(websocket, task_id)

            elif msg_type == "ping":
                # 心跳
                await ws_manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, websocket)

            elif msg_type == "get_stats":
                # 获取统计信息
                stats = ws_manager.get_stats()
                await ws_manager.send_personal_message({
                    "type": "stats",
                    "data": stats
                }, websocket)

            else:
                # 未知消息类型
                await ws_manager.send_personal_message({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                    "timestamp": datetime.now().isoformat()
                }, websocket)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("[WS] Client disconnected")
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
