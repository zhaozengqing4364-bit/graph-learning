"""Common models: ID generator, pagination, and base schemas."""

import secrets


def generate_id(prefix: str) -> str:
    """Generate a unique ID with the given prefix (e.g. 'tp_abc123')."""
    suffix = secrets.token_urlsafe(6)
    return f"{prefix}_{suffix}"


# --- Pagination ---

class PageParams:
    """Query pagination parameters (not a Pydantic model, used as query params)."""

    def __init__(self, limit: int = 20, offset: int = 0):
        self.limit = min(max(limit, 1), 100)
        self.offset = max(offset, 0)
