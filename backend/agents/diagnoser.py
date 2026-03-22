"""Diagnoser agent - analyze practice answers and identify friction points."""

import logging
from pathlib import Path

from backend.agents.base import AIClient, validate_ai_output
from backend.models.friction import FrictionType

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

# Intent-specific guidance for Diagnoser
_INTENT_GUIDANCE = {
    "fix_gap": "优先看前置缺失，关注 prerequisite_gap 标签。",
    "build_system": "正常流程，关注各维度均衡发展。",
    "solve_task": "关注应用维度，重视实际场景中的表现。",
    "prepare_expression": "关注结构/自然度/受众适配三个表达维度。",
    "prepare_interview": "优先表达薄弱维度，关注口头表达的自然度。",
}

_DIAGNOSE_SCHEMA = {
    "type": "object",
    "properties": {
        "friction_tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Friction type tags from: prerequisite_gap, concept_confusion, lack_of_example, weak_structure, abstract_overload, weak_recall, weak_application",
        },
        "friction_reasons": {
            "type": "object",
            "description": "Per-tag reason explaining why this friction was detected. Keys are friction_tags, values are Chinese explanation strings.",
            "additionalProperties": {"type": "string"},
        },
        "severity": {
            "type": "integer",
            "description": "Overall severity 1-5",
        },
        "ability_delta": {
            "type": "object",
            "properties": {
                "understand": {"type": "integer"},
                "example": {"type": "integer"},
                "contrast": {"type": "integer"},
                "apply": {"type": "integer"},
                "explain": {"type": "integer"},
                "recall": {"type": "integer"},
                "transfer": {"type": "integer"},
                "teach": {"type": "integer"},
            },
        },
        "misconception_hints": {
            "type": "array",
            "items": {"type": "string"},
        },
        "suggested_prerequisite_nodes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommended_practice_type": {"type": "string"},
        "short_feedback": {"type": "string"},
        "node_id": {"type": "string"},
        "node_name": {"type": "string"},
    },
    "required": ["friction_tags", "severity", "ability_delta", "short_feedback"],
}


def _load_prompt(name: str) -> str:
    path = _PROMPT_DIR / name
    if not path.exists():
        logging.warning(f"Diagnoser prompt file not found: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def diagnose_prompt(
    node_name: str,
    node_summary: str,
    practice_type: str,
    prompt_text: str,
    user_answer: str,
    ability_record: dict | None = None,
    friction_history: list[str] | None = None,
    learning_intent: str = "build_system",
) -> tuple[str, str]:
    """Build diagnose prompts."""
    system = _load_prompt("diagnose.md")
    if not system:
        system = "你是一个学习诊断专家。请分析用户的练习回答，识别薄弱维度并提供改进建议。"
    user = (
        f"当前节点：{node_name} - {node_summary}\n"
        f"练习类型：{practice_type}\n"
        f"题目：{prompt_text}\n"
        f"用户回答：{user_answer}\n"
        f"学习意图：{_INTENT_GUIDANCE.get(learning_intent, learning_intent)}"
    )
    if ability_record:
        dims = ", ".join(f"{k}={v}" for k, v in ability_record.items() if isinstance(v, (int, float)))
        user += f"\n当前能力记录：{dims}"
    if friction_history:
        user += f"\n历史卡点标签：{', '.join(friction_history[:5])}"
    return system, user


async def diagnose(
    node_name: str,
    node_summary: str,
    practice_type: str,
    prompt_text: str,
    user_answer: str,
    node_id: str = "",
    model: str | None = None,
    ability_record: dict | None = None,
    friction_history: list[str] | None = None,
    learning_intent: str = "build_system",
) -> dict | None:
    """Diagnose a practice answer. Returns DiagnosticResult or None on failure."""
    system, user = diagnose_prompt(node_name, node_summary, practice_type, prompt_text, user_answer, ability_record, friction_history, learning_intent)
    client = AIClient(model=model)
    result = await client.call(system, user, output_schema=_DIAGNOSE_SCHEMA)
    # Validate critical fields
    result = validate_ai_output(
        result,
        required_fields=["friction_tags", "severity", "ability_delta", "short_feedback"],
        field_types={"friction_tags": list, "severity": int, "ability_delta": dict},
    )
    if result:
        result["friction_tags"] = [t for t in result["friction_tags"] if t in FrictionType.ALL]
        result["node_id"] = node_id
        result["node_name"] = node_name
    return result


def diagnose_fallback() -> dict:
    """Fallback: generic diagnosis when AI fails."""
    return {
        "friction_tags": [],
        "severity": 1,
        "ability_delta": {},
        "misconception_hints": [],
        "suggested_prerequisite_nodes": [],
        "recommended_practice_type": "",
        "short_feedback": "已使用简化反馈模式。建议继续练习。",
    }
