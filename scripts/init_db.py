#!/usr/bin/env python3
"""Initialize all three databases (SQLite, Neo4j, LanceDB)."""

import sys
import asyncio
from pathlib import Path

# Ensure project root is on sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


async def init_sqlite():
    """Initialize SQLite tables."""
    print("  [SQLite] Initializing tables...")
    import aiosqlite
    from backend.core.config import get_settings
    from backend.repositories.sqlite_repo import init_tables

    settings = get_settings()
    db_path = Path(settings.sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await init_tables(db)
    await db.close()
    print("  [SQLite] Done.")


async def init_neo4j():
    """Initialize Neo4j constraints and indexes."""
    print("  [Neo4j]  Initializing constraints...")
    from backend.core.config import get_settings
    from neo4j import AsyncGraphDatabase
    from backend.repositories.neo4j_repo import init_constraints

    settings = get_settings()
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    await driver.verify_connectivity()
    async with driver.session() as session:
        await init_constraints(session)
    await driver.close()
    print("  [Neo4j]  Done.")


def init_lancedb():
    """Initialize LanceDB tables."""
    print("  [LanceDB] Initializing tables...")
    from backend.core.config import get_settings
    from backend.repositories.lancedb_repo import init_tables

    settings = get_settings()
    db_path = Path(settings.lancedb_path)
    db_path.mkdir(parents=True, exist_ok=True)

    import lancedb
    conn = lancedb.connect(str(db_path))
    init_tables(conn)
    print("  [LanceDB] Done.")


async def main():
    print("=" * 60)
    print("  AxonClone Database Initialization")
    print("=" * 60)

    try:
        await init_sqlite()
    except Exception as e:
        print(f"  [SQLite] FAILED: {e}")

    try:
        await init_neo4j()
    except Exception as e:
        print(f"  [Neo4j]  FAILED: {e}")

    try:
        init_lancedb()
    except Exception as e:
        print(f"  [LanceDB] FAILED: {e}")

    print("=" * 60)
    print("  Database initialization complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
