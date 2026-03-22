"""API endpoint tests - Layer 2 tests per QA doc.

Tests all ~30 endpoints using httpx AsyncClient with in-memory SQLite.
Neo4j and LanceDB are None (graceful degradation mode).
"""

import json

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch


# ==================== System ====================

@pytest.mark.asyncio
async def test_health_check(app_client):
    r = await app_client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_health_check_returns_degraded_when_only_optional_services_are_missing(app_client):
    r = await app_client.get("/api/v1/system/health")
    assert r.status_code == 200
    data = r.json()

    assert data["success"] is True
    assert data["data"]["status"] == "degraded"
    assert data["data"]["services"]["api"] is True
    assert data["data"]["services"]["sqlite"] is True


@pytest.mark.asyncio
async def test_health_check_accepts_lancedb_list_tables_only(app_client):
    class FakeLanceDb:
        def list_tables(self):
            return ["concept_embeddings"]

    app_client._transport.app.state.lancedb = FakeLanceDb()

    r = await app_client.get("/api/v1/system/health")
    assert r.status_code == 200
    data = r.json()

    assert data["success"] is True
    assert data["data"]["services"]["lancedb"] is True


@pytest.mark.asyncio
async def test_capabilities(app_client):
    r = await app_client.get("/api/v1/system/capabilities")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


# ==================== Settings ====================

@pytest.mark.asyncio
async def test_get_settings(app_client):
    r = await app_client.get("/api/v1/settings")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "data" in data
    # Password should be masked
    assert "••••" in str(data["data"].get("neo4j_password", ""))


@pytest.mark.asyncio
async def test_update_settings(app_client):
    r = await app_client.patch("/api/v1/settings", json={"app_env": "testing"})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_settings_returns_error_envelope_when_repo_read_fails(app_client):
    with patch("backend.api.settings.settings_repo.get_all_settings", new=AsyncMock(side_effect=RuntimeError("db offline"))):
        r = await app_client.get("/api/v1/settings")

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SETTINGS_GET_FAILED"


@pytest.mark.asyncio
async def test_update_settings_only_echoes_applied_mutable_fields(app_client):
    r = await app_client.patch(
        "/api/v1/settings",
        json={
            "app_env": "testing",
            "sqlite_path": "/tmp/should-not-apply.db",
            "unexpected_field": "ignored",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"] == {"app_env": "testing"}

    follow_up = await app_client.get("/api/v1/settings")
    follow_up_data = follow_up.json()["data"]
    assert follow_up_data["app_env"] == "testing"
    assert follow_up_data["sqlite_path"] != "/tmp/should-not-apply.db"


# ==================== Topics ====================

@pytest.mark.asyncio
async def test_create_topic(app_client):
    body = {
        "title": "测试主题",
        "source_type": "concept",
        "source_content": "测试内容，关于机器学习的基本概念",
        "learning_intent": "build_system",
        "mode": "full_system",
    }
    r = await app_client.post("/api/v1/topics", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["title"] == "测试主题"
    assert data["data"]["topic_id"].startswith("tp_")


@pytest.mark.asyncio
async def test_list_topics(app_client):
    r = await app_client.get("/api/v1/topics")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    # list_topics returns data as array, total in meta
    assert isinstance(data["data"], list)
    assert "total" in data["meta"]


@pytest.mark.asyncio
async def test_list_topics_with_due_review_count(app_client, db_conn):
    """list_topics should include due_review_count and deferred_count."""
    topic_id = "tp_reviewtest"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Review Test"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO review_items (review_id, topic_id, node_id, status, priority) VALUES (?, ?, ?, 'pending', 0.5)",
        ("rv_1", topic_id, "nd_1"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO deferred_nodes (topic_id, node_id) VALUES (?, ?)",
        (topic_id, "nd_2"),
    )
    await db_conn.commit()

    r = await app_client.get("/api/v1/topics")
    data = r.json()
    items = data["data"]
    test_topic = next((t for t in items if t["topic_id"] == topic_id), None)
    if test_topic:
        assert "due_review_count" in test_topic
        assert "deferred_count" in test_topic
        assert test_topic["due_review_count"] >= 1
        assert test_topic["deferred_count"] >= 1


@pytest.mark.asyncio
async def test_get_topic_detail(app_client, db_conn):
    topic_id = "tp_detailtest"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Detail Test"),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["topic_id"] == topic_id
    assert "due_review_count" in data["data"]


@pytest.mark.asyncio
async def test_update_topic(app_client, db_conn):
    topic_id = "tp_updatetest"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Update Test"),
    )
    await db_conn.commit()

    r = await app_client.patch(f"/api/v1/topics/{topic_id}", json={"title": "Updated Title"})
    assert r.status_code == 200
    data = r.json()
    assert data["data"]["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_archive_topic(app_client, db_conn):
    topic_id = "tp_archivetest"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Archive Test"),
    )
    await db_conn.commit()

    r = await app_client.post(f"/api/v1/topics/{topic_id}/archive")
    assert r.status_code == 200
    data = r.json()
    assert data["data"]["status"] == "archived"


@pytest.mark.asyncio
async def test_delete_topic(app_client, db_conn):
    topic_id = "tp_deletetest"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Delete Test"),
    )
    await db_conn.commit()

    r = await app_client.delete(f"/api/v1/topics/{topic_id}")
    assert r.status_code == 200


# ==================== Sessions ====================

@pytest.mark.asyncio
async def test_create_session(app_client, db_conn):
    topic_id = "tp_sess_test"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Session Test"),
    )
    await db_conn.commit()

    r = await app_client.post(f"/api/v1/topics/{topic_id}/sessions", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["session_id"].startswith("ss_")


@pytest.mark.asyncio
async def test_get_session(app_client, db_conn):
    topic_id = "tp_sess2"
    session_id = "ss_gettest"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Session Get"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO sessions (session_id, topic_id, status) VALUES (?, ?, 'active')",
        (session_id, topic_id),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}/sessions/{session_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["data"]["session_id"] == session_id


@pytest.mark.asyncio
async def test_record_visit_rejects_completed_session(app_client, db_conn):
    topic_id = "tp_sess_completed"
    session_id = "ss_completed_visit"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status, current_node_id) VALUES (?, ?, 'active', ?)",
        (topic_id, "Completed Session", "nd_old"),
    )
    await db_conn.execute(
        """
        INSERT OR IGNORE INTO sessions (
            session_id,
            topic_id,
            status,
            visited_node_ids,
            started_at,
            completed_at,
            updated_at
        ) VALUES (?, ?, 'completed', ?, datetime('now'), datetime('now'), datetime('now'))
        """,
        (session_id, topic_id, '["nd_old"]'),
    )
    await db_conn.commit()

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/sessions/{session_id}/visit",
        json={"node_id": "nd_new", "action_type": "open_node"},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SESSION_NOT_ACTIVE"

    session_cursor = await db_conn.execute(
        "SELECT visited_node_ids FROM sessions WHERE session_id = ?",
        (session_id,),
    )
    session_row = await session_cursor.fetchone()
    assert session_row is not None
    assert session_row[0] == '["nd_old"]'

    topic_cursor = await db_conn.execute(
        "SELECT current_node_id FROM topics WHERE topic_id = ?",
        (topic_id,),
    )
    topic_row = await topic_cursor.fetchone()
    assert topic_row is not None
    assert topic_row[0] == "nd_old"


@pytest.mark.asyncio
async def test_complete_session_returns_persisted_synthesis_when_already_completed(app_client, db_conn):
    topic_id = "tp_sess_done"
    session_id = "ss_done"
    synthesis_json = json.dumps({
        "mainline_summary": "persisted summary",
        "key_takeaways": [],
        "next_recommendations": [],
        "review_items_created": 0,
        "new_assets_count": 0,
        "covered_scope": "",
        "skippable_nodes": [],
        "review_candidates": [],
    }, ensure_ascii=False)
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Done Session"),
    )
    await db_conn.execute(
        """
        INSERT OR IGNORE INTO sessions (
            session_id,
            topic_id,
            status,
            summary,
            synthesis_json,
            started_at,
            completed_at,
            updated_at
        ) VALUES (?, ?, 'completed', ?, ?, datetime('now'), datetime('now'), datetime('now'))
        """,
        (session_id, topic_id, "persisted summary", synthesis_json),
    )
    await db_conn.commit()

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/sessions/{session_id}/complete",
        json={"generate_summary": True, "generate_review_items": True},
    )

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["status"] == "completed"
    assert data["data"]["synthesis"]["mainline_summary"] == "persisted summary"


# ==================== Nodes ====================

@pytest.mark.asyncio
async def test_get_node_detail_fallback(app_client, db_conn):
    """Node detail should return fallback data when Neo4j is unavailable."""
    topic_id = "tp_node_fb"
    node_id = "nd_fb_test"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status, entry_node_id) VALUES (?, ?, 'active', ?)",
        (topic_id, "Node Fallback", node_id),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}/nodes/{node_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["node"]["node_id"] == node_id
    assert data["data"]["prerequisites"] == []
    assert data["data"]["concept_refs"] == []


@pytest.mark.asyncio
async def test_defer_node(app_client, db_conn):
    topic_id = "tp_defer"
    node_id = "nd_defer_test"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Defer Test"),
    )
    await db_conn.commit()

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/defer",
        json={"reason": "太复杂，稍后再学"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_update_node_status(app_client, db_conn):
    topic_id = "tp_status"
    node_id = "nd_status_test"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Status Test"),
    )
    await db_conn.commit()

    r = await app_client.patch(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/status",
        json={"status": "mastered"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_generate_article_force_refresh(app_client, monkeypatch):
    topic_id = "tp_generate_force"
    node_id = "nd_generate_force"
    saved_updates = {}

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def run(self, *args, **kwargs):
            raise RuntimeError("graph write boom")

        async def run(self, *args, **kwargs):
            raise RuntimeError("graph write boom")

    class FakeDriver:
        def session(self):
            return FakeSession()

    async def fake_get_concept_node(session, lookup_node_id):
        assert lookup_node_id == node_id
        return {
            "node_id": node_id,
            "name": "消息传递",
            "summary": "旧版摘要",
            "examples": [],
            "misconceptions": [],
            "applications": [],
            "article_body": "旧文章内容",
        }

    async def fake_get_node_neighbors(session, lookup_node_id, radius=1):
        assert lookup_node_id == node_id
        return {"neighbors": [{"name": "图的表示"}]}

    async def fake_update_concept_node(session, lookup_node_id, updates):
        saved_updates["node_id"] = lookup_node_id
        saved_updates["updates"] = updates

    async def fake_generate_article_for_node(**kwargs):
        return {
            "article_body": "新文章内容，提到 [[图的表示]]。",
            "concept_refs": ["图的表示"],
        }

    app_client._transport.app.state.neo4j = FakeDriver()

    from backend.repositories import neo4j_repo as graph
    from backend.agents import article_generator

    monkeypatch.setattr(graph, "get_concept_node", fake_get_concept_node)
    monkeypatch.setattr(graph, "get_node_neighbors", fake_get_node_neighbors)
    monkeypatch.setattr(graph, "update_concept_node", fake_update_concept_node)
    monkeypatch.setattr(article_generator, "generate_article_for_node", fake_generate_article_for_node)

    cached_response = await app_client.post(f"/api/v1/topics/{topic_id}/nodes/{node_id}/generate-article")
    assert cached_response.status_code == 200
    cached_data = cached_response.json()
    assert cached_data["meta"]["cached"] is True
    assert cached_data["data"]["article_body"] == "旧文章内容"

    refreshed_response = await app_client.post(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/generate-article",
        params={"force": "true"},
    )
    assert refreshed_response.status_code == 200
    refreshed_data = refreshed_response.json()
    assert refreshed_data["meta"]["cached"] is False
    assert refreshed_data["data"]["article_body"] == "新文章内容，提到 [[图的表示]]。"
    assert saved_updates == {
        "node_id": node_id,
        "updates": {"article_body": "新文章内容，提到 [[图的表示]]。"},
    }


@pytest.mark.asyncio
async def test_expand_node_records_sync_event_when_graph_write_fails(app_client, db_conn, monkeypatch):
    topic_id = "tp_expand_sync"
    node_id = "nd_current"
    session_id = "ss_expand_sync"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status, learning_intent) VALUES (?, ?, 'active', ?)",
        (topic_id, "Expand Sync Topic", "build_system"),
    )
    await db_conn.execute(
        "INSERT INTO sessions (session_id, topic_id, status, visited_node_ids) VALUES (?, ?, 'active', ?)",
        (session_id, topic_id, "[]"),
    )
    await db_conn.commit()

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeDriver:
        def session(self):
            return FakeSession()

    async def fake_get_concept_node(session, lookup_node_id):
        return {
            "node_id": lookup_node_id,
            "name": "当前节点",
            "summary": "当前节点摘要",
            "is_mainline": True,
        }

    async def fake_get_topic_graph(session, lookup_topic_id):
        return {
            "nodes": [{"node_id": node_id, "name": "当前节点"}],
            "edges": [],
        }

    async def fake_get_node_neighbors(session, lookup_node_id, radius=1):
        return {"neighbors": []}

    app_client._transport.app.state.neo4j = FakeDriver()

    from backend.agents import explorer as explorer_agent
    from backend.graph import traversal, validator
    from backend.repositories import neo4j_repo as graph
    from backend.repositories import sqlite_repo

    monkeypatch.setattr(explorer_agent, "expand_node", AsyncMock(return_value={
        "nodes": [{"name": "邻接节点", "summary": "新扩展节点", "importance": 3}],
        "edges": [{"source": "当前节点", "target": "邻接节点", "relation_type": "PREREQUISITE"}],
    }))
    monkeypatch.setattr(validator, "validate_and_filter_nodes", AsyncMock(return_value=[
        {"name": "邻接节点", "summary": "新扩展节点", "importance": 3},
    ]))
    monkeypatch.setattr(validator, "validate_and_filter_edges", lambda edges, _: edges)
    monkeypatch.setattr(traversal, "filter_nodes_for_expand", lambda nodes, **_: nodes)
    monkeypatch.setattr(graph, "get_concept_node", fake_get_concept_node)
    monkeypatch.setattr(graph, "get_topic_graph", fake_get_topic_graph)
    monkeypatch.setattr(graph, "get_node_neighbors", fake_get_node_neighbors)
    monkeypatch.setattr(graph, "create_concept_node", AsyncMock(side_effect=RuntimeError("graph write boom")))
    monkeypatch.setattr(sqlite_repo, "record_sync_event", AsyncMock(), raising=False)

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/expand",
        json={"depth_limit": 2, "strategy": "balanced", "session_id": session_id},
    )
    assert r.status_code == 200

    sqlite_repo.record_sync_event.assert_awaited()
    payload = sqlite_repo.record_sync_event.await_args.kwargs
    assert payload["topic_id"] == topic_id
    assert payload["session_id"] == session_id
    assert payload["node_id"] == node_id
    assert payload["storage_kind"] == "neo4j"
    assert payload["operation"] == "node.expand"
    assert payload["status"] == "pending"
    assert "graph write boom" in payload["error_message"]


# ==================== Abilities ====================

@pytest.mark.asyncio
async def test_get_ability_record(app_client, db_conn):
    topic_id = "tp_ability"
    node_id = "nd_ability_test"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Ability Test"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO ability_records (topic_id, node_id, understand, explain) VALUES (?, ?, 50, 40)",
        (topic_id, node_id),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}/nodes/{node_id}/ability")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["understand"] == 50


@pytest.mark.asyncio
async def test_ability_overview(app_client, db_conn):
    topic_id = "tp_ab_ov"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Ability Overview"),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}/abilities/overview")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_list_frictions(app_client, db_conn):
    topic_id = "tp_fric"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Friction Test"),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}/frictions")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


# ==================== Graph ====================

@pytest.mark.asyncio
async def test_get_graph_fallback(app_client, db_conn):
    """Graph should return fallback when Neo4j is unavailable."""
    topic_id = "tp_graph"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Graph Test"),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}/graph")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


# ==================== Practice ====================

@pytest.mark.asyncio
async def test_get_practice_prompt_fallback(app_client, db_conn):
    """Practice prompt should fallback when AI is unavailable."""
    topic_id = "tp_practice"
    node_id = "nd_practice"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Practice Test"),
    )
    await db_conn.commit()

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/practice",
        json={"practice_type": "define"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["practice_type"] == "define"


@pytest.mark.asyncio
async def test_practice_cache_hit(app_client, db_conn):
    """Second request for same (topic, node, type) should hit cache."""
    topic_id = "tp_cache"
    node_id = "nd_cache"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Cache Test"),
    )
    await db_conn.execute(
        """INSERT OR IGNORE INTO practice_prompt_cache (topic_id, node_id, practice_type, prompt_text)
           VALUES (?, ?, ?, 'cached prompt')""",
        (topic_id, node_id, "define"),
    )
    await db_conn.commit()

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/practice",
        json={"practice_type": "define", "regenerate": False},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["data"]["prompt_text"] == "cached prompt"
    assert data["meta"].get("cached") is True


@pytest.mark.asyncio
async def test_submit_practice_fallback(app_client, db_conn):
    """Practice submit should work with fallback evaluation."""
    topic_id = "tp_submit"
    node_id = "nd_submit"
    session_id = "ss_submit"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Submit Test"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO sessions (session_id, topic_id, status) VALUES (?, ?, 'active')",
        (session_id, topic_id),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO ability_records (topic_id, node_id, understand, explain) VALUES (?, ?, 30, 20)",
        (topic_id, node_id),
    )
    await db_conn.commit()

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/practice/submit",
        json={
            "practice_type": "define",
            "prompt_text": "请定义这个概念",
            "user_answer": "这个概念是指用数学方法让计算机从数据中学习规律的技术。它包括监督学习、无监督学习和强化学习三个主要方向。",
            "session_id": session_id,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_submit_practice_rejects_cross_topic_session(app_client, db_conn):
    topic_id = "tp_submit_guard"
    other_topic_id = "tp_submit_other"
    node_id = "nd_submit_guard"
    foreign_session_id = "ss_submit_foreign"

    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Submit Guard"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (other_topic_id, "Submit Other"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO sessions (session_id, topic_id, status, practice_count) VALUES (?, ?, 'active', 0)",
        (foreign_session_id, other_topic_id),
    )
    await db_conn.commit()

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/practice/submit",
        json={
            "practice_type": "define",
            "prompt_text": "请定义这个概念",
            "user_answer": "这是一个足够长的答案，用来证明错误 session 不应该被接受。",
            "session_id": foreign_session_id,
        },
    )

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SESSION_NOT_FOUND"

    cursor = await db_conn.execute(
        "SELECT COUNT(*) AS count FROM practice_attempts WHERE topic_id = ?",
        (topic_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["count"] == 0

    cursor = await db_conn.execute(
        "SELECT practice_count FROM sessions WHERE session_id = ?",
        (foreign_session_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["practice_count"] == 0


@pytest.mark.asyncio
async def test_submit_practice_rejects_completed_session(app_client, db_conn):
    topic_id = "tp_submit_completed"
    node_id = "nd_submit_completed"
    session_id = "ss_submit_completed"

    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Submit Completed"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO sessions (session_id, topic_id, status, practice_count) VALUES (?, ?, 'completed', 0)",
        (session_id, topic_id),
    )
    await db_conn.commit()

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/practice/submit",
        json={
            "practice_type": "define",
            "prompt_text": "请定义这个概念",
            "user_answer": "这是一个足够长的答案，用来证明已完成会话不应该继续接收练习提交。",
            "session_id": session_id,
        },
    )

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SESSION_NOT_ACTIVE"

    cursor = await db_conn.execute(
        "SELECT COUNT(*) AS count FROM practice_attempts WHERE topic_id = ?",
        (topic_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["count"] == 0

    cursor = await db_conn.execute(
        "SELECT practice_count FROM sessions WHERE session_id = ?",
        (session_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["practice_count"] == 0


@pytest.mark.asyncio
async def test_submit_practice_rejects_invalid_body(app_client, db_conn):
    topic_id = "tp_submit_invalid"
    node_id = "nd_submit_invalid"

    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Submit Invalid"),
    )
    await db_conn.commit()

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/practice/submit",
        json={
            "practice_type": "define",
            "prompt_text": "请定义这个概念",
            "user_answer": "短",
        },
    )

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert data["error"]["code"] == "PRACTICE_SUBMIT_INVALID"


@pytest.mark.asyncio
async def test_save_expression_asset(app_client, db_conn):
    topic_id = "tp_expr"
    node_id = "nd_expr"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Expression Test"),
    )
    await db_conn.commit()

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/expression-assets",
        json={
            "expression_type": "define",
            "user_expression": "机器学习是让计算机从数据中学习的学科",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["asset_id"].startswith("ea_")


@pytest.mark.asyncio
async def test_save_expression_asset_rejects_invalid_body(app_client, db_conn):
    topic_id = "tp_expr_invalid"
    node_id = "nd_expr_invalid"

    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Expression Invalid"),
    )
    await db_conn.commit()

    r = await app_client.post(
        f"/api/v1/topics/{topic_id}/nodes/{node_id}/expression-assets",
        json={
            "expression_type": "not-a-real-type",
            "user_expression": "机器学习是让计算机从数据中学习的学科",
        },
    )

    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False
    assert data["error"]["code"] == "ASSET_REQUEST_INVALID"


@pytest.mark.asyncio
async def test_toggle_favorite(app_client, db_conn):
    topic_id = "tp_fav"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Favorite Test"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO expression_assets (asset_id, topic_id, node_id, expression_type, user_expression) VALUES (?, ?, ?, ?, ?)",
        ("ea_fav_test", topic_id, "nd_1", "define", "test expression"),
    )
    await db_conn.commit()

    r = await app_client.post(f"/api/v1/expression-assets/ea_fav_test/toggle-favorite")
    assert r.status_code == 200


# ==================== Reviews ====================

@pytest.mark.asyncio
async def test_list_reviews(app_client):
    r = await app_client.get("/api/v1/reviews")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_generate_review_queue(app_client, db_conn):
    topic_id = "tp_revq"
    node_id = "nd_revq"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Review Queue Test"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO ability_records (topic_id, node_id, understand, explain, recall) VALUES (?, ?, 30, 20, 15)",
        (topic_id, node_id),
    )
    await db_conn.commit()

    r = await app_client.post(f"/api/v1/topics/{topic_id}/reviews/generate")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_skip_review_not_found(app_client):
    r = await app_client.post("/api/v1/reviews/rv_nonexistent/skip")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_snooze_review_not_found(app_client):
    r = await app_client.post("/api/v1/reviews/rv_nonexistent/snooze")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is False


# ==================== Stats ====================

@pytest.mark.asyncio
async def test_global_stats(app_client, db_conn):
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        ("tp_stats1", "Stats 1"),
    )
    await db_conn.commit()

    r = await app_client.get("/api/v1/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_topic_stats(app_client, db_conn):
    topic_id = "tp_tstats"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status, total_nodes, learned_nodes, total_practice) VALUES (?, ?, 'active', 10, 3, 5)",
        (topic_id, "Topic Stats"),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/stats/topics/{topic_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


# ==================== Export ====================

@pytest.mark.asyncio
async def test_export_markdown(app_client, db_conn):
    topic_id = "tp_export"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status, source_type, learning_intent, mode) VALUES (?, ?, 'active', 'concept', 'build_system', 'full_system')",
        (topic_id, "Export Test"),
    )
    await db_conn.commit()

    r = await app_client.post(f"/api/v1/topics/{topic_id}/export", json={"export_type": "markdown"})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "Export Test" in data["data"]["content"]


@pytest.mark.asyncio
async def test_export_json(app_client, db_conn):
    topic_id = "tp_export_json"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Export JSON"),
    )
    await db_conn.commit()

    r = await app_client.post(f"/api/v1/topics/{topic_id}/export", json={"export_type": "json"})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    import json
    parsed = json.loads(data["data"]["content"])
    assert parsed["topic"]["title"] == "Export JSON"


# ==================== Deferred Nodes ====================

@pytest.mark.asyncio
async def test_list_deferred_nodes(app_client, db_conn):
    topic_id = "tp_deferred"
    node_id = "nd_deferred_list"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Deferred List"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO deferred_nodes (topic_id, node_id, reason) VALUES (?, ?, '太复杂')",
        (topic_id, node_id),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}/deferred")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1


# ==================== Practice Attempts ====================

@pytest.mark.asyncio
async def test_list_practice_attempts(app_client, db_conn):
    topic_id = "tp_attempts"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Practice Attempts"),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}/practice-attempts")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


# ==================== Recommended Practice ====================

@pytest.mark.asyncio
async def test_recommended_practice(app_client, db_conn):
    topic_id = "tp_rec"
    node_id = "nd_rec"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Recommended"),
    )
    await db_conn.execute(
        "INSERT OR IGNORE INTO ability_records (topic_id, node_id, understand, explain, recall) VALUES (?, ?, 30, 20, 15)",
        (topic_id, node_id),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}/nodes/{node_id}/recommended-practice")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


# ==================== Ability Snapshots ====================

@pytest.mark.asyncio
async def test_list_ability_snapshots(app_client, db_conn):
    topic_id = "tp_snap"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Snapshots"),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}/abilities/snapshots")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True


# ==================== Entry Node ====================

@pytest.mark.asyncio
async def test_entry_node_fallback(app_client, db_conn):
    """Entry node should work when Neo4j is unavailable."""
    topic_id = "tp_entry"
    await db_conn.execute(
        "INSERT OR IGNORE INTO topics (topic_id, title, status, entry_node_id) VALUES (?, ?, 'active', 'nd_entry')",
        (topic_id, "Entry Test"),
    )
    await db_conn.commit()

    r = await app_client.get(f"/api/v1/topics/{topic_id}/entry-node")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert data["data"]["node_id"] == "nd_entry"


# ==================== Global Deferred ====================

@pytest.mark.asyncio
async def test_list_all_deferred_nodes(app_client):
    r = await app_client.get("/api/v1/deferred-nodes")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
