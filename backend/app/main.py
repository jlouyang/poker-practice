"""FastAPI application entry point.

Creates the app instance, registers CORS middleware, includes API and
WebSocket routers, and starts the background session cleanup task on boot.

In production (when static/ exists), serves the frontend SPA at / so the app
can be deployed as a single container.

Run with: uvicorn app.main:app --port 8000 --reload
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.rate_limit import limiter
from app.api.routes import router as api_router
from app.api.session import active_session_count, start_cleanup_task
from app.api.ws import router as ws_router

_cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_cleanup_task()
    yield


app = FastAPI(title="Poker Training Engine", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-Token"],
)

app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0", "active_sessions": active_session_count()}


# Serve frontend SPA when static build is present (production Docker image).
# STATIC_DIR is set in production Dockerfile; with pip install . the app runs from site-packages.
_static_dir = os.environ.get("STATIC_DIR") or str(Path(__file__).resolve().parent.parent / "static")
if Path(_static_dir).is_dir():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="spa")
