"""Topic service - orchestration for topic operations."""

import json
import logging
from datetime import datetime

import aiosqlite

logger = logging.getLogger(__name__)
from neo4j import AsyncDriver
from backend.repositories.neo4j_repo import ALLOWED_RELATIONSHIP_TYPES

from backend.models.topic import Topic, TopicCreate, TopicUpdate
from backend.models.common import generate_id
from backend.repositories import sqlite_repo
from backend.repositories import neo4j_repo as graph
from backend.agents import explorer as explorer_agent
from backend.agents.base import validate_ai_output
from backend.graph.validator import validate_and_filter_nodes, validate_and_filter_edges


async def create_topic(db: aiosqlite.Connection, neo4j: AsyncDriver, data: TopicCreate, lancedb=None) -> dict:
    """Create a new topic: SQLite first, call Explorer AI, then write to Neo4j + LanceDB."""
    topic = Topic.create(data)

    # 0. Check for duplicate topic via vector similarity
    if lancedb and data.source_content:
        try:
            from backend.repositories import lancedb_repo
            similar = await lancedb_repo.search_similar_topics(lancedb, data.source_content, limit=3)
            for s in similar:
                if lancedb_repo.is_duplicate(s.get("similarity", 0)):
                    existing = await sqlite_repo.get_topic(db, s["id"])
                    if existing:
                        existing["_duplicate_of"] = s["id"]
                        existing["_similarity"] = s["similarity"]
                        return existing
        except Exception as e:
            logger.warning(f"Topic dedup check failed: {e}")

    # 1. Write to SQLite (without entry_node_id yet)
    created = await sqlite_repo.create_topic(db, topic.model_dump())

    # 2. Call Explorer AI to generate initial node bundle
    ai_result = None
    fallback_used = False
    try:
        source = data.source_content or data.title
        if source:
            ai_result = await explorer_agent.create_topic(
                source_content=source,
                learning_intent=data.learning_intent,
            )
    except Exception as e:
        logger.warning(f"Explorer AI failed, using fallback: {e}")

    # 2b. Validate AI output schema before use
    if ai_result:
        ai_result = validate_ai_output(
            ai_result,
            required_fields=["entry_node"],
            field_types={"entry_node": dict, "nodes": list, "edges": list},
        )

    # 3. Use fallback if AI failed or returned nothing
    if ai_result is None:
        ai_result = explorer_agent.create_topic_fallback(data.title)
        fallback_used = True

    # 4. Extract entry node and write graph data
    entry_node_data = ai_result.get("entry_node", {})
    entry_node_id = None
    node_name_to_id: dict[str, str] = {}

    # Generate entry_node_id even without Neo4j so the topic is usable
    if entry_node_data.get("name"):
        entry_node_id = generate_id("nd")
        node_name_to_id[entry_node_data["name"]] = entry_node_id

    if neo4j:
        try:
            async with neo4j.session() as session:
                # Write Topic node
                await graph.create_topic_node(session, created)

                # Write entry node
                if entry_node_data.get("name"):
                    concept = {
                        "node_id": entry_node_id,
                        "name": entry_node_data["name"],
                        "summary": entry_node_data.get("summary", ""),
                        "why_it_matters": entry_node_data.get("why_it_matters", ""),
                        "importance": entry_node_data.get("importance", 3),
                        "topic_id": topic.topic_id,
                        "status": "current",
                        "applications": entry_node_data.get("applications", []),
                        "examples": entry_node_data.get("examples", []),
                        "misconceptions": entry_node_data.get("misconceptions", []),
                        "article_body": entry_node_data.get("article_body", ""),
                    }
                    await graph.create_concept_node(session, concept)
                    await graph.update_concept_node(session, entry_node_id, {"is_mainline": True})
                    await graph.link_concept_to_topic(session, topic.topic_id, entry_node_id)

                    # Write additional nodes from AI result
                    nodes = ai_result.get("nodes", [])

                    # Hard cap for shortest_path mode: max 5 total nodes
                    max_initial = 5
                    if data.mode == "shortest_path":
                        max_initial = min(max_initial, 4)  # entry + 4 max

                    # Validate nodes via graph validator (schema + dedup) before writing
                    valid_nodes = await validate_and_filter_nodes(lancedb, nodes, topic.topic_id)

                    # Extract mainline names from outline for is_mainline flag
                    outline_mainline = ai_result.get("outline", {}).get("mainline", [])
                    if entry_node_data.get("name") and entry_node_data["name"] not in outline_mainline:
                        outline_mainline.insert(0, entry_node_data["name"])

                    # Batch-create additional nodes via UNWIND (N*3 queries -> 4 queries)
                    _now = datetime.now().isoformat()
                    _batch_nodes = []
                    _mainline_node_ids = []
                    for n in valid_nodes[:max_initial]:
                        node_id = generate_id("nd")
                        node_name_to_id[n.get("name", "")] = node_id
                        is_mainline = n.get("name", "") in outline_mainline
                        _batch_nodes.append({
                            "node_id": node_id,
                            "name": n.get("name", ""),
                            "summary": n.get("summary", ""),
                            "why_it_matters": n.get("why_it_matters", ""),
                            "importance": n.get("importance", 2),
                            "topic_id": topic.topic_id,
                            "status": "unseen",
                            "applications": n.get("applications", []),
                            "examples": n.get("examples", []),
                            "misconceptions": n.get("misconceptions", []),
                            "article_body": n.get("article_body", ""),
                            "created_at": _now,
                            "updated_at": _now,
                        })
                        if is_mainline:
                            _mainline_node_ids.append(node_id)

                    if _batch_nodes:
                        await session.run(
                            """UNWIND $items AS item
                               MERGE (c:Concept {node_id: item.node_id})
                               SET c.name = item.name, c.summary = item.summary,
                                   c.why_it_matters = item.why_it_matters, c.article_body = item.article_body,
                                   c.applications = item.applications, c.examples = item.examples,
                                   c.misconceptions = item.misconceptions, c.importance = item.importance,
                                   c.status = item.status, c.confidence = 0.0,
                                   c.topic_id = item.topic_id, c.created_at = item.created_at, c.updated_at = item.updated_at""",
                            {"items": _batch_nodes},
                        )

                    # Batch-set is_mainline flag
                    if _mainline_node_ids:
                        await session.run(
                            """UNWIND $ids AS nid
                               MATCH (c:Concept {node_id: nid})
                               SET c.is_mainline = true""",
                            {"ids": _mainline_node_ids},
                        )

                    # Batch-link all nodes (entry + additional) to topic
                    _all_node_ids = [entry_node_id] + [n["node_id"] for n in _batch_nodes]
                    await session.run(
                        """UNWIND $items AS item
                           MATCH (t:Topic {topic_id: $topic_id}), (c:Concept {node_id: item.node_id})
                           MERGE (t)-[:HAS_NODE]->(c)""",
                        {"topic_id": topic.topic_id, "items": [{"node_id": nid} for nid in _all_node_ids]},
                    )

                    # Validate edges via graph validator before writing
                    all_known_names = set(node_name_to_id.keys())
                    edges = ai_result.get("edges", [])
                    valid_edges = validate_and_filter_edges(edges, all_known_names)

                    # Batch-create relationships via UNWIND
                    _batch_edges = []
                    for edge in valid_edges:
                        src_id = node_name_to_id.get(edge.get("source", ""))
                        tgt_id = node_name_to_id.get(edge.get("target", ""))
                        if src_id and tgt_id and src_id != tgt_id:
                            _batch_edges.append({
                                "src_id": src_id,
                                "tgt_id": tgt_id,
                                "rel_type": edge.get("relation_type", "PREREQUISITE"),
                                "reason": edge.get("reason", ""),
                            })
                    if _batch_edges:
                        # Group edges by rel_type for batch UNWIND (Cypher doesn't support dynamic types)
                        from collections import defaultdict
                        edges_by_type: dict[str, list[dict]] = defaultdict(list)
                        for be in _batch_edges:
                            edges_by_type[be["rel_type"]].append(be)
                        for rel_type, rel_items in edges_by_type.items():
                            if rel_type not in ALLOWED_RELATIONSHIP_TYPES:
                                logger.warning(f"Skipping invalid rel_type during topic create: {rel_type}")
                                continue
                            await session.run(
                                f"""UNWIND $items AS item
                                   MATCH (src:Concept {{node_id: item.src_id}}), (tgt:Concept {{node_id: item.tgt_id}})
                                   MERGE (src)-[r:`{rel_type}`]->(tgt)
                                   SET r.reason = item.reason""",
                                {"items": rel_items},
                            )
        except Exception as e:
            logger.warning(f"Neo4j write failed for topic: {e}")
            await sqlite_repo.record_sync_event(
                db,
                topic_id=topic.topic_id,
                storage_kind="neo4j",
                operation="topic.create",
                status="pending",
                error_message=str(e),
                payload={
                    "stage": "graph_write",
                    "entry_node_id": entry_node_id,
                    "entry_node_name": entry_node_data.get("name", ""),
                    "initial_node_names": [n.get("name", "") for n in ai_result.get("nodes", [])[:5] if n.get("name")],
                },
            )

    # 5. Write vectors to LanceDB
    if lancedb and entry_node_data.get("name"):
        try:
            from backend.repositories import lancedb_repo
            embed_parts = [entry_node_data['name'], entry_node_data.get('summary', '')]
            why = entry_node_data.get('why_it_matters', '')
            if why:
                embed_parts.append(why)
            examples = entry_node_data.get('examples', [])
            if examples:
                embed_parts.append(' '.join(examples[:2]))
            embed_text = ' '.join(embed_parts)
            await lancedb_repo.add_concept_embedding(
                lancedb, entry_node_id, topic.topic_id,
                entry_node_data["name"], entry_node_data.get("summary", ""),
                embed_text,
            )
        except Exception as e:
            logger.warning(f"LanceDB write failed for topic: {e}")
            await sqlite_repo.record_sync_event(
                db,
                topic_id=topic.topic_id,
                storage_kind="lancedb",
                operation="topic.create",
                status="pending",
                error_message=str(e),
                payload={
                    "stage": "entry_embedding",
                    "entry_node_id": entry_node_id,
                    "entry_node_name": entry_node_data.get("name", ""),
                },
            )

    # 5b. Write vectors for initial non-entry nodes
    if lancedb and entry_node_data.get("name"):
        try:
            from backend.repositories import lancedb_repo
            for n in ai_result.get("nodes", [])[:5]:
                n_name = n.get("name", "")
                n_id = node_name_to_id.get(n_name)
                if n_id:
                    n_parts = [n_name, n.get("summary", "")]
                    n_why = n.get("why_it_matters", "")
                    if n_why:
                        n_parts.append(n_why)
                    await lancedb_repo.add_concept_embedding(
                        lancedb, n_id, topic.topic_id, n_name, n.get("summary", ""), ' '.join(n_parts),
                    )
        except Exception as e:
            logger.warning(f"LanceDB write failed for initial nodes: {e}")
            await sqlite_repo.record_sync_event(
                db,
                topic_id=topic.topic_id,
                storage_kind="lancedb",
                operation="topic.create",
                status="pending",
                error_message=str(e),
                payload={
                    "stage": "initial_node_embeddings",
                    "new_node_names": [n.get("name", "") for n in ai_result.get("nodes", [])[:5] if n.get("name")],
                    "initial_node_ids": [node_name_to_id.get(n.get("name", ""), "") for n in ai_result.get("nodes", [])[:5] if n.get("name")],
                },
            )

    # 5c. Write topic embedding for dedup
    if lancedb:
        try:
            from backend.repositories import lancedb_repo
            topic_embed_text = f"{data.title} {data.source_content or ''}"
            await lancedb_repo.add_topic_embedding(
                lancedb, topic.topic_id, data.title, topic_embed_text,
            )
        except Exception as e:
            logger.warning(f"LanceDB topic embedding write failed: {e}")
            await sqlite_repo.record_sync_event(
                db,
                topic_id=topic.topic_id,
                storage_kind="lancedb",
                operation="topic.create",
                status="pending",
                error_message=str(e),
                payload={"stage": "topic_embedding", "title": data.title},
            )

    # 6. Update topic with entry_node_id and node count
    if entry_node_id:
        await sqlite_repo.update_topic(db, topic.topic_id, {
            "entry_node_id": entry_node_id,
            "total_nodes": 1 + min(len(ai_result.get("nodes", [])), 5),
        })
        created["entry_node_id"] = entry_node_id
        created["total_nodes"] = 1 + min(len(ai_result.get("nodes", [])), 5)

    if data.source_content:
        try:
            from backend.services import article_service

            await article_service.create_initial_source_article_for_topic(
                db,
                neo4j,
                topic.topic_id,
                data.title,
                data.source_content,
            )
        except Exception as e:
            logger.warning(f"Failed to create initial source article for topic: {e}")
            await sqlite_repo.record_sync_event(
                db,
                topic_id=topic.topic_id,
                storage_kind="sqlite",
                operation="topic.create_source_article",
                status="pending",
                error_message=str(e),
                payload={
                    "stage": "initial_source_article",
                    "entry_node_id": entry_node_id,
                    "entry_node_name": entry_node_data.get("name", ""),
                    "title": data.title,
                },
            )

    # Build outline mainline from AI-generated nodes
    mainline_names = []
    if entry_node_data.get("name"):
        mainline_names.append(entry_node_data["name"])
    for n in ai_result.get("nodes", [])[:5]:
        name = n.get("name", "")
        if name:
            mainline_names.append(name)
    created["_outline_mainline"] = mainline_names

    created["fallback_used"] = fallback_used
    # Store entry node info for API response
    if entry_node_data.get("name"):
        created["entry_node_name"] = entry_node_data["name"]
        created["entry_node_summary"] = entry_node_data.get("summary", "")
    return created


async def get_topic_detail(db: aiosqlite.Connection, topic_id: str) -> dict | None:
    """Get topic with computed stats."""
    topic = await sqlite_repo.get_topic(db, topic_id)
    if not topic:
        return None

    # Add review count
    review_count = await sqlite_repo.count_review_items(db, topic_id, "pending")
    topic["due_review_count"] = review_count

    # Add deferred count (O(1) COUNT instead of O(n) list)
    topic["deferred_count"] = await sqlite_repo.count_deferred_nodes(db, topic_id)

    return topic


async def list_topics(
    db: aiosqlite.Connection,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """List topics with total count and computed review/deferred counts."""
    topics = await sqlite_repo.list_topics(db, status=status, limit=limit, offset=offset)
    total = await sqlite_repo.count_topics(db, status=status)

    # Batch-fetch review counts and deferred counts for listed topics
    if topics:
        topic_ids = [t["topic_id"] for t in topics]
        review_counts = await sqlite_repo.batch_count_pending_reviews(db, topic_ids)
        deferred_counts = await sqlite_repo.batch_count_unresolved_deferred(db, topic_ids)

        for t in topics:
            t["due_review_count"] = review_counts.get(t["topic_id"], 0)
            t["deferred_count"] = deferred_counts.get(t["topic_id"], 0)

    return {"items": topics, "total": total}


async def update_topic(db: aiosqlite.Connection, topic_id: str, data: TopicUpdate) -> dict | None:
    """Update topic fields."""
    updates = data.model_dump(exclude_none=True)
    if not updates:
        return await sqlite_repo.get_topic(db, topic_id)
    return await sqlite_repo.update_topic(db, topic_id, updates)


async def archive_topic(db: aiosqlite.Connection, neo4j: AsyncDriver, topic_id: str) -> dict | None:
    """Archive a topic (soft delete)."""
    return await sqlite_repo.update_topic(db, topic_id, {"status": "archived"})


async def delete_topic(db: aiosqlite.Connection, neo4j: AsyncDriver, topic_id: str, lancedb=None) -> bool:
    """Hard delete a topic with full cascade cleanup."""
    # SQLite (cascades to all related tables)
    deleted = await sqlite_repo.delete_topic(db, topic_id)
    # Neo4j (delete Topic + all associated Concept nodes)
    if neo4j:
        try:
            async with neo4j.session() as session:
                await graph.delete_topic_node(session, topic_id)
        except Exception as e:
            logger.warning(f"Failed to delete topic from Neo4j: {e}")
            await sqlite_repo.record_sync_event(
                db,
                topic_id=topic_id,
                storage_kind="neo4j",
                operation="topic.delete",
                status="pending",
                error_message=str(e),
                payload={"stage": "graph_delete"},
            )
    # LanceDB (best effort)
    if lancedb:
        try:
            from backend.repositories import lancedb_repo
            lancedb_repo.delete_topic_vectors(lancedb, topic_id)
        except Exception as e:
            logger.warning(f"Failed to delete topic vectors from LanceDB: {e}")
            await sqlite_repo.record_sync_event(
                db,
                topic_id=topic_id,
                storage_kind="lancedb",
                operation="topic.delete",
                status="pending",
                error_message=str(e),
                payload={"stage": "vector_delete"},
            )
    return deleted


async def search_topics(db: aiosqlite.Connection, q: str, limit: int = 20) -> list[dict]:
    """Search topics by query string."""
    return await sqlite_repo.search_topics(db, q, limit=limit)


async def count_mastered_nodes(db: aiosqlite.Connection, topic_id: str) -> int:
    """Count mastered nodes for a topic."""
    if hasattr(sqlite_repo, 'count_mastered_nodes'):
        return await sqlite_repo.count_mastered_nodes(db, topic_id)
    return 0


async def get_last_session_id(db: aiosqlite.Connection, topic_id: str) -> str | None:
    """Get the most recent session ID for a topic."""
    sessions = await sqlite_repo.list_sessions(db, topic_id)
    if sessions:
        return sessions[0].get("session_id")
    return None


async def list_all_deferred_nodes(db: aiosqlite.Connection, neo4j: AsyncDriver | None, resolved: bool = False) -> list[dict]:
    """List all deferred nodes across topics, enriched with concept names."""
    result = await sqlite_repo.list_all_deferred_nodes(db, resolved=resolved)

    if neo4j and result:
        try:
            node_ids = list({d.get("node_id", "") for d in result if d.get("node_id")})
            async with neo4j.session() as session:
                node_map = await graph.batch_get_concept_names(session, node_ids)
            for d in result:
                d["node_name"] = node_map.get(d.get("node_id", ""), d.get("node_id", ""))
        except Exception as e:
            logger.warning(f"Failed to enrich deferred nodes with names: {e}")
            for d in result:
                d["node_name"] = d.get("node_id", "")

    return result


async def list_practice_attempts(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None,
    topic_id: str,
    node_id: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """List practice attempts for a topic, enriched with concept names."""
    attempts = await sqlite_repo.get_practice_attempts(db, topic_id, node_id=node_id, limit=limit)

    if neo4j and attempts:
        try:
            node_ids = list({a.get("node_id", "") for a in attempts if a.get("node_id")})
            async with neo4j.session() as session:
                node_map = await graph.batch_get_concept_names(session, node_ids)
            for a in attempts:
                a["node_name"] = node_map.get(a.get("node_id", ""), a.get("node_id", ""))
        except Exception as e:
            logger.warning(f"Failed to enrich practice attempts with node names: {e}")
            for a in attempts:
                a["node_name"] = a.get("node_id", "")

    return attempts
