"""Review service - review scheduling and submission."""

import logging
import math

logger = logging.getLogger(__name__)
from datetime import datetime, timedelta

import aiosqlite

from backend.models.review import ReviewItem, ReviewItemCreate, ReviewResult, ReviewFeedbackDetail
from backend.models.ability import PRACTICE_DIMENSION_MAP, AbilityRecord, AbilityDelta, apply_delta
from backend.repositories import sqlite_repo

# Recall confidence decay parameters (from algorithm doc)
# Half-life: how many reviews until confidence halves
_DECAY_HALF_LIFE = 3.0
# Minimum confidence floor
_MIN_CONFIDENCE = 0.1
# Confidence gain on successful review
_SUCCESS_CONFIDENCE_GAIN = 0.3
# Confidence loss on failed review
_FAILURE_CONFIDENCE_LOSS = 0.2


# Mapping from review_type to practice_type for AI evaluation
_REVIEW_TYPE_PRACTICE_MAP = {
    "recall": "recall",
    "contrast": "contrast",
    "explain": "explain",
    "spaced": "recall",
}


def _suggest_review_type(ability: dict) -> str:
    """Suggest review_type based on ability scores.

    Uses weakest dimension to pick the most beneficial review type.
    """
    if not ability:
        return "recall"
    scores = {
        "recall": ability.get("recall", 0),
        "contrast": ability.get("contrast", 0),
        "explain": ability.get("explain", 0),
    }
    weakest = min(scores, key=scores.get)
    return weakest


def _rule_based_review_evaluation(user_answer: str, review_type: str = "recall"):
    """Rule-based review evaluation when AI is unavailable.

    Considers answer length, keyword density, and review type specificity.
    Returns (result_level, ReviewFeedbackDetail).
    """
    length = len(user_answer.strip())
    # Score based on multiple signals
    score = 0
    # Length signals (0-40 points)
    if length > 200:
        score += 40
    elif length > 100:
        score += 30
    elif length > 50:
        score += 20
    elif length > 20:
        score += 10
    # Review-type specific keyword signals (0-30 points)
    _TYPE_KEYWORDS = {
        "recall": ["是", "指", "表示", "包括", "用于", "特点", "作用", "因为", "所以", "分为"],
        "contrast": ["区别", "不同", "相比", "而", "但是", "差异", "类似", "独特"],
        "explain": ["因为", "所以", "例如", "比如", "可以理解为", "简单来说", "本质"],
        "spaced": ["是", "指", "包括", "特点", "用于", "作用"],
    }
    keywords = _TYPE_KEYWORDS.get(review_type, _TYPE_KEYWORDS["spaced"])
    keyword_hits = sum(1 for kw in keywords if kw in user_answer)
    score += min(30, keyword_hits * 6)
    # Structure signals (0-30 points) — has sentences with reasonable length
    sentences = [s.strip() for s in user_answer.replace("。", ".").split(".") if s.strip()]
    if len(sentences) >= 3:
        score += 20
    elif len(sentences) >= 2:
        score += 10

    if score >= 60:
        result_level = "good"
    elif score >= 40:
        result_level = "medium"
    elif score >= 20:
        result_level = "partial"
    else:
        result_level = "weak"

    issues = []
    suggestions = []
    if length < 30:
        issues.append("回答内容较少")
        suggestions.append("尝试更详细地描述，至少写 2-3 句话")
    if keyword_hits < 2:
        issues.append("缺少关键概念描述")
        suggestions.append("尝试使用更准确的专业术语")
    if not issues:
        issues.append("规则引擎评估（AI 不可用）")
        suggestions.append("继续练习以巩固理解")

    feedback_detail = ReviewFeedbackDetail(
        correctness=result_level,
        clarity=result_level,
        naturalness=result_level,
        issues=issues,
        suggestions=suggestions,
    )
    return result_level, feedback_detail


# Spaced repetition intervals (days) — per review type
_FORGET_RISK_INTERVALS = [1, 3, 7, 14, 30]
_REVIEW_SUCCESS_INTERVALS = [3, 7, 14, 30, 60]
_REVIEW_TYPE_INTERVALS: dict[str, list[int]] = {
    "recall": [1, 3, 7, 14, 30],
    "contrast": [3, 7, 14, 21, 45],
    "explain": [2, 5, 10, 21, 45],
    "spaced": [3, 7, 14, 30, 60],
}
_REVIEW_FAILURE_INTERVAL = 1  # 1 day


def _calculate_forget_risk(history_count: int) -> float:
    """Calculate ForgetRisk based on review history count.

    Uses intervals [1, 3, 7, 14, 30] indexed by history_count.
    More history = lower forget risk (harder to forget).
    """
    if history_count <= 0:
        return 1.0
    idx = min(history_count, len(_FORGET_RISK_INTERVALS) - 1)
    # ForgetRisk inversely proportional to interval length
    interval = _FORGET_RISK_INTERVALS[idx]
    return min(1.0, 3.0 / interval)


def _calculate_explain_gap(understand_score: int, explain_score: int) -> float:
    """Calculate ExplainGap when understand > explain."""
    if understand_score > explain_score:
        return max(0.0, (50 - explain_score) / 50)
    return 0.0


def _calculate_confusion_risk(frictions: list[dict]) -> float:
    """Calculate ConfusionRisk based on friction records with type-aware weights."""
    # Friction type severity weights
    _severity_weights = {
        "prerequisite_gap": 0.4,
        "concept_confusion": 0.35,
        "weak_structure": 0.2,
        "abstract_overload": 0.2,
        "weak_recall": 0.15,
        "weak_application": 0.15,
        "lack_of_example": 0.1,
    }
    risk = 1.0
    for f in frictions:
        ftype = f.get("friction_type", "")
        weight = _severity_weights.get(ftype, 0.2)
        risk *= (1.0 + weight)
    return risk


def _calculate_time_due_weight(due_at: str | None) -> float:
    """Calculate TimeDueWeight: higher when overdue, lower when far in future."""
    if not due_at:
        return 1.0
    try:
        due = datetime.fromisoformat(due_at)
        now = datetime.now()
        days_until_due = (due - now).total_seconds() / 86400
        if days_until_due < -7:
            return 2.0  # Very overdue
        elif days_until_due < 0:
            return 1.5  # Overdue
        elif days_until_due < 1:
            return 1.2  # Due today
        elif days_until_due < 3:
            return 1.0  # Due soon
        elif days_until_due < 7:
            return 0.8  # Due this week
        else:
            return 0.5  # Far in future
    except (ValueError, TypeError):
        return 1.0


def calculate_review_priority(
    importance: int = 3,
    history_count: int = 0,
    understand_score: int = 0,
    explain_score: int = 0,
    frictions: list[dict] | None = None,
    due_at: str | None = None,
) -> float:
    """Calculate ReviewPriority using the full formula.

    ReviewPriority = Importance * ForgetRisk * ExplainGap * ConfusionRisk * TimeDueWeight
    """
    forget_risk = _calculate_forget_risk(history_count)
    explain_gap = _calculate_explain_gap(understand_score, explain_score)
    confusion_risk = _calculate_confusion_risk(frictions or [])
    time_due_weight = _calculate_time_due_weight(due_at)

    # Normalize importance to 0.2-1.0 range (from 1-5 scale)
    importance_factor = importance / 5.0

    priority = importance_factor * forget_risk * explain_gap * confusion_risk * time_due_weight
    return round(priority, 4)


def _get_next_review_interval(history_count: int, success: bool, review_type: str = "spaced") -> int | None:
    """Calculate next review interval.

    On success: intervals per review_type, falling back to _REVIEW_SUCCESS_INTERVALS.
    On failure: 1 day.
    On completed mastery: no next due (None).
    """
    if not success:
        return _REVIEW_FAILURE_INTERVAL
    intervals = _REVIEW_TYPE_INTERVALS.get(review_type, _REVIEW_SUCCESS_INTERVALS)
    idx = min(history_count, len(intervals) - 1)
    return intervals[idx]


def _calculate_recall_confidence(current_confidence: float, success: bool) -> float:
    """Calculate new recall confidence after a review attempt.

    On success: confidence += SUCCESS_CONFIDENCE_GAIN, capped at 1.0
    On failure: exponential decay: confidence *= exp(-FAILURE_CONFIDENCE_LOSS)
    Floor at MIN_CONFIDENCE.
    """
    if success:
        return min(1.0, current_confidence + _SUCCESS_CONFIDENCE_GAIN)
    else:
        decayed = current_confidence * math.exp(-_FAILURE_CONFIDENCE_LOSS * 2)
        return max(_MIN_CONFIDENCE, decayed)


def _calculate_ability_avg(ability: dict) -> float:
    """Calculate average ability score across all 8 dimensions."""
    if not ability:
        return 0.0
    dims = ["understand", "example", "contrast", "apply", "explain", "recall", "transfer", "teach"]
    scores = [ability.get(d, 0) for d in dims]
    return sum(scores) / len(scores) if scores else 0.0


def _should_reschedule_future_review(
    scheduled_at: datetime,
    now: datetime,
    history_count: int,
) -> bool:
    """Allow weak nodes to be pulled forward when their next review is scheduled too far out.

    A future review normally blocks duplicate queue generation. The exception is when the
    existing schedule is later than the success interval policy would allow for the node's
    current review history, which means the node has likely drifted below the desired recall
    threshold and should be surfaced again now.
    """
    max_interval_days = _get_next_review_interval(history_count, success=True)
    if max_interval_days is None:
        return False
    return scheduled_at > (now + timedelta(days=max_interval_days))


async def _auto_transition_node_status(
    db: aiosqlite.Connection, topic_id: str, node_id: str,
    ability: dict, neo4j=None, current_status: str | None = None,
):
    """Auto-transition node status based on ability scores.

    - If avg ability >= 70: set status to 'mastered', increment learned_nodes
    - If avg ability drops < 70 after being mastered: set status to 'practiced', decrement learned_nodes
    """
    from backend.repositories import neo4j_repo as graph

    avg = _calculate_ability_avg(ability)
    topic = await sqlite_repo.get_topic(db, topic_id)
    if not topic:
        return

    # Get current node status (use provided value or query Neo4j)
    if current_status is None:
        current_status = "unseen"
        if neo4j:
            try:
                async with neo4j.session() as session:
                    node = await graph.get_concept_node(session, node_id)
                    if node:
                        current_status = node.get("status", "unseen")
            except Exception as e:
                logger.warning("Failed to get current node status from Neo4j for review: %s", e)

    new_status = None
    if avg >= 70 and current_status != "mastered":
        new_status = "mastered"
    elif avg < 70 and current_status == "mastered":
        new_status = "practiced"

    if new_status:
        neo4j_updated = False
        if neo4j:
            try:
                async with neo4j.session() as session:
                    await graph.update_concept_node(session, node_id, {"status": new_status})
                    neo4j_updated = True
            except Exception as e:
                logger.warning(f"Failed to update node status in Neo4j: {e}")
                await sqlite_repo.record_sync_event(
                    db,
                    topic_id=topic_id,
                    node_id=node_id,
                    storage_kind="neo4j",
                    operation="review.update_node_status",
                    status="pending",
                    error_message=str(e),
                    payload={"new_status": new_status},
                )

        if neo4j_updated:
            if new_status == "mastered":
                # Cancel pending review items first (idempotent, safe if it fails)
                try:
                    await db.execute(
                        "UPDATE review_items SET status = 'cancelled' WHERE topic_id = ? AND node_id = ? AND status IN ('pending', 'due')",
                        (topic_id, node_id),
                    )
                    await db.commit()
                except Exception as cancel_err:
                    logger.warning("Failed to cancel pending reviews for mastered node %s: %s", node_id, cancel_err)
                # Then increment learned_nodes (commits internally)
                await sqlite_repo.increment_topic_stats(db, topic_id, "learned_nodes")
            elif new_status == "practiced":
                # Decrement learned_nodes (but not below 0)
                if (topic.get("learned_nodes") or 0) > 0:
                    await sqlite_repo.increment_topic_stats(db, topic_id, "learned_nodes", delta=-1)


async def list_reviews(
    db: aiosqlite.Connection,
    status: str | None = None,
    topic_id: str | None = None,
    due_before: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """List review items."""
    def _review_sort_key(item: dict) -> tuple[float, bool, str]:
        return (
            -(item.get("priority") or 0),
            item.get("due_at") is not None,
            item.get("due_at") or "",
        )

    def _is_due(item: dict, now: datetime) -> bool:
        due_at = item.get("due_at")
        if not due_at:
            return True
        try:
            return datetime.fromisoformat(due_at) <= now
        except (ValueError, TypeError):
            logger.warning("Failed to parse due_at '%s' for review item %s", due_at, item.get("review_id"))
            return True

    fetch_limit = max(limit + offset, 1)
    due_before_value: str | None = None
    if due_before:
        try:
            due_before_value = datetime.fromisoformat(due_before).isoformat()
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse due_before '%s' for review filtering: %s", due_before, e)

    if status == "pending":
        now = datetime.now()
        pending = await sqlite_repo.list_review_items(db, "pending", topic_id, fetch_limit, 0, due_before=due_before_value)
        due = await sqlite_repo.list_review_items(db, "due", topic_id, fetch_limit, 0, due_before=due_before_value)
        snoozed = await sqlite_repo.list_review_items(db, "snoozed", topic_id, fetch_limit, 0, due_before=due_before_value)
        actionable_snoozed = [item for item in snoozed if _is_due(item, now)]
        items = sorted([*pending, *due, *actionable_snoozed], key=_review_sort_key)
    else:
        items = await sqlite_repo.list_review_items(db, status, topic_id, fetch_limit, 0, due_before=due_before_value)
    return items[offset:offset + limit]


async def get_review(db: aiosqlite.Connection, review_id: str) -> dict | None:
    """Get review item detail."""
    return await sqlite_repo.get_review_item(db, review_id)


async def skip_review(db: aiosqlite.Connection, review_id: str):
    """Mark a review item as skipped."""
    await sqlite_repo.update_review_item_status(db, review_id, "skipped")


async def snooze_review(db: aiosqlite.Connection, review_id: str):
    """Snooze a review item (postpone by 1 day)."""
    row = await sqlite_repo.get_review_item(db, review_id)
    if not row:
        return
    await sqlite_repo.update_review_item_status(db, review_id, "snoozed")
    # Push due_at forward by 1 day
    if row.get("due_at"):
        try:
            due = datetime.fromisoformat(row["due_at"])
            new_due = due + timedelta(days=1)
            await sqlite_repo.update_review_item(db, review_id, {"due_at": new_due.isoformat()})
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse due_at for snooze review %s: %s", review_id, e)


async def _evaluate_review_answer(
    review_item: dict,
    user_answer: str,
    neo4j=None,
) -> tuple[str, ReviewFeedbackDetail, dict | None, str | None]:
    """Evaluate a review answer using AI or rule-based fallback.

    Returns (result_level, feedback_detail, ability_update, fetched_node_status).
    """
    topic_id = review_item["topic_id"]
    node_id = review_item["node_id"]

    ability_update = None
    feedback_detail = ReviewFeedbackDetail()
    result_level = "medium"
    _fetched_node_status: str | None = None

    try:
        from backend.agents import diagnoser as diagnoser_agent

        node_name = node_id
        node_summary = ""
        if neo4j:
            try:
                from backend.repositories import neo4j_repo as graph
                async with neo4j.session() as session:
                    node = await graph.get_concept_node(session, node_id)
                    if node:
                        node_name = node.get("name", "")
                        node_summary = node.get("summary", "")
                        _fetched_node_status = node.get("status", "unseen")
            except Exception as e:
                logger.warning(f"Failed to get node info from Neo4j for review: {e}")

        review_type = review_item.get("review_type", "recall")
        practice_type_for_eval = _REVIEW_TYPE_PRACTICE_MAP.get(review_type, "recall")

        eval_prompts = {
            "recall": "请回忆并复述这个知识节点的核心内容。",
            "contrast": "请说明这个概念与相关概念的区别。",
            "explain": "请用自己的话解释这个概念。",
        }

        diag_result = await diagnoser_agent.diagnose(
            node_name=node_name,
            node_summary=node_summary,
            practice_type=practice_type_for_eval,
            prompt_text=eval_prompts.get(review_type, eval_prompts["recall"]),
            user_answer=user_answer,
        )
        if diag_result:
            ability_update = diag_result.get("ability_delta", {})
            friction_tags = diag_result.get("friction_tags", [])

            if ability_update:
                avg_delta = sum(v for v in ability_update.values() if isinstance(v, (int, float))) / max(len(ability_update), 1)
                if avg_delta >= 5:
                    result_level = "good"
                elif avg_delta >= 2:
                    result_level = "medium"
                elif avg_delta >= 0:
                    result_level = "partial"
                else:
                    result_level = "weak"
            else:
                result_level = "medium"

            issues = friction_tags if friction_tags else []
            suggestions = diag_result.get("suggestions", [])
            feedback_detail = ReviewFeedbackDetail(
                correctness=result_level,
                clarity=result_level,
                naturalness=result_level,
                issues=issues,
                suggestions=suggestions,
            )
    except Exception as e:
        logger.warning(f"AI review evaluation failed, using rule-based evaluation: {e}")
        review_type = review_item.get("review_type", "recall")
        result_level, feedback_detail = _rule_based_review_evaluation(user_answer, review_type)

    return result_level, feedback_detail, ability_update, _fetched_node_status


def _calculate_review_schedule(
    result_level: str,
    history_count: int,
    review_type: str,
) -> tuple[bool, str | None, str]:
    """Calculate review completion status, next due time, and interval.

    Returns (success, next_due_iso, status_string).
    """
    success = result_level in ("good", "medium")
    partial = result_level == "partial"
    if partial:
        interval_days = _REVIEW_FAILURE_INTERVAL
    else:
        interval_days = _get_next_review_interval(history_count, success, review_type)

    now = datetime.now()
    if success and interval_days is None:
        next_due = None
    elif interval_days is not None:
        next_due = (now + timedelta(days=interval_days)).isoformat()
    else:
        next_due = None

    return success, next_due, "completed" if success else "failed"


async def _apply_review_ability_update(
    ability: dict,
    ability_update: dict | None,
    review_item: dict,
    result_level: str,
    success: bool,
    now: datetime,
) -> dict:
    """Apply ability delta from review, update recall confidence, and create snapshot.

    Returns updated ability dict.
    """
    topic_id = review_item["topic_id"]
    node_id = review_item["node_id"]
    review_type = review_item.get("review_type", "recall")

    if ability_update:
        practice_type_for_dim = _REVIEW_TYPE_PRACTICE_MAP.get(review_type, "recall")
        allowed_dims = set(PRACTICE_DIMENSION_MAP.get(practice_type_for_dim, ["recall", "explain"]))
        filtered_delta = {dim: int(delta) for dim, delta in ability_update.items() if dim in allowed_dims and isinstance(delta, (int, float))}
        record = AbilityRecord(**ability)
        delta_obj = AbilityDelta(**{k: filtered_delta.get(k, 0) for k in AbilityDelta.model_fields})
        updated = apply_delta(record, delta_obj)
        for dim in AbilityDelta.model_fields:
            if dim in allowed_dims:
                ability[dim] = getattr(updated, dim)

    # Update recall confidence
    current_confidence = ability.get("recall_confidence", 1.0)
    new_confidence = _calculate_recall_confidence(current_confidence, success)
    ability["recall_confidence"] = round(new_confidence, 4)
    ability["last_reviewed_at"] = now.isoformat()
    ability["review_history_count"] = (ability.get("review_history_count") or 0) + 1

    return ability


async def submit_review(
    db: aiosqlite.Connection,
    review_id: str,
    user_answer: str,
    neo4j=None,
    session_id: str | None = None,
) -> ReviewResult:
    """Submit a review answer, with AI-powered evaluation when possible.

    Returns ReviewResult with:
    - result: FeedbackLevel ("good"/"medium"/"partial"/"weak")
    - feedback: structured ReviewFeedbackDetail
    - ability_update: ability delta dict
    - next_due_time: ISO timestamp or None
    - needs_relearn: bool
    """
    review_item = await sqlite_repo.get_review_item(db, review_id)
    if not review_item:
        raise ValueError(f"Review item {review_id} not found")

    # Idempotency: skip re-processing already completed/failed reviews
    if review_item.get("status") in ("completed", "failed"):
        logger.info("Review %s already %s, returning existing result", review_id, review_item["status"])
        return ReviewResult(
            result=review_item.get("last_result", "medium") or "medium",
            feedback=ReviewFeedbackDetail().model_dump(),
            ability_update=None,
            next_due_time=review_item.get("next_review_at"),
            needs_relearn=(review_item.get("last_result") in ("weak", "partial")),
        )

    topic_id = review_item["topic_id"]
    node_id = review_item["node_id"]

    # Evaluate answer (AI or rule-based fallback)
    result_level, feedback_detail, ability_update, _fetched_node_status = await _evaluate_review_answer(
        review_item, user_answer, neo4j,
    )

    # Calculate schedule
    history_count = await sqlite_repo.count_review_items(db, topic_id=topic_id, node_id=node_id, status="completed")
    review_type = review_item.get("review_type", "spaced")
    success, next_due, status_str = _calculate_review_schedule(result_level, history_count, review_type)

    # Persist review result
    now = datetime.now()
    new_history_count = history_count + 1
    await sqlite_repo.update_review_item(db, review_id, {
        "status": status_str,
        "last_result": result_level,
        "completed_at": now.isoformat() if success else None,
        "next_review_at": next_due,
        "history_count": new_history_count,
    })

    # Apply ability update
    ability = await sqlite_repo.get_ability_record(db, topic_id, node_id)
    if ability is None:
        ability = AbilityRecord(topic_id=topic_id, node_id=node_id).model_dump()

    if ability:
        ability = await _apply_review_ability_update(ability, ability_update, review_item, result_level, success, now)
        await sqlite_repo.upsert_ability_record(db, ability)

        # Create ability snapshot for review tracking
        try:
            snapshot_data = {
                "understand": ability.get("understand", 0),
                "example": ability.get("example", 0),
                "contrast": ability.get("contrast", 0),
                "apply": ability.get("apply", 0),
                "explain": ability.get("explain", 0),
                "recall": ability.get("recall", 0),
                "transfer": ability.get("transfer", 0),
                "teach": ability.get("teach", 0),
                "practice_type": review_type,
                "feedback_correctness": result_level,
            }
            await sqlite_repo.create_ability_snapshot(
                db, topic_id, snapshot_data, node_id=node_id, session_id=session_id,
            )
        except Exception as e:
            logger.warning(f"Failed to create ability snapshot for review: {e}")

        # Auto-transition node status
        await _auto_transition_node_status(db, topic_id, node_id, ability, neo4j=neo4j, current_status=_fetched_node_status)

    return ReviewResult(
        result=result_level,
        feedback=feedback_detail.model_dump(),
        ability_update=ability_update,
        next_due_time=next_due,
        needs_relearn=result_level in ("weak", "partial"),
    )


# Learning intent priority multipliers for review queue
_INTENT_PRIORITY_WEIGHTS: dict[str, dict[str, float]] = {
    "fix_gap": {"recall": 2.0, "explain": 1.5, "contrast": 1.0, "apply": 0.8},
    "build_system": {"recall": 1.0, "explain": 1.0, "contrast": 1.0, "apply": 1.0},
    "solve_task": {"apply": 2.0, "transfer": 1.5, "contrast": 1.0, "recall": 0.8},
    "prepare_expression": {"explain": 2.0, "teach": 1.5, "contrast": 1.0, "recall": 0.8},
    "prepare_interview": {"apply": 2.0, "contrast": 1.5, "explain": 1.5, "recall": 1.0},
}


async def generate_review_queue(
    db: aiosqlite.Connection,
    topic_id: str,
    neo4j=None,
    learning_intent: str = "build_system",
    max_per_topic: int = 10,
) -> list[dict]:
    """Generate review items for a topic based on ability records.

    Uses the full ReviewPriority formula with learning intent weighting:
    ReviewPriority = Importance * ForgetRisk * ExplainGap * ConfusionRisk * TimeDueWeight * IntentWeight
    """
    records = await sqlite_repo.list_ability_records(db, topic_id)

    # Pre-fetch node importance from Neo4j if available
    node_importance: dict[str, int] = {}
    if neo4j:
        try:
            from backend.repositories import neo4j_repo as graph
            async with neo4j.session() as session:
                node_result = await session.run(
                    "MATCH (c:Concept {topic_id: $topic_id}) RETURN c.node_id AS node_id, c.importance AS importance",
                    {"topic_id": topic_id},
                )
                for record in await node_result.data():
                    nid = record.get("node_id", "")
                    imp = record.get("importance", 3)
                    if nid:
                        node_importance[nid] = int(imp) if imp else 3
        except Exception as e:
            logger.warning(f"Failed to fetch node importance from Neo4j: {e}")

    # Batch pre-fetch all existing reviews and frictions to avoid N+1 queries
    all_existing_reviews = await sqlite_repo.list_review_items(db, topic_id=topic_id, limit=None)
    # Build per-node review history counts and pending/due set
    node_review_counts: dict[str, int] = {}
    node_has_pending: dict[str, bool] = {}
    node_next_scheduled_at: dict[str, datetime] = {}
    node_due_from_history: dict[str, datetime] = {}
    node_due_reason_from_history: dict[str, str] = {}
    now = datetime.now()
    for rev in all_existing_reviews:
        nid = rev.get("node_id", "")
        if not nid:
            continue
        if rev.get("status") == "completed":
            node_review_counts[nid] = node_review_counts.get(nid, 0) + 1
        if rev.get("status") in ("pending", "due"):
            node_has_pending[nid] = True
        next_review_at = rev.get("next_review_at") or (
            rev.get("due_at") if rev.get("status") == "snoozed" else None
        )
        if not next_review_at:
            continue
        try:
            scheduled_at = datetime.fromisoformat(next_review_at)
        except (TypeError, ValueError):
            continue
        if scheduled_at > now:
            existing_schedule = node_next_scheduled_at.get(nid)
            if existing_schedule is None or scheduled_at < existing_schedule:
                node_next_scheduled_at[nid] = scheduled_at
        else:
            existing_due = node_due_from_history.get(nid)
            if existing_due is None or scheduled_at > existing_due:
                node_due_from_history[nid] = scheduled_at
                node_due_reason_from_history[nid] = (rev.get("reason") or "").strip()

    # Batch pre-fetch all frictions for this topic
    all_frictions = await sqlite_repo.list_frictions(db, topic_id)
    # Group frictions by node_id
    node_frictions: dict[str, list[dict]] = {}
    for f in all_frictions:
        nid = f.get("node_id", "")
        if nid:
            node_frictions.setdefault(nid, []).append(f)

    created = []
    _pending_anchors: list[dict] = []
    for r in records:
        scores = [r.get(d, 0) for d in ["understand", "example", "contrast", "apply", "explain", "recall", "transfer", "teach"]]
        avg = sum(scores) / len(scores) if scores else 0
        max_score = max(scores) if scores else 0

        # Only generate reviews for nodes that have been meaningfully practiced
        # (at least one dimension > 0) and have room for improvement (avg < 70)
        if avg < 70 and max_score > 0:
            node_id = r["node_id"]
            # Use pre-fetched data
            frictions = node_frictions.get(node_id, [])
            history_count = node_review_counts.get(node_id, 0)

            # Get importance from Neo4j or default to 3
            importance = node_importance.get(r["node_id"], 3)
            due_at = node_due_from_history.get(node_id, now).isoformat()

            priority = calculate_review_priority(
                importance=importance,
                history_count=history_count,
                understand_score=r.get("understand", 0),
                explain_score=r.get("explain", 0),
                frictions=frictions,
                due_at=due_at,
            )

            # Apply learning intent weighting
            review_type = _suggest_review_type(r)
            intent_weights = _INTENT_PRIORITY_WEIGHTS.get(learning_intent, {})
            if intent_weights:
                weakest_dim = min(
                    (d for d in ["recall", "explain", "contrast", "apply", "teach", "transfer"]
                     if r.get(d, 0) > 0),
                    key=lambda d: r.get(d, 0),
                    default=None,
                )
                if weakest_dim and weakest_dim in intent_weights:
                    priority *= intent_weights[weakest_dim]
                priority = round(priority, 4)

            # Check for existing pending review for this (topic_id, node_id) to avoid duplicates
            has_existing = node_has_pending.get(node_id, False)
            if has_existing:
                continue
            scheduled_future = node_next_scheduled_at.get(node_id)
            if scheduled_future and not _should_reschedule_future_review(
                scheduled_future,
                now,
                history_count,
            ):
                continue

            # Build reason string
            reason_parts = []
            prior_due_reason = node_due_reason_from_history.get(node_id)
            if prior_due_reason:
                reason_parts.append(prior_due_reason)
            else:
                ability_by_dimension = {
                    "understand": r.get("understand", 0),
                    "example": r.get("example", 0),
                    "contrast": r.get("contrast", 0),
                    "apply": r.get("apply", 0),
                    "explain": r.get("explain", 0),
                    "recall": r.get("recall", 0),
                    "transfer": r.get("transfer", 0),
                    "teach": r.get("teach", 0),
                }
                weakest = min(ability_by_dimension, key=ability_by_dimension.get)
                weakest_dim_map = {"recall": "记忆薄弱", "contrast": "对比不清", "explain": "理解不足", "example": "缺乏例子", "apply": "应用困难", "transfer": "迁移困难", "teach": "教学困难", "understand": "理解不足"}
                reason_parts.append(f"{weakest_dim_map.get(weakest, '能力不足')}")
            if len(frictions) > 0:
                reason_parts.append(f"有{len(frictions)}个卡点")
            if priority > 0.3:
                reason_parts.append("优先级较高")
            reason = "，".join(reason_parts)

            item = ReviewItem.create(topic_id, ReviewItemCreate(
                node_id=r["node_id"],
                review_type=review_type,
                priority=priority,
                due_at=due_at,
                reason=reason,
            ))
            created.append(item.model_dump())

            # Collect anchor data for batch Neo4j write (1 session instead of N)
            if neo4j:
                ra_id = item.review_id
                _pending_anchors.append({
                    "review_anchor_id": ra_id,
                    "node_id": r["node_id"],
                    "priority": priority,
                    "topic_id": topic_id,
                })

    # Apply per-topic density limit
    if max_per_topic > 0 and len(created) > max_per_topic:
        created.sort(key=lambda x: x.get("priority", 0), reverse=True)
        created = created[:max_per_topic]

    # Batch-create all review items in SQLite (N queries -> 1)
    if created:
        await sqlite_repo.batch_create_review_items(db, created)

    # Batch-create all ReviewAnchors in a single Neo4j session (N sessions -> 1)
    if neo4j and _pending_anchors:
        try:
            from backend.repositories import neo4j_repo as graph
            async with neo4j.session() as session:
                # Batch MERGE ReviewAnchor nodes
                await session.run(
                    """UNWIND $items AS item
                       MERGE (ra:ReviewAnchor {review_anchor_id: item.review_anchor_id})
                       SET ra.node_id = item.node_id, ra.priority = item.priority,
                           ra.topic_id = item.topic_id, ra.created_at = $created_at""",
                    {"items": _pending_anchors, "created_at": datetime.now().isoformat()},
                )
                # Batch create relationships
                await session.run(
                    """UNWIND $items AS item
                       MATCH (c:Concept {node_id: item.node_id}), (ra:ReviewAnchor {review_anchor_id: item.review_anchor_id})
                       MERGE (c)-[:HAS_REVIEW_ANCHOR]->(ra)""",
                    {"items": _pending_anchors},
                )
        except Exception as ra_err:
            logger.warning(f"Failed to batch-create ReviewAnchors in Neo4j: {ra_err}")
            for anchor in _pending_anchors:
                await sqlite_repo.record_sync_event(
                    db,
                    topic_id=anchor["topic_id"],
                    node_id=anchor["node_id"],
                    storage_kind="neo4j",
                    operation="review.create_anchor",
                    status="pending",
                    error_message=str(ra_err),
                    payload={"review_id": anchor["review_anchor_id"], "priority": anchor["priority"]},
                )

    return created


async def generate_global_review_queue(
    db: aiosqlite.Connection,
    neo4j=None,
    max_per_topic: int = 10,
) -> list[dict]:
    """Generate review items across all active topics with dynamic density.

    Distributes review slots proportionally based on the number of
    nodes needing review in each topic.
    """
    topics = await sqlite_repo.list_topics(db, status="active")
    all_created = []
    for topic in topics:
        tid = topic["topic_id"]
        learning_intent = topic.get("learning_intent", "build_system")
        try:
            created = await generate_review_queue(
                db, tid, neo4j=neo4j, learning_intent=learning_intent,
                max_per_topic=max_per_topic,
            )
            all_created.extend(created)
        except Exception as e:
            logger.warning("generate_global_review_queue: failed for topic %s: %s", tid, e)
    return all_created
