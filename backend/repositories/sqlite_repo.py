"""SQLite repository - database initialization and CRUD operations."""

import json
import logging
from datetime import datetime

import aiosqlite

from backend.models.common import generate_id

logger = logging.getLogger(__name__)

# Column/table name whitelists to prevent SQL injection via string interpolation
_ALLOWED_TOPIC_COLUMNS = frozenset({
    "title", "description", "status", "learning_intent", "mode",
    "entry_node_id", "total_nodes", "learned_nodes", "total_sessions",
    "total_practice", "current_node_id", "last_session_id", "source_content",
})

_ALLOWED_STAT_FIELDS = frozenset({
    "total_nodes", "learned_nodes", "total_sessions", "total_practice",
})

_ALLOWED_REVIEW_ITEM_COLUMNS = frozenset({
    "status", "due_at", "next_review_at", "last_result",
    "completed_at", "review_type", "reason", "history_count", "priority",
})

_ALLOWED_ARTICLE_COLUMNS = frozenset({
    "title", "body", "source_label", "is_editable",
})

_ALLOWED_CONCEPT_CANDIDATE_COLUMNS = frozenset({
    "status", "matched_node_id", "matched_concept_name",
    "concept_text", "confidence",
})

REVIEW_ITEMS_CREATE_TABLE_SQL = """
CREATE TABLE review_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT UNIQUE NOT NULL,
    topic_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    node_name TEXT DEFAULT '',
    priority REAL DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','completed','skipped','due','failed','snoozed','cancelled')),
    due_at TEXT,
    next_review_at TEXT,
    review_type TEXT DEFAULT 'spaced',
    reason TEXT DEFAULT '',
    last_result TEXT DEFAULT '',
    history_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);
"""

SQL_INIT_TABLES = """
CREATE TABLE IF NOT EXISTS topics (
    topic_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'active' CHECK(status IN ('active','archived','completed')),
    learning_intent TEXT DEFAULT 'build_system',
    entry_node_id TEXT,
    total_nodes INTEGER DEFAULT 0,
    learned_nodes INTEGER DEFAULT 0,
    total_practice INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    source_type TEXT DEFAULT 'concept',
    source_content TEXT DEFAULT '',
    mode TEXT DEFAULT 'full_system',
    current_node_id TEXT,
    last_session_id TEXT,
    archived_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(topic_id),
    status TEXT DEFAULT 'active' CHECK(status IN ('active','completed','abandoned')),
    visited_node_ids TEXT DEFAULT '[]',
    practice_count INTEGER DEFAULT 0,
    started_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    summary TEXT,
    entry_node_id TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS session_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id),
    node_id TEXT NOT NULL,
    visited_at TEXT DEFAULT (datetime('now')),
    visit_order INTEGER DEFAULT 0,
    entered_at TEXT,
    left_at TEXT,
    action_type TEXT DEFAULT 'open_node',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ability_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    understand INTEGER DEFAULT 0,
    example INTEGER DEFAULT 0,
    contrast INTEGER DEFAULT 0,
    apply INTEGER DEFAULT 0,
    explain INTEGER DEFAULT 0,
    recall INTEGER DEFAULT 0,
    transfer INTEGER DEFAULT 0,
    teach INTEGER DEFAULT 0,
    recall_confidence REAL DEFAULT 1.0,
    last_reviewed_at TEXT,
    review_history_count INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(topic_id, node_id)
);

CREATE TABLE IF NOT EXISTS ability_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL,
    node_id TEXT,
    session_id TEXT,
    snapshot_data TEXT DEFAULT '{}',
    understand INTEGER DEFAULT 0,
    example INTEGER DEFAULT 0,
    contrast INTEGER DEFAULT 0,
    apply INTEGER DEFAULT 0,
    explain INTEGER DEFAULT 0,
    recall INTEGER DEFAULT 0,
    transfer INTEGER DEFAULT 0,
    teach INTEGER DEFAULT 0,
    source TEXT DEFAULT 'practice',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS friction_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    friction_id TEXT UNIQUE NOT NULL,
    topic_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    session_id TEXT,
    friction_type TEXT NOT NULL,
    severity INTEGER DEFAULT 1,
    evidence_text TEXT DEFAULT '',
    suggested_next_node_id TEXT,
    description TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    resolved INTEGER DEFAULT 0,
    resolved_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expression_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT UNIQUE NOT NULL,
    topic_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    expression_type TEXT NOT NULL,
    user_expression TEXT NOT NULL,
    ai_rewrite TEXT DEFAULT '',
    expression_skeleton TEXT DEFAULT '',
    correctness INTEGER DEFAULT 0,
    clarity INTEGER DEFAULT 0,
    naturalness INTEGER DEFAULT 0,
    session_id TEXT,
    quality_tags TEXT DEFAULT '[]',
    favorited INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS practice_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id TEXT UNIQUE NOT NULL,
    topic_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    session_id TEXT,
    practice_type TEXT NOT NULL,
    prompt_text TEXT DEFAULT '',
    user_answer TEXT NOT NULL,
    feedback TEXT DEFAULT '',
    scores TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS review_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT UNIQUE NOT NULL,
    topic_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    node_name TEXT DEFAULT '',
    priority REAL DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','completed','skipped','due','failed','snoozed','cancelled')),
    due_at TEXT,
    next_review_at TEXT,
    review_type TEXT DEFAULT 'spaced',
    reason TEXT DEFAULT '',
    last_result TEXT DEFAULT '',
    history_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS deferred_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    source_node_id TEXT,
    reason TEXT DEFAULT '',
    resolved_at TEXT,
    deferred_at TEXT DEFAULT (datetime('now')),
    UNIQUE(topic_id, node_id)
);

CREATE TABLE IF NOT EXISTS sync_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    topic_id TEXT NOT NULL,
    session_id TEXT,
    node_id TEXT,
    entity_type TEXT DEFAULT 'topic',
    entity_id TEXT,
    storage_kind TEXT NOT NULL,
    target_store TEXT,
    operation TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','resolved','ignored')),
    retryable INTEGER NOT NULL DEFAULT 1,
    error_message TEXT DEFAULT '',
    payload TEXT DEFAULT '{}',
    attempt_count INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS exports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    export_id TEXT UNIQUE NOT NULL,
    topic_id TEXT NOT NULL,
    format TEXT NOT NULL DEFAULT 'markdown',
    content TEXT NOT NULL,
    file_path TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS practice_prompt_cache (
    topic_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    practice_type TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'medium',
    learning_intent TEXT NOT NULL DEFAULT 'build_system',
    prompt_text TEXT NOT NULL,
    requirements TEXT NOT NULL DEFAULT '[]',
    scoring_dimensions TEXT NOT NULL DEFAULT '[]',
    min_answer_hint TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (topic_id, node_id, practice_type, difficulty, learning_intent)
);

CREATE TABLE IF NOT EXISTS articles (
    article_id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(topic_id),
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    article_kind TEXT NOT NULL DEFAULT 'source' CHECK(article_kind IN ('source')),
    source_label TEXT DEFAULT '我的文章',
    is_editable INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS article_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mention_id TEXT UNIQUE NOT NULL,
    topic_id TEXT NOT NULL,
    article_id TEXT NOT NULL REFERENCES articles(article_id),
    concept_text TEXT NOT NULL,
    concept_name TEXT NOT NULL,
    concept_key TEXT,
    mention_type TEXT NOT NULL DEFAULT 'explicit' CHECK(mention_type IN ('explicit','recognized','candidate')),
    confidence REAL DEFAULT 0,
    paragraph_index INTEGER DEFAULT 0,
    anchor_id TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS concept_notes (
    note_id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(topic_id),
    concept_key TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(topic_id, concept_key)
);

CREATE TABLE IF NOT EXISTS article_reading_state (
    topic_id TEXT PRIMARY KEY REFERENCES topics(topic_id),
    article_id TEXT NOT NULL,
    scroll_top REAL DEFAULT 0,
    trail TEXT DEFAULT '[]',
    completed_article_ids TEXT DEFAULT '[]',
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS concept_candidates (
    candidate_id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(topic_id),
    concept_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'candidate' CHECK(status IN ('candidate','confirmed','ignored')),
    matched_node_id TEXT,
    matched_concept_name TEXT DEFAULT '',
    source_article_id TEXT,
    paragraph_index INTEGER,
    anchor_id TEXT DEFAULT '',
    origin TEXT NOT NULL DEFAULT 'manual' CHECK(origin IN ('manual','article_analysis')),
    confidence REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_topics_status ON topics(status);
CREATE INDEX IF NOT EXISTS idx_sessions_topic ON sessions(topic_id);
CREATE INDEX IF NOT EXISTS idx_ability_topic_node ON ability_records(topic_id, node_id);
CREATE INDEX IF NOT EXISTS idx_friction_topic ON friction_records(topic_id);
CREATE INDEX IF NOT EXISTS idx_review_status ON review_items(status);
CREATE INDEX IF NOT EXISTS idx_review_priority ON review_items(priority DESC);
CREATE INDEX IF NOT EXISTS idx_expression_topic ON expression_assets(topic_id);
CREATE INDEX IF NOT EXISTS idx_deferred_topic ON deferred_nodes(topic_id);
CREATE INDEX IF NOT EXISTS idx_sync_events_topic_status ON sync_events(topic_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_events_status ON sync_events(status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_events_target_status ON sync_events(target_store, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_practice_topic_node ON practice_attempts(topic_id, node_id);
CREATE INDEX IF NOT EXISTS idx_sessions_topic_status ON sessions(topic_id, status);
CREATE INDEX IF NOT EXISTS idx_review_topic ON review_items(topic_id);
CREATE INDEX IF NOT EXISTS idx_review_topic_node ON review_items(topic_id, node_id);
CREATE INDEX IF NOT EXISTS idx_friction_topic_node ON friction_records(topic_id, node_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_topic ON ability_snapshots(topic_id);
CREATE INDEX IF NOT EXISTS idx_articles_topic ON articles(topic_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_mentions_article ON article_mentions(article_id);
CREATE INDEX IF NOT EXISTS idx_mentions_concept_key ON article_mentions(topic_id, concept_key);
CREATE INDEX IF NOT EXISTS idx_notes_topic_concept ON concept_notes(topic_id, concept_key);
CREATE INDEX IF NOT EXISTS idx_candidates_topic_status ON concept_candidates(topic_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidates_topic_norm ON concept_candidates(topic_id, normalized_text);
CREATE INDEX IF NOT EXISTS idx_session_nodes_session_id ON session_nodes(session_id);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT DEFAULT (datetime('now'))
);
"""


async def _ensure_review_items_schema(db: aiosqlite.Connection):
    cursor = await db.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'review_items'",
    )
    row = await cursor.fetchone()
    if not row or not row[0]:
        return

    create_sql = str(row[0])
    info_cursor = await db.execute("PRAGMA table_info(review_items)")
    columns = {column[1] for column in await info_cursor.fetchall()}
    required_columns = {
        "review_id",
        "topic_id",
        "node_id",
        "node_name",
        "priority",
        "status",
        "due_at",
        "next_review_at",
        "review_type",
        "reason",
        "last_result",
        "history_count",
        "created_at",
        "completed_at",
        "updated_at",
    }
    normalized_sql = "".join(create_sql.lower().split())
    has_full_status_set = all(
        token in normalized_sql
        for token in ("'due'", "'failed'", "'snoozed'", "'cancelled'")
    )
    if required_columns.issubset(columns) and has_full_status_set:
        return

    await db.execute("ALTER TABLE review_items RENAME TO review_items_legacy")
    await db.execute(REVIEW_ITEMS_CREATE_TABLE_SQL)

    def column_or_default(column: str, default_sql: str) -> str:
        return column if column in columns else default_sql

    status_expr = (
        "CASE WHEN status IN ('pending','completed','skipped','due','failed','snoozed','cancelled') THEN status ELSE 'pending' END"
        if "status" in columns
        else "'pending'"
    )
    updated_at_expr = (
        "COALESCE(updated_at, completed_at, created_at, datetime('now'))"
        if "updated_at" in columns
        else "COALESCE(completed_at, created_at, datetime('now'))"
    )
    await db.execute(
        """
        INSERT INTO review_items (
            id,
            review_id,
            topic_id,
            node_id,
            node_name,
            priority,
            status,
            due_at,
            next_review_at,
            review_type,
            reason,
            last_result,
            history_count,
            created_at,
            completed_at,
            updated_at
        )
        SELECT
            id,
            review_id,
            topic_id,
            node_id,
            {node_name},
            {priority},
            {status},
            {due_at},
            {next_review_at},
            {review_type},
            {reason},
            {last_result},
            {history_count},
            {created_at},
            {completed_at},
            {updated_at}
        FROM review_items_legacy
        """.format(
            node_name=column_or_default("node_name", "''"),
            priority=column_or_default("priority", "0"),
            status=status_expr,
            due_at=column_or_default("due_at", "NULL"),
            next_review_at=column_or_default("next_review_at", "NULL"),
            review_type=column_or_default("review_type", "'spaced'"),
            reason=column_or_default("reason", "''"),
            last_result=column_or_default("last_result", "''"),
            history_count=column_or_default("history_count", "0"),
            created_at=column_or_default("created_at", "datetime('now')"),
            completed_at=column_or_default("completed_at", "NULL"),
            updated_at=updated_at_expr,
        ),
    )
    await db.execute("DROP TABLE review_items_legacy")


async def _ensure_single_active_session_per_topic(db: aiosqlite.Connection):
    """Resolve legacy double-active sessions before enforcing uniqueness."""
    await db.execute(
        """
        WITH ranked AS (
            SELECT
                rowid,
                ROW_NUMBER() OVER (
                    PARTITION BY topic_id
                    ORDER BY COALESCE(started_at, updated_at, completed_at, '') DESC, rowid DESC
                ) AS rn
            FROM sessions
            WHERE status = 'active'
        )
        UPDATE sessions
        SET status = 'abandoned', updated_at = ?
        WHERE rowid IN (SELECT rowid FROM ranked WHERE rn > 1)
        """,
        (datetime.now().isoformat(),),
    )


_CURRENT_SCHEMA_VERSION = 3


async def init_tables(db: aiosqlite.Connection):
    """Initialize all SQLite tables and run versioned migrations."""
    await db.executescript(SQL_INIT_TABLES)
    # Initialize schema_version table if empty
    try:
        await db.execute("INSERT INTO schema_version (version) SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_version)")
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to initialize schema_version: {e}")

    # Read current schema version
    cursor = await db.execute("SELECT version FROM schema_version LIMIT 1")
    row = await cursor.fetchone()
    current_version = row[0] if row else 0

    # Version 2 migrations: add missing columns to existing tables
    if current_version < 2:
        migrations = [
            ("topics", "source_type", "TEXT DEFAULT 'concept'"),
            ("topics", "source_content", "TEXT DEFAULT ''"),
            ("topics", "mode", "TEXT DEFAULT 'full_system'"),
            ("topics", "current_node_id", "TEXT"),
            ("topics", "last_session_id", "TEXT"),
            ("topics", "archived_at", "TEXT"),
            ("review_items", "node_name", "TEXT DEFAULT ''"),
            ("review_items", "reason", "TEXT DEFAULT ''"),
            ("review_items", "history_count", "INTEGER DEFAULT 0"),
            ("review_items", "updated_at", "TEXT"),
            ("friction_records", "description", "TEXT DEFAULT ''"),
            ("friction_records", "tags", "TEXT DEFAULT '[]'"),
            ("sessions", "entry_node_id", "TEXT"),
            ("practice_attempts", "prompt_text", "TEXT DEFAULT ''"),
            ("sessions", "updated_at", "TEXT"),
            ("sessions", "end_time", "TEXT"),
            ("deferred_nodes", "source_node_id", "TEXT"),
            ("deferred_nodes", "resolved_at", "TEXT"),
            ("ability_records", "recall_confidence", "REAL DEFAULT 1.0"),
            ("ability_records", "last_reviewed_at", "TEXT"),
            ("ability_records", "review_history_count", "INTEGER DEFAULT 0"),
            ("sessions", "synthesis_json", "TEXT DEFAULT ''"),
        ]
        # NOTE: migrations list is hardcoded and trusted — f-string interpolation is safe
        for table, column, col_def in migrations:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
            except Exception as e:
                logger.warning(f"Migration ALTER TABLE {table} ADD COLUMN {column} skipped: {e}")

        await db.execute(
            "UPDATE schema_version SET version = ?, updated_at = datetime('now')",
            (2,),
        )

    if current_version < 3:
        try:
            await db.execute("ALTER TABLE session_nodes ADD COLUMN created_at TEXT DEFAULT (datetime('now'))")
        except Exception as e:
            logger.warning(f"Migration ALTER TABLE session_nodes ADD COLUMN created_at skipped: {e}")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sync_events_topic_status ON sync_events(topic_id, status, created_at DESC)")
        await db.execute(
            "UPDATE schema_version SET version = ?, updated_at = datetime('now')",
            (_CURRENT_SCHEMA_VERSION,),
        )

    sync_event_migrations = [
        # v4: add difficulty to practice_prompt_cache, resolved_at to friction_records
        ("practice_prompt_cache", "difficulty", "TEXT NOT NULL DEFAULT 'medium'"),
        ("friction_records", "resolved_at", "TEXT"),
        ("practice_prompt_cache", "learning_intent", "TEXT NOT NULL DEFAULT 'build_system'"),
        ("sync_events", "entity_type", "TEXT DEFAULT 'topic'"),
        ("sync_events", "entity_id", "TEXT"),
        ("sync_events", "target_store", "TEXT"),
        ("sync_events", "retryable", "INTEGER NOT NULL DEFAULT 1"),
        ("sync_events", "attempt_count", "INTEGER NOT NULL DEFAULT 1"),
        ("sync_events", "updated_at", "TEXT"),
    ]
    # NOTE: sync_event_migrations list is hardcoded and trusted — f-string interpolation is safe
    for table, column, col_def in sync_event_migrations:
        try:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        except Exception as e:
            logger.warning(f"Migration ALTER TABLE {table} ADD COLUMN {column} skipped: {e}")

    await _ensure_review_items_schema(db)
    await db.execute("UPDATE review_items SET updated_at = COALESCE(updated_at, completed_at, created_at, datetime('now'))")
    await db.execute("UPDATE sessions SET updated_at = COALESCE(updated_at, completed_at, started_at, datetime('now'))")
    await db.execute("UPDATE session_nodes SET created_at = COALESCE(created_at, entered_at, visited_at, datetime('now'))")
    await db.execute("UPDATE sync_events SET target_store = COALESCE(target_store, storage_kind)")
    await db.execute("UPDATE sync_events SET entity_id = COALESCE(entity_id, node_id, session_id, topic_id)")
    await db.execute("UPDATE sync_events SET entity_type = COALESCE(entity_type, 'topic')")
    await db.execute("UPDATE sync_events SET updated_at = COALESCE(updated_at, resolved_at, created_at, datetime('now'))")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_review_status ON review_items(status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_review_priority ON review_items(priority DESC)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_review_topic ON review_items(topic_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_review_topic_node ON review_items(topic_id, node_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_review_updated ON review_items(updated_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_deferred_topic_resolved ON deferred_nodes(topic_id, resolved_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_sync_events_status ON sync_events(status, updated_at DESC)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_sync_events_target_status ON sync_events(target_store, status, updated_at DESC)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_session_nodes_session_id ON session_nodes(session_id)")
    await _ensure_single_active_session_per_topic(db)
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_active_topic_unique ON sessions(topic_id) WHERE status = 'active'"
    )
    await db.commit()


def _row_to_dict(row: aiosqlite.Row) -> dict:
    return dict(row)


def _decode_json(value):
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _normalize_sync_event_metadata(
    *,
    topic_id: str,
    operation: str,
    target_store: str,
    payload: dict,
    entity_type: str | None,
    entity_id: str | None,
    session_id: str | None,
    node_id: str | None,
) -> tuple[str, str, str]:
    stage = payload.get("stage")
    derived_entity_type = entity_type
    derived_entity_id = entity_id

    if operation == "topic.create":
        stage_mapping = {
            "graph_write": "create_topic_graph",
            "entry_embedding": "create_topic_entry_embedding",
            "initial_node_embeddings": "create_topic_initial_embeddings",
            "topic_embedding": "create_topic_embedding",
        }
        operation = stage_mapping.get(stage, "create_topic_sync")
        derived_entity_type = derived_entity_type or "topic"
        derived_entity_id = derived_entity_id or topic_id
    elif operation == "topic.create_source_article":
        operation = "create_initial_source_article"
        derived_entity_type = derived_entity_type or "topic"
        derived_entity_id = derived_entity_id or topic_id
    elif operation == "node.expand":
        stage_mapping = {
            "session_tracking": "expand_node_session_tracking",
            "vector_write": "expand_node_embeddings",
            "graph_write": "expand_node_graph",
        }
        operation = stage_mapping.get(stage, "expand_node_sync")
        derived_entity_type = derived_entity_type or "node_expand"
        derived_entity_id = derived_entity_id or node_id or session_id or topic_id
    elif operation == "topic.delete":
        stage_mapping = {
            "graph_delete": "delete_topic_graph",
            "vector_delete": "delete_topic_vectors",
        }
        operation = stage_mapping.get(stage, "delete_topic_sync")
        derived_entity_type = derived_entity_type or "topic_delete"
        derived_entity_id = derived_entity_id or topic_id
    elif operation == "candidate.confirm":
        stage_mapping = {
            "graph_write": "confirm_candidate_graph",
            "vector_write": "confirm_candidate_embedding",
        }
        operation = stage_mapping.get(stage, "confirm_candidate_sync")
        derived_entity_type = derived_entity_type or "concept_candidate"
        derived_entity_id = derived_entity_id or payload.get("candidate_id") or node_id or topic_id

    return operation, derived_entity_type or "topic", derived_entity_id or topic_id


def _serialize_sync_event(row: aiosqlite.Row | None) -> dict | None:
    if row is None:
        return None
    data = _row_to_dict(row)
    data["payload"] = _decode_json(data.get("payload", "{}"))
    data["retryable"] = bool(data.get("retryable", 1))
    return data


# ==================== Topics ====================

async def create_topic(db: aiosqlite.Connection, topic: dict) -> dict:
    await db.execute(
        """INSERT INTO topics (topic_id, title, description, status, learning_intent,
           entry_node_id, source_type, source_content, mode, current_node_id,
           last_session_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            topic["topic_id"],
            topic["title"],
            topic.get("description", ""),
            topic.get("status", "active"),
            topic.get("learning_intent", "build_system"),
            topic.get("entry_node_id"),
            topic.get("source_type", "concept"),
            topic.get("source_content", ""),
            topic.get("mode", "full_system"),
            topic.get("current_node_id"),
            topic.get("last_session_id"),
            topic.get("created_at", datetime.now().isoformat()),
            topic.get("updated_at", datetime.now().isoformat()),
        ),
    )
    await db.commit()
    return await get_topic(db, topic["topic_id"])


async def get_topic(db: aiosqlite.Connection, topic_id: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM topics WHERE topic_id = ?", (topic_id,))
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def list_topics(
    db: aiosqlite.Connection,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    query = "SELECT * FROM topics WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cursor = await db.execute(query, params)
    return [_row_to_dict(row) for row in await cursor.fetchall()]


async def count_topics(db: aiosqlite.Connection, status: str | None = None) -> int:
    query = "SELECT COUNT(*) FROM topics WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    cursor = await db.execute(query, params)
    row = await cursor.fetchone()
    return row[0] if row else 0


async def batch_count_pending_reviews(db: aiosqlite.Connection, topic_ids: list[str]) -> dict[str, int]:
    """Count pending reviews per topic in batch."""
    if not topic_ids:
        return {}
    placeholders = ",".join("?" for _ in topic_ids)
    cursor = await db.execute(
        f"SELECT topic_id, COUNT(*) as cnt FROM review_items WHERE topic_id IN ({placeholders}) AND status = 'pending' GROUP BY topic_id",
        topic_ids,
    )
    return {row[0]: row[1] for row in await cursor.fetchall()}


async def batch_count_unresolved_deferred(db: aiosqlite.Connection, topic_ids: list[str]) -> dict[str, int]:
    """Count unresolved deferred nodes per topic in batch."""
    if not topic_ids:
        return {}
    placeholders = ",".join("?" for _ in topic_ids)
    cursor = await db.execute(
        f"SELECT topic_id, COUNT(*) as cnt FROM deferred_nodes WHERE topic_id IN ({placeholders}) AND resolved_at IS NULL GROUP BY topic_id",
        topic_ids,
    )
    return {row[0]: row[1] for row in await cursor.fetchall()}


async def get_topic_stats_aggregates(db: aiosqlite.Connection) -> dict:
    """Get aggregate stats across all topics with a single SQL query instead of loading full rows."""
    cursor = await db.execute(
        "SELECT COUNT(*) as topic_count, SUM(total_nodes) as total_nodes, "
        "SUM(learned_nodes) as learned_nodes, SUM(total_practice) as total_practice, "
        "SUM(total_sessions) as total_sessions "
        "FROM topics"
    )
    row = await cursor.fetchone()
    if not row:
        return {"topic_count": 0, "total_nodes": 0, "learned_nodes": 0, "total_practice": 0, "total_sessions": 0}
    return {k: (row[k] or 0) for k in ["topic_count", "total_nodes", "learned_nodes", "total_practice", "total_sessions"]}


async def update_topic(db: aiosqlite.Connection, topic_id: str, updates: dict) -> dict | None:
    if not updates:
        return await get_topic(db, topic_id)
    unknown = set(updates) - _ALLOWED_TOPIC_COLUMNS
    if unknown:
        raise ValueError(f"update_topic: disallowed columns {unknown}")
    sets = []
    params: list = []
    for key, value in updates.items():
        sets.append(f"{key} = ?")
        params.append(value)
    sets.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(topic_id)
    await db.execute(f"UPDATE topics SET {', '.join(sets)} WHERE topic_id = ?", params)
    await db.commit()
    return await get_topic(db, topic_id)


async def delete_topic(db: aiosqlite.Connection, topic_id: str) -> bool:
    # Cascade delete all related rows
    # Tables with direct topic_id column
    direct_tables = [
        "practice_attempts", "expression_assets", "ability_records",
        "ability_snapshots", "friction_records", "review_items",
        "deferred_nodes", "exports", "practice_prompt_cache",
        "article_mentions", "articles", "concept_notes", "article_reading_state", "concept_candidates",
        "sync_events",
    ]
    for table in direct_tables:
        await db.execute(f"DELETE FROM {table} WHERE topic_id = ?", (topic_id,))
    # session_nodes has no topic_id; delete via sessions subquery
    await db.execute(
        "DELETE FROM session_nodes WHERE session_id IN (SELECT session_id FROM sessions WHERE topic_id = ?)",
        (topic_id,),
    )
    await db.execute("DELETE FROM sessions WHERE topic_id = ?", (topic_id,))
    cursor = await db.execute("DELETE FROM topics WHERE topic_id = ?", (topic_id,))
    await db.commit()
    return cursor.rowcount > 0


async def increment_topic_stats(db: aiosqlite.Connection, topic_id: str, field: str, delta: int = 1):
    if field not in _ALLOWED_STAT_FIELDS:
        raise ValueError(f"increment_topic_stats: disallowed field '{field}'")
    if field == "learned_nodes":
        await db.execute(
            "UPDATE topics SET learned_nodes = MAX(0, learned_nodes + ?), updated_at = ? WHERE topic_id = ?",
            (delta, datetime.now().isoformat(), topic_id),
        )
    else:
        await db.execute(
            f"UPDATE topics SET {field} = {field} + ?, updated_at = ? WHERE topic_id = ?",
            (delta, datetime.now().isoformat(), topic_id),
        )
    await db.commit()


# ==================== Sessions (re-exports from session_repo) ====================

from backend.repositories.session_repo import (  # noqa: E402
    create_session,
    get_session,
    get_active_session,
    complete_session,
    claim_session_completion,
    update_session_summary,
    complete_session_synthesis,
    add_session_visit,
    increment_session_practice_count,
    update_session_node_left_at,
    list_sessions,
)


# ==================== Ability Records ====================

async def get_ability_record(db: aiosqlite.Connection, topic_id: str, node_id: str) -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM ability_records WHERE topic_id = ? AND node_id = ?",
        (topic_id, node_id),
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def upsert_ability_record(db: aiosqlite.Connection, record: dict) -> dict:
    await db.execute(
        """INSERT INTO ability_records (topic_id, node_id, understand, example, contrast,
           apply, explain, recall, transfer, teach, recall_confidence, last_reviewed_at,
           review_history_count, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(topic_id, node_id) DO UPDATE SET
           understand = excluded.understand, example = excluded.example, contrast = excluded.contrast,
           apply = excluded.apply, explain = excluded.explain, recall = excluded.recall,
           transfer = excluded.transfer, teach = excluded.teach,
           recall_confidence = COALESCE(excluded.recall_confidence, ability_records.recall_confidence),
           last_reviewed_at = COALESCE(excluded.last_reviewed_at, ability_records.last_reviewed_at),
           review_history_count = COALESCE(excluded.review_history_count, ability_records.review_history_count),
           updated_at = excluded.updated_at
           WHERE ability_records.updated_at IS NULL
              OR ability_records.updated_at <= excluded.updated_at""",
        (
            record["topic_id"], record["node_id"],
            record.get("understand", 0), record.get("example", 0), record.get("contrast", 0),
            record.get("apply", 0), record.get("explain", 0), record.get("recall", 0),
            record.get("transfer", 0), record.get("teach", 0),
            record.get("recall_confidence", 1.0),
            record.get("last_reviewed_at"),
            record.get("review_history_count", 0),
            record.get("updated_at", datetime.now().isoformat()),
        ),
    )
    await db.commit()
    return await get_ability_record(db, record["topic_id"], record["node_id"])


async def list_ability_records(db: aiosqlite.Connection, topic_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM ability_records WHERE topic_id = ?", (topic_id,)
    )
    return [_row_to_dict(row) for row in await cursor.fetchall()]


async def create_ability_snapshot(db: aiosqlite.Connection, topic_id: str, snapshot_data: dict, node_id: str | None = None, session_id: str | None = None):
    await db.execute(
        """INSERT INTO ability_snapshots (topic_id, node_id, session_id, snapshot_data,
           understand, example, contrast, apply, explain, recall, transfer, teach, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            topic_id, node_id, session_id, json.dumps(snapshot_data),
            snapshot_data.get("understand", 0), snapshot_data.get("example", 0),
            snapshot_data.get("contrast", 0), snapshot_data.get("apply", 0),
            snapshot_data.get("explain", 0), snapshot_data.get("recall", 0),
            snapshot_data.get("transfer", 0), snapshot_data.get("teach", 0),
            snapshot_data.get("source", "practice"),
        ),
    )
    await db.commit()


# ==================== Practice Attempts ====================

async def create_practice_attempt(db: aiosqlite.Connection, attempt: dict) -> dict:
    await db.execute(
        """INSERT INTO practice_attempts (attempt_id, topic_id, node_id, session_id,
           practice_type, prompt_text, user_answer, feedback, scores)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            attempt["attempt_id"], attempt["topic_id"], attempt["node_id"],
            attempt.get("session_id"), attempt.get("practice_type"),
            attempt.get("prompt_text", ""),
            attempt.get("user_answer"), attempt.get("feedback"),
            json.dumps(attempt.get("scores", {})),
        ),
    )
    await db.commit()
    if attempt.get("session_id"):
        await increment_session_practice_count(db, attempt["session_id"])
    await increment_topic_stats(db, attempt["topic_id"], "total_practice")
    return attempt


async def get_practice_attempts(
    db: aiosqlite.Connection,
    topic_id: str,
    node_id: str | None = None,
    limit: int = 20,
) -> list[dict]:
    query = "SELECT * FROM practice_attempts WHERE topic_id = ?"
    params: list = [topic_id]
    if node_id:
        query += " AND node_id = ?"
        params.append(node_id)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    cursor = await db.execute(query, params)
    return [_row_to_dict(row) for row in await cursor.fetchall()]


async def get_practice_attempt(db: aiosqlite.Connection, attempt_id: str) -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM practice_attempts WHERE attempt_id = ?",
        (attempt_id,),
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


# ==================== Friction Records ====================

async def create_friction_record(db: aiosqlite.Connection, record: dict) -> dict:
    friction_id = record.get("friction_id", "")
    if not friction_id:
        friction_id = generate_id("fr")
    tags = record.get("tags", [])
    if isinstance(tags, list):
        tags = json.dumps(tags)
    await db.execute(
        """INSERT INTO friction_records (friction_id, topic_id, node_id, session_id, friction_type,
           severity, evidence_text, suggested_next_node_id, description, tags, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            friction_id,
            record["topic_id"], record["node_id"],
            record.get("session_id"),
            record.get("friction_type"),
            record.get("severity", 1),
            record.get("evidence_text", ""),
            record.get("suggested_next_node_id"),
            record.get("description", ""),
            tags,
            record.get("created_at", datetime.now().isoformat()),
        ),
    )
    await db.commit()
    return record


async def batch_create_friction_records(db: aiosqlite.Connection, records: list[dict]) -> None:
    """Batch insert friction records using executemany (single commit)."""
    if not records:
        return
    _now = datetime.now().isoformat()
    rows = []
    for record in records:
        friction_id = record.get("friction_id", "")
        if not friction_id:
            friction_id = generate_id("fr")
        tags = record.get("tags", [])
        if isinstance(tags, list):
            tags = json.dumps(tags)
        rows.append((
            friction_id,
            record["topic_id"], record["node_id"],
            record.get("session_id"),
            record.get("friction_type"),
            record.get("severity", 1),
            record.get("evidence_text", ""),
            record.get("suggested_next_node_id"),
            record.get("description", ""),
            tags,
            record.get("created_at", _now),
        ))
    await db.executemany(
        """INSERT INTO friction_records (friction_id, topic_id, node_id, session_id, friction_type,
           severity, evidence_text, suggested_next_node_id, description, tags, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    await db.commit()


async def list_frictions(
    db: aiosqlite.Connection,
    topic_id: str,
    node_id: str | None = None,
    friction_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    query = "SELECT * FROM friction_records WHERE topic_id = ?"
    params: list = [topic_id]
    if node_id:
        query += " AND node_id = ?"
        params.append(node_id)
    if friction_type:
        query += " AND friction_type = ?"
        params.append(friction_type)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    cursor = await db.execute(query, params)
    rows = [_row_to_dict(row) for row in await cursor.fetchall()]
    # Parse tags from JSON string to list
    for r in rows:
        if isinstance(r.get("tags"), str):
            try:
                r["tags"] = json.loads(r["tags"])
            except (json.JSONDecodeError, TypeError):
                r["tags"] = []
    return rows


# ==================== Expression Assets (re-exports from expression_repo) ====================

from backend.repositories.expression_repo import (  # noqa: E402
    create_expression_asset,
    get_expression_asset,
    list_expression_assets,
    toggle_favorite,
)


# ==================== Review Items (re-exports from review_repo) ====================

from backend.repositories.review_repo import (  # noqa: E402
    create_review_item,
    batch_create_review_items,
    list_review_items,
    get_review_item,
    update_review_item,
    update_review_item_status,
    count_review_items,
)


# ==================== Deferred Nodes ====================

async def create_deferred_node(db: aiosqlite.Connection, topic_id: str, node_id: str, reason: str = "", source_node_id: str | None = None) -> dict:
    await db.execute(
        """INSERT OR IGNORE INTO deferred_nodes (topic_id, node_id, reason, source_node_id)
           VALUES (?, ?, ?, ?)""",
        (topic_id, node_id, reason, source_node_id),
    )
    await db.commit()
    return {"topic_id": topic_id, "node_id": node_id, "reason": reason, "source_node_id": source_node_id}


async def record_sync_event(
    db: aiosqlite.Connection,
    *,
    topic_id: str,
    storage_kind: str | None = None,
    operation: str,
    status: str = "pending",
    error_message: str = "",
    session_id: str | None = None,
    node_id: str | None = None,
    payload: dict | None = None,
    target_store: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    retryable: bool = True,
    attempt_count: int = 1,
) -> dict:
    event_id = generate_id("se")
    payload = dict(payload or {})
    resolved_target_store = target_store or storage_kind or "sqlite"
    (
        resolved_operation,
        resolved_entity_type,
        resolved_entity_id,
    ) = _normalize_sync_event_metadata(
        topic_id=topic_id,
        operation=operation,
        target_store=resolved_target_store,
        payload=payload,
        entity_type=entity_type,
        entity_id=entity_id,
        session_id=session_id,
        node_id=node_id,
    )
    payload_json = json.dumps(payload, ensure_ascii=False)
    await db.execute(
        """
        INSERT INTO sync_events (
            event_id, topic_id, session_id, node_id, entity_type, entity_id,
            storage_kind, target_store, operation, status, retryable,
            error_message, payload, attempt_count, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            topic_id,
            session_id,
            node_id,
            resolved_entity_type,
            resolved_entity_id,
            resolved_target_store,
            resolved_target_store,
            resolved_operation,
            status,
            int(retryable),
            error_message,
            payload_json,
            attempt_count,
            datetime.now().isoformat(),
        ),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM sync_events WHERE event_id = ?", (event_id,))
    row = await cursor.fetchone()
    return _serialize_sync_event(row) if row else {
        "event_id": event_id,
        "topic_id": topic_id,
        "session_id": session_id,
        "node_id": node_id,
        "entity_type": resolved_entity_type,
        "entity_id": resolved_entity_id,
        "storage_kind": resolved_target_store,
        "target_store": resolved_target_store,
        "operation": resolved_operation,
        "status": status,
        "retryable": retryable,
        "error_message": error_message,
        "payload": payload,
        "attempt_count": attempt_count,
    }


async def list_sync_events(
    db: aiosqlite.Connection,
    topic_id: str | None = None,
    status: str | None = None,
    target_store: str | None = None,
    limit: int = 100,
) -> list[dict]:
    query = "SELECT * FROM sync_events WHERE 1=1"
    params: list = []
    if topic_id:
        query += " AND topic_id = ?"
        params.append(topic_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    if target_store:
        query += " AND target_store = ?"
        params.append(target_store)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    cursor = await db.execute(query, params)
    return [_serialize_sync_event(row) for row in await cursor.fetchall()]


async def resolve_sync_event(
    db: aiosqlite.Connection,
    event_id: str,
    status: str = "resolved",
) -> dict | None:
    resolved_at = datetime.now().isoformat()
    await db.execute(
        """
        UPDATE sync_events
        SET status = ?, resolved_at = ?, updated_at = ?
        WHERE event_id = ?
        """,
        (status, resolved_at, resolved_at, event_id),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM sync_events WHERE event_id = ?", (event_id,))
    return _serialize_sync_event(await cursor.fetchone())


async def count_deferred_nodes(db: aiosqlite.Connection, topic_id: str) -> int:
    cursor = await db.execute(
        "SELECT COUNT(*) FROM deferred_nodes WHERE topic_id = ? AND resolved_at IS NULL",
        (topic_id,),
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def list_deferred_nodes(db: aiosqlite.Connection, topic_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM deferred_nodes WHERE topic_id = ? ORDER BY deferred_at DESC",
        (topic_id,),
    )
    return [_row_to_dict(row) for row in await cursor.fetchall()]


# ==================== App Settings (re-exports from settings_repo) ====================

from backend.repositories.settings_repo import (  # noqa: E402
    get_setting,
    set_setting,
    get_all_settings,
    update_settings,
)


# ==================== Deferred Nodes (extended) ====================

async def resolve_deferred_node(db: aiosqlite.Connection, topic_id: str, node_id: str) -> bool:
    """Mark a deferred node as resolved."""
    await db.execute(
        "UPDATE deferred_nodes SET resolved_at = ? WHERE topic_id = ? AND node_id = ? AND resolved_at IS NULL",
        (datetime.now().isoformat(), topic_id, node_id),
    )
    await db.commit()
    cursor = await db.execute(
        "SELECT changes()",
    )
    row = await cursor.fetchone()
    return (row[0] or 0) > 0


async def list_all_deferred_nodes(db: aiosqlite.Connection, resolved: bool = False) -> list[dict]:
    """List all deferred nodes across topics."""
    query = "SELECT * FROM deferred_nodes WHERE 1=1"
    params: list = []
    if not resolved:
        query += " AND resolved_at IS NULL"
    query += " ORDER BY deferred_at DESC"
    cursor = await db.execute(query, params)
    return [_row_to_dict(row) for row in await cursor.fetchall()]


# ==================== Topics (search) ====================

async def search_topics(db: aiosqlite.Connection, query_str: str, limit: int = 20) -> list[dict]:
    """Search topics by title (case-insensitive partial match)."""
    escaped = query_str.replace("%", "\\%").replace("_", "\\_")
    cursor = await db.execute(
        "SELECT * FROM topics WHERE title LIKE ? ESCAPE '\\' ORDER BY updated_at DESC LIMIT ?",
        (f"%{escaped}%", limit),
    )
    return [_row_to_dict(row) for row in await cursor.fetchall()]


# ==================== Ability Snapshots (query) ====================

async def get_ability_snapshots(db: aiosqlite.Connection, topic_id: str, limit: int = 20) -> list[dict]:
    """Get ability snapshots for a topic."""
    cursor = await db.execute(
        "SELECT * FROM ability_snapshots WHERE topic_id = ? ORDER BY created_at DESC LIMIT ?",
        (topic_id, limit),
    )
    return [_row_to_dict(row) for row in await cursor.fetchall()]


# ==================== Practice Prompt Cache ====================

async def get_cached_practice_prompt(
    db: aiosqlite.Connection, topic_id: str, node_id: str, practice_type: str,
    difficulty: str = "medium", learning_intent: str = "build_system",
) -> dict | None:
    """Get cached practice prompt if exists."""
    cursor = await db.execute(
        "SELECT * FROM practice_prompt_cache WHERE topic_id = ? AND node_id = ? AND practice_type = ? AND difficulty = ? AND learning_intent = ?",
        (topic_id, node_id, practice_type, difficulty, learning_intent),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    data = _row_to_dict(row)
    return {
        "practice_type": data["practice_type"],
        "prompt_text": data["prompt_text"],
        "requirements": json.loads(data.get("requirements", "[]")),
        "scoring_dimensions": json.loads(data.get("scoring_dimensions", "[]")),
        "min_answer_hint": data.get("min_answer_hint", ""),
    }


async def save_practice_prompt_cache(
    db: aiosqlite.Connection, topic_id: str, node_id: str, practice_type: str, data: dict,
    difficulty: str = "medium", learning_intent: str = "build_system",
):
    """Save a practice prompt to cache."""
    await db.execute(
        """INSERT OR REPLACE INTO practice_prompt_cache
           (topic_id, node_id, practice_type, difficulty, learning_intent, prompt_text, requirements, scoring_dimensions, min_answer_hint)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            topic_id, node_id, practice_type, difficulty, learning_intent,
            data.get("prompt_text", ""),
            json.dumps(data.get("requirements", []), ensure_ascii=False),
            json.dumps(data.get("scoring_dimensions", []), ensure_ascii=False),
            data.get("min_answer_hint", ""),
        ),
    )
    await db.commit()


async def count_mastered_nodes(db: aiosqlite.Connection, topic_id: str) -> int:
    """Count nodes with average ability >= 70 (mastered threshold)."""
    cursor = await db.execute(
        """SELECT COUNT(*) FROM ability_records
           WHERE topic_id = ? AND (understand + example + contrast + apply + explain + recall + transfer + teach) / 8.0 >= 70""",
        (topic_id,),
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def count_global_pending_reviews(db: aiosqlite.Connection) -> int:
    """Count all pending reviews globally."""
    cursor = await db.execute("SELECT COUNT(*) FROM review_items WHERE status = 'pending'")
    row = await cursor.fetchone()
    return row[0] if row else 0


async def count_expression_assets(db: aiosqlite.Connection) -> int:
    """Count all expression assets globally."""
    cursor = await db.execute("SELECT COUNT(*) FROM expression_assets")
    row = await cursor.fetchone()
    return row[0] if row else 0


async def count_friction_records(db: aiosqlite.Connection) -> int:
    """Count all friction records globally."""
    cursor = await db.execute("SELECT COUNT(*) FROM friction_records")
    row = await cursor.fetchone()
    return row[0] if row else 0


def _json_or_default(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


# ==================== Article Workspace ====================

async def create_article(db: aiosqlite.Connection, article: dict) -> dict:
    await db.execute(
        """INSERT INTO articles
           (article_id, topic_id, title, body, article_kind, source_label, is_editable, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            article["article_id"],
            article["topic_id"],
            article["title"],
            article.get("body", ""),
            article.get("article_kind", "source"),
            article.get("source_label", "我的文章"),
            1 if article.get("is_editable", True) else 0,
            article.get("created_at", datetime.now().isoformat()),
            article.get("updated_at", datetime.now().isoformat()),
        ),
    )
    await db.commit()
    return await get_article(db, article["article_id"])


async def get_article(db: aiosqlite.Connection, article_id: str) -> dict | None:
    cursor = await db.execute("SELECT * FROM articles WHERE article_id = ?", (article_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    article = _row_to_dict(row)
    article["is_editable"] = bool(article.get("is_editable", 1))
    return article


async def list_articles(db: aiosqlite.Connection, topic_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM articles WHERE topic_id = ? ORDER BY updated_at DESC",
        (topic_id,),
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        article = _row_to_dict(row)
        article["is_editable"] = bool(article.get("is_editable", 1))
        result.append(article)
    return result


async def update_article(db: aiosqlite.Connection, article_id: str, updates: dict) -> dict | None:
    if not updates:
        return await get_article(db, article_id)
    for key in updates:
        if key not in _ALLOWED_ARTICLE_COLUMNS:
            raise ValueError(f"Invalid article column: {key}")
    sets = []
    params: list = []
    for key, value in updates.items():
        sets.append(f"{key} = ?")
        params.append(value)
    sets.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(article_id)
    await db.execute(f"UPDATE articles SET {', '.join(sets)} WHERE article_id = ?", params)
    await db.commit()
    return await get_article(db, article_id)


async def delete_article_mentions(db: aiosqlite.Connection, article_id: str) -> int:
    cursor = await db.execute(
        "DELETE FROM article_mentions WHERE article_id = ?",
        (article_id,),
    )
    await db.commit()
    return cursor.rowcount or 0


async def create_article_mentions(db: aiosqlite.Connection, mentions: list[dict]) -> None:
    if not mentions:
        return
    _now = datetime.now().isoformat()
    rows = [
        (
            m["mention_id"], m["topic_id"], m["article_id"], m["concept_text"], m["concept_name"],
            m.get("concept_key"), m.get("mention_type", "explicit"), m.get("confidence", 0.0),
            m.get("paragraph_index", 0), m.get("anchor_id", ""),
            m.get("created_at", _now), m.get("updated_at", _now),
        )
        for m in mentions
    ]
    await db.executemany(
        """INSERT INTO article_mentions
           (mention_id, topic_id, article_id, concept_text, concept_name, concept_key, mention_type,
            confidence, paragraph_index, anchor_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    await db.commit()


async def list_article_mentions(
    db: aiosqlite.Connection,
    topic_id: str,
    article_id: str | None = None,
    concept_key: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM article_mentions WHERE topic_id = ?"
    params: list = [topic_id]
    if article_id:
        query += " AND article_id = ?"
        params.append(article_id)
    if concept_key:
        query += " AND concept_key = ?"
        params.append(concept_key)
    query += " ORDER BY updated_at DESC, paragraph_index ASC"
    cursor = await db.execute(query, params)
    return [_row_to_dict(row) for row in await cursor.fetchall()]


async def upsert_concept_note(db: aiosqlite.Connection, note: dict) -> dict:
    await db.execute(
        """INSERT INTO concept_notes (note_id, topic_id, concept_key, title, body, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(topic_id, concept_key) DO UPDATE SET
           title = excluded.title,
           body = excluded.body,
           updated_at = excluded.updated_at""",
        (
            note["note_id"],
            note["topic_id"],
            note["concept_key"],
            note.get("title", ""),
            note.get("body", ""),
            note.get("updated_at", datetime.now().isoformat()),
        ),
    )
    await db.commit()
    return await get_concept_note(db, note["topic_id"], note["concept_key"])


async def get_concept_note(db: aiosqlite.Connection, topic_id: str, concept_key: str) -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM concept_notes WHERE topic_id = ? AND concept_key = ?",
        (topic_id, concept_key),
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def list_concept_notes(db: aiosqlite.Connection, topic_id: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM concept_notes WHERE topic_id = ? ORDER BY updated_at DESC",
        (topic_id,),
    )
    return [_row_to_dict(row) for row in await cursor.fetchall()]


async def upsert_article_reading_state(db: aiosqlite.Connection, reading_state: dict) -> dict:
    await db.execute(
        """INSERT INTO article_reading_state (topic_id, article_id, scroll_top, trail, completed_article_ids, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(topic_id) DO UPDATE SET
           article_id = excluded.article_id,
           scroll_top = excluded.scroll_top,
           trail = excluded.trail,
           completed_article_ids = excluded.completed_article_ids,
           updated_at = excluded.updated_at""",
        (
            reading_state["topic_id"],
            reading_state["article_id"],
            reading_state.get("scroll_top", 0),
            json.dumps(reading_state.get("trail", []), ensure_ascii=False),
            json.dumps(reading_state.get("completed_article_ids", []), ensure_ascii=False),
            reading_state.get("updated_at", datetime.now().isoformat()),
        ),
    )
    await db.commit()
    return await get_article_reading_state(db, reading_state["topic_id"])


async def get_article_reading_state(db: aiosqlite.Connection, topic_id: str) -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM article_reading_state WHERE topic_id = ?",
        (topic_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    data = _row_to_dict(row)
    data["trail"] = _json_or_default(data.get("trail"), [])
    data["completed_article_ids"] = _json_or_default(data.get("completed_article_ids"), [])
    return data


async def create_concept_candidate(db: aiosqlite.Connection, candidate: dict) -> dict:
    await db.execute(
        """INSERT INTO concept_candidates
           (candidate_id, topic_id, concept_text, normalized_text, status, matched_node_id,
            matched_concept_name, source_article_id, paragraph_index, anchor_id, origin, confidence, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            candidate["candidate_id"],
            candidate["topic_id"],
            candidate["concept_text"],
            candidate["normalized_text"],
            candidate.get("status", "candidate"),
            candidate.get("matched_node_id"),
            candidate.get("matched_concept_name", ""),
            candidate.get("source_article_id"),
            candidate.get("paragraph_index"),
            candidate.get("anchor_id", ""),
            candidate.get("origin", "manual"),
            candidate.get("confidence", 0.0),
            candidate.get("created_at", datetime.now().isoformat()),
            candidate.get("updated_at", datetime.now().isoformat()),
        ),
    )
    await db.commit()
    return await get_concept_candidate(db, candidate["candidate_id"])


async def get_concept_candidate(db: aiosqlite.Connection, candidate_id: str) -> dict | None:
    cursor = await db.execute(
        "SELECT * FROM concept_candidates WHERE candidate_id = ?",
        (candidate_id,),
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def find_candidate_by_normalized_text(
    db: aiosqlite.Connection,
    topic_id: str,
    normalized_text: str,
) -> dict | None:
    cursor = await db.execute(
        """SELECT * FROM concept_candidates
           WHERE topic_id = ? AND normalized_text = ?
           ORDER BY CASE status WHEN 'confirmed' THEN 0 WHEN 'candidate' THEN 1 ELSE 2 END, updated_at DESC
           LIMIT 1""",
        (topic_id, normalized_text),
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def find_candidates_by_normalized_texts(
    db: aiosqlite.Connection,
    topic_id: str,
    normalized_texts: list[str],
) -> dict[str, dict]:
    """Batch lookup concept candidates by normalized text. Returns {normalized_text: candidate}."""
    if not normalized_texts:
        return {}
    placeholders = ",".join("?" for _ in normalized_texts)
    cursor = await db.execute(
        f"""SELECT * FROM concept_candidates
            WHERE topic_id = ? AND normalized_text IN ({placeholders})
            ORDER BY CASE status WHEN 'confirmed' THEN 0 WHEN 'candidate' THEN 1 ELSE 2 END, updated_at DESC""",
        [topic_id] + normalized_texts,
    )
    result: dict[str, dict] = {}
    for row in await cursor.fetchall():
        row_dict = _row_to_dict(row)
        nt = row_dict.get("normalized_text", "")
        if nt and nt not in result:
            result[nt] = row_dict
    return result


async def list_concept_candidates(
    db: aiosqlite.Connection,
    topic_id: str,
    status: str | None = None,
    exclude_ignored: bool = False,
) -> list[dict]:
    query = "SELECT * FROM concept_candidates WHERE topic_id = ?"
    params: list = [topic_id]
    if status:
        query += " AND status = ?"
        params.append(status)
    if exclude_ignored:
        query += " AND status != 'ignored'"
    query += " ORDER BY updated_at DESC"
    cursor = await db.execute(query, params)
    return [_row_to_dict(row) for row in await cursor.fetchall()]


async def update_concept_candidate(db: aiosqlite.Connection, candidate_id: str, updates: dict) -> dict | None:
    if not updates:
        return await get_concept_candidate(db, candidate_id)
    for key in updates:
        if key not in _ALLOWED_CONCEPT_CANDIDATE_COLUMNS:
            raise ValueError(f"Invalid concept_candidate column: {key}")
    sets = []
    params: list = []
    for key, value in updates.items():
        sets.append(f"{key} = ?")
        params.append(value)
    sets.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(candidate_id)
    await db.execute(f"UPDATE concept_candidates SET {', '.join(sets)} WHERE candidate_id = ?", params)
    await db.commit()
    return await get_concept_candidate(db, candidate_id)


async def delete_article_generated_candidates(db: aiosqlite.Connection, article_id: str) -> int:
    cursor = await db.execute(
        """DELETE FROM concept_candidates
           WHERE source_article_id = ? AND origin = 'article_analysis' AND status = 'candidate'""",
        (article_id,),
    )
    await db.commit()
    return cursor.rowcount or 0


async def rebind_mentions_to_concept(
    db: aiosqlite.Connection,
    topic_id: str,
    normalized_text: str,
    node_id: str,
    concept_name: str,
) -> int:
    cursor = await db.execute(
        """UPDATE article_mentions
           SET concept_key = ?, concept_name = ?, mention_type = CASE WHEN mention_type = 'candidate' THEN 'explicit' ELSE mention_type END,
               updated_at = ?
           WHERE topic_id = ? AND lower(trim(concept_text)) = ?""",
        (node_id, concept_name, datetime.now().isoformat(), topic_id, normalized_text),
    )
    await db.commit()
    return cursor.rowcount or 0


async def list_backlinks_for_concept(db: aiosqlite.Connection, topic_id: str, concept_key: str) -> list[dict]:
    cursor = await db.execute(
        """SELECT m.article_id, a.title, m.anchor_id, m.paragraph_index, a.body, m.updated_at
           FROM article_mentions m
           JOIN articles a ON a.article_id = m.article_id
           WHERE m.topic_id = ? AND m.concept_key = ?
           ORDER BY m.updated_at DESC, m.paragraph_index ASC""",
        (topic_id, concept_key),
    )
    return [_row_to_dict(row) for row in await cursor.fetchall()]


async def search_workspace(db: aiosqlite.Connection, topic_id: str, query_str: str, limit: int = 10) -> dict:
    like_query = f"%{query_str}%"
    article_cursor = await db.execute(
        """SELECT article_id, title, body, updated_at
           FROM articles
           WHERE topic_id = ? AND (title LIKE ? OR body LIKE ?)
           ORDER BY updated_at DESC LIMIT ?""",
        (topic_id, like_query, like_query, limit),
    )
    note_cursor = await db.execute(
        """SELECT concept_key, title, body, updated_at
           FROM concept_notes
           WHERE topic_id = ? AND (title LIKE ? OR body LIKE ?)
           ORDER BY updated_at DESC LIMIT ?""",
        (topic_id, like_query, like_query, limit),
    )
    return {
        "articles": [_row_to_dict(row) for row in await article_cursor.fetchall()],
        "notes": [_row_to_dict(row) for row in await note_cursor.fetchall()],
    }


async def cleanup_old_sync_events(db: aiosqlite.Connection, max_age_days: int = 7) -> int:
    """Delete resolved/ignored sync events older than max_age_days.

    Returns the number of deleted rows.
    """
    cursor = await db.execute(
        """DELETE FROM sync_events
           WHERE status IN ('resolved', 'ignored')
             AND created_at < datetime('now', ?)""",
        (f'-{max_age_days} days',),
    )
    await db.commit()
    return cursor.rowcount
