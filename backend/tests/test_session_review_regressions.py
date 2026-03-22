import asyncio
from datetime import datetime, timedelta

import aiosqlite
import pytest

from backend.repositories.sqlite_repo import init_tables
from backend.services.node_service import get_entry_node
from backend.services.review_service import generate_review_queue
from backend.services.session_service import complete_session


async def _make_db():
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await init_tables(db)
    return db


@pytest.mark.asyncio
async def test_complete_session_closes_open_session_nodes():
    db = await _make_db()
    try:
        await db.execute(
            "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, ?)",
            ("tp_graph", "图学习", "active"),
        )
        await db.execute(
            """
            INSERT INTO sessions (
                session_id,
                topic_id,
                status,
                visited_node_ids,
                practice_count,
                started_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "ss_live",
                "tp_graph",
                "active",
                '["nd_intro"]',
                0,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ),
        )
        await db.execute(
            """
            INSERT INTO session_nodes (
                session_id,
                node_id,
                visited_at,
                visit_order,
                entered_at,
                left_at,
                action_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "ss_live",
                "nd_intro",
                datetime.now().isoformat(),
                0,
                datetime.now().isoformat(),
                None,
                "open_node",
            ),
        )
        await db.commit()

        await complete_session(
            db,
            neo4j=None,
            session_id="ss_live",
            generate_summary=False,
            generate_review_items=False,
        )

        cursor = await db.execute(
            "SELECT left_at FROM session_nodes WHERE session_id = ? AND node_id = ?",
            ("ss_live", "nd_intro"),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["left_at"] is not None
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_generate_review_queue_respects_future_next_review_time():
    db = await _make_db()
    try:
        await db.execute(
            "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, ?)",
            ("tp_graph", "图学习", "active"),
        )
        await db.execute(
            """
            INSERT INTO ability_records (
                topic_id,
                node_id,
                understand,
                example,
                contrast,
                apply,
                explain,
                recall,
                transfer,
                teach,
                recall_confidence,
                review_history_count,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "tp_graph",
                "nd_message",
                20,
                20,
                20,
                20,
                20,
                20,
                20,
                20,
                0.4,
                1,
                datetime.now().isoformat(),
            ),
        )
        await db.execute(
            """
            INSERT INTO review_items (
                review_id,
                topic_id,
                node_id,
                priority,
                status,
                due_at,
                next_review_at,
                review_type,
                last_result,
                reason,
                created_at,
                completed_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "rv_done",
                "tp_graph",
                "nd_message",
                0.8,
                "completed",
                datetime.now().isoformat(),
                (datetime.now() + timedelta(days=7)).isoformat(),
                "recall",
                "good",
                "复习通过",
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ),
        )
        await db.commit()

        created = await generate_review_queue(db, "tp_graph", neo4j=None)

        assert created == []
        cursor = await db.execute(
            "SELECT COUNT(*) AS count FROM review_items WHERE topic_id = ? AND node_id = ?",
            ("tp_graph", "nd_message"),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["count"] == 1
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_get_entry_node_returns_flat_shape_when_restoring_current_node():
    db = await _make_db()
    try:
        await db.execute(
            """
            INSERT INTO topics (
                topic_id,
                title,
                status,
                learning_intent,
                current_node_id,
                entry_node_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("tp_graph", "图学习", "active", "build_system", "nd_message", "nd_intro"),
        )
        await db.commit()

        result = await get_entry_node(db, None, "tp_graph")

        assert result == {
            "node_id": "nd_message",
            "name": "图学习",
            "summary": "",
            "importance": 3,
            "ability": None,
            "why_now": "继续上次学习：图学习",
        }
    finally:
        await db.close()
