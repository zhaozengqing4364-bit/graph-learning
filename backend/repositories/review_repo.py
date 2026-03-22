"""Review repository - review_items table CRUD."""

from datetime import datetime

import aiosqlite

_ALLOWED_REVIEW_ITEM_COLUMNS = frozenset({
    "status", "due_at", "next_review_at", "last_result",
    "completed_at", "review_type", "reason", "history_count", "priority",
})


def _row_to_dict(row: aiosqlite.Row) -> dict:
    return dict(row)


async def create_review_item(db: aiosqlite.Connection, item: dict) -> dict:
    await db.execute(
        """INSERT INTO review_items (review_id, topic_id, node_id, priority, status,
           due_at, next_review_at, review_type, last_result, reason, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            item["review_id"], item["topic_id"], item["node_id"],
            item.get("priority", 0), item.get("status", "pending"),
            item.get("due_at"), item.get("next_review_at"),
            item.get("review_type", "spaced"),
            item.get("last_result", ""),
            item.get("reason", ""),
            item.get("updated_at", datetime.now().isoformat()),
        ),
    )
    await db.commit()
    return item


async def batch_create_review_items(db: aiosqlite.Connection, items: list[dict]) -> None:
    """Batch insert review items using executemany (single commit)."""
    if not items:
        return
    _now = datetime.now().isoformat()
    rows = [
        (
            i["review_id"], i["topic_id"], i["node_id"],
            i.get("priority", 0), i.get("status", "pending"),
            i.get("due_at"), i.get("next_review_at"),
            i.get("review_type", "spaced"),
            i.get("last_result", ""),
            i.get("reason", ""),
            i.get("updated_at", _now),
        )
        for i in items
    ]
    await db.executemany(
        """INSERT INTO review_items (review_id, topic_id, node_id, priority, status,
           due_at, next_review_at, review_type, last_result, reason, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    await db.commit()


async def list_review_items(
    db: aiosqlite.Connection,
    status: str | None = None,
    topic_id: str | None = None,
    limit: int | None = 20,
    offset: int = 0,
    due_before: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM review_items WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if topic_id:
        query += " AND topic_id = ?"
        params.append(topic_id)
    if due_before:
        query += " AND due_at IS NOT NULL AND due_at <= ?"
        params.append(due_before)
    query += " ORDER BY priority DESC, due_at ASC"
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    cursor = await db.execute(query, params)
    return [_row_to_dict(row) for row in await cursor.fetchall()]


async def get_review_item(db: aiosqlite.Connection, review_id: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM review_items WHERE review_id = ?", (review_id,))
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def update_review_item(db: aiosqlite.Connection, review_id: str, updates: dict) -> dict | None:
    if updates:
        unknown = set(updates) - _ALLOWED_REVIEW_ITEM_COLUMNS
        if unknown:
            raise ValueError(f"update_review_item: disallowed columns {unknown}")
    sets = []
    params: list = []
    for key, value in updates.items():
        sets.append(f"{key} = ?")
        params.append(value)
    params.append(review_id)
    await db.execute(f"UPDATE review_items SET {', '.join(sets)} WHERE review_id = ?", params)
    await db.commit()
    return await get_review_item(db, review_id)


async def update_review_item_status(db: aiosqlite.Connection, review_id: str, status: str) -> None:
    await db.execute(
        "UPDATE review_items SET status = ?, updated_at = datetime('now') WHERE review_id = ?",
        (status, review_id),
    )
    await db.commit()


async def count_review_items(db: aiosqlite.Connection, topic_id: str, status: str = "pending", node_id: str | None = None) -> int:
    if node_id:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM review_items WHERE topic_id = ? AND node_id = ? AND status = ?",
            (topic_id, node_id, status),
        )
    else:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM review_items WHERE topic_id = ? AND status = ?",
            (topic_id, status),
        )
    row = await cursor.fetchone()
    return row[0] if row else 0
