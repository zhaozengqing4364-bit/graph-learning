"""Article generator - produce article_body for existing nodes (backward compat)."""

from backend.agents.base import AIClient, validate_ai_output

_ARTICLE_SCHEMA = {
    "type": "object",
    "properties": {
        "article_body": {"type": "string"},
        "concept_refs": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["article_body", "concept_refs"],
}

_ARTICLE_SYSTEM_PROMPT = """你是一个知识内容写作者。你的任务是为知识节点撰写一篇结构化的文章内容（article_body）。

## 要求
1. 200-500 字的连贯文章，像维基百科或教材段落一样流畅
2. 内容必须包含：概念定义、核心原理、至少一个具体示例
3. 如有常见误解或应用场景，一并融入文章
4. 文中出现的其他知识节点，用 [[节点名称]] 语法标记（双层方括号包裹）
5. concept_refs 字段列出文中引用的所有节点名称列表

## 输入信息
- 节点名称：{node_name}
- 节点摘要：{node_summary}
- 示例：{examples}
- 常见误解：{misconceptions}
- 应用场景：{applications}
- 可引用的关联概念：{related_concepts}

注意：只引用 related_concepts 中列出的概念名，使用 [[概念名]] 标记。"""


async def generate_article_for_node(
    node_name: str,
    node_summary: str,
    node_examples: list[str],
    node_misconceptions: list[str],
    node_applications: list[str],
    related_concepts: list[str],
    model: str | None = None,
) -> dict | None:
    """Generate article_body for an existing node.

    Returns {"article_body": "...", "concept_refs": ["..."]} or None on failure.
    """
    system = _ARTICLE_SYSTEM_PROMPT
    system = system.replace("{node_name}", node_name)
    system = system.replace("{node_summary}", node_summary or "无摘要")
    system = system.replace("{examples}", "; ".join(node_examples) if node_examples else "无")
    system = system.replace("{misconceptions}", "; ".join(node_misconceptions) if node_misconceptions else "无")
    system = system.replace("{applications}", "; ".join(node_applications) if node_applications else "无")
    system = system.replace("{related_concepts}", ", ".join(related_concepts) if related_concepts else "无")

    user = f"请为「{node_name}」撰写一篇结构化的学习文章。"

    client = AIClient(model=model)
    result = await client.call(system, user, output_schema=_ARTICLE_SCHEMA)
    return validate_ai_output(result, required_fields=["article_body"], field_types={"article_body": str})
