"""Dependency injection for database connections."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)
from neo4j import AsyncGraphDatabase, AsyncDriver
import lancedb

from backend.core.config import get_settings


@asynccontextmanager
async def lifespan(app):
    """Initialize and cleanup database connections."""
    settings = get_settings()

    # SQLite
    db_path = Path(settings.sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db: aiosqlite.Connection = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")

    # Initialize SQLite tables
    from backend.repositories.sqlite_repo import init_tables
    await init_tables(db)

    # Cleanup old resolved/ignored sync events (keep 7 days)
    try:
        from backend.repositories.sqlite_repo import cleanup_old_sync_events
        deleted = await cleanup_old_sync_events(db, max_age_days=7)
        if deleted > 0:
            logger.info("Cleaned up %d old sync events", deleted)
    except Exception as e:
        logger.warning(f"Failed to cleanup old sync events: {e}")

    app.state.db = db

    # Load DB-stored settings into AI client on startup
    try:
        from backend.repositories.sqlite_repo import get_all_settings
        from backend.agents.base import set_db_overrides
        import json
        stored = await get_all_settings(db)
        overrides = {}
        for key, value in stored.items():
            try:
                overrides[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                overrides[key] = value
        set_db_overrides(overrides)
    except Exception as e:
        logger.warning(f"Failed to load DB-stored settings into AI client: {e}")

    # Neo4j
    neo4j_driver: AsyncDriver | None = None
    try:
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            max_connection_pool_size=settings.neo4j_max_connection_pool_size,
            connection_acquisition_timeout=settings.neo4j_connection_acquisition_timeout,
        )
        await neo4j_driver.verify_connectivity()
        from backend.repositories.neo4j_repo import init_constraints
        async with neo4j_driver.session() as session:
            await init_constraints(session)
        app.state.neo4j = neo4j_driver
        logger.info(
            "Neo4j connected: %s (pool_size=%d, acquire_timeout=%.1fs)",
            settings.neo4j_uri,
            settings.neo4j_max_connection_pool_size,
            settings.neo4j_connection_acquisition_timeout,
        )
    except Exception as e:
        logger.warning(f"Neo4j connection failed: {e}")
        app.state.neo4j = None

    # LanceDB
    lancedb_conn = None
    try:
        Path(settings.lancedb_path).mkdir(parents=True, exist_ok=True)
        lancedb_conn = lancedb.connect(settings.lancedb_path)
        from backend.repositories.lancedb_repo import init_tables
        init_tables(lancedb_conn)
        logger.info("LanceDB connected: %s", settings.lancedb_path)
    except Exception as e:
        logger.warning(f"LanceDB connection failed: {e}")
        app.state.lancedb = None

    # Recover pending sync events
    try:
        from backend.services.sync_recovery import recover_pending_sync_events
        result = await recover_pending_sync_events(db, neo4j=neo4j_driver, lancedb=lancedb_conn)
        if result["recovered"] > 0 or result["failed_permanent"] > 0:
            logger.info(
                "Sync event recovery: recovered=%d, failed_permanent=%d, skipped=%d",
                result["recovered"], result["failed_permanent"], result["skipped"],
            )
    except Exception as e:
        logger.warning(f"Sync event recovery failed: {e}")

    # Startup summary
    logger.info(
        "AxonClone startup — SQLite: %s | Neo4j: %s | LanceDB: %s",
        db_path,
        "connected" if neo4j_driver else "unavailable",
        "connected" if lancedb_conn else "unavailable",
    )

    yield

    # Cleanup
    await db.close()
    if neo4j_driver:
        await neo4j_driver.close()


def get_db(request):
    return request.app.state.db


def get_neo4j(request):
    return request.app.state.neo4j


def get_lancedb(request):
    return request.app.state.lancedb
