"""Regression tests for development startup scripts."""

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEV_SCRIPT = PROJECT_ROOT / "scripts" / "dev.sh"


def test_dev_script_runs_backend_via_project_environment():
    """Backend startup must use the project environment, not global uvicorn."""
    content = DEV_SCRIPT.read_text(encoding="utf-8")

    assert re.search(
        r'^uv run --directory "\$ROOT_DIR" uvicorn backend\.main:app\b',
        content,
        re.MULTILINE,
    )
