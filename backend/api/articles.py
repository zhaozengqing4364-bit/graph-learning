"""Article workspace API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.core.response import error_response, success_response
from backend.models.article import (
    ConceptCandidateConfirm,
    ConceptCandidateCreate,
    ConceptNoteUpsert,
    ReadingStateUpsert,
    SourceArticleCreate,
    SourceArticleUpdate,
)
from backend.services import article_service

router = APIRouter()

logger = logging.getLogger(__name__)


async def _topic_exists(request: Request, topic_id: str) -> bool:
    db = request.app.state.db
    cursor = await db.execute("SELECT 1 FROM topics WHERE topic_id = ?", (topic_id,))
    return await cursor.fetchone() is not None


@router.get("/topics/{topic_id}/workspace")
async def get_workspace(request: Request, topic_id: str):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        data = await article_service.get_workspace_bundle(db, topic_id)
        return success_response(data=data)
    except Exception as e:
        logger.exception("Failed to get workspace for topic %s", topic_id)
        return error_response("工作区加载失败", error_code="WORKSPACE_FAILED")


@router.get("/topics/{topic_id}/articles")
async def list_articles(request: Request, topic_id: str):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        data = await article_service.list_articles(db, topic_id)
        return success_response(data=data, meta={"total": len(data)})
    except Exception as e:
        logger.exception("Failed to list articles for topic %s", topic_id)
        return error_response("文章列表加载失败", error_code="ARTICLES_LIST_FAILED")


@router.post("/topics/{topic_id}/articles")
async def create_article(request: Request, topic_id: str, data: SourceArticleCreate):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        neo4j = request.app.state.neo4j
        result = await article_service.create_source_article(db, neo4j, topic_id, data)
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to create article for topic %s", topic_id)
        return error_response("文章创建失败", error_code="ARTICLE_CREATE_FAILED")


@router.get("/topics/{topic_id}/articles/{article_id}")
async def get_article(request: Request, topic_id: str, article_id: str):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        article = await article_service.get_article(db, article_id)
        if not article or article.get("topic_id") != topic_id:
            return error_response("Article not found", error_code="ARTICLE_NOT_FOUND")
        return success_response(data=article)
    except Exception as e:
        logger.exception("Failed to get article %s", article_id)
        return error_response("文章详情加载失败", error_code="ARTICLE_GET_FAILED")


@router.patch("/topics/{topic_id}/articles/{article_id}")
async def update_article(request: Request, topic_id: str, article_id: str, data: SourceArticleUpdate):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        neo4j = request.app.state.neo4j
        result = await article_service.update_source_article(db, neo4j, topic_id, article_id, data)
        if not result:
            return error_response("Article not found", error_code="ARTICLE_NOT_FOUND")
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to update article %s", article_id)
        return error_response("文章更新失败", error_code="ARTICLE_UPDATE_FAILED")


@router.get("/topics/{topic_id}/concept-notes/{concept_key}")
async def get_concept_note(request: Request, topic_id: str, concept_key: str):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        note = await article_service.get_concept_note(db, topic_id, concept_key)
        return success_response(data=note)
    except Exception as e:
        logger.exception("Failed to get concept note %s for topic %s", concept_key, topic_id)
        return error_response("概念笔记加载失败", error_code="CONCEPT_NOTE_GET_FAILED")


@router.put("/topics/{topic_id}/concept-notes/{concept_key}")
async def upsert_concept_note(request: Request, topic_id: str, concept_key: str, data: ConceptNoteUpsert):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        note = await article_service.upsert_note(db, topic_id, concept_key, data)
        return success_response(data=note)
    except Exception as e:
        logger.exception("Failed to upsert concept note %s for topic %s", concept_key, topic_id)
        return error_response("概念笔记保存失败", error_code="CONCEPT_NOTE_UPSERT_FAILED")


@router.get("/topics/{topic_id}/reading-state")
async def get_reading_state(request: Request, topic_id: str):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        state = await article_service.get_article_reading_state(db, topic_id)
        return success_response(data=state)
    except Exception as e:
        logger.exception("Failed to get reading state for topic %s", topic_id)
        return error_response("阅读状态加载失败", error_code="READING_STATE_GET_FAILED")


@router.put("/topics/{topic_id}/reading-state")
async def put_reading_state(request: Request, topic_id: str, data: ReadingStateUpsert):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        state = await article_service.save_reading_state(db, topic_id, data)
        return success_response(data=state)
    except Exception as e:
        logger.exception("Failed to save reading state for topic %s", topic_id)
        return error_response("阅读状态保存失败", error_code="READING_STATE_SAVE_FAILED")


@router.get("/topics/{topic_id}/concept-candidates")
async def list_concept_candidates(request: Request, topic_id: str, status: str | None = None):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        items = await article_service.list_concept_candidates(db, topic_id, status=status)
        return success_response(data=items, meta={"total": len(items)})
    except Exception as e:
        logger.exception("Failed to list concept candidates for topic %s", topic_id)
        return error_response("概念候选加载失败", error_code="CANDIDATES_LIST_FAILED")


@router.post("/topics/{topic_id}/concept-candidates")
async def create_concept_candidate(request: Request, topic_id: str, data: ConceptCandidateCreate):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        candidate = await article_service.create_candidate(db, topic_id, data)
        return success_response(data=candidate)
    except Exception as e:
        logger.exception("Failed to create concept candidate for topic %s", topic_id)
        return error_response("概念候选创建失败", error_code="CANDIDATE_CREATE_FAILED")


@router.post("/topics/{topic_id}/concept-candidates/{candidate_id}/confirm")
async def confirm_concept_candidate(
    request: Request,
    topic_id: str,
    candidate_id: str,
    data: ConceptCandidateConfirm | None = None,
):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        neo4j = request.app.state.neo4j
        lancedb = request.app.state.lancedb
        result = await article_service.confirm_candidate(
            db,
            neo4j,
            lancedb,
            topic_id,
            candidate_id,
            data or ConceptCandidateConfirm(),
        )
        if not result:
            return error_response("Candidate not found", error_code="CANDIDATE_NOT_FOUND")
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to confirm candidate %s for topic %s", candidate_id, topic_id)
        return error_response("概念确认失败", error_code="CANDIDATE_CONFIRM_FAILED")


class BatchConfirmRequest(BaseModel):
    candidate_ids: list[str]
    concept_name: str | None = None


@router.post("/topics/{topic_id}/concept-candidates/batch-confirm")
async def batch_confirm_concept_candidates(request: Request, topic_id: str, body: BatchConfirmRequest):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        neo4j = request.app.state.neo4j
        lancedb = request.app.state.lancedb
        data = ConceptCandidateConfirm(concept_name=body.concept_name) if body.concept_name else None
        result = await article_service.batch_confirm_candidates(
            db, neo4j, lancedb, topic_id, body.candidate_ids, data,
        )
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to batch confirm candidates for topic %s", topic_id)
        return error_response("批量确认失败", error_code="BATCH_CONFIRM_FAILED")


@router.post("/topics/{topic_id}/concept-candidates/{candidate_id}/ignore")
async def ignore_concept_candidate(request: Request, topic_id: str, candidate_id: str):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        result = await article_service.ignore_candidate(db, topic_id, candidate_id)
        if not result:
            return error_response("Candidate not found", error_code="CANDIDATE_NOT_FOUND")
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to ignore candidate %s for topic %s", candidate_id, topic_id)
        return error_response("概念忽略失败", error_code="CANDIDATE_IGNORE_FAILED")


@router.get("/topics/{topic_id}/workspace-search")
async def workspace_search(request: Request, topic_id: str, q: str = ""):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        neo4j = request.app.state.neo4j
        result = await article_service.search_workspace(db, neo4j, topic_id, q)
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to search workspace for topic %s", topic_id)
        return error_response("工作区搜索失败", error_code="WORKSPACE_SEARCH_FAILED")


@router.get("/topics/{topic_id}/nodes/{node_id}/backlinks")
async def get_backlinks(request: Request, topic_id: str, node_id: str):
    try:
        if not await _topic_exists(request, topic_id):
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        db = request.app.state.db
        result = await article_service.list_backlinks(db, topic_id, node_id)
        return success_response(data=result, meta={"total": len(result)})
    except Exception as e:
        logger.exception("Failed to get backlinks for node %s", node_id)
        return error_response("反向链接加载失败", error_code="BACKLINKS_FAILED")
