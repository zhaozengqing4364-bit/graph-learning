# Architecture Drag Audit -- AxonClone

> Perspective: What structural problems are slowing delivery of the project's core value?
> Date: 2026-03-19

## Summary

The project has made significant architecture progress (sqlite_repo reduced from 2077 to 1715 lines, 87% API-to-repo calls moved to service layer). However, **two critical drag sources remain**: `nodes.py` `expand_node` (308 lines of inline business logic in API layer) and `article-workspace-page.tsx` (1732 lines -- the largest single-file component). Together these create the highest-risk change amplification zones. Additionally, there are structural frictions in data storage duplication (localStorage vs SQLite), Neo4j Cypher leaking into API layer, and sqlite_repo containing extractable domain clusters.

---

## Issues (structural problems that actively slow core value delivery)

### ISSUE-AD-001: `expand_node` -- 308 lines of business logic in API route layer

**File**: `backend/api/nodes.py:52-361`
**Severity**: High
**Category**: Layer violation / Change amplification

The `expand_node` endpoint contains the entire node expansion orchestration inline: session cap checking, AI agent invocation, Neo4j batch writes (Cypher queries directly in API), LanceDB vector writes, sync event recording, and topic stats incrementing. This is the single largest layer violation in the backend.

**Why it drags**: Every change to node expansion logic (e.g., adding a new edge type, changing the expansion algorithm, modifying write ordering) requires editing the API route file. The 5 `session.run()` calls with inline Cypher in nodes.py mean graph query changes are scattered across both `neo4j_repo.py` and `nodes.py`.

**Impact on core value**: Node expansion is the "knowledge network" step in the core value chain. This is where Explorer role generates the learning graph. Having 308 lines in the API layer makes it the riskiest area to modify and test.

**Evidence**: 4 direct `sqlite_repo` calls, 3 `from backend.repositories import neo4j_repo/lancedb_repo` lazy imports, 5 inline Cypher `session.run()` calls -- all inside what should be a thin route handler.

---

### ISSUE-AD-002: `generate_article` -- 66 lines of business logic bypassing service layer

**File**: `backend/api/nodes.py:394-460`
**Severity**: Medium
**Category**: Layer violation

The `generate_article` endpoint directly calls `article_generator` agent and writes to Neo4j, with sync event fallback recording. No service function wraps this. This is a second major business logic path in `nodes.py` that bypasses the service layer.

**Why it drags**: When the article generation prompt, neighbor fetching, or Neo4j save logic needs to change, the API route is the target. This breaks the "API/Service/Repository" contract that other endpoints follow.

---

### ISSUE-AD-003: `article-workspace-page.tsx` -- 1732 lines, the largest single component

**File**: `src/features/article-workspace/article-workspace-page.tsx`
**Severity**: High
**Category**: Component megathread / Cognitive overhead

This single file handles: article rendering, command palette, concept drawer, sidebar toggle, session flow, concept candidate management, source article CRUD, reading state persistence, workspace navigation, breadcrumb management, and recommendation logic. It imports 20+ React hooks, 8+ service functions, and 7+ lib functions.

**Why it drags**: This is the primary learning page -- the core user experience. Every new feature related to reading/workspace (concept linking, notes, candidates, search, backlinks) adds complexity to this file. At 1732 lines, the cognitive overhead for any developer making a change is very high, and merge conflicts are likely.

---

### ISSUE-AD-004: Neo4j Cypher queries leaked into `graph.py` API layer

**File**: `backend/api/graph.py:37-97`
**Severity**: Medium
**Category**: Layer violation

`get_topic_graph` contains 5 inline `session.run()` calls with raw Cypher for `mainline`, `prerequisite`, and `misconception` views. These are not routed through `neo4j_repo`.

**Why it drags**: Graph view logic changes require editing the API layer. If a new view mode is added or an existing view's query needs optimization, the change spans both `neo4j_repo.py` and `graph.py`.

---

### ISSUE-AD-005: `reviews.py` API directly enriches with Neo4j data instead of delegating to service

**File**: `backend/api/reviews.py:31-43`
**Severity**: Low
**Category**: Minor layer violation

The `list_reviews` endpoint directly calls `neo4j_repo.batch_get_concept_names` after fetching from service, mixing enrichment logic into the API layer.

**Why it drags**: The enrichment pattern (fetch from SQLite, enrich from Neo4j) is repeated in `reviews.py` and `stats.py` without a shared service helper. If enrichment logic changes, multiple API files must be updated.

---

### ISSUE-AD-006: `stats.py` API directly calls Neo4j for name enrichment

**File**: `backend/api/stats.py:49-55`
**Severity**: Low
**Category**: Minor layer violation

Same pattern as reviews.py -- direct Neo4j call for batch name enrichment in `get_topic_stats`.

---

### ISSUE-AD-007: `workspace-storage.ts` duplicates localStorage state that overlaps with backend SQLite

**File**: `src/lib/workspace-storage.ts`
**Severity**: Medium
**Category**: Data duplication / State consistency risk

Source articles, concept notes, and reading state are stored in both `localStorage` (via `workspace-storage.ts`) and SQLite (via backend API). The `article-workspace-page.tsx` uses localStorage as a write-through cache and the API as the source of truth, but the synchronization is implicit.

**Why it drags**: Any bug in the sync logic causes silent data divergence. If a user opens the app in a new browser, localStorage state is lost but SQLite state persists, creating inconsistent behavior. The `reading_state` is saved via mutation but loaded from localStorage first.

---

### ISSUE-AD-008: `practice-page.tsx` draft persistence uses raw localStorage instead of Zustand

**File**: `src/routes/review-page.tsx:34-53`
**Severity**: Low
**Category**: State management inconsistency

Review answer drafts are persisted via raw `localStorage.getItem/setItem` calls inside the component, bypassing both Zustand (which should handle UI state) and the backend.

---

### ISSUE-AD-009: `sqlite_repo.py` still contains 3 extractable domain clusters (ability, practice, friction)

**File**: `backend/repositories/sqlite_repo.py:832-1030` (ability: 832-894, practice: 896-941, friction: 944-1030)
**Severity**: Medium
**Category**: Module cohesion

The ability records (10 functions including snapshots), practice attempts (3 functions + prompt cache at 1276-1314), and friction records (3 functions + batch create) form three distinct domain clusters within the monolithic `sqlite_repo.py`. These have no cross-dependencies and are consumed by different services.

**Why it drags**: The 1715-line file is still too large to navigate efficiently. When a practice-related schema change is needed, the developer must work within the same file as topic CRUD, deferred node management, and sync event handling.

---

### ISSUE-AD-010: `sqlite_repo.py` contains article workspace functions that should align with `article_service`

**File**: `backend/repositories/sqlite_repo.py:1338-1703`
**Severity**: Medium
**Category**: Module cohesion

Lines 1338-1703 contain all article-related repository functions (articles, mentions, concept notes, reading state, concept candidates, backlinks, workspace search) -- approximately 365 lines. These are consumed exclusively by `article_service.py`, creating a hidden coupling between `sqlite_repo` and `article_service`.

---

### ISSUE-AD-011: `navigation-context.ts` mixes route parsing with business logic (160 lines)

**File**: `src/lib/navigation-context.ts`
**Severity**: Low
**Category**: Lib boundary

This file combines URL parsing helpers (`extractRouteTopicId`, `extractRouteSessionId`) with business logic (`resolveNavigationContext`, `pickResolvedTopic` which sorts by `updated_at` and filters by `active`). The route builders (`buildPracticeRoute`, `buildLearnRoute`, `buildSummaryRoute`) duplicate knowledge about URL structure that should be co-located with the router.

**Why it drags**: If the route structure changes, both `app.tsx` and `navigation-context.ts` must be updated in sync.

---

### ISSUE-AD-012: `article-workspace.ts` lib contains 516 lines of business logic

**File**: `src/lib/article-workspace.ts`
**Severity**: Low
**Category**: Lib boundary

This file contains extensive business logic: workspace article construction (guide/source/concept), command palette building, breadcrumb management, wiki link validation, next-article recommendations, and backlink computation. These are not pure utility functions -- they encode workspace-specific business rules.

**Why it drags**: `lib/` is conventionally for framework-agnostic utilities. Having 516 lines of workspace domain logic in `lib/` makes it harder to understand what's a reusable utility vs. workspace-specific logic.

---

### ISSUE-AD-013: No shared "Neo4j name enrichment" helper -- pattern duplicated across API files

**Files**: `backend/api/reviews.py:31-43`, `backend/api/stats.py:49-55`
**Severity**: Low
**Category**: Code duplication / Shared concern

Both `reviews.py` and `stats.py` independently fetch node names from Neo4j after getting data from services. The pattern (fetch node_ids, batch-get names, merge) is identical.

---

### ISSUE-AD-014: `_topic_exists` helper in `articles.py` directly queries SQLite

**File**: `backend/api/articles.py:25-28`
**Severity**: Low
**Category**: Minor layer violation

The `_topic_exists` helper runs a raw SQL query instead of delegating to a service or repo function. This is used in 11 out of 13 endpoints in `articles.py`.

---

### ISSUE-AD-015: `nodes.py` `expand_node` function has 3 nested `from backend.repositories import` statements

**File**: `backend/api/nodes.py:84, 290, 403, 447`
**Severity**: Low
**Category**: Dependency visibility

Multiple lazy imports of repository modules inside function bodies. While this avoids circular imports, it signals that the API layer is too tightly coupled to implementation details. The top-level import `from backend.repositories import sqlite_repo` at line 12 further confirms this coupling.

---

## Candidates (not currently slowing delivery, but structural risks worth watching)

### CANDIDATE-AD-001: Extract `expand_node` orchestration to `node_service.expand_node()`

The 308-line inline logic in `nodes.py:52-361` should be extracted to a `node_service.expand_node()` function that handles: session cap checking, AI invocation, validation, Neo4j batch writes (moved to `neo4j_repo` batch helpers), LanceDB writes, sync event recording, and topic stats update.

**Effort estimate**: Medium (the logic is complex but well-contained)
**Value**: Reduces the highest-risk change amplification zone; enables independent testing of expansion logic.

---

### CANDIDATE-AD-002: Extract `generate_article` to a service function

Move the article generation orchestration from `nodes.py:394-460` to either `node_service.generate_article()` or `article_service.generate_article()`.

**Effort estimate**: Small
**Value**: Completes the API/Service separation for the `nodes.py` file.

---

### CANDIDATE-AD-003: Split `article-workspace-page.tsx` into focused sub-components

Extract at minimum: (1) CommandPalette, (2) ConceptDrawer, (3) ArticleContentPanel, (4) SessionFlowControls. The page file should be ~300 lines of composition.

**Effort estimate**: Large (1732 lines to refactor, but each piece is already partially scoped)
**Value**: Reduces cognitive overhead on the most-changed file; reduces merge conflicts.

---

### CANDIDATE-AD-004: Extract `ability_repo.py` from `sqlite_repo.py`

Move ability_records and ability_snapshots CRUD (~60 lines) to a dedicated `ability_repo.py`.

**Effort estimate**: Small
**Value**: Reduces sqlite_repo from 1715 to ~1655; creates clean domain boundary.

---

### CANDIDATE-AD-005: Extract `practice_repo.py` from `sqlite_repo.py`

Move practice_attempts CRUD + practice_prompt_cache (~50 lines) to a dedicated `practice_repo.py`.

**Effort estimate**: Small
**Value**: Clean domain boundary; practice-related schema changes become isolated.

---

### CANDIDATE-AD-006: Extract `friction_repo.py` from `sqlite_repo.py`

Move friction_records CRUD (~90 lines) to a dedicated `friction_repo.py`.

**Effort estimate**: Small
**Value**: Clean domain boundary; friction records are a distinct diagnostic domain.

---

### CANDIDATE-AD-007: Extract `article_repo.py` from `sqlite_repo.py`

Move article-related functions (~365 lines) to a dedicated `article_repo.py`. This is the largest extractable cluster.

**Effort estimate**: Medium
**Value**: Reduces sqlite_repo from 1715 to ~1350; aligns repo structure with article_service boundary.

---

### CANDIDATE-AD-008: Move graph view Cypher queries from `graph.py` API to `neo4j_repo.py`

Create `get_mainline_edges`, `get_prerequisite_graph`, `get_misconception_graph` functions in `neo4j_repo.py`, and have `graph.py` call them.

**Effort estimate**: Medium
**Value**: Completes the repository encapsulation for graph queries.

---

### CANDIDATE-AD-009: Create a shared `enrich_with_node_names()` helper in a service

Extract the repeated "fetch node_ids, batch-get names from Neo4j, merge" pattern into a shared helper callable by `review_service`, `stats_service`, and any future consumer.

**Effort estimate**: Small
**Value**: Eliminates duplication; centralizes Neo4j enrichment logic.

---

### CANDIDATE-AD-010: Move `workspace-storage.ts` to a proper React Query cache strategy

Replace localStorage write-through caching with React Query's `initialData` or `placeholderData` + optimistic updates. The backend SQLite is the source of truth.

**Effort estimate**: Medium
**Value**: Eliminates localStorage/SQLite sync bugs; simplifies state management.

---

### CANDIDATE-AD-011: Move `navigation-context.ts` business logic to hooks

Extract `resolveNavigationContext`, `pickResolvedTopic` into `use-resolved-topic-context.ts` hook (which already exists at 42 lines). Keep pure URL parsing in `lib/`.

**Effort estimate**: Small
**Value**: Clearer separation between routing utilities and business logic.

---

### CANDIDATE-AD-012: Move `article-workspace.ts` from `lib/` to `features/article-workspace/`

The 516 lines of workspace-specific logic belong with the feature, not in the generic `lib/` directory.

**Effort estimate**: Small
**Value**: Clearer domain boundaries; `lib/` returns to pure utilities.

---

### CANDIDATE-AD-013: Move `practice-constants.ts` from `lib/` to the practice feature

These constants (PRACTICE_LABELS, PRACTICE_SEQUENCE) are domain-specific and used by practice components.

**Effort estimate**: Trivial
**Value**: Consistent domain organization.

---

### CANDIDATE-AD-014: Move `review-display.ts` and `summary-display.ts` from `lib/` to their respective feature areas

Both are display-specific helpers used by single pages.

**Effort estimate**: Trivial
**Value**: Consistent domain organization.

---

### CANDIDATE-AD-015: Consolidate route definitions to avoid `navigation-context.ts` / `app.tsx` sync

Currently route paths are defined in `app.tsx` and also constructed as strings in `navigation-context.ts`. If a route changes, both must be updated. Consider a shared route constants file.

**Effort estimate**: Small
**Value**: Single source of truth for route structure.

---

### CANDIDATE-AD-016: Add `_topic_exists` to `topic_service` instead of raw SQL in articles.py

Replace the `articles.py:25-28` helper with a service call.

**Effort estimate**: Trivial
**Value**: Consistent layer separation.

---

## Top Priority Actions

| Priority | Issue | Action | Expected Impact |
|----------|-------|--------|----------------|
| 1 | AD-001 | Extract `expand_node` to `node_service` | Eliminates the highest-risk layer violation; enables independent testing |
| 2 | AD-003 | Split `article-workspace-page.tsx` | Reduces merge conflict risk on the most-changed file |
| 3 | AD-002 | Extract `generate_article` to service | Completes API/service separation for nodes |
| 4 | AD-007+010 | Extract ability/practice/friction/article repos from sqlite_repo | Reduces sqlite_repo from 1715 to ~1350 lines |
| 5 | AD-004 | Move graph Cypher to neo4j_repo | Completes repository encapsulation |

## Metrics

- **Backend files with layer violations**: 4/12 API files (`nodes.py`, `graph.py`, `reviews.py`, `stats.py`)
- **Direct repo calls from API (excluding nodes.py)**: 5 calls across 4 files
- **Direct repo calls from nodes.py**: 5 calls (the single worst offender)
- **Inline Cypher in API layer**: 9 queries across 2 files
- **Frontend largest component**: 1732 lines (`article-workspace-page.tsx`)
- **Frontend lib/ files with business logic**: 3/9 (`navigation-context.ts`, `article-workspace.ts`, `workspace-storage.ts`)
- **sqlite_repo extractable clusters**: 4 (ability ~60L, practice ~50L, friction ~90L, article ~365L)
- **Estimated sqlite_repo post-extraction**: ~1350 lines (from 1715)
