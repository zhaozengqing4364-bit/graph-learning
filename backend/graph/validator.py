"""Graph write validator - validates AI output before writing to Neo4j."""

import logging

from backend.models.edge import EdgeType
from backend.repositories import lancedb_repo

logger = logging.getLogger(__name__)

ALLOWED_RELATION_TYPES = {rt.value for rt in EdgeType}
DUPLICATE_THRESHOLD = 0.92
SIMILAR_CANDIDATE_MIN = 0.85

# Patterns that should not appear in any AI-generated text field
SUSPICIOUS_PATTERNS = ("<script", "javascript:", "data:text/html", "onerror=", "onload=", "<iframe", "```html", "<img src=x onerror")
MAX_TEXT_FIELD_LENGTH = 50000


def validate_relation_type(relation_type: str) -> bool:
    """Check if relation type is in the whitelist."""
    return relation_type.upper() in ALLOWED_RELATION_TYPES


def validate_node_fields(node: dict) -> list[str]:
    """Validate required fields for a node. Returns list of errors."""
    errors = []
    if not node.get("name"):
        errors.append("name is required")
    if not node.get("summary"):
        errors.append("summary is required")
    if "importance" in node:
        importance = node["importance"]
        if not isinstance(importance, int) or importance < 1 or importance > 5:
            errors.append("importance must be 1-5")
    return errors


def validate_edge_fields(edge: dict) -> list[str]:
    """Validate required fields for an edge. Returns list of errors."""
    errors = []
    if not edge.get("source"):
        errors.append("source is required")
    if not edge.get("target"):
        errors.append("target is required")
    if not edge.get("relation_type"):
        errors.append("relation_type is required")
    elif not validate_relation_type(edge["relation_type"]):
        errors.append(f"invalid relation_type: {edge['relation_type']}")
    if edge.get("source") == edge.get("target"):
        errors.append("source and target must be different")
    return errors


async def check_duplicate_node(
    lancedb_conn,
    name: str,
    summary: str,
    topic_id: str,
) -> dict:
    """Check if a similar node already exists in the vector store.

    Returns {"is_duplicate": bool, "similarity": float, "candidate": dict|None}
    """
    if not lancedb_conn:
        return {"is_duplicate": False, "similarity": 0.0, "candidate": None}

    text = f"{name} {summary}"
    results = await lancedb_repo.search_similar_concepts(lancedb_conn, text, topic_id=topic_id, limit=1)

    if not results:
        return {"is_duplicate": False, "similarity": 0.0, "candidate": None}

    best = results[0]
    return {
        "is_duplicate": lancedb_repo.is_duplicate(best["similarity"]),
        "similarity": best["similarity"],
        "candidate": best,
    }


async def validate_and_filter_nodes(
    lancedb_conn,
    nodes: list[dict],
    topic_id: str,
) -> list[dict]:
    """Filter out nodes that are duplicates or have validation errors.

    Validation pipeline:
    1. Schema/field validation
    2. LanceDB semantic dedup (>=0.92 threshold)
    3. Topic context consistency (name length, no special chars)
    """
    valid_nodes = []
    for node in nodes:
        errors = validate_node_fields(node)
        if errors:
            logger.warning(f"Node validation errors for '{node.get('name', '')}': {errors}")
            continue

        # Check for duplicates via LanceDB
        dup_check = await check_duplicate_node(lancedb_conn, node["name"], node["summary"], topic_id)
        if dup_check["is_duplicate"]:
            logger.info(f"Skipping duplicate node '{node['name']}' (similarity={dup_check['similarity']})")
            continue

        # Topic context consistency: ensure node name is reasonable
        name = node["name"]
        if len(name) > 100:
            logger.warning(f"Skipping node with excessively long name ({len(name)} chars): {name[:50]}...")
            continue
        # Reject names with suspicious patterns (URLs, code blocks)
        if any(p in name.lower() for p in ("http://", "https://", "```", "<script")):
            logger.warning(f"Skipping node with suspicious name pattern: {name[:50]}")
            continue

        # Check summary and article_body for injection patterns and length
        _skip_node = False
        for field_name in ("summary", "article_body"):
            text = node.get(field_name, "")
            if not text:
                continue
            if len(text) > MAX_TEXT_FIELD_LENGTH:
                logger.warning(f"Skipping node with excessively long {field_name} ({len(text)} chars): {name[:50]}")
                _skip_node = True
                break
            if any(p in text.lower() for p in SUSPICIOUS_PATTERNS):
                logger.warning(f"Skipping node with suspicious pattern in {field_name}: {name[:50]}")
                _skip_node = True
                break

        if not _skip_node:
            valid_nodes.append(node)
    return valid_nodes


def validate_and_filter_edges(
    edges: list[dict],
    valid_node_names: set[str],
) -> list[dict]:
    """Filter out edges that have validation errors or reference invalid nodes."""
    valid_edges = []
    for edge in edges:
        errors = validate_edge_fields(edge)
        if errors:
            logger.warning(f"Edge validation errors: {errors}")
            continue

        source = edge["source"]
        target = edge["target"]

        # Allow references by name if they match valid nodes
        if source not in valid_node_names or target not in valid_node_names:
            logger.warning(f"Edge references unknown nodes: {source} -> {target}")
            continue

        valid_edges.append(edge)
    return valid_edges
