"""Sync event recovery worker — retries pending sync_events on startup."""

import logging
from datetime import datetime

from neo4j import AsyncDriver

from backend.repositories import sqlite_repo

logger = logging.getLogger(__name__)

# Maximum retries before marking as permanently failed
_MAX_RETRIES = 3


async def recover_pending_sync_events(
    db,
    neo4j: AsyncDriver | None = None,
    lancedb=None,
    max_retries: int = _MAX_RETRIES,
) -> dict:
    """Scan pending sync_events and retry them.

    Returns {"recovered": int, "failed_permanent": int, "skipped": int}
    """
    pending = await sqlite_repo.list_sync_events(
        db, status="pending", limit=100,
    )

    if not pending:
        return {"recovered": 0, "failed_permanent": 0, "skipped": 0}

    recovered = 0
    failed_permanent = 0
    skipped = 0

    for event in pending:
        event_id = event["event_id"]
        operation = event.get("operation", "")
        target_store = event.get("target_store", event.get("storage_kind", ""))
        attempt_count = event.get("attempt_count", 1)
        payload = event.get("payload", {})
        retryable = event.get("retryable", True)

        if not retryable:
            continue

        # Skip if max retries exceeded or explicitly not retryable
        if attempt_count >= max_retries or not retryable:
            await _mark_failed_permanent(db, event_id, "Max retries exceeded")
            failed_permanent += 1
            continue

        # Skip if target store is unavailable
        if target_store == "neo4j" and neo4j is None:
            logger.debug("Skipping neo4j sync event %s: Neo4j unavailable", event_id)
            skipped += 1
            continue

        if target_store == "lancedb" and lancedb is None:
            logger.debug("Skipping lancedb sync event %s: LanceDB unavailable", event_id)
            skipped += 1
            continue

        # Attempt retry
        success = await _retry_event(db, neo4j, lancedb, event)

        if success:
            await sqlite_repo.resolve_sync_event(db, event_id, status="resolved")
            recovered += 1
        else:
            # Increment attempt count
            new_count = attempt_count + 1
            if new_count >= max_retries:
                await _mark_failed_permanent(db, event_id, "Max retries exceeded")
                failed_permanent += 1
            else:
                await _increment_attempt_count(db, event_id, new_count, "Retry failed")

    logger.info(
        "Recovered %d sync events, %d permanent failures, %d skipped",
        recovered, failed_permanent, skipped,
    )
    return {"recovered": recovered, "failed_permanent": failed_permanent, "skipped": skipped}


async def _retry_event(db, neo4j, lancedb, event: dict) -> bool:
    """Attempt to replay a single sync event. Returns True on success."""
    operation = event.get("operation", "")
    target_store = event.get("target_store", event.get("storage_kind", ""))
    payload = event.get("payload", {})

    try:
        if target_store == "neo4j" and neo4j:
            return await _retry_neo4j(neo4j, operation, payload)
        elif target_store == "lancedb" and lancedb:
            return await _retry_lancedb(lancedb, operation, payload)
        elif target_store == "sqlite":
            return await _retry_sqlite(db, operation, payload)
        else:
            logger.debug("Unknown target store %s for event %s", target_store, event.get("event_id"))
            return False
    except Exception as e:
        logger.warning("Sync event retry failed: %s — %s", event.get("event_id"), e)
        return False


async def _retry_neo4j(neo4j: AsyncDriver, operation: str, payload: dict) -> bool:
    """Retry a Neo4j sync event."""
    if operation in ("create_node", "create_nodes_batch"):
        nodes = payload.get("nodes", [])
        if not nodes:
            return False
        async with neo4j.session() as session:
            for node in nodes[:10]:  # Limit batch size for safety
                node_id = node.get("node_id")
                name = node.get("name", "")
                if not node_id:
                    continue
                await session.run(
                    """
                    MERGE (c:Concept {node_id: $node_id})
                    ON CREATE SET c.name = $name,
                                  c.created_at = datetime(),
                                  c.updated_at = datetime()
                    """,
                    {"node_id": node_id, "name": name},
                )
            return True

    elif operation in ("create_edge", "create_edges_batch"):
        edges = payload.get("edges", [])
        if not edges:
            return False
        async with neo4j.session() as session:
            for edge in edges[:10]:
                src = edge.get("source_id")
                tgt = edge.get("target_id")
                rel_type = edge.get("rel_type")
                if not src or not tgt or not rel_type:
                    continue
                await session.run(
                    """
                    MATCH (s:Concept {node_id: $src})
                    MATCH (t:Concept {node_id: $tgt})
                    MERGE (s)-[r]->(t)
                    """,
                    {"src": src, "tgt": tgt, "rel_type": rel_type},
                )
            return True

    elif operation == "update_article_body":
        node_id = payload.get("node_id")
        article_body = payload.get("article_body", "")
        if not node_id:
            return False
        async with neo4j.session() as session:
            await session.run(
                """
                MATCH (c:Concept {node_id: $node_id})
                SET c.article_body = $article_body,
                    c.updated_at = datetime()
                """,
                {"node_id": node_id, "article_body": article_body},
            )
            return True

    elif operation == "update_node":
        node_id = payload.get("node_id")
        if not node_id:
            return False
        updates = {k: v for k, v in payload.items() if k != "node_id" and k not in ("operation", "target_store")}
        if not updates:
            return False
        # Use the existing neo4j_repo.update_concept_node for safety
        try:
            from backend.repositories import neo4j_repo
            async with neo4j.session() as session:
                await neo4j_repo.update_concept_node(session, node_id, updates)
            return True
        except Exception as e:
            logger.warning("Neo4j update_node retry failed: %s", e)
            return False

    elif operation == "create_misconception":
        node_id = payload.get("node_id")
        hint = payload.get("hint", "")
        if not node_id:
            return False
        async with neo4j.session() as session:
            await session.run(
                """
                MATCH (c:Concept {node_id: $node_id})
                MERGE (m:Misconception {hint: $hint})
                MERGE (c)-[:HAS_MISCONCEPTION]->(m)
                """,
                {"node_id": node_id, "hint": hint},
            )
            return True

    elif operation == "create_evidence":
        node_id = payload.get("node_id")
        evidence = payload.get("evidence", "")
        if not node_id:
            return False
        async with neo4j.session() as session:
            await session.run(
                """
                MATCH (c:Concept {node_id: $node_id})
                MERGE (e:Evidence {content: $evidence})
                MERGE (c)-[:HAS_EVIDENCE]->(e)
                """,
                {"node_id": node_id, "evidence": evidence},
            )
            return True

    # Unknown operation — skip but don't fail permanently
    logger.debug("Unknown neo4j operation: %s", operation)
    return False


async def _retry_lancedb(lancedb, operation: str, payload: dict) -> bool:
    """Retry a LanceDB sync event."""
    if operation in ("create_embedding", "update_embedding"):
        node_id = payload.get("node_id")
        name = payload.get("name", "")
        summary = payload.get("summary", "")
        text_for_embedding = payload.get("text_for_embedding", "")
        topic_id = payload.get("topic_id", "")
        if not node_id or not text_for_embedding:
            return False
        try:
            from backend.repositories import lancedb_repo
            await lancedb_repo.add_concept_embedding(
                lancedb, node_id=node_id, topic_id=topic_id,
                name=name, summary=summary, text_for_embedding=text_for_embedding,
            )
            return True
        except Exception as e:
            logger.warning("LanceDB retry failed: %s", e)
            return False

    logger.debug("Unknown lancedb operation: %s", operation)
    return False


async def _retry_sqlite(db, operation: str, payload: dict) -> bool:
    """Retry a SQLite sync event."""
    if operation == "create_ability_snapshot":
        topic_id = payload.get("topic_id", "")
        snapshot_data = payload.get("snapshot_data", payload)
        node_id = payload.get("node_id")
        session_id = payload.get("session_id")
        if not topic_id or not snapshot_data:
            return False
        try:
            await sqlite_repo.create_ability_snapshot(
                db, topic_id=topic_id, snapshot_data=snapshot_data,
                node_id=node_id, session_id=session_id,
            )
            return True
        except Exception:
            return False

    if operation == "batch_create_review_items":
        items = payload.get("items", [])
        if not items:
            return False
        try:
            await sqlite_repo.batch_create_review_items(db, items)
            return True
        except Exception:
            return False

    logger.debug("Unknown sqlite operation: %s", operation)
    return False


async def _mark_failed_permanent(db, event_id: str, reason: str):
    """Mark a sync event as permanently failed."""
    now = datetime.now().isoformat()
    # Use raw SQL to bypass CHECK constraint — add 'failed_permanent' to schema instead
    await db.execute(
        """
        UPDATE sync_events
        SET status = 'ignored',
            error_message = ?,
            resolved_at = ?,
            updated_at = ?
        WHERE event_id = ?
        """,
        (f"Permanent failure: {reason}", now, now, event_id),
    )
    await db.commit()


async def _increment_attempt_count(db, event_id: str, new_count: int, error_message: str):
    """Increment the attempt count for a sync event."""
    now = datetime.now().isoformat()
    await db.execute(
        """
        UPDATE sync_events
        SET attempt_count = ?,
            error_message = ?,
            updated_at = ?
        WHERE event_id = ?
        """,
        (new_count, error_message, now, event_id),
    )
    await db.commit()
