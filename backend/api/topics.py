"""Topic API routes."""

import logging

from fastapi import APIRouter, Request

from backend.core.response import success_response, error_response
from backend.models.topic import TopicCreate, TopicUpdate
from backend.services import topic_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/topics")
async def list_topics(
    request: Request,
    status: str | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    try:
        limit = min(max(limit, 1), 200)
        offset = max(offset, 0)
        db = request.app.state.db
        if q:
            items = await topic_service.search_topics(db, q, limit=limit)
            return success_response(data=items, meta={"total": len(items), "search": q})
        result = await topic_service.list_topics(db, status=status, limit=limit, offset=offset)
        return success_response(data=result["items"], meta={"total": result["total"]})
    except Exception as e:
        logger.exception("Failed to list topics")
        return error_response("主题列表加载失败", error_code="TOPICS_LIST_FAILED")


@router.post("/topics")
async def create_topic(request: Request, data: TopicCreate):
    db = request.app.state.db
    neo4j = request.app.state.neo4j
    lancedb = request.app.state.lancedb
    try:
        result = await topic_service.create_topic(db, neo4j, data, lancedb=lancedb)
        fallback_used = result.pop("fallback_used", False)
        # Build entry_node object and outline for frontend
        entry_node_id = result.get("entry_node_id")
        entry_node_name = result.get("entry_node_name", "")
        entry_node_summary = result.get("entry_node_summary", "")
        entry_node = None
        if entry_node_id:
            entry_node = {"node_id": entry_node_id, "name": entry_node_name or result.get("title", ""), "summary": entry_node_summary}
        outline = {"mainline": result.pop("_outline_mainline", []), "suggested_nodes": result.get("total_nodes", 0)}
        result["entry_node"] = entry_node
        result["outline"] = outline
        return success_response(data=result, meta={"fallback_used": fallback_used, "partial": False})
    except Exception as e:
        logger.warning(f"Failed to create topic: {e}", exc_info=e)
        return error_response("主题创建失败", error_code="TOPIC_CREATE_FAILED")


@router.get("/topics/{topic_id}")
async def get_topic(request: Request, topic_id: str):
    try:
        db = request.app.state.db
        result = await topic_service.get_topic_detail(db, topic_id)
        if not result:
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")
        result["mastered_nodes"] = await topic_service.count_mastered_nodes(db, topic_id)
        if not result.get("last_session_id"):
            last_session = await topic_service.get_last_session_id(db, topic_id)
            if last_session:
                result["last_session_id"] = last_session
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to get topic %s", topic_id)
        return error_response("主题详情加载失败", error_code="TOPIC_GET_FAILED")


@router.patch("/topics/{topic_id}")
async def update_topic(request: Request, topic_id: str, data: TopicUpdate):
    try:
        db = request.app.state.db
        result = await topic_service.update_topic(db, topic_id, data)
        if not result:
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to update topic %s", topic_id)
        return error_response("主题更新失败", error_code="TOPIC_UPDATE_FAILED")


@router.post("/topics/{topic_id}/archive")
async def archive_topic(request: Request, topic_id: str):
    try:
        db = request.app.state.db
        neo4j = request.app.state.neo4j
        result = await topic_service.archive_topic(db, neo4j, topic_id)
        if not result:
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to archive topic %s", topic_id)
        return error_response("主题归档失败", error_code="TOPIC_ARCHIVE_FAILED")


@router.delete("/topics/{topic_id}")
async def delete_topic(request: Request, topic_id: str):
    try:
        db = request.app.state.db
        neo4j = request.app.state.neo4j
        lancedb = getattr(request.app.state, "lancedb", None)
        deleted = await topic_service.delete_topic(db, neo4j, topic_id, lancedb=lancedb)
        if not deleted:
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")
        return success_response(data=None, meta={"deleted": True})
    except Exception as e:
        logger.exception("Failed to delete topic %s", topic_id)
        return error_response("主题删除失败", error_code="TOPIC_DELETE_FAILED")


@router.get("/deferred-nodes")
async def list_all_deferred_nodes(request: Request, resolved: bool = False):
    """List all deferred nodes across topics."""
    try:
        db = request.app.state.db
        neo4j = request.app.state.neo4j
        result = await topic_service.list_all_deferred_nodes(db, neo4j, resolved=resolved)
        return success_response(data=result, meta={"total": len(result)})
    except Exception as e:
        logger.exception("Failed to list deferred nodes")
        return error_response("待学节点加载失败", error_code="DEFERRED_LIST_FAILED")


@router.get("/topics/{topic_id}/practice-attempts")
async def get_practice_attempts(request: Request, topic_id: str, node_id: str | None = None, limit: int = 20):
    """Get practice attempts for a topic, optionally filtered by node."""
    try:
        limit = min(max(limit, 1), 200)
        db = request.app.state.db
        neo4j = request.app.state.neo4j
        attempts = await topic_service.list_practice_attempts(db, neo4j, topic_id, node_id=node_id, limit=limit)
        return success_response(data=attempts, meta={"total": len(attempts)})
    except Exception as e:
        logger.exception("Failed to get practice attempts for topic %s", topic_id)
        return error_response("练习记录加载失败", error_code="PRACTICE_ATTEMPTS_FAILED")


@router.get("/topics/{topic_id}/nodes/{node_id}/recommended-practice")
async def get_recommended_practice(request: Request, topic_id: str, node_id: str):
    """Get recommended next practice type for a node."""
    try:
        db = request.app.state.db
        from backend.services import practice_service
        result = await practice_service.get_recommended_practice_type(db, topic_id, node_id)
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to get recommended practice for node %s", node_id)
        return error_response("推荐练习类型加载失败", error_code="RECOMMENDED_PRACTICE_FAILED")
