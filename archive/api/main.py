"""
FastAPI Application Main Entry Point.

Provides REST API for HiddenGem trading system.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from config.settings import settings
from config.database import db_config
from api.routes import strategy, market, portfolio, orders, agents, signals, websocket
from api.middleware.logging import LoggingMiddleware


class HealthCheckFilter(logging.Filter):
    """Filter out health check and status endpoint logs from uvicorn access logger."""

    EXCLUDED_PATHS = {"/health", "/", "/api/v1/agents/status"}

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out requests to excluded paths."""
        message = record.getMessage()

        # Filter out requests to excluded paths
        for path in self.EXCLUDED_PATHS:
            if f'"{path} ' in message or f'"{path}?' in message:
                return False

        return True


# Configure uvicorn access logger filter on module import
# This ensures it works whether started via python or uvicorn command
logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting HiddenGem API Server...")
    logger.info(f"Environment: {'Development' if settings.is_development else 'Production'}")
    logger.info(f"Database: {settings.database_url}")

    # Initialize database connection pool
    # (Already initialized in db_config)

    yield

    # Shutdown
    logger.info("Shutting down HiddenGem API Server...")
    await db_config.close()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="HiddenGem Trading System API",
    description="REST API for A-share quantitative trading system with MCP agents",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Add logging middleware
app.add_middleware(LoggingMiddleware)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred",
            "path": request.url.path
        }
    )


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "HiddenGem Trading API",
        "version": "0.1.0",
        "environment": "development" if settings.is_development else "production"
    }


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.

    Returns:
        API information
    """
    return {
        "name": "HiddenGem Trading System API",
        "version": "0.1.0",
        "description": "A-share quantitative trading with MCP agents",
        "docs": "/docs",
        "health": "/health"
    }


# Include routers
app.include_router(strategy.router, prefix="/api/v1/strategies", tags=["Strategies"])
app.include_router(market.router, prefix="/api/v1/market", tags=["Market Data"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["MCP Agents"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["Trading Signals"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


# Startup message
@app.on_event("startup")
async def startup_message():
    """Log startup message."""
    logger.info("=" * 60)
    logger.info("HiddenGem Trading System API")
    logger.info("=" * 60)
    logger.info(f"API Server running on http://{settings.api_host}:{settings.api_port}")
    logger.info(f"API Documentation: http://{settings.api_host}:{settings.api_port}/docs")
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=settings.api_workers if not settings.api_reload else 1,
        log_level=settings.log_level.lower()
    )
