"""Practice API routes."""

import logging

from fastapi import APIRouter, Request
from pydantic import ValidationError

from backend.core.response import success_response, error_response
from backend.models.practice import PracticeSubmit, PracticeRequest
from backend.models.expression import ExpressionAssetCreate
from backend.services import practice_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/topics/{topic_id}/nodes/{node_id}/practice")
async def get_practice_prompt(request: Request, topic_id: str, node_id: str):
    """Generate a practice prompt for a node using AI, with cache and static fallback."""
    try:
        body = PracticeRequest(**await request.json())
    except Exception as e:
        logger.exception("Failed to parse practice request for node %s", node_id)
        return error_response("练习请求格式错误", error_code="PRACTICE_REQUEST_INVALID")

    try:
        db = request.app.state.db
        neo4j = request.app.state.neo4j
        data, cached = await practice_service.get_practice_prompt(
            db, topic_id, node_id, body.practice_type,
            neo4j=neo4j,
            regenerate=body.regenerate,
            difficulty=body.difficulty,
        )
        return success_response(data=data, meta={"cached": cached})
    except Exception as e:
        logger.exception("Failed to generate practice prompt for node %s", node_id)
        return error_response("练习题生成失败，请稍后重试", error_code="PRACTICE_PROMPT_FAILED")


@router.post("/topics/{topic_id}/nodes/{node_id}/practice/submit")
async def submit_practice(request: Request, topic_id: str, node_id: str):
    """Submit a practice answer with Tutor AI feedback."""
    db = request.app.state.db
    neo4j = request.app.state.neo4j
    try:
        body = await request.json()
        data = PracticeSubmit(**body)
    except (ValidationError, TypeError, ValueError):
        return error_response("练习提交请求格式错误", error_code="PRACTICE_SUBMIT_INVALID")

    try:
        result = await practice_service.submit_practice(
            db, topic_id, node_id, data, neo4j=neo4j,
        )
        return success_response(data=result.model_dump())
    except practice_service.PracticeSessionNotFoundError:
        return error_response("Session not found", error_code="SESSION_NOT_FOUND")
    except practice_service.PracticeSessionNotActiveError:
        return error_response("会话已结束，请重新开始学习", error_code="SESSION_NOT_ACTIVE")
    except Exception as e:
        logger.exception("Failed to submit practice for node %s", node_id)
        return error_response("提交练习失败，请稍后重试", error_code="PRACTICE_SUBMIT_FAILED")


@router.post("/topics/{topic_id}/nodes/{node_id}/expression-assets")
async def save_expression_asset(request: Request, topic_id: str, node_id: str):
    db = request.app.state.db
    try:
        body = await request.json()
        data = ExpressionAssetCreate(**body)
    except (ValidationError, TypeError, ValueError):
        return error_response("表达资产请求格式错误", error_code="ASSET_REQUEST_INVALID")

    # Verify topic exists
    from backend.services import topic_service
    topic = await topic_service.get_topic_detail(db, topic_id)
    if not topic:
        return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

    try:
        result = await practice_service.save_expression_asset(db, topic_id, node_id, data)
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to save expression asset for node %s", node_id)
        return error_response("保存表达资产失败", error_code="ASSET_SAVE_FAILED")


@router.post("/expression-assets/{asset_id}/toggle-favorite")
async def toggle_expression_favorite(request: Request, asset_id: str):
    """Toggle favorite status of an expression asset."""
    try:
        db = request.app.state.db
        result = await practice_service.toggle_favorite(db, asset_id)
        if not result:
            return error_response("Asset not found", error_code="ASSET_NOT_FOUND")
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to toggle favorite for asset %s", asset_id)
        return error_response("收藏操作失败", error_code="TOGGLE_FAVORITE_FAILED")


@router.get("/topics/{topic_id}/expression-assets")
async def list_expression_assets(
    request: Request,
    topic_id: str,
    node_id: str | None = None,
    expression_type: str | None = None,
    favorited: bool | None = None,
    limit: int = 20,
):
    try:
        limit = min(max(limit, 1), 200)
        db = request.app.state.db
        result = await practice_service.list_expression_assets(db, topic_id, node_id, expression_type, limit, favorited=favorited)
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to list expression assets for topic %s", topic_id)
        return error_response("表达资产加载失败", error_code="EXPRESSION_ASSETS_LIST_FAILED")
