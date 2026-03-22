# Article Workspace Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an article-first learning workspace with an editorial reading shell, source article authoring, article library, concept side panel, command palette, and backend-backed persistence for article-specific learning state.

**Architecture:** Reuse backend topic and concept data as the canonical graph/concept source, then layer an article workspace model on top in the frontend. Known concept articles continue to come from the backend graph; source articles, concept notes, reading resume state, candidate concepts, backlinks, and initial source-article seeding are now persisted through dedicated backend article-workspace APIs.

**Tech Stack:** React 19, React Router 7, TanStack Query, Tailwind 4, FastAPI, SQLite, Neo4j, existing backend graph APIs, shadcn/ui-inspired composition and CSS-variable theming.

---

### Task 1: Lock in workspace data transforms with tests

**Files:**
- Create: `src/lib/article-workspace.ts`
- Test: `src/__tests__/article-workspace.test.ts`

**Step 1: Write the failing test**

Cover:
- topic + entry node -> guide article transform
- graph nodes + local source articles -> article library sections
- breadcrumb push/pop behavior
- command palette result grouping

**Step 2: Run test to verify it fails**

Run: `npm test -- src/__tests__/article-workspace.test.ts`

**Step 3: Write minimal implementation**

Add pure helpers only.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/__tests__/article-workspace.test.ts`

### Task 2: Add persistent workspace store

**Files:**
- Modify: `src/stores/app-store.ts`
- Create: `src/lib/workspace-storage.ts`
- Test: `src/__tests__/workspace-storage.test.ts`

**Step 1: Write the failing test**

Cover:
- source article persistence
- concept note persistence
- reading position persistence

**Step 2: Run test to verify it fails**

Run: `npm test -- src/__tests__/workspace-storage.test.ts`

**Step 3: Write minimal implementation**

Persist only article-workspace data that the backend lacks.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/__tests__/workspace-storage.test.ts`

### Task 3: Rebuild the learning route into an article workspace

**Files:**
- Modify: `src/routes/learning-page.tsx`
- Create: `src/components/workspace/*`
- Modify: `src/components/shared/article-renderer.tsx`

**Step 1: Add failing rendering test(s)**

Cover:
- article library renders sections
- article header renders source tag/title/deck
- concept panel action states

**Step 2: Run targeted tests to verify failure**

Run: `npm test -- src/__tests__/workspace-ui.test.tsx`

**Step 3: Implement minimal UI**

Add:
- guide/source/concept article selection
- editorial reading column
- article library sidebar
- breadcrumb trail
- concept panel and source-article edit mode

**Step 4: Run targeted tests**

Run: `npm test -- src/__tests__/workspace-ui.test.tsx`

### Task 4: Update global shell and theme

**Files:**
- Modify: `src/app/app-layout.tsx`
- Modify: `src/components/shared/topbar.tsx`
- Modify: `src/styles/globals.css`
- Modify: `src/components/ui/index.tsx`

**Step 1: Add or extend tests if pure logic exists**

Prefer snapshot/static render tests for lightweight shell pieces.

**Step 2: Implement**

Add:
- editorial CSS variables
- narrow reading column
- quieter shell chrome
- command-palette trigger

**Step 3: Verify**

Run: `npm test -- src/__tests__/core-logic.test.ts src/__tests__/stats-page.test.tsx`

### Task 5: Full verification

**Files:**
- N/A

**Step 1: Run frontend tests**

Run: `npm test`

**Step 2: Run build**

Run: `npm run build`

**Step 3: Record remaining backend-dependent gaps**

Document anything that is still simulated locally because the backend surface is missing.

---

## Execution Notes

### Completed

- Added `src/lib/article-workspace.ts` as the workspace domain layer:
  - guide article transform
  - library section assembly
  - breadcrumb helpers
  - command palette grouping
  - wiki link validation
  - next-article recommendation
  - concept backlinks from local source articles
- Added backend article-workspace data model and persistence:
  - `backend/models/article.py`
  - `backend/services/article_service.py`
  - `backend/api/articles.py`
  - `backend/repositories/sqlite_repo.py` article tables, indexes, and CRUD support
- Added backend article-workspace APIs for:
  - source article CRUD
  - workspace bundle loading
  - concept note read/write
  - reading-state read/write
  - candidate concept create / confirm / ignore
  - concept backlinks
  - workspace search
- Wired topic creation to seed an initial source article from `topics.source_content`:
  - `backend/services/topic_service.py`
  - seed article is analyzed immediately so candidate concepts and mentions exist from the first load
- Added article-workspace UI components:
  - `src/features/article-workspace/article-header.tsx`
  - `src/features/article-workspace/article-library-sidebar.tsx`
  - `src/features/article-workspace/article-footer-panel.tsx`
  - `src/features/article-workspace/concept-drawer-content.tsx`
  - `src/features/article-workspace/article-workspace-page.tsx`
- Replaced `src/routes/learning-page.tsx` with an article-first workspace adapter.
- Reworked `src/components/shared/article-renderer.tsx` to support:
  - weak concept highlighting
  - explicit `[[concept]]` links
  - click-to-open concept panel
  - manual text selection -> mark concept
  - paragraph anchors for backlinks
- Updated shell and entry flow:
  - `src/app/app-layout.tsx` now bypasses the old global app shell for `/topic/:topicId/learn`
  - `src/routes/home-page.tsx` now enters the article workspace directly
  - `src/main.tsx` now wraps the app with `TooltipProvider`
- Replaced `src/styles/globals.css` with a warm-paper editorial theme compatible with the shadcn-generated components.
- Migrated the workspace page from local-only persistence to backend-backed React Query flows:
  - `src/features/article-workspace/article-workspace-page.tsx`
  - `src/hooks/use-queries.ts`
  - `src/hooks/use-mutations.ts`
  - `src/services/index.ts`
  - `src/services/api-client.ts`
  - `src/types/index.ts`
- Added debounced backend persistence for:
  - reading resume state
  - completed article ids
  - concept notes
- Replaced local candidate confirmation / ignore state with backend candidate records so candidate concepts survive reloads and feed backlinks / graph confirmation correctly.
- Added force-refresh support for concept articles backed by the existing article generation endpoint:
  - `backend/api/nodes.py` now accepts `force=true` on `generate-article`
  - `src/features/article-workspace/article-workspace-page.tsx` now turns the “有新材料可更新” banner into an executable refresh action
- Fixed an unrelated compile blocker in `src/components/ui/confirm-dialog.tsx` while getting the full app build green.

### Verification Results

- Targeted workspace tests:
  - `npm test -- src/__tests__/article-workspace.test.ts`
  - `14 passed`
- Added UI shell tests:
  - `npm test -- src/__tests__/workspace-ui.test.tsx`
  - `2 passed`
- Broader frontend regression slice:
  - `npm test -- src/__tests__/article-workspace.test.ts src/__tests__/article-workspace.test.tsx src/__tests__/workspace-storage.test.ts src/__tests__/workspace-ui.test.tsx src/__tests__/core-logic.test.ts src/__tests__/stats-page.test.tsx`
  - `30 passed`
- Full frontend test suite:
  - `npm test`
  - `31 passed`
- Production build:
  - `npm run build`
  - success
  - added Vite 8 `rolldownOptions.output.codeSplitting` vendor grouping in `vite.config.ts`
  - bundle warning for oversized chunks is gone
- Targeted backend article-workspace API suite:
  - `cd backend && uv run python -m pytest tests/test_articles_api.py -q`
  - `4 passed`
- Targeted forced article refresh regression:
  - `cd backend && uv run python -m pytest tests/test_api.py -q -k generate_article_force_refresh`
  - `1 passed`
- Backend regression suite:
  - `cd backend && uv run python -m pytest tests/ -q`
  - `99 passed`

### Current Notes

- The command palette now switches to the backend `workspace-search` endpoint when the user types a query, so article / concept / note hits can come from persisted workspace data instead of only the already-loaded in-memory lists.
- Existing concept article generation still uses the current node article-generation endpoint; confirming a candidate concept makes it eligible for that same generation path, and concept articles can now be force-refreshed when newer source material appears.
- `src/lib/workspace-storage.ts` remains only as a legacy local cleanup utility and compatibility layer for older tests; it is no longer the source of truth for workspace persistence.
