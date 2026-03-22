"""Ability service - ability record operations and overview."""

import logging

import aiosqlite

logger = logging.getLogger(__name__)
from neo4j import AsyncDriver

from backend.repositories import sqlite_repo
from backend.agents import diagnoser as diagnoser_agent


async def get_ability(
    db: aiosqlite.Connection,
    topic_id: str,
    node_id: str,
) -> dict | None:
    """Get ability record for a node."""
    return await sqlite_repo.get_ability_record(db, topic_id, node_id)


async def get_ability_overview(db: aiosqlite.Connection, topic_id: str) -> dict:
    """Get ability overview for a topic."""
    records = await sqlite_repo.list_ability_records(db, topic_id)

    if not records:
        return {
            "ability_averages": None,
            "total_nodes": 0,
            "weak_nodes": [],
            "strongest_nodes": [],
            "explain_gap_nodes": [],
        }

    dimensions = ["understand", "example", "contrast", "apply", "explain", "recall", "transfer", "teach"]
    averages = {}
    for dim in dimensions:
        values = [r.get(dim, 0) for r in records if r.get(dim, 0) > 0]
        averages[dim] = round(sum(values) / len(values), 1) if values else 0

    # Find weak nodes (average < 30)
    weak = []
    strongest = []
    explain_gap = []

    for r in records:
        scores = [r.get(dim, 0) for dim in dimensions]
        avg = sum(scores) / len(scores) if scores else 0
        # Skip nodes with zero practice (all dimensions are 0) — they dilute the ranking
        if avg == 0:
            continue
        entry = {"node_id": r["node_id"], "average": round(avg, 1)}
        if avg < 30:
            weak.append(entry)
        if avg >= 70:
            strongest.append(entry)
        if r.get("explain", 0) < 20 and r.get("understand", 0) > 40:
            explain_gap.append({"node_id": r["node_id"], "explain": r.get("explain", 0), "understand": r.get("understand", 0)})

    weak.sort(key=lambda x: x["average"])
    strongest.sort(key=lambda x: x["average"], reverse=True)

    # Dimension imbalance metric: std dev of dimension averages (higher = more unbalanced)
    nonzero_avgs = [v for v in averages.values() if v > 0]
    imbalance_score = 0.0
    if len(nonzero_avgs) >= 2:
        mean_avg = sum(nonzero_avgs) / len(nonzero_avgs)
        variance = sum((v - mean_avg) ** 2 for v in nonzero_avgs) / len(nonzero_avgs)
        imbalance_score = round(variance ** 0.5, 1)  # standard deviation

    return {
        "ability_averages": averages,
        "total_nodes": len(records),
        "weak_nodes": weak[:5],
        "strongest_nodes": strongest[:5],
        "explain_gap_nodes": explain_gap[:5],
        "imbalance_score": imbalance_score,
    }

    # Find nodes with ability records but no practice attempts (unpracticed but tracked)
    try:
        practiced_node_ids = set()
        all_attempts = await sqlite_repo.get_practice_attempts(db, topic_id, limit=1000)
        for a in all_attempts:
            if a.get("node_id"):
                practiced_node_ids.add(a["node_id"])
        unpracticed = [
            {"node_id": r["node_id"], "average": round(
                sum(r.get(dim, 0) for dim in dimensions) / len(dimensions), 1
            )}
            for r in records
            if r["node_id"] not in practiced_node_ids and any(r.get(dim, 0) > 0 for dim in dimensions)
        ]
    except Exception:
        unpracticed = []

    return {
        "ability_averages": averages,
        "total_nodes": len(records),
        "weak_nodes": weak[:5],
        "strongest_nodes": strongest[:5],
        "explain_gap_nodes": explain_gap[:5],
        "imbalance_score": imbalance_score,
        "unpracticed_nodes": unpracticed[:5],
    }


async def get_frictions(
    db: aiosqlite.Connection,
    topic_id: str,
    node_id: str | None = None,
    friction_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """List friction records."""
    return await sqlite_repo.list_frictions(db, topic_id, node_id, friction_type, limit)


async def diagnose(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None,
    topic_id: str,
    node_id: str,
    practice_type: str,
    prompt_text: str,
    user_answer: str,
    node_name: str = "",
    node_summary: str = "",
    ability_record: dict | None = None,
    friction_history: list[str] | None = None,
    learning_intent: str | None = None,
) -> dict:
    """Diagnose a practice answer using the Diagnoser AI agent.

    Falls back to diagnose_fallback on AI failure.
    """
    # Try to get node info from Neo4j if not provided
    if not node_name and neo4j:
        try:
            from backend.repositories import neo4j_repo as graph
            async with neo4j.session() as session:
                node = await graph.get_concept_node(session, node_id)
                if node:
                    node_name = node.get("name", "")
                    node_summary = node.get("summary", "")
        except Exception as e:
            logger.warning(f"Failed to get node info for diagnosis: {e}")

    # Resolve learning_intent from topic if not provided
    if learning_intent is None:
        try:
            topic = await sqlite_repo.get_topic(db, topic_id)
            learning_intent = topic.get("learning_intent", "build_system") if topic else "build_system"
        except Exception as e:
            logger.warning(f"Failed to resolve learning_intent from topic: {e}")
            learning_intent = "build_system"

    # Call Diagnoser AI
    result = None
    if node_name:
        try:
            result = await diagnoser_agent.diagnose(
                node_name=node_name,
                node_summary=node_summary,
                practice_type=practice_type,
                prompt_text=prompt_text,
                user_answer=user_answer,
                ability_record=ability_record,
                friction_history=friction_history,
                learning_intent=learning_intent,
            )
        except Exception as e:
            logger.warning(f"Diagnoser AI failed, using fallback: {e}")

    # Fallback
    if result is None:
        result = diagnoser_agent.diagnose_fallback()

    return result


async def get_ability_snapshots(db: aiosqlite.Connection, topic_id: str, limit: int = 50) -> list[dict]:
    """Get ability snapshots for timeline visualization."""
    return await sqlite_repo.get_ability_snapshots(db, topic_id, limit=limit)


async def diagnose_full(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None,
    topic_id: str,
    node_id: str,
    practice_type: str,
    prompt_text: str,
    user_answer: str,
    node_name: str = "",
    node_summary: str = "",
    learning_intent: str | None = None,
) -> dict:
    """Full diagnose: auto-collects ability record and friction history before delegating to diagnose()."""
    # Auto-collect ability record
    ability_record = None
    try:
        ability_record = await sqlite_repo.get_ability_record(db, topic_id, node_id)
    except Exception as e:
        logger.warning(f"Failed to get ability record for diagnosis context: {e}")

    # Auto-collect friction history
    friction_history = None
    try:
        existing_frictions = await sqlite_repo.list_frictions(db, topic_id, node_id=node_id, limit=10)
        if existing_frictions:
            friction_history = [f.get("friction_type", "") for f in existing_frictions]
    except Exception as e:
        logger.warning(f"Failed to get friction history for diagnosis context: {e}")

    return await diagnose(
        db=db,
        neo4j=neo4j,
        topic_id=topic_id,
        node_id=node_id,
        practice_type=practice_type,
        prompt_text=prompt_text,
        user_answer=user_answer,
        node_name=node_name,
        node_summary=node_summary,
        ability_record=dict(ability_record) if ability_record else None,
        friction_history=friction_history,
        learning_intent=learning_intent,
    )
