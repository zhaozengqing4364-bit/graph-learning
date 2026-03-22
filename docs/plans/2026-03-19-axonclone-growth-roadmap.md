# AxonClone Growth Roadmap — 2026-03-19 Deep Refresh

> **Status**: refreshed against full codebase analysis on 2026-03-19.
> **Previous roadmap**: `docs/plans/2026-03-18-axonclone-growth-roadmap.md` (6 items, all still valid).
> **Latest verified signals**: `npm run lint` OK, `npm run build` OK, frontend 64 tests, backend 167 tests.

**Analysis inputs**: 5 parallel agents covering user journey friction (24 findings), core capability gaps, learning quality signals, test/iteration safety, and architecture drag points.

---

## What Changed Since Last Roadmap

The previous roadmap focused on product surface gaps (asset_highlights, practice re-entry, sync visibility). Those remain valid. But the deep analysis revealed **structural issues that make those surface fixes fragile**:

1. **sessionId propagation is broken across the core loop** — users lose session context when navigating between learn/practice/summary pages, causing the entire learn -> practice -> summary flow to fracture silently.
2. **Architecture drag is actively slowing iteration** — sqlite_repo.py is 2077 lines, API handlers bypass the service layer in 22 places, and front-end/back-end type contracts have drifted.
3. **Zero CI infrastructure exists** — no GitHub Actions, no coverage tools, no pre-commit hooks. Every iteration flies blind.
4. **Diagnoser few-shot bias may cause ability stagnation** — only negative delta examples exist, so AI may never award positive scores.
5. **Review queue includes never-practiced nodes** — generates noise for learners.

The previous roadmap's items (GROW-SUMMARY-001, GROW-ASSET-001, etc.) are **demoted but not dropped**. They should follow after the structural fixes, because fixing asset_highlights before fixing sessionId propagation means the feature still breaks in practice.

---

## Current System Understanding

**What's strong:**
- All P0 APIs are implemented with try/except + Chinese error messages
- AI four-role architecture strictly enforces responsibility separation
- Three-store write order (SQLite -> Neo4j -> LanceDB) with compensation
- Graph write validation pipeline (5-step) fully implemented
- ReviewPriority formula and spaced repetition algorithm match design docs
- 168 backend + 64 frontend tests, all green
- Article-first workspace is real product surface, not a placeholder

**What's fragile:**
- Core learning flow depends on sessionId passed via URL params, which is lost on navigation
- 22 API handlers import sqlite_repo directly, bypassing service layer
- Front-end/back-end types have 5+ drift points (PracticePrompt field names, ReviewStatus enum)
- No CI/CD, no coverage, no contract tests
- Diagnoser prompt has no positive-delta examples
- Review queue generation includes nodes with avg=0 (never practiced)

---

## Growth Score Snapshot

Scoring formula: `user leverage + core-capability leverage + evidence strength + compounding value + validation ease - blast radius`

| Rank | Item | ID | User | Core | Evidence | Compound | Validation | Blast | Net |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Fix sessionId propagation across core loop | GROW-FLOW-001 | 5 | 5 | 5 | 5 | 5 | 2 | **23** |
| 2 | Add GitHub Actions CI + coverage baseline | GROW-CI-001 | 2 | 3 | 5 | 5 | 5 | 1 | **19** |
| 3 | Fix Diagnoser few-shot bias + review queue noise | GROW-QUALITY-001 | 4 | 4 | 5 | 4 | 5 | 2 | **19** |
| 4 | Fix front-end/back-end type drift | GROW-TYPE-001 | 2 | 3 | 5 | 5 | 4 | 2 | **17** |
| 5 | Normalize and surface summary asset_highlights | GROW-SUMMARY-001 | 4 | 3 | 5 | 4 | 5 | 2 | **17** |
| 6 | Split sqlite_repo.py into domain modules | GROW-REPO-001 | 1 | 3 | 5 | 5 | 3 | 3 | **14** |
| 7 | Enforce service layer (remove API repo leakage) | GROW-API-001 | 1 | 4 | 5 | 5 | 3 | 3 | **15** |
| 8 | Add mutation feedback (toasts) across all pages | GROW-FEEDBACK-001 | 3 | 1 | 4 | 3 | 5 | 1 | **15** |
| 9 | Add asset-to-practice re-entry from assets page | GROW-ASSET-001 | 3 | 2 | 5 | 3 | 5 | 1 | **17** |
| 10 | Improve empty states with actionable guidance | GROW-EMPTY-001 | 3 | 1 | 4 | 2 | 4 | 1 | **13** |

---

## Highest-Leverage Bottlenecks

### 1. sessionId propagation is broken — the core loop fractures silently

**User problem:** learners who navigate from learn -> practice -> summary -> back to learn lose their session context. The session is the container that ties practice results to ability updates and summary generation. Without it, practice results still save, but session completion and summary generation break.

**Evidence:**
- `practice-page.tsx:59` reads sessionId from URL search params
- `article-workspace-page.tsx:269` reads sessionId from URL search params
- `navigation-context.ts:125-151` `buildLearnRoute` passes sessionId, but many call sites omit it
- `summary-page.tsx:221` next-recommendation click navigates without sessionId
- `review-page.tsx:258` "return to learn" navigates without sessionId
- `practice-page.tsx:218-259` `handleCompleteSession` returns null route when sessionId is empty
- Practice initiated from graph page has no session context at all

**Smallest credible slice:** audit all `navigate()` and `buildLearnRoute()` / `buildPracticeRoute()` calls to ensure sessionId is propagated when available. Add a navigation helper that automatically preserves sessionId from the current URL context.

**Validation:** route parameter tests + `npm test` + `npm run build`.

**Why first:** this breaks the product's main value loop. No amount of surface polish fixes a fractured core loop.

### 2. Zero CI infrastructure — every iteration flies blind

**User problem:** regressions can ship silently because nothing automatically validates the build and test baseline.

**Evidence:**
- No `.github/workflows/` directory
- No `pytest-cov` or `vitest --coverage` configuration
- No pre-commit hooks
- 168 backend + 64 frontend tests exist but are only run manually

**Smallest credible slice:** one GitHub Actions workflow that runs `npm run lint`, `npm run build`, `npm run test:all` on push/PR. Optionally add `pytest --cov` and `vitest --coverage` with a minimum threshold comment (not enforced).

**Validation:** push a commit and watch CI run.

**Why second:** CI is the foundation that makes safe-grow actually safe across sessions.

### 3. Diagnoser few-shot bias + review queue noise

**User problem:** ability scores may stagnate because Diagnoser only sees negative-delta examples, and review queues contain never-practiced nodes that waste learner time.

**Evidence:**
- `backend/prompts/diagnose.md` two few-shot examples both give negative deltas
- `review_service.py:620` generates review items for all nodes with avg < 70, including never-practiced nodes (avg=0)
- `PRACTICE_DIMENSION_MAP` shows 5 dimensions (example/contrast/recall/transfer/teach) only updatable through 1 practice type

**Smallest credible slice:**
1. Add one positive-delta few-shot example to `diagnose.md`
2. Add `min_practice_count >= 1` filter to `generate_review_queue`
3. Add teach_beginner and compress few-shot examples to `tutor_prompt.md`

**Validation:** backend tests for review queue filtering + prompt validation + `pytest`.

**Why third:** small prompt changes with high learning-quality impact.

### 4. Front-end/back-end type contract has drifted

**User problem:** type drift means front-end bugs surface at runtime instead of compile time.

**Evidence:**
- `PracticePrompt` field names differ (backend: `minimum_answer_hint`, frontend: `min_answer_hint`; backend: `evaluation_dimensions`, frontend: `scoring_dimensions`)
- `ReviewStatus` enum: frontend has `overdue` but not `due`/`cancelled`; backend has `due`/`cancelled` but not `overdue`
- `CompleteSessionResponse`, `StartSessionResponse`, `CreateTopicResponse` have `[key: string]: unknown` index signatures
- `asset_highlights` not in front-end types at all

**Smallest credible slice:** fix PracticePrompt field names to align (choose one convention), fix ReviewStatus enum, add `asset_highlights` to CompleteSessionResponse, remove `[key: string]: unknown` where possible.

**Validation:** `npm test` + `npm run build` (TS compiler catches mismatches).

**Why fourth:** type alignment is a prerequisite for GROW-SUMMARY-001 and other surface fixes.

---

## Horizon 1: Fix Core Loop Reliability

The immediate priority is making the main learning loop work end-to-end without silent fractures.

### Initiative 1: Fix sessionId propagation

- item: `GROW-FLOW-001`
- scope: all `navigate()` / `buildLearnRoute()` / `buildPracticeRoute()` calls
- success signal: learn -> practice -> summary -> back to learn preserves session context
- validation: route parameter tests + build

### Initiative 2: Fix Diagnoser bias and review noise

- item: `GROW-QUALITY-001`
- scope: `backend/prompts/diagnose.md`, `backend/prompts/tutor_prompt.md`, `backend/services/review_service.py`
- success signal: Diagnoser can award positive deltas; review queue excludes never-practiced nodes
- validation: backend tests + prompt inspection

---

## Horizon 2: Strengthen Iteration Foundation

Make future changes safer and faster.

### Initiative 3: Add GitHub Actions CI

- item: `GROW-CI-001`
- scope: `.github/workflows/ci.yml`, optionally `pytest-cov`, `vitest --coverage`
- success signal: push/PR triggers automated lint + build + test
- validation: CI itself

### Initiative 4: Fix front-end/back-end type drift

- item: `GROW-TYPE-001`
- scope: `src/types/index.ts`, `backend/models/practice.py`, review-related types
- success signal: no `[key: string]: unknown` on core response types; PracticePrompt and ReviewStatus aligned
- validation: `npm run build` catches mismatches

### Initiative 5: Add mutation feedback across all pages

- item: `GROW-FEEDBACK-001`
- scope: home-page.tsx (archive/delete), assets-page.tsx (favorite), practice-page.tsx
- success signal: every user action has visible success/error feedback
- validation: existing tests + manual spot-check

---

## Horizon 3: Close the Session-Asset Loop

After the core loop is reliable and types are aligned, surface the session outputs.

### Initiative 6: Normalize and surface asset_highlights

- item: `GROW-SUMMARY-001` (from previous backlog, now unblocked)
- scope: synthesizer.py schema, session_service.py, src/types/index.ts, summary-page.tsx
- success signal: summary shows concrete asset rows + assets CTA
- validation: backend tests + summary route tests + build

### Initiative 7: Add asset-to-practice re-entry

- item: `GROW-ASSET-001` (from previous backlog)
- scope: assets-page.tsx, navigation-context.ts
- success signal: asset cards link directly to practice for that node
- validation: assets route tests + build

---

## Horizon 4: Reduce Architecture Drag

Structural improvements that make all future work easier.

### Initiative 8: Split sqlite_repo.py

- item: `GROW-REPO-001`
- scope: `backend/repositories/sqlite_repo.py` -> 8-10 domain modules + migrations module + init module
- success signal: no file exceeds 300 lines; all existing tests pass without modification
- validation: `pytest` + `npm test` + build

### Initiative 9: Enforce service layer

- item: `GROW-API-001`
- scope: 12 API files — remove direct sqlite_repo imports, use FastAPI Depends injection
- success signal: zero direct repo imports from API layer; all DB access through service or Depends
- validation: `grep -r "from backend.repositories import sqlite_repo" backend/api/` returns nothing + all tests pass

---

## Immediate Next Safe-Grow Candidates (ordered by leverage)

1. **GROW-FLOW-001**: Fix sessionId propagation across all navigation paths
2. **GROW-QUALITY-001**: Fix Diagnoser few-shot bias + review queue noise filter
3. **GROW-CI-001**: Add GitHub Actions CI workflow
4. **GROW-TYPE-001**: Fix front-end/back-end type drift
5. **GROW-FEEDBACK-001**: Add toast feedback to all mutation operations

---

## Explicit Anti-Goals

- do not redesign the article workspace or routing architecture — fix propagation, not structure
- do not split sqlite_repo.py before CI exists — refactoring without a safety net is fragile
- do not add generic chat, multi-user, cloud, or enterprise features
- do not replace the current stack
- do not broaden CI into a full deployment pipeline before the basic lint+build+test gate works
- do not add E2E browser tests before the route parameter and navigation layer is stable
- do not redesign the summary page layout before the type contract is aligned

---

## Carried Forward from Previous Roadmap

These items remain valid but are now sequenced after structural fixes:

| Previous ID | Status | Reason for Reordering |
|---|---|---|
| GROW-SUMMARY-001 | deferred | Needs GROW-TYPE-001 first (type alignment) |
| GROW-ASSET-001 | deferred | Low risk, can follow after SUMMARY |
| GROW-RESILIENCE-001 | deferred | Lower leverage than flow/CI fixes |
| GROW-DESKTOP-001 | deferred | Desktop-only, lower priority |
| GROW-VERIFY-001 | deferred | E2E tests need stable navigation first |
| GROW-WORKFLOW-001 | dropped | Internal tooling, not user-facing value |

---

## Roadmap Validation Strategy

This roadmap is healthy only if:

- sessionId propagation is the top item (it breaks the core loop)
- CI exists before any refactoring begins
- type alignment precedes surface feature work
- sqlite_repo splitting waits for CI coverage baseline
- no item adds new features before the core loop is reliable
- Diagnoser prompt quality is verified before more AI-dependent features ship

If those stop being true, refresh this roadmap before continuing.
