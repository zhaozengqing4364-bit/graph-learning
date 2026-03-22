"""Settings API routes."""

import json
import logging
import re

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.core.response import success_response, error_response
from backend.models.settings import AppSettings
from backend.repositories import settings_repo

logger = logging.getLogger(__name__)

# ollama_base_url must point to local machine only (SSRF prevention)
_ALLOWED_OLLAMA_PREFIX = re.compile(r"^https?://(localhost|127\.0\.0\.1|::1)(:\d+)?/?$")

router = APIRouter()

# Default settings (overlay config.py env values onto AppSettings defaults)
def _build_defaults() -> dict:
    from backend.core.config import get_settings as get_env_settings
    app = AppSettings()
    env = get_env_settings()
    app.neo4j_uri = env.neo4j_uri
    app.neo4j_user = env.neo4j_user
    app.neo4j_password = env.neo4j_password
    app.lancedb_path = env.lancedb_path
    app.sqlite_path = env.sqlite_path
    app.ollama_base_url = env.ollama_base_url
    app.app_env = env.app_env
    app.log_level = env.log_level
    return app.model_dump()

DEFAULTS = _build_defaults()

# Fields to mask in GET response
SENSITIVE_FIELDS = {"openai_api_key", "neo4j_password"}


def _mask_dict(data: dict) -> dict:
    """Return a copy of data with sensitive fields masked."""
    result = {}
    for key, value in data.items():
        if key in SENSITIVE_FIELDS and isinstance(value, str) and value and not value.startswith("••••"):
            result[key] = mask_value(value)
        else:
            result[key] = value
    return result

# Fields that must NEVER be changed via API (infrastructure paths and credentials)
IMMUTABLE_FIELDS = {"neo4j_uri", "neo4j_user", "neo4j_password", "sqlite_path", "lancedb_path"}


def mask_value(value: str) -> str:
    """Mask sensitive values — only indicate whether set, never reveal actual characters."""
    return "••••" if value else ""


@router.get("/settings")
async def get_settings(request: Request):
    try:
        db = request.app.state.db
        stored = await settings_repo.get_all_settings(db)
        merged = {**DEFAULTS}
        for key, value in stored.items():
            try:
                parsed = json.loads(value)
                merged[key] = parsed
            except (json.JSONDecodeError, TypeError):
                merged[key] = value

        return success_response(data=_mask_dict(merged))
    except Exception as e:
        logger.exception("Failed to get settings")
        return error_response("设置加载失败", error_code="SETTINGS_GET_FAILED")


class UpdateSettingsRequest(BaseModel):
    model_config = {"extra": "allow"}


@router.patch("/settings")
async def update_settings(request: Request, body: UpdateSettingsRequest):
    try:
        db = request.app.state.db
        updates = {}
        applied_updates = {}
        for key, value in body.model_dump(exclude_unset=True).items():
            if key not in DEFAULTS:
                continue
            if key in IMMUTABLE_FIELDS:
                continue
            # SSRF prevention: ollama_base_url must be localhost only
            if key == "ollama_base_url" and isinstance(value, str):
                if not _ALLOWED_OLLAMA_PREFIX.match(value.strip()):
                    logger.warning("Rejected non-local ollama_base_url: %s", value)
                    continue
            # Skip if masked value sent back unchanged
            if key in SENSITIVE_FIELDS and isinstance(value, str) and "••••" in value:
                continue
            # Serialize to string for storage
            if isinstance(value, bool):
                updates[key] = json.dumps(value)
            elif isinstance(value, (int, float)):
                updates[key] = str(value)
            else:
                updates[key] = str(value)
            applied_updates[key] = value

        if updates:
            await settings_repo.update_settings(db, updates)

            # Sync to AI client runtime so changes take effect immediately
            if any(k in updates for k in ("openai_api_key", "openai_base_url", "openai_model_default", "openai_embed_model", "ollama_base_url", "ollama_enabled")):
                from backend.agents.base import set_db_overrides
                effective = await get_effective_settings(request)
                set_db_overrides(effective)

        return success_response(data=_mask_dict(applied_updates))
    except Exception as e:
        logger.exception("Failed to update settings")
        return error_response("设置保存失败，请稍后重试", error_code="SETTINGS_UPDATE_FAILED")


async def get_effective_settings(request: Request) -> dict:
    """Get merged settings from DB (overrides) + env defaults.

    Used by health/capabilities checks and AIClient.
    DB values take precedence over .env values.
    """
    db = request.app.state.db
    stored = await settings_repo.get_all_settings(db)
    merged = {**DEFAULTS}
    for key, value in stored.items():
        try:
            merged[key] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            merged[key] = value
    return merged
