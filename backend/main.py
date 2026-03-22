"""AxonClone Backend - FastAPI Application Entry Point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import get_settings
from backend.core.deps import lifespan
from backend.core.response import error_response
from backend.api import articles, system, topics, nodes, graph, sessions, practice, reviews, abilities, export, stats
from backend.api import settings as settings_api

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    async with lifespan(app):
        yield


def create_app() -> FastAPI:
    settings = get_settings()

    # Disable Swagger docs in non-development environments
    _is_dev = settings.app_env == "development"
    app = FastAPI(
        title="AxonClone API",
        description="AI Learning Operating System",
        version="0.1.0",
        lifespan=lifespan_handler,
        docs_url="/docs" if _is_dev else None,
        redoc_url="/redoc" if _is_dev else None,
    )

    # CORS — restricted to known origins and explicit methods/headers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "tauri://localhost"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Routers
    app.include_router(system.router, prefix="/api/v1", tags=["system"])
    app.include_router(topics.router, prefix="/api/v1", tags=["topics"])
    app.include_router(articles.router, prefix="/api/v1", tags=["articles"])
    app.include_router(nodes.router, prefix="/api/v1", tags=["nodes"])
    app.include_router(graph.router, prefix="/api/v1", tags=["graph"])
    app.include_router(sessions.router, prefix="/api/v1", tags=["sessions"])
    app.include_router(practice.router, prefix="/api/v1", tags=["practice"])
    app.include_router(reviews.router, prefix="/api/v1", tags=["reviews"])
    app.include_router(abilities.router, prefix="/api/v1", tags=["abilities"])
    app.include_router(settings_api.router, prefix="/api/v1", tags=["settings"])
    app.include_router(export.router, prefix="/api/v1", tags=["export"])
    app.include_router(stats.router, prefix="/api/v1", tags=["stats"])

    # Global exception handler — ensures all unhandled errors return the standard envelope
    @app.exception_handler(Exception)
    async def _global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_response("服务器内部错误，请稍后重试", error_code="INTERNAL_ERROR"),
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
