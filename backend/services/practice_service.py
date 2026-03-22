"""Practice service - practice submission orchestration."""

import asyncio
import json
import logging
from datetime import datetime

import aiosqlite

logger = logging.getLogger(__name__)

from backend.models.practice import PracticeAttempt, PracticeSubmit, PracticeResult, PracticeFeedback
from backend.models.ability import AbilityRecord, AbilityDelta, apply_delta, PRACTICE_DIMENSION_MAP

# Valid ability dimension names — whitelist for AI-returned ability_delta keys
_VALID_ABILITY_DIMS = frozenset(AbilityDelta.model_fields.keys())
from backend.models.friction import FrictionRecord
from backend.models.expression import ExpressionAsset, ExpressionAssetCreate
from backend.repositories import sqlite_repo
from backend.agents import tutor as tutor_agent
from backend.agents import diagnoser as diagnoser_agent


class PracticeSessionNotFoundError(ValueError):
    """Raised when a practice submission references a missing or foreign session."""


class PracticeSessionNotActiveError(ValueError):
    """Raised when a practice submission references a non-active session."""


async def _get_node_info(db: aiosqlite.Connection, neo4j, node_id: str) -> dict:
    """Try to get node name/summary from Neo4j, fallback to empty strings."""
    name = ""
    summary = ""
    if neo4j:
        try:
            from backend.repositories import neo4j_repo as graph
            async with neo4j.session() as session:
                node = await graph.get_concept_node(session, node_id)
                if node:
                    name = node.get("name", "")
                    summary = node.get("summary", "")
        except Exception as e:
            logger.warning(f"Failed to get node info for practice: {e}")
    return {"name": name, "summary": summary}


def _rule_based_ability_delta(practice_type: str, feedback: dict) -> dict:
    """Rule-based fallback for ability delta when AI diagnosis fails."""
    correctness = feedback.get("correctness", "medium")
    score_map = {"good": 8, "medium": 4, "weak": 1}
    base = score_map.get(correctness, 4)
    allowed_dims = PRACTICE_DIMENSION_MAP.get(practice_type, ["understand", "explain"])
    delta = {dim: base for dim in allowed_dims}
    # Slightly reduce for weak
    if correctness == "weak":
        delta = {dim: max(-3, base - 5) for dim in allowed_dims}
    return delta


def _log_friction_update_result(task: asyncio.Task, topic_id: str, node_id: str, session_id: str) -> None:
    """Log unhandled exceptions from fire-and-forget friction update."""
    exc = task.exception()
    if exc:
        logger.error(f"Async friction update failed: topic={topic_id} node={node_id} session={session_id}: {exc}", exc_info=exc)


async def _validate_practice_session(
    db: aiosqlite.Connection,
    topic_id: str,
    session_id: str | None,
) -> dict | None:
    if not session_id:
        return None

    session = await sqlite_repo.get_session(db, session_id)
    if not session or session.get("topic_id") != topic_id:
        raise PracticeSessionNotFoundError(f"Session {session_id} not found for topic {topic_id}")
    if session.get("status") != "active":
        raise PracticeSessionNotActiveError(f"Session {session_id} is not active")
    return session


async def submit_practice(
    db: aiosqlite.Connection,
    topic_id: str,
    node_id: str,
    data: PracticeSubmit,
    neo4j=None,
    feedback: dict | None = None,
    ability_delta: dict | None = None,
    friction_tags: list[str] | None = None,
) -> PracticeResult:
    """Submit a practice attempt with Tutor AI feedback and update ability/friction records."""
    await _validate_practice_session(db, topic_id, data.session_id)

    # Pre-fetch shared data (avoids duplicate DB calls in Tutor and Diagnoser blocks)
    topic_data = await sqlite_repo.get_topic(db, topic_id)
    learning_intent = topic_data.get("learning_intent", "build_system") if topic_data else "build_system"
    node_info = await _get_node_info(db, neo4j, node_id)

    # 1. Generate AI feedback if not provided
    if feedback is None:
        try:
            if node_info["name"]:
                feedback = await tutor_agent.generate_feedback(
                    node_name=node_info["name"],
                    node_summary=node_info["summary"],
                    practice_type=data.practice_type,
                    prompt_text=data.prompt_text,
                    user_answer=data.user_answer,
                    learning_intent=learning_intent,
                )
        except Exception as e:
            logger.warning(f"Tutor AI feedback failed, using fallback: {e}")

    # Use static fallback if AI still didn't produce feedback
    if feedback is None:
        feedback = tutor_agent.static_feedback_fallback()

    # 1b. Run Diagnoser (friction identification)
    diagnosis_fallback_used = False
    _misconception_hints: list[str] = []
    if ability_delta is None or friction_tags is None:
        try:
            if node_info["name"]:
                # Get existing ability and friction history for context
                existing_ability = await sqlite_repo.get_ability_record(db, topic_id, node_id)
                existing_frictions = await sqlite_repo.list_frictions(db, topic_id, node_id=node_id, limit=10)
                friction_history = [f.get("friction_type", "") for f in existing_frictions] if existing_frictions else None

                diag_result = await diagnoser_agent.diagnose(
                    node_name=node_info["name"],
                    node_summary=node_info["summary"],
                    practice_type=data.practice_type,
                    prompt_text=data.prompt_text,
                    user_answer=data.user_answer,
                    ability_record=dict(existing_ability) if existing_ability else None,
                    friction_history=friction_history,
                    learning_intent=learning_intent,
                )
                if diag_result:
                    if friction_tags is None:
                        friction_tags = diag_result.get("friction_tags", [])
                    if ability_delta is None:
                        ability_delta = diag_result.get("ability_delta", {})
                    _misconception_hints = diag_result.get("misconception_hints", [])
        except Exception as e:
            logger.warning(f"Diagnoser AI failed, using fallback: {e}")
            diagnosis_fallback_used = True
            diag_result = diagnoser_agent.diagnose_fallback()
            if friction_tags is None:
                friction_tags = diag_result.get("friction_tags", [])
            if ability_delta is None:
                ability_delta = diag_result.get("ability_delta", {})

    # 1c. Schedule async friction update (fire-and-forget after response)
    # Also compute recommended practice types from friction tags
    _recommended_practice_types: list[str] | None = None
    if friction_tags:
        _recommended_practice_types = []
        _friction_practice_map = {
            "prerequisite_gap": ["define", "explain"],
            "weak_structure": ["compress", "define"],
            "concept_confusion": ["contrast", "explain"],
            "vague_expression": ["example", "apply"],
        }
        for tag in friction_tags:
            for pt in _friction_practice_map.get(tag, []):
                if pt not in _recommended_practice_types:
                    _recommended_practice_types.append(pt)

    async def _async_friction_update():
        # Use a separate SQLite connection to avoid WAL write contention
        # with the main request's db connection
        from backend.core.config import get_settings
        async_db = None
        try:
            settings = get_settings()
            async_db = await aiosqlite.connect(settings.sqlite_path)
            async_db.row_factory = aiosqlite.Row

            tags_to_write = friction_tags
            misconception_hints_to_write = _misconception_hints
            if tags_to_write:
                _friction_records = [
                    FrictionRecord.create(
                        topic_id=topic_id,
                        node_id=node_id,
                        friction_type=tag,
                        session_id=data.session_id,
                    ).model_dump()
                    for tag in tags_to_write
                ]
                await sqlite_repo.batch_create_friction_records(async_db, _friction_records)

            # Persist misconception_hints to Neo4j if available (batch UNWIND)
            if misconception_hints_to_write and neo4j:
                try:
                    from backend.repositories import neo4j_repo as graph
                    from backend.models.common import generate_id
                    _mc_hints = misconception_hints_to_write[:3]
                    _mc_items = [{"node_id": generate_id("mc"), "description": h, "severity": 1, "topic_id": topic_id} for h in _mc_hints]
                    async with neo4j.session() as session:
                        await session.run(
                            """UNWIND $items AS item
                               MERGE (m:Misconception {node_id: item.node_id})
                               SET m.description = item.description, m.severity = item.severity, m.topic_id = item.topic_id""",
                            {"items": _mc_items},
                        )
                        await session.run(
                            """UNWIND $items AS item
                               MATCH (c:Concept {node_id: $node_id}), (m:Misconception {node_id: item.node_id})
                               MERGE (c)-[:HAS_MISCONCEPTION]->(m)""",
                            {"node_id": node_id, "items": _mc_items},
                        )
                except Exception as mc_err:
                    logger.warning(f"Failed to persist misconception to Neo4j: {mc_err}")
                    await sqlite_repo.record_sync_event(
                        async_db,
                        topic_id=topic_id,
                        session_id=data.session_id,
                        node_id=node_id,
                        storage_kind="neo4j",
                        operation="practice.persist_misconceptions",
                        status="pending",
                        error_message=str(mc_err),
                        payload={"count": len(misconception_hints_to_write[:3])},
                    )

            # Persist evidence from user_answer as diagnostic evidence node
            if neo4j and data.user_answer:
                try:
                    from backend.repositories import neo4j_repo as graph
                    from backend.models.common import generate_id
                    async with neo4j.session() as session:
                        ev_id = generate_id("ev")
                        await graph.create_evidence_node(session, {
                            "node_id": ev_id,
                            "text": data.user_answer[:500],
                            "source": f"practice:{data.practice_type}",
                            "topic_id": topic_id,
                        })
                        await graph.link_evidence_to_concept(session, node_id, ev_id)
                except Exception as ev_err:
                    logger.warning(f"Failed to persist evidence to Neo4j: {ev_err}")
                    await sqlite_repo.record_sync_event(
                        async_db,
                        topic_id=topic_id,
                        session_id=data.session_id,
                        node_id=node_id,
                        storage_kind="neo4j",
                        operation="practice.persist_evidence",
                        status="pending",
                        error_message=str(ev_err),
                        payload={"practice_type": data.practice_type},
                    )
        except Exception as e:
            logger.warning(f"Async friction update failed: {e}")
        finally:
            if async_db:
                await async_db.close()

    if friction_tags:
        # Launch friction update with timeout (GROW-H1-004)
        async def _run_friction_with_timeout():
            try:
                await asyncio.wait_for(_async_friction_update(), timeout=30)
            except asyncio.TimeoutError:
                logger.error(
                    "Async friction update timed out: topic=%s node=%s session=%s",
                    topic_id, node_id, data.session_id,
                )
                try:
                    await sqlite_repo.record_sync_event(
                        db,
                        topic_id=topic_id,
                        session_id=data.session_id,
                        node_id=node_id,
                        storage_kind="sqlite",
                        operation="practice.friction_timeout",
                        status="pending",
                        error_message="Friction update timed out after 30s",
                    )
                except Exception:
                    pass

        _task = asyncio.create_task(_run_friction_with_timeout())
        _task.add_done_callback(lambda t: _log_friction_update_result(t, topic_id, node_id, data.session_id))

    # 2. Create practice attempt
    attempt = PracticeAttempt.create(
        topic_id=topic_id,
        node_id=node_id,
        practice_type=data.practice_type,
        user_answer=data.user_answer,
        session_id=data.session_id,
        prompt_text=data.prompt_text,
    )

    feedback_str = ""
    scores = {}
    if feedback:
        feedback_str = json.dumps(feedback)
        scores = {
            "correctness": feedback.get("correctness", ""),
            "clarity": feedback.get("clarity", ""),
            "naturalness": feedback.get("naturalness", ""),
        }

    attempt_dict = attempt.model_dump()
    attempt_dict["feedback"] = feedback_str
    attempt_dict["scores"] = scores
    await sqlite_repo.create_practice_attempt(db, attempt_dict)

    # 3. Update ability record
    updated_ability = None
    # Use rule-based fallback if AI diagnosis didn't produce ability_delta
    if not ability_delta and feedback:
        ability_delta = _rule_based_ability_delta(data.practice_type, feedback)
    # Filter ability_delta to only valid dimension names, then to practice-relevant ones
    if ability_delta:
        allowed_dims = PRACTICE_DIMENSION_MAP.get(data.practice_type, [])
        filtered_delta = {k: v for k, v in ability_delta.items() if k in _VALID_ABILITY_DIMS and k in allowed_dims}
        if not filtered_delta:
            filtered_delta = _rule_based_ability_delta(data.practice_type, feedback)
        ability_delta = filtered_delta

        existing = await sqlite_repo.get_ability_record(db, topic_id, node_id)
        existing_data = dict(existing) if existing else {}
        # Remove keys already provided explicitly to avoid duplicate kwarg error
        existing_data.pop("topic_id", None)
        existing_data.pop("node_id", None)
        existing_data = {key: value for key, value in existing_data.items() if value is not None}
        record = AbilityRecord(
            topic_id=topic_id,
            node_id=node_id,
            **existing_data,
        )
        delta = AbilityDelta(**ability_delta)
        updated = apply_delta(record, delta)
        await sqlite_repo.upsert_ability_record(db, updated.model_dump())
        updated_ability = updated.model_dump()

    # 3b. Record ability snapshot for historical tracking
    try:
        if updated_ability:
            snapshot_data = {
                "understand": updated_ability.get("understand", 0),
                "example": updated_ability.get("example", 0),
                "contrast": updated_ability.get("contrast", 0),
                "apply": updated_ability.get("apply", 0),
                "explain": updated_ability.get("explain", 0),
                "recall": updated_ability.get("recall", 0),
                "transfer": updated_ability.get("transfer", 0),
                "teach": updated_ability.get("teach", 0),
                "practice_type": data.practice_type,
                "feedback_correctness": feedback.get("correctness", "") if feedback else "",
            }
            await sqlite_repo.create_ability_snapshot(
                db, topic_id, snapshot_data, node_id=node_id, session_id=data.session_id,
            )
    except Exception as e:
        logger.warning(f"Failed to create ability snapshot: {e}")
        try:
            await sqlite_repo.record_sync_event(
                db,
                topic_id=topic_id,
                session_id=data.session_id,
                node_id=node_id,
                storage_kind="sqlite",
                operation="practice.create_ability_snapshot",
                status="pending",
                error_message=str(e),
            )
        except Exception as sync_err:
            logger.warning(f"Failed to record sync event for ability snapshot: {sync_err}")

    # 5. Build result
    return PracticeResult(
        attempt_id=attempt.attempt_id,
        feedback=feedback,
        recommended_answer=feedback.get("recommended_answer", "") if feedback else "",
        expression_skeleton=feedback.get("expression_skeleton", "") if feedback else "",
        ability_update=updated_ability,
        friction_tags=friction_tags or [],
        diagnosis_fallback=diagnosis_fallback_used,
        next_practice_recommendation=_recommended_practice_types or [],
    )


async def save_expression_asset(
    db: aiosqlite.Connection,
    topic_id: str,
    node_id: str,
    data: ExpressionAssetCreate,
    session_id: str | None = None,
) -> dict:
    """Save an expression asset."""
    if not session_id and data.attempt_id:
        attempt = await sqlite_repo.get_practice_attempt(db, data.attempt_id)
        if (
            attempt
            and attempt.get("topic_id") == topic_id
            and attempt.get("node_id") == node_id
        ):
            session_id = attempt.get("session_id")

    asset = ExpressionAsset.create(topic_id, node_id, data, session_id)
    return await sqlite_repo.create_expression_asset(db, asset.model_dump())


async def list_expression_assets(
    db: aiosqlite.Connection,
    topic_id: str,
    node_id: str | None = None,
    expression_type: str | None = None,
    limit: int = 20,
    favorited: bool | None = None,
    session_id: str | None = None,
) -> list[dict]:
    """List expression assets."""
    return await sqlite_repo.list_expression_assets(
        db,
        topic_id,
        node_id=node_id,
        expression_type=expression_type,
        favorited=favorited,
        limit=limit,
        session_id=session_id,
    )


PRACTICE_SEQUENCE = ["define", "example", "contrast", "apply", "teach_beginner", "compress"]


async def get_recommended_practice_type(db: aiosqlite.Connection, topic_id: str, node_id: str) -> dict:
    """Recommend the next practice type based on completed practice history and time gaps."""
    attempts = await sqlite_repo.get_practice_attempts(db, topic_id, node_id, limit=50)
    completed_types = set(a.get("practice_type", "") for a in attempts)

    # Find first uncompleted type in sequence
    for pt in PRACTICE_SEQUENCE:
        if pt not in completed_types:
            return {"recommended_type": pt, "reason": f"推荐练习类型：{pt}（尚未完成）"}

    # All completed — consider time since last practice per type for variety
    from datetime import datetime, timedelta
    now = datetime.now()
    type_last_practiced: dict[str, datetime] = {}
    for a in attempts:
        pt = a.get("practice_type", "")
        created = a.get("created_at", "")
        if pt and created:
            try:
                ts = datetime.fromisoformat(created)
                if pt not in type_last_practiced or ts > type_last_practiced[pt]:
                    type_last_practiced[pt] = ts
            except (ValueError, TypeError):
                pass

    # Prefer types not practiced in the last 24h for spaced variety
    stale_types = [pt for pt in PRACTICE_SEQUENCE
                   if pt in type_last_practiced and (now - type_last_practiced[pt]) > timedelta(hours=24)]
    if stale_types:
        return {"recommended_type": stale_types[0], "reason": f"推荐练习类型：{stale_types[0]}（已超过 24 小时未练习）"}

    # Fall back to weakest dimension
    ability = await sqlite_repo.get_ability_record(db, topic_id, node_id)
    if ability:
        dims = {dim: ability.get(dim, 0) for dim in AbilityDelta.model_fields if dim in ability}
        if dims:
            weakest = min(dims, key=dims.get)
            for pt, related_dims in PRACTICE_DIMENSION_MAP.items():
                if weakest in related_dims:
                    return {"recommended_type": pt, "reason": f"推荐练习类型：{pt}（{weakest}维度最薄弱）"}

    return {"recommended_type": "define", "reason": "推荐从定义表达开始"}


async def get_practice_prompt(
    db: aiosqlite.Connection,
    topic_id: str,
    node_id: str,
    practice_type: str,
    neo4j=None,
    regenerate: bool = False,
    difficulty: str | None = None,
) -> dict:
    """Generate a practice prompt for a node, with cache and static fallback."""
    difficulty = difficulty or "medium"
    # Fetch learning_intent early for cache key correctness
    learning_intent = "build_system"
    try:
        topic_data = await sqlite_repo.get_topic(db, topic_id)
        if topic_data:
            learning_intent = topic_data.get("learning_intent", "build_system")
    except Exception:
        pass
    # Check cache first (unless regenerate is true)
    if not regenerate:
        cached = await sqlite_repo.get_cached_practice_prompt(db, topic_id, node_id, practice_type, difficulty, learning_intent)
        if cached:
            cached["cached"] = True
            if "min_answer_hint" in cached and "minimum_answer_hint" not in cached:
                cached["minimum_answer_hint"] = cached.pop("min_answer_hint")
            if "scoring_dimensions" in cached and "evaluation_dimensions" not in cached:
                cached["evaluation_dimensions"] = cached.pop("scoring_dimensions")
            if "requirements" in cached:
                cached.pop("requirements")
            return cached, True

    # Try AI-generated prompt
    ai_result = None
    try:
        node_info = await _get_node_info(db, neo4j, node_id)
        if node_info["name"]:
            # Get current ability for adaptive difficulty
            ability_record = None
            try:
                ability_record = await sqlite_repo.get_ability_record(db, topic_id, node_id)
            except Exception as e:
                logger.warning(f"Failed to get ability record for practice: {e}")

            # Get historical expression assets
            expression_assets = None
            try:
                expression_assets = await sqlite_repo.list_expression_assets(db, topic_id, node_id, limit=3)
            except Exception as e:
                logger.warning(f"Failed to get expression assets for practice prompt: {e}")

            # Get misconceptions
            misconceptions = None
            try:
                if neo4j:
                    from backend.repositories import neo4j_repo as graph
                    async with neo4j.session() as session:
                        misconceptions = await graph.get_misconceptions_for_concept(session, node_id)
            except Exception as e:
                logger.warning(f"Failed to get misconceptions for practice prompt: {e}")

            ai_result = await tutor_agent.generate_practice(
                node_name=node_info["name"],
                node_summary=node_info["summary"],
                practice_type=practice_type,
                learning_intent=learning_intent,
                ability=dict(ability_record) if ability_record else None,
                difficulty=difficulty,
                expression_assets=expression_assets,
                misconceptions=misconceptions,
            )
    except Exception as e:
        logger.warning(f"Tutor AI practice prompt failed, using fallback: {e}")

    if ai_result:
        response_data = {
            "practice_type": ai_result.get("practice_type", practice_type),
            "prompt_text": ai_result.get("prompt_text", ""),
            "minimum_answer_hint": ai_result.get("minimum_answer_hint", "至少写一句话"),
            "evaluation_dimensions": ai_result.get("evaluation_dimensions", ["correctness", "clarity", "naturalness"]),
            "cached": False,
        }
        try:
            await sqlite_repo.save_practice_prompt_cache(db, topic_id, node_id, practice_type, response_data, difficulty, learning_intent)
        except Exception as e:
            logger.warning(f"Failed to cache practice prompt: {e}")
        return response_data, False

    # Static fallback
    prompts = {
        "define": "请用自己的话定义或解释这个概念。",
        "example": "请举一个具体的例子来说明这个概念。",
        "contrast": "请说明这个概念和相邻概念的区别。",
        "apply": "请描述如何在实际问题中应用这个概念。",
        "teach_beginner": "请用初学者能理解的方式解释这个概念。",
        "compress": "请用一句话总结这个概念的核心。",
        "explain": "请用自己的话解释这个概念，让不了解的人也能理解。",
    }
    return {
        "practice_type": practice_type,
        "prompt_text": prompts.get(practice_type, prompts["explain"]),
        "minimum_answer_hint": "至少写一句话",
        "evaluation_dimensions": ["correctness", "clarity", "naturalness"],
        "cached": False,
    }, False


async def toggle_favorite(db: aiosqlite.Connection, asset_id: str) -> dict | None:
    """Toggle favorite status of an expression asset."""
    return await sqlite_repo.toggle_favorite(db, asset_id)
