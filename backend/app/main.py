"""FastAPI application entry point.

Creates the app instance, registers CORS middleware, includes API and
WebSocket routers, and starts the background session cleanup task on boot.

In production (when static/ exists), serves the frontend SPA at / so the app
can be deployed as a single container.

Observability: request ID middleware, optional JSON logs (LOG_JSON=1),
/metrics with uptime and counters. See docs/OBSERVABILITY.md.

Run with: uvicorn app.main:app --port 8000 --reload
"""

import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.rate_limit import limiter
from app.api.routes import router as api_router
from app.api.session import active_session_count, start_cleanup_task
from app.api.ws import router as ws_router

logger = logging.getLogger(__name__)

def _cors_origins_list() -> list[str]:
    origins = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")
    # On Railway, allow the public app URL so the deployed frontend can call the API
    public_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("RAILWAY_STATIC_URL")
    if public_domain:
        base = public_domain if public_domain.startswith("http") else f"https://{public_domain}"
        if base.rstrip("/") not in [o.strip() for o in origins if o]:
            origins.append(base.rstrip("/"))
    return [o.strip() for o in origins if o]


def _configure_logging() -> None:
    """Set log level and optional JSON formatter (LOG_JSON=1)."""
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.getLogger().setLevel(getattr(logging, level, logging.INFO))
    if os.environ.get("LOG_JSON") == "1":
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        root = logging.getLogger()
        root.handlers = [handler]
        root.setLevel(getattr(logging, level, logging.INFO))


class JsonLogFormatter(logging.Formatter):
    """Format log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        obj = {
            "ts": round(record.created, 3),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    app.state.start_time = time.monotonic()
    app.state.total_requests = 0
    start_cleanup_task()
    yield


app = FastAPI(title="Poker Training Engine", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def request_id_and_access_log(request: Request, call_next):
    """Assign X-Request-ID, count requests, log method/path/status/duration."""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    n = getattr(request.app.state, "total_requests", 0) + 1
    setattr(request.app.state, "total_requests", n)
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request %s %s %s %.2fms %s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-Token", "X-Request-ID"],
)

app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0", "active_sessions": active_session_count()}


@app.get("/metrics")
async def metrics():
    """Light metrics: uptime, active sessions, total HTTP requests since boot."""
    start_time = getattr(app.state, "start_time", None)
    uptime_seconds = round(time.monotonic() - start_time, 1) if start_time is not None else 0.0
    return {
        "uptime_seconds": uptime_seconds,
        "active_sessions": active_session_count(),
        "total_requests": getattr(app.state, "total_requests", 0),
    }


# Serve frontend SPA when static build is present (production Docker image).
# STATIC_DIR is set in production Dockerfile; with pip install . the app runs from site-packages.
_static_dir = os.environ.get("STATIC_DIR") or str(Path(__file__).resolve().parent.parent / "static")
if Path(_static_dir).is_dir():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="spa")
