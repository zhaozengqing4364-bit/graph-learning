"""System health check and capabilities."""

import logging

from fastapi import APIRouter, Request

from backend.core.config import get_settings
from backend.core.response import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter()


def _touch_lancedb_tables(conn) -> None:
    """Support both legacy and newer LanceDB connection APIs."""
    if hasattr(conn, "list_tables"):
        conn.list_tables()
        return
    conn.table_names()


@router.get("/health")
async def health_check_root(request: Request):
    """Root-level health check for Tauri sidecar management."""
    return await _do_health_check(request)


@router.get("/system/health")
async def health_check(request: Request):
    """Check all service statuses with 6 service checks."""
    return await _do_health_check(request)


async def _do_health_check(request: Request):
    services = {
        "api": True,
        "sqlite": False,
        "neo4j": False,
        "lancedb": False,
        "model_provider": False,
        "ollama": False,
    }

    # SQLite
    try:
        db = request.app.state.db
        await db.execute("SELECT 1")
        services["sqlite"] = True
    except Exception as e:
        logger.warning(f"SQLite health check failed: {e}")

    # Neo4j
    try:
        driver = request.app.state.neo4j
        if driver:
            await driver.verify_connectivity()
            services["neo4j"] = True
    except Exception as e:
        logger.warning(f"Neo4j health check failed: {e}")

    # LanceDB
    try:
        conn = request.app.state.lancedb
        if conn:
            _touch_lancedb_tables(conn)
            services["lancedb"] = True
    except Exception as e:
        logger.warning(f"LanceDB health check failed: {e}")

    # Model provider (check if openai_api_key is set)
    try:
        from backend.api.settings import get_effective_settings
        effective = await get_effective_settings(request)
        if effective.get("openai_api_key"):
            services["model_provider"] = True
    except Exception as e:
        logger.warning(f"Model provider check failed: {e}")
        settings = get_settings()
        if settings.openai_api_key:
            services["model_provider"] = True

    # Ollama
    try:
        settings = get_settings()
        if settings.ollama_enabled:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                services["ollama"] = resp.status_code == 200
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        services["ollama"] = False

    # Determine overall status
    critical = ["api", "sqlite"]
    all_critical_ok = all(services[k] for k in critical)
    all_ok = all(services.values())

    if all_critical_ok and not all_ok:
        status = "degraded"
    elif all_ok:
        status = "ok"
    else:
        status = "error"

    return success_response(data={"status": status, "services": services})


@router.get("/system/capabilities")
async def get_capabilities(request: Request):
    """Return which services and capabilities are available."""
    from backend.api.settings import get_effective_settings
    effective = await get_effective_settings(request)

    has_api_key = bool(effective.get("openai_api_key"))
    has_ollama = effective.get("ollama_enabled", False)

    capabilities = {
        "ai_provider": "openai" if has_api_key else ("ollama" if has_ollama else None),
        "ai_model": effective.get("openai_model_default", get_settings().openai_model_default),
        "embed_model": effective.get("openai_embed_model", get_settings().openai_embed_model),
        "ollama_enabled": has_ollama,
        "ollama_base_url": get_settings().ollama_base_url,
        "supports_multimodal": False,
        "supports_local_fallback": has_ollama,
        "supports_export": True,
        "supports_review": True,
        "supports_expression_assets": True,
    }

    return success_response(data=capabilities)
