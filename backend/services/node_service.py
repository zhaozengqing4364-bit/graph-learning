"""Node service - node detail aggregation and expansion."""

import logging
import re

logger = logging.getLogger(__name__)

import aiosqlite
from neo4j import AsyncDriver

from backend.models.node import Node, NodeDetail, NodeNeighbor
from backend.repositories import sqlite_repo
from backend.repositories import neo4j_repo as graph


_CONCEPT_REF_RE = re.compile(r'\[\[(.+?)\]\]')


def _extract_concept_refs(article_body: str) -> list[str]:
    """Extract [[concept_name]] references from article body."""
    if not article_body:
        return []
    return list(dict.fromkeys(_CONCEPT_REF_RE.findall(article_body)))


def _entry_node_payload_from_detail(detail: dict, why_now: str) -> dict:
    node = detail.get("node") or {}
    return {
        "node_id": node.get("node_id", ""),
        "name": node.get("name", ""),
        "summary": node.get("summary", ""),
        "importance": node.get("importance", 3),
        "ability": detail.get("ability"),
        "why_now": why_now,
    }


async def get_entry_node(db: aiosqlite.Connection, neo4j: AsyncDriver, topic_id: str) -> dict | None:
    """Get the recommended entry node for a topic."""
    topic = await sqlite_repo.get_topic(db, topic_id)
    if not topic:
        return None

    # If topic has a current_node_id, return that
    if topic.get("current_node_id"):
        detail = await get_node_detail(db, neo4j, topic_id, topic["current_node_id"])
        if detail:
            node_name = (detail.get("node") or {}).get("name", "")
            return _entry_node_payload_from_detail(detail, f"继续上次学习：{node_name}")
        return None

    # Otherwise find the entry_node_id from topic
    entry_node_id = topic.get("entry_node_id")
    learning_intent = topic.get("learning_intent", "build_system")

    def _ability_avg(ability_by_node: dict, node_id: str) -> float | None:
        """Compute average of understand/explain/apply from pre-fetched ability map."""
        ability = ability_by_node.get(node_id)
        if not ability:
            return None
        return sum(ability.get(d, 0) for d in ["understand", "explain", "apply"]) / 3

    # Batch-fetch all ability records for this topic (1 query instead of up to 8 per-node queries)
    all_abilities = await sqlite_repo.list_ability_records(db, topic_id)
    ability_by_node = {r.get("node_id", ""): r for r in all_abilities}

    # For solve_task: try to find shortest path of low-ability nodes
    if learning_intent == "solve_task" and neo4j:
        try:
            async with neo4j.session() as session:
                mainline = await graph.get_mainline_path(session, topic_id)
                best_node = None
                best_avg = 999
                for n in mainline[:5]:
                    avg = _ability_avg(ability_by_node, n.get("node_id", ""))
                    if avg is not None and avg < best_avg:
                        best_avg = avg
                        best_node = n
                if best_node:
                    entry_node_id = best_node.get("node_id", "")
        except Exception as e:
            logger.warning(f"Failed to find best entry node for solve_task: {e}")

    # For build_system: prioritize unseen nodes with lowest ability on mainline
    elif learning_intent == "build_system" and neo4j:
        try:
            async with neo4j.session() as session:
                mainline = await graph.get_mainline_path(session, topic_id)
                best_node = None
                best_avg = 999
                for n in mainline[:8]:
                    nid = n.get("node_id", "")
                    status = n.get("status", "unseen")
                    if status != "unseen":
                        continue
                    avg = _ability_avg(ability_by_node, nid)
                    if avg is not None:
                        if avg < best_avg:
                            best_avg = avg
                            best_node = n
                    else:
                        best_node = n
                        break
                if best_node:
                    entry_node_id = best_node.get("node_id", "")
        except Exception as e:
            logger.warning(f"Failed to find best entry node for build_system: {e}")

    # For fix_gap: prioritize prerequisite nodes with lowest ability
    elif learning_intent == "fix_gap" and neo4j:
        try:
            async with neo4j.session() as session:
                mainline = await graph.get_mainline_path(session, topic_id)
                # Batch-check which nodes have PREREQUISITE edges (1 query instead of up to 8)
                node_ids = [n.get("node_id", "") for n in mainline[:8]]
                prereq_nodes: set[str] = set()
                if node_ids:
                    prereq_result = await session.run(
                        """UNWIND $nids AS nid
                           MATCH (c:Concept {node_id: nid})-[r:PREREQUISITE]->(t:Concept)
                           WHERE t.topic_id = $topic_id
                           RETURN DISTINCT c.node_id""",
                        {"nids": node_ids, "topic_id": topic_id},
                    )
                    async for record in prereq_result:
                        prereq_nodes.add(record["c.node_id"])
                best_node = None
                best_avg = 999
                for n in mainline[:8]:
                    nid = n.get("node_id", "")
                    if nid not in prereq_nodes:
                        continue
                    avg = _ability_avg(ability_by_node, nid)
                    if avg is not None:
                        if avg < best_avg:
                            best_avg = avg
                            best_node = n
                    else:
                        best_node = n
                        break
                if best_node:
                    entry_node_id = best_node.get("node_id", "")
        except Exception as e:
            logger.warning(f"Failed to find best entry node for fix_gap: {e}")

    # For prepare_expression / prepare_interview: prioritize nodes with low explain/apply
    elif learning_intent in ("prepare_expression", "prepare_interview") and neo4j:
        try:
            async with neo4j.session() as session:
                mainline = await graph.get_mainline_path(session, topic_id)
                best_node = None
                best_expr_avg = 999
                for n in mainline[:8]:
                    nid = n.get("node_id", "")
                    ability = ability_by_node.get(nid)
                    if not ability:
                        continue
                    expr_avg = (ability.get("explain", 0) + ability.get("apply", 0)) / 2
                    if expr_avg < best_expr_avg:
                        best_expr_avg = expr_avg
                        best_node = n
                if best_node:
                    entry_node_id = best_node.get("node_id", "")
        except Exception as e:
            logger.warning(f"Failed to find best entry node for {learning_intent}: {e}")

    if entry_node_id and neo4j:
        try:
            async with neo4j.session() as session:
                node = await graph.get_concept_node(session, entry_node_id)
                if node:
                    ability = ability_by_node.get(node["node_id"])
                    # Build why_now
                    importance = node.get("importance", 3)
                    node_name = node.get("name", "")
                    if ability:
                        avg = sum(ability.get(d, 0) for d in ["understand", "explain", "apply"]) / 3
                        why_now = f"这个节点的能力得分较低（{avg:.0f}/100），建议优先巩固"
                    else:
                        why_now = f"这是主题的推荐起始节点，重要度 {importance}/5"
                    return {
                        "node_id": node["node_id"],
                        "name": node_name,
                        "summary": node.get("summary", ""),
                        "importance": importance,
                        "ability": dict(ability) if ability else None,
                        "why_now": why_now,
                    }
        except Exception as e:
            logger.warning(f"Failed to get entry node from Neo4j: {e}")

    # Fallback when Neo4j is unavailable: build entry node from topic metadata
    if entry_node_id:
        ability = ability_by_node.get(entry_node_id)
        node_name = topic.get("title", "未知节点")
        importance = 3
        if ability:
            avg = sum(ability.get(d, 0) for d in ["understand", "explain", "apply"]) / 3
            why_now = f"这个节点的能力得分较低（{avg:.0f}/100），建议优先巩固"
        else:
            why_now = f"这是主题的推荐起始节点，重要度 {importance}/5"
        return {
            "node_id": entry_node_id,
            "name": node_name,
            "summary": topic.get("description", f"关于 {node_name} 的学习内容。"),
            "importance": importance,
            "ability": dict(ability) if ability else None,
            "why_now": why_now,
        }

    return None


async def get_node_detail(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver,
    topic_id: str,
    node_id: str,
) -> dict | None:
    """Get full node detail for learning page."""
    # Get node from Neo4j
    node_data = None
    if neo4j:
        try:
            async with neo4j.session() as session:
                node_data = await graph.get_concept_node(session, node_id)
        except Exception as e:
            logger.warning(f"Failed to get concept node from Neo4j: {e}")

    if not node_data:
        # Fallback when Neo4j is unavailable: build minimal node from topic + ability data
        topic = await sqlite_repo.get_topic(db, topic_id)
        ability = await sqlite_repo.get_ability_record(db, topic_id, node_id)
        # Determine node name: use topic title if this is the entry node
        node_name = node_id
        if topic and (node_id == topic.get("entry_node_id") or node_id == topic.get("current_node_id")):
            node_name = topic.get("title", node_id)
        node_obj = {
            "node_id": node_id,
            "name": node_name,
            "summary": "",
            "importance": 3,
            "status": "current",
            "topic_id": topic_id,
        }
        return {
            "node": node_obj,
            "examples": [],
            "misconceptions": [],
            "concept_refs": [],
            "prerequisites": [],
            "contrasts": [],
            "applications": [],
            "misunderstandings": [],
            "related": [],
            "ability": dict(ability) if ability else None,
            "why_now": "",
        }

    # Get neighbors from Neo4j
    prerequisites, contrasts, applications, misunderstandings, related = [], [], [], [], []
    seen = set()  # Dedup by node_id to avoid O(n²) list scans
    dynamic_misconceptions = []  # Diagnoser-generated misconception hints from Neo4j
    if neo4j:
        try:
            async with neo4j.session() as session:
                neighbors = await graph.get_node_neighbors(session, node_id, radius=1)
                # Also fetch dynamic misconception hints (from Diagnoser)
                try:
                    dynamic_misconceptions = await graph.get_misconceptions_for_concept(session, node_id)
                except Exception as e:
                    logger.warning("Failed to fetch misconception hints for node %s: %s", node_id, e)

                for neighbor in neighbors.get("neighbors", []):
                    rel_types = neighbor.get("relation_types", [])
                    nid = neighbor.get("node_id", "")
                    if not nid or nid in seen:
                        continue
                    seen.add(nid)
                    entry = NodeNeighbor(
                        node_id=nid,
                        name=neighbor.get("name", ""),
                        summary=neighbor.get("summary", ""),
                    )
                    entry_data = entry.model_dump()
                    for rt in rel_types:
                        if rt == "PREREQUISITE":
                            prerequisites.append(entry)
                        elif rt == "CONTRASTS":
                            contrasts.append(entry)
                        elif rt == "APPLIES_IN":
                            applications.append(entry)
                        elif rt == "MISUNDERSTOOD_AS":
                            misunderstandings.append(entry)
                        else:
                            related.append(entry)
        except Exception as e:
            logger.warning(f"Failed to get node neighbors from Neo4j: {e}")

    # Get ability from SQLite
    ability = await sqlite_repo.get_ability_record(db, topic_id, node_id)

    # Build contextual why_now
    node_name = node_data.get("name", "")
    importance = node_data.get("importance", 3)
    is_mainline = node_data.get("is_mainline", False)
    why_parts = []
    if is_mainline:
        why_parts.append("这是当前主题的主干节点")
    else:
        why_parts.append("这是当前主题中的重要支线节点")
    if prerequisites:
        why_parts.append(f"是 {len(prerequisites)} 个前置概念的后继")
    if contrasts:
        why_parts.append(f"与 {len(contrasts)} 个概念形成对比关系")
    if importance >= 4:
        why_parts.append("核心重要度高")
    why_now = f"{'，'.join(why_parts)}（重要度 {importance}/5）。"

    return {
        "node": node_data,
        "examples": node_data.get("examples", []),
        "misconceptions": node_data.get("misconceptions", []),
        "dynamic_misconceptions": [
            {"description": m.get("description", ""), "correction": m.get("correction", ""), "severity": m.get("severity", 1)}
            for m in dynamic_misconceptions
        ],
        "concept_refs": _extract_concept_refs(node_data.get("article_body", "")),
        "prerequisites": [p.model_dump() for p in prerequisites],
        "contrasts": [c.model_dump() for c in contrasts],
        "applications": [a.model_dump() for a in applications],
        "misunderstandings": [m.model_dump() for m in misunderstandings],
        "related": [r.model_dump() for r in related],
        "ability": dict(ability) if ability else None,
        "why_now": why_now,
    }


async def defer_node(
    db: aiosqlite.Connection,
    topic_id: str,
    node_id: str,
    source_node_id: str | None = None,
    reason: str = "",
) -> dict:
    """Add a node to the deferred learning stack."""
    return await sqlite_repo.create_deferred_node(db, topic_id, node_id, reason, source_node_id=source_node_id)


async def update_node_status(db: aiosqlite.Connection, neo4j: AsyncDriver, topic_id: str, node_id: str, status: str) -> dict | None:
    """Update a node's status."""
    if neo4j:
        try:
            async with neo4j.session() as session:
                await graph.update_concept_node(session, node_id, {"status": status})
        except Exception as e:
            logger.warning(f"Failed to update concept node status in Neo4j: {e}")
            await sqlite_repo.record_sync_event(
                db,
                topic_id=topic_id,
                node_id=node_id,
                storage_kind="neo4j",
                operation="node.update_status",
                status="pending",
                error_message=str(e),
                payload={"status": status},
            )

    if status == "mastered":
        # Idempotent guard: only increment learned_nodes if node was not already mastered
        was_mastered = False
        if neo4j:
            try:
                async with neo4j.session() as session:
                    existing = await graph.get_concept_node(session, node_id)
                    if existing and existing.get("status") == "mastered":
                        was_mastered = True
            except Exception as e:
                logger.warning("Failed to check mastered status before increment: %s", e)
        if not was_mastered:
            await sqlite_repo.increment_topic_stats(db, topic_id, "learned_nodes")
    return {"node_id": node_id, "status": status}


async def get_sqlite_graph_fallback(db: aiosqlite.Connection, topic_id: str) -> dict:
    """Build minimal graph from SQLite when Neo4j is unavailable."""
    topic = await sqlite_repo.get_topic(db, topic_id)
    records = await sqlite_repo.list_ability_records(db, topic_id)

    nodes = []
    if topic and topic.get("entry_node_id"):
        entry_id = topic["entry_node_id"]
        nodes.append({
            "node_id": entry_id,
            "name": topic.get("title", "未知节点"),
            "summary": "",
            "importance": 3,
            "topic_id": topic_id,
            "status": "current",
        })

    seen_ids = {n["node_id"] for n in nodes}
    for r in records:
        if r["node_id"] not in seen_ids:
            seen_ids.add(r["node_id"])
            nodes.append({
                "node_id": r["node_id"],
                "name": r["node_id"],
                "summary": "",
                "importance": 3,
                "topic_id": topic_id,
                "status": "unseen",
            })

    return {"nodes": nodes, "edges": []}


async def list_deferred_nodes(db: aiosqlite.Connection, topic_id: str) -> list[dict]:
    """List deferred nodes for a topic."""
    return await sqlite_repo.list_deferred_nodes(db, topic_id)


async def resolve_deferred_node(db: aiosqlite.Connection, topic_id: str, node_id: str) -> bool:
    """Mark a deferred node as resolved."""
    return await sqlite_repo.resolve_deferred_node(db, topic_id, node_id)
