# Article-First Workspace Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the node-first learning shell with an article-first workspace that supports a guide/source article reader, an article library sidebar, concept sheets, concept notes, and a lightweight command palette.

**Architecture:** Keep the existing topic/node backend APIs for concepts, graph data, and generated concept articles. Add a frontend article-workspace layer that composes guide/source/concept articles, persists source-article drafts and concept notes locally for now, and uses shadcn-style structural primitives with a warm editorial theme.

**Tech Stack:** React 19, React Router 7, TanStack Query 5, Zustand 5, Tailwind 4, Vitest 4

---

### Task 1: Lock the new workspace behavior with tests

**Files:**
- Create: `src/__tests__/article-workspace.test.tsx`
- Create: `src/features/article-workspace/workspace-helpers.ts`

**Step 1: Write failing tests**

- Assert helper functions build an article library with `guide`, `source`, and `concept` groups.
- Assert search results partition into `articles`, `concepts`, `notes`, and `recent`.
- Assert concept appearance state differentiates `candidate` vs `confirmed`.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/__tests__/article-workspace.test.tsx`

**Step 3: Write minimal implementation**

- Add pure helpers that transform topic/node/source-article state into workspace view models.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/__tests__/article-workspace.test.tsx`

### Task 2: Introduce the article workspace state layer

**Files:**
- Modify: `src/stores/app-store.ts`
- Modify: `src/types/index.ts`
- Create: `src/features/article-workspace/workspace-store.ts`

**Step 1: Write failing tests**

- Add coverage for restoring current article id, article kind, reading trail, and concept panel state through helper-driven state transitions.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/__tests__/article-workspace.test.tsx`

**Step 3: Write minimal implementation**

- Add article workspace types and persisted store state for:
  - current article
  - reading trail
  - source articles
  - concept notes
  - command palette / library visibility

**Step 4: Run test to verify it passes**

Run: `npm test -- src/__tests__/article-workspace.test.tsx`

### Task 3: Replace the app chrome with an article-first shell

**Files:**
- Modify: `src/app/app-layout.tsx`
- Modify: `src/components/shared/topbar.tsx`
- Modify: `src/styles/globals.css`
- Modify: `src/components/shared/index.tsx`
- Create: `src/features/article-workspace/article-workspace-layout.tsx`
- Create: `src/features/article-workspace/article-library-sidebar.tsx`
- Create: `src/features/article-workspace/article-header.tsx`
- Create: `src/features/article-workspace/breadcrumb-trail.tsx`

**Step 1: Write failing tests**

- Render the workspace shell and assert the presence of the library groups, breadcrumb meta line, and editorial article header.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/__tests__/article-workspace.test.tsx`

**Step 3: Write minimal implementation**

- Build the warm-paper workspace chrome.
- Move the old global nav behind a lighter article-library sidebar.
- Keep responsive behavior mobile-first.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/__tests__/article-workspace.test.tsx`

### Task 4: Refactor learning into the single-reader article workspace

**Files:**
- Modify: `src/routes/learning-page.tsx`
- Modify: `src/components/shared/article-renderer.tsx`
- Create: `src/features/article-workspace/concept-sheet.tsx`
- Create: `src/features/article-workspace/concept-note-panel.tsx`
- Create: `src/features/article-workspace/knowledge-map.tsx`

**Step 1: Write failing tests**

- Assert guide/source articles render through the reader model.
- Assert concept clicks route through the concept sheet instead of hard navigation.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/__tests__/article-workspace.test.tsx`

**Step 3: Write minimal implementation**

- Build one article reader that can render:
  - guide article
  - source article
  - concept article
- Add concept sheet state, concept note tabs, and knowledge-map card groups.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/__tests__/article-workspace.test.tsx`

### Task 5: Add authoring and lightweight command/search flows

**Files:**
- Modify: `src/routes/home-page.tsx`
- Create: `src/features/article-workspace/article-editor.tsx`
- Create: `src/features/article-workspace/command-palette.tsx`

**Step 1: Write failing tests**

- Assert source articles can be created in local workspace state and reappear in the library.
- Assert command helper results expose `new source article`, `open library`, `return to guide`, and `recent`.

**Step 2: Run test to verify it fails**

Run: `npm test -- src/__tests__/article-workspace.test.tsx`

**Step 3: Write minimal implementation**

- Add inline Markdown-style editing for source articles.
- Add a lightweight command palette shell and actions.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/__tests__/article-workspace.test.tsx`

### Task 6: Verify integration

**Files:**
- Test: `src/__tests__/article-workspace.test.tsx`
- Test: `src/__tests__/core-logic.test.ts`

**Step 1: Run targeted tests**

Run: `npm test -- src/__tests__/article-workspace.test.tsx src/__tests__/core-logic.test.ts`

**Step 2: Run full frontend test suite**

Run: `npm test`

**Step 3: Run production build**

Run: `npm run build`

**Step 4: Record known gaps**

- Call out backend gaps that remain local-only for this iteration:
  - multiple source-article persistence
  - concept-note server sync
  - cross-article search index
