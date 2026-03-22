"""Explorer agent - knowledge graph exploration and node generation."""

import json
import logging
from pathlib import Path

from backend.agents.base import AIClient, validate_ai_output
from backend.models.common import generate_id

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

# Intent-specific guidance for Explorer
_INTENT_GUIDANCE = {
    "fix_gap": "优先生成 prerequisite 关系的节点，聚焦补齐前置知识。",
    "build_system": "优先生成主干结构节点，建立完整的知识体系。",
    "solve_task": "优先生成最短路径节点（2-5个），聚焦问题解决。",
    "prepare_expression": "正常流程，但节点生成应考虑表达训练的便利性。",
    "prepare_interview": "优先生成高频面试考点相关的节点。",
}

_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "entry_node": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "summary": {"type": "string"},
                "why_it_matters": {"type": "string"},
                "importance": {"type": "integer"},
                "article_body": {"type": "string"},
            },
            "required": ["name", "summary", "article_body"],
        },
        "outline": {
            "type": "object",
            "properties": {
                "mainline": {"type": "array", "items": {"type": "string"}},
                "suggested_nodes": {"type": "integer"},
            },
            "required": ["mainline", "suggested_nodes"],
        },
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "summary": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "importance": {"type": "integer"},
                    "article_body": {"type": "string"},
                    "applications": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "examples": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "misconceptions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name", "summary", "article_body"],
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "relation_type": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["source", "target", "relation_type"],
            },
        },
    },
    "required": ["entry_node", "outline", "nodes", "edges"],
}

_EXPAND_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "summary": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "importance": {"type": "integer"},
                    "article_body": {"type": "string"},
                    "applications": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "examples": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "misconceptions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["name", "summary", "article_body"],
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "relation_type": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["source", "target", "relation_type"],
            },
        },
        "suggested_next": {"type": "string"},
    },
    "required": ["nodes", "edges"],
}


def _load_prompt(name: str) -> str:
    path = _PROMPT_DIR / name
    if not path.exists():
        logging.warning(f"Explorer prompt file not found: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def create_topic_prompt(
    source_content: str,
    learning_intent: str = "build_system",
) -> tuple[str, str]:
    """Build system and user prompts for topic creation."""
    intent_guidance = _INTENT_GUIDANCE.get(learning_intent, "正常流程。")
    system = _load_prompt("explorer_create.md")
    if not system:
        system = "你是一个知识结构提取专家。请从用户输入中提取知识节点和关系。"
    system = system.replace("{learning_intent}", learning_intent)
    system = system.replace("{intent_guidance}", intent_guidance)
    _MAX_SOURCE_LENGTH = 8000
    truncated_content = source_content[:_MAX_SOURCE_LENGTH]
    if len(source_content) > _MAX_SOURCE_LENGTH:
        logger = logging.getLogger(__name__)
        logger.warning("Source content truncated from %d to %d chars for topic creation", len(source_content), _MAX_SOURCE_LENGTH)
    user = f"请从以下输入内容中提取知识结构：\n\n{truncated_content}"
    return system, user


def expand_node_prompt(
    current_node: dict,
    topic_title: str,
    learning_intent: str,
    existing_nodes: str,
    depth_limit: int = 2,
) -> tuple[str, str]:
    """Build prompts for node expansion."""
    system = _load_prompt("explorer_expand.md")
    if not system:
        system = "你是一个知识图谱扩展专家。请根据当前节点和已有节点扩展相关知识。"
    system = system.replace("{topic_title}", topic_title)
    system = system.replace("{learning_intent}", learning_intent)
    user = f"当前节点：{current_node.get('name', '')} - {current_node.get('summary', '')}\n\n已有节点：{existing_nodes}\n\n扩展深度限制：{depth_limit} 层"
    return system, user


async def create_topic(
    source_content: str,
    learning_intent: str = "build_system",
    model: str | None = None,
) -> dict | None:
    """Create a topic by parsing source content with AI.

    Returns structured output with entry_node, outline, nodes, edges.
    Returns None on failure (caller should use fallback).
    """
    system, user = create_topic_prompt(source_content, learning_intent)
    client = AIClient(model=model)
    result = await client.call(system, user, output_schema=_OUTPUT_SCHEMA)
    return validate_ai_output(result, required_fields=["entry_node", "nodes"], field_types={"entry_node": dict, "nodes": list})


async def expand_node(
    current_node: dict,
    topic_title: str,
    learning_intent: str,
    existing_nodes: str,
    depth_limit: int = 2,
    model: str | None = None,
) -> dict | None:
    """Expand nodes around current node with AI."""
    system, user = expand_node_prompt(current_node, topic_title, learning_intent, existing_nodes, depth_limit=depth_limit)
    client = AIClient(model=model)
    result = await client.call(system, user, output_schema=_EXPAND_SCHEMA)
    return validate_ai_output(result, required_fields=["nodes"], field_types={"nodes": list})


def create_topic_fallback(title: str) -> dict:
    """Fallback: return minimal topic data when AI fails."""
    return {
        "entry_node": {
            "name": title,
            "summary": f"关于 {title} 的学习。",
            "why_it_matters": "这是你选择的学习主题。",
            "importance": 3,
        },
        "outline": {
            "mainline": [title],
            "suggested_nodes": 1,
        },
        "nodes": [],
        "edges": [],
    }
