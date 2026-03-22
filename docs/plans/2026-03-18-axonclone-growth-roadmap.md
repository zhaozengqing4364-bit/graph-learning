# AxonClone Growth Roadmap — 2026-03-18 Codex Refresh

> **Status**: refreshed against the real repository snapshot on 2026-03-18.
> **Latest verified signals**: `npm run lint` OK, `npm run build` OK, frontend `64` tests passed, backend `167` tests passed.
> **Planning note**: this repo currently ships `_axon/` as the live workflow directory. `.claude/` and `.codex/` planning directories are absent in this snapshot, so this roadmap uses `AGENTS.md`, `CLAUDE.md`, `_axon/loop/state.json`, audit docs, and the actual codebase as its evidence base.

**Planning inputs:** `AGENTS.md`, `CLAUDE.md`, `_axon/loop/state.json`, `task_plan.md`, `findings.md`, `progress.md`, `docs/audits/2026-03-16-frontend-surface-map.md`, `docs/audits/2026-03-16-full-frontend-audit.md`, plus current `src/`, `backend/`, `src-tauri/`, `scripts/`, and test suites.

## Current System Understanding

AxonClone has moved beyond the phase where whole surfaces were missing. The main learning path already exists in code:

- article workspace is the real learning shell, not a placeholder
- session start / visit / complete mutations are wired into the learning and practice flow
- summary, review, settings, assets, and stats routes all exist and are covered by targeted route or logic tests
- multi-store resilience is no longer theoretical: `sync_events` storage, indexes, queries, cleanup, and regression tests all exist
- the repo has a meaningful safety floor today: lint, build, 64 frontend tests, and 167 backend tests are green

That changes the planning problem. The next growth arc should not chase more pages or more abstractions. The main gaps are now:

1. session outputs are still only partly reusable on the frontend
2. expression assets are stored but still weakly connected back into practice
3. degraded runtime state is mostly invisible to the learner
4. desktop-shell capability exists but is not yet shaping the desktop experience
5. the highest-value user flow still lacks a true browser-level guardrail
6. the repo-local Axon workflow files are partially out of sync with the actual repo layout

## Strengths Worth Preserving

- **The product boundary is still sharp.** The repo still reinforces Topic -> Learn -> Practice -> Summary -> Review instead of drifting toward a generic chat app.
- **The article-first workspace is now real product surface.** Learning is anchored in articles, concepts, and reading state, not in disconnected route shells.
- **Session plumbing is materially better than in the original audit.** `useStartSessionMutation`, `useVisitNodeMutation`, and `useCompleteSessionMutation` are consumed in the core path.
- **Settings now influence behavior.** `auto_start_practice` and `auto_generate_summary` are read by real session-flow logic.
- **Resilience groundwork exists.** `sync_events` is persisted, queried, indexed, and regression-tested instead of existing only as an idea.
- **Verification culture is strong enough to support safe-grow.** The current test/build baseline makes small, validated iterations practical.

## Growth Score Snapshot

Scoring formula:
`user leverage + core-capability leverage + evidence strength + compounding value + validation ease - blast radius`

| Rank | Item | ID | User | Core | Evidence | Compound | Validation | Blast | Net |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Stabilize and surface summary asset highlights | `GROW-SUMMARY-001` | 5 | 5 | 5 | 4 | 5 | 2 | 22 |
| 2 | Add asset-to-practice re-entry | `GROW-ASSET-001` | 4 | 4 | 5 | 4 | 5 | 1 | 21 |
| 3 | Expose pending sync degradation in health surfaces | `GROW-RESILIENCE-001` | 4 | 4 | 5 | 5 | 4 | 2 | 20 |
| 4 | Consume desktop sidecar status in the app shell | `GROW-DESKTOP-001` | 4 | 4 | 5 | 4 | 4 | 2 | 19 |
| 5 | Add one deterministic browser smoke for the main loop | `GROW-VERIFY-001` | 3 | 4 | 5 | 5 | 2 | 3 | 16 |
| 6 | Align Axon workflow paths with actual repo layout | `GROW-WORKFLOW-001` | 1 | 2 | 5 | 5 | 4 | 1 | 16 |

## Highest-Leverage Bottlenecks

### 1. Summary-to-asset handoff is still contract-fragile and mostly invisible

**User problem:** after finishing a session, the learner sees asset counts but cannot reliably inspect what was saved or reuse it immediately.

**Desired user outcome:** summary should show concrete saved asset highlights and provide a direct next step into the asset library.

**System-capability outcome:** session outputs become stable reusable product data instead of backend-only metadata.

**Evidence:**

- `backend/services/session_service.py` supplements `asset_highlights` with object records from session assets
- `backend/agents/synthesizer.py` still declares `asset_highlights` as `string[]` in the summary schema
- `backend/tests/test_services.py` already asserts object-shaped `asset_highlights`
- `src/types/index.ts` does not model `asset_highlights` in `CompleteSessionResponse`
- `src/lib/summary-display.ts` consumes `new_assets_count` but drops `asset_highlights`
- `src/routes/summary-page.tsx` only renders the count card, not the saved assets themselves

**Likely files:**

- `backend/agents/synthesizer.py`
- `backend/services/session_service.py`
- `src/types/index.ts`
- `src/lib/summary-display.ts`
- `src/routes/summary-page.tsx`

**Smallest credible slice:** normalize `asset_highlights` to a stable array-of-objects contract across backend and frontend types, then render one compact highlights block plus a direct "查看资产库" CTA on summary.

**Dependencies:** existing summary payload and current summary route tests.

**Validation plan:** backend session tests for `asset_highlights` shape, summary-display tests, summary route tests, `npm test`, `.venv/bin/python -m pytest backend/tests -q`, `npm run build`.

**Success signal:** after a session with saved assets, the summary payload has a stable shape and the summary page shows concrete asset rows instead of only a number.

**Why not broader now:** do not redesign the entire summary page, add ranking logic, or build a new asset workflow before the contract is stable and visible.

### 2. The asset library is still closer to an archive than a practice tool

**User problem:** learners can inspect saved expressions, but the shortest route back into deliberate practice is still missing.

**Desired user outcome:** a saved expression should immediately reopen practice for the associated node.

**System-capability outcome:** expression assets become reusable training material instead of passive storage.

**Evidence:**

- `src/routes/assets-page.tsx` currently offers "查看节点" but not a direct practice CTA
- `buildPracticeRoute()` already exists and is used elsewhere for safe navigation into practice

**Likely files:**

- `src/routes/assets-page.tsx`
- `src/lib/navigation-context.ts`
- `src/__tests__/route-pages.test.tsx`

**Smallest credible slice:** add a per-asset "练习这个节点" entrypoint that routes to the practice page for `asset.node_id`.

**Dependencies:** none beyond the existing route builder.

**Validation plan:** assets route interaction tests, `npm test`, `npm run build`.

**Success signal:** from a non-empty assets page, one click takes the learner directly back into practice for that asset's node.

**Why not broader now:** do not build a full asset-workbench, reuse scoring system, or sorting overhaul before the basic re-entry path exists.

### 3. Degraded multi-store state exists in backend records but is still hidden from users

**User problem:** when Neo4j or LanceDB synchronization falls behind, learners can keep using the product without seeing that part of the system is degraded.

**Desired user outcome:** degraded synchronization should be visible in system health and settings before trust erodes.

**System-capability outcome:** `sync_events` becomes operationally useful instead of being only a backend recovery log.

**Evidence:**

- `backend/repositories/sqlite_repo.py` defines, records, lists, and cleans up `sync_events`
- `backend/tests/test_resilience.py` covers multiple partial-failure cases and confirms pending events are written
- `backend/api/system.py` currently returns service booleans and capabilities only
- `src/routes/settings-page.tsx` only renders coarse health dots and no sync backlog signal

**Likely files:**

- `backend/api/system.py`
- `backend/repositories/sqlite_repo.py`
- `src/routes/settings-page.tsx`
- backend and frontend health tests

**Smallest credible slice:** expose pending sync-event counts and latest degraded store through `/system/health` or `/system/capabilities`, then render a warning hint in settings when pending events exist.

**Dependencies:** existing `sync_events` repository queries.

**Validation plan:** backend API regression tests, settings page rendering tests, `.venv/bin/python -m pytest backend/tests -q`, `npm test`.

**Success signal:** a user can tell from settings that the system is partially degraded before they discover missing downstream data.

**Why not broader now:** do not build an auto-healer or cross-store orchestration daemon before visibility exists.

### 4. The desktop shell still behaves like a passive wrapper

**User problem:** in desktop mode, the user still gets no first-class signal for backend startup, unavailability, or degraded local runtime.

**Desired user outcome:** desktop users should know whether the local backend is healthy, starting, degraded, or unavailable.

**System-capability outcome:** the Tauri shell starts owning the runtime boundary instead of shipping dormant commands.

**Evidence:**

- `src/lib/tauri.ts` exports `isTauriDesktop()`, `startBackend()`, `stopBackend()`, and `checkBackendHealth()`
- repository-wide search shows no call sites for those functions
- `src-tauri/src/main.rs` already exposes `start_backend`, `stop_backend`, and `check_backend_health`
- `src/components/shared/topbar.tsx` currently shows learning/review navigation only

**Likely files:**

- `src/lib/tauri.ts`
- `src/app/app.tsx`
- `src/components/shared/topbar.tsx`
- `src/routes/settings-page.tsx`

**Smallest credible slice:** detect desktop mode in the app shell, check backend health on boot, and render a visible status chip or degraded banner.

**Dependencies:** existing Tauri commands.

**Validation plan:** targeted frontend tests around desktop status rendering plus `npm test` and `npm run build`.

**Success signal:** desktop mode visibly reports backend runtime state instead of silently assuming success.

**Why not broader now:** do not rewrite full startup orchestration or introduce background retry loops in the first slice.

### 5. Core workflow protection still stops at unit/API level

**User problem:** the highest-value learning path can still regress at route-integration level without a browser-level smoke.

**Desired user outcome:** fewer broken path regressions reach the learner.

**System-capability outcome:** future safe-grow turns have at least one real workflow guardrail.

**Evidence:**

- repo search finds no Playwright, Cypress, or other dedicated browser smoke entrypoint
- `findings.md` already records the lack of reliable browser automation evidence
- current frontend coverage is strong for route and logic tests, but not for a full Topic -> Learn -> Practice -> Summary path

**Likely files:**

- `package.json`
- a new lightweight browser smoke entrypoint under `scripts/` or a focused test directory
- route helpers and deterministic test data setup

**Smallest credible slice:** one deterministic Topic -> Learn -> Practice -> Summary smoke path, not a framework-wide E2E rollout.

**Dependencies:** stable seed data or deterministic test fixture path.

**Validation plan:** run the smoke itself, then `npm test` and `npm run build`.

**Success signal:** one high-value browser flow becomes repeatable enough to gate future changes.

**Why not broader now:** do not introduce a heavyweight E2E suite before the first narrow smoke proves its value.

### 6. Axon workflow files are partially out of sync with the actual repo layout

**User problem:** future planning and safe-grow automation is harder to resume because commands and instructions still point at missing directories.

**Desired user outcome:** the repo-local workflow can be resumed from real files instead of requiring manual path interpretation.

**System-capability outcome:** growth planning and safe iteration become less brittle across fresh sessions.

**Evidence:**

- `AGENTS.md` still instructs safe-grow and growth-planning reads under `.claude/loop/*`
- `_axon/scripts/codex-growth-plan.sh` still requires `.codex/roadmap/*`
- this repo snapshot has `_axon/` but no `.claude/` or `.codex/` directories
- `_axon/scripts/codex-loop.sh` expects `_axon/loop/GROWTH_BACKLOG.md` and related planning files that are only partially present today

**Likely files:**

- `AGENTS.md`
- `_axon/scripts/codex-growth-plan.sh`
- `_axon/scripts/codex-loop.sh`
- `_axon/loop/*`

**Smallest credible slice:** align docs and scripts on one live workflow directory, or add a compatibility layer that makes the expected files resolvable without manual guesswork.

**Dependencies:** none.

**Validation plan:** script `--dry-run` checks and file-presence checks.

**Success signal:** a fresh operator can run the documented growth or safe-grow scripts without path-related failure.

**Why not broader now:** do not redesign the full Axon framework; just make the repo-local workflow self-consistent.

## Horizon 1: Close the Session -> Asset Loop

This should remain the next product horizon. The system already creates summaries and saves expression assets; the immediate job is to make those outputs visible and reusable.

### Initiative 1: Stabilize and surface summary asset highlights

- item: `GROW-SUMMARY-001`
- user problem: summary currently hides or weakens the most reusable output of a session
- first slice: normalize `asset_highlights` contract and render a compact highlights card on summary
- validation: backend session tests + summary route tests + `npm test` + backend pytest + build
- success signal: concrete saved assets are visible on summary with a direct path to the library

### Initiative 2: Add direct asset-to-practice re-entry

- item: `GROW-ASSET-001`
- user problem: saved assets are inspectable but not actionable enough
- first slice: add a "练习这个节点" action for each asset card
- validation: assets route tests + `npm test` + build
- success signal: asset cards reopen practice directly

## Horizon 2: Make Runtime Health and Degradation Visible

This horizon turns hidden system state into visible product feedback.

### Initiative 3: Expose sync backlog in health surfaces

- item: `GROW-RESILIENCE-001`
- user problem: partial sync failure is invisible outside logs and tests
- first slice: add pending `sync_events` counts and a settings warning
- validation: backend API tests + settings page tests + backend pytest + frontend test run
- success signal: users can see degraded sync without opening logs

### Initiative 4: Consume Tauri sidecar status in the app shell

- item: `GROW-DESKTOP-001`
- user problem: the desktop runtime still feels like a browser app with silent assumptions
- first slice: surface desktop backend status in the shell
- validation: focused frontend tests + build
- success signal: desktop mode reports runtime state explicitly

## Horizon 3: Raise the Iteration Floor

This horizon improves the safety and repeatability of future work without losing focus on the learning loop.

### Initiative 5: Add one deterministic browser smoke for the main path

- item: `GROW-VERIFY-001`
- user problem: high-value flow regressions can still slip between route-level tests
- first slice: one Topic -> Learn -> Practice -> Summary browser smoke
- validation: smoke run + existing frontend checks
- success signal: one repeatable user-path guardrail exists

### Initiative 6: Make the repo-local Axon workflow self-consistent

- item: `GROW-WORKFLOW-001`
- user problem: workflow automation still depends on missing directories or partially installed files
- first slice: align one live directory and dry-run the scripts
- validation: dry-run script checks
- success signal: fresh sessions can resume workflow without path triage

## Immediate Next Safe-Grow Candidates

1. `GROW-SUMMARY-001`: normalize and surface `asset_highlights` on summary, then add a direct assets CTA
2. `GROW-ASSET-001`: add per-asset "练习这个节点" re-entry from the assets page
3. `GROW-RESILIENCE-001`: expose pending `sync_events` in system health/settings
4. `GROW-DESKTOP-001`: show desktop backend health using existing Tauri commands
5. `GROW-VERIFY-001`: add one deterministic browser smoke for Topic -> Learn -> Practice -> Summary

## Explicit Anti-Goals

- do not redesign the whole article workspace information architecture again
- do not rewrite routing or state management while the highest-leverage gaps are reuse and observability gaps
- do not add generic chat, multi-user, cloud, or enterprise features
- do not replace the current stack
- do not broaden resilience work into an auto-healing orchestration subsystem yet
- do not roll out a full E2E platform before one narrow smoke proves value

## Roadmap Validation Strategy

This roadmap should be considered healthy only if the following remain true:

- the top item is still clearly better than cosmetic cleanup or internal-only churn
- summary/asset work remains a single-turn safe-grow candidate with a bounded file set
- runtime visibility items stay behind the session/asset loop unless production evidence shows more urgent degradation
- browser smoke stays deterministic and narrow, not a broad framework rollout
- workflow-path alignment stays secondary unless missing files block the next growth or safe-grow execution

If those stop being true, refresh this roadmap before continuing.
