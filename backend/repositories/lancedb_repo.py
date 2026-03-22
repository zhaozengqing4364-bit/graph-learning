"""LanceDB repository - vector database operations."""

import json
import logging
import re
from typing import Any

import lancedb
import numpy as np
import pyarrow as pa
from openai import OpenAI

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

# Known embedding model → dimension mapping
_MODEL_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


def get_embed_dimension() -> int:
    """Get the configured embedding dimension.

    Falls back to model-to-dimension mapping if embed_dimension is not explicitly set,
    or uses the default 1536 as last resort.
    """
    settings = get_settings()
    dim = settings.embed_dimension
    if dim > 0:
        return dim
    # Derive from model name if not explicitly configured
    return _MODEL_DIMENSIONS.get(settings.openai_embed_model, 1536)

# ID format pattern — all business IDs must match this (e.g. nd_xxx, tp_xxx, eg_xxx)
_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        from backend.agents.base import _get_config
        api_key = _get_config("openai_api_key")
        base_url = _get_config("openai_base_url")
        client_kwargs: dict = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        _client = OpenAI(**client_kwargs, timeout=120.0)
    return _client


def list_table_names(conn) -> list[str]:
    """Return table names across LanceDB API variants."""
    if hasattr(conn, "list_tables"):
        tables = conn.list_tables()
        return list(tables or [])
    if hasattr(conn, "table_names"):
        tables = conn.table_names()
        return list(tables or [])
    raise AttributeError("LanceDB connection does not expose list_tables() or table_names()")


def _get_embedding(text: str) -> list[float]:
    """Get embedding vector for a text using OpenAI."""
    client = _get_openai_client()
    settings = get_settings()
    response = client.embeddings.create(
        input=text,
        model=settings.openai_embed_model,
    )
    vec = response.data[0].embedding
    expected = get_embed_dimension()
    if len(vec) != expected:
        logger.warning(
            "Embedding dimension mismatch: model '%s' returned %d-dim vector, expected %d",
            settings.openai_embed_model, len(vec), expected,
        )
    return vec


def init_tables(conn):
    """Initialize LanceDB tables."""
    try:
        dim = get_embed_dimension()
        existing = list_table_names(conn)
        if "concept_embeddings" not in existing:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("topic_id", pa.string()),
                pa.field("name", pa.string()),
                pa.field("summary", pa.string()),
                pa.field("text_for_embedding", pa.string()),
                pa.field("importance", pa.float32()),
                pa.field("updated_at", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), dim)),
            ])
            conn.create_table("concept_embeddings", schema=schema)
        if "topic_embeddings" not in existing:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("title", pa.string()),
                pa.field("source_digest", pa.string()),
                pa.field("learning_intent", pa.string()),
                pa.field("topic_summary", pa.string()),
                pa.field("updated_at", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), dim)),
            ])
            conn.create_table("topic_embeddings", schema=schema)
    except Exception as e:
        logger.warning(f"LanceDB init failed: {e}")


async def add_concept_embedding(conn, node_id: str, topic_id: str, name: str, summary: str, text_for_embedding: str, importance: float = 3.0):
    """Add a concept embedding to the vector store."""
    if conn is None:
        return
    try:
        from datetime import datetime
        vector = _get_embedding(text_for_embedding)
        table = conn.open_table("concept_embeddings")
        # Upsert: delete old if exists
        try:
            if not _ID_PATTERN.match(node_id):
                raise ValueError(f"add_concept_embedding: invalid node_id '{node_id}'")
            table.delete(f"id = '{node_id}'")
        except Exception as e:
            logger.warning(f"Failed to delete old concept embedding: {e}")
        table.add([{
            "id": node_id,
            "topic_id": topic_id,
            "name": name,
            "summary": summary,
            "text_for_embedding": text_for_embedding,
            "importance": importance,
            "updated_at": datetime.now().isoformat(),
            "vector": vector,
        }])
    except Exception as e:
        logger.warning(f"Failed to add concept embedding: {e}")


async def add_topic_embedding(conn, topic_id: str, title: str, text_for_embedding: str, learning_intent: str = "", source_digest: str = "", topic_summary: str = ""):
    """Add a topic embedding to the vector store."""
    if conn is None:
        return
    try:
        from datetime import datetime
        import hashlib
        vector = _get_embedding(text_for_embedding)
        table = conn.open_table("topic_embeddings")
        try:
            if not _ID_PATTERN.match(topic_id):
                raise ValueError(f"add_topic_embedding: invalid topic_id '{topic_id}'")
            table.delete(f"id = '{topic_id}'")
        except Exception as e:
            logger.warning(f"Failed to delete old topic embedding: {e}")
        digest = source_digest or hashlib.md5(text_for_embedding.encode()).hexdigest()
        row = {
            "id": topic_id,
            "title": title,
            "source_digest": digest,
            "learning_intent": learning_intent,
            "topic_summary": topic_summary,
            "updated_at": datetime.now().isoformat(),
            "vector": vector,
        }
        table.add([row])
    except Exception as e:
        logger.warning(f"Failed to add topic embedding: {e}")


async def search_similar_concepts(
    conn,
    text: str,
    topic_id: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Search for similar concepts. Returns results with similarity scores.

    Thresholds:
    - >=0.92: high probability duplicate
    - 0.85-0.92: similar candidate
    - <0.85: likely new node
    """
    if conn is None:
        return []

    try:
        vector = _get_embedding(text)
        table = conn.open_table("concept_embeddings")

        query = table.search(vector).limit(limit).to_pandas()
        if query.empty:
            return []

        results = []
        for _, row in query.iterrows():
            result = {
                "id": row.get("id", ""),
                "topic_id": row.get("topic_id", ""),
                "name": row.get("name", ""),
                "summary": row.get("summary", ""),
                "similarity": float(row.get("_distance", 0)),
            }
            # Convert distance to similarity (cosine: similarity = 1 - distance)
            result["similarity"] = round(1.0 - result["similarity"], 4)
            if topic_id and result["topic_id"] != topic_id:
                continue
            results.append(result)

        return sorted(results, key=lambda x: x["similarity"], reverse=True)
    except Exception as e:
        logger.warning(f"Concept search failed: {e}")
        return []


async def search_similar_topics(conn, text: str, limit: int = 5) -> list[dict]:
    """Search for similar topics."""
    if conn is None:
        return []

    try:
        vector = _get_embedding(text)
        table = conn.open_table("topic_embeddings")

        query = table.search(vector).limit(limit).to_pandas()
        if query.empty:
            return []

        results = []
        for _, row in query.iterrows():
            results.append({
                "id": row.get("id", ""),
                "title": row.get("title", ""),
                "similarity": round(1.0 - float(row.get("_distance", 0)), 4),
            })

        return sorted(results, key=lambda x: x["similarity"], reverse=True)
    except Exception as e:
        logger.warning(f"Topic search failed: {e}")
        return []


def is_duplicate(similarity: float) -> bool:
    """Check if similarity indicates a duplicate (>=0.92)."""
    return similarity >= 0.92


def is_similar_candidate(similarity: float) -> bool:
    """Check if similarity indicates a candidate for review (0.85-0.92)."""
    return 0.85 <= similarity < 0.92


def delete_topic_vectors(conn, topic_id: str):
    """Delete all vectors (concept + topic embeddings) for a given topic_id."""
    if conn is None:
        return
    try:
        table = conn.open_table("concept_embeddings")
        df = table.to_pandas()
        if not df.empty:
            mask = df["topic_id"] == topic_id
            if mask.any():
                table.delete(mask)
    except Exception as e:
        logger.warning(f"Failed to delete concept vectors for topic {topic_id}: {e}")
    try:
        table = conn.open_table("topic_embeddings")
        df = table.to_pandas()
        if not df.empty:
            mask = df["id"] == topic_id
            if mask.any():
                table.delete(mask)
    except Exception as e:
        logger.warning(f"Failed to delete topic vectors for topic {topic_id}: {e}")
