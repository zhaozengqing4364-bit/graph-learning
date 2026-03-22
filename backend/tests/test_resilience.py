"""Reliability and multi-store consistency regression tests."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _AsyncSessionContext:
    def __init__(self, value: object):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeNeo4jDriver:
    def __init__(self, session_value: object | None = None):
        self._session_value = session_value or object()

    def session(self):
        return _AsyncSessionContext(self._session_value)


class _FakeNeo4jWritableSession:
    async def run(self, *args, **kwargs):
        return None


def _load_check_health_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "check_health.py"
    spec = importlib.util.spec_from_file_location("check_health_test_module", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_init_tables_creates_sync_events_table(db_conn):
    cursor = await db_conn.execute("PRAGMA table_info(sync_events)")
    columns = {row[1] for row in await cursor.fetchall()}

    assert {
        "event_id",
        "topic_id",
        "session_id",
        "node_id",
        "entity_type",
        "entity_id",
        "storage_kind",
        "target_store",
        "operation",
        "status",
        "retryable",
        "payload",
        "error_message",
        "attempt_count",
        "created_at",
        "resolved_at",
        "updated_at",
    }.issubset(columns)


@pytest.mark.asyncio
async def test_create_topic_records_sync_event_when_neo4j_write_fails(db_conn):
    from backend.models.topic import TopicCreate
    from backend.services.topic_service import create_topic

    topic_input = TopicCreate(title="图神经网络")
    ai_result = {
        "entry_node": {
            "name": "消息传递",
            "summary": "图神经网络的核心机制。",
            "importance": 5,
        },
        "nodes": [],
        "edges": [],
    }

    with (
        patch("backend.services.topic_service.explorer_agent.create_topic", new=AsyncMock(return_value=ai_result)),
        patch("backend.services.topic_service.graph.create_topic_node", new=AsyncMock(side_effect=RuntimeError("neo4j offline"))),
    ):
        created = await create_topic(db_conn, _FakeNeo4jDriver(), topic_input, lancedb=None)

    cursor = await db_conn.execute(
        """
        SELECT target_store, operation, status, entity_type, entity_id, error_message, payload
        FROM sync_events
        WHERE topic_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (created["topic_id"],),
    )
    row = await cursor.fetchone()

    assert row is not None
    assert row["target_store"] == "neo4j"
    assert row["operation"] == "create_topic_graph"
    assert row["status"] == "pending"
    assert row["entity_type"] == "topic"
    assert row["entity_id"] == created["topic_id"]
    assert "neo4j offline" in row["error_message"]
    payload = json.loads(row["payload"])
    assert payload["entry_node_name"] == "消息传递"
    assert payload["stage"] == "graph_write"


@pytest.mark.asyncio
async def test_create_topic_records_sync_event_when_lancedb_write_fails(db_conn):
    from backend.models.topic import TopicCreate
    from backend.services.topic_service import create_topic

    topic_input = TopicCreate(title="图表示学习")
    ai_result = {
        "entry_node": {
            "name": "节点表示",
            "summary": "把节点映射到向量空间。",
            "importance": 4,
        },
        "nodes": [],
        "edges": [],
    }

    with (
        patch("backend.services.topic_service.explorer_agent.create_topic", new=AsyncMock(return_value=ai_result)),
        patch("backend.repositories.lancedb_repo.add_concept_embedding", new=AsyncMock(side_effect=RuntimeError("vector write failed"))),
        patch("backend.repositories.lancedb_repo.add_topic_embedding", new=AsyncMock(return_value=None)),
    ):
        created = await create_topic(db_conn, None, topic_input, lancedb=MagicMock(name="lancedb"))

    cursor = await db_conn.execute(
        """
        SELECT target_store, operation, status, error_message, payload
        FROM sync_events
        WHERE topic_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (created["topic_id"],),
    )
    row = await cursor.fetchone()

    assert row is not None
    assert row["target_store"] == "lancedb"
    assert row["operation"] == "create_topic_entry_embedding"
    assert row["status"] == "pending"
    assert "vector write failed" in row["error_message"]
    payload = json.loads(row["payload"])
    assert payload["entry_node_name"] == "节点表示"


@pytest.mark.asyncio
async def test_expand_node_records_sync_event_when_lancedb_write_fails(db_conn):
    from backend.api.nodes import expand_node
    from backend.models.node import ExpandRequest

    topic_id = "tp_expand_sync"
    session_id = "ss_expand_sync"
    node_id = "nd_expand_root"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Expand Sync Topic"),
    )
    await db_conn.execute(
        "INSERT INTO sessions (session_id, topic_id, status, visited_node_ids) VALUES (?, ?, 'active', '[]')",
        (session_id, topic_id),
    )
    await db_conn.commit()

    ai_result = {
        "nodes": [
            {
                "name": "聚合函数",
                "summary": "决定邻居信息怎么合并。",
                "importance": 4,
            },
        ],
        "edges": [],
    }
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                db=db_conn,
                neo4j=_FakeNeo4jDriver(_FakeNeo4jWritableSession()),
                lancedb=MagicMock(name="lancedb"),
            )
        )
    )

    with (
        patch("backend.agents.explorer.expand_node", new=AsyncMock(return_value=ai_result)),
        patch("backend.repositories.neo4j_repo.get_concept_node", new=AsyncMock(return_value={"node_id": node_id, "name": "图卷积", "is_mainline": True})),
        patch("backend.repositories.neo4j_repo.get_topic_graph", new=AsyncMock(return_value={"nodes": [{"node_id": node_id, "name": "图卷积"}], "edges": []})),
        patch("backend.graph.validator.validate_and_filter_nodes", new=AsyncMock(side_effect=lambda _db, nodes, _topic_id: nodes)),
        patch("backend.graph.validator.validate_and_filter_edges", return_value=[]),
        patch("backend.graph.traversal.filter_nodes_for_expand", side_effect=lambda nodes, **_: nodes),
        patch("backend.repositories.neo4j_repo.create_concept_node", new=AsyncMock(return_value=None)),
        patch("backend.repositories.neo4j_repo.update_concept_node", new=AsyncMock(return_value=None)),
        patch("backend.repositories.neo4j_repo.link_concept_to_topic", new=AsyncMock(return_value=None)),
        patch("backend.repositories.neo4j_repo.create_relationship", new=AsyncMock(return_value=None)),
        patch("backend.repositories.neo4j_repo.get_node_neighbors", new=AsyncMock(return_value={"neighbors": []})),
        patch("backend.repositories.lancedb_repo.add_concept_embedding", new=AsyncMock(side_effect=RuntimeError("vector expand failed"))),
    ):
        response = await expand_node(
            request,
            topic_id,
            node_id,
            ExpandRequest(session_id=session_id),
        )

    assert response["success"] is True
    cursor = await db_conn.execute(
        """
        SELECT target_store, operation, status, entity_type, error_message, payload
        FROM sync_events
        WHERE topic_id = ? AND node_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (topic_id, node_id),
    )
    row = await cursor.fetchone()

    assert row is not None
    assert row["target_store"] == "lancedb"
    assert row["operation"] == "expand_node_embeddings"
    assert row["status"] == "pending"
    assert row["entity_type"] == "node_expand"
    assert "vector expand failed" in row["error_message"]
    payload = json.loads(row["payload"])
    assert payload["source_node_id"] == node_id
    assert payload["new_node_names"] == ["聚合函数"]


@pytest.mark.asyncio
async def test_delete_topic_records_sync_event_when_neo4j_delete_fails(db_conn):
    from backend.services.topic_service import delete_topic

    topic_id = "tp_delete_sync"
    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Delete Sync Topic"),
    )
    await db_conn.commit()

    with patch("backend.services.topic_service.graph.delete_topic_node", new=AsyncMock(side_effect=RuntimeError("graph delete failed"))):
        deleted = await delete_topic(db_conn, _FakeNeo4jDriver(), topic_id, lancedb=None)

    assert deleted is True
    cursor = await db_conn.execute(
        """
        SELECT target_store, operation, entity_type, entity_id, error_message
        FROM sync_events
        WHERE topic_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (topic_id,),
    )
    row = await cursor.fetchone()

    assert row is not None
    assert row["target_store"] == "neo4j"
    assert row["operation"] == "delete_topic_graph"
    assert row["entity_type"] == "topic_delete"
    assert row["entity_id"] == topic_id
    assert "graph delete failed" in row["error_message"]


@pytest.mark.asyncio
async def test_confirm_candidate_records_sync_events_when_graph_and_vector_sync_fail(db_conn):
    from backend.models.article import ConceptCandidateConfirm
    from backend.services.article_service import confirm_candidate

    topic_id = "tp_candidate_sync"
    candidate_id = "cd_sync_event"
    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Candidate Sync Topic"),
    )
    await db_conn.execute(
        """
        INSERT INTO concept_candidates (
            candidate_id, topic_id, concept_text, normalized_text, status, confidence, origin
        ) VALUES (?, ?, ?, ?, 'candidate', ?, 'manual')
        """,
        (candidate_id, topic_id, "图注意力", "图注意力", 0.7),
    )
    await db_conn.commit()

    with (
        patch("backend.services.article_service.graph.create_concept_node", new=AsyncMock(side_effect=RuntimeError("candidate graph failed"))),
        patch("backend.repositories.lancedb_repo.add_concept_embedding", new=AsyncMock(side_effect=RuntimeError("candidate vector failed"))),
    ):
        updated = await confirm_candidate(
            db_conn,
            _FakeNeo4jDriver(),
            MagicMock(name="lancedb"),
            topic_id,
            candidate_id,
            ConceptCandidateConfirm(concept_name="图注意力机制"),
        )

    assert updated is not None
    cursor = await db_conn.execute(
        """
        SELECT target_store, operation, entity_type, error_message
        FROM sync_events
        WHERE topic_id = ?
        ORDER BY id
        """,
        (topic_id,),
    )
    rows = await cursor.fetchall()

    assert [row["target_store"] for row in rows] == ["neo4j", "lancedb"]
    assert [row["operation"] for row in rows] == ["confirm_candidate_graph", "confirm_candidate_embedding"]
    assert all(row["entity_type"] == "concept_candidate" for row in rows)
    assert "candidate graph failed" in rows[0]["error_message"]
    assert "candidate vector failed" in rows[1]["error_message"]


def test_lancedb_init_tables_supports_list_tables_api():
    from backend.repositories import lancedb_repo

    class FakeConn:
        def __init__(self):
            self.created: list[str] = []

        def list_tables(self):
            return []

        def create_table(self, name, schema=None):
            self.created.append(name)

    conn = FakeConn()
    lancedb_repo.init_tables(conn)

    assert conn.created == ["concept_embeddings", "topic_embeddings"]


@pytest.mark.asyncio
async def test_system_health_uses_modern_lancedb_api(db_conn):
    from backend.api.system import _do_health_check

    class FakeLanceDb:
        def list_tables(self):
            return []

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                db=db_conn,
                neo4j=None,
                lancedb=FakeLanceDb(),
            )
        )
    )

    with patch("backend.api.settings.get_effective_settings", new=AsyncMock(return_value={"openai_api_key": ""})):
        response = await _do_health_check(request)

    assert response["data"]["status"] == "degraded"
    assert response["data"]["services"]["sqlite"] is True
    assert response["data"]["services"]["lancedb"] is True


@pytest.mark.asyncio
async def test_check_health_returns_zero_when_only_optional_services_are_unavailable(capsys):
    module = _load_check_health_module()

    with (
        patch.object(module, "check_python_version", return_value=(True, "Python 3.12.9")),
        patch.object(module, "check_pip_packages", return_value=(True, "All required packages installed")),
        patch.object(module, "check_sqlite", return_value=(True, "SQLite ready")),
        patch.object(module, "check_neo4j", new=AsyncMock(return_value=(False, "Neo4j unavailable"))),
        patch.object(module, "check_lancedb", return_value=(True, "LanceDB ready")),
        patch.object(module, "check_openai_key", return_value=(False, "OPENAI_API_KEY is not set")),
    ):
        with pytest.raises(SystemExit) as exc_info:
            await module.main()

    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert "degraded" in output.lower()
