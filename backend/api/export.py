"""Export API routes."""

import logging

from fastapi import APIRouter, Request

from backend.core.response import success_response, error_response
from backend.models.node import ExportRequest
from backend.services import export_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/topics/{topic_id}/export")
async def export_topic(request: Request, topic_id: str, body: ExportRequest):
    """Export topic data as markdown, JSON, or Anki."""
    db = request.app.state.db
    neo4j = request.app.state.neo4j

    try:
        result = await export_service.export_topic(
            db, topic_id, neo4j=neo4j, export_type=body.export_type,
        )
        if result is None:
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")
        if "error" in result:
            return error_response(result["error"], error_code=result.get("error_code", "EXPORT_FAILED"))
        return success_response(data=result)
    except Exception as e:
        logger.warning(f"Export failed: {e}", exc_info=True)
        return error_response("导出失败，请稍后重试", error_code="EXPORT_FAILED")
