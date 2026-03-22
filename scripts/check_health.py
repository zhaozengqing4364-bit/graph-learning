#!/usr/bin/env python3
"""Check all service dependencies and report status."""

import sys
from pathlib import Path

# Ensure project root is on sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def check_python_version() -> tuple[bool, str]:
    required = (3, 12)
    current = sys.version_info[:2]
    if current >= required:
        return True, f"Python {sys.version.split()[0]}"
    return False, f"Python {sys.version.split()[0]} (need >=3.12)"


def check_pip_packages() -> tuple[bool, str]:
    required = ["fastapi", "aiosqlite", "neo4j", "lancedb", "pydantic", "pydantic_settings"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if not missing:
        return True, "All required packages installed"
    return False, f"Missing packages: {', '.join(missing)}"


def check_sqlite() -> tuple[bool, str]:
    try:
        from backend.core.config import get_settings
        settings = get_settings()
        db_path = Path(settings.sqlite_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Use synchronous sqlite3 for a quick check
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute("SELECT 1")
        conn.close()
        return True, f"SQLite accessible at {settings.sqlite_path}"
    except Exception as e:
        return False, f"SQLite check failed: {e}"


async def check_neo4j() -> tuple[bool, str]:
    try:
        from backend.core.config import get_settings
        settings = get_settings()
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        await driver.verify_connectivity()
        await driver.close()
        return True, f"Neo4j connected at {settings.neo4j_uri}"
    except Exception as e:
        return False, f"Neo4j check failed: {e}"


def check_lancedb() -> tuple[bool, str]:
    try:
        from backend.core.config import get_settings
        settings = get_settings()
        import lancedb
        db_path = Path(settings.lancedb_path)
        db_path.mkdir(parents=True, exist_ok=True)
        conn = lancedb.connect(str(db_path))
        if hasattr(conn, "list_tables"):
            conn.list_tables()
        else:
            conn.table_names()
        return True, f"LanceDB accessible at {settings.lancedb_path}"
    except Exception as e:
        return False, f"LanceDB check failed: {e}"


def check_openai_key() -> tuple[bool, str]:
    try:
        from backend.core.config import get_settings
        settings = get_settings()
        if settings.openai_api_key:
            return True, "OPENAI_API_KEY is set"
        return False, "OPENAI_API_KEY is not set"
    except Exception as e:
        return False, f"Settings check failed: {e}"


def summarize_checks(checks: list[tuple[str, tuple[bool, str]]]) -> tuple[str, int]:
    critical_names = {"Python Version", "Pip Packages", "SQLite"}
    critical_ok = all(ok for name, (ok, _) in checks if name in critical_names)
    all_ok = all(ok for _, (ok, _) in checks)

    if all_ok:
        return "ok", 0
    if critical_ok:
        return "degraded", 0
    return "error", 1


async def main():
    checks = [
        ("Python Version", check_python_version()),
        ("Pip Packages", check_pip_packages()),
        ("SQLite", check_sqlite()),
        ("Neo4j", await check_neo4j()),
        ("LanceDB", check_lancedb()),
        ("OPENAI_API_KEY", check_openai_key()),
    ]

    print("=" * 60)
    print("  AxonClone Service Health Check")
    print("=" * 60)

    for name, (ok, msg) in checks:
        status = "OK" if ok else "FAIL"
        symbol = "+" if ok else "-"
        print(f"  [{symbol}] {name:20s}  {status:4s}  {msg}")

    print("=" * 60)
    overall_status, exit_code = summarize_checks(checks)
    if overall_status == "ok":
        print("  Overall status: ok. All checks passed.")
    elif overall_status == "degraded":
        print("  Overall status: degraded. Optional services are unavailable, but the core stack is healthy.")
    else:
        print("  Overall status: error. Core services failed.")
    sys.exit(exit_code)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
