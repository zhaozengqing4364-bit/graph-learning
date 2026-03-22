"""Synthesizer agent - session summary and review generation."""

import logging
from pathlib import Path

from backend.agents.base import AIClient, validate_ai_output

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

# Intent-specific guidance for Synthesizer
_INTENT_GUIDANCE = {
    "fix_gap": "总结重点强调前置知识的补齐情况和剩余缺口。",
    "build_system": "强化主线总结，梳理知识体系的完整性和连贯性。",
    "solve_task": "强调「你现在能解决什么」，总结问题解决能力的提升。",
    "prepare_expression": "强调表达训练的进展，给出表达薄弱环节的建议。",
    "prepare_interview": "强调面试高频考点的掌握情况和准备建议。",
}

_SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "mainline_summary": {"type": "string"},
        "key_takeaways": {
            "type": "array",
            "items": {"type": "string"},
        },
        "new_key_nodes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "deferred_nodes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "next_recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "name": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["node_id", "name", "summary"],
            },
        },
        "review_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "node_name": {"type": "string"},
                    "reason": {"type": "string"},
                    "review_type": {"type": "string"},
                    "priority": {"type": "integer"},
                },
                "required": ["node_name", "reason"],
            },
        },
        "asset_highlights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "practice_type": {"type": "string"},
                    "correctness": {"type": "number"},
                },
                "required": ["node_id", "practice_type"],
            },
        },
        "key_improvements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Key improvements made in this session",
        },
        "areas_to_improve": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Areas that need more work",
        },
    },
    "required": ["mainline_summary", "key_takeaways", "next_recommendations"],
}


def _load_prompt(name: str) -> str:
    path = _PROMPT_DIR / name
    if not path.exists():
        logging.warning(f"Synthesizer prompt file not found: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def synthesize_prompt(
    topic_title: str,
    visited_nodes: list[str],
    practice_count: int,
    ability_summary: str,
    deferred_nodes: list[str],
    learning_intent: str = "build_system",
) -> tuple[str, str]:
    """Build synthesis prompts."""
    system = _load_prompt("synthesize.md")
    if not system:
        system = "你是一个学习总结专家。请为一轮学习会话生成结构化总结。"
    system = system.replace("{topic_title}", topic_title)
    system = system.replace("{visited_nodes}", ", ".join(visited_nodes[:20]))
    system = system.replace("{practice_count}", str(practice_count))
    system = system.replace("{ability_summary}", ability_summary)
    system = system.replace("{deferred_nodes}", ", ".join(deferred_nodes[:10]))
    system = system.replace("{learning_intent}", _INTENT_GUIDANCE.get(learning_intent, learning_intent))
    user = f"请为这一轮学习生成总结。"
    return system, user


async def synthesize(
    topic_title: str,
    visited_nodes: list[str],
    practice_count: int,
    ability_summary: str = "",
    deferred_nodes: list[str] | None = None,
    model: str | None = None,
    learning_intent: str = "build_system",
) -> dict | None:
    """Generate session summary with AI."""
    system, user = synthesize_prompt(
        topic_title, visited_nodes, practice_count,
        ability_summary, deferred_nodes or [],
        learning_intent,
    )
    client = AIClient(model=model)
    result = await client.call(system, user, output_schema=_SUMMARY_SCHEMA)
    if result is None:
        return None
    validated = validate_ai_output(
        result,
        required_fields=["mainline_summary", "key_takeaways", "next_recommendations"],
        field_types={"mainline_summary": str, "key_takeaways": list, "next_recommendations": list},
    )
    return validated


def synthesize_fallback(
    topic_title: str,
    visited_nodes: list[str],
    practice_count: int,
) -> dict:
    """Fallback: rule-based summary when AI fails."""
    return {
        "mainline_summary": f"本轮围绕「{topic_title}」进行了学习，访问了 {len(visited_nodes)} 个节点，完成 {practice_count} 次练习。",
        "key_takeaways": [f"学习了 {n}" for n in visited_nodes[:8]],
        "new_key_nodes": visited_nodes[:8],
        "deferred_nodes": [],
        "next_recommendations": [
            {
                "node_id": "",
                "name": "继续扩展知识图谱",
                "summary": "探索更多相关节点以完善知识网络",
            },
            {
                "node_id": "",
                "name": "对薄弱节点进行表达练习",
                "summary": "针对已学习但理解不深的节点进行练习巩固",
            },
        ],
        "review_candidates": [],
        "asset_highlights": [],
        "key_improvements": [],
        "areas_to_improve": [],
    }
