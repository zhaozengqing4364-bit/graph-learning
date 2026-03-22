"""Session service - session management."""

import json
import logging
from datetime import datetime

import aiosqlite

logger = logging.getLogger(__name__)
from neo4j import AsyncDriver

from backend.models.session import Session, SessionCreate, SessionVisit
from backend.models.common import generate_id
from backend.repositories import sqlite_repo
from backend.agents import synthesizer as synthesizer_agent


async def start_session(
    db: aiosqlite.Connection,
    topic_id: str,
    data: SessionCreate,
) -> dict:
    """Start a new learning session."""
    # Check for active session
    existing = await sqlite_repo.get_active_session(db, topic_id)
    if existing:
        return {**existing, "restored": True}

    session = Session.create(topic_id, data)
    try:
        created = await sqlite_repo.create_session(db, session.model_dump())
        return {**created, "restored": False}
    except aiosqlite.IntegrityError:
        restored = await sqlite_repo.get_active_session(db, topic_id)
        if restored:
            logger.info("Recovered concurrent session creation for topic %s", topic_id)
            return {**restored, "restored": True}
        raise


async def get_session(db: aiosqlite.Connection, session_id: str) -> dict | None:
    """Get session details, including persisted synthesis if available."""
    session = await sqlite_repo.get_session(db, session_id)
    if session and session.get("synthesis_json"):
        try:
            session["synthesis"] = json.loads(session["synthesis_json"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to parse synthesis_json for session %s: %s", session_id, e)
    return session


async def record_visit(
    db: aiosqlite.Connection,
    session_id: str,
    visit: SessionVisit,
    topic_id: str | None = None,
) -> None:
    """Record a node visit in a session and update topic current_node_id."""
    session = await sqlite_repo.get_session(db, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")
    if session.get("status") != "active":
        raise ValueError(f"Session {session_id} is not active")

    await sqlite_repo.add_session_visit(db, session_id, visit.node_id, action_type=visit.action_type)
    # Update topic's current_node_id to track the last visited node
    if topic_id:
        try:
            await sqlite_repo.update_topic(db, topic_id, {"current_node_id": visit.node_id})
        except Exception as e:
            logger.warning(f"Failed to update current_node_id on visit: {e}")
    else:
        try:
            session = await sqlite_repo.get_session(db, session_id)
            if session:
                await sqlite_repo.update_topic(db, session["topic_id"], {"current_node_id": visit.node_id})
        except Exception as e:
            logger.warning(f"Failed to update current_node_id on visit: {e}")


async def complete_session(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None = None,
    lancedb=None,
    session_id: str = "",
    generate_summary: bool = False,
    generate_review_items: bool = False,
    summary_text: str | None = None,
) -> dict | None:
    """Complete a session with optional Synthesizer AI summary and review item generation."""
    session = await get_session(db, session_id)
    if not session:
        return None

    # Prevent double completion — return early if session is already completed
    if session.get("status") != "active":
        logger.info("Session %s is already '%s', skipping completion", session_id, session.get("status"))
        return session

    # NOTE: We do NOT claim completion here. Claim is deferred until after
    # synthesis and review items are generated, so that failures keep the
    # session active and retryable (GROW-H1-003).

    topic_id = session["topic_id"]
    visited_nodes = json.loads(session.get("visited_node_ids", "[]"))
    practice_count = session.get("practice_count", 0)
    topic_title = ""

    # Get topic title for synthesis
    topic = await sqlite_repo.get_topic(db, topic_id)
    if topic:
        topic_title = topic.get("title", "")
        learning_intent = topic.get("learning_intent", "build_system")
    else:
        learning_intent = "build_system"

    # Build ability summary string for synthesis
    ability_summary = ""
    records = await sqlite_repo.list_ability_records(db, topic_id)
    if records:
        parts = []
        for r in records[:5]:
            parts.append(f"{r.get('node_id', 'unknown')}: understand={r.get('understand', 0)}, explain={r.get('explain', 0)}")
        ability_summary = "; ".join(parts)

    # Query expression assets for asset_highlights aggregation
    session_assets = await sqlite_repo.list_expression_assets(
        db,
        topic_id,
        limit=10,
        session_id=session_id,
    )
    asset_highlights = []
    for a in session_assets[:5]:
        asset_highlights.append({
            "node_id": a.get("node_id", ""),
            "practice_type": a.get("expression_type", ""),
            "correctness": a.get("correctness", ""),
        })

    # Get deferred nodes
    deferred = await sqlite_repo.list_deferred_nodes(db, topic_id)
    deferred_names = [d.get("node_id", "") for d in deferred]

    # Call Synthesizer AI if summary requested
    synthesis_result = None
    if generate_summary:
        try:
            synthesis_result = await synthesizer_agent.synthesize(
                topic_title=topic_title,
                visited_nodes=visited_nodes,
                practice_count=practice_count,
                ability_summary=ability_summary,
                deferred_nodes=deferred_names,
                learning_intent=learning_intent,
            )
        except Exception as e:
            logger.warning(f"Synthesizer AI failed, using fallback: {e}")
            synthesis_result = None

    # Use fallback if AI failed
    if synthesis_result is None:
        synthesis_result = synthesizer_agent.synthesize_fallback(
            topic_title, visited_nodes, practice_count
        )

    # Supplement asset_highlights from DB if AI didn't return them
    if not synthesis_result.get("asset_highlights") and asset_highlights:
        synthesis_result["asset_highlights"] = asset_highlights
    current_asset_count = len(session_assets)
    try:
        existing_asset_count = int(synthesis_result.get("new_assets_count", 0) or 0)
    except (TypeError, ValueError):
        existing_asset_count = 0
    synthesis_result["new_assets_count"] = max(existing_asset_count, current_asset_count)

    # Build summary text
    if summary_text is None:
        summary_text = synthesis_result.get("mainline_summary", "")
        if not summary_text:
            summary_text = f"本轮学习完成，访问了 {len(visited_nodes)} 个节点，完成 {practice_count} 次练习。"
    try:
        await sqlite_repo.update_session_summary(db, session_id, summary_text)
    except Exception as e:
        logger.warning(f"Failed to persist session summary text: {e}")

    # Close any open session_nodes (set left_at)
    try:
        await sqlite_repo.update_session_node_left_at(db, session_id, "")
    except Exception as e:
        logger.warning(f"Failed to close open session_nodes on complete: {e}")

    # Update topic last_session_id
    try:
        await sqlite_repo.update_topic(db, topic_id, {"last_session_id": session_id})
    except Exception as e:
        logger.warning(f"Failed to update topic last_session_id: {e}")

    # Generate review items if requested
    created_reviews = []
    if generate_review_items:
        review_candidates = synthesis_result.get("review_candidates", [])
        name_to_id: dict[str, str] = {}
        if neo4j and review_candidates[:5]:
            try:
                from backend.repositories import neo4j_repo as graph
                # Batch-resolve all candidate names to node_ids in a single Neo4j query
                all_names = [c.get("node_name", "") for c in review_candidates[:5] if c.get("node_name")]
                name_to_id = {}
                if all_names:
                    async with neo4j.session() as sess:
                        result = await sess.run(
                            """UNWIND $names AS name
                               MATCH (c:Concept {topic_id: $topic_id, name: name})
                               RETURN c.name AS name, c.node_id AS node_id""",
                            {"topic_id": topic_id, "names": all_names},
                        )
                        async for record in result:
                            name_to_id[record["name"]] = record["node_id"]
            except Exception as e:
                logger.warning(f"Failed to batch-match review candidates to nodes: {e}")

        _session_review_items = []
        for candidate in review_candidates[:5]:
            node_id = name_to_id.get(candidate.get("node_name", ""))

            if node_id:
                _session_review_items.append({
                    "review_id": generate_id("rv"),
                    "topic_id": topic_id,
                    "node_id": node_id,
                    "priority": candidate.get("priority", 3),
                    "review_type": "spaced",
                })

        if _session_review_items:
            await sqlite_repo.batch_create_review_items(db, _session_review_items)
            created_reviews.extend(_session_review_items)

        try:
            from backend.services import review_service

            generated_queue = await review_service.generate_review_queue(db, topic_id, neo4j=neo4j)
            created_reviews.extend(generated_queue)
        except Exception as e:
            logger.warning(f"Failed to generate review queue from ability records: {e}")
            try:
                await sqlite_repo.record_sync_event(
                    db,
                    topic_id=topic_id,
                    session_id=session_id,
                    storage_kind="sqlite",
                    operation="session.generate_review_queue",
                    status="pending",
                    error_message=str(e),
                )
            except Exception as sync_err:
                logger.warning(f"Failed to record sync event for review queue: {sync_err}")

    # Build result with synthesis data
    session_data = await get_session(db, session_id)
    result = {**session_data} if session_data else {}
    result["synthesis"] = {
        "mainline_summary": synthesis_result.get("mainline_summary", ""),
        "key_takeaways": synthesis_result.get("key_takeaways", []),
        "next_recommendations": synthesis_result.get("next_recommendations", []),
        "review_items_created": len(created_reviews),
        "new_assets_count": synthesis_result.get("new_assets_count", 0),
        "covered_scope": synthesis_result.get("covered_scope", ""),
        "skippable_nodes": synthesis_result.get("skippable_nodes", []),
        "asset_highlights": synthesis_result.get("asset_highlights", []),
    }

    # Enrich review candidates with node names from Neo4j
    review_candidates = synthesis_result.get("review_candidates", [])
    if neo4j and review_candidates:
        try:
            from backend.repositories import neo4j_repo as graph
            async with neo4j.session() as sess:
                names = await graph.batch_get_concept_names(
                    sess, [c.get("node_id", "") for c in review_candidates if c.get("node_id")]
                )
            for c in review_candidates:
                if not c.get("node_name") and c.get("node_id"):
                    c["node_name"] = names.get(c["node_id"], "")
        except Exception as e:
            logger.warning(f"Failed to enrich review candidates with node names: {e}")
    if not review_candidates and created_reviews:
        review_candidates = [
            {
                "review_id": review.get("review_id"),
                "node_id": review.get("node_id"),
                "node_name": review.get("node_name") or review.get("node_id", ""),
                "reason": review.get("reason", ""),
            }
            for review in created_reviews
        ]
    result["synthesis"]["review_candidates"] = review_candidates

    # Persist synthesis data for refresh recovery
    synthesis_json = ""
    try:
        synthesis_json = json.dumps(result["synthesis"], ensure_ascii=False)
        await sqlite_repo.complete_session_synthesis(db, session_id, synthesis_json)
    except Exception as e:
        logger.warning(f"Failed to persist synthesis_json: {e}")
        try:
            await sqlite_repo.record_sync_event(
                db,
                topic_id=topic_id,
                session_id=session_id,
                storage_kind="sqlite",
                operation="session.persist_synthesis",
                status="pending",
                error_message=str(e),
                payload={"synthesis_length": len(synthesis_json)},
            )
        except Exception as sync_err:
            logger.warning(f"Failed to record sync event for synthesis: {sync_err}")

    # Now claim completion — session stays active if anything above failed
    # (GROW-H1-003: delayed claim until synthesis is complete)
    claimed = await sqlite_repo.claim_session_completion(db, session_id)
    if not claimed:
        logger.info("Session %s was completed concurrently", session_id)
        return await get_session(db, session_id)

    # Refresh session data to get the completed status and timestamps
    completed = await get_session(db, session_id)
    if completed:
        result = {**completed}

    return result
