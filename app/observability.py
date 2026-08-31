import json
import logging
import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, Request


class _JsonFormatter(logging.Formatter):
    """Format service logs as one JSON object per line for easy collection."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_fields = getattr(record, "request_fields", None)
        if request_fields:
            payload.update(request_fields)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Configure a single structured stdout handler for the application."""
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def register_request_logging(app: FastAPI) -> None:
    """Log request outcome and latency without logging bodies or credentials."""
    logger = logging.getLogger("sharp_operations.request")

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed",
                extra={
                    "request_fields": {
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    }
                },
            )
            raise
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            extra={
                "request_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            },
        )
        return response
