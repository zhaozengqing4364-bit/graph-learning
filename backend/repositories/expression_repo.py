"""Expression asset repository - expression_assets table CRUD."""

import json

import aiosqlite


def _row_to_dict(row: aiosqlite.Row) -> dict:
    return dict(row)


async def create_expression_asset(db: aiosqlite.Connection, asset: dict) -> dict:
    quality_tags = asset.get("quality_tags", [])
    if isinstance(quality_tags, list):
        quality_tags = json.dumps(quality_tags)
    await db.execute(
        """INSERT INTO expression_assets (asset_id, topic_id, node_id, expression_type,
           user_expression, ai_rewrite, expression_skeleton,
           correctness, clarity, naturalness, session_id, quality_tags, favorited)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            asset["asset_id"], asset["topic_id"], asset["node_id"],
            asset.get("expression_type", asset.get("practice_type", "")),
            asset.get("user_expression", asset.get("user_text", "")),
            asset.get("ai_rewrite", ""),
            asset.get("expression_skeleton", asset.get("skeleton", "")),
            asset.get("correctness", 0), asset.get("clarity", 0), asset.get("naturalness", 0),
            asset.get("session_id"),
            quality_tags,
            1 if asset.get("favorited") else 0,
        ),
    )
    await db.commit()
    return asset


async def get_expression_asset(db: aiosqlite.Connection, asset_id: str) -> dict | None:
    """Get a single expression asset by ID."""
    cursor = await db.execute("SELECT * FROM expression_assets WHERE asset_id = ?", (asset_id,))
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def list_expression_assets(
    db: aiosqlite.Connection,
    topic_id: str,
    node_id: str | None = None,
    expression_type: str | None = None,
    favorited: bool | None = None,
    limit: int = 20,
    session_id: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM expression_assets WHERE topic_id = ?"
    params: list = [topic_id]
    if node_id:
        query += " AND node_id = ?"
        params.append(node_id)
    if expression_type:
        query += " AND expression_type = ?"
        params.append(expression_type)
    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)
    if favorited is not None:
        query += " AND favorited = ?"
        params.append(1 if favorited else 0)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    cursor = await db.execute(query, params)
    return [_row_to_dict(row) for row in await cursor.fetchall()]


async def toggle_favorite(db: aiosqlite.Connection, asset_id: str) -> dict | None:
    """Toggle the favorited flag on an expression asset."""
    cursor = await db.execute(
        "UPDATE expression_assets SET favorited = CASE WHEN favorited = 1 THEN 0 ELSE 1 END WHERE asset_id = ?",
        (asset_id,),
    )
    await db.commit()
    return await get_expression_asset(db, asset_id)
