"""Unified API response format."""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)
T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    meta: dict[str, Any] | None = None
    error: ErrorDetail | None = None


def _build_meta(meta: dict | None = None) -> dict:
    """Auto-inject request_id and timestamp into response meta."""
    base = {
        "request_id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0",
    }
    if meta:
        base.update(meta)
    return base


def success_response(data: Any = None, meta: dict | None = None) -> dict:
    return {"success": True, "data": data, "meta": _build_meta(meta), "error": None}


def _is_production_env() -> bool:
    try:
        from backend.core.config import get_settings
        return get_settings().app_env != "development"
    except Exception:
        return False


# Patterns that indicate internal implementation details in error messages
_INTERNAL_PATTERNS = re.compile(
    r'(?:'
    r'/[\w/.-]+\.py'        # file paths like /path/to/file.py
    r'|Traceback'             # Python traceback
    r'|\\w+\.py'              # Windows paths
    r'|Exception|Error|Fault' # Python exception class names
    r'|neo4j|sqlite|aiosqlite|lancedb'  # DB internals
    r'|neo4j\+|bolt://'       # DB protocol strings
    r'|\.pyc|\.pyo'           # compiled Python files
    r'|ModuleNotFoundError|ImportError|AttributeError'  # import errors
    r')',
    re.IGNORECASE,
)


def _sanitize_error_message(message: str) -> str:
    """Remove internal implementation details from error messages in production."""
    if not message or _is_production_env() is False:
        return message

    if not _INTERNAL_PATTERNS.search(message):
        return message

    # Keep the human-readable prefix (before the first ": " which is usually
    # where str(e) gets appended), but drop the internal detail suffix
    colon_idx = message.find(": ")
    if colon_idx > 0:
        prefix = message[:colon_idx].strip()
        if prefix and not _INTERNAL_PATTERNS.search(prefix):
            return prefix

    # Fallback: return a generic message
    return "操作失败，请稍后重试"


def error_response(
    message: str,
    error_code: str = "INTERNAL_ERROR",
    details: dict | None = None,
    meta: dict | None = None,
) -> dict:
    # In non-development mode, sanitize message to avoid leaking internals
    sanitized = _sanitize_error_message(message)
    if sanitized != message:
        logger.warning("Error message sanitized (original: %s)", message[:200])
    return {
        "success": False,
        "data": None,
        "meta": _build_meta(meta),
        "error": {
            "code": error_code,
            "message": sanitized,
            "details": details or {},
        },
    }
