# Reliability Audit - AxonClone

> Perspective: System stability and recoverability
> Date: 2026-03-19
> Scope: Backend API error handling, database write consistency, concurrency safety, frontend degradation, state drift

---

## Critical Issues (ISSUE-RL-NNN)

### ISSUE-RL-001: `record_sync_event` is write-only — no consumer/recovery worker exists

**File**: All files that call `sqlite_repo.record_sync_event()` (12 call sites across 6 service files)

**Problem**: `sync_events` table is populated when Neo4j/LanceDB/SQLite writes fail, but there is **no recovery worker or retry mechanism** in the codebase. A grep for `process_pending_sync`, `list_pending_sync`, `retry_sync_events`, `sync_recover`, or `sync_worker` returns zero results. The only cleanup is `cleanup_old_sync_events` which deletes resolved events older than 7 days on startup — but nothing ever resolves them.

**Impact**: Once a sync event is written, it accumulates indefinitely as dead data. Failed Neo4j writes (graph nodes, edges, article_body updates), failed LanceDB writes (embeddings), and failed SQLite writes (snapshots, review queues) will never be retried.

**Severity**: P0 — the compensation mechanism described in CLAUDE.md ("失败时记录补偿任务或回滚标记") is documented but not implemented.

---

### ISSUE-RL-002: `expand_node` multi-step write lacks transactional integrity

**File**: `backend/api/nodes.py:134-339`

**Problem**: The expand operation writes across three stores in sequence:
1. SQLite `session_nodes` tracking (line 154-180) — has its own try/except + sync_event
2. Neo4j batch node/edge creation (line 182-286) — wrapped in one try/except
3. LanceDB vector writes (line 288-319) — has its own try/except + sync_event

If step 1 succeeds but step 2 fails: session_nodes reference node IDs that don't exist in Neo4j.
If step 2 succeeds but step 3 fails: nodes exist in Neo4j but not in LanceDB (semantics silently lost).
If step 1 fails (but only partially — some rows inserted before the exception): inconsistent session_node tracking.

There is no rollback of earlier steps when a later step fails.

**Impact**: Orphaned session_node records in SQLite, nodes in Neo4j without corresponding vectors in LanceDB, and vice versa. The `increment_topic_stats` call at line 339 runs unconditionally even when writes partially fail.

**Severity**: P0 — violates the "SQLite -> Neo4j -> LanceDB" write order contract and has no rollback.

---

### ISSUE-RL-003: `create_topic` Neo4j write uses a single massive try block — partial writes are undetectable

**File**: `backend/services/topic_service.py:79-223`

**Problem**: The entire Neo4j write sequence (create topic node, create entry concept, batch-create additional nodes, batch-set mainline flags, batch-link to topic, validate+create edges) is in one try/except. If the batch UNWIND for nodes succeeds but the subsequent batch UNWIND for edges fails, the entry node and additional nodes exist in Neo4j but their relationships are missing. The sync_event payload only records `entry_node_id` and `entry_node_name` — it cannot reconstruct the partial graph state.

**Impact**: Silent partial graph writes. Nodes exist in Neo4j without their PREREQUISITE/CONTRASTS relationships. No way to detect or repair this from the recorded sync event.

**Severity**: P0 — data corruption risk during topic creation.

---

### ISSUE-RL-004: Async friction update in `submit_practice` uses fire-and-forget with silent data loss

**File**: `backend/services/practice_service.py:171-264`

**Problem**: The `_async_friction_update()` coroutine is launched via `asyncio.create_task()` and the response is returned to the user immediately. This fire-and-forget task:
- Opens a **separate** SQLite connection (line 178) — writes to `friction_records` via this connection
- Writes to Neo4j (misconceptions + evidence nodes)

If the task fails (e.g., Neo4j connection drops between misconception and evidence writes), the error is only logged. The friction_records written to the separate SQLite connection are committed independently. There is no way to correlate a successful friction_record insert with a failed Neo4j misconception write.

Worse: if the Python process crashes between `asyncio.create_task()` and the task's first line executing, the friction data is lost entirely.

**Impact**: Friction records that inform diagnostic and review decisions can be silently incomplete or missing.

**Severity**: P1 — business logic depends on friction data for review prioritization and ability gap detection.

---

### ISSUE-RL-005: `delete_topic` cascade delete is not atomic — SQLite deletes succeed, Neo4j/LanceDB may fail

**File**: `backend/services/topic_service.py:429-465`

**Problem**: SQLite cascade delete runs first (`delete_topic` in sqlite_repo.py:777-796 runs DELETE on 16 tables + commit). Only after this succeeds does the code attempt Neo4j and LanceDB cleanup. If Neo4j or LanceDB cleanup fails:
- SQLite records are permanently deleted
- Neo4j nodes/relationships for the topic remain as orphans
- LanceDB vectors for the topic remain

A sync_event is recorded, but per ISSUE-RL-001, it will never be processed.

**Impact**: Neo4j graph pollution with orphaned nodes and edges. LanceDB storage bloat. On the next topic creation for similar content, vector dedup may match old orphaned vectors.

**Severity**: P1 — growing data corruption over time.

---

### ISSUE-RL-006: `complete_session` non-atomic multi-write with partial state

**File**: `backend/services/session_service.py:81-321`

**Problem**: Session completion performs 8+ sequential write operations:
1. `claim_session_completion` (marks session completed)
2. `update_session_summary`
3. `update_session_node_left_at`
4. `update_topic` (last_session_id)
5. `batch_create_review_items`
6. `generate_review_queue`
7. `complete_session_synthesis`

Each has its own try/except that logs a warning and continues. If step 1 succeeds (session marked completed) but step 6 fails, the session appears completed but review items are missing. The user cannot retry because the session is no longer active.

If step 7 fails, the synthesis JSON is lost, and the user sees a "partial summary" in the frontend. There is a `record_sync_event` fallback for step 7, but per ISSUE-RL-001 it will never be retried.

**Impact**: Users lose review items and synthesis data on partial failures. Cannot recover without manual intervention.

**Severity**: P1 — critical for the learning session lifecycle.

---

### ISSUE-RL-007: No SQLite transaction wrapping for multi-step operations

**File**: Across all service files

**Problem**: aiosqlite operates in auto-commit mode by default (each `db.execute()` + `db.commit()` is a separate transaction). Multi-step operations like `submit_practice` (create attempt + update ability + create snapshot) and `complete_session` (claim + summary + review items + synthesis) issue multiple independent commits. If the process crashes mid-operation, some writes persist and others are lost.

Example in `practice_service.py`:
- Line 289: `create_practice_attempt` + commit
- Line 319: `upsert_ability_record` + commit
- Line 338: `create_ability_snapshot` + commit (has its own try/except)

If crash after line 289 but before line 319: practice attempt exists but ability was never updated.

**Impact**: Partial state across the most critical business operations.

**Severity**: P0 — fundamental data integrity gap.

---

### ISSUE-RL-008: `list_topics` SQL injection surface via f-string

**File**: `backend/services/topic_service.py:396-400`

**Problem**:
```python
placeholders = ",".join("?" for _ in topic_ids)
review_cursor = await db.execute(
    f"SELECT topic_id, COUNT(*) as cnt FROM review_items WHERE topic_id IN ({placeholders}) AND status = 'pending' GROUP BY topic_id",
    topic_ids,
)
```

While the `topic_ids` come from an internal DB query (not user input), this pattern uses f-string SQL construction. The `topic_ids` are extracted from `topics` which were fetched via `sqlite_repo.list_topics`. If `list_topics` ever returns unexpected data (e.g., due to a data migration bug), this could produce malformed SQL.

**Impact**: Low immediate risk since `topic_ids` is internal, but the pattern violates defense-in-depth.

**Severity**: P2 — pattern risk, not an active vulnerability.

---

### ISSUE-RL-009: Neo4j dynamic relation type in f-string — potential Cypher injection

**File**: `backend/services/topic_service.py:200-207` and `backend/api/nodes.py:265-271`

**Problem**:
```python
await session.run(
    f"""UNWIND $items AS item
       MATCH (src:Concept {{node_id: item.src_id}}), (tgt:Concept {{node_id: item.tgt_id}})
       MERGE (src)-[r:`{rel_type}`]->(tgt)
       SET r.reason = item.reason""",
    {"items": rel_items},
)
```

The `rel_type` variable is interpolated directly into the Cypher query string. While `validate_and_filter_edges` checks against `ALLOWED_RELATION_TYPES`, the validation happens before the write — if someone bypasses the validator or adds a new edge type without updating the whitelist, this becomes a Cypher injection vector.

**Impact**: Cypher injection could manipulate graph structure.

**Severity**: P2 — mitigated by existing validation, but the f-string interpolation of relation types is architecturally risky.

---

### ISSUE-RL-010: `update_node_status` mastered check has TOCTOU race condition

**File**: `backend/services/node_service.py:329-361`

**Problem**:
```python
if status == "mastered":
    was_mastered = False
    if neo4j:
        async with neo4j.session() as session:
            existing = await graph.get_concept_node(session, node_id)
            if existing and existing.get("status") == "mastered":
                was_mastered = True
    if not was_mastered:
        await sqlite_repo.increment_topic_stats(db, topic_id, "learned_nodes")
```

Between reading `existing.status` and writing `increment_topic_stats`, another concurrent request could also read `was_mastered = False` and both would increment. The Neo4j status update (line 334) and the SQLite increment are not atomic.

**Impact**: `learned_nodes` counter can over-count if multiple concurrent requests mark the same node as mastered.

**Severity**: P2 — counter inaccuracy affects topic progress display.

---

### ISSUE-RL-011: Single shared SQLite connection across all async requests

**File**: `backend/core/deps.py:25-27`

**Problem**: One `aiosqlite.Connection` is created at startup and shared across all requests via `app.state.db`. While aiosqlite serializes write operations internally, concurrent reads may see inconsistent intermediate states during multi-step writes (per ISSUE-RL-007). Additionally, if any unhandled exception leaves the connection in a bad state, all subsequent requests fail.

WAL mode is enabled (line 27), which helps with read concurrency, but does not provide snapshot isolation for readers during a writer's transaction.

**Impact**: All API requests share fate — one connection corruption affects the entire application.

**Severity**: P1 — single point of failure.

---

### ISSUE-RL-012: `create_session` race condition recovery is fragile

**File**: `backend/services/session_service.py:18-38`

**Problem**:
```python
existing = await sqlite_repo.get_active_session(db, topic_id)
if existing:
    return {**existing, "restored": True}
# ...
created = await sqlite_repo.create_session(db, session.model_dump())
```

Two concurrent `POST /topics/{id}/sessions` requests can both pass the `existing` check (both see no active session) and both attempt `create_session`. The `IntegrityError` catch on line 33 handles this for the `sessions` table (assuming a UNIQUE constraint on `(topic_id, status)`), but it does not handle the `increment_topic_stats` that already ran inside `session_repo.create_session` (line 31).

**Impact**: `total_sessions` counter may be over-counted by 1 on concurrent session creation.

**Severity**: P2 — cosmetic counter issue.

---

### ISSUE-RL-013: `generate_article` has no idempotency guard

**File**: `backend/api/nodes.py:394-461`

**Problem**: If the user clicks "generate article" rapidly, two concurrent requests can both pass the `if node.get("article_body") and not force` check (line 412), both call the AI agent, and both write to Neo4j. The second write overwrites the first, wasting an AI call. There is no lock or claim mechanism.

**Impact**: Wasted AI API calls and potential inconsistency if the two AI calls produce different results.

**Severity**: P2 — cost and UX issue.

---

### ISSUE-RL-014: `get_session` in sessions.py API has no try/except

**File**: `backend/api/sessions.py:32-40`

**Problem**:
```python
@router.get("/topics/{topic_id}/sessions/{session_id}")
async def get_session(request: Request, topic_id: str, session_id: str):
    db = request.app.state.db
    result = await session_service.get_session(db, session_id)
```

Unlike all other API endpoints, this route handler has no try/except. If `session_service.get_session` raises an unhandled exception (e.g., JSON parse error on `synthesis_json`), FastAPI's default 500 handler will return a generic error without the Chinese error message format.

**Impact**: Inconsistent error handling — one endpoint lacks the standard try/except wrapper.

**Severity**: P2 — inconsistent with the established pattern.

---

### ISSUE-RL-015: Frontend React Query has no retry limit configuration for most queries

**File**: `src/hooks/use-queries.ts`

**Problem**: Only `useHealthQuery` and `useSystemCapabilitiesQuery` set `retry: false`. All other 25+ queries use React Query's default retry behavior (3 retries with exponential backoff). For mutations that fail due to validation errors (e.g., session already completed), retrying is wasteful. For queries that fail because Neo4j is down (returns fallback data), retrying 3 times adds unnecessary delay.

**Impact**: UX delay on transient failures, wasted network requests.

**Severity**: P2 — degrades perceived performance.

---

### ISSUE-RL-016: `delete_topic` SQLite cascade misses `sync_events` table

**File**: `backend/repositories/sqlite_repo.py:780-785`

**Problem**: The `direct_tables` list for cascade deletion includes 16 tables but **does not include `sync_events`**. When a topic is deleted, its sync_events remain in the database. These orphaned sync_events reference a deleted topic_id and will never be cleaned up by the startup cleanup (which only removes resolved events, and these pending events will never be resolved per ISSUE-RL-001).

**Impact**: Growing orphaned sync_events table, minor storage bloat.

**Severity**: P2 — minor data hygiene issue.

---

### ISSUE-RL-017: `increment_topic_stats` is called outside transaction scope in `expand_node`

**File**: `backend/api/nodes.py:339`

**Problem**: After the entire try/except block for Neo4j+LanceDB writes (lines 136-337), `increment_topic_stats` runs unconditionally at line 339, even when the inner try/except caught an exception and only logged a warning. This means `total_nodes` is incremented even when node creation partially or fully failed.

**Impact**: `total_nodes` counter becomes inaccurate, potentially exceeding the 30-node topic cap check.

**Severity**: P1 — counter drift affects the topic cap enforcement.

---

### ISSUE-RL-018: `submit_practice` ability update uses read-modify-write without optimistic locking

**File**: `backend/services/practice_service.py:306-320`

**Problem**:
```python
existing = await sqlite_repo.get_ability_record(db, topic_id, node_id)
# ... modify ...
updated = apply_delta(record, delta)
await sqlite_repo.upsert_ability_record(db, updated.model_dump())
```

If two concurrent practice submissions for the same node both read the same `existing` ability, both compute their deltas, and both write — one delta is lost (last-write-wins). This is a classic lost-update anomaly.

**Impact**: Ability scores may not reflect all practice attempts when concurrent submissions occur (unlikely but possible with rapid UI interaction or multiple tabs).

**Severity**: P2 — requires unusual timing but violates correctness guarantees.

---

### ISSUE-RL-019: Neo4j session timeout not configured — long AI operations can exhaust connection pool

**File**: `backend/core/deps.py:63-76`

**Problem**: The Neo4j driver is created with default settings:
```python
neo4j_driver = AsyncGraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_user, settings.neo4j_password),
)
```

No `connection_acquisition_timeout`, `max_connection_lifetime`, or `max_connection_pool_size` is configured. The `create_topic` operation can hold a Neo4j session open for 60-120 seconds while waiting for the Explorer AI response (the AI call happens before Neo4j writes in topic_service.py, but Neo4j sessions are used extensively elsewhere).

If multiple slow operations (expand_node, create_topic, generate_article) run concurrently, they may exhaust the default connection pool, causing timeouts on unrelated read operations.

**Impact**: Cascading failures under load — read operations timeout because write operations hold connections too long.

**Severity**: P1 — affects availability under concurrent use.

---

### ISSUE-RL-020: Frontend `onError` handlers are generic — no error-code-based recovery

**File**: `src/hooks/use-mutations.ts`

**Problem**: All 30+ mutation onError handlers use the same generic handler:
```typescript
const _onError = () => showToast('操作失败，请重试', 'error')
```

The backend returns specific `error_code` values (e.g., `SESSION_NOT_ACTIVE`, `TOPIC_NOT_FOUND`), but the frontend ignores them entirely. For example, `SESSION_NOT_ACTIVE` should redirect to start a new session, not just show "操作失败".

**Impact**: Users see generic error messages when specific recovery actions are possible (e.g., "session expired, start a new one").

**Severity**: P1 — degrades user experience and prevents self-service recovery.

---

### ISSUE-RL-021: `complete_session` review candidate resolution uses name-to-ID matching that is fragile

**File**: `backend/services/session_service.py:205-220`

**Problem**: The Synthesizer AI returns review candidates with `node_name` strings. These are matched to Neo4j `Concept` nodes by exact name match. If:
- The AI returns a slightly different name (e.g., "closure" vs "闭包")
- Two nodes have the same name in different topics
- The node was renamed after creation

Then the review item silently has no `node_id` and is skipped.

**Impact**: Review items may be silently dropped during session completion.

**Severity**: P2 — silent data loss in review queue generation.

---

### ISSUE-RL-022: `topic_service.list_topics` uses raw SQL in service layer with f-string

**File**: `backend/services/topic_service.py:396-407`

**Problem**: This is the same pattern as ISSUE-RL-008, but located in the service layer instead of the repository layer. The service directly constructs and executes SQL queries, bypassing the repository abstraction. This is the only service that does raw SQL for business queries.

**Impact**: Violates the layering contract (services should use repositories for data access).

**Severity**: P2 — architectural concern.

---

### ISSUE-RL-023: `claim_session_completion` marks session completed before synthesis generation

**File**: `backend/services/session_service.py:100-103`

**Problem**: `claim_session_completion` atomically sets status to "completed" and commits. If the subsequent synthesis generation or review item creation fails, the session is already marked completed and cannot be retried. The user must start a new session to generate review items.

While there is a fallback synthesis (line 164), it only has basic statistics. The AI-generated synthesis with key_takeaways, next_recommendations, and review_candidates is lost.

**Impact**: Users lose AI-generated session summaries on failure and cannot retry.

**Severity**: P1 — irreversible state transition before dependent operations complete.

---

## Candidates (CANDIDATE-RL-NNN)

### CANDIDATE-RL-001: Implement sync event recovery worker

**Location**: New file `backend/services/sync_recovery.py` or startup task in `deps.py`

**Proposal**: Create a background task that polls `sync_events WHERE status = 'pending'` and attempts to replay failed operations. Use exponential backoff with max 5 retries. Mark events as `resolved` or `failed_permanent`.

**Rationale**: The sync_events table exists but has no consumer. This is the most impactful reliability improvement.

---

### CANDIDATE-RL-002: Wrap multi-step writes in explicit SQLite transactions

**Location**: `practice_service.py`, `session_service.py`, `topic_service.py`

**Proposal**: Use `async with db.execute("BEGIN")` / `await db.commit()` to wrap multi-step operations. Example for submit_practice: wrap create_practice_attempt + upsert_ability_record + create_ability_snapshot in a single transaction.

**Rationale**: Prevents partial state on crash. SQLite WAL mode supports concurrent reads during writes.

---

### CANDIDATE-RL-003: Add query-level retry configuration to React Query hooks

**Location**: `src/hooks/use-queries.ts`

**Proposal**: Set `retry: 1` for write-adjacent queries and `retry: false` for health/capability checks that already have it. Add `staleTime` values to frequently-accessed queries that currently have none.

**Rationale**: Reduces unnecessary retries on transient failures and improves perceived performance.

---

### CANDIDATE-RL-004: Move Neo4j edge creation to parameterized relation types

**Location**: `backend/services/topic_service.py:200-207`, `backend/api/nodes.py:265-271`

**Proposal**: Pre-validate relation types against the whitelist, then use a lookup dict to select from a fixed set of Cypher templates instead of f-string interpolation. This eliminates the Cypher injection surface entirely.

---

### CANDIDATE-RL-005: Add `error_code`-based frontend error recovery

**Location**: `src/hooks/use-mutations.ts`, `src/services/api.ts`

**Proposal**: Parse the `error_code` field from API error responses and implement specific recovery actions:
- `SESSION_NOT_ACTIVE` -> invalidate session query, show "start new session" prompt
- `TOPIC_NOT_FOUND` -> redirect to home
- `NODE_NOT_FOUND` -> invalidate node query, refetch from graph

---

### CANDIDATE-RL-006: Add connection pool configuration to Neo4j driver

**Location**: `backend/core/deps.py:64-68`

**Proposal**: Configure `max_connection_pool_size=20`, `connection_acquisition_timeout=30`, and per-session `transaction_timeout=60` to prevent connection exhaustion under concurrent load.

---

### CANDIDATE-RL-007: Add idempotency key to `generate_article` endpoint

**Location**: `backend/api/nodes.py:394-461`

**Proposal**: Check-and-set pattern: read article_body, if empty claim via a SQLite flag (e.g., `article_generating` field or in-memory set with TTL), proceed with AI generation, clear flag on completion or timeout.

---

### CANDIDATE-RL-008: Include `sync_events` in topic cascade delete

**Location**: `backend/repositories/sqlite_repo.py:780-785`

**Proposal**: Add `"sync_events"` to the `direct_tables` list in `delete_topic`.

---

### CANDIDATE-RL-009: Add try/except to `get_session` API endpoint

**Location**: `backend/api/sessions.py:32-40`

**Proposal**: Wrap in standard try/except pattern consistent with all other endpoints.

---

### CANDIDATE-RL-010: Use atomic increment for mastered node count

**Location**: `backend/services/node_service.py:348-361`

**Proposal**: Replace the read-then-increment pattern with a single SQL UPDATE that only increments if the current node status is not "mastered":
```sql
UPDATE topics SET learned_nodes = learned_nodes + 1
WHERE topic_id = ? AND NOT EXISTS (
    SELECT 1 FROM concept_nodes WHERE node_id = ? AND status = 'mastered'
)
```
(Note: this requires the status to be tracked in SQLite, which it currently isn't — would need a status cache or Neo4j truth-source.)

---

### CANDIDATE-RL-011: Defer session completion claim until after synthesis

**Location**: `backend/services/session_service.py`

**Proposal**: Move `claim_session_completion` to after synthesis generation and review item creation. If synthesis fails, the session remains "active" and can be retried. Use a separate "completing" intermediate status to prevent concurrent completion attempts.

---

### CANDIDATE-RL-012: Add optimistic locking to ability record updates

**Location**: `backend/services/practice_service.py:306-320`, `backend/repositories/sqlite_repo.py`

**Proposal**: Add an `updated_at` or version column to ability_records. Use conditional UPDATE: `UPDATE ability_records SET ... WHERE topic_id = ? AND node_id = ? AND updated_at = ?`. If rowcount is 0, retry with fresh data.

---

### CANDIDATE-RL-013: Move raw SQL out of topic_service.list_topics

**Location**: `backend/services/topic_service.py:396-411`

**Proposal**: Create `sqlite_repo.batch_get_review_counts(db, topic_ids)` and `sqlite_repo.batch_get_deferred_counts(db, topic_ids)` repository methods.

---

### CANDIDATE-RL-014: Use node_id instead of node_name for review candidate resolution

**Location**: `backend/services/session_service.py:205-220`

**Proposal**: Update the Synthesizer prompt to return `node_id` directly (it already has access to the node data). Fall back to name matching only as a secondary strategy.

---

### CANDIDATE-RL-015: Add circuit breaker for Neo4j operations

**Location**: New file `backend/core/circuit_breaker.py`

**Proposal**: Track Neo4j operation failure rates. After N consecutive failures, short-circuit all Neo4j calls and use SQLite fallbacks immediately (instead of attempting and timing out). Reset after a cooldown period with a health check.

---

### CANDIDATE-RL-016: Guard `increment_topic_stats` in expand_node behind success check

**Location**: `backend/api/nodes.py:339`

**Proposal**: Move `increment_topic_stats` inside the success path and only increment by the actual number of nodes successfully written (track count from Neo4j/LanceDB write results).

---

### CANDIDATE-RL-017: Add timeout to async friction update task

**Location**: `backend/services/practice_service.py:262-264`

**Proposal**: Wrap `asyncio.create_task(_async_friction_update())` with `asyncio.wait_for(task, timeout=30)`. If it times out, log a warning and record a sync event.

---

### CANDIDATE-RL-018: Validate Neo4j rel_type in dedicated repository method

**Location**: `backend/repositories/neo4j_repo.py`

**Proposal**: Create `batch_create_relationships(session, edges)` that validates all rel_types against the whitelist and raises `ValueError` before any Cypher execution.

---

## Summary

| Category | Count |
|----------|-------|
| P0 Issues | 3 (RL-001, RL-002, RL-007) |
| P1 Issues | 7 (RL-004, RL-005, RL-006, RL-011, RL-017, RL-019, RL-020, RL-023) |
| P2 Issues | 12 (RL-003, RL-008, RL-009, RL-010, RL-012-RL-016, RL-018, RL-021, RL-022) |
| Candidates | 18 |
| **Total** | **41** |

### Top 3 Actions by Impact

1. **Implement sync event recovery worker** (addresses ISSUE-RL-001, partially mitigates RL-002/003/005/006/016/017)
2. **Add SQLite transaction wrapping for multi-step operations** (addresses ISSUE-RL-002/005/006/007)
3. **Add error-code-based frontend recovery** (addresses ISSUE-RL-020, improves UX for all error scenarios)
