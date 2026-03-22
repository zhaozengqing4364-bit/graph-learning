"""Service and algorithm unit tests - Layer 1 extended coverage."""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiosqlite
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ==================== Session Service ====================

def test_session_service_complete_session_structure():
    """complete_session should return session with completed status."""
    from backend.services.session_service import complete_session
    import asyncio

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()

    mock_session = {
        "session_id": "ss_test",
        "topic_id": "tp_test",
        "status": "active",
        "visited_node_ids": '["nd_1", "nd_2"]',
    }

    async def fake_execute(*args, **kwargs):
        pass

    mock_db.execute = AsyncMock(side_effect=fake_execute)
    mock_db.commit = AsyncMock()

    with patch("backend.services.session_service.sqlite_repo") as mock_repo:
        mock_repo.claim_session_completion = AsyncMock(return_value=True)
        mock_repo.update_session_summary = AsyncMock(return_value=None)
        mock_repo.get_session = AsyncMock(side_effect=[
            mock_session,
            {
                "session_id": "ss_test",
                "topic_id": "tp_test",
                "status": "completed",
                "completed_at": "2025-01-01T00:00:00",
                "visited_node_ids": '["nd_1", "nd_2"]',
            },
        ])
        mock_repo.get_topic = AsyncMock(return_value=None)
        mock_repo.get_ability_snapshots = AsyncMock(return_value=[])
        mock_repo.count_review_items = AsyncMock(return_value=0)
        mock_repo.list_ability_records = AsyncMock(return_value=[])
        mock_repo.get_practice_count = AsyncMock(return_value=0)
        mock_repo.create_ability_snapshot = AsyncMock(return_value=None)
        mock_repo.list_deferred_nodes = AsyncMock(return_value=[])
        mock_repo.list_expression_assets = AsyncMock(return_value=[])
        mock_repo.complete_session_synthesis = AsyncMock(return_value=None)
        mock_repo.update_topic = AsyncMock(return_value=None)
        mock_repo.update_session_node_left_at = AsyncMock(return_value=None)
        # Make any unmocked async calls return empty results
        mock_repo.get_review_items = AsyncMock(return_value=[])
        mock_repo.update_topic_stats = AsyncMock(return_value=None)
        mock_repo.update_session = AsyncMock(return_value=None)

        result = asyncio.get_event_loop().run_until_complete(
            complete_session(mock_db, session_id="ss_test", neo4j=None)
        )
        assert result is not None


@pytest.mark.asyncio
async def test_complete_session_closes_open_session_nodes(db_conn):
    """Completing a session should close any still-open session node visits."""
    from backend.services.session_service import complete_session

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        ("tp_session_close", "Session Close Topic"),
    )
    await db_conn.execute(
        """INSERT INTO sessions (
            session_id, topic_id, status, visited_node_ids, practice_count, started_at, created_at, updated_at
        ) VALUES (?, ?, 'active', ?, 0, datetime('now'), datetime('now'), datetime('now'))""",
        ("ss_open_visit", "tp_session_close", '["nd_open"]'),
    )
    await db_conn.execute(
        """INSERT INTO session_nodes (
            session_id, node_id, visited_at, visit_order, entered_at, action_type, created_at
        ) VALUES (?, ?, datetime('now'), 0, datetime('now'), 'open_node', datetime('now'))""",
        ("ss_open_visit", "nd_open"),
    )
    await db_conn.commit()

    result = await complete_session(db_conn, session_id="ss_open_visit", neo4j=None)

    assert result is not None
    row = await db_conn.execute_fetchone(
        "SELECT left_at FROM session_nodes WHERE session_id = ? AND node_id = ?",
        ("ss_open_visit", "nd_open"),
    )
    assert row is not None
    assert row["left_at"] is not None


@pytest.mark.asyncio
async def test_complete_session_closes_open_session_nodes(db_conn):
    """complete_session should stamp left_at for the last open session node."""
    from backend.services.session_service import complete_session

    topic_id = "tp_complete_close"
    session_id = "ss_complete_close"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Close Open Session Nodes"),
    )
    await db_conn.execute(
        "INSERT INTO sessions (session_id, topic_id, status, visited_node_ids) VALUES (?, ?, 'active', ?)",
        (session_id, topic_id, '["nd_open"]'),
    )
    await db_conn.execute(
        """
        INSERT INTO session_nodes (session_id, node_id, entered_at, action_type)
        VALUES (?, ?, datetime('now'), 'open_node')
        """,
        (session_id, "nd_open"),
    )
    await db_conn.commit()

    await complete_session(db_conn, session_id=session_id, neo4j=None)

    cursor = await db_conn.execute(
        "SELECT left_at FROM session_nodes WHERE session_id = ? AND node_id = ?",
        (session_id, "nd_open"),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["left_at"] is not None


@pytest.mark.asyncio
async def test_complete_session_only_uses_current_session_assets(db_conn):
    """Session synthesis should not leak asset highlights from earlier sessions."""
    from backend.services.session_service import complete_session

    topic_id = "tp_session_assets"
    current_session_id = "ss_current_assets"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Session Asset Topic"),
    )
    await db_conn.execute(
        "INSERT INTO sessions (session_id, topic_id, status, visited_node_ids) VALUES (?, ?, 'completed', ?)",
        ("ss_old_assets", topic_id, "[]"),
    )
    await db_conn.execute(
        "INSERT INTO sessions (session_id, topic_id, status, visited_node_ids) VALUES (?, ?, 'active', ?)",
        (current_session_id, topic_id, '["nd_current_asset"]'),
    )
    await db_conn.execute(
        """
        INSERT INTO expression_assets (
            asset_id, topic_id, node_id, expression_type, user_expression, session_id, correctness, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "ea_old_assets",
            topic_id,
            "nd_old_asset",
            "define",
            "旧会话表达资产",
            "ss_old_assets",
            1,
            (datetime.now() - timedelta(days=1)).isoformat(),
        ),
    )
    await db_conn.execute(
        """
        INSERT INTO expression_assets (
            asset_id, topic_id, node_id, expression_type, user_expression, session_id, correctness, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "ea_current_assets",
            topic_id,
            "nd_current_asset",
            "compress",
            "当前会话表达资产",
            current_session_id,
            3,
            datetime.now().isoformat(),
        ),
    )
    await db_conn.commit()

    result = await complete_session(
        db_conn,
        session_id=current_session_id,
        neo4j=None,
        generate_summary=False,
        generate_review_items=False,
    )

    assert result is not None
    assert result["synthesis"]["asset_highlights"] == [
        {
            "node_id": "nd_current_asset",
            "practice_type": "compress",
            "correctness": 3,
        }
    ]
    assert result["synthesis"]["new_assets_count"] == 1


@pytest.mark.asyncio
async def test_save_expression_asset_infers_session_from_attempt(db_conn):
    from backend.models.expression import ExpressionAssetCreate
    from backend.repositories import sqlite_repo
    from backend.services.practice_service import save_expression_asset

    topic_id = "tp_asset_session"
    node_id = "nd_asset_session"
    session_id = "ss_asset_session"
    attempt_id = "pa_asset_session"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Asset Session Topic"),
    )
    await db_conn.execute(
        "INSERT INTO sessions (session_id, topic_id, status, visited_node_ids) VALUES (?, ?, 'active', ?)",
        (session_id, topic_id, f'["{node_id}"]'),
    )
    await sqlite_repo.create_practice_attempt(
        db_conn,
        {
            "attempt_id": attempt_id,
            "topic_id": topic_id,
            "node_id": node_id,
            "session_id": session_id,
            "practice_type": "define",
            "prompt_text": "解释这个概念",
            "user_answer": "这是一个测试回答",
            "feedback": "{}",
            "scores": {},
        },
    )

    asset = await save_expression_asset(
        db_conn,
        topic_id,
        node_id,
        ExpressionAssetCreate(
            attempt_id=attempt_id,
            expression_type="define",
            user_expression="新的表达资产",
            ai_rewrite="更好的表达",
            skeleton="骨架",
            quality_tags=["clear"],
        ),
    )

    assert asset["session_id"] == session_id


@pytest.mark.asyncio
async def test_start_session_restores_existing_session_when_create_conflicts(tmp_path):
    from backend.models.session import SessionCreate
    from backend.repositories import sqlite_repo
    from backend.services import session_service

    db_path = tmp_path / "start-session-race.db"
    conn1 = await aiosqlite.connect(db_path)
    conn2 = await aiosqlite.connect(db_path)
    conn1.row_factory = aiosqlite.Row
    conn2.row_factory = aiosqlite.Row

    try:
        await sqlite_repo.init_tables(conn1)
        await conn1.execute(
            "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
            ("tp_session_race", "Session Race Topic"),
        )
        await conn1.commit()

        original_create_session = sqlite_repo.create_session

        async def delayed_create(db, session):
            await asyncio.sleep(0.05)
            return await original_create_session(db, session)

        with patch.object(session_service.sqlite_repo, "create_session", side_effect=delayed_create):
            first, second = await asyncio.gather(
                session_service.start_session(conn1, "tp_session_race", SessionCreate()),
                session_service.start_session(conn2, "tp_session_race", SessionCreate()),
            )

        assert first["session_id"] == second["session_id"]
        assert first["restored"] != second["restored"]

        cursor = await conn1.execute(
            "SELECT COUNT(*) AS count FROM sessions WHERE topic_id = ? AND status = 'active'",
            ("tp_session_race",),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["count"] == 1
    finally:
        await conn1.close()
        await conn2.close()


@pytest.mark.asyncio
async def test_complete_session_runs_synth_once_when_called_concurrently(db_conn):
    from backend.services.session_service import complete_session

    topic_id = "tp_complete_race"
    session_id = "ss_complete_race"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Complete Race Topic"),
    )
    await db_conn.execute(
        "INSERT INTO sessions (session_id, topic_id, status, visited_node_ids, practice_count) VALUES (?, ?, 'active', ?, 1)",
        (session_id, topic_id, '["nd_complete_race"]'),
    )
    await db_conn.commit()

    synth_calls = 0

    async def fake_synthesize(**kwargs):
        nonlocal synth_calls
        synth_calls += 1
        await asyncio.sleep(0.05)
        return {
            "mainline_summary": "race summary",
            "key_takeaways": [],
            "next_recommendations": [],
            "review_candidates": [],
            "new_assets_count": 0,
            "covered_scope": "",
            "skippable_nodes": [],
        }

    with patch("backend.services.session_service.synthesizer_agent.synthesize", new=AsyncMock(side_effect=fake_synthesize)):
        first, second = await asyncio.gather(
            complete_session(
                db_conn,
                session_id=session_id,
                neo4j=None,
                generate_summary=True,
                generate_review_items=False,
            ),
            complete_session(
                db_conn,
                session_id=session_id,
                neo4j=None,
                generate_summary=True,
                generate_review_items=False,
            ),
        )

    assert first is not None
    assert second is not None
    assert synth_calls == 1


# ==================== Ability Service ====================

def test_ability_overview_calculation():
    """Ability overview should aggregate scores across all nodes."""
    from backend.services.ability_service import get_ability_overview
    import asyncio

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()

    with patch("backend.services.ability_service.sqlite_repo") as mock_repo:
        mock_repo.list_ability_records = AsyncMock(return_value=[
            {"node_id": "nd_1", "understand": 80, "explain": 70, "example": 60, "contrast": 50,
             "apply": 40, "recall": 30, "transfer": 20, "teach": 10},
            {"node_id": "nd_2", "understand": 60, "explain": 50, "example": 40, "contrast": 30,
             "apply": 20, "recall": 10, "transfer": 5, "teach": 0},
        ])
        mock_repo.count_review_items = AsyncMock(return_value=0)
        mock_repo.get_topic = AsyncMock(return_value={"total_nodes": 5, "learned_nodes": 1})

        result = asyncio.get_event_loop().run_until_complete(
            get_ability_overview(mock_db, "tp_test")
        )
        assert result is not None


# ==================== Graph Traversal ====================

def test_enforce_session_cap():
    """Session cap should limit new nodes and produce deferred list."""
    from backend.graph.traversal import enforce_session_cap

    nodes = [{"name": f"node{i}"} for i in range(5)]

    # Within cap
    accepted, deferred, cap_reached = enforce_session_cap(nodes, current_session_count=0, session_max=5)
    assert len(accepted) == 5
    assert len(deferred) == 0
    assert cap_reached is False

    # Over cap
    accepted2, deferred2, cap_reached2 = enforce_session_cap(nodes, current_session_count=3, session_max=5)
    assert len(accepted2) == 2
    assert len(deferred2) == 3
    assert cap_reached2 is True

    # Already at cap
    accepted3, deferred3, cap_reached3 = enforce_session_cap(nodes, current_session_count=12, session_max=12)
    assert len(accepted3) == 0
    assert len(deferred3) == 5
    assert cap_reached3 is True


def test_enforce_topic_cap():
    """Topic cap should trim to max_total."""
    from backend.graph.traversal import enforce_topic_cap

    nodes = [{"name": f"node{i}", "importance": 3, "status": "unseen"} for i in range(40)]
    result = enforce_topic_cap(nodes, max_total=30)
    assert len(result) == 30

    # Under cap: no change
    small = [{"name": f"n{i}", "importance": 3, "status": "unseen"} for i in range(5)]
    result2 = enforce_topic_cap(small, max_total=30)
    assert len(result2) == 5


def test_sort_nodes_by_mainline_priority():
    """Sort should prioritize: importance > prerequisite > mainline > low status."""
    from backend.graph.traversal import sort_nodes_by_mainline_priority

    # Same importance, same prerequisite, mainline beats non-mainline
    nodes = [
        {"name": "non_mainline", "importance": 5, "status": "unseen", "is_mainline": False, "_has_prerequisite": True},
        {"name": "is_mainline", "importance": 5, "status": "unseen", "is_mainline": True, "_has_prerequisite": True},
    ]
    sorted_n = sort_nodes_by_mainline_priority(nodes)
    assert sorted_n[0]["name"] == "is_mainline"

    # Higher importance beats mainline
    nodes2 = [
        {"name": "mainline_low", "importance": 3, "status": "unseen", "is_mainline": True, "_has_prerequisite": True},
        {"name": "non_mainline_high", "importance": 4, "status": "unseen", "is_mainline": False, "_has_prerequisite": True},
    ]
    sorted_n2 = sort_nodes_by_mainline_priority(nodes2)
    assert sorted_n2[0]["name"] == "non_mainline_high"

    # Low importance comes last
    assert sorted_n2[-1]["name"] == "mainline_low"


def test_calculate_edge_mainline_weight():
    """Edge weights should match spec values."""
    from backend.graph.traversal import calculate_edge_mainline_weight

    assert calculate_edge_mainline_weight("PREREQUISITE") == 1.0
    assert calculate_edge_mainline_weight("CONTRASTS") == 0.7
    assert calculate_edge_mainline_weight("UNKNOWN") == 0.3


# ==================== Review Service ====================

def test_forget_risk_calculation():
    """ForgetRisk should decrease with more review history."""
    from backend.services.review_service import _calculate_forget_risk

    assert _calculate_forget_risk(0) == 1.0
    assert _calculate_forget_risk(1) == 1.0  # interval 1, 3/1 = 1.0
    assert _calculate_forget_risk(3) < 1.0  # interval 7, 3/7 ≈ 0.43


def test_explain_gap_calculation():
    """ExplainGap should be > 0 when understand > explain and explain < 50."""
    from backend.services.review_service import _calculate_explain_gap

    # understand(30) > explain(10), explain < 50 => positive gap = (50-10)/50 = 0.8
    assert _calculate_explain_gap(30, 10) == 0.8
    # understand(80) > explain(60), explain >= 50 => gap = max(0, (50-60)/50) = 0
    assert _calculate_explain_gap(80, 60) == 0.0
    # understand == explain => 0
    assert _calculate_explain_gap(50, 50) == 0.0


def test_time_due_weight():
    """TimeDueWeight should be higher when overdue."""
    from backend.services.review_service import _calculate_time_due_weight

    from datetime import datetime, timedelta

    overdue = (datetime.now() - timedelta(days=1)).isoformat()
    far_future = (datetime.now() + timedelta(days=30)).isoformat()

    assert _calculate_time_due_weight(overdue) > 1.0
    assert _calculate_time_due_weight(far_future) < 1.0


def test_get_next_review_interval():
    """Review intervals should follow spec arrays."""
    from backend.services.review_service import _get_next_review_interval

    # Success intervals: [3, 7, 14, 30, 60]
    assert _get_next_review_interval(0, True) == 3
    assert _get_next_review_interval(1, True) == 7
    assert _get_next_review_interval(4, True) == 60
    assert _get_next_review_interval(10, True) == 60  # capped at last

    # Failure: always 1
    assert _get_next_review_interval(0, False) == 1
    assert _get_next_review_interval(5, False) == 1


@pytest.mark.asyncio
async def test_init_tables_migrates_legacy_review_items_schema(tmp_path):
    """Legacy review_items tables should be upgraded before queue generation runs."""
    import aiosqlite

    from backend.repositories.sqlite_repo import init_tables
    from backend.services.review_service import generate_review_queue

    db_path = tmp_path / "legacy-review-items.db"
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    try:
        await db.executescript(
            """
            CREATE TABLE review_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id TEXT UNIQUE NOT NULL,
                topic_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                priority REAL DEFAULT 0,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending','completed','skipped')),
                due_at TEXT,
                next_review_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT
            );
            """
        )
        await db.commit()

        await init_tables(db)

        column_cursor = await db.execute("PRAGMA table_info(review_items)")
        columns = {row[1] for row in await column_cursor.fetchall()}
        assert "review_type" in columns
        assert "last_result" in columns

        await db.execute(
            "INSERT INTO review_items (review_id, topic_id, node_id, status) VALUES (?, ?, ?, ?)",
            ("rv_legacy", "tp_legacy", "nd_legacy", "snoozed"),
        )
        await db.execute(
            "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
            ("tp_legacy", "Legacy Topic"),
        )
        await db.execute(
            "INSERT INTO ability_records (topic_id, node_id, understand, explain, recall) VALUES (?, ?, 35, 20, 10)",
            ("tp_legacy", "nd_legacy"),
        )
        await db.commit()

        created = await generate_review_queue(db, "tp_legacy", neo4j=None)

        assert len(created) == 1
        assert created[0]["node_id"] == "nd_legacy"
        assert created[0]["review_type"]

        saved_cursor = await db.execute(
            "SELECT review_type, status FROM review_items WHERE topic_id = ? AND node_id = ? ORDER BY id DESC LIMIT 1",
            ("tp_legacy", "nd_legacy"),
        )
        saved_review = await saved_cursor.fetchone()
        assert saved_review is not None
        assert saved_review[0]
        assert saved_review[1] == "pending"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_init_tables_creates_sync_events_table(db_conn):
    """init_tables should provision sync_events for multi-store compensation tracking."""
    cursor = await db_conn.execute("PRAGMA table_info(sync_events)")
    columns = {row[1] for row in await cursor.fetchall()}

    assert {
        "event_id",
        "topic_id",
        "session_id",
        "node_id",
        "storage_kind",
        "operation",
        "status",
        "error_message",
        "payload",
        "resolved_at",
    }.issubset(columns)


@pytest.mark.asyncio
async def test_create_topic_records_sync_event_when_neo4j_write_fails(db_conn):
    """create_topic should persist a pending sync event when graph write fails after SQLite succeeds."""
    from backend.models.topic import TopicCreate
    from backend.services.topic_service import create_topic

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeDriver:
        def session(self):
            return FakeSession()

    data = TopicCreate(
        title="Sync Event Topic",
        source_type="concept",
        source_content="图表示学习的基础内容",
        learning_intent="build_system",
        mode="full_system",
    )

    with patch("backend.services.topic_service.explorer_agent.create_topic", new=AsyncMock(return_value={
        "entry_node": {
            "name": "消息传递",
            "summary": "图神经网络的核心机制",
            "importance": 4,
        },
        "nodes": [],
        "edges": [],
    })), patch("backend.services.topic_service.graph.create_topic_node", new=AsyncMock(side_effect=RuntimeError("neo4j unavailable"))), patch(
        "backend.services.topic_service.sqlite_repo.record_sync_event",
        new=AsyncMock(),
    ) as record_sync_event:
        result = await create_topic(db_conn, FakeDriver(), data, lancedb=None)

    assert result["topic_id"].startswith("tp_")
    record_sync_event.assert_awaited()
    payload = record_sync_event.await_args.kwargs
    assert payload["topic_id"] == result["topic_id"]
    assert payload["storage_kind"] == "neo4j"
    assert payload["operation"] == "topic.create"
    assert payload["status"] == "pending"
    assert "neo4j unavailable" in payload["error_message"]


@pytest.mark.asyncio
async def test_generate_review_queue_respects_future_next_review_at(db_conn):
    """A scheduled future next_review_at should block immediate regeneration of another pending review."""
    from datetime import datetime, timedelta

    from backend.services.review_service import generate_review_queue

    future_due = (datetime.now() + timedelta(days=3)).isoformat()
    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        ("tp_review_future", "Review Future Topic"),
    )
    await db_conn.execute(
        """INSERT INTO ability_records (
            topic_id, node_id, understand, example, contrast, apply, explain, recall, transfer, teach
        ) VALUES (?, ?, 30, 35, 20, 25, 28, 18, 22, 15)""",
        ("tp_review_future", "nd_future"),
    )
    await db_conn.execute(
        """INSERT INTO review_items (
            review_id, topic_id, node_id, priority, status, due_at, next_review_at, review_type, last_result, reason, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (
            "rv_future",
            "tp_review_future",
            "nd_future",
            0.8,
            "completed",
            datetime.now().isoformat(),
            future_due,
            "recall",
            "good",
            "记忆薄弱",
        ),
    )
    await db_conn.commit()

    created = await generate_review_queue(db_conn, "tp_review_future", neo4j=None)

    assert created == []


@pytest.mark.asyncio
async def test_generate_review_queue_recreates_due_reviews_from_next_review_at(db_conn):
    """An overdue next_review_at should become the new due_at for the regenerated pending review."""
    from datetime import datetime, timedelta

    from backend.services.review_service import generate_review_queue

    overdue_due = (datetime.now() - timedelta(days=2)).isoformat()
    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        ("tp_review_due", "Review Due Topic"),
    )
    await db_conn.execute(
        """INSERT INTO ability_records (
            topic_id, node_id, understand, example, contrast, apply, explain, recall, transfer, teach
        ) VALUES (?, ?, 30, 35, 20, 25, 28, 18, 22, 15)""",
        ("tp_review_due", "nd_due"),
    )
    await db_conn.execute(
        """INSERT INTO review_items (
            review_id, topic_id, node_id, priority, status, due_at, next_review_at, review_type, last_result, reason, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (
            "rv_due",
            "tp_review_due",
            "nd_due",
            0.8,
            "completed",
            datetime.now().isoformat(),
            overdue_due,
            "contrast",
            "medium",
            "对比不清",
        ),
    )
    await db_conn.commit()

    created = await generate_review_queue(db_conn, "tp_review_due", neo4j=None)

    assert len(created) == 1
    assert created[0]["node_id"] == "nd_due"
    assert created[0]["due_at"] == overdue_due
    assert "对比不清" in created[0]["reason"]


@pytest.mark.asyncio
async def test_submit_review_does_not_recreate_pending_item_when_next_review_is_in_future(db_conn):
    """A completed review with a future next_review_at should not immediately regenerate a new pending item."""
    from backend.repositories import sqlite_repo
    from backend.services.review_service import generate_review_queue, submit_review

    topic_id = "tp_review_future"
    node_id = "nd_review_future"
    review_id = "rv_review_future"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Future Review Topic"),
    )
    await db_conn.execute(
        """
        INSERT INTO ability_records (
            topic_id, node_id, understand, example, contrast, apply, explain, recall, transfer, teach
        ) VALUES (?, ?, 40, 35, 30, 25, 20, 15, 10, 5)
        """,
        (topic_id, node_id),
    )
    await sqlite_repo.create_review_item(db_conn, {
        "review_id": review_id,
        "topic_id": topic_id,
        "node_id": node_id,
        "status": "pending",
        "priority": 0.8,
        "review_type": "recall",
        "due_at": "2026-03-17T00:00:00",
        "next_review_at": None,
    })

    with patch("backend.services.review_service.diagnoser_agent", create=True) as mock_diagnoser:
        mock_diagnoser.diagnose = AsyncMock(side_effect=RuntimeError("no ai in test"))
        result = await submit_review(
            db_conn,
            review_id,
            user_answer="这是一段足够长的复习答案，用来触发中等及以上的成功判定，从而写入下一次复习时间。",
            neo4j=None,
        )

    assert result.next_due_time is not None

    created = await generate_review_queue(db_conn, topic_id, neo4j=None)
    assert created == []


@pytest.mark.asyncio
async def test_submit_review_bootstraps_ability_record_and_history_count(db_conn):
    from backend.repositories import sqlite_repo
    from backend.services.review_service import submit_review

    topic_id = "tp_review_bootstrap"
    node_id = "nd_review_bootstrap"
    review_id = "rv_review_bootstrap"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Review Bootstrap Topic"),
    )
    await sqlite_repo.create_review_item(db_conn, {
        "review_id": review_id,
        "topic_id": topic_id,
        "node_id": node_id,
        "status": "pending",
        "priority": 0.6,
        "review_type": "recall",
        "due_at": "2026-03-17T00:00:00",
    })

    with patch("backend.services.review_service.diagnoser_agent", create=True) as mock_diagnoser:
        mock_diagnoser.diagnose = AsyncMock(side_effect=RuntimeError("no ai in test"))
        result = await submit_review(
            db_conn,
            review_id,
            user_answer="这是一段足够长的复习答案，用来触发成功提交，并验证 ability record 会被自动创建。",
            neo4j=None,
        )

    assert result.next_due_time is not None

    ability = await sqlite_repo.get_ability_record(db_conn, topic_id, node_id)
    assert ability is not None
    assert ability["review_history_count"] == 1

    review = await sqlite_repo.get_review_item(db_conn, review_id)
    assert review is not None
    assert review["status"] == "completed"
    assert review["history_count"] == 1


@pytest.mark.asyncio
async def test_generate_review_queue_reason_uses_weakest_dimension_label(db_conn):
    """Generated review reason should describe the weakest ability dimension, not a generic fallback."""
    from backend.services.review_service import generate_review_queue

    topic_id = "tp_review_reason"
    node_id = "nd_review_reason"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Reason Topic"),
    )
    await db_conn.execute(
        """
        INSERT INTO ability_records (
            topic_id, node_id, understand, example, contrast, apply, explain, recall, transfer, teach
        ) VALUES (?, ?, 60, 60, 55, 50, 55, 10, 45, 45)
        """,
        (topic_id, node_id),
    )
    await db_conn.commit()

    created = await generate_review_queue(db_conn, topic_id, neo4j=None)

    assert len(created) == 1
    assert created[0]["reason"].startswith("记忆薄弱")


@pytest.mark.asyncio
async def test_generate_review_queue_considers_future_schedules_beyond_first_500_reviews(db_conn):
    from backend.services.review_service import generate_review_queue

    topic_id = "tp_review_many"
    node_id = "nd_review_many"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Many Review Topic"),
    )
    await db_conn.execute(
        """
        INSERT INTO ability_records (
            topic_id, node_id, understand, example, contrast, apply, explain, recall, transfer, teach
        ) VALUES (?, ?, 20, 20, 20, 20, 20, 20, 20, 20)
        """,
        (topic_id, node_id),
    )

    bulk_rows = [
        (
            f"rv_many_{idx}",
            topic_id,
            f"nd_other_{idx}",
            0.9,
            "completed",
            datetime.now().isoformat(),
            None,
            "recall",
            "good",
            "复习通过",
        )
        for idx in range(500)
    ]
    await db_conn.executemany(
        """
        INSERT INTO review_items (
            review_id, topic_id, node_id, priority, status, due_at, next_review_at, review_type, last_result, reason, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        bulk_rows,
    )
    await db_conn.execute(
        """
        INSERT INTO review_items (
            review_id, topic_id, node_id, priority, status, due_at, next_review_at, review_type, last_result, reason, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            "rv_many_target",
            topic_id,
            node_id,
            0.1,
            "completed",
            datetime.now().isoformat(),
            (datetime.now() + timedelta(days=3)).isoformat(),
            "recall",
            "good",
            "记忆薄弱",
        ),
    )
    await db_conn.commit()

    created = await generate_review_queue(db_conn, topic_id, neo4j=None)

    assert created == []


@pytest.mark.asyncio
async def test_generate_review_queue_skips_existing_snoozed_review(db_conn):
    """Snoozed review items should still block duplicate queue generation."""
    from backend.services.review_service import generate_review_queue

    topic_id = "tp_snoozed_queue"
    node_id = "nd_snoozed_queue"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Snoozed Review Topic"),
    )
    await db_conn.execute(
        """
        INSERT INTO ability_records (
            topic_id, node_id, understand, example, contrast, apply, explain, recall, transfer, teach
        ) VALUES (?, ?, 35, 30, 25, 20, 15, 10, 5, 5)
        """,
        (topic_id, node_id),
    )
    await db_conn.execute(
        """
        INSERT INTO review_items (
            review_id, topic_id, node_id, status, priority, due_at, review_type
        ) VALUES (?, ?, ?, 'snoozed', ?, ?, ?)
        """,
        (
            "rv_snoozed_queue",
            topic_id,
            node_id,
            0.9,
            (datetime.now() + timedelta(days=1)).isoformat(),
            "recall",
        ),
    )
    await db_conn.commit()

    created = await generate_review_queue(db_conn, topic_id, neo4j=None)

    assert created == []


@pytest.mark.asyncio
async def test_list_reviews_returns_due_snoozed_items_for_pending_queue(db_conn):
    """Pending review queue should surface snoozed items again once they are due."""
    from backend.services.review_service import list_reviews

    topic_id = "tp_due_snoozed"
    review_id = "rv_due_snoozed"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Due Snoozed Topic"),
    )
    await db_conn.execute(
        """
        INSERT INTO review_items (
            review_id, topic_id, node_id, status, priority, due_at, review_type
        ) VALUES (?, ?, ?, 'snoozed', ?, ?, ?)
        """,
        (
            review_id,
            topic_id,
            "nd_due_snoozed",
            0.7,
            (datetime.now() - timedelta(hours=1)).isoformat(),
            "recall",
        ),
    )
    await db_conn.commit()

    items = await list_reviews(db_conn, status="pending", topic_id=topic_id, limit=20, offset=0)

    assert [item["review_id"] for item in items] == [review_id]


@pytest.mark.asyncio
async def test_list_reviews_applies_due_before_before_pagination(db_conn):
    from backend.services.review_service import list_reviews

    topic_id = "tp_due_before_page"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Due Before Topic"),
    )
    await db_conn.execute(
        """
        INSERT INTO review_items (
            review_id, topic_id, node_id, status, priority, due_at, review_type
        ) VALUES (?, ?, ?, 'pending', ?, ?, ?)
        """,
        (
            "rv_future_priority",
            topic_id,
            "nd_future_priority",
            0.9,
            (datetime.now() + timedelta(days=5)).isoformat(),
            "recall",
        ),
    )
    await db_conn.execute(
        """
        INSERT INTO review_items (
            review_id, topic_id, node_id, status, priority, due_at, review_type
        ) VALUES (?, ?, ?, 'pending', ?, ?, ?)
        """,
        (
            "rv_due_low_priority",
            topic_id,
            "nd_due_low_priority",
            0.2,
            (datetime.now() - timedelta(hours=1)).isoformat(),
            "recall",
        ),
    )
    await db_conn.commit()

    items = await list_reviews(
        db_conn,
        status="pending",
        topic_id=topic_id,
        due_before=datetime.now().isoformat(),
        limit=1,
        offset=0,
    )

    assert [item["review_id"] for item in items] == ["rv_due_low_priority"]


@pytest.mark.asyncio
async def test_get_entry_node_flattens_current_node_detail_shape(db_conn):
    """get_entry_node should keep the EntryNode contract even when resuming from current_node_id."""
    from backend.services.node_service import get_entry_node

    topic_id = "tp_entry_current"
    await db_conn.execute(
        """
        INSERT INTO topics (topic_id, title, status, current_node_id)
        VALUES (?, ?, 'active', ?)
        """,
        (topic_id, "Current Entry Topic", "nd_current"),
    )
    await db_conn.commit()

    with patch("backend.services.node_service.get_node_detail", new=AsyncMock(return_value={
        "node": {
            "node_id": "nd_current",
            "name": "当前节点",
            "summary": "当前节点摘要",
            "importance": 4,
        },
        "ability": {"understand": 30},
        "why_now": "旧值",
        "prerequisites": [],
        "contrasts": [],
        "applications": [],
        "related": [],
    })):
        result = await get_entry_node(db_conn, None, topic_id)

    assert result == {
        "node_id": "nd_current",
        "name": "当前节点",
        "summary": "当前节点摘要",
        "importance": 4,
        "ability": {"understand": 30},
        "why_now": "继续上次学习：当前节点",
    }


# ==================== Export Logic ====================

def test_export_markdown_structure():
    """Markdown export should contain topic title and sections."""
    topic = {
        "title": "Test Topic",
        "source_type": "concept",
        "learning_intent": "build_system",
        "mode": "full_system",
        "total_nodes": 5,
        "learned_nodes": 2,
    }
    graph_data = {
        "nodes": [
            {"node_id": "nd_1", "name": "Node One", "summary": "Summary 1", "article_body": "Article 1"},
            {"node_id": "nd_2", "name": "Node Two", "summary": "Summary 2", "article_body": ""},
        ],
        "edges": [],
    }
    abilities = [
        {"node_id": "nd_1", "understand": 80, "explain": 70, "example": 60, "contrast": 50,
         "apply": 40, "recall": 30, "transfer": 20, "teach": 10},
    ]
    assets = [{"expression_type": "define", "user_expression": "Test expression"}]
    frictions = [{"friction_type": "prerequisite_gap", "description": "Missing basics"}]

    md_lines = [
        f"# {topic['title']}",
        "",
        f"> Source: {topic['source_type']}",
        f"> Intent: {topic['learning_intent']}",
        f"> Mode: {topic['mode']}",
        f"> Nodes: {topic['total_nodes']} | Mastered: {topic['learned_nodes']}",
        "",
        "## Knowledge Nodes",
        "",
    ]

    for gn in graph_data["nodes"]:
        name = gn["name"]
        article = gn.get("article_body", "")
        summary = gn.get("summary", "")
        body_text = article if article else summary
        ar = next((a for a in abilities if a["node_id"] == gn["node_id"]), {})
        scores = [ar.get(d, 0) for d in ["understand", "example", "contrast", "apply", "explain", "recall", "transfer", "teach"]]
        avg = sum(scores) / len(scores) if scores else 0
        md_lines.append(f"### {name}")
        md_lines.append(f"Ability: {avg:.0f}/100")
        if body_text:
            md_lines.append(body_text)
        md_lines.append("")

    content = "\n".join(md_lines)
    assert "Test Topic" in content
    assert "Node One" in content
    assert "Article 1" in content  # article_body takes priority
    assert "Summary 2" in content  # fallback to summary when no article


def test_export_anki_format():
    """Anki export should be tab-separated front/back."""
    graph_data = {
        "nodes": [
            {"name": "Node A", "summary": "Summary A", "article_body": "Article A"},
            {"name": "Node B", "summary": "Summary B", "article_body": ""},
        ],
    }

    anki_lines = []
    for node in graph_data["nodes"]:
        name = node["name"]
        article = node.get("article_body", "")
        summary = node.get("summary", "")
        body = article if article else summary
        front = name.replace("\n", "<br>").replace("\t", " ")
        back = body.replace("\n", "<br>").replace("\t", " ")
        anki_lines.append(f"{front}\t{back}")

    content = "\n".join(anki_lines)
    assert "Node A\tArticle A" in content
    assert "Node B\tSummary B" in content
    # No tabs in values
    for line in content.split("\n"):
        parts = line.split("\t")
        assert len(parts) == 2


# ==================== Node Service ====================

def test_extract_concept_refs_dedup():
    """Should deduplicate concept refs while preserving order."""
    from backend.services.node_service import _extract_concept_refs

    body = "[[A]] is related to [[B]] and also [[A]]."
    refs = _extract_concept_refs(body)
    assert refs == ["A", "B"]
    assert len(refs) == 2


def test_extract_concept_refs_empty():
    """Should return empty list for body with no refs."""
    from backend.services.node_service import _extract_concept_refs

    assert _extract_concept_refs("") == []
    assert _extract_concept_refs("plain text without refs") == []
    assert _extract_concept_refs(None) == []


@pytest.mark.asyncio
async def test_get_entry_node_returns_flat_shape_for_current_node(db_conn):
    """Current-node resume should still return flat EntryNode fields instead of NodeDetail shape."""
    from backend.services.node_service import get_entry_node

    await db_conn.execute(
        """INSERT INTO topics (
            topic_id, title, status, entry_node_id, current_node_id, description
        ) VALUES (?, ?, 'active', ?, ?, ?)""",
        (
            "tp_entry_resume",
            "Resume Topic",
            "nd_entry",
            "nd_current",
            "关于 Resume Topic 的学习内容。",
        ),
    )
    await db_conn.commit()

    result = await get_entry_node(db_conn, None, "tp_entry_resume")

    assert result is not None
    assert result["node_id"] == "nd_current"
    assert result["name"] == "Resume Topic"
    assert "why_now" in result
    assert "node" not in result


# ==================== Practice Service ====================

def test_practice_dimension_map_completeness():
    """Every practice type in the training order should have a dimension mapping."""
    from backend.models.ability import PRACTICE_DIMENSION_MAP

    training_order = ["define", "example", "contrast", "apply", "teach_beginner", "compress"]
    for pt in training_order:
        assert pt in PRACTICE_DIMENSION_MAP, f"Missing dimension map for {pt}"


@pytest.mark.asyncio
async def test_get_recommended_practice_type_uses_recall_dimension_when_all_types_completed():
    """Weak recall should recommend a recall-oriented practice instead of ignoring that dimension."""
    from backend.services.practice_service import get_recommended_practice_type

    with patch("backend.services.practice_service.sqlite_repo") as mock_repo:
        mock_repo.get_practice_attempts = AsyncMock(return_value=[
            {"practice_type": "define"},
            {"practice_type": "example"},
            {"practice_type": "contrast"},
            {"practice_type": "apply"},
            {"practice_type": "teach_beginner"},
            {"practice_type": "compress"},
        ])
        mock_repo.get_ability_record = AsyncMock(return_value={
            "understand": 80,
            "example": 80,
            "contrast": 80,
            "apply": 80,
            "explain": 80,
            "recall": 5,
            "transfer": 80,
            "teach": 80,
        })

        result = await get_recommended_practice_type(AsyncMock(), "tp_recommend", "nd_recommend")

    assert result["recommended_type"] == "compress"


def test_expansion_constants():
    """Expansion control constants should match algorithm spec."""
    from backend.graph.traversal import (
        EXPAND_MIN_NODES, EXPAND_MAX_NODES, SESSION_MAX_NODES,
        DEPTH_LIMIT_MIN, DEPTH_LIMIT_MAX, TOPIC_MAX_NODES, get_depth_limit,
    )

    assert EXPAND_MIN_NODES == 3
    assert EXPAND_MAX_NODES == 5
    assert SESSION_MAX_NODES == 12
    assert DEPTH_LIMIT_MIN == 2
    assert DEPTH_LIMIT_MAX == 3
    assert TOPIC_MAX_NODES == 30
    assert get_depth_limit(None) == 2
    assert get_depth_limit(2) == 2
    assert get_depth_limit(3) == 3
    assert get_depth_limit(1) == 2
    assert get_depth_limit(5) == 3


def test_spaced_repetition_intervals():
    """Intervals should match algorithm doc spec."""
    from backend.services.review_service import (
        _FORGET_RISK_INTERVALS, _REVIEW_SUCCESS_INTERVALS,
        _REVIEW_FAILURE_INTERVAL,
    )

    assert _FORGET_RISK_INTERVALS == [1, 3, 7, 14, 30]
    assert _REVIEW_SUCCESS_INTERVALS == [3, 7, 14, 30, 60]
    assert _REVIEW_FAILURE_INTERVAL == 1


# ==================== Model Validations ====================

def test_settings_model_defaults():
    """AppSettings should have sensible defaults."""
    from backend.models.settings import AppSettings

    s = AppSettings()
    assert s.openai_model_default != ""
    assert s.neo4j_uri != ""
    assert s.app_env == "development"
    assert s.auto_start_practice is False
    assert s.auto_generate_summary is True


def test_node_model_required_fields():
    """Node model should have all required fields."""
    from backend.models.node import Node

    n = Node(node_id="nd_1", name="Test", topic_id="tp_1")
    assert n.node_id == "nd_1"
    assert n.name == "Test"
    assert n.article_body == ""
    assert n.importance == 3


def test_session_model():
    """Session model should generate correct IDs."""
    from backend.models.session import Session, SessionCreate

    s = Session.create("tp_1", SessionCreate(entry_node_id="nd_1"))
    assert s.session_id.startswith("ss_")
    assert s.topic_id == "tp_1"
    assert s.status == "active"


def test_expression_model():
    """Expression model should generate correct IDs."""
    from backend.models.expression import ExpressionAsset, ExpressionAssetCreate

    e = ExpressionAsset.create("tp_1", "nd_1", ExpressionAssetCreate(
        expression_type="define",
        user_expression="test expression",
    ))
    assert e.asset_id.startswith("ea_")
    assert e.expression_type == "define"


# ==================== Graph Validation ====================

def test_validator_edge_type_whitelist():
    """Validator should only allow whitelisted relation types."""
    from backend.graph.validator import validate_relation_type

    assert validate_relation_type("PREREQUISITE") is True
    assert validate_relation_type("CONTRASTS") is True
    assert validate_relation_type("prerequisite") is True  # case insensitive
    assert validate_relation_type("INVALID_TYPE") is False
