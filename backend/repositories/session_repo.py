"""Session repository - sessions and session_nodes table CRUD."""

import json
import logging
from datetime import datetime

import aiosqlite

logger = logging.getLogger(__name__)


def _row_to_dict(row: aiosqlite.Row) -> dict:
    return dict(row)


async def create_session(db: aiosqlite.Connection, session: dict) -> dict:
    await db.execute(
        """INSERT INTO sessions (session_id, topic_id, status, started_at, entry_node_id)
           VALUES (?, ?, ?, ?, ?)""",
        (
            session["session_id"],
            session["topic_id"],
            session.get("status", "active"),
            session.get("started_at", datetime.now().isoformat()),
            session.get("entry_node_id"),
        ),
    )
    await db.commit()
    # Import increment_topic_stats from sqlite_repo to avoid circular dependency
    from backend.repositories.sqlite_repo import increment_topic_stats
    await increment_topic_stats(db, session["topic_id"], "total_sessions")
    return await get_session(db, session["session_id"])


async def get_session(db: aiosqlite.Connection, session_id: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def get_active_session(db: aiosqlite.Connection, topic_id: str) -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM sessions WHERE topic_id = ? AND status = 'active' ORDER BY started_at DESC LIMIT 1",
        (topic_id,),
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def complete_session(db: aiosqlite.Connection, session_id: str, summary: str | None = None) -> dict | None:
    now = datetime.now().isoformat()
    cursor = await db.execute(
        "UPDATE sessions SET status = 'completed', completed_at = ?, end_time = ?, summary = ?, updated_at = ? WHERE session_id = ? AND status = 'active'",
        (now, now, summary, now, session_id),
    )
    await db.commit()
    if cursor.rowcount == 0:
        return await get_session(db, session_id)
    return await get_session(db, session_id)


async def claim_session_completion(db: aiosqlite.Connection, session_id: str) -> bool:
    """Atomically claim completion rights for an active session."""
    now = datetime.now().isoformat()
    cursor = await db.execute(
        """
        UPDATE sessions
        SET status = 'completed',
            completed_at = COALESCE(completed_at, ?),
            end_time = COALESCE(end_time, ?),
            updated_at = ?
        WHERE session_id = ? AND status = 'active'
        """,
        (now, now, now, session_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def update_session_summary(db: aiosqlite.Connection, session_id: str, summary: str | None) -> None:
    await db.execute(
        "UPDATE sessions SET summary = ?, updated_at = ? WHERE session_id = ?",
        (summary, datetime.now().isoformat(), session_id),
    )
    await db.commit()


async def complete_session_synthesis(db: aiosqlite.Connection, session_id: str, synthesis_json: str) -> None:
    """Persist synthesis JSON data to a completed session for refresh recovery."""
    await db.execute(
        "UPDATE sessions SET synthesis_json = ?, updated_at = ? WHERE session_id = ?",
        (synthesis_json, datetime.now().isoformat(), session_id),
    )
    await db.commit()


async def add_session_visit(db: aiosqlite.Connection, session_id: str, node_id: str, action_type: str = "open_node"):
    try:
        await db.execute(
            """
            UPDATE session_nodes
            SET left_at = ?
            WHERE id = (
                SELECT id
                FROM session_nodes
                WHERE session_id = ? AND left_at IS NULL
                ORDER BY entered_at DESC
                LIMIT 1
            )
            """,
            (datetime.now().isoformat(), session_id),
        )
    except Exception as e:
        logger.warning("Failed to close previous session visit: %s", e)

    cursor = await db.execute(
        "SELECT COUNT(*) FROM session_nodes WHERE session_id = ?", (session_id,)
    )
    row = await cursor.fetchone()
    visit_order = row[0] if row else 0
    now = datetime.now().isoformat()

    await db.execute(
        """INSERT INTO session_nodes (session_id, node_id, visited_at, visit_order, entered_at, action_type)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, node_id, now, visit_order, now, action_type),
    )
    cursor = await db.execute("SELECT visited_node_ids FROM sessions WHERE session_id = ?", (session_id,))
    row = await cursor.fetchone()
    if row:
        visited = json.loads(row[0])
        if node_id not in visited:
            visited.append(node_id)
            await db.execute(
                "UPDATE sessions SET visited_node_ids = ?, updated_at = ? WHERE session_id = ?",
                (json.dumps(visited), datetime.now().isoformat(), session_id),
            )
    await db.commit()


async def increment_session_practice_count(db: aiosqlite.Connection, session_id: str):
    await db.execute(
        "UPDATE sessions SET practice_count = practice_count + 1, updated_at = ? WHERE session_id = ?",
        (datetime.now().isoformat(), session_id),
    )
    await db.commit()


async def update_session_node_left_at(db: aiosqlite.Connection, session_id: str, node_id: str | None = None):
    """Update left_at for the most recent open visit in a session."""
    now = datetime.now().isoformat()
    if node_id:
        await db.execute(
            """
            UPDATE session_nodes
            SET left_at = ?
            WHERE id = (
                SELECT id
                FROM session_nodes
                WHERE session_id = ? AND node_id = ? AND left_at IS NULL
                ORDER BY entered_at DESC
                LIMIT 1
            )
            """,
            (now, session_id, node_id),
        )
    else:
        await db.execute(
            """
            UPDATE session_nodes
            SET left_at = ?
            WHERE id = (
                SELECT id
                FROM session_nodes
                WHERE session_id = ? AND left_at IS NULL
                ORDER BY entered_at DESC
                LIMIT 1
            )
            """,
            (now, session_id),
        )
    await db.commit()


async def list_sessions(db: aiosqlite.Connection, topic_id: str | None = None, limit: int = 20) -> list[dict]:
    if topic_id:
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE topic_id = ? ORDER BY started_at DESC LIMIT ?",
            (topic_id, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
    return [_row_to_dict(row) for row in await cursor.fetchall()]
