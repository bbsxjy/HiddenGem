"""
Logging middleware for request/response logging.
"""

import time
from typing import Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    """

    # Paths to exclude from logging (health checks, status endpoints)
    EXCLUDED_PATHS = {
        "/health",           # Health check endpoint
        "/",                 # Root endpoint
        "/docs",             # API documentation
        "/redoc",            # ReDoc documentation
        "/openapi.json",     # OpenAPI schema
        "/api/v1/agents/status",  # Agent status endpoint
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response
        """
        # Start timer
        start_time = time.time()

        # Get request details
        method = request.method
        url = str(request.url)
        path = request.url.path
        client = request.client.host if request.client else "unknown"

        # Check if path should be excluded from logging
        should_log = path not in self.EXCLUDED_PATHS

        # Log request (only if not excluded)
        if should_log:
            logger.info(f"→ {method} {url} from {client}")

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response (only if not excluded)
            if should_log:
                logger.info(
                    f"← {method} {url} "
                    f"status={response.status_code} "
                    f"duration={duration*1000:.2f}ms"
                )

            # Add custom headers
            response.headers["X-Process-Time"] = str(duration)

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Always log errors, even for excluded paths
            logger.error(
                f"✗ {method} {url} "
                f"error={str(e)} "
                f"duration={duration*1000:.2f}ms"
            )
            raise
