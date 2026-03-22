"""Graph traversal algorithms - BFS+DFS hybrid with mainline priority.

Core strategy: Mainline BFS + high-value branch limited-depth DFS + global convergence control.

Per CLAUDE.md algorithm spec:
- Each expand produces 3-5 nodes
- Single session max 8-12 new nodes
- Depth limit default 2-3
- Mainline priority via prerequisite weight + importance + relevance
- High-value branch: importance >= 4 or friction-correlated nodes get limited DFS
- Global convergence: cap total nodes, defer excess as "learn later" candidates
"""

from __future__ import annotations

from typing import Any

# Edge type weights for mainline scoring (from algorithm doc)
EDGE_MAINLINE_WEIGHTS: dict[str, float] = {
    "PREREQUISITE": 1.0,
    "CONTRASTS": 0.7,
    "APPLIES_IN": 0.6,
    "VARIANT_OF": 0.5,
    "EXTENDS": 0.4,
    # MISUNDERSTOOD_AS: not mainline, used for correction
}

# Edge type weights for structural priority in ExpandScore
EDGE_STRUCTURAL_PRIORITY: dict[str, float] = {
    "PREREQUISITE": 1.0,
    "CONTRASTS": 0.8,
    "APPLIES_IN": 0.6,
    "VARIANT_OF": 0.5,
    "EXTENDS": 0.4,
    "MISUNDERSTOOD_AS": 0.3,
}

# Expansion control constants (from algorithm doc)
EXPAND_MIN_NODES = 3
EXPAND_MAX_NODES = 5
SESSION_MAX_NODES = 12
DEPTH_LIMIT_MIN = 2
DEPTH_LIMIT_MAX = 3
DEFAULT_RADIUS = 1
TOPIC_MAX_NODES = 30


def get_depth_limit(requested_depth: int | None = None) -> int:
    """Get the depth limit, clamped to [2, 3]."""
    if requested_depth is None:
        return DEPTH_LIMIT_MIN
    return max(DEPTH_LIMIT_MIN, min(DEPTH_LIMIT_MAX, int(requested_depth)))


def calculate_expand_score(
    node: dict,
    learning_intent: str = "build_system",
    existing_node_names: set[str] | None = None,
    friction_tags: list[str] | None = None,
    relation_type: str = "PREREQUISITE",
) -> float:
    """Calculate ExpandScore for candidate node ordering.

    ExpandScore = Relevance x IntentMatch x StructuralPriority x ImportanceWeight x NoveltyWeight x FrictionBonus
    """
    existing = existing_node_names or set()
    frictions = set(friction_tags or [])

    # 1. ImportanceWeight (normalized 0.2-1.0 from 1-5 scale)
    importance = node.get("importance", 3)
    importance_weight = importance / 5.0

    # 2. StructuralPriority (edge type weight)
    structural = EDGE_STRUCTURAL_PRIORITY.get(relation_type, 0.5)

    # 3. IntentMatch (weight different intent priorities)
    intent_weights: dict[str, dict[str, float]] = {
        "fix_gap": {"unseen": 1.5, "browsed": 1.0, "learning": 0.5, "practiced": 0.3},
        "solve_task": {"unseen": 0.8, "browsed": 0.6, "learning": 0.4, "practiced": 0.2},
        "build_system": {"unseen": 1.0, "browsed": 0.8, "learning": 0.6, "practiced": 0.4},
        "prepare_expression": {"unseen": 0.8, "browsed": 0.8, "learning": 1.0, "practiced": 0.6},
        "prepare_interview": {"unseen": 0.8, "browsed": 0.6, "learning": 0.8, "practiced": 0.5},
    }
    weights = intent_weights.get(learning_intent, intent_weights["build_system"])
    status = node.get("status", "unseen")
    intent_match = weights.get(status, 0.5)

    # 4. NoveltyWeight (penalize if name similar to existing nodes)
    name = node.get("name", "")
    novelty = 1.0
    if name and existing:
        # Simple substring overlap check
        name_lower = name.lower()
        for existing_name in existing:
            existing_lower = existing_name.lower()
            if name_lower in existing_lower or existing_lower in name_lower:
                novelty = 0.5
                break

    # 5. FrictionBonus (boost if related to current frictions)
    friction_bonus = 1.0
    if frictions:
        # Check if node's name or summary contains friction-related terms
        summary = node.get("summary", "").lower()
        name_lower = name.lower()
        friction_keywords = {"基础", "前置", "入门", "理解", "概念", "原理"}
        if any(kw in summary or kw in name_lower for kw in friction_keywords):
            friction_bonus = 1.3

    # Importance appears as both importance_weight (normalized) and raw importance boost
    # Per algorithm doc: ExpandScore = Importance x IntentMatch x StructuralPriority x ImportanceWeight x NoveltyWeight x FrictionBonus
    importance_boost = 0.6 + (importance / 5.0) * 0.4  # Range 0.68-1.0 based on importance 1-5
    score = importance_boost * importance_weight * intent_match * structural * novelty * friction_bonus
    return round(score, 4)


def sort_nodes_by_mainline_priority(nodes: list[dict]) -> list[dict]:
    """Sort nodes for mainline-first display.

    Mainline criteria (from algorithm doc):
    - High importance
    - Has prerequisite relationships
    - Appears on multiple paths
    - Related to input goal
    """
    def mainline_sort_key(n: dict) -> tuple:
        importance = n.get("importance", 3)
        # Boost nodes that have prerequisite edges
        has_prereq = 1 if n.get("_has_prerequisite") else 0
        is_mainline = 1 if n.get("is_mainline") else 0
        # Lower status = more to learn (unseen=0, browsed=1, etc.)
        status_order = {"unseen": 0, "browsed": 1, "learning": 2, "practiced": 3, "review_due": 4, "mastered": 5}
        status_val = status_order.get(n.get("status", "unseen"), 3)
        return (-importance, -has_prereq, -is_mainline, status_val)

    return sorted(nodes, key=mainline_sort_key)


def calculate_edge_mainline_weight(relation_type: str) -> float:
    """Get the mainline weight for an edge type."""
    return EDGE_MAINLINE_WEIGHTS.get(relation_type, 0.3)


def filter_nodes_for_expand(
    candidates: list[dict],
    max_nodes: int = EXPAND_MAX_NODES,
    min_nodes: int = EXPAND_MIN_NODES,
    learning_intent: str = "build_system",
    existing_node_names: set[str] | None = None,
    friction_tags: list[str] | None = None,
) -> list[dict]:
    """Filter and sort candidate nodes for expansion.

    Applies ExpandScore ranking, then returns top 3-5 nodes.
    """
    if not candidates:
        return []

    existing = existing_node_names or set()

    # Score and sort candidates
    scored = []
    for node in candidates:
        name = node.get("name", "")
        # Skip nodes already in the topic
        if name in existing:
            continue
        # Calculate a representative relation type (use first edge if available)
        rel_type = node.get("_primary_relation_type", "PREREQUISITE")
        score = calculate_expand_score(
            node,
            learning_intent=learning_intent,
            existing_node_names=existing,
            friction_tags=friction_tags,
            relation_type=rel_type,
        )
        scored.append((score, node))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Return top N (clamped between min and max)
    count = min(max(len(scored), min_nodes), max_nodes)
    return [node for _, node in scored[:count]]


def enforce_session_cap(
    new_nodes: list[dict],
    current_session_count: int,
    session_max: int = SESSION_MAX_NODES,
) -> tuple[list[dict], list[dict], bool]:
    """Enforce session-level node creation cap.

    Returns (accepted_nodes, deferred_nodes, cap_reached).
    """
    remaining = session_max - current_session_count
    if remaining <= 0:
        return [], new_nodes, True

    if len(new_nodes) <= remaining:
        return new_nodes, [], False

    return new_nodes[:remaining], new_nodes[remaining:], True


def enforce_topic_cap(
    nodes: list[dict],
    max_total: int = TOPIC_MAX_NODES,
) -> list[dict]:
    """Enforce topic-level node cap (30 nodes).

    Prioritizes mainline nodes and high importance when trimming.
    """
    if len(nodes) <= max_total:
        return nodes

    # Sort by mainline priority before slicing
    sorted_nodes = sort_nodes_by_mainline_priority(nodes)
    return sorted_nodes[:max_total]
