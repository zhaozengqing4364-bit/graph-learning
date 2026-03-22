"""Session management module.

Re-exports from session_service for structured module access.
Session logic is implemented in backend.services.session_service.
"""

from backend.services.session_service import (
    start_session,
    get_session,
    record_visit,
    complete_session,
)
