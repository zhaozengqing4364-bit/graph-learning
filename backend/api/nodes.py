"""Node API routes."""

import asyncio
import logging

from fastapi import APIRouter, Request

from backend.core.response import success_response, error_response
from backend.models.node import ExpandRequest, DeferRequest, UpdateStatusRequest
from backend.services import node_service

# expand_node uses these for sync event recording and stat tracking within complex inline logic
from backend.repositories import sqlite_repo
from backend.repositories.neo4j_repo import ALLOWED_RELATIONSHIP_TYPES

# Per-node in-flight lock for idempotent article generation
_article_gen_locks: dict[str, asyncio.Lock] = {}

logger = logging.getLogger(__name__)

router = APIRouter()


def _neo4j_session_supports_run(session: object) -> bool:
    """Test stubs sometimes only implement the repository helper surface."""
    return callable(getattr(session, "run", None))


@router.get("/topics/{topic_id}/entry-node")
async def get_entry_node(request: Request, topic_id: str):
    try:
        db = request.app.state.db
        neo4j = request.app.state.neo4j
        result = await node_service.get_entry_node(db, neo4j, topic_id)
        if not result:
            return error_response("No entry node found", error_code="ENTRY_NODE_NOT_FOUND")
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to get entry node for topic %s", topic_id)
        return error_response("获取入口节点失败", error_code="ENTRY_NODE_FAILED")


@router.get("/topics/{topic_id}/nodes/{node_id}")
async def get_node_detail(request: Request, topic_id: str, node_id: str):
    try:
        db = request.app.state.db
        neo4j = request.app.state.neo4j
        result = await node_service.get_node_detail(db, neo4j, topic_id, node_id)
        if not result:
            return error_response("Node not found", error_code="NODE_NOT_FOUND")
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to get node detail %s", node_id)
        return error_response("节点详情加载失败", error_code="NODE_DETAIL_FAILED")


@router.post("/topics/{topic_id}/nodes/{node_id}/expand")
async def expand_node(request: Request, topic_id: str, node_id: str, body: ExpandRequest):
    """Expand nodes around current node via Explorer AI, with Neo4j fallback."""
    try:
        depth_limit = body.depth_limit
        strategy = body.strategy
        session_id = body.session_id
        intent = body.intent

        db = request.app.state.db
        neo4j = request.app.state.neo4j
        lancedb = request.app.state.lancedb
        if not neo4j:
            return error_response("Graph service unavailable")

        # Check topic-level node cap (max 30 per topic, per CLAUDE.md)
        try:
            topic_row = await db.execute(
                "SELECT total_nodes FROM topics WHERE topic_id = ?", (topic_id,),
            )
            topic_data = await topic_row.fetchone()
            topic_node_count = topic_data["total_nodes"] if topic_data else 0
            if topic_node_count >= 30:
                return success_response(
                    data={"neighbors": [], "suggested_next_nodes": [], "summary_delta": ""},
                    meta={"cap_reached": True, "topic_nodes": topic_node_count, "reason": "topic_cap"},
                )
        except Exception as e:
            logger.warning(f"Failed to check topic node cap: {e}")

        # Check session-level node creation cap (max 12 per session)
        if session_id:
            try:
                cur = await db.execute(
                    "SELECT COUNT(*) as cnt FROM session_nodes WHERE session_id = ?",
                    (session_id,),
                )
                row = await cur.fetchone()
                session_node_count = row["cnt"] if row else 0
                if session_node_count >= 12:
                    return success_response(
                        data={"neighbors": [], "suggested_next_nodes": [], "summary_delta": ""},
                        meta={"cap_reached": True, "session_nodes": session_node_count},
                    )
            except Exception as e:
                logger.warning(f"Failed to check session node cap: {e}")

        from backend.repositories import neo4j_repo as graph
        from backend.agents import explorer as explorer_agent
        from backend.graph.validator import validate_and_filter_nodes, validate_and_filter_edges
        from backend.graph.traversal import filter_nodes_for_expand

        # Get current node info and existing nodes for context
        async with neo4j.session() as session:
            current_node = await graph.get_concept_node(session, node_id)
            topic_graph = await graph.get_topic_graph(session, topic_id)

        if not current_node:
            return error_response("Node not found", error_code="NODE_NOT_FOUND")

        topic = await db.execute_fetchall(
            "SELECT title, learning_intent FROM topics WHERE topic_id = ?", (topic_id,)
        )
        topic_title = topic[0]["title"] if topic else ""
        learning_intent = intent or (topic[0]["learning_intent"] if topic else "build_system")

        existing_names = [n.get("name", "") for n in topic_graph.get("nodes", [])]
        existing_nodes_str = "; ".join(existing_names)

        # Try Explorer AI first
        ai_used = False
        new_nodes, new_edges = [], []
        try:
            ai_result = await explorer_agent.expand_node(
                current_node=current_node,
                topic_title=topic_title,
                learning_intent=learning_intent,
                existing_nodes=existing_nodes_str,
                depth_limit=depth_limit,
            )
            if ai_result:
                ai_used = True
                # Validate nodes via validator (schema + dedup)
                valid_nodes = await validate_and_filter_nodes(lancedb, ai_result.get("nodes", []), topic_id)
                valid_node_names = {n["name"] for n in valid_nodes}
                # Also include existing node names for edge validation
                all_known_names = valid_node_names | set(existing_names)
                new_edges = validate_and_filter_edges(ai_result.get("edges", []), all_known_names)
                new_nodes = filter_nodes_for_expand(
                    valid_nodes,
                    max_nodes=5,
                    learning_intent=learning_intent,
                    existing_node_names=set(existing_names),
                )
        except Exception as e:
            logger.warning(f"Explorer AI expand failed, falling back to Neo4j neighbors: {e}")

        if ai_used and new_nodes:
            # Write AI-generated nodes: SQLite → Neo4j → LanceDB
            try:
                from backend.models.common import generate_id
                from backend.models.topic import Topic

                name_to_id = {}
                # Map existing node names to IDs
                for n in topic_graph.get("nodes", []):
                    name_to_id[n.get("name", "")] = n.get("node_id", "")

                # Get current node's mainline status for inheritance
                current_is_mainline = current_node.get("is_mainline", False)

                # Pre-generate node IDs for SQLite tracking
                for n in new_nodes[:5]:
                    node_id_new = generate_id("nd")
                    name_to_id[n["name"]] = node_id_new

                # 1. SQLite first: track new nodes in session_nodes
                if session_id:
                    try:
                        for n in new_nodes[:5]:
                            n_id = name_to_id.get(n["name"])
                            if n_id:
                                await db.execute(
                                    "INSERT OR IGNORE INTO session_nodes (session_id, node_id, action_type) VALUES (?, ?, 'expand')",
                                    (session_id, n_id),
                                )
                        await db.commit()
                    except Exception as e:
                        logger.warning(f"Failed to track session nodes: {e}")
                        await sqlite_repo.record_sync_event(
                            db,
                            topic_id=topic_id,
                            session_id=session_id,
                            node_id=node_id,
                            storage_kind="sqlite",
                            operation="node.expand",
                            status="pending",
                            error_message=str(e),
                            payload={
                                "stage": "session_tracking",
                                "source_node_id": node_id,
                                "new_node_names": [n.get("name", "") for n in new_nodes[:5] if n.get("name")],
                            },
                        )

                # 2. Neo4j: create concept nodes and relationships (batch)
                from datetime import datetime as _dt
                _expand_now = _dt.now().isoformat()
                async with neo4j.session() as session:
                    # Pre-compute is_mainline flags and build batch node data
                    _expand_nodes = []
                    _expand_mainline_ids = []
                    _expand_edges = []
                    for n in new_nodes[:5]:
                        node_id_new = name_to_id[n["name"]]
                        is_mainline = False
                        for edge in new_edges:
                            if edge.get("source") == current_node.get("name") and edge.get("target") == n["name"] and edge.get("relation_type") == "PREREQUISITE":
                                is_mainline = current_is_mainline
                                break
                        _expand_nodes.append({
                            "node_id": node_id_new,
                            "name": n["name"],
                            "summary": n.get("summary", ""),
                            "why_it_matters": n.get("why_it_matters", ""),
                            "importance": n.get("importance", 2),
                            "topic_id": topic_id,
                            "status": "unseen",
                            "applications": n.get("applications", []),
                            "examples": n.get("examples", []),
                            "misconceptions": n.get("misconceptions", []),
                            "article_body": n.get("article_body", ""),
                            "created_at": _expand_now,
                            "updated_at": _expand_now,
                        })
                        if is_mainline:
                            _expand_mainline_ids.append(node_id_new)

                    for edge in new_edges:
                        src_id = name_to_id.get(edge.get("source", ""))
                        tgt_id = name_to_id.get(edge.get("target", ""))
                        if src_id and tgt_id and src_id != tgt_id:
                            _expand_edges.append({
                                "src_id": src_id,
                                "tgt_id": tgt_id,
                                "rel_type": edge.get("relation_type", "PREREQUISITE"),
                                "reason": edge.get("reason", ""),
                            })

                    _neo4j_written_ids = []  # Track successfully written node IDs for rollback
                    try:
                        if _neo4j_session_supports_run(session):
                            # Batch-create nodes via UNWIND
                            if _expand_nodes:
                                await session.run(
                                    """UNWIND $items AS item
                                       MERGE (c:Concept {node_id: item.node_id})
                                       SET c.name = item.name, c.summary = item.summary,
                                           c.why_it_matters = item.why_it_matters, c.article_body = item.article_body,
                                           c.applications = item.applications, c.examples = item.examples,
                                           c.misconceptions = item.misconceptions, c.importance = item.importance,
                                           c.status = item.status, c.confidence = 0.0,
                                           c.topic_id = item.topic_id, c.created_at = item.created_at, c.updated_at = item.updated_at""",
                                    {"items": _expand_nodes},
                                )
                                _neo4j_written_ids = [n["node_id"] for n in _expand_nodes]

                            # Batch-set is_mainline
                            if _expand_mainline_ids:
                                await session.run(
                                    """UNWIND $ids AS nid
                                       MATCH (c:Concept {node_id: nid})
                                       SET c.is_mainline = true""",
                                    {"ids": _expand_mainline_ids},
                                )

                            # Batch-link all new nodes to topic
                            await session.run(
                                """UNWIND $items AS item
                                   MATCH (t:Topic {topic_id: $topic_id}), (c:Concept {node_id: item.node_id})
                                   MERGE (t)-[:HAS_NODE]->(c)""",
                                {"topic_id": topic_id, "items": [{"node_id": n["node_id"]} for n in _expand_nodes]},
                            )

                            # Batch-create relationships grouped by rel_type
                            if _expand_edges:
                                from collections import defaultdict
                                _edges_by_type: dict[str, list[dict]] = defaultdict(list)
                                for be in _expand_edges:
                                    _edges_by_type[be["rel_type"]].append(be)
                                for rel_type, rel_items in _edges_by_type.items():
                                    if rel_type not in ALLOWED_RELATIONSHIP_TYPES:
                                        logger.warning(f"Skipping invalid rel_type during expand: {rel_type}")
                                        continue
                                    await session.run(
                                        f"""UNWIND $items AS item
                                           MATCH (src:Concept {{node_id: item.src_id}}), (tgt:Concept {{node_id: item.tgt_id}})
                                           MERGE (src)-[r:`{rel_type}`]->(tgt)
                                           SET r.reason = item.reason""",
                                        {"items": rel_items},
                                    )
                        else:
                            for node_data in _expand_nodes:
                                await graph.create_concept_node(session, node_data)
                                _neo4j_written_ids.append(node_data["node_id"])
                                if node_data["node_id"] in _expand_mainline_ids:
                                    await graph.update_concept_node(session, node_data["node_id"], {"is_mainline": True})
                                await graph.link_concept_to_topic(session, topic_id, node_data["node_id"])
                            for edge_data in _expand_edges:
                                await graph.create_relationship(
                                    session,
                                    edge_data["src_id"],
                                    edge_data["tgt_id"],
                                    edge_data["rel_type"],
                                    reason=edge_data["reason"],
                                )
                    except Exception as neo4j_err:
                        # Rollback: clean up any nodes that were successfully written
                        if _neo4j_written_ids:
                            logger.warning(f"Neo4j partial write detected, rolling back {len(_neo4j_written_ids)} nodes")
                            try:
                                await session.run(
                                    """UNWIND $ids AS nid
                                       MATCH (c:Concept {node_id: nid})
                                       DETACH DELETE c""",
                                    {"ids": _neo4j_written_ids},
                                )
                            except Exception as rb_err:
                                logger.error(f"Neo4j rollback failed for {len(_neo4j_written_ids)} nodes: {rb_err}")
                        raise  # Re-raise to be caught by outer handler

                # Increment total_nodes only after successful Neo4j write (GROW-H1-005)
                await sqlite_repo.increment_topic_stats(db, topic_id, "total_nodes", len(_expand_nodes))

                # 3. LanceDB: write vectors
                if lancedb:
                    try:
                        from backend.repositories import lancedb_repo as vector
                        for n in new_nodes[:5]:
                            n_id = name_to_id.get(n["name"])
                            if n_id:
                                embed_parts = [n['name'], n.get('summary', '')]
                                n_why = n.get('why_it_matters', '')
                                if n_why:
                                    embed_parts.append(n_why)
                                embed_text = ' '.join(embed_parts)
                                await vector.add_concept_embedding(
                                    lancedb, n_id, topic_id,
                                    n["name"], n.get("summary", ""), embed_text,
                                )
                    except Exception as e:
                        logger.warning(f"LanceDB write failed during expand: {e}")
                        await sqlite_repo.record_sync_event(
                            db,
                            topic_id=topic_id,
                            session_id=session_id,
                            node_id=node_id,
                            storage_kind="lancedb",
                            operation="node.expand",
                            status="pending",
                            error_message=str(e),
                            payload={
                                "stage": "vector_write",
                                "source_node_id": node_id,
                                "new_node_names": [n.get("name", "") for n in new_nodes[:5] if n.get("name")],
                            },
                        )

            except Exception as e:
                logger.warning(f"Node write failed during expand: {e}")
                await sqlite_repo.record_sync_event(
                    db,
                    topic_id=topic_id,
                    session_id=session_id,
                    node_id=node_id,
                    storage_kind="neo4j",
                    operation="node.expand",
                    status="pending",
                    error_message=str(e),
                    payload={
                        "stage": "graph_write",
                        "source_node_id": node_id,
                        "new_node_names": [n.get("name", "") for n in new_nodes[:5] if n.get("name")],
                    },
                )

            # Get updated graph view
            async with neo4j.session() as session:
                updated = await graph.get_node_neighbors(session, node_id, radius=1)
            suggested_next = [
                {"node_id": name_to_id.get(n["name"], ""), "name": n["name"], "importance": n.get("importance", 2)}
                for n in new_nodes
            ]
            summary_delta = f"新增 {len(new_nodes)} 个节点: {', '.join(n.get('name', '') for n in new_nodes[:3])}"
            return success_response(data={**updated, "suggested_next_nodes": suggested_next, "summary_delta": summary_delta}, meta={"ai_generated": True, "new_nodes": len(new_nodes)})
        else:
            # Fallback: direct Neo4j neighbor query
            try:
                async with neo4j.session() as session:
                    neighbors = await graph.get_node_neighbors(session, node_id, radius=1)
                return success_response(data=neighbors, meta={"ai_generated": False})
            except Exception as e:
                logger.warning(f"Node expansion failed: {e}", exc_info=True)
                return error_response("Node expansion failed")
    except Exception as e:
        logger.exception("Unexpected error in expand_node for %s", node_id)
        return error_response("节点扩展失败，请稍后重试", error_code="EXPAND_FAILED")



@router.post("/topics/{topic_id}/nodes/{node_id}/defer")
async def defer_node(request: Request, topic_id: str, node_id: str, body: DeferRequest):
    try:
        db = request.app.state.db
        result = await node_service.defer_node(
            db, topic_id, node_id,
            source_node_id=body.source_node_id,
            reason=body.reason,
        )
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to defer node %s", node_id)
        return error_response("延迟节点失败，请稍后重试", error_code="NODE_DEFER_FAILED")


@router.patch("/topics/{topic_id}/nodes/{node_id}/status")
async def update_node_status(request: Request, topic_id: str, node_id: str, body: UpdateStatusRequest):
    try:
        db = request.app.state.db
        neo4j = request.app.state.neo4j
        status = body.status

        result = await node_service.update_node_status(db, neo4j, topic_id, node_id, status)
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to update status for node %s", node_id)
        return error_response("节点状态更新失败", error_code="NODE_STATUS_UPDATE_FAILED")


@router.post("/topics/{topic_id}/nodes/{node_id}/generate-article")
async def generate_article(request: Request, topic_id: str, node_id: str, force: bool = False):
    """Generate article_body for a node, or force-refresh an existing article."""
    # Acquire per-node lock for idempotent generation
    if node_id not in _article_gen_locks:
        _article_gen_locks[node_id] = asyncio.Lock()
    lock = _article_gen_locks[node_id]

    if lock.locked():
        return success_response(
            data={"article_body": "", "concept_refs": []},
            meta={"in_progress": True, "message": "文章生成中，请稍后"},
        )
    try:
        return await _do_generate_article(request, topic_id, node_id, force)
    finally:
        lock.release()


async def _do_generate_article(request: Request, topic_id: str, node_id: str, force: bool):
    """Internal implementation of article generation (called under per-node lock)."""
    db = request.app.state.db
    neo4j = request.app.state.neo4j

    if not neo4j:
        return error_response("Graph service unavailable")

    from backend.repositories import neo4j_repo as graph
    from backend.agents import article_generator

    async with neo4j.session() as session:
        node = await graph.get_concept_node(session, node_id)

    if not node:
        return error_response("Node not found", error_code="NODE_NOT_FOUND")

    if node.get("article_body") and not force:
        return success_response(data={"article_body": node["article_body"], "concept_refs": []}, meta={"cached": True})

    # Get related concepts from neighbors
    related_names = []
    try:
        async with neo4j.session() as session:
            neighbors = await graph.get_node_neighbors(session, node_id, radius=1)
            for n in neighbors.get("neighbors", []):
                name = n.get("name", "")
                if name and name != node.get("name"):
                    related_names.append(name)
    except Exception as e:
        logger.warning(f"Failed to get related node names from Neo4j: {e}")

    result = await article_generator.generate_article_for_node(
        node_name=node.get("name", ""),
        node_summary=node.get("summary", ""),
        node_examples=node.get("examples", []),
        node_misconceptions=node.get("misconceptions", []),
        node_applications=node.get("applications", []),
        related_concepts=related_names,
    )

    if not result:
        return error_response("Article generation failed")

    # Save to Neo4j
    try:
        async with neo4j.session() as session:
            await graph.update_concept_node(session, node_id, {
                "article_body": result.get("article_body", ""),
            })
    except Exception as e:
        logger.warning(f"Failed to save article_body to Neo4j: {e}")
        from backend.repositories import sqlite_repo

        await sqlite_repo.record_sync_event(
            db,
            topic_id=topic_id,
            node_id=node_id,
            storage_kind="neo4j",
            operation="node.generate_article",
            status="pending",
            error_message=str(e),
            payload={"stage": "save_article_body"},
        )

    return success_response(data=result, meta={"cached": False})


@router.get("/topics/{topic_id}/deferred")
async def list_deferred_nodes(request: Request, topic_id: str):
    """List deferred nodes for a topic."""
    try:
        db = request.app.state.db
        result = await node_service.list_deferred_nodes(db, topic_id)
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to list deferred nodes for topic %s", topic_id)
        return error_response("延迟节点列表加载失败", error_code="DEFERRED_LIST_FAILED")


@router.post("/topics/{topic_id}/nodes/{node_id}/resolve-deferred")
async def resolve_deferred(request: Request, topic_id: str, node_id: str):
    """Mark a deferred node as resolved."""
    try:
        db = request.app.state.db
        resolved = await node_service.resolve_deferred_node(db, topic_id, node_id)
        return success_response(data={"resolved": resolved})
    except Exception as e:
        logger.exception("Failed to resolve deferred node %s", node_id)
        return error_response("解决延迟节点失败", error_code="DEFERRED_RESOLVE_FAILED")
