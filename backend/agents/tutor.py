"""Tutor agent - practice prompt generation and expression feedback."""

import logging
from pathlib import Path

from backend.agents.base import AIClient, validate_ai_output

_PROMPT_DIR = Path(__file__).parent.parent / "prompts"

# Intent-specific guidance for Tutor
_INTENT_GUIDANCE = {
    "fix_gap": "优先直觉解释与例子，帮助学生通过具体案例理解概念。",
    "build_system": "正常流程，按推荐顺序出题。",
    "solve_task": "优先应用表达，聚焦实际场景中的使用。",
    "prepare_expression": "提高表达练习密度，增加表达类题目比例。",
    "prepare_interview": "优先应用+对比，模拟面试常见问题。",
}

_PRACTICE_TYPE_MAP = {
    "define": "定义表达：用自己的话定义或解释概念",
    "example": "举例表达：举具体例子说明概念",
    "contrast": "对比表达：区分这个概念和相似概念",
    "apply": "应用表达：描述如何在实际场景中应用",
    "teach_beginner": "教学表达：用初学者能理解的方式解释",
    "compress": "压缩表达：用一句话总结核心",
    "explain": "解释表达：让不了解的人也能理解",
}

_PROMPT_SCHEMA = {
    "type": "object",
    "properties": {
        "practice_type": {"type": "string"},
        "prompt_text": {"type": "string"},
        "requirements": {
            "type": "array",
            "items": {"type": "string"},
        },
        "minimum_answer_hint": {"type": "string"},
        "evaluation_dimensions": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["practice_type", "prompt_text"],
}

_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "correctness": {"type": "string", "enum": ["good", "medium", "weak"]},
        "clarity": {"type": "string", "enum": ["good", "medium", "weak"]},
        "naturalness": {"type": "string", "enum": ["good", "medium", "weak"]},
        "consistency": {"type": "string", "enum": ["good", "medium", "weak"]},
        "issues": {
            "type": "array",
            "items": {"type": "string"},
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommended_answer": {"type": "string"},
        "expression_skeleton": {"type": "string"},
        "follow_up_question": {
            "type": "string",
            "description": "An optional follow-up question to probe deeper understanding when the answer is weak or medium.",
        },
    },
    "required": ["correctness", "clarity", "naturalness", "issues", "suggestions"],
}


def _load_prompt(name: str) -> str:
    path = _PROMPT_DIR / name
    if not path.exists():
        logging.warning(f"Tutor prompt file not found: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def generate_practice_prompt(
    node_name: str,
    node_summary: str,
    practice_type: str,
    learning_intent: str = "build_system",
    ability: dict | None = None,
    difficulty: str = "medium",
    expression_assets: list[dict] | None = None,
    misconceptions: list[dict] | None = None,
    related_nodes: list[dict] | None = None,
) -> tuple[str, str]:
    """Build practice prompt generation prompts."""
    system = _load_prompt("tutor_prompt.md")
    if not system:
        system = "你是一个学习教练。请根据知识节点信息生成练习题。"
    system = system.replace("{node_name}", node_name)
    system = system.replace("{node_summary}", node_summary)
    system = system.replace("{practice_type}", _PRACTICE_TYPE_MAP.get(practice_type, practice_type))
    system = system.replace("{learning_intent}", _INTENT_GUIDANCE.get(learning_intent, learning_intent))
    if ability:
        ability_str = ", ".join(f"{k}={v}" for k, v in ability.items() if isinstance(v, (int, float)))
        system = system.replace("{ability_context}", f"当前能力：{ability_str}")
    else:
        system = system.replace("{ability_context}", "暂无能力记录")

    # Difficulty control
    adaptive_hint = ""
    if difficulty == "adaptive" and ability:
        numeric_scores = [v for v in ability.values() if isinstance(v, (int, float))]
        avg_ability = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 50
        if avg_ability > 70:
            adaptive_hint = "用户整体能力较好，可以适当提高出题难度"
        elif avg_ability < 30:
            adaptive_hint = "用户基础较薄弱，请用简单语言出题"
        else:
            adaptive_hint = "正常难度出题"
    system = system.replace("{difficulty}", difficulty)
    system = system.replace("{adaptive_difficulty_hint}", adaptive_hint)

    # Few-shot examples for apply practice type
    _APPLY_FEW_SHOT = """
以下是「应用题」的示例格式，请参考：
示例：请描述一个可以用[概念]解决的实际场景或问题，并说明如何应用。
用户回答：在数据分析中，我使用[概念]来[具体操作]，因为[原因]...
评分标准：是否准确识别了应用场景，是否正确描述了应用方法。
"""
    if practice_type == "apply":
        system = system.replace("{few_shot_context}", _APPLY_FEW_SHOT)
    else:
        system = system.replace("{few_shot_context}", "")

    # Expression assets context — feed historical expression style into prompts
    if expression_assets:
        lines = []
        for asset in expression_assets[:3]:
            practice_t = asset.get("expression_type", asset.get("practice_type", ""))
            user_ans = asset.get("user_answer", asset.get("original_text", ""))
            correctness = asset.get("correctness", asset.get("score", ""))
            preview = (user_ans[:80] + "...") if len(user_ans) > 80 else user_ans
            lines.append(f"- [{practice_t}] \"{preview}\" (评分: {correctness})")
        expression_context = (
            "如果用户有历史表达记录，请参考用户之前的表达风格和内容来出题，引导用户改进。\n"
            "用户之前的表达参考：\n" + "\n".join(lines)
        )
    else:
        expression_context = ""
    system = system.replace("{expression_context}", expression_context)

    # Misconception context — for contrast questions
    if misconceptions and practice_type == "contrast":
        mc_lines = []
        for mc in misconceptions[:5]:
            desc = mc.get("description", mc.get("text", ""))
            severity = mc.get("severity", "medium")
            mc_lines.append(f"- {desc}（严重度: {severity}）")
        misconception_context = (
            "该节点有以下已识别的误解，请在对比题中引导用户区分这些误解：\n" + "\n".join(mc_lines)
        )
    else:
        misconception_context = ""
    system = system.replace("{misconception_context}", misconception_context)

    # Related nodes context — help generate relationship-aware prompts
    if related_nodes:
        rel_lines = []
        for rn in related_nodes[:5]:
            rn_name = rn.get("name", "未知节点")
            rn_rel = rn.get("relation_type", "")
            rn_label = {"PREREQUISITE": "前置知识", "CONTRASTS": "对比概念", "APPLIES_IN": "应用场景",
                        "VARIANT_OF": "变体", "EXTENDS": "扩展"}.get(rn_rel, rn_rel)
            rel_lines.append(f"- {rn_name}（{rn_label}）")
        relationship_context = "该节点与以下知识相关，可以在题目中适当关联：\n" + "\n".join(rel_lines)
    else:
        relationship_context = ""
    system = system.replace("{relationship_context}", relationship_context)

    user = f"请为以下节点生成一个「{_PRACTICE_TYPE_MAP.get(practice_type, practice_type)}」类型的练习题。"
    return system, user


def generate_feedback_prompt(
    node_name: str,
    node_summary: str,
    practice_type: str,
    prompt_text: str,
    user_answer: str,
    learning_intent: str = "build_system",
) -> tuple[str, str]:
    """Build feedback generation prompts."""
    system = _load_prompt("tutor_feedback.md")
    if not system:
        system = "你是一个学习反馈专家。请评估用户的练习回答并给出改进建议。当回答质量为 weak 或 medium 时，请提供一个 follow_up_question 来帮助用户深入思考。"
    system = system.replace("{node_name}", node_name)
    system = system.replace("{node_summary}", node_summary)
    system = system.replace("{practice_type}", _PRACTICE_TYPE_MAP.get(practice_type, practice_type))
    system = system.replace("{learning_intent}", _INTENT_GUIDANCE.get(learning_intent, learning_intent))
    user = (
        f"题目：{prompt_text}\n"
        f"用户回答：{user_answer}"
    )
    return system, user


async def generate_practice(
    node_name: str,
    node_summary: str,
    practice_type: str,
    learning_intent: str = "build_system",
    model: str | None = None,
    ability: dict | None = None,
    difficulty: str = "medium",
    expression_assets: list[dict] | None = None,
    misconceptions: list[dict] | None = None,
) -> dict | None:
    """Generate a practice prompt with AI."""
    system, user = generate_practice_prompt(node_name, node_summary, practice_type, learning_intent, ability, difficulty, expression_assets, misconceptions)
    client = AIClient(model=model)
    result = await client.call(system, user, output_schema=_PROMPT_SCHEMA)
    result = validate_ai_output(
        result,
        required_fields=["practice_type", "prompt_text"],
        field_types={"practice_type": str, "prompt_text": str},
    )
    return result


async def generate_feedback(
    node_name: str,
    node_summary: str,
    practice_type: str,
    prompt_text: str,
    user_answer: str,
    model: str | None = None,
    learning_intent: str = "build_system",
) -> dict | None:
    """Generate feedback for a practice answer with AI."""
    system, user = generate_feedback_prompt(node_name, node_summary, practice_type, prompt_text, user_answer, learning_intent)
    client = AIClient(model=model)
    result = await client.call(system, user, output_schema=_FEEDBACK_SCHEMA)
    result = validate_ai_output(
        result,
        required_fields=["correctness", "clarity", "naturalness", "issues", "suggestions"],
        field_types={"correctness": str, "clarity": str, "naturalness": str, "issues": list, "suggestions": list},
    )
    return result


def static_practice_fallback(practice_type: str) -> dict:
    """Fallback: return static practice prompt when AI fails."""
    return {
        "practice_type": practice_type,
        "prompt_text": _PRACTICE_TYPE_MAP.get(practice_type, "请用自己的话解释这个概念。"),
        "minimum_answer_hint": "至少写一句话",
        "evaluation_dimensions": ["correctness", "clarity", "naturalness"],
    }


def static_feedback_fallback() -> dict:
    """Fallback: return static feedback when AI fails."""
    return {
        "correctness": "medium",
        "clarity": "medium",
        "naturalness": "medium",
        "issues": ["反馈生成暂时不可用"],
        "suggestions": ["继续尝试用自己的话表达"],
        "recommended_answer": "",
        "expression_skeleton": "",
    }
