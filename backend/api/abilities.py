"""Ability and diagnostics API routes."""

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.core.response import success_response, error_response
from backend.services import ability_service

logger = logging.getLogger(__name__)

router = APIRouter()


class DiagnoseRequest(BaseModel):
    practice_type: str = Field(default="explain", pattern="^(define|example|contrast|apply|explain|teach_beginner|compress)$")
    prompt_text: str = Field(default="", max_length=50000)
    user_answer: str = Field(default="", max_length=50000)
    node_name: str = ""
    node_summary: str = ""
    learning_intent: str = ""


@router.get("/topics/{topic_id}/nodes/{node_id}/ability")
async def get_ability(request: Request, topic_id: str, node_id: str):
    try:
        db = request.app.state.db
        result = await ability_service.get_ability(db, topic_id, node_id)
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to get ability for node %s", node_id)
        return error_response("能力数据加载失败", error_code="ABILITY_FAILED")


@router.get("/topics/{topic_id}/abilities/overview")
async def get_ability_overview(request: Request, topic_id: str):
    try:
        db = request.app.state.db
        result = await ability_service.get_ability_overview(db, topic_id)
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to get ability overview for topic %s", topic_id)
        return error_response("能力概览加载失败", error_code="ABILITY_OVERVIEW_FAILED")


@router.get("/topics/{topic_id}/frictions")
async def get_frictions(
    request: Request,
    topic_id: str,
    node_id: str | None = None,
    friction_type: str | None = None,
    limit: int = 20,
):
    limit = min(max(limit, 1), 200)
    try:
        db = request.app.state.db
        result = await ability_service.get_frictions(db, topic_id, node_id, friction_type, limit)
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to get frictions for topic %s", topic_id)
        return error_response("卡点数据加载失败", error_code="FRICTIONS_FAILED")


@router.post("/topics/{topic_id}/nodes/{node_id}/diagnose")
async def diagnose_node(request: Request, topic_id: str, node_id: str, body: DiagnoseRequest):
    """Diagnose a practice answer using the Diagnoser AI agent."""
    try:
        db = request.app.state.db
        neo4j = request.app.state.neo4j

        result = await ability_service.diagnose_full(
            db=db,
            neo4j=neo4j,
            topic_id=topic_id,
            node_id=node_id,
            practice_type=body.practice_type,
            prompt_text=body.prompt_text,
            user_answer=body.user_answer,
            node_name=body.node_name,
            node_summary=body.node_summary,
            learning_intent=body.learning_intent or None,
        )
        # Normalize response to match API spec fields
        if result:
            if "reasoning_summary" not in result:
                result["reasoning_summary"] = result.get("short_feedback", "")
            if "recommended_practice_types" not in result:
                recommended = result.get("recommended_practice_type", "")
                result["recommended_practice_types"] = [recommended] if recommended else []
            if "suggested_prerequisites" not in result:
                result["suggested_prerequisites"] = [
                    {"name": n} for n in result.get("suggested_prerequisite_nodes", [])
                ]
        return success_response(data=result)
    except Exception as e:
        logger.exception("Failed to diagnose node %s", node_id)
        return error_response("诊断分析失败，请稍后重试", error_code="DIAGNOSE_FAILED")


@router.get("/topics/{topic_id}/abilities/snapshots")
async def get_ability_snapshots(request: Request, topic_id: str, limit: int = 50):
    """Get ability snapshots for timeline visualization."""
    limit = min(max(limit, 1), 200)
    try:
        db = request.app.state.db
        snapshots = await ability_service.get_ability_snapshots(db, topic_id, limit=limit)
        return success_response(data=snapshots)
    except Exception as e:
        logger.exception("Failed to get ability snapshots for topic %s", topic_id)
        return error_response("能力快照加载失败", error_code="SNAPSHOTS_FAILED")
