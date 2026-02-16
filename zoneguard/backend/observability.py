"""Observability middleware utilities for API tracing."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("zoneguard.api")


def configure_logging() -> None:
    """Configure basic structured-style logging once."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class RequestTraceMiddleware(BaseHTTPMiddleware):
    """Attach request ID and latency metadata to API responses and logs."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        response = await call_next(request)

        latency_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{latency_ms:.2f}"

        logger.info(
            "request_id=%s method=%s path=%s status=%s latency_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
        )
        return response
