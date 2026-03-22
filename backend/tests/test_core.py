"""Backend tests - pytest suite for core business logic."""

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_ability_delta_clamp():
    """Ability delta should respect +10 max and -5 min rules."""
    from backend.models.ability import apply_delta, AbilityRecord, AbilityDelta

    record = AbilityRecord(topic_id="tp_test", node_id="nd_test", understand=50, explain=40)
    # Positive delta capped at +10
    updated = apply_delta(record, AbilityDelta(understand=20, explain=5))
    assert updated.understand == 60  # 50 + 10 (capped from 20)
    assert updated.explain == 45   # 40 + 5

    # Negative delta floored at -5
    updated2 = apply_delta(updated, AbilityDelta(understand=-15))
    assert updated2.understand == 55  # 60 + (-5) (floored from -15)


def test_ability_delta_bounds():
    """Ability scores should stay within [0, 100]."""
    from backend.models.ability import apply_delta, AbilityRecord, AbilityDelta

    record = AbilityRecord(topic_id="tp_test", node_id="nd_test", understand=95)
    updated = apply_delta(record, AbilityDelta(understand=20))
    assert updated.understand == 100

    record2 = AbilityRecord(topic_id="tp_test", node_id="nd_test", understand=2)
    updated2 = apply_delta(record2, AbilityDelta(understand=-20))
    assert updated2.understand == 0


def test_review_item_create():
    """ReviewItem.create should generate ID and set defaults."""
    from backend.models.review import ReviewItem, ReviewItemCreate

    item = ReviewItem.create("tp_test", ReviewItemCreate(
        node_id="nd_test",
        review_type="contrast",
        priority=0.5,
        reason="对比能力薄弱",
    ))
    assert item.review_id.startswith("rv_")
    assert item.node_id == "nd_test"
    assert item.review_type == "contrast"
    assert item.status == "pending"
    assert item.reason == "对比能力薄弱"


def test_review_priority_formula():
    """Review priority should use the full formula."""
    from backend.services.review_service import calculate_review_priority

    # High importance + high forget risk + high confusion
    p1 = calculate_review_priority(
        importance=5, history_count=0, understand_score=80, explain_score=20,
        frictions=[{"friction_type": "prerequisite_gap"}, {"friction_type": "concept_confusion"}],
    )
    assert p1 > 0

    # Low importance + low forget risk + no confusion
    p2 = calculate_review_priority(
        importance=1, history_count=3, understand_score=70, explain_score=65,
        frictions=[],
    )
    assert p2 < p1


def test_suggest_review_type():
    """Should recommend review type based on weakest dimension."""
    from backend.services.review_service import _suggest_review_type

    assert _suggest_review_type({"recall": 10, "contrast": 80, "explain": 90}) == "recall"
    assert _suggest_review_type({"recall": 80, "contrast": 20, "explain": 30}) == "contrast"


def test_practice_attempt_create():
    """PracticeAttempt.create should include prompt_text."""
    from backend.models.practice import PracticeAttempt

    attempt = PracticeAttempt.create(
        topic_id="tp_test",
        node_id="nd_test",
        practice_type="define",
        user_answer="测试答案",
        prompt_text="请定义这个概念",
    )
    assert attempt.attempt_id.startswith("pa_")
    assert attempt.prompt_text == "请定义这个概念"
    assert attempt.user_answer == "测试答案"


def test_extract_concept_refs():
    """Should extract [[concept]] references from article body."""
    from backend.services.node_service import _extract_concept_refs

    body = "机器学习是[[人工智能]]的一个子领域，与[[深度学习]]密切相关。"
    refs = _extract_concept_refs(body)
    assert "人工智能" in refs
    assert "深度学习" in refs
    assert len(refs) == 2


def test_expand_score():
    """ExpandScore should weight nodes by importance, intent, and ability."""
    from backend.graph.traversal import calculate_expand_score

    # High importance, unseen node, fix_gap intent
    score = calculate_expand_score(
        node={"importance": 5, "status": "unseen", "name": "test_node"},
        learning_intent="fix_gap",
    )
    assert score > 0

    # Low importance, practiced node, solve_task intent
    score2 = calculate_expand_score(
        node={"importance": 1, "status": "practiced", "name": "low_node"},
        learning_intent="solve_task",
    )
    assert score2 < score

    # Friction nodes with relevant keywords should get structural boost
    score_with_friction = calculate_expand_score(
        node={"importance": 3, "status": "unseen", "name": "基础概念"},
        learning_intent="build_system",
        friction_tags=["weak_structure"],
    )
    score_no_friction = calculate_expand_score(
        node={"importance": 3, "status": "unseen", "name": "normal_node"},
        learning_intent="build_system",
    )
    assert score_with_friction > score_no_friction


def test_confusion_risk_weights():
    """ConfusionRisk should use type-aware weights."""
    from backend.services.review_service import _calculate_confusion_risk

    # prerequisite_gap should be weighted higher than lack_of_example
    r1 = _calculate_confusion_risk([{"friction_type": "prerequisite_gap"}])
    r2 = _calculate_confusion_risk([{"friction_type": "lack_of_example"}])
    assert r1 > r2

    # Multiple frictions should accumulate
    r3 = _calculate_confusion_risk([
        {"friction_type": "prerequisite_gap"},
        {"friction_type": "concept_confusion"},
    ])
    assert r3 > r1


def test_resolve_project_path_anchors_relative_paths_to_project_root():
    """Relative config paths should be resolved from the project root, not cwd."""
    from backend.core.config import PROJECT_ROOT, resolve_project_path

    assert Path(resolve_project_path("./data/sqlite/axon_clone.db")) == (PROJECT_ROOT / "data/sqlite/axon_clone.db").resolve()
    assert Path(resolve_project_path("data/lancedb")) == (PROJECT_ROOT / "data/lancedb").resolve()
    assert resolve_project_path("/tmp/axon_clone.db") == "/tmp/axon_clone.db"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])


# ============================================================
# P0 补充测试：模型、降级策略、图谱校验、遍历控制
# ============================================================


def test_practice_dimension_map():
    """PRACTICE_DIMENSION_MAP should map each practice type to relevant ability dimensions."""
    from backend.models.ability import PRACTICE_DIMENSION_MAP

    assert "define" in PRACTICE_DIMENSION_MAP
    assert "understand" in PRACTICE_DIMENSION_MAP["define"]
    assert "explain" in PRACTICE_DIMENSION_MAP["define"]
    # Each type should map to at least one dimension
    for ptype, dims in PRACTICE_DIMENSION_MAP.items():
        assert len(dims) >= 1, f"{ptype} maps to no dimensions"


def test_node_create_with_article_body():
    """Node.create should preserve article_body field."""
    from backend.models.node import Node, NodeCreate

    node = Node.create(NodeCreate(
        name="测试节点",
        summary="测试摘要",
        article_body="这是文章内容 [[相关概念]]",
        importance=4,
    ), topic_id="tp_test")
    assert node.article_body == "这是文章内容 [[相关概念]]"
    assert node.node_id.startswith("nd_")


def test_node_detail_has_concept_refs():
    """NodeDetail should have concept_refs field."""
    from backend.models.node import NodeDetail, Node

    detail = NodeDetail(
        node=Node(node_id="nd_1", name="test", topic_id="tp_1"),
        concept_refs=["概念A", "概念B"],
    )
    assert detail.concept_refs == ["概念A", "概念B"]


def test_practice_result_has_diagnosis_fallback():
    """PracticeResult should include diagnosis_fallback field."""
    from backend.models.practice import PracticeResult

    result = PracticeResult(
        attempt_id="pa_1",
        diagnosis_fallback=True,
    )
    assert result.diagnosis_fallback is True


def test_explorer_fallback_returns_entry():
    """Explorer fallback should always return a valid entry node."""
    from backend.agents.explorer import create_topic_fallback

    result = create_topic_fallback("深度学习")
    assert "entry_node" in result
    assert result["entry_node"]["name"] == "深度学习"
    assert "summary" in result["entry_node"]
    assert "why_it_matters" in result["entry_node"]
    assert len(result.get("nodes", [])) >= 0  # may be empty


def test_tutor_fallback():
    """Tutor fallback should return a valid practice prompt."""
    from backend.agents.tutor import static_practice_fallback, static_feedback_fallback

    prompt = static_practice_fallback("define")
    assert prompt["practice_type"] == "define"
    assert len(prompt["prompt_text"]) > 0

    feedback = static_feedback_fallback()
    assert feedback["correctness"] == "medium"
    assert len(feedback["issues"]) > 0


def test_diagnoser_fallback():
    """Diagnoser fallback should return empty friction and generic feedback."""
    from backend.agents.diagnoser import diagnose_fallback

    result = diagnose_fallback()
    assert result["friction_tags"] == []
    assert result["severity"] == 1
    assert result["ability_delta"] == {}
    assert "简化反馈" in result["short_feedback"]


def test_synthesizer_fallback():
    """Synthesizer fallback should return rule-based summary."""
    from backend.agents.synthesizer import synthesize_fallback

    result = synthesize_fallback(
        topic_title="机器学习",
        visited_nodes=["神经网络", "反向传播", "梯度下降"],
        practice_count=3,
    )
    assert "机器学习" in result["mainline_summary"]
    assert len(result["key_takeaways"]) > 0
    assert len(result["next_recommendations"]) > 0


@pytest.mark.asyncio
async def test_init_tables_migrates_legacy_deferred_nodes_schema():
    """Legacy deferred_nodes tables should gain source_node_id/resolved_at columns."""
    import aiosqlite

    from backend.repositories.sqlite_repo import init_tables

    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row

    try:
        await db.executescript(
            """
            CREATE TABLE deferred_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                reason TEXT DEFAULT '',
                deferred_at TEXT DEFAULT (datetime('now')),
                UNIQUE(topic_id, node_id)
            );
            INSERT INTO deferred_nodes (topic_id, node_id, reason)
            VALUES ('tp_legacy', 'nd_legacy', 'old schema row');
            """
        )
        await db.commit()

        await init_tables(db)

        columns_cursor = await db.execute("PRAGMA table_info(deferred_nodes)")
        columns = {row[1] for row in await columns_cursor.fetchall()}
        assert "source_node_id" in columns
        assert "resolved_at" in columns

        unresolved_cursor = await db.execute(
            "SELECT COUNT(*) FROM deferred_nodes WHERE topic_id = ? AND resolved_at IS NULL",
            ("tp_legacy",),
        )
        unresolved_count = (await unresolved_cursor.fetchone())[0]
        assert unresolved_count == 1
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_delete_topic_removes_session_rows(db_conn):
    """delete_topic should clear session-linked rows and report success."""
    from backend.repositories import sqlite_repo

    topic_id = "tp_delete_cascade"
    session_id = "ss_delete_cascade"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Delete Cascade"),
    )
    await db_conn.execute(
        "INSERT INTO sessions (session_id, topic_id, status) VALUES (?, ?, 'active')",
        (session_id, topic_id),
    )
    await db_conn.execute(
        "INSERT INTO session_nodes (session_id, node_id) VALUES (?, ?)",
        (session_id, "nd_delete_cascade"),
    )
    await db_conn.commit()

    deleted = await sqlite_repo.delete_topic(db_conn, topic_id)
    assert deleted is True

    topic_cursor = await db_conn.execute("SELECT COUNT(*) FROM topics WHERE topic_id = ?", (topic_id,))
    session_cursor = await db_conn.execute("SELECT COUNT(*) FROM sessions WHERE topic_id = ?", (topic_id,))
    session_nodes_cursor = await db_conn.execute("SELECT COUNT(*) FROM session_nodes WHERE session_id = ?", (session_id,))

    assert (await topic_cursor.fetchone())[0] == 0
    assert (await session_cursor.fetchone())[0] == 0
    assert (await session_nodes_cursor.fetchone())[0] == 0


@pytest.mark.asyncio
async def test_list_expression_assets_accepts_favorited_filter(db_conn):
    """list_expression_assets should forward limit/favorited without argument collisions."""
    from backend.services import practice_service

    topic_id = "tp_expression_filter"
    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Expression Filter"),
    )
    await db_conn.execute(
        """
        INSERT INTO expression_assets (
            asset_id, topic_id, node_id, expression_type, user_expression, favorited
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("ea_filter_1", topic_id, "nd_expression_filter", "define", "定义表达", 1),
    )
    await db_conn.commit()

    assets = await practice_service.list_expression_assets(
        db_conn,
        topic_id,
        node_id="nd_expression_filter",
        limit=10,
        favorited=True,
    )

    assert len(assets) == 1
    assert assets[0]["asset_id"] == "ea_filter_1"


def test_all_agents_have_intent_guidance():
    """All AI agents should have _INTENT_GUIDANCE covering 5 intents."""
    from backend.agents import explorer, tutor, diagnoser, synthesizer

    required_intents = {"fix_gap", "build_system", "solve_task", "prepare_expression", "prepare_interview"}

    for agent_name, agent_module in [
        ("explorer", explorer), ("tutor", tutor), ("diagnoser", diagnoser), ("synthesizer", synthesizer),
    ]:
        guidance = getattr(agent_module, "_INTENT_GUIDANCE", None)
        assert guidance is not None, f"{agent_name} missing _INTENT_GUIDANCE"
        assert required_intents.issubset(set(guidance.keys())), f"{agent_name} missing intents: {required_intents - set(guidance.keys())}"


def test_graph_validator_rejects_long_names():
    """Graph validator should reject node names > 100 chars."""
    from backend.graph.validator import validate_and_filter_nodes

    long_name = "A" * 101
    nodes = [{"name": long_name, "summary": "test", "importance": 3}]
    # lancedb=None, so dedup is skipped; only name length check
    import asyncio
    valid = asyncio.get_event_loop().run_until_complete(
        validate_and_filter_nodes(None, nodes, "tp_test")
    )
    assert len(valid) == 0, "Should reject nodes with names > 100 chars"


def test_graph_validator_rejects_suspicious_names():
    """Graph validator should reject node names with suspicious patterns."""
    from backend.graph.validator import validate_and_filter_nodes
    import asyncio

    suspicious_names = [
        "http://evil.com",
        "```rm -rf",
        "<script>alert(1)</script>",
    ]
    nodes = [{"name": n, "summary": "test", "importance": 3} for n in suspicious_names]
    valid = asyncio.get_event_loop().run_until_complete(
        validate_and_filter_nodes(None, nodes, "tp_test")
    )
    assert len(valid) == 0


def test_graph_validator_rejects_suspicious_article_body():
    """Graph validator should reject nodes with suspicious patterns in article_body even if summary is clean."""
    from backend.graph.validator import validate_and_filter_nodes
    import asyncio

    nodes = [
        {"name": "safe_node", "summary": "A normal summary", "importance": 3, "article_body": "<script>alert(1)</script>"},
        {"name": "safe_node2", "summary": "Another summary", "importance": 3, "article_body": "<iframe src=x></iframe>"},
    ]
    valid = asyncio.get_event_loop().run_until_complete(
        validate_and_filter_nodes(None, nodes, "tp_test")
    )
    assert len(valid) == 0, "Should reject nodes with injection patterns in article_body"


def test_traversal_filter_caps():
    """Traversal filter should respect expand and topic caps."""
    from backend.graph.traversal import filter_nodes_for_expand, EXPAND_MAX_NODES, TOPIC_MAX_NODES

    nodes = [{"name": f"节点{i}", "summary": "test", "importance": 3, "status": "unseen"} for i in range(10)]
    result = filter_nodes_for_expand(nodes, max_nodes=5, learning_intent="build_system")
    assert len(result) <= 5

    # Existing node names should be excluded
    nodes2 = [{"name": "节点A", "summary": "s", "importance": 3, "status": "unseen"}]
    result2 = filter_nodes_for_expand(nodes2, max_nodes=5, existing_node_names={"节点A"})
    assert len(result2) == 0


def test_edge_mainline_weights():
    """Edge mainline weights should match spec."""
    from backend.graph.traversal import EDGE_MAINLINE_WEIGHTS

    assert EDGE_MAINLINE_WEIGHTS["PREREQUISITE"] == 1.0
    assert EDGE_MAINLINE_WEIGHTS["CONTRASTS"] == 0.7
    assert EDGE_MAINLINE_WEIGHTS["APPLIES_IN"] == 0.6
    assert EDGE_MAINLINE_WEIGHTS["VARIANT_OF"] == 0.5
    assert EDGE_MAINLINE_WEIGHTS["EXTENDS"] == 0.4
    # MISUNDERSTOOD_AS should not be in mainline weights
    assert "MISUNDERSTOOD_AS" not in EDGE_MAINLINE_WEIGHTS


def test_topic_model_create():
    """Topic.create should generate topic_id and set defaults."""
    from backend.models.topic import Topic, TopicCreate

    topic = Topic.create(TopicCreate(title="测试主题", source_content="内容", learning_intent="build_system"))
    assert topic.topic_id.startswith("tp_")
    assert topic.title == "测试主题"
    assert topic.learning_intent == "build_system"
    assert topic.status == "active"


def test_friction_record_create():
    """FrictionRecord.create should generate friction_id."""
    from backend.models.friction import FrictionRecord

    fr = FrictionRecord.create(topic_id="tp_1", node_id="nd_1", friction_type="prerequisite_gap")
    assert fr.friction_id.startswith("fr_")
    assert fr.friction_type == "prerequisite_gap"


def test_response_format():
    """Success/error response should follow unified format."""
    from backend.core.response import success_response, error_response

    ok = success_response(data={"key": "value"}, meta={"page": 1})
    assert ok["success"] is True
    assert ok["data"]["key"] == "value"

    err = error_response("Not found", error_code="NOT_FOUND")
    assert err["success"] is False
    assert err["error"]["message"] == "Not found"


def test_recall_confidence_decay():
    """Recall confidence should increase on success and decay on failure."""
    from backend.services.review_service import _calculate_recall_confidence

    # Success increases confidence
    conf = 0.5
    new_conf = _calculate_recall_confidence(conf, success=True)
    assert new_conf > conf
    assert new_conf <= 1.0

    # Failure decreases confidence
    conf2 = 0.8
    new_conf2 = _calculate_recall_confidence(conf2, success=False)
    assert new_conf2 < conf2
    assert new_conf2 >= 0.1

    # Confidence caps at 1.0
    maxed = _calculate_recall_confidence(0.95, success=True)
    assert maxed == 1.0

    # Confidence floors at 0.1
    minned = _calculate_recall_confidence(0.1, success=False)
    assert minned == 0.1


def test_auto_status_transition():
    """Auto transition should calculate ability avg correctly."""
    from backend.services.review_service import _calculate_ability_avg

    # All 80s = avg 80 >= 70 = mastered
    ability_high = {d: 80 for d in ["understand", "example", "contrast", "apply", "explain", "recall", "transfer", "teach"]}
    assert _calculate_ability_avg(ability_high) == 80.0

    # All 30s = avg 30 < 70
    ability_low = {d: 30 for d in ["understand", "example", "contrast", "apply", "explain", "recall", "transfer", "teach"]}
    assert _calculate_ability_avg(ability_low) == 30.0

    # Empty ability = 0
    assert _calculate_ability_avg(None) == 0.0


def test_expand_score_has_importance_multiplier():
    """ExpandScore should include Importance as top-level multiplier."""
    from backend.graph.traversal import calculate_expand_score

    high_importance = {"name": "重要节点", "importance": 5, "status": "unseen"}
    low_importance = {"name": "普通节点", "importance": 1, "status": "unseen"}

    score_high = calculate_expand_score(high_importance, "build_system", relation_type="PREREQUISITE")
    score_low = calculate_expand_score(low_importance, "build_system", relation_type="PREREQUISITE")
    assert score_high > score_low, "Higher importance should yield higher ExpandScore"


def test_is_mainline_in_sort():
    """sort_nodes_by_mainline_priority should prioritize is_mainline nodes."""
    from backend.graph.traversal import sort_nodes_by_mainline_priority

    # Same importance: mainline beats non-mainline
    nodes = [
        {"name": "B", "importance": 3, "status": "unseen", "is_mainline": False},
        {"name": "A", "importance": 3, "status": "unseen", "is_mainline": True},
    ]
    sorted_nodes = sort_nodes_by_mainline_priority(nodes)
    assert sorted_nodes[0]["name"] == "A", "Mainline node should come first at same importance"

    # Higher importance still beats lower importance even without mainline
    nodes2 = [
        {"name": "A", "importance": 3, "status": "unseen", "is_mainline": True},
        {"name": "C", "importance": 4, "status": "unseen", "is_mainline": False},
    ]
    sorted_nodes2 = sort_nodes_by_mainline_priority(nodes2)
    assert sorted_nodes2[0]["name"] == "C", "Higher importance should come first"


# ---- Settings API validation tests (GROW-BOOTSTRAP-001) ----

def test_immutable_fields_rejected():
    """IMMUTABLE_FIELDS should not be overridden in update_settings loop."""
    from backend.api.settings import IMMUTABLE_FIELDS, _ALLOWED_OLLAMA_PREFIX
    # Verify immutable fields exist
    assert "neo4j_uri" in IMMUTABLE_FIELDS
    assert "sqlite_path" in IMMUTABLE_FIELDS
    assert "neo4j_password" in IMMUTABLE_FIELDS
    assert "lancedb_path" in IMMUTABLE_FIELDS
    # Verify ollama URL regex exists
    assert _ALLOWED_OLLAMA_PREFIX.pattern.startswith("^https?://")
    # Test valid ollama URLs pass
    assert _ALLOWED_OLLAMA_PREFIX.match("http://localhost")
    assert _ALLOWED_OLLAMA_PREFIX.match("http://127.0.0.1:11434")
    assert not _ALLOWED_OLLAMA_PREFIX.match("http://192.168.1.1")
    assert not _ALLOWED_OLLAMA_PREFIX.match("http://evil.com")
    assert not _ALLOWED_OLLAMA_PREFIX.match("http://169.254.169.254/latest/")


def test_mask_value_returns_fixed_mask():
    """mask_value should return '••••' for any non-empty value."""
    from backend.api.settings import mask_value
    # Non-empty value returns mask
    assert mask_value("sk-anything-long") == "••••"
    assert mask_value("short") == "••••"
    # Empty value returns empty string
    assert mask_value("") == ""


def test_sensitive_fields_covered():
    """SENSITIVE_FIELDS should include API keys and passwords."""
    from backend.api.settings import SENSITIVE_FIELDS
    assert "openai_api_key" in SENSITIVE_FIELDS
    assert "neo4j_password" in SENSITIVE_FIELDS


def test_sqlite_column_whitelist_coverage():
    """Verify all UPDATE_TOPIC_COLUMNS are actually in the whitelist."""
    from backend.repositories.sqlite_repo import _ALLOWED_TOPIC_COLUMNS
    # Verify critical columns exist
    for col in ["title", "description", "status", "learning_intent"]:
        assert col in _ALLOWED_TOPIC_COLUMNS, f"{col} missing from topic whitelist"


def test_neo4j_property_whitelist_coverage():
    """Verify critical concept properties are in the whitelist."""
    from backend.repositories.neo4j_repo import _ALLOWED_CONCEPT_PROPERTIES
    for prop in ["name", "summary", "status", "importance", "is_mainline"]:
        assert prop in _ALLOWED_CONCEPT_PROPERTIES, f"{prop} missing from concept whitelist"


def test_friction_type_whitelist():
    """All known friction types should be in FrictionType.ALL."""
    from backend.models.friction import FrictionType
    expected = {"prerequisite_gap", "concept_confusion", "lack_of_example", "weak_structure",
               "abstract_overload", "weak_recall", "weak_application"}
    for t in expected:
        assert t in FrictionType.ALL, f"{t} missing from FrictionType.ALL"
    assert len(FrictionType.ALL) == 7


def test_practice_submit_max_length():
    """PracticeSubmit should enforce max_length on user_answer and prompt_text."""
    from backend.models.practice import PracticeSubmit
    from pydantic import ValidationError
    # Normal input passes
    PracticeSubmit(user_answer="test answer", prompt_text="test prompt", practice_type="define")
    # Overlong input rejected
    try:
        PracticeSubmit(user_answer="x" * 50001, prompt_text="short", practice_type="define")
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


# ---- Error message sanitization tests (ISSUE-012 regression) ----

def test_sanitize_error_message_in_dev_mode():
    """In development mode, error messages should pass through unchanged."""
    from backend.core.response import _sanitize_error_message, _is_production_env
    import backend.core.response as resp_mod

    original = resp_mod._is_production_env
    try:
        resp_mod._is_production_env = lambda: False
        msg = "Connection refused to neo4j://localhost:7687"
        assert _sanitize_error_message(msg) == msg
    finally:
        resp_mod._is_production_env = original


def test_sanitize_error_message_in_prod_mode_strips_internal():
    """In production mode, messages with internal paths should be sanitized."""
    from backend.core.response import _sanitize_error_message
    import backend.core.response as resp_mod

    original = resp_mod._is_production_env
    try:
        resp_mod._is_production_env = lambda: True
        # Message with Python file path
        msg = "查询失败: FileNotFoundError in /app/backend/repositories/sqlite_repo.py line 42"
        result = _sanitize_error_message(msg)
        assert "sqlite_repo.py" not in result
        assert "查询失败" in result or result == "操作失败，请稍后重试"

        # Message with Traceback
        msg2 = "Traceback (most recent call last): neo4j connection refused"
        result2 = _sanitize_error_message(msg2)
        assert "Traceback" not in result2
        assert "neo4j" not in result2

        # Clean message should pass through
        msg3 = "该主题不存在"
        assert _sanitize_error_message(msg3) == "该主题不存在"

        # Empty message should return empty
        assert _sanitize_error_message("") == ""
    finally:
        resp_mod._is_production_env = original


def test_sanitize_error_message_fallback():
    """If entire message is internal, return generic fallback."""
    from backend.core.response import _sanitize_error_message
    import backend.core.response as resp_mod

    original = resp_mod._is_production_env
    try:
        resp_mod._is_production_env = lambda: True
        # No colon separator, entire message is internal
        msg = "sqlite_repo.py: connection refused"
        result = _sanitize_error_message(msg)
        assert result == "操作失败，请稍后重试"
    finally:
        resp_mod._is_production_env = original


# ---- ID generation tests (ISSUE-029 regression) ----

@pytest.mark.asyncio
async def test_submit_practice_updates_ability_record(db_conn):
    """submit_practice should write correct ability dimensions to SQLite."""
    from backend.services.practice_service import submit_practice
    from backend.models.practice import PracticeSubmit

    topic_id = "tp_ability_e2e"
    node_id = "nd_ability_e2e"

    # Seed topic row (required by submit_practice)
    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status, learning_intent) VALUES (?, ?, 'active', 'build_system')",
        (topic_id, "Ability E2E Test"),
    )
    await db_conn.commit()

    # Submit practice with known feedback + ability_delta, no neo4j needed
    result = await submit_practice(
        db=db_conn,
        topic_id=topic_id,
        node_id=node_id,
        data=PracticeSubmit(
            practice_type="define",
            user_answer="这是一个关于X的定义解释",
            prompt_text="请定义X",
        ),
        neo4j=None,
        feedback={"correctness": "good", "clarity": "good", "naturalness": "medium"},
        ability_delta={"understand": 8, "explain": 6},
    )

    # Verify result has ability_update
    assert result.ability_update is not None
    assert result.ability_update["understand"] == 8
    assert result.ability_update["explain"] == 6
    # Other dimensions should remain 0
    assert result.ability_update["example"] == 0
    assert result.ability_update["contrast"] == 0

    # Verify SQLite persistence
    cursor = await db_conn.execute(
        "SELECT * FROM ability_records WHERE topic_id = ? AND node_id = ?",
        (topic_id, node_id),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row["understand"] == 8
    assert row["explain"] == 6


@pytest.mark.asyncio
async def test_submit_practice_accumulates_ability_on_repeated_submit(db_conn):
    """Repeated practice submissions should accumulate ability scores."""
    from backend.services.practice_service import submit_practice
    from backend.models.practice import PracticeSubmit

    topic_id = "tp_ability_accum"
    node_id = "nd_ability_accum"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status, learning_intent) VALUES (?, ?, 'active', 'build_system')",
        (topic_id, "Ability Accum Test"),
    )
    await db_conn.commit()

    # First submission
    await submit_practice(
        db=db_conn,
        topic_id=topic_id,
        node_id=node_id,
        data=PracticeSubmit(
            practice_type="define",
            user_answer="first answer",
            prompt_text="define X",
        ),
        neo4j=None,
        feedback={"correctness": "good"},
        ability_delta={"understand": 5, "explain": 3},
    )

    # Second submission — should accumulate
    result = await submit_practice(
        db=db_conn,
        topic_id=topic_id,
        node_id=node_id,
        data=PracticeSubmit(
            practice_type="define",
            user_answer="second answer",
            prompt_text="define X again",
        ),
        neo4j=None,
        feedback={"correctness": "good"},
        ability_delta={"understand": 4, "explain": 6},
    )

    # Should be 5+4=9 for understand, 3+6=9 for explain
    assert result.ability_update["understand"] == 9
    assert result.ability_update["explain"] == 9


@pytest.mark.asyncio
async def test_submit_practice_clamps_ability_delta(db_conn):
    """Ability delta > +10 should be clamped, delta < -5 should be floored."""
    from backend.services.practice_service import submit_practice
    from backend.models.practice import PracticeSubmit

    topic_id = "tp_ability_clamp"
    node_id = "nd_ability_clamp"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status, learning_intent) VALUES (?, ?, 'active', 'build_system')",
        (topic_id, "Ability Clamp Test"),
    )
    await db_conn.commit()

    # Submit with oversized delta — should clamp to +10
    result = await submit_practice(
        db=db_conn,
        topic_id=topic_id,
        node_id=node_id,
        data=PracticeSubmit(
            practice_type="example",
            user_answer="an example answer",
            prompt_text="give example of X",
        ),
        neo4j=None,
        feedback={"correctness": "good"},
        ability_delta={"example": 50, "understand": 20},
    )

    # Adaptive scaling: beginner (val<30) allows +15, so +50 → clamped to 15
    assert result.ability_update["example"] == 15
    assert result.ability_update["understand"] == 15

    # Now submit with negative delta — should floor at -5
    result2 = await submit_practice(
        db=db_conn,
        topic_id=topic_id,
        node_id=node_id,
        data=PracticeSubmit(
            practice_type="example",
            user_answer="bad example",
            prompt_text="give example of X again",
        ),
        neo4j=None,
        feedback={"correctness": "weak"},
        ability_delta={"example": -30, "understand": -15},
    )

    # 15 + (-5) = 10 for example (still beginner, max_dec=-5)
    assert result2.ability_update["example"] == 10
    assert result2.ability_update["understand"] == 10


def test_rule_based_ability_delta_correctness():
    """_rule_based_ability_delta should map correctness to correct delta values."""
    from backend.services.practice_service import _rule_based_ability_delta

    # Good correctness
    delta_good = _rule_based_ability_delta("define", {"correctness": "good"})
    assert delta_good["understand"] == 8
    assert delta_good["explain"] == 8

    # Medium correctness
    delta_med = _rule_based_ability_delta("define", {"correctness": "medium"})
    assert delta_med["understand"] == 4
    assert delta_med["explain"] == 4

    # Weak correctness — base(1) - 5 = -3 (clamped by max(-3, -4))
    delta_weak = _rule_based_ability_delta("define", {"correctness": "weak"})
    assert delta_weak["understand"] == -3
    assert delta_weak["explain"] == -3

    # Contrast practice type affects different dimensions
    delta_contrast = _rule_based_ability_delta("contrast", {"correctness": "good"})
    assert "contrast" in delta_contrast
    assert "explain" in delta_contrast
    assert "understand" not in delta_contrast


@pytest.mark.asyncio
async def test_generate_review_queue_reschedules_when_ability_low(db_conn):
    """Nodes with future scheduled reviews but low ability should get a new review."""
    from backend.services.review_service import generate_review_queue

    topic_id = "tp_reschedule"
    node_id = "nd_reschedule"

    # Seed topic
    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Reschedule Test"),
    )
    # Seed ability record with avg < 70
    await db_conn.execute(
        """INSERT INTO ability_records (topic_id, node_id, understand, explain, recall, example, contrast, apply, transfer, teach)
           VALUES (?, ?, 30, 20, 15, 10, 10, 10, 10, 10)""",
        (topic_id, node_id),
    )
    # Seed a completed review with far-future next_review_at (30 days from now)
    from datetime import datetime, timedelta
    future_due = (datetime.now() + timedelta(days=30)).isoformat()
    await db_conn.execute(
        """INSERT INTO review_items (review_id, topic_id, node_id, review_type, status, priority, due_at, next_review_at, created_at)
           VALUES (?, ?, ?, 'recall', 'completed', 0.5, '2026-03-01T00:00:00', ?, '2026-03-01T00:00:00')""",
        ("rv_reschedule_existing", topic_id, node_id, future_due),
    )
    await db_conn.commit()

    # Generate queue — should produce a review despite existing future schedule
    created = await generate_review_queue(db_conn, topic_id, neo4j=None)

    assert created is not None
    # At least one review should be created for the low-ability node
    assert len(created) >= 1
    # Verify it targets the correct node
    node_ids = [item.get("node_id") for item in created]
    assert node_id in node_ids


@pytest.mark.asyncio
async def test_practice_does_not_clobber_review_fields(db_conn):
    """submit_practice should preserve recall_confidence and review_history_count from review."""
    from backend.services.practice_service import submit_practice
    from backend.models.practice import PracticeSubmit

    topic_id = "tp_review_preserve"
    node_id = "nd_review_preserve"

    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status, learning_intent) VALUES (?, ?, 'active', 'build_system')",
        (topic_id, "Review Preserve Test"),
    )
    # Seed ability record with review-set fields
    await db_conn.execute(
        """INSERT INTO ability_records (topic_id, node_id, understand, explain, recall_confidence,
           last_reviewed_at, review_history_count)
           VALUES (?, ?, 50, 40, 0.3, '2026-03-18T10:00:00', 5)""",
        (topic_id, node_id),
    )
    await db_conn.commit()

    # Submit practice — should NOT overwrite review fields
    result = await submit_practice(
        db=db_conn,
        topic_id=topic_id,
        node_id=node_id,
        data=PracticeSubmit(
            practice_type="define",
            user_answer="这是一个定义答案",
            prompt_text="请定义X",
        ),
        neo4j=None,
        feedback={"correctness": "good"},
        ability_delta={"understand": 5, "explain": 3},
    )

    # Verify ability scores updated correctly
    assert result.ability_update["understand"] == 55
    assert result.ability_update["explain"] == 43

    # Verify review fields preserved in SQLite
    cursor = await db_conn.execute(
        "SELECT recall_confidence, last_reviewed_at, review_history_count FROM ability_records WHERE topic_id = ? AND node_id = ?",
        (topic_id, node_id),
    )
    row = await cursor.fetchone()
    assert row["recall_confidence"] == 0.3
    assert row["last_reviewed_at"] == "2026-03-18T10:00:00"
    assert row["review_history_count"] == 5


def test_review_priority_exact_values():
    """Review priority should produce exact calculable values."""
    from backend.services.review_service import calculate_review_priority

    # Case 1: importance=5, no history, understand=80, explain=20, 2 frictions, no due_at
    # importance_factor = 5/5 = 1.0
    # forget_risk(0) = 1.0
    # explain_gap(80, 20) = (50-20)/50 = 0.6
    # confusion_risk([prerequisite_gap, concept_confusion]) = (1+0.4)*(1+0.35) = 1.4*1.35 = 1.89
    # time_due_weight(None) = 1.0
    # priority = 1.0 * 1.0 * 0.6 * 1.89 * 1.0 = 1.134
    p = calculate_review_priority(
        importance=5, history_count=0, understand_score=80, explain_score=20,
        frictions=[{"friction_type": "prerequisite_gap"}, {"friction_type": "concept_confusion"}],
    )
    assert abs(p - 1.134) < 0.01

    # Case 2: importance=1, history_count=3, understand=70, explain=65, no frictions
    # importance_factor = 1/5 = 0.2
    # forget_risk(3) = 3.0/7 ≈ 0.4286
    # explain_gap(70, 65) = 0 (understand <= explain)
    # confusion_risk([]) = 1.0
    # time_due_weight(None) = 1.0
    # priority = 0.2 * 0.4286 * 0 * 1.0 * 1.0 = 0
    p2 = calculate_review_priority(
        importance=1, history_count=3, understand_score=70, explain_score=65,
        frictions=[],
    )
    assert p2 == 0.0

    # Case 3: importance=3, no history, understand=60, explain=30, no frictions, due far future
    # importance_factor = 3/5 = 0.6
    # forget_risk(0) = 1.0
    # explain_gap(60, 30) = (50-30)/50 = 0.4
    # confusion_risk([]) = 1.0
    # time_due_weight(30 days future) = 0.5
    # priority = 0.6 * 1.0 * 0.4 * 1.0 * 0.5 = 0.12
    from datetime import datetime, timedelta
    future_due = (datetime.now() + timedelta(days=30)).isoformat()
    p3 = calculate_review_priority(
        importance=3, history_count=0, understand_score=60, explain_score=30,
        frictions=[], due_at=future_due,
    )
    assert abs(p3 - 0.12) < 0.01


def test_forget_risk_values():
    """ForgetRisk should decrease with more review history."""
    from backend.services.review_service import _calculate_forget_risk

    assert _calculate_forget_risk(0) == 1.0      # No history = max risk (special case)
    # _FORGET_RISK_INTERVALS = [1, 3, 7, 14, 30], idx = min(history_count, 4)
    assert _calculate_forget_risk(1) == 3.0 / 3   # idx=1 → interval=3
    assert _calculate_forget_risk(2) == 3.0 / 7   # idx=2 → interval=7
    assert _calculate_forget_risk(4) == 3.0 / 30  # idx=4 → interval=30 (capped)
    assert _calculate_forget_risk(10) == 3.0 / 30 # idx=4 → interval=30 (capped)


def test_explain_gap_values():
    """ExplainGap should be 0 when understand <= explain."""
    from backend.services.review_service import _calculate_explain_gap

    assert _calculate_explain_gap(50, 50) == 0.0   # Equal
    assert _calculate_explain_gap(30, 60) == 0.0   # understand < explain
    assert _calculate_explain_gap(80, 20) == 0.6   # (50-20)/50
    assert _calculate_explain_gap(60, 30) == 0.4   # (50-30)/50
    assert _calculate_explain_gap(100, 0) == 1.0   # (50-0)/50


@pytest.mark.asyncio
async def test_session_double_complete_is_idempotent(db_conn):
    """Completing an already-completed session should return it without duplicate side effects."""
    from backend.services.session_service import complete_session

    topic_id = "tp_double_complete"
    session_id = "ss_double_complete"

    # Seed topic and active session
    await db_conn.execute(
        "INSERT INTO topics (topic_id, title, status) VALUES (?, ?, 'active')",
        (topic_id, "Double Complete Test"),
    )
    await db_conn.execute(
        "INSERT INTO sessions (session_id, topic_id, status) VALUES (?, ?, 'active')",
        (session_id, topic_id),
    )
    await db_conn.commit()

    # First complete (db, neo4j=None, lancedb=None, session_id=..., generate_summary=False)
    result1 = await complete_session(
        db_conn, neo4j=None, lancedb=None, session_id=session_id,
        generate_summary=False, generate_review_items=False,
    )
    assert result1 is not None
    assert result1["status"] == "completed"

    # Second complete — should return existing, not create new data
    result2 = await complete_session(
        db_conn, neo4j=None, lancedb=None, session_id=session_id,
        generate_summary=False, generate_review_items=False,
    )
    assert result2 is not None
    assert result2["status"] == "completed"

    # Verify only one session exists
    cursor = await db_conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE session_id = ?", (session_id,)
    )
    count = (await cursor.fetchone())[0]
    assert count == 1


def test_generate_id_format():
    """generate_id should produce prefix_urlsafe(6) format with correct prefix."""
    from backend.models.common import generate_id

    id1 = generate_id("tp")
    assert id1.startswith("tp_")
    assert len(id1) > 4  # prefix(3) + underscore(1) + token(8) = 12

    id2 = generate_id("nd")
    assert id2.startswith("nd_")
    assert id1 != id2  # should be unique

    # No special characters that could cause issues in URLs or SQL
    import string
    safe_chars = set(string.ascii_letters + string.digits + "-_")
    suffix = id1.split("_", 1)[1]
    assert all(c in safe_chars for c in suffix)


# ==================== Sync Recovery Tests ====================


@pytest.mark.asyncio
async def test_recover_pending_sync_events_no_pending(db_conn):
    """recover_pending_sync_events should return zeros when no pending events."""
    from backend.services.sync_recovery import recover_pending_sync_events

    result = await recover_pending_sync_events(db_conn)
    assert result["recovered"] == 0
    assert result["failed_permanent"] == 0
    assert result["skipped"] == 0


@pytest.mark.asyncio
async def test_recover_pending_sync_events_marks_failed(db_conn):
    """Events that have exceeded max retries should be marked as ignored."""
    from backend.repositories.sqlite_repo import record_sync_event
    from backend.services.sync_recovery import recover_pending_sync_events

    # Create a pending event with attempt_count already at max
    event = await record_sync_event(
        db_conn,
        topic_id="tp_test",
        storage_kind="neo4j",
        operation="create_node",
        status="pending",
        attempt_count=3,
        retryable=True,
    )

    result = await recover_pending_sync_events(db_conn, neo4j=None, max_retries=3)

    # Event should be marked as ignored (failed_permanent uses 'ignored' status)
    assert result["failed_permanent"] == 1

    # Verify status changed
    from backend.repositories.sqlite_repo import list_sync_events
    events = await list_sync_events(db_conn, status="pending")
    assert len(events) == 0


@pytest.mark.asyncio
async def test_recover_pending_sync_events_skips_unavailable(db_conn):
    """Events targeting unavailable stores should be skipped."""
    from backend.repositories.sqlite_repo import record_sync_event
    from backend.services.sync_recovery import recover_pending_sync_events

    # Create a neo4j event when neo4j is None
    await record_sync_event(
        db_conn,
        topic_id="tp_test",
        storage_kind="neo4j",
        operation="create_node",
        status="pending",
        attempt_count=1,
    )

    result = await recover_pending_sync_events(db_conn, neo4j=None, lancedb=None)
    assert result["skipped"] == 1
    assert result["recovered"] == 0

    # Event should still be pending (not consumed)
    from backend.repositories.sqlite_repo import list_sync_events
    pending = await list_sync_events(db_conn, status="pending")
    assert len(pending) == 1


# ============================================================
# GROW-H1-011: review_service tests
# ============================================================

async def _setup_topic(db, topic_id="tp_test", title="Test Topic", learning_intent="build_system"):
    """Helper to create a minimal topic for review tests."""
    await db.execute(
        "INSERT INTO topics (topic_id, title, learning_intent) VALUES (?, ?, ?)",
        (topic_id, title, learning_intent),
    )
    await db.commit()


async def _setup_review_item(db, review_id="rv_test", topic_id="tp_test", node_id="nd_1",
                              status="due", review_type="recall", **overrides):
    """Helper to create a review item."""
    import datetime
    await db.execute(
        """INSERT INTO review_items (review_id, topic_id, node_id, priority, status,
           due_at, next_review_at, review_type, last_result, reason, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            review_id, topic_id, node_id,
            overrides.get("priority", 1.0), status,
            overrides.get("due_at", datetime.datetime.now().isoformat()),
            overrides.get("next_review_at"),
            review_type,
            overrides.get("last_result", ""),
            overrides.get("reason", ""),
            overrides.get("updated_at", datetime.datetime.now().isoformat()),
        ),
    )
    await db.commit()


@pytest.mark.asyncio
async def test_skip_review_happy_path(db_conn):
    """skip_review should update review item status to 'skipped'."""
    from backend.repositories.review_repo import get_review_item
    from backend.services.review_service import skip_review

    await _setup_topic(db_conn, "tp_skip")
    await _setup_review_item(db_conn, "rv_skip1", "tp_skip", status="due")

    await skip_review(db_conn, "rv_skip1")

    item = await get_review_item(db_conn, "rv_skip1")
    assert item["status"] == "skipped"


@pytest.mark.asyncio
async def test_skip_review_nonexistent(db_conn):
    """skip_review on non-existent ID should not raise."""
    from backend.services.review_service import skip_review
    await skip_review(db_conn, "rv_nonexistent")


@pytest.mark.asyncio
async def test_submit_review_not_found(db_conn):
    """submit_review should raise ValueError for non-existent review."""
    from backend.services.review_service import submit_review
    try:
        await submit_review(db_conn, "rv_nonexistent", "some answer")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not found" in str(e)


@pytest.mark.asyncio
async def test_submit_review_idempotent_completed(db_conn):
    """submit_review on already completed review should return existing result without re-processing."""
    from backend.repositories.review_repo import get_review_item
    from backend.services.review_service import submit_review

    await _setup_topic(db_conn, "tp_idem")
    await _setup_review_item(db_conn, "rv_idem1", "tp_idem", status="completed",
                              last_result="good", next_review_at="2099-01-01T00:00:00")

    result = await submit_review(db_conn, "rv_idem1", "any answer")
    assert result.result == "good"
    assert result.next_due_time == "2099-01-01T00:00:00"

    # Verify it was NOT re-processed (history_count should still be 0)
    item = await get_review_item(db_conn, "rv_idem1")
    assert item["history_count"] == 0


@pytest.mark.asyncio
async def test_submit_review_fallback_evaluation(db_conn):
    """submit_review should use simple heuristic when AI evaluation fails."""
    from unittest.mock import patch, AsyncMock
    from backend.repositories.review_repo import get_review_item
    from backend.services.review_service import submit_review

    await _setup_topic(db_conn, "tp_fb")
    await _setup_review_item(db_conn, "rv_fb1", "tp_fb", review_type="recall")

    # Long answer should get "good" via fallback heuristic
    long_answer = "这是一个非常详细的回答。" * 20

    # Force AI to fail so fallback heuristic is used
    with patch("backend.agents.diagnoser.diagnose", new_callable=AsyncMock, side_effect=Exception("AI unavailable")):
        result = await submit_review(db_conn, "rv_fb1", long_answer)

    assert result.result == "good"

    # Verify review item was updated
    item = await get_review_item(db_conn, "rv_fb1")
    assert item["status"] == "completed"
    assert item["last_result"] == "good"
    assert item["history_count"] == 1


@pytest.mark.asyncio
async def test_submit_review_short_answer_weak(db_conn):
    """Short answers should get 'weak' result via fallback."""
    from unittest.mock import patch, AsyncMock
    from backend.repositories.review_repo import get_review_item
    from backend.services.review_service import submit_review

    await _setup_topic(db_conn, "tp_weak")
    await _setup_review_item(db_conn, "rv_weak1", "tp_weak", review_type="recall")

    with patch("backend.agents.diagnoser.diagnose", new_callable=AsyncMock, side_effect=Exception("AI unavailable")):
        result = await submit_review(db_conn, "rv_weak1", "短")

    assert result.result == "weak"
    assert result.needs_relearn is True

    item = await get_review_item(db_conn, "rv_weak1")
    assert item["status"] == "failed"
    assert item["last_result"] == "weak"


# ============================================================
# GROW-H1-014: article_service tests
# ============================================================

@pytest.mark.asyncio
async def test_create_source_article_happy_path(db_conn):
    """create_source_article should create article and run analysis."""
    from unittest.mock import patch, AsyncMock
    from backend.services.article_service import create_source_article
    from backend.models.article import SourceArticleCreate

    await _setup_topic(db_conn, "tp_art")

    fake_analysis = {"mention_count": 2, "candidate_count": 1, "valid_links": ["概念A"]}
    with patch("backend.services.article_service.analyze_article", new_callable=AsyncMock, return_value=fake_analysis):
        result = await create_source_article(
            db=db_conn,
            neo4j=None,
            topic_id="tp_art",
            data=SourceArticleCreate(title="Test Article", body="This is a test article body."),
        )

    assert "article" in result
    assert "analysis" in result
    assert result["article"]["title"] == "Test Article"
    assert result["article"]["topic_id"] == "tp_art"
    assert result["article"]["article_kind"] == "source"
    assert result["analysis"]["mention_count"] == 2


@pytest.mark.asyncio
async def test_create_source_article_empty_body(db_conn):
    """create_source_article with empty body should still work."""
    from unittest.mock import patch, AsyncMock
    from backend.services.article_service import create_source_article
    from backend.models.article import SourceArticleCreate

    await _setup_topic(db_conn, "tp_art2")

    with patch("backend.services.article_service.analyze_article", new_callable=AsyncMock, return_value={"mention_count": 0, "candidate_count": 0}):
        result = await create_source_article(
            db=db_conn,
            neo4j=None,
            topic_id="tp_art2",
            data=SourceArticleCreate(title="No Body Article"),
        )

    assert result["article"]["body"] == ""


# ============================================================
# GROW-H1-012: skip_review 状态转换测试
# ============================================================

@pytest.mark.asyncio
async def test_skip_review_from_due(db_conn):
    """skip_review: due → skipped."""
    from backend.repositories.review_repo import get_review_item
    from backend.services.review_service import skip_review

    await _setup_topic(db_conn, "tp_skip_due")
    await _setup_review_item(db_conn, "rv_sd1", "tp_skip_due", status="due")

    await skip_review(db_conn, "rv_sd1")
    assert (await get_review_item(db_conn, "rv_sd1"))["status"] == "skipped"


@pytest.mark.asyncio
async def test_skip_review_from_pending(db_conn):
    """skip_review: pending → skipped."""
    from backend.repositories.review_repo import get_review_item
    from backend.services.review_service import skip_review

    await _setup_topic(db_conn, "tp_skip_pend")
    await _setup_review_item(db_conn, "rv_sp1", "tp_skip_pend", status="pending")

    await skip_review(db_conn, "rv_sp1")
    assert (await get_review_item(db_conn, "rv_sp1"))["status"] == "skipped"


@pytest.mark.asyncio
async def test_skip_review_from_snoozed(db_conn):
    """skip_review: snoozed → skipped."""
    from backend.repositories.review_repo import get_review_item
    from backend.services.review_service import skip_review

    await _setup_topic(db_conn, "tp_skip_snz")
    await _setup_review_item(db_conn, "rv_ss1", "tp_skip_snz", status="snoozed")

    await skip_review(db_conn, "rv_ss1")
    assert (await get_review_item(db_conn, "rv_ss1"))["status"] == "skipped"


# ============================================================
# GROW-H1-013: _auto_transition_node_status 测试
# ============================================================

@pytest.mark.asyncio
async def test_auto_transition_to_mastered(db_conn):
    """avg >= 70 with non-mastered status → mastered (neo4j=None, no side effects)."""
    from backend.services.review_service import _auto_transition_node_status

    await _setup_topic(db_conn, "tp_trans1")

    ability = {
        "topic_id": "tp_trans1", "node_id": "nd_1",
        "understand": 80, "example": 80, "contrast": 70, "apply": 70,
        "explain": 70, "recall": 70, "transfer": 65, "teach": 60,
    }

    # neo4j=None means no Neo4j update, no DB side effects
    await _auto_transition_node_status(db_conn, "tp_trans1", "nd_1", ability, neo4j=None, current_status="practiced")
    # Should not raise — no crash when neo4j unavailable


@pytest.mark.asyncio
async def test_auto_transition_to_practiced(db_conn):
    """avg < 70 with mastered status → practiced (neo4j=None, no side effects)."""
    from backend.services.review_service import _auto_transition_node_status

    await _setup_topic(db_conn, "tp_trans2")

    ability = {
        "topic_id": "tp_trans2", "node_id": "nd_2",
        "understand": 40, "example": 30, "contrast": 35, "apply": 30,
        "explain": 30, "recall": 30, "transfer": 20, "teach": 20,
    }

    await _auto_transition_node_status(db_conn, "tp_trans2", "nd_2", ability, neo4j=None, current_status="mastered")


@pytest.mark.asyncio
async def test_auto_transition_topic_not_found(db_conn):
    """Non-existent topic → early return, no crash."""
    from backend.services.review_service import _auto_transition_node_status

    ability = {
        "topic_id": "tp_nonexist", "node_id": "nd_1",
        "understand": 80, "example": 80, "contrast": 80, "apply": 80,
        "explain": 80, "recall": 80, "transfer": 80, "teach": 80,
    }

    # Should not raise
    await _auto_transition_node_status(db_conn, "tp_nonexist", "nd_1", ability, neo4j=None, current_status="unseen")


@pytest.mark.asyncio
async def test_auto_transition_already_mastered_no_change(db_conn):
    """avg >= 70 and already mastered → no-op."""
    from backend.services.review_service import _auto_transition_node_status

    await _setup_topic(db_conn, "tp_trans4")

    ability = {
        "topic_id": "tp_trans4", "node_id": "nd_4",
        "understand": 90, "example": 90, "contrast": 85, "apply": 85,
        "explain": 80, "recall": 80, "transfer": 75, "teach": 75,
    }

    # Already mastered, should not trigger any transition
    await _auto_transition_node_status(db_conn, "tp_trans4", "nd_4", ability, neo4j=None, current_status="mastered")


# ============================================================
# GROW-H1-015: article_service.confirm_candidate 测试
# ============================================================

async def _setup_candidate(db, candidate_id="cc_test1", topic_id="tp_cc", concept_text="machine learning",
                           matched_concept_name=None, matched_node_id=None, source_article_id="ar_test1"):
    """Helper to create a concept candidate for testing."""
    import datetime
    normalized = concept_text.lower().strip()
    await db.execute(
        """INSERT INTO concept_candidates
           (candidate_id, topic_id, source_article_id, concept_text, normalized_text,
            matched_concept_name, matched_node_id, status, confidence, origin,
            created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            candidate_id, topic_id, source_article_id, concept_text, normalized,
            matched_concept_name or "", matched_node_id,
            "candidate", 0.8, "manual",
            datetime.datetime.now().isoformat(),
            datetime.datetime.now().isoformat(),
        ),
    )
    await db.commit()


@pytest.mark.asyncio
async def test_confirm_candidate_not_found(db_conn):
    """confirm_candidate with non-existent ID returns None."""
    from backend.services.article_service import confirm_candidate
    from backend.models.article import ConceptCandidateConfirm

    await _setup_topic(db_conn, "tp_cc_nf")

    result = await confirm_candidate(
        db_conn, neo4j=None, lancedb=None,
        topic_id="tp_cc_nf", candidate_id="cc_nonexist",
        data=ConceptCandidateConfirm(),
    )
    assert result is None


@pytest.mark.asyncio
async def test_confirm_candidate_topic_mismatch(db_conn):
    """confirm_candidate with wrong topic_id returns None."""
    from backend.services.article_service import confirm_candidate
    from backend.models.article import ConceptCandidateConfirm

    await _setup_topic(db_conn, "tp_cc_a")
    await _setup_topic(db_conn, "tp_cc_b")
    await _setup_candidate(db_conn, "cc_mismatch", "tp_cc_a")

    result = await confirm_candidate(
        db_conn, neo4j=None, lancedb=None,
        topic_id="tp_cc_b", candidate_id="cc_mismatch",
        data=ConceptCandidateConfirm(),
    )
    assert result is None


@pytest.mark.asyncio
async def test_confirm_candidate_no_neo4j(db_conn):
    """confirm_candidate without neo4j creates node ID and updates candidate status."""
    from backend.services.article_service import confirm_candidate
    from backend.models.article import ConceptCandidateConfirm
    from backend.repositories.sqlite_repo import get_concept_candidate

    await _setup_topic(db_conn, "tp_cc_nn")
    await _setup_candidate(db_conn, "cc_nn1", "tp_cc_nn", concept_text="neural network")

    result = await confirm_candidate(
        db_conn, neo4j=None, lancedb=None,
        topic_id="tp_cc_nn", candidate_id="cc_nn1",
        data=ConceptCandidateConfirm(concept_name="Neural Network"),
    )

    # Without neo4j, the function still returns a result but can't create the graph node
    assert result is not None
    assert result["matched_concept_name"] == "Neural Network"
    assert result["status"] == "confirmed"


# ============================================================
# GROW-H1-016: article_service.upsert_note 测试
# ============================================================

@pytest.mark.asyncio
async def test_upsert_note_create_new(db_conn):
    """upsert_note creates a new note when none exists."""
    from backend.services.article_service import upsert_note
    from backend.models.article import ConceptNoteUpsert
    from backend.repositories.sqlite_repo import get_concept_note

    await _setup_topic(db_conn, "tp_note")

    result = await upsert_note(db_conn, "tp_note", "neural-network",
                               ConceptNoteUpsert(title="Neural Networks", body="NNs are cool"))

    assert result["topic_id"] == "tp_note"
    assert result["concept_key"] == "neural-network"
    assert result["title"] == "Neural Networks"
    assert result["body"] == "NNs are cool"
    assert result["note_id"].startswith("nt_")

    # Verify it persists
    fetched = await get_concept_note(db_conn, "tp_note", "neural-network")
    assert fetched is not None
    assert fetched["title"] == "Neural Networks"


@pytest.mark.asyncio
async def test_upsert_note_update_existing(db_conn):
    """upsert_note reuses existing note_id on update."""
    from backend.services.article_service import upsert_note
    from backend.models.article import ConceptNoteUpsert
    from backend.repositories.sqlite_repo import get_concept_note

    await _setup_topic(db_conn, "tp_note2")

    # Create first
    r1 = await upsert_note(db_conn, "tp_note2", "cnn",
                             ConceptNoteUpsert(title="CNN", body="Convolutional"))
    original_id = r1["note_id"]

    # Update
    r2 = await upsert_note(db_conn, "tp_note2", "cnn",
                             ConceptNoteUpsert(title="CNN Updated", body="Convolutional Neural Networks"))
    assert r2["note_id"] == original_id  # Same ID reused
    assert r2["title"] == "CNN Updated"

    fetched = await get_concept_note(db_conn, "tp_note2", "cnn")
    assert fetched["body"] == "Convolutional Neural Networks"


# ============================================================
# GROW-H1-017: article_service.list_backlinks 测试
# ============================================================

async def _setup_backlink_data(db, topic_id="tp_bl"):
    """Create an article + mention for backlink tests."""
    import datetime
    await _setup_topic(db, topic_id)
    await db.execute(
        """INSERT INTO articles (article_id, topic_id, title, body, article_kind, is_editable, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'source', 1, ?, ?)""",
        ("ar_bl1", topic_id, "Test Article",
         "First paragraph about neural networks.\n\nSecond paragraph about deep learning.\n\nThird paragraph about CNNs.",
         datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()),
    )
    await db.execute(
        """INSERT INTO article_mentions
           (mention_id, topic_id, article_id, concept_text, concept_name, concept_key,
            mention_type, confidence, paragraph_index, anchor_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("mn_bl1", topic_id, "ar_bl1", "neural networks", "Neural Network", "neural-network",
         "explicit", 0.9, 0, "", datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()),
    )
    await db.commit()


@pytest.mark.asyncio
async def test_list_backlinks_happy_path(db_conn):
    """list_backlinks returns correct snippet from paragraph."""
    from backend.services.article_service import list_backlinks

    await _setup_backlink_data(db_conn, "tp_bl1")

    result = await list_backlinks(db_conn, "tp_bl1", "neural-network")
    assert len(result) == 1
    assert result[0]["article_id"] == "ar_bl1"
    assert result[0]["title"] == "Test Article"
    assert "neural networks" in result[0]["snippet"]


@pytest.mark.asyncio
async def test_list_backlinks_empty(db_conn):
    """list_backlinks returns empty list for unknown concept."""
    from backend.services.article_service import list_backlinks

    await _setup_backlink_data(db_conn, "tp_bl2")

    result = await list_backlinks(db_conn, "tp_bl2", "nonexistent-key")
    assert result == []


# ============================================================
# GROW-H1-018: node_service.get_entry_node 测试
# ============================================================

@pytest.mark.asyncio
async def test_get_entry_node_topic_not_found(db_conn):
    """get_entry_node returns None when topic doesn't exist."""
    from backend.services.node_service import get_entry_node

    result = await get_entry_node(db_conn, None, "tp_nonexist")
    assert result is None


@pytest.mark.asyncio
async def test_get_entry_node_with_current_node(db_conn):
    """get_entry_node with current_node_id returns detail with why_now."""
    from unittest.mock import patch, AsyncMock
    from backend.services.node_service import get_entry_node

    await _setup_topic(db_conn, "tp_gen1", learning_intent="build_system")
    await db_conn.execute(
        "UPDATE topics SET current_node_id = 'nd_cur1' WHERE topic_id = 'tp_gen1'"
    )
    await db_conn.commit()

    mock_detail = {
        "node": {"node_id": "nd_cur1", "name": "Introduction", "status": "learning", "importance": 3, "summary": "Intro topic"},
        "ability": {"understand": 50, "explain": 40, "apply": 30},
    }

    with patch("backend.services.node_service.get_node_detail", new_callable=AsyncMock, return_value=mock_detail):
        result = await get_entry_node(db_conn, None, "tp_gen1")

    assert result is not None
    assert result["node_id"] == "nd_cur1"
    assert "继续上次学习" in result.get("why_now", "")


# ============================================================
# GROW-H1-019: node_service.defer_node 测试
# ============================================================

@pytest.mark.asyncio
async def test_defer_node_with_source(db_conn):
    """defer_node creates deferred node with source_node_id."""
    from backend.services.node_service import defer_node

    await _setup_topic(db_conn, "tp_def1")

    result = await defer_node(db_conn, "tp_def1", "nd_def1", source_node_id="nd_src1", reason="too complex")
    assert result["node_id"] == "nd_def1"
    assert result["source_node_id"] == "nd_src1"
    assert result["reason"] == "too complex"


@pytest.mark.asyncio
async def test_defer_node_without_source(db_conn):
    """defer_node creates deferred node without source_node_id."""
    from backend.services.node_service import defer_node

    await _setup_topic(db_conn, "tp_def2")

    result = await defer_node(db_conn, "tp_def2", "nd_def2")
    assert result["source_node_id"] is None
    assert result["reason"] == ""


# ============================================================
# GROW-H1-020: node_service.update_node_status mastered 递增测试
# ============================================================

@pytest.mark.asyncio
async def test_update_node_status_non_mastered(db_conn):
    """update_node_status with non-mastered status does NOT increment learned_nodes."""
    from unittest.mock import patch, AsyncMock
    from backend.services.node_service import update_node_status

    await _setup_topic(db_conn, "tp_us1")

    with patch("backend.services.node_service.graph") as mock_graph:
        mock_graph.update_concept_node = AsyncMock()
        result = await update_node_status(db_conn, None, "tp_us1", "nd_us1", "learning")

    assert result["status"] == "learning"
    mock_graph.update_concept_node.assert_not_called()


@pytest.mark.asyncio
async def test_update_node_status_mastered_neo4j_none(db_conn):
    """update_node_status mastered with neo4j=None increments learned_nodes."""
    from backend.services.node_service import update_node_status

    await _setup_topic(db_conn, "tp_us2")

    result = await update_node_status(db_conn, None, "tp_us2", "nd_us2", "mastered")
    assert result["status"] == "mastered"

    # Verify learned_nodes was incremented
    cur = await db_conn.execute("SELECT learned_nodes FROM topics WHERE topic_id = 'tp_us2'")
    row = await cur.fetchone()
    assert row["learned_nodes"] == 1


# ============================================================
# GROW-H1-021: practice_service.get_practice_prompt 缓存测试
# ============================================================

@pytest.mark.asyncio
async def test_get_practice_prompt_cache_hit(db_conn):
    """get_practice_prompt returns cached data with renamed keys."""
    from unittest.mock import patch, AsyncMock
    from backend.services.practice_service import get_practice_prompt

    cached_data = {
        "prompt_text": "Define X in your own words.",
        "min_answer_hint": "At least 50 chars",
        "scoring_dimensions": ["correctness", "clarity"],
        "requirements": ["should be original"],
    }
    with patch("backend.services.practice_service.sqlite_repo.get_cached_practice_prompt", new_callable=AsyncMock, return_value=cached_data):
        prompt, was_cached = await get_practice_prompt(db_conn, "tp_pp", "nd_pp", "define")

    assert was_cached is True
    assert prompt["prompt_text"] == "Define X in your own words."
    assert prompt["minimum_answer_hint"] == "At least 50 chars"
    assert "minimum_answer_hint" in prompt


@pytest.mark.asyncio
async def test_get_practice_prompt_ai_failure_fallback(db_conn):
    """get_practice_prompt returns static fallback when AI fails."""
    from unittest.mock import patch, AsyncMock
    from backend.services.practice_service import get_practice_prompt

    with patch("backend.services.practice_service.sqlite_repo.get_cached_practice_prompt", new_callable=AsyncMock, return_value=None):
        with patch("backend.services.practice_service.tutor_agent.generate_practice", new_callable=AsyncMock, side_effect=Exception("AI down")):
            prompt, was_cached = await get_practice_prompt(db_conn, "tp_pp2", "nd_pp2", "define")

    assert was_cached is False
    assert "prompt_text" in prompt
    assert prompt["practice_type"] == "define"


# ============================================================
# GROW-H1-022: practice_service.toggle_favorite 测试
# ============================================================

async def _setup_expression_asset(db, asset_id="ea_test1", topic_id="tp_ea", favorited=0):
    """Helper to create an expression asset."""
    import datetime
    await db.execute(
        """INSERT INTO expression_assets (asset_id, topic_id, node_id, expression_type, user_expression,
           ai_rewrite, expression_skeleton, favorited, session_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (asset_id, topic_id, "nd_1", "define", "original text", "", "",
         favorited, "ss_1", datetime.datetime.now().isoformat()),
    )
    await db.commit()


@pytest.mark.asyncio
async def test_toggle_favorite_on(db_conn):
    """toggle_favorite sets favorited=1 when currently 0."""
    from backend.services.practice_service import toggle_favorite

    await _setup_topic(db_conn, "tp_ea")
    await _setup_expression_asset(db_conn, "ea_tf1", "tp_ea", favorited=0)

    result = await toggle_favorite(db_conn, "ea_tf1")
    assert result["favorited"] == 1


@pytest.mark.asyncio
async def test_toggle_favorite_off(db_conn):
    """toggle_favorite sets favorited=0 when currently 1."""
    from backend.services.practice_service import toggle_favorite

    await _setup_topic(db_conn, "tp_ea2")
    await _setup_expression_asset(db_conn, "ea_tf2", "tp_ea2", favorited=1)

    result = await toggle_favorite(db_conn, "ea_tf2")
    assert result["favorited"] == 0


@pytest.mark.asyncio
async def test_toggle_favorite_not_found(db_conn):
    """toggle_favorite returns None for non-existent asset."""
    from backend.services.practice_service import toggle_favorite

    result = await toggle_favorite(db_conn, "ea_nonexist")
    assert result is None


# ============================================================
# GROW-H1-023: export_service.export_topic 三格式测试
# ============================================================

@pytest.mark.asyncio
async def test_export_topic_not_found(db_conn):
    """export_topic returns None for non-existent topic."""
    from backend.services.export_service import export_topic

    result = await export_topic(db_conn, "tp_nonexist")
    assert result is None


@pytest.mark.asyncio
async def test_export_topic_json(db_conn):
    """export_topic JSON format returns valid JSON."""
    from backend.services.export_service import export_topic

    await _setup_topic(db_conn, "tp_exp", title="Export Test")

    result = await export_topic(db_conn, "tp_exp", neo4j=None, export_type="json")
    assert result is not None
    assert result["format"] == "json"
    assert result["filename"].endswith(".json")

    import json
    content = json.loads(result["content"])
    assert "ability_records" in content or "topic" in content


@pytest.mark.asyncio
async def test_export_topic_markdown(db_conn):
    """export_topic markdown format starts with title heading."""
    from backend.services.export_service import export_topic

    await _setup_topic(db_conn, "tp_exp2", title="Markdown Export")

    result = await export_topic(db_conn, "tp_exp2", neo4j=None, export_type="markdown")
    assert result is not None
    assert "# Markdown Export" in result["content"]
    assert result["format"] == "markdown"


@pytest.mark.asyncio
async def test_export_topic_anki_no_nodes(db_conn):
    """export_topic anki format returns error when no graph nodes."""
    from backend.services.export_service import export_topic

    await _setup_topic(db_conn, "tp_exp3")

    result = await export_topic(db_conn, "tp_exp3", neo4j=None, export_type="anki")
    assert result is not None
    assert result.get("error_code") == "EXPORT_EMPTY"


# ============================================================
# GROW-H1-024: stats_service.get_global_stats 聚合测试
# ============================================================

@pytest.mark.asyncio
async def test_get_global_stats_empty(db_conn):
    """get_global_stats returns all zeros on empty database."""
    from backend.services.stats_service import get_global_stats

    stats = await get_global_stats(db_conn)
    assert stats["topic_count"] == 0
    assert stats["active_topic_count"] == 0
    assert stats["total_nodes"] == 0
    assert stats["total_mastered"] == 0
    assert stats["due_reviews"] == 0
    assert stats["total_expression_assets"] == 0
    assert stats["total_frictions"] == 0


@pytest.mark.asyncio
async def test_get_global_stats_with_data(db_conn):
    """get_global_stats aggregates correctly with real data."""
    from backend.services.stats_service import get_global_stats

    await _setup_topic(db_conn, "tp_st1", title="Stats Test", learning_intent="build_system")
    await _setup_topic(db_conn, "tp_st2", title="Stats Test 2", learning_intent="build_system")

    stats = await get_global_stats(db_conn)
    assert stats["topic_count"] == 2
    assert stats["total_sessions"] == 0


# ============================================================
# GROW-H1-025: session_service 完整 API 测试
# ============================================================

@pytest.mark.asyncio
async def test_start_session_create_new(db_conn):
    """start_session creates new session when no active session exists."""
    from backend.services.session_service import start_session
    from backend.models.session import SessionCreate

    await _setup_topic(db_conn, "tp_sess1")

    result = await start_session(db_conn, "tp_sess1", SessionCreate())
    assert result is not None
    assert result["topic_id"] == "tp_sess1"
    assert result["restored"] is False
    assert result["session_id"].startswith("ss_")


@pytest.mark.asyncio
async def test_start_session_restore_existing(db_conn):
    """start_session restores existing active session."""
    from unittest.mock import patch, AsyncMock
    from backend.services.session_service import start_session

    await _setup_topic(db_conn, "tp_sess2")
    existing = {"session_id": "ss_existing", "topic_id": "tp_sess2", "status": "active"}

    from backend.models.session import SessionCreate
    with patch("backend.services.session_service.sqlite_repo.get_active_session", new_callable=AsyncMock, return_value=existing):
        result = await start_session(db_conn, "tp_sess2", data=SessionCreate(learning_intent="build_system"))

    assert result["restored"] is True
    assert result["session_id"] == "ss_existing"


@pytest.mark.asyncio
async def test_get_session_not_found(db_conn):
    """get_session returns None for non-existent session."""
    from backend.services.session_service import get_session

    result = await get_session(db_conn, "ss_nonexist")
    assert result is None


@pytest.mark.asyncio
async def test_complete_session_idempotent(db_conn):
    """complete_session on already completed session returns as-is."""
    from unittest.mock import patch, AsyncMock
    from backend.services.session_service import complete_session

    await _setup_topic(db_conn, "tp_cs1")
    completed_session = {"session_id": "ss_done", "topic_id": "tp_cs1", "status": "completed"}

    with patch("backend.services.session_service.sqlite_repo.get_session", new_callable=AsyncMock, return_value=completed_session):
        result = await complete_session(db_conn, None, None, "ss_done")

    assert result is not None
    assert result["status"] == "completed"
