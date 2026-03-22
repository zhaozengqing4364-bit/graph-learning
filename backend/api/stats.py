"""Stats API routes - global learning statistics aggregation."""

import logging

from fastapi import APIRouter, Request

from backend.core.response import success_response, error_response
from backend.services import stats_service, ability_service, topic_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats")
async def get_global_stats(request: Request):
    """Get global learning statistics across all topics."""
    try:
        db = request.app.state.db
        data = await stats_service.get_global_stats(db)
        return success_response(data=data)
    except Exception as e:
        logger.exception("Failed to get global stats")
        return error_response("统计数据加载失败，请稍后重试", error_code="STATS_GLOBAL_FAILED")


@router.get("/stats/topics/{topic_id}")
async def get_topic_stats(request: Request, topic_id: str):
    """Get detailed stats for a specific topic."""
    try:
        db = request.app.state.db
        neo4j = request.app.state.neo4j

        topic = await topic_service.get_topic_detail(db, topic_id)
        if not topic:
            return error_response("Topic not found", error_code="TOPIC_NOT_FOUND")

        # Ability overview — delegate to ability_service for consistent logic
        overview = await ability_service.get_ability_overview(db, topic_id)
        ability_averages = overview.get("ability_averages") or {}

        # Enrich with Neo4j node names
        weak_nodes_raw = overview.get("weak_nodes", [])
        strongest_nodes_raw = overview.get("strongest_nodes", [])
        explain_gap_nodes_raw = overview.get("explain_gap_nodes", [])

        all_node_ids = list({n["node_id"] for lst in [weak_nodes_raw, strongest_nodes_raw, explain_gap_nodes_raw] for n in lst})
        name_map: dict[str, str] = {}
        if neo4j and all_node_ids:
            try:
                from backend.repositories import neo4j_repo as graph
                async with neo4j.session() as sess:
                    name_map = await graph.batch_get_concept_names(sess, all_node_ids)
            except Exception as e:
                logger.warning(f"Failed to batch-fetch concept names from Neo4j: {e}")

        weak_nodes = [
            {"node_id": n["node_id"], "name": name_map.get(n["node_id"], ""), "avg": n.get("average", 0)}
            for n in weak_nodes_raw
        ]
        strongest_nodes = [
            {"node_id": n["node_id"], "name": name_map.get(n["node_id"], ""), "avg": n.get("average", 0)}
            for n in strongest_nodes_raw
        ]
        explain_gap_nodes = [
            {"node_id": n["node_id"], "name": name_map.get(n["node_id"], "")}
            for n in explain_gap_nodes_raw
        ]

        return success_response(data={
            "topic": {
                "topic_id": topic_id,
                "title": topic.get("title", ""),
                "total_nodes": topic.get("total_nodes", 0),
                "learned_nodes": topic.get("learned_nodes", 0),
                "total_practice": topic.get("total_practice", 0),
                "total_sessions": topic.get("total_sessions", 0),
            },
            "ability_averages": ability_averages,
            "weak_nodes": weak_nodes,
            "strongest_nodes": strongest_nodes,
            "explain_gap_nodes": explain_gap_nodes,
            "total_ability_records": overview.get("total_nodes", 0),
        })
    except Exception as e:
        logger.exception("Failed to get topic stats for %s", topic_id)
        return error_response("主题统计加载失败", error_code="STATS_TOPIC_FAILED")
