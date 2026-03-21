"""Request logging middleware with request-id propagation."""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("access")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        response: Response | None = None
        start = time.perf_counter()

        try:
            response = await call_next(request)
            return response
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("unhandled_exception", exc_info=exc)
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            status_code = response.status_code if response is not None else 500
            logger.info("request", status=status_code, duration_ms=duration_ms)
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            structlog.contextvars.clear_contextvars()
