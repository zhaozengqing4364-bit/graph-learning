"""Shared test fixtures for backend API tests."""

import sys
import os
from pathlib import Path

import pytest
import pytest_asyncio
from unittest.mock import patch
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Override env vars for testing (no real DB connections)
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "test")
os.environ.setdefault("SQLITE_PATH", "/tmp/axon_clone_test.db")
os.environ.setdefault("LANCEDB_PATH", "/tmp/axon_clone_lancedb_test")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def db_conn():
    """Create a fresh in-memory SQLite connection for testing."""
    import aiosqlite

    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")

    from backend.repositories.sqlite_repo import init_tables
    await init_tables(db)

    yield db
    await db.close()


@pytest_asyncio.fixture
async def app_client(db_conn):
    """Create a test FastAPI client with mocked database.

    Uses starlette.test.TestClient which properly runs the lifespan.
    """
    from starlette.testclient import TestClient
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from backend.api import articles, system, topics, nodes, graph, sessions, practice, reviews, abilities, export, stats
    from backend.api import settings as settings_api

    test_db = db_conn

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        app.state.db = test_db
        app.state.neo4j = None
        app.state.lancedb = None
        yield

    app = FastAPI(
        title="AxonClone Test API",
        lifespan=test_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "tauri://localhost"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
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

    # TestClient runs lifespan automatically and provides synchronous interface
    # Wrap in async-friendly manner using httpx AsyncClient with manually managed lifespan
    from httpx import AsyncClient, ASGITransport

    # Manually enter lifespan, then create httpx client
    lifespan_manager = test_lifespan(app)
    await lifespan_manager.__aenter__()

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        await lifespan_manager.__aexit__(None, None, None)
