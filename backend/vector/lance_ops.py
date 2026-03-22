"""LanceDB vector operations - clean interface for embedding CRUD.

Provides: add_embedding, search_similar, is_duplicate.
Wraps backend.repositories.lancedb_repo for a higher-level API.
"""

from typing import Any


async def add_embedding(
    lancedb_conn: Any,
    node_id: str,
    topic_id: str,
    name: str,
    summary: str,
    text_for_embedding: str,
) -> None:
    """Add a concept embedding to the vector store.

    Args:
        lancedb_conn: LanceDB connection object.
        node_id: Unique node ID (e.g. nd_xxx).
        topic_id: Topic this node belongs to.
        name: Node name.
        summary: Node summary text.
        text_for_embedding: Full text to embed (usually name + summary).
    """
    from backend.repositories import lancedb_repo

    await lancedb_repo.add_concept_embedding(
        lancedb_conn, node_id, topic_id, name, summary, text_for_embedding
    )


async def add_topic_embedding(
    lancedb_conn: Any,
    topic_id: str,
    title: str,
    text_for_embedding: str,
) -> None:
    """Add a topic embedding to the vector store.

    Args:
        lancedb_conn: LanceDB connection object.
        topic_id: Topic ID (e.g. tp_xxx).
        title: Topic title.
        text_for_embedding: Full text to embed.
    """
    from backend.repositories import lancedb_repo

    await lancedb_repo.add_topic_embedding(
        lancedb_conn, topic_id, title, text_for_embedding
    )


async def search_similar(
    lancedb_conn: Any,
    text: str,
    topic_id: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Search for similar concepts by text query.

    Returns list of dicts with keys: id, topic_id, name, summary, similarity.
    Thresholds:
      - >=0.92: high probability duplicate
      - 0.85-0.92: similar candidate
      - <0.85: likely new node

    Args:
        lancedb_conn: LanceDB connection object.
        text: Query text to search.
        topic_id: Optional topic filter.
        limit: Max results to return.
    """
    from backend.repositories import lancedb_repo

    return await lancedb_repo.search_similar_concepts(
        lancedb_conn, text, topic_id=topic_id, limit=limit
    )


async def is_duplicate(
    lancedb_conn: Any,
    name: str,
    summary: str,
    topic_id: str,
    threshold: float = 0.92,
) -> dict:
    """Check if a node is a duplicate of an existing one.

    Args:
        lancedb_conn: LanceDB connection object.
        name: Candidate node name.
        summary: Candidate node summary.
        topic_id: Topic context for dedup.
        threshold: Similarity threshold (default 0.92).

    Returns:
        dict with keys: is_duplicate (bool), similarity (float), candidate (dict|None)
    """
    from backend.repositories import lancedb_repo

    if not lancedb_conn:
        return {"is_duplicate": False, "similarity": 0.0, "candidate": None}

    text = f"{name} {summary}"
    results = await lancedb_repo.search_similar_concepts(
        lancedb_conn, text, topic_id=topic_id, limit=1
    )

    if not results:
        return {"is_duplicate": False, "similarity": 0.0, "candidate": None}

    best = results[0]
    return {
        "is_duplicate": best.get("similarity", 0) >= threshold,
        "similarity": best.get("similarity", 0),
        "candidate": best,
    }
