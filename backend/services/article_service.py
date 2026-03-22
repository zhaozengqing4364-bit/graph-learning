"""Article workspace service layer."""

from __future__ import annotations

import logging
import re
from datetime import datetime

import aiosqlite
from neo4j import AsyncDriver

from backend.models.article import (
    ConceptCandidate,
    ConceptCandidateConfirm,
    ConceptCandidateCreate,
    ConceptNote,
    ConceptNoteUpsert,
    ReadingState,
    ReadingStateUpsert,
    SourceArticle,
    SourceArticleCreate,
    SourceArticleUpdate,
)
from backend.models.common import generate_id
from backend.repositories import sqlite_repo
from backend.repositories import neo4j_repo as graph

logger = logging.getLogger(__name__)

WIKI_LINK_RE = re.compile(r"\[\[(.+?)\]\]")
PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _extract_wiki_links(paragraph: str) -> list[str]:
    return [match.strip() for match in WIKI_LINK_RE.findall(paragraph) if match.strip()]


async def _get_known_concepts(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None,
    topic_id: str,
) -> dict[str, dict]:
    concepts: dict[str, dict] = {}

    confirmed_candidates = await sqlite_repo.list_concept_candidates(db, topic_id, status="confirmed")
    for candidate in confirmed_candidates:
        concept_name = candidate.get("matched_concept_name") or candidate.get("concept_text", "")
        node_id = candidate.get("matched_node_id")
        if concept_name and node_id:
            concepts[_normalize_text(concept_name)] = {
                "name": concept_name,
                "node_id": node_id,
            }

    if neo4j:
        try:
            async with neo4j.session() as session:
                topic_graph = await graph.get_topic_graph(session, topic_id)
            for node in topic_graph.get("nodes", []):
                name = node.get("name", "")
                node_id = node.get("node_id")
                if name and node_id:
                    concepts[_normalize_text(name)] = {
                        "name": name,
                        "node_id": node_id,
                    }
        except Exception as e:
            logger.warning("Failed to extract concept names from nodes: %s", e)
    return concepts


async def _ensure_candidate(
    db: aiosqlite.Connection,
    topic_id: str,
    concept_text: str,
    source_article_id: str | None,
    paragraph_index: int | None,
    anchor_id: str | None,
    origin: str,
    confidence: float,
) -> dict:
    normalized_text = _normalize_text(concept_text)
    existing = await sqlite_repo.find_candidate_by_normalized_text(db, topic_id, normalized_text)

    if existing:
        return existing

    now = datetime.now().isoformat()
    candidate = ConceptCandidate(
        candidate_id=generate_id("cd"),
        topic_id=topic_id,
        concept_text=concept_text,
        normalized_text=normalized_text,
        status="candidate",
        matched_node_id=None,
        matched_concept_name="",
        source_article_id=source_article_id,
        paragraph_index=paragraph_index,
        anchor_id=anchor_id or "",
        origin=origin,
        confidence=confidence,
        created_at=now,
        updated_at=now,
    )
    return await sqlite_repo.create_concept_candidate(db, candidate.model_dump())


def _mention_signature(mention: dict) -> tuple[str, str, str]:
    return (
        mention.get("anchor_id", ""),
        _normalize_text(mention.get("concept_text", "")),
        mention.get("concept_key") or "",
    )


async def analyze_article(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None,
    topic_id: str,
    article: dict,
) -> dict:
    existing_mentions = await sqlite_repo.list_article_mentions(db, topic_id, article_id=article["article_id"])
    existing_signatures = {_mention_signature(mention) for mention in existing_mentions}

    await sqlite_repo.delete_article_generated_candidates(db, article["article_id"])
    await sqlite_repo.delete_article_mentions(db, article["article_id"])

    known_concepts = await _get_known_concepts(db, neo4j, topic_id)
    paragraphs = [paragraph.strip() for paragraph in PARAGRAPH_SPLIT_RE.split(article.get("body", ""))]

    mentions: list[dict] = []
    valid_links: list[str] = []
    invalid_links: list[str] = []
    candidate_ids: list[str] = []

    known_items = sorted(
        known_concepts.items(),
        key=lambda item: len(item[1]["name"]),
        reverse=True,
    )

    # Pre-fetch all concept candidates for unknown explicit links (batch query)
    # to eliminate N+1 SQLite queries inside the per-link loop
    _unknown_explicit: list[tuple[str, str, int, str]] = []
    for paragraph_index, paragraph in enumerate(paragraphs):
        if not paragraph:
            continue
        explicit_links = _extract_wiki_links(paragraph)
        for link_text in explicit_links:
            normalized = _normalize_text(link_text)
            if normalized not in known_concepts:
                anchor_id = f"{article['article_id']}:paragraph:{paragraph_index}"
                _unknown_explicit.append((link_text, normalized, paragraph_index, anchor_id))
    unknown_batch: dict[str, dict] = {}
    if _unknown_explicit:
        unknown_norms = list({nt for _, nt, _, _ in _unknown_explicit})
        unknown_batch = await sqlite_repo.find_candidates_by_normalized_texts(db, topic_id, unknown_norms)

    for paragraph_index, paragraph in enumerate(paragraphs):
        if not paragraph:
            continue

        anchor_id = f"{article['article_id']}:paragraph:{paragraph_index}"
        explicit_links = _extract_wiki_links(paragraph)
        explicit_normalized = {_normalize_text(link) for link in explicit_links}

        for link_text in explicit_links:
            normalized = _normalize_text(link_text)
            known = known_concepts.get(normalized)

            if known:
                valid_links.append(known["name"])
                mentions.append({
                    "mention_id": generate_id("mt"),
                    "topic_id": topic_id,
                    "article_id": article["article_id"],
                    "concept_text": link_text,
                    "concept_name": known["name"],
                    "concept_key": known["node_id"],
                    "mention_type": "explicit",
                    "confidence": 1.0,
                    "paragraph_index": paragraph_index,
                    "anchor_id": anchor_id,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                })
                continue

            invalid_links.append(link_text)
            # Use batch-fetched candidate dict instead of per-link _ensure_candidate
            candidate = unknown_batch.get(normalized)
            if not candidate:
                candidate = await _ensure_candidate(
                    db,
                    topic_id,
                    link_text,
                    article["article_id"],
                    paragraph_index,
                    anchor_id,
                    "article_analysis",
                    0.7,
                )
            if candidate.get("status") != "ignored":
                candidate_ids.append(candidate["candidate_id"])
                mentions.append({
                    "mention_id": generate_id("mt"),
                    "topic_id": topic_id,
                    "article_id": article["article_id"],
                    "concept_text": link_text,
                    "concept_name": link_text,
                    "concept_key": candidate.get("matched_node_id"),
                    "mention_type": "candidate",
                    "confidence": 0.7,
                    "paragraph_index": paragraph_index,
                    "anchor_id": anchor_id,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                })

        for normalized_name, known in known_items:
            concept_name = known["name"]
            if normalized_name in explicit_normalized:
                continue
            if concept_name and concept_name in paragraph:
                mentions.append({
                    "mention_id": generate_id("mt"),
                    "topic_id": topic_id,
                    "article_id": article["article_id"],
                    "concept_text": concept_name,
                    "concept_name": concept_name,
                    "concept_key": known["node_id"],
                    "mention_type": "recognized",
                    "confidence": 0.35,
                    "paragraph_index": paragraph_index,
                    "anchor_id": anchor_id,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                })

    deduped_mentions: list[dict] = []
    seen_signatures: set[tuple[str, str, str]] = set()
    for mention in mentions:
        signature = _mention_signature(mention)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        deduped_mentions.append(mention)

    await sqlite_repo.create_article_mentions(db, deduped_mentions)
    new_signatures = {_mention_signature(mention) for mention in deduped_mentions}

    return {
        "mention_count": len(deduped_mentions),
        "candidate_count": len(set(candidate_ids)),
        "candidate_ids": list(dict.fromkeys(candidate_ids)),
        "valid_links": list(dict.fromkeys(valid_links)),
        "invalid_links": list(dict.fromkeys(invalid_links)),
        "added_mentions": len(new_signatures - existing_signatures),
        "removed_mentions": len(existing_signatures - new_signatures),
    }


async def create_source_article(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None,
    topic_id: str,
    data: SourceArticleCreate,
) -> dict:
    article = SourceArticle.create(topic_id, data)
    created = await sqlite_repo.create_article(db, article.model_dump())
    analysis = await analyze_article(db, neo4j, topic_id, created)
    return {"article": created, "analysis": analysis}


async def create_initial_source_article_for_topic(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None,
    topic_id: str,
    topic_title: str,
    source_content: str,
) -> dict | None:
    if not source_content.strip():
        return None
    existing = await sqlite_repo.list_articles(db, topic_id)
    if existing:
        return existing[0]
    article = SourceArticle.create(
        topic_id,
        SourceArticleCreate(
            title=f"{topic_title} · 源文章",
            body=source_content,
        ),
    )
    created = await sqlite_repo.create_article(db, article.model_dump())
    await analyze_article(db, neo4j, topic_id, created)
    return created


async def update_source_article(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None,
    topic_id: str,
    article_id: str,
    data: SourceArticleUpdate,
) -> dict | None:
    article = await sqlite_repo.get_article(db, article_id)
    if not article or article.get("topic_id") != topic_id:
        return None
    updates = {key: value for key, value in data.model_dump().items() if value is not None}
    updated = await sqlite_repo.update_article(db, article_id, updates)
    if not updated:
        return None
    analysis = await analyze_article(db, neo4j, topic_id, updated)
    return {"article": updated, "analysis": analysis}


async def upsert_note(
    db: aiosqlite.Connection,
    topic_id: str,
    concept_key: str,
    data: ConceptNoteUpsert,
) -> dict:
    existing = await sqlite_repo.get_concept_note(db, topic_id, concept_key)
    now = datetime.now().isoformat()
    note = ConceptNote(
        note_id=existing.get("note_id") if existing else generate_id("nt"),
        topic_id=topic_id,
        concept_key=concept_key,
        title=data.title,
        body=data.body,
        updated_at=now,
    )
    return await sqlite_repo.upsert_concept_note(db, note.model_dump())


async def save_reading_state(
    db: aiosqlite.Connection,
    topic_id: str,
    data: ReadingStateUpsert,
) -> dict:
    reading_state = ReadingState(
        topic_id=topic_id,
        article_id=data.article_id,
        scroll_top=data.scroll_top,
        trail=data.trail,
        completed_article_ids=data.completed_article_ids,
        updated_at=datetime.now().isoformat(),
    )
    return await sqlite_repo.upsert_article_reading_state(db, reading_state.model_dump())


async def create_candidate(
    db: aiosqlite.Connection,
    topic_id: str,
    data: ConceptCandidateCreate,
) -> dict:
    return await _ensure_candidate(
        db,
        topic_id,
        data.concept_text,
        data.source_article_id,
        data.paragraph_index,
        data.anchor_id,
        data.origin,
        0.6,
    )


async def confirm_candidate(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None,
    lancedb,
    topic_id: str,
    candidate_id: str,
    data: ConceptCandidateConfirm,
) -> dict | None:
    candidate = await sqlite_repo.get_concept_candidate(db, candidate_id)
    if not candidate or candidate.get("topic_id") != topic_id:
        return None

    concept_name = data.concept_name or candidate.get("matched_concept_name") or candidate["concept_text"]
    node_id = candidate.get("matched_node_id")
    created_new_node = False

    if not node_id:
        node_id = generate_id("nd")
        created_new_node = True

    if created_new_node and neo4j:
        try:
            async with neo4j.session() as session:
                await graph.create_concept_node(session, {
                    "node_id": node_id,
                    "name": concept_name,
                    "summary": f"{concept_name} 是由用户确认的新概念。",
                    "why_it_matters": "",
                    "article_body": "",
                    "applications": [],
                    "examples": [],
                    "misconceptions": [],
                    "importance": 2,
                    "status": "unseen",
                    "confidence": candidate.get("confidence", 0.6),
                    "topic_id": topic_id,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                })
                await graph.link_concept_to_topic(session, topic_id, node_id)
        except Exception as e:
            await sqlite_repo.record_sync_event(
                db,
                topic_id=topic_id,
                node_id=node_id,
                storage_kind="neo4j",
                operation="candidate.confirm",
                status="pending",
                error_message=str(e),
                payload={
                    "stage": "graph_write",
                    "candidate_id": candidate_id,
                    "concept_name": concept_name,
                },
            )

    if created_new_node:
        await sqlite_repo.increment_topic_stats(db, topic_id, "total_nodes")
        if lancedb:
            try:
                from backend.repositories import lancedb_repo
                await lancedb_repo.add_concept_embedding(
                    lancedb,
                    node_id,
                    topic_id,
                    concept_name,
                    f"{concept_name} 是由用户确认的新概念。",
                    f"{concept_name} {candidate.get('concept_text', concept_name)}",
                )
            except Exception as e:
                await sqlite_repo.record_sync_event(
                    db,
                    topic_id=topic_id,
                    node_id=node_id,
                    storage_kind="lancedb",
                    operation="candidate.confirm",
                    status="pending",
                    error_message=str(e),
                    payload={
                        "stage": "vector_write",
                        "candidate_id": candidate_id,
                        "concept_name": concept_name,
                    },
                )

    updated = await sqlite_repo.update_concept_candidate(db, candidate_id, {
        "status": "confirmed",
        "matched_node_id": node_id,
        "matched_concept_name": concept_name,
    })
    await sqlite_repo.rebind_mentions_to_concept(db, topic_id, candidate["normalized_text"], node_id, concept_name)
    return updated


async def batch_confirm_candidates(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None,
    lancedb,
    topic_id: str,
    candidate_ids: list[str],
    data: ConceptCandidateConfirm | None = None,
) -> dict:
    """Confirm multiple concept candidates in batch.

    Returns {confirmed: int, failed: int, results: list}.
    """
    results = []
    confirmed = 0
    failed = 0
    for cid in candidate_ids:
        try:
            result = await confirm_candidate(db, neo4j, lancedb, topic_id, cid, data or ConceptCandidateConfirm())
            if result:
                results.append({"candidate_id": cid, "status": "confirmed"})
                confirmed += 1
            else:
                results.append({"candidate_id": cid, "status": "not_found"})
                failed += 1
        except Exception as e:
            logger.warning("batch_confirm_candidates: failed for %s: %s", cid, e)
            results.append({"candidate_id": cid, "status": "error", "error": str(e)})
            failed += 1
    return {"confirmed": confirmed, "failed": failed, "results": results}


async def ignore_candidate(
    db: aiosqlite.Connection,
    topic_id: str,
    candidate_id: str,
) -> dict | None:
    candidate = await sqlite_repo.get_concept_candidate(db, candidate_id)
    if not candidate or candidate.get("topic_id") != topic_id:
        return None
    return await sqlite_repo.update_concept_candidate(db, candidate_id, {"status": "ignored"})


async def list_backlinks(
    db: aiosqlite.Connection,
    topic_id: str,
    concept_key: str,
) -> list[dict]:
    backlinks = await sqlite_repo.list_backlinks_for_concept(db, topic_id, concept_key)
    result = []
    for backlink in backlinks:
        paragraphs = [paragraph.strip() for paragraph in PARAGRAPH_SPLIT_RE.split(backlink.get("body", ""))]
        paragraph_index = backlink.get("paragraph_index", 0) or 0
        snippet = paragraphs[paragraph_index] if paragraph_index < len(paragraphs) else ""
        result.append({
            "article_id": backlink["article_id"],
            "title": backlink["title"],
            "anchor_id": backlink.get("anchor_id", ""),
            "snippet": snippet,
            "updated_at": backlink.get("updated_at"),
        })
    return result


async def get_workspace_bundle(
    db: aiosqlite.Connection,
    topic_id: str,
) -> dict:
    return {
        "source_articles": await sqlite_repo.list_articles(db, topic_id),
        "concept_notes": await sqlite_repo.list_concept_notes(db, topic_id),
        "reading_state": await sqlite_repo.get_article_reading_state(db, topic_id),
        "concept_candidates": await sqlite_repo.list_concept_candidates(db, topic_id, exclude_ignored=True),
    }


async def search_workspace(
    db: aiosqlite.Connection,
    neo4j: AsyncDriver | None,
    topic_id: str,
    query: str,
) -> dict:
    result = await sqlite_repo.search_workspace(db, topic_id, query)
    concepts: list[dict] = []
    if neo4j:
        try:
            async with neo4j.session() as session:
                concepts = await graph.search_nodes_by_name(session, topic_id, query)
        except Exception as e:
            logger.warning("Failed to search concepts by name in Neo4j: %s", e)
            concepts = []
    result["concepts"] = concepts
    return result


async def list_articles(db: aiosqlite.Connection, topic_id: str) -> list[dict]:
    """List articles for a topic."""
    return await sqlite_repo.list_articles(db, topic_id)


async def get_article(db: aiosqlite.Connection, article_id: str) -> dict | None:
    """Get a single article by ID."""
    return await sqlite_repo.get_article(db, article_id)


async def get_concept_note(db: aiosqlite.Connection, topic_id: str, concept_key: str) -> dict | None:
    """Get concept note for a topic."""
    return await sqlite_repo.get_concept_note(db, topic_id, concept_key)


async def get_article_reading_state(db: aiosqlite.Connection, topic_id: str) -> dict | None:
    """Get reading state for a topic."""
    return await sqlite_repo.get_article_reading_state(db, topic_id)


async def list_concept_candidates(db: aiosqlite.Connection, topic_id: str, status: str | None = None) -> list[dict]:
    """List concept candidates for a topic."""
    return await sqlite_repo.list_concept_candidates(db, topic_id, status=status)
