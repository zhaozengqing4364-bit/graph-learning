"""Stats service - global and per-topic statistics aggregation."""

import aiosqlite

from backend.repositories import sqlite_repo


async def get_global_stats(db: aiosqlite.Connection) -> dict:
    """Get global learning statistics across all topics."""
    aggregates = await sqlite_repo.get_topic_stats_aggregates(db)
    active_topic_count = await sqlite_repo.count_topics(db, status="active")

    due_reviews = await sqlite_repo.count_global_pending_reviews(db)
    total_assets = await sqlite_repo.count_expression_assets(db)
    total_frictions = await sqlite_repo.count_friction_records(db)

    return {
        "topic_count": aggregates["topic_count"],
        "active_topic_count": active_topic_count,
        "total_nodes": aggregates["total_nodes"],
        "total_mastered": aggregates["learned_nodes"],
        "total_practice": aggregates["total_practice"],
        "total_sessions": aggregates["total_sessions"],
        "due_reviews": due_reviews,
        "total_expression_assets": total_assets,
        "total_frictions": total_frictions,
    }
