# 2026-03-17 Frontend Remediation

## Scope

This remediation closes the browser-audited frontend defects found on 2026-03-17 for AxonClone's React/Tauri UI.

## Fixed Areas

### 1. Route-derived context replaced stale persisted context

- Stopped relying on persisted `current_topic_id/current_node_id/current_session_id` for navigation and page behavior.
- Added route/query-aware navigation resolution helpers and a shared `useResolvedTopicContext` hook.
- Updated shell navigation, topbar, graph page, assets page, and settings export target selection to use real route/query/topic data.
- Preserved persisted store usage only for UI state that is safe to restore, such as sidebar collapse, graph view preference, and practice draft text.

### 2. Summary, review, practice, and assets accuracy fixes

- Summary page now treats partial session fallback as partial data, hides fake precise cards, and shows an explicit warning instead.
- Review detail titles now fall back to the queued review item name when detail payloads omit `node_name`.
- Review submit/skip/snooze failures now surface visible toast feedback.
- Practice page now renders an explicit empty state when `nodeId` is missing instead of showing a blank page.
- Practice submissions no longer depend on stale session state and only attach `sessionId` when the route explicitly provides one.
- Practice completion only exposes the summary CTA when a reliable session id exists.
- Assets empty-state CTA now routes to practice only when a concrete node context exists; otherwise it returns to learning.

### 3. Settings and homepage UX/accessibility fixes

- Homepage form controls now have proper `label/htmlFor/id/name` wiring.
- Homepage recent-topic cards expose accessible action labels for continue/archive/delete actions.
- Homepage recent topics are sorted by `updated_at` descending and default intent/mode initialize from saved settings.
- Settings page now uses the resolved active topic as export default, exposes an explicit export target selector, and shows success/failure toast feedback.
- Settings form controls and toggle rows now have accessible ids, labels, and names.

### 4. Learning workspace responsive and status fixes

- Article workspace mobile header layout now stacks and wraps instead of collapsing at narrow widths.
- Article header typography now scales down on small screens.
- Article status chips now use the shared `articleStatusLabel(articleId, activeArticleId, trail, completedArticleIds)` helper, so the active article correctly renders as `在读` instead of `已浏览`.

## Key Files

- `src/lib/navigation-context.ts`
- `src/hooks/use-resolved-topic-context.ts`
- `src/stores/app-store.ts`
- `src/app/app-layout.tsx`
- `src/components/shared/topbar.tsx`
- `src/routes/graph-page.tsx`
- `src/routes/summary-page.tsx`
- `src/routes/practice-page.tsx`
- `src/routes/assets-page.tsx`
- `src/routes/review-page.tsx`
- `src/routes/home-page.tsx`
- `src/routes/settings-page.tsx`
- `src/features/article-workspace/article-workspace-page.tsx`
- `src/features/article-workspace/article-header.tsx`
- `src/__tests__/navigation-context.test.ts`
- `src/__tests__/summary-display.test.ts`
- `src/__tests__/review-display.test.ts`
- `src/__tests__/article-workspace.test.ts`
- `src/__tests__/route-pages.test.tsx`

## Verification

### Automated

Run on 2026-03-17 11:52:56 CST:

```bash
npm test
npm run build
npm run lint
```

Result:

- `npm test`: 10 test files passed, 51 tests passed.
- `npm run build`: TypeScript build and Vite production build succeeded.
- `npm run lint`: passed with no remaining frontend lint errors.

### Browser checks

Validated in a live browser session against the local frontend and backend:

- Health endpoint responded successfully: `GET http://127.0.0.1:8000/api/v1/health`
- Homepage showed labeled form fields and named recent-topic actions.
- Settings page showed labeled export controls, and export posted to `POST /api/v1/topics/tp_ng9tcvw5/export` with HTTP 200.
- Review detail rendered `复习: academic-research-skills` instead of an empty `复习:` title.
- Practice page without `nodeId` rendered an explicit empty state with `请选择一个节点后再开始练习`.
- Assets empty state now routes to `/topic/tp_ng9tcvw5/practice?nodeId=nd_3fmfzxq9` instead of the old blank practice page.
- Graph page rendered the `当前节点` action using route/topic-derived context.
- Clicking `当前节点` updated the URL to `?focus=nd_3fmfzxq9`.
- Learn workspace at `390x844` rendered the header and action row without the previous mobile collapse.
- The active article in the learn workspace rendered the status chip `在读`.
- Injected stale `axon-app-store` data (`tp_11768sfd / nd_hh1no3ck / ss_10339rzx`) into `localStorage`, refreshed the app, and confirmed sidebar quick-nav still resolved to the live topic `tp_ng9tcvw5` rather than the stale ids.
- No completed live session was available in the current dataset, so partial-summary rendering was verified via automated tests and code path inspection rather than a browser reproduction.
