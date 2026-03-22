"""Unit tests for scripts/check_health.py semantics."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from unittest.mock import AsyncMock


def _load_check_health_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "check_health.py"
    spec = spec_from_file_location("check_health_script", script_path)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_check_lancedb_supports_list_tables_only(monkeypatch):
    module = _load_check_health_module()

    class FakeConn:
        def list_tables(self):
            return ["concept_embeddings"]

    class FakeSettings:
        lancedb_path = "/tmp/lancedb-test"

    monkeypatch.setattr("backend.core.config.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("lancedb.connect", lambda _: FakeConn())

    ok, message = module.check_lancedb()

    assert ok is True
    assert "LanceDB accessible" in message


@pytest.mark.asyncio
async def test_health_script_exits_zero_for_degraded_optional_failures(monkeypatch):
    module = _load_check_health_module()

    monkeypatch.setattr(module, "check_python_version", lambda: (True, "Python 3.12.0"))
    monkeypatch.setattr(module, "check_pip_packages", lambda: (True, "packages ok"))
    monkeypatch.setattr(module, "check_sqlite", lambda: (True, "sqlite ok"))
    monkeypatch.setattr(module, "check_neo4j", AsyncMock(return_value=(False, "neo4j unavailable")))
    monkeypatch.setattr(module, "check_lancedb", lambda: (True, "lancedb ok"))
    monkeypatch.setattr(module, "check_openai_key", lambda: (False, "api key missing"))

    with pytest.raises(SystemExit) as exc_info:
        await module.main()

    assert exc_info.value.code == 0
