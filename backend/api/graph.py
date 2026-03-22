"""Graph API routes."""

import logging

from fastapi import APIRouter, Request

from backend.core.response import success_response, error_response
from backend.repositories import neo4j_repo as graph
from backend.services import node_service

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_VIEWS = {"full", "mainline", "prerequisite", "misconception"}


@router.get("/topics/{topic_id}/graph")
async def get_topic_graph(
    request: Request,
    topic_id: str,
    view: str = "mainline",
    max_depth: int = 3,

    focus_node_id: str | None = None,
    collapsed: bool = True,
):
    neo4j = request.app.state.neo4j
    if not neo4j:
        # Fallback: build minimal graph from SQLite data
        return await _sqlite_graph_fallback(request, topic_id, view, focus_node_id, collapsed)

    if view not in _VALID_VIEWS:
        return error_response(f"Invalid view mode: {view}. Must be one of {', '.join(sorted(_VALID_VIEWS))}", error_code="GRAPH_INVALID_VIEW")

    try:
        async with neo4j.session() as session:
            if view == "mainline":
                # Only return nodes/edges on the mainline path (PREREQUISITE chain)
                nodes = await graph.get_mainline_path(session, topic_id)
                # Also get edges between these mainline nodes
                mainline_ids = [n.get("node_id") for n in nodes if n.get("node_id")]
                result = {"nodes": nodes, "edges": []}
                if mainline_ids:
                    edge_result = await session.run(
                        """MATCH (c1:Concept)-[r:PREREQUISITE]->(c2:Concept)
                           WHERE c1.node_id IN $ids AND c2.node_id IN $ids
                           AND c1.topic_id = $topic_id AND c2.topic_id = $topic_id
                           RETURN c1.node_id AS source, type(r) AS relation_type,
                                  c2.node_id AS target, r.reason AS reason, r.weight AS weight, r.confidence AS confidence""",
                        {"ids": mainline_ids, "topic_id": topic_id},
                    )
                    result["edges"] = [dict(record) for record in await edge_result.data()]
            elif view == "prerequisite":
                # Only return PREREQUISITE edges
                node_result = await session.run(
                    "MATCH (c:Concept {topic_id: $topic_id}) RETURN c ORDER BY c.importance DESC",
                    {"topic_id": topic_id},
                )
                all_nodes = [dict(record["c"]) for record in await node_result.data()]
                edge_result = await session.run(
                    """MATCH (c1:Concept {topic_id: $topic_id})-[r:PREREQUISITE]->(c2:Concept {topic_id: $topic_id})
                       RETURN c1.node_id AS source, type(r) AS relation_type, c2.node_id AS target,
                              r.reason AS reason, r.weight AS weight, r.confidence AS confidence""",
                    {"topic_id": topic_id},
                )
                edges = [dict(record) for record in await edge_result.data()]
                # Filter nodes to only those involved in prerequisite edges
                involved_ids = set()
                for e in edges:
                    involved_ids.add(e["source"])
                    involved_ids.add(e["target"])
                filtered_nodes = [n for n in all_nodes if n.get("node_id") in involved_ids]
                result = {"nodes": filtered_nodes, "edges": edges}
            elif view == "misconception":
                # Only return MISUNDERSTOOD_AS edges
                node_result = await session.run(
                    "MATCH (c:Concept {topic_id: $topic_id}) RETURN c ORDER BY c.importance DESC",
                    {"topic_id": topic_id},
                )
                all_nodes = [dict(record["c"]) for record in await node_result.data()]
                edge_result = await session.run(
                    """MATCH (c1:Concept {topic_id: $topic_id})-[r:MISUNDERSTOOD_AS]->(c2:Concept {topic_id: $topic_id})
                       RETURN c1.node_id AS source, type(r) AS relation_type, c2.node_id AS target,
                              r.reason AS reason, r.weight AS weight, r.confidence AS confidence""",
                    {"topic_id": topic_id},
                )
                edges = [dict(record) for record in await edge_result.data()]
                involved_ids = set()
                for e in edges:
                    involved_ids.add(e["source"])
                    involved_ids.add(e["target"])
                filtered_nodes = [n for n in all_nodes if n.get("node_id") in involved_ids]
                result = {"nodes": filtered_nodes, "edges": edges}
            else:
                # view == "full": return all nodes/edges
                result = await graph.get_topic_graph(session, topic_id)

        meta = {"view": view, "collapsed": collapsed}
        if focus_node_id:
            meta["current_node_id"] = focus_node_id
        return success_response(data=result, meta=meta)
    except Exception as e:
        logger.warning(f"Failed to get graph: {e}", exc_info=True)
        return error_response("图谱数据加载失败", error_code="GRAPH_LOAD_FAILED")


@router.get("/topics/{topic_id}/graph/mainline")
async def get_mainline(request: Request, topic_id: str):
    neo4j = request.app.state.neo4j
    if not neo4j:
        return await _sqlite_graph_fallback(request, topic_id, "mainline")

    try:
        async with neo4j.session() as session:
            nodes = await graph.get_mainline_path(session, topic_id)
        return success_response(data=nodes)
    except Exception as e:
        logger.warning(f"Failed to get mainline: {e}", exc_info=True)
        return error_response("主干路径加载失败", error_code="MAINLINE_FAILED")


@router.get("/topics/{topic_id}/graph/neighborhood/{node_id}")
async def get_neighborhood(
    request: Request,
    topic_id: str,
    node_id: str,
    radius: int = 1,
    relation_types: str | None = None,
):
    neo4j = request.app.state.neo4j
    if not neo4j:
        return success_response(data={"node_id": node_id, "name": node_id, "neighbors": []})

    try:
        types = relation_types.split(",") if relation_types else None
        async with neo4j.session() as session:
            result = await graph.get_node_neighbors(session, node_id, radius=radius, relation_types=types)
        return success_response(data=result)
    except Exception as e:
        logger.warning(f"Failed to get neighborhood: {e}", exc_info=True)
        return error_response("节点邻域加载失败", error_code="NEIGHBORHOOD_FAILED")


async def _sqlite_graph_fallback(request: Request, topic_id: str, view: str = "full", focus_node_id: str | None = None, collapsed: bool = True):
    """Build minimal graph from SQLite when Neo4j is unavailable."""
    db = request.app.state.db
    result = await node_service.get_sqlite_graph_fallback(db, topic_id)

    meta = {"view": view, "collapsed": collapsed, "fallback": True}
    if focus_node_id:
        meta["current_node_id"] = focus_node_id
    return success_response(data=result, meta=meta)
