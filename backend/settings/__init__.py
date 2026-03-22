"""Settings management module.

Re-exports from config and api for structured module access.
Settings logic is split between:
- backend.core.config: pydantic-settings (env file loading)
- backend.api.settings: REST API routes for get/update settings
"""

from backend.core.config import get_settings, reload_settings
from backend.models.settings import AppSettings
