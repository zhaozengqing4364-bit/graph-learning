"""Review API routes."""

import logging

from fastapi import APIRouter, Request

from backend.core.response import success_response, error_response
from backend.services import review_service
from backend.models.review import ReviewSubmitRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/reviews")
async def list_reviews(
    request: Request,
    status: str | None = None,
    topic_id: str | None = None,
    due_before: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    try:
        db = request.app.state.db
        neo4j = request.app.state.neo4j
        result = await review_service.list_reviews(db, status=status, topic_id=topic_id, due_before=due_before, limit=limit, offset=offset)
        # Enrich with node_name from Neo4j
        if neo4j and result:
            node_ids = list(set(r.get("node_id", "") for r in result if r.get("node_id")))
            if node_ids:
                try:
                    from backend.repositories import neo4j_repo
                    async with neo4j.session() as session:
                        names = await neo4j_repo.batch_get_concept_names(session, node_ids)
                    for r in result:
                        if not r.get("node_name"):
                            r["node_name"] = names.get(r.get("node_id", ""), "")
                except Exception as e:
                    logger.warning(f"Failed to enrich review items with node names: {e}")
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to list reviews")
        return error_response("复习队列加载失败，请稍后重试", error_code="REVIEWS_LIST_FAILED")


@router.get("/reviews/{review_id}")
async def get_review(request: Request, review_id: str):
    try:
        db = request.app.state.db
        result = await review_service.get_review(db, review_id)
        if not result:
            return error_response("Review item not found", error_code="REVIEW_NOT_FOUND")
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to get review %s", review_id)
        return error_response("复习详情加载失败", error_code="REVIEW_NOT_FOUND")


@router.post("/reviews/{review_id}/submit")
async def submit_review(request: Request, review_id: str):
    try:
        db = request.app.state.db
        neo4j = request.app.state.neo4j
        body = ReviewSubmitRequest(**await request.json())
        result = await review_service.submit_review(
            db, review_id,
            user_answer=body.user_answer,
            neo4j=neo4j,
            session_id=body.session_id,
        )
        return success_response(data=result.model_dump())
    except ValueError as e:
        logger.warning("Review submit failed (not found): %s", e)
        return error_response("未找到复习项目", error_code="REVIEW_NOT_FOUND")
    except Exception as e:
        logger.exception("Failed to submit review %s", review_id)
        return error_response("复习提交失败，请稍后重试", error_code="REVIEW_SUBMIT_FAILED")


@router.post("/topics/{topic_id}/reviews/generate")
async def generate_reviews(request: Request, topic_id: str):
    db = request.app.state.db
    neo4j = request.app.state.neo4j
    try:
        created = await review_service.generate_review_queue(db, topic_id, neo4j=neo4j)
        return success_response(data=created, meta={"generated_count": len(created)})
    except Exception as e:
        logger.exception("Failed to generate review queue for topic %s", topic_id)
        return error_response("生成复习队列失败，请稍后重试", error_code="REVIEW_GENERATE_FAILED")


@router.post("/reviews/{review_id}/skip")
async def skip_review(request: Request, review_id: str):
    try:
        db = request.app.state.db
        existing = await review_service.get_review(db, review_id)
        if not existing:
            return error_response("Review item not found", error_code="REVIEW_NOT_FOUND")
        await review_service.skip_review(db, review_id)
        return success_response(data=None)
    except Exception as e:
        logger.warning(f"Failed to skip review {review_id}: {e}")
        return error_response("跳过复习失败，请稍后重试", error_code="REVIEW_SKIP_FAILED")


@router.post("/reviews/{review_id}/snooze")
async def snooze_review(request: Request, review_id: str):
    try:
        db = request.app.state.db
        existing = await review_service.get_review(db, review_id)
        if not existing:
            return error_response("Review item not found", error_code="REVIEW_NOT_FOUND")
        await review_service.snooze_review(db, review_id)
        return success_response(data=None)
    except Exception as e:
        logger.warning(f"Failed to snooze review {review_id}: {e}")
        return error_response("稍后提醒设置失败，请稍后重试", error_code="REVIEW_SNOOZE_FAILED")
