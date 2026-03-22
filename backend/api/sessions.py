"""Session API routes."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.core.response import success_response, error_response
from backend.models.session import SessionCreate, SessionVisit
from backend.services import session_service

import logging
logger = logging.getLogger(__name__)

router = APIRouter()


class CompleteSessionRequest(BaseModel):
    generate_summary: bool = False
    generate_review_items: bool = False


@router.post("/topics/{topic_id}/sessions")
async def create_session(request: Request, topic_id: str, data: SessionCreate):
    db = request.app.state.db
    try:
        result = await session_service.start_session(db, topic_id, data)
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to create session for topic %s", topic_id)
        return error_response("创建会话失败，请稍后重试", error_code="SESSION_CREATE_FAILED")


@router.get("/topics/{topic_id}/sessions/{session_id}")
async def get_session(request: Request, topic_id: str, session_id: str):
    db = request.app.state.db
    result = await session_service.get_session(db, session_id)
    if not result:
        return error_response("Session not found", error_code="SESSION_NOT_FOUND")
    if result.get("topic_id") != topic_id:
        return error_response("Session not found", error_code="SESSION_NOT_FOUND")
    return success_response(data=result)


@router.post("/topics/{topic_id}/sessions/{session_id}/visit")
async def record_visit(request: Request, topic_id: str, session_id: str, visit: SessionVisit):
    db = request.app.state.db
    session = await session_service.get_session(db, session_id)
    if not session or session.get("topic_id") != topic_id:
        return error_response("Session not found", error_code="SESSION_NOT_FOUND")
    try:
        await session_service.record_visit(db, session_id, visit, topic_id=topic_id)
    except ValueError:
        return error_response("会话已结束，请重新开始学习", error_code="SESSION_NOT_ACTIVE")
    except Exception as e:
        logger.warning("Failed to record visit for session %s: %s", session_id, e)
        return error_response("记录访问失败", error_code="VISIT_RECORD_FAILED")
    return success_response(data=None)


@router.post("/topics/{topic_id}/sessions/{session_id}/complete")
async def complete_session(request: Request, topic_id: str, session_id: str, body: CompleteSessionRequest | None = None):
    db = request.app.state.db
    neo4j = request.app.state.neo4j
    lancedb = request.app.state.lancedb

    # Verify session belongs to this topic before completing
    session = await session_service.get_session(db, session_id)
    if not session or session.get("topic_id") != topic_id:
        return error_response("Session not found", error_code="SESSION_NOT_FOUND")

    generate_summary = body.generate_summary if body else False
    generate_review_items = body.generate_review_items if body else False

    try:
        result = await session_service.complete_session(
            db, neo4j, lancedb, session_id,
            generate_summary=generate_summary,
            generate_review_items=generate_review_items,
        )
        if not result:
            return error_response("Session not found", error_code="SESSION_NOT_FOUND")
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to complete session %s", session_id)
        return error_response("完成会话失败，请稍后重试", error_code="SESSION_COMPLETE_FAILED")
