"""Export service - topic data export orchestration."""

import json
import logging
import re

import aiosqlite

logger = logging.getLogger(__name__)

from backend.repositories import sqlite_repo
from backend.repositories import neo4j_repo as graph


def _sanitize_filename(title: str) -> str:
    """Remove path separators and dangerous characters from a topic title."""
    name = re.sub(r'[/\\]', '_', title.strip())
    name = re.sub(r'\.{2,}', '', name)
    name = name.strip('. ')
    return name or 'export'


async def export_topic(
    db: aiosqlite.Connection,
    topic_id: str,
    neo4j=None,
    export_type: str = "markdown",
) -> dict:
    """Export topic data as markdown, JSON, or Anki."""
    topic = await sqlite_repo.get_topic(db, topic_id)
    if not topic:
        return None

    # Gather all data
    nodes = await sqlite_repo.list_ability_records(db, topic_id)
    assets = await sqlite_repo.list_expression_assets(db, topic_id, limit=100)
    frictions = await sqlite_repo.list_frictions(db, topic_id, limit=50)
    reviews = await sqlite_repo.list_review_items(db, topic_id=topic_id, limit=100)

    graph_data = None
    if neo4j:
        try:
            async with neo4j.session() as session:
                graph_nodes = await graph.get_topic_graph(session, topic_id)
                graph_data = {
                    "nodes": graph_nodes.get("nodes", []),
                    "edges": graph_nodes.get("edges", []),
                }
        except Exception as e:
            logger.warning(f"Failed to get graph data for export: {e}")

    if export_type == "json":
        content = json.dumps({
            "topic": topic,
            "ability_records": nodes,
            "expression_assets": assets,
            "frictions": frictions,
            "reviews": reviews,
            "graph": graph_data,
        }, ensure_ascii=False, indent=2)
        return {"content": content, "format": "json", "filename": f"{_sanitize_filename(topic['title'])}.json", "topic_id": topic_id}

    # Anki format
    if export_type == "anki":
        anki_lines = []
        if graph_data:
            for node in graph_data.get("nodes", []):
                name = node.get("name", "?")
                summary = node.get("summary", "")
                article = node.get("article_body", "")
                body = article if article else summary
                body = re.sub(r"<[^>]+>", "", body)
                if len(body) > 5000:
                    body = body[:5000] + "..."
                front = name.replace("\n", "<br>").replace("\t", " ")
                back = body.replace("\n", "<br>").replace("\t", " ")
                anki_lines.append(f"{front}\t{back}")
        if not anki_lines:
            return {"error": "No nodes found for Anki export", "error_code": "EXPORT_EMPTY"}
        content = "\n".join(anki_lines)
        return {"content": content, "format": "anki", "filename": f"{_sanitize_filename(topic['title'])}.txt", "topic_id": topic_id}

    # Default: markdown
    md_lines = [
        f"# {topic.get('title', 'Unknown Topic')}",
        "",
        f"> Source: {topic.get('source_type', 'unknown')}",
        f"> Intent: {topic.get('learning_intent', 'unknown')}",
        f"> Mode: {topic.get('mode', 'unknown')}",
        f"> Nodes: {topic.get('total_nodes', 0)} | Mastered: {topic.get('learned_nodes', 0)}",
        "",
        "## Knowledge Nodes",
        "",
    ]

    graph_nodes_list = graph_data.get("nodes", []) if graph_data else []
    ability_map = {n.get("node_id"): n for n in nodes}
    for gn in graph_nodes_list:
        nid = gn.get("node_id", "")
        name = gn.get("name", nid)
        summary = gn.get("summary", "")
        article = gn.get("article_body", "")
        body_text = article if article else summary
        ar = ability_map.get(nid, {})
        scores = [ar.get(d, 0) for d in ["understand", "example", "contrast", "apply", "explain", "recall", "transfer", "teach"]]
        avg = sum(scores) / len(scores) if scores else 0
        md_lines.append(f"### {name}")
        md_lines.append(f"Ability: {avg:.0f}/100")
        if body_text:
            md_lines.append(body_text)
        md_lines.append("")

    if assets:
        md_lines.extend(["## Expression Assets", ""])
        for a in assets[:20]:
            md_lines.append(f"- **{a.get('expression_type', '?')}**: {a.get('user_expression', '')[:100]}")
        md_lines.append("")

    if frictions:
        md_lines.extend(["## Friction Records", ""])
        for f in frictions[:20]:
            md_lines.append(f"- [{f.get('friction_type', '?')}] {f.get('description', '')[:100]}")
        md_lines.append("")

    content = "\n".join(md_lines)

    # Save export record to SQLite
    try:
        from backend.models.common import generate_id
        from datetime import datetime
        export_id = generate_id("ex")
        await db.execute(
            """INSERT INTO exports (export_id, topic_id, format, content, file_path, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (export_id, topic_id, export_type, content[:1000], f"{_sanitize_filename(topic['title'])}.{export_type}", datetime.now().isoformat()),
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to save export record to SQLite: {e}")

    return {"content": content, "format": "markdown", "filename": f"{_sanitize_filename(topic['title'])}.md", "topic_id": topic_id}
