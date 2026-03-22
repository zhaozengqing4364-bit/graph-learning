"""Neo4j repository - graph database operations."""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Allowed relationship types for graph writes
# Concept-to-concept edge types (AI-generated): used by graph validator
_CONCEPT_EDGE_TYPES = frozenset({
    "PREREQUISITE", "CONTRASTS", "VARIANT_OF", "APPLIES_IN", "EXTENDS", "MISUNDERSTOOD_AS",
})
# Structural/auxiliary edge types (system-generated, not from AI output)
_STRUCTURAL_EDGE_TYPES = frozenset({"HAS_MISCONCEPTION", "EVIDENCED_BY", "HAS_REVIEW_ANCHOR"})

# Allowed Concept node properties for SET clauses (prevent Cypher injection via dict keys)
_ALLOWED_CONCEPT_PROPERTIES = frozenset({
    "name", "summary", "why_it_matters", "article_body",
    "applications", "examples", "misconceptions",
    "importance", "status", "confidence", "is_mainline",
    "topic_id", "created_at", "updated_at",
})
ALLOWED_RELATIONSHIP_TYPES = _CONCEPT_EDGE_TYPES | _STRUCTURAL_EDGE_TYPES


async def init_constraints(session):
    """Initialize Neo4j constraints and indexes."""
    constraints = [
        "CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.topic_id IS UNIQUE",
        "CREATE CONSTRAINT concept_node_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.node_id IS UNIQUE",
        "CREATE CONSTRAINT misconception_node_id IF NOT EXISTS FOR (m:Misconception) REQUIRE m.node_id IS UNIQUE",
        "CREATE CONSTRAINT evidence_node_id IF NOT EXISTS FOR (e:Evidence) REQUIRE e.node_id IS UNIQUE",
        "CREATE CONSTRAINT review_anchor_id IF NOT EXISTS FOR (r:ReviewAnchor) REQUIRE r.review_anchor_id IS UNIQUE",
    ]
    indexes = [
        "CREATE INDEX concept_topic_id IF NOT EXISTS FOR (c:Concept) ON (c.topic_id)",
        "CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)",
        "CREATE INDEX concept_importance IF NOT EXISTS FOR (c:Concept) ON (c.importance)",
        "CREATE INDEX concept_status IF NOT EXISTS FOR (c:Concept) ON (c.status)",
        "CREATE INDEX misconception_node_id IF NOT EXISTS FOR (m:Misconception) ON (m.node_id)",
        "CREATE INDEX evidence_node_id IF NOT EXISTS FOR (e:Evidence) ON (e.node_id)",
    ]
    for stmt in constraints + indexes:
        try:
            await session.run(stmt)
        except Exception as e:
            logger.warning(f"Failed to run Neo4j init statement: {e}")


def _node_to_dict(record: dict) -> dict:
    """Convert a Neo4j node record to dict."""
    if record is None:
        return None
    node = record.get("n") or record.get("c") or record.get("t")
    if node is None:
        # Direct property access
        return dict(record)
    return dict(node)


# ==================== Topic Node ====================

async def create_topic_node(session, topic: dict) -> dict:
    await session.run(
        """MERGE (t:Topic {topic_id: $topic_id})
           SET t.title = $title, t.source_type = $source_type,
               t.learning_intent = $learning_intent, t.mode = $mode,
               t.status = $status, t.created_at = $created_at, t.updated_at = $updated_at""",
        {
            "topic_id": topic["topic_id"],
            "title": topic.get("title", ""),
            "source_type": topic.get("source_type", ""),
            "learning_intent": topic.get("learning_intent", "build_system"),
            "mode": topic.get("mode", "full_system"),
            "status": topic.get("status", "active"),
            "created_at": topic.get("created_at", datetime.now().isoformat()),
            "updated_at": topic.get("updated_at", datetime.now().isoformat()),
        },
    )


async def delete_topic_node(session, topic_id: str):
    # First delete orphan-prone Misconception and Evidence nodes linked to this topic's Concepts
    await session.run(
        """MATCH (t:Topic {topic_id: $topic_id})-[:HAS_NODE]->(c:Concept)-[:HAS_MISCONCEPTION]->(m:Misconception)
           DETACH DELETE m""",
        {"topic_id": topic_id},
    )
    await session.run(
        """MATCH (t:Topic {topic_id: $topic_id})-[:HAS_NODE]->(c:Concept)-[:EVIDENCED_BY]->(e:Evidence)
           DETACH DELETE e""",
        {"topic_id": topic_id},
    )
    # Then detach and delete all Concept nodes belonging to this topic
    await session.run(
        """MATCH (t:Topic {topic_id: $topic_id})-[:HAS_NODE]->(c:Concept)
           DETACH DELETE c""",
        {"topic_id": topic_id},
    )
    # Finally delete the Topic node itself
    await session.run(
        """MATCH (t:Topic {topic_id: $topic_id})
           DETACH DELETE t""",
        {"topic_id": topic_id},
    )


# ==================== Concept Node ====================

async def batch_get_concept_names(session, node_ids: list[str]) -> dict[str, str]:
    """Batch fetch concept names by node_ids. Returns {node_id: name}."""
    if not node_ids:
        return {}
    result = await session.run(
        """UNWIND $node_ids AS nid
           MATCH (c:Concept {node_id: nid})
           RETURN c.node_id AS node_id, c.name AS name""",
        {"node_ids": node_ids},
    )
    names = {}
    async for record in result:
        names[record["node_id"]] = record["name"]
    return names


async def create_concept_node(session, node: dict) -> dict:
    await session.run(
        """MERGE (c:Concept {node_id: $node_id})
           SET c.name = $name, c.summary = $summary, c.why_it_matters = $why_it_matters,
               c.article_body = $article_body,
               c.applications = $applications, c.examples = $examples,
               c.misconceptions = $misconceptions, c.importance = $importance,
               c.status = $status, c.confidence = $confidence,
               c.topic_id = $topic_id, c.created_at = $created_at, c.updated_at = $updated_at""",
        {
            "node_id": node["node_id"],
            "name": node.get("name", ""),
            "summary": node.get("summary", ""),
            "why_it_matters": node.get("why_it_matters", ""),
            "article_body": node.get("article_body", ""),
            "applications": node.get("applications", []),
            "examples": node.get("examples", []),
            "misconceptions": node.get("misconceptions", []),
            "importance": node.get("importance", 3),
            "status": node.get("status", "unseen"),
            "confidence": node.get("confidence", 0.0),
            "topic_id": node.get("topic_id", ""),
            "created_at": node.get("created_at", datetime.now().isoformat()),
            "updated_at": node.get("updated_at", datetime.now().isoformat()),
        },
    )


async def get_concept_node(session, node_id: str) -> dict | None:
    result = await session.run(
        "MATCH (c:Concept {node_id: $node_id}) RETURN c",
        {"node_id": node_id},
    )
    record = await result.single()
    if record:
        return dict(record["c"])
    return None


async def update_concept_node(session, node_id: str, updates: dict):
    if not updates:
        return
    unknown = set(updates) - _ALLOWED_CONCEPT_PROPERTIES
    if unknown:
        raise ValueError(f"update_concept_node: disallowed properties {unknown}")
    updates = {**updates, "updated_at": datetime.now().isoformat()}
    set_clauses = ", ".join(f"c.{k} = ${k}" for k in updates)
    await session.run(
        f"MATCH (c:Concept {{node_id: $node_id}}) SET {set_clauses}",
        {"node_id": node_id, **updates},
    )


# ==================== Relationships ====================

async def create_relationship(
    session,
    source_node_id: str,
    target_node_id: str,
    rel_type: str,
    edge_id: str = "",
    reason: str = "",
    weight: float = 1.0,
    confidence: float = 0.0,
):
    """Create a relationship between two concept nodes."""
    rel_type_upper = rel_type.upper()
    if rel_type_upper not in ALLOWED_RELATIONSHIP_TYPES:
        logger.warning("create_relationship: rejected unknown rel_type '%s'", rel_type)
        return

    # Link concept nodes to their topic
    await session.run(
        f"""MATCH (c1:Concept {{node_id: $source}}), (c2:Concept {{node_id: $target}})
            MERGE (c1)-[r:{rel_type_upper}]->(c2)
            SET r.edge_id = $edge_id, r.reason = $reason, r.weight = $weight,
                r.confidence = $confidence, r.created_at = $created_at""",
        {
            "source": source_node_id,
            "target": target_node_id,
            "edge_id": edge_id,
            "reason": reason,
            "weight": weight,
            "confidence": confidence,
            "created_at": datetime.now().isoformat(),
        },
    )


async def link_concept_to_topic(session, topic_id: str, node_id: str):
    await session.run(
        """MATCH (t:Topic {topic_id: $topic_id}), (c:Concept {node_id: $node_id})
           MERGE (t)-[:HAS_NODE]->(c)""",
        {"topic_id": topic_id, "node_id": node_id},
    )


# ==================== Graph Queries ====================

async def get_topic_graph(session, topic_id: str) -> dict:
    """Get all nodes and edges for a topic."""
    # Get all concept nodes for this topic
    result = await session.run(
        "MATCH (c:Concept {topic_id: $topic_id}) RETURN c ORDER BY c.importance DESC",
        {"topic_id": topic_id},
    )
    nodes = [dict(record["c"]) for record in await result.data()]

    # Get all edges between concepts in this topic
    edge_result = await session.run(
        """MATCH (c1:Concept {topic_id: $topic_id})-[r]->(c2:Concept {topic_id: $topic_id})
           RETURN c1.node_id AS source, type(r) AS relation_type, c2.node_id AS target,
                  r.edge_id AS edge_id, r.reason AS reason, r.weight AS weight, r.confidence AS confidence""",
        {"topic_id": topic_id},
    )
    edges = [dict(record) for record in await edge_result.data()]

    return {"nodes": nodes, "edges": edges}


async def get_node_neighbors(
    session,
    node_id: str,
    radius: int = 1,
    relation_types: list[str] | None = None,
) -> dict:
    """Get neighbors of a node within a given radius."""
    rel_filter = ""
    params: dict[str, Any] = {"node_id": node_id}
    if relation_types:
        invalid = [t for t in relation_types if t not in ALLOWED_RELATIONSHIP_TYPES]
        if invalid:
            raise ValueError(f"get_node_neighbors: disallowed relation_types {invalid}")
        type_patterns = "|".join(relation_types)
        rel_filter = f"|{type_patterns}"

    query = f"""
    MATCH (c:Concept {{node_id: $node_id}})
    OPTIONAL MATCH path = (c)-[r{rel_filter}*1..{radius}]-(neighbor:Concept)
    WHERE neighbor.node_id <> $node_id
    RETURN DISTINCT neighbor, [rel IN relationships(path) | type(rel)] AS rel_types
    """
    result = await session.run(query, params)
    neighbors = []
    for record in await result.data():
        neighbor = dict(record["neighbor"])
        neighbor["relation_types"] = record["rel_types"]
        neighbors.append(neighbor)
    return {"node_id": node_id, "neighbors": neighbors}


async def get_mainline_path(session, topic_id: str) -> list[dict]:
    """Get the mainline path (highest importance chain) for a topic."""
    result = await session.run(
        """MATCH (t:Topic {topic_id: $topic_id})-[:HAS_NODE]->(c:Concept)
           WHERE c.topic_id = $topic_id
           WITH c ORDER BY c.importance DESC
           LIMIT 10
           OPTIONAL MATCH (c)-[r:PREREQUISITE]->(next:Concept {topic_id: $topic_id})
           RETURN c, next ORDER BY c.importance DESC""",
        {"topic_id": topic_id},
    )
    nodes = []
    seen = set()
    for record in await result.data():
        c = dict(record["c"])
        if c["node_id"] not in seen:
            nodes.append(c)
            seen.add(c["node_id"])
        if record.get("next"):
            n = dict(record["next"])
            if n["node_id"] not in seen:
                nodes.append(n)
                seen.add(n["node_id"])
    return nodes


async def get_prerequisite_chain(session, node_id: str) -> list[dict]:
    """Get the prerequisite chain for a node."""
    result = await session.run(
        """MATCH (c:Concept {node_id: $node_id})
           OPTIONAL MATCH (c)<-[r:PREREQUISITE]-(prev:Concept)
           RETURN c, prev""",
        {"node_id": node_id},
    )
    chain = []
    seen = set()
    current_node = None
    for record in await result.data():
        if current_node is None:
            current_node = dict(record["c"])
        prev = record.get("prev")
        if prev:
            p = dict(prev)
            if p["node_id"] not in seen:
                chain.append(p)
                seen.add(p["node_id"])
    # Add current node at end
    if current_node and current_node["node_id"] not in seen:
        chain.append(current_node)
    return chain


async def search_nodes_by_name(session, topic_id: str, name_query: str) -> list[dict]:
    """Search concept nodes by name (case-insensitive partial match)."""
    result = await session.run(
        """MATCH (c:Concept {topic_id: $topic_id})
           WHERE toLower(c.name) CONTAINS toLower($name_query)
           RETURN c LIMIT 20""",
        {"topic_id": topic_id, "name_query": name_query},
    )
    return [dict(record["c"]) for record in await result.data()]


async def count_topic_nodes(session, topic_id: str) -> int:
    """Count concept nodes for a topic."""
    result = await session.run(
        "MATCH (c:Concept {topic_id: $topic_id}) RETURN count(c) AS cnt",
        {"topic_id": topic_id},
    )
    record = await result.single()
    return record["cnt"] if record else 0


async def delete_concept_node(session, node_id: str):
    """Delete a concept node and its relationships."""
    await session.run(
        "MATCH (c:Concept {node_id: $node_id}) DETACH DELETE c",
        {"node_id": node_id},
    )


# ==================== Misconception Node ====================

async def create_misconception_node(session, data: dict) -> dict:
    """Create a Misconception node linked to a Concept."""
    await session.run(
        """MERGE (m:Misconception {node_id: $node_id})
           SET m.description = $description, m.severity = $severity,
               m.correction = $correction, m.topic_id = $topic_id,
               m.created_at = $created_at""",
        {
            "node_id": data["node_id"],
            "description": data.get("description", ""),
            "severity": data.get("severity", 1),
            "correction": data.get("correction", ""),
            "topic_id": data.get("topic_id", ""),
            "created_at": datetime.now().isoformat(),
        },
    )


async def link_misconception_to_concept(session, concept_node_id: str, misconception_node_id: str):
    """Link a Misconception to a Concept node."""
    await session.run(
        """MATCH (c:Concept {node_id: $concept_id}), (m:Misconception {node_id: $misconception_id})
           MERGE (c)-[:HAS_MISCONCEPTION]->(m)""",
        {"concept_id": concept_node_id, "misconception_id": misconception_node_id},
    )


async def get_misconceptions_for_concept(session, concept_node_id: str) -> list[dict]:
    """Get all misconceptions linked to a concept."""
    result = await session.run(
        """MATCH (c:Concept {node_id: $node_id})-[:HAS_MISCONCEPTION]->(m:Misconception)
           RETURN m""",
        {"node_id": concept_node_id},
    )
    return [dict(record["m"]) for record in await result.data()]


# ==================== Evidence Node ====================

async def create_evidence_node(session, data: dict) -> dict:
    """Create an Evidence node."""
    await session.run(
        """MERGE (e:Evidence {node_id: $node_id})
           SET e.text = $text, e.source = $source, e.topic_id = $topic_id,
               e.created_at = $created_at""",
        {
            "node_id": data["node_id"],
            "text": data.get("text", ""),
            "source": data.get("source", ""),
            "topic_id": data.get("topic_id", ""),
            "created_at": datetime.now().isoformat(),
        },
    )


async def link_evidence_to_concept(session, concept_node_id: str, evidence_node_id: str):
    """Link an Evidence node to a Concept."""
    await session.run(
        """MATCH (c:Concept {node_id: $concept_id}), (e:Evidence {node_id: $evidence_id})
           MERGE (c)-[:EVIDENCED_BY]->(e)""",
        {"concept_id": concept_node_id, "evidence_id": evidence_node_id},
    )


# ==================== Review Anchor Node ====================

async def create_review_anchor_node(session, data: dict) -> dict:
    """Create a ReviewAnchor node linked to a Concept."""
    await session.run(
        """MERGE (ra:ReviewAnchor {review_anchor_id: $review_anchor_id})
           SET ra.node_id = $node_id, ra.priority = $priority,
               ra.topic_id = $topic_id, ra.created_at = $created_at""",
        {
            "review_anchor_id": data["review_anchor_id"],
            "node_id": data.get("node_id", ""),
            "priority": data.get("priority", 0),
            "topic_id": data.get("topic_id", ""),
            "created_at": datetime.now().isoformat(),
        },
    )


async def link_review_anchor_to_concept(session, concept_node_id: str, review_anchor_id: str):
    """Link a ReviewAnchor to a Concept node."""
    await session.run(
        """MATCH (c:Concept {node_id: $concept_id}), (ra:ReviewAnchor {review_anchor_id: $review_anchor_id})
           MERGE (c)-[:HAS_REVIEW_ANCHOR]->(ra)""",
        {"concept_id": concept_node_id, "review_anchor_id": review_anchor_id},
    )


async def get_review_anchors_for_concept(session, concept_node_id: str) -> list[dict]:
    """Get all review anchors linked to a concept."""
    result = await session.run(
        """MATCH (c:Concept {node_id: $node_id})-[:HAS_REVIEW_ANCHOR]->(ra:ReviewAnchor)
           RETURN ra""",
        {"node_id": concept_node_id},
    )
    return [dict(record["ra"]) for record in await result.data()]
