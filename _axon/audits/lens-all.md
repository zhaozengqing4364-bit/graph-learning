# AxonClone 6-Lens Audit Report

> Generated: 2026-03-19 | Codebase scan date: 2026-03-19
> Total: 60 ISSUE + 60 CANDIDATE = 120 items across 6 lenses

---

## Lens 1: User Journey (UJ) — Frontend Experience Friction

### ISSUE-UJ-001: Practice page draft persists across node switches with stale ref check
- **User scenario**: User switches from node A to node B on practice page, sees stale answer from node A briefly
- **Impact degree**: Medium
- **Problem detail**: `practice-page.tsx:100-108` uses `prevNodeIdRef` to clear draft on node switch, but `answerState.nodeId` comparison at line 93 means the UI can flash old content for one render frame before the useEffect fires. The `setPracticeDraft('')` in the effect is conditional on `practice_draft` being truthy, so if the draft was already cleared by a previous navigation, the cleanup is skipped.
- **Files involved**: `src/routes/practice-page.tsx:92-108`
- **Min fix**: Reset answer state synchronously in the render when nodeId changes, not in useEffect
- **Validation**: Switch nodes rapidly and verify no stale text appears
- **Score**: [user_leverage:4, core_capability:2, evidence:3, compounding:2, validation_ease:5, blast_radius:2]

### ISSUE-UJ-002: Review queue generation runs on all active topics without progress indication
- **User scenario**: User clicks "generate review queue" with 5+ topics, sees no per-topic progress
- **Impact degree**: Medium
- **Problem detail**: `review-page.tsx:62-84` fires `Promise.allSettled(activeTopics.map(...))` which can take 30+ seconds for multiple topics. Only a generic "isGenerating" spinner is shown, with no indication of which topics have been processed or how many remain.
- **Files involved**: `src/routes/review-page.tsx:62-84`
- **Min fix**: Show progress like "Processing topic 2/5..." or use sequential processing with per-topic status
- **Validation**: Create 3+ topics with ability records, click generate, observe progress
- **Score**: [user_leverage:4, core_capability:3, evidence:4, compounding:2, validation_ease:4, blast_radius:2]

### ISSUE-UJ-003: No error boundary wrapping route components
- **User scenario**: JavaScript error in any page crashes the entire app
- **Impact degree**: High
- **Problem detail**: An `error-boundary.tsx` component exists in `src/components/ui/` but no route page is wrapped with it. If any page throws during render, the user sees a blank white screen. The `src/routes/index.ts` does not use `ErrorBoundary`.
- **Files involved**: `src/routes/index.ts`, `src/components/ui/error-boundary.tsx`
- **Min fix**: Wrap each route's element in `<ErrorBoundary>` in the route config
- **Validation**: Throw an error in a page render, verify fallback UI shows
- **Score**: [user_leverage:5, core_capability:2, evidence:5, compounding:3, validation_ease:5, blast_radius:4]

### ISSUE-UJ-004: Graph page dagreLayout recalculates on every render cycle
- **User scenario**: User hovers nodes in graph, layout flickers or repositions
- **Impact degree**: Medium
- **Problem detail**: `graph-page.tsx:19-69` implements `dagreLayout` inline with no memoization. Called from `useMemo` at line 171 which depends on `graphData` and filters, but node click/hover events trigger re-renders that recalculate positions unnecessarily since the layout algorithm is deterministic and depends only on the topology.
- **Files involved**: `src/routes/graph-page.tsx:19-69,171`
- **Min fix**: Extract layout to a separate `useMemo` keyed only on `(nodes.length, edges.length, focusNodeId)`
- **Validation**: Open graph with 20+ nodes, hover nodes, observe no visual jumps
- **Score**: [user_leverage:3, core_capability:2, evidence:4, compounding:2, validation_ease:4, blast_radius:2]

### ISSUE-UJ-005: Stats page has duplicate early return for loading state
- **User scenario**: User sees a flash of duplicate loading skeleton on stats page
- **Impact degree**: Low
- **Problem detail**: `stats-page.tsx` has `if (topicsLoading)` at line 42 and again at line 76. The second check is dead code since the first return already exited. But this indicates copy-paste neglect.
- **Files involved**: `src/routes/stats-page.tsx:42,76`
- **Min fix**: Remove duplicate loading check at line 76
- **Validation**: Code review only
- **Score**: [user_leverage:1, core_capability:1, evidence:3, compounding:1, validation_ease:5, blast_radius:1]

### ISSUE-UJ-006: Home page deferred nodes panel lacks empty state for resolved state
- **User scenario**: User has no deferred nodes but still sees an empty bordered box
- **Impact degree**: Low
- **Problem detail**: `home-page.tsx:346-362` renders the deferred nodes panel when `deferredNodes.length > 0`, which is correct. However, the "Recent Practice" panel at line 365-380 similarly renders only when data exists. The issue is that if `deferredData` is still loading (undefined), the panel silently disappears with no loading indicator.
- **Files involved**: `src/routes/home-page.tsx:64-65`
- **Min fix**: Show loading skeleton for deferred nodes while data is fetching
- **Validation**: Create topic, observe deferred panel loading state
- **Score**: [user_leverage:2, core_capability:1, evidence:3, compounding:1, validation_ease:5, blast_radius:1]

### ISSUE-UJ-007: No keyboard shortcut for common practice actions
- **User scenario**: Power user wants to submit with Ctrl+Enter instead of clicking button
- **Impact degree**: Medium
- **Problem detail**: `practice-page.tsx:470-517` has no `onKeyDown` handler on the textarea for keyboard shortcuts. The user must click "submit" button. Similarly, `review-page.tsx:170-207` lacks Ctrl+Enter shortcut for review submission.
- **Files involved**: `src/routes/practice-page.tsx:473-487`, `src/routes/review-page.tsx:172-182`
- **Min fix**: Add `onKeyDown={(e) => { if (e.ctrlKey && e.key === 'Enter') handleSubmit() }}` to the textarea
- **Validation**: Type answer, press Ctrl+Enter, verify submission
- **Score**: [user_leverage:4, core_capability:1, evidence:4, compounding:2, validation_ease:5, blast_radius:2]

### ISSUE-UJ-008: Summary page "view all assets" link navigates to non-existent route
- **User scenario**: User clicks "view all assets" on summary page, gets 404
- **Impact degree**: Medium
- **Problem detail**: `summary-page.tsx:232-238` links to `/topic/${topicId}/assets` but no route handler exists for this path in `src/routes/index.ts`. Available routes are `learn`, `graph`, `practice`, `reviews`, `stats`, `settings`.
- **Files involved**: `src/routes/summary-page.tsx:233`
- **Min fix**: Change link to `/stats` or add a dedicated assets route
- **Validation**: Click the link, verify navigation works
- **Score**: [user_leverage:3, core_capability:2, evidence:5, compounding:1, validation_ease:5, blast_radius:2]

### ISSUE-UJ-009: Practice page back button has no confirmation for submitted but unsaved feedback
- **User scenario**: User gets feedback, doesn't save expression asset, clicks back, loses ability to save
- **Impact degree**: Low
- **Problem detail**: `practice-page.tsx:325` shows leave confirmation only when `practice_state === 'answering' && answer.trim()`, but not when in `feedback_ready` state where the user has valuable AI feedback they haven't saved as an expression asset.
- **Files involved**: `src/routes/practice-page.tsx:325`
- **Min fix**: Extend leave confirmation to `feedback_ready` state
- **Validation**: Get feedback, click back, verify confirmation dialog shows
- **Score**: [user_leverage:2, core_capability:2, evidence:3, compounding:1, validation_ease:4, blast_radius:1]

### ISSUE-UJ-010: Graph sidebar does not close on navigation
- **User scenario**: User opens graph sidebar, clicks "go to learn", sidebar stays open when returning to graph
- **Impact degree**: Low
- **Problem detail**: `graph-page.tsx` stores `graph_sidebar_open` in Zustand with `partialize` that only persists `sidebar_collapsed` and `graph_view`. When the user navigates away and back, `graph_sidebar_open` resets to `true` (initial state) but the selected node remains, creating a confusing "stale sidebar" experience.
- **Files involved**: `src/routes/graph-page.tsx:379-454`, `src/stores/app-store.ts:111-114`
- **Min fix**: Reset `graph_selected_node_id` when navigating away from graph page
- **Validation**: Open sidebar, navigate away and back, verify clean state
- **Score**: [user_leverage:2, core_capability:1, evidence:3, compounding:1, validation_ease:4, blast_radius:1]

### CANDIDATE-UJ-001: Practice type selector should show completion checkmarks per node
- **User problem**: User doesn't know which practice types they've already completed for the current node without scrolling to the history panel
- **User benefit**: One-glance visibility of practice progress for current node
- **Min entry point**: Add checkmark badges to the top-level practice type buttons (line 335-349) similar to the idle state buttons (line 363-381)
- **Files involved**: `src/routes/practice-page.tsx:335-349`
- **Score**: [user_leverage:3, core_capability:2, evidence:4, compounding:2, validation_ease:5, blast_radius:1, total:17]

### CANDIDATE-UJ-002: Add estimated time for AI operations
- **User problem**: User clicks "generate summary" and doesn't know if it takes 5 seconds or 60 seconds
- **User benefit**: Better expectations, less perceived "stuckness"
- **Min entry point**: Show "Estimated: 10-30 seconds" text near loading spinners for AI operations
- **Files involved**: `src/routes/practice-page.tsx:521-526`, `src/routes/home-page.tsx:174-178`
- **Score**: [user_leverage:3, core_capability:1, evidence:3, compounding:1, validation_ease:5, blast_radius:1, total:14]

### CANDIDATE-UJ-003: Concept drawer should show node ability on hover
- **User problem**: User sees concept link in article but doesn't know their current ability level for that node
- **User benefit**: Helps user decide whether to click through to learn or practice
- **Min entry point**: Show a mini ability badge next to concept links that have ability records
- **Files involved**: `src/components/shared/article-renderer.tsx`, `src/features/article-workspace/concept-drawer-content.tsx`
- **Score**: [user_leverage:3, core_capability:3, evidence:3, compounding:2, validation_ease:3, blast_radius:2, total:16]

### CANDIDATE-UJ-004: Review page should auto-advance after successful review
- **User problem**: User must click "continue to next" after each review, breaking flow
- **User benefit**: Faster review sessions for users doing 10+ reviews
- **Min entry point**: Add a 2-second auto-advance timer after successful review, with cancel option
- **Files involved**: `src/routes/review-page.tsx:254-256`
- **Score**: [user_leverage:3, core_capability:2, evidence:3, compounding:2, validation_ease:4, blast_radius:1, total:15]

### CANDIDATE-UJ-005: Add breadcrumb navigation to practice and review pages
- **User problem**: User lands on practice page from a deep link and doesn't know which topic they're in
- **User benefit**: Better spatial orientation in the learning flow
- **Min entry point**: Add a breadcrumb like "Home > Topic > Node > Practice" at the top
- **Files involved**: `src/routes/practice-page.tsx:323-333`, `src/routes/review-page.tsx:143-148`
- **Score**: [user_leverage:3, core_capability:1, evidence:4, compounding:2, validation_ease:4, blast_radius:2, total:16]

### CANDIDATE-UJ-006: Graph edge labels should show relationship type inline
- **User problem**: User must hover edges to see relationship type, which is tedious for dense graphs
- **User benefit**: Quick understanding of graph structure without interaction
- **Min entry point**: Add small type labels on edges using React Flow edge label feature
- **Files involved**: `src/components/shared/graph-adapter.ts`
- **Score**: [user_leverage:2, core_capability:2, evidence:3, compounding:1, validation_ease:3, blast_radius:1, total:12]

### CANDIDATE-UJ-007: Practice textarea should auto-resize more aggressively
- **User problem**: User writes a long answer and the textarea stays small, requiring manual scroll
- **User benefit**: Better writing experience for longer practice answers
- **Min entry point**: Increase max-height and use `overflow: auto` instead of fixed `rows={5}`
- **Files involved**: `src/routes/practice-page.tsx:473-487`
- **Score**: [user_leverage:2, core_capability:1, evidence:4, compounding:1, validation_ease:5, blast_radius:1, total:14]

### CANDIDATE-UJ-008: Add "Mark as mastered" button to practice page
- **User problem**: User gets a "good" rating but must manually navigate to set node status to mastered
- **User benefit**: One-click mastery acknowledgment after successful practice
- **Min entry point**: Add a "Mark mastered" button when feedback is "good" and ability avg >= 70
- **Files involved**: `src/routes/practice-page.tsx:537-647`
- **Score**: [user_leverage:3, core_capability:3, evidence:3, compounding:2, validation_ease:4, blast_radius:2, total:17]

### CANDIDATE-UJ-009: Home page should show learning streak or daily activity
- **User problem**: User has no motivation metric on the home page
- **User benefit**: Daily engagement indicator
- **Min entry point**: Add a "days active" or "streak" counter to the home page hero section
- **Files involved**: `src/routes/home-page.tsx:69-180`
- **Score**: [user_leverage:2, core_capability:1, evidence:2, compounding:1, validation_ease:3, blast_radius:1, total:10]

### CANDIDATE-UJ-010: Settings page export should show preview before download
- **User problem**: User clicks export and immediately downloads without seeing content first
- **User benefit**: Verify export content before saving to disk
- **Min entry point**: Show a preview modal with first 20 lines of exported content
- **Files involved**: `src/routes/settings-page.tsx:69-90`
- **Score**: [user_leverage:2, core_capability:1, evidence:3, compounding:1, validation_ease:3, blast_radius:1, total:11]

---

## Lens 2: Core Capability (CC) — Product Promise Delivery

### ISSUE-CC-001: Explorer agent truncates source content to 8000 chars silently
- **User scenario**: User pastes a long article, only first 8000 chars are processed
- **Impact degree**: High
- **Problem detail**: `explorer.py:153-158` silently truncates `source_content` to 8000 characters with only a warning log. The user has no UI indication that their content was truncated. This means large articles lose significant information.
- **Files involved**: `backend/agents/explorer.py:153-158`
- **Min fix**: Return truncation metadata to the caller and show a warning in the UI
- **Validation**: Paste 15000 char article, verify UI shows truncation warning
- **Score**: [user_leverage:5, core_capability:5, evidence:5, compounding:3, validation_ease:4, blast_radius:3]

### ISSUE-CC-002: Diagnoser fallback returns empty friction_tags, breaking the feedback loop
- **User scenario**: AI Diagnoser fails, user gets no friction identification or recommendations
- **Impact degree**: High
- **Problem detail**: `diagnoser.py:120-130` `diagnose_fallback()` returns empty `friction_tags: []` and empty `ability_delta: {}`. In `practice_service.py:148-153`, when fallback is used, `friction_tags` and `ability_delta` stay empty, meaning the practice session produces no diagnostic signal, no recommended next practice, and no misconception tracking.
- **Files involved**: `backend/agents/diagnoser.py:120-130`, `backend/services/practice_service.py:148-153`
- **Min fix**: Generate a basic ability_delta in fallback based on feedback correctness (good=+5, medium=+3, weak=-3)
- **Validation**: Simulate Diagnoser failure, verify fallback still produces ability update
- **Score**: [user_leverage:5, core_capability:5, evidence:5, compounding:4, validation_ease:4, blast_radius:4]

### ISSUE-CC-003: Tutor static feedback fallback provides no recommended_answer or expression_skeleton
- **User scenario**: AI Tutor fails, user gets "feedback temporarily unavailable" with no model answer
- **Impact degree**: Medium
- **Problem detail**: `tutor.py:226-236` `static_feedback_fallback()` returns empty `recommended_answer: ""` and `expression_skeleton: ""`. The practice page at line 592-613 shows the "recommended expression" box which is empty, and the "expression skeleton" box which is empty, resulting in confusing empty UI sections.
- **Files involved**: `backend/agents/tutor.py:226-236`
- **Min fix**: At minimum populate `recommended_answer` with a generic template like "Based on the topic..."
- **Validation**: Simulate Tutor failure, verify practice page shows meaningful fallback
- **Score**: [user_leverage:4, core_capability:4, evidence:4, compounding:3, validation_ease:4, blast_radius:3]

### ISSUE-CC-004: Learning intent "prepare_expression" does not increase practice density
- **User scenario**: User selects "prepare_expression" intent, expects more practice prompts but gets same flow
- **Impact degree**: Medium
- **Problem detail**: Per CLAUDE.md, `prepare_expression` should "increase expression practice density." However, the Explorer agent's intent guidance at `explorer.py:17` only says "normal flow but consider expression training convenience." The Tutor at `tutor.py:15` says "increase expression practice density" but there is no actual mechanism to force more practice prompts or auto-redirect to practice.
- **Files involved**: `backend/agents/explorer.py:17`, `backend/agents/tutor.py:15`, CLAUDE.md
- **Min fix**: Implement `prepare_expression` detection in the session flow to auto-suggest practice after each node
- **Validation**: Create topic with prepare_expression intent, verify practice prompts appear more frequently
- **Score**: [user_leverage:3, core_capability:5, evidence:5, compounding:3, validation_ease:3, blast_radius:3]

### ISSUE-CC-005: Review queue generation only considers nodes with avg < 70 and max > 0
- **User scenario**: User has a node with all dimensions at 0 (never practiced) that never enters review queue
- **Impact degree**: Medium
- **Problem detail**: `review_service.py:622` filters `if avg < 70 and max_score > 0`, meaning completely unpracticed nodes never enter the review queue. But nodes that have been visited but not practiced (all scores = 0) should arguably be surfaced as review candidates.
- **Files involved**: `backend/services/review_service.py:622`
- **Min fix**: Change condition to `avg < 70` (remove `max_score > 0` check) or add a separate "unpracticed" category
- **Validation**: Create node, visit it without practicing, generate review queue, verify it appears
- **Score**: [user_leverage:3, core_capability:4, evidence:4, compounding:3, validation_ease:4, blast_radius:2]

### ISSUE-CC-006: Session completion does not prevent practice after completion
- **User scenario**: User completes session, navigates back to practice page, submits more practices to a "completed" session
- **Impact detail**: Medium
- **Problem detail**: `practice_service.py:66-79` `_validate_practice_session` rejects non-active sessions, which is correct. But the front-end does not proactively stop the user from navigating to the practice page after completion. The user sees the practice page but gets an error on submit.
- **Files involved**: `backend/services/practice_service.py:66-79`, `src/routes/practice-page.tsx:177-197`
- **Min fix**: Front-end should check session status before allowing practice submission
- **Validation**: Complete a session, try to navigate to practice, verify graceful handling
- **Score**: [user_leverage:3, core_capability:3, evidence:4, compounding:2, validation_ease:4, blast_radius:2]

### ISSUE-CC-007: Ability snapshot only records after full AI diagnosis, not rule-based fallback
- **User scenario**: AI Diagnoser fails, rule-based ability delta is applied, but no snapshot is taken
- **Impact degree**: Low
- **Problem detail**: `practice_service.py:322-341` creates ability snapshots based on `updated_ability`, which is populated when `ability_delta` is non-empty. Rule-based fallback at line 294-295 does produce a delta, so this actually works. However, the snapshot does not record the `diagnosis_fallback_used` flag, making it impossible to distinguish AI vs rule-based snapshots in analytics.
- **Files involved**: `backend/services/practice_service.py:322-341`
- **Min fix**: Add `diagnosis_fallback` boolean to the snapshot data
- **Validation**: Check snapshot records after AI failure vs success
- **Score**: [user_leverage:2, core_capability:3, evidence:3, compounding:1, validation_ease:4, blast_radius:1]

### ISSUE-CC-008: Async friction update uses fire-and-forget with no completion guarantee
- **User scenario**: User submits practice, friction data may or may not be persisted depending on timing
- **Impact degree**: High
- **Problem detail**: `practice_service.py:171-264` uses `asyncio.create_task()` for friction update with only a `done_callback` for logging. If the server restarts or the task fails, friction records, misconception nodes, and evidence nodes are silently lost. The `record_sync_event` only records the failure but no automatic retry mechanism exists.
- **Files involved**: `backend/services/practice_service.py:171-264`
- **Min fix**: Use a background task queue or at minimum persist the friction data synchronously in the main request
- **Validation**: Submit practice, check Neo4j for misconception nodes immediately after response
- **Score**: [user_leverage:4, core_capability:5, evidence:5, compounding:4, validation_ease:3, blast_radius:4]

### ISSUE-CC-009: expand_node in API directly imports sqlite_repo for sync event recording
- **User scenario**: N/A (architectural), but indicates the API layer is violating separation of concerns
- **Impact degree**: Medium
- **Problem detail**: `nodes.py:12` imports `sqlite_repo` directly into the API layer: `from backend.repositories import sqlite_repo`. This is used for `record_sync_event` calls within the 300-line inline expand_node logic at lines 166-180, 305-319, 323-337. The API layer should not directly access the repository layer.
- **Files involved**: `backend/api/nodes.py:12,166-337`
- **Min fix**: Extract expand_node logic to node_service and move all sqlite_repo calls there
- **Validation**: Code review, verify no direct repo imports in API layer
- **Score**: [user_leverage:3, core_capability:4, evidence:5, compounding:3, validation_ease:3, blast_radius:3]

### ISSUE-CC-010: Synthesizer fallback uses generic visited_node count without node names
- **User scenario**: AI Synthesizer fails, user gets "visited 3 nodes" instead of meaningful summary
- **Impact degree**: Medium
- **Problem detail**: `session_service.py:164-166` calls `synthesizer_agent.synthesize_fallback(topic_title, visited_nodes, practice_count)` which generates a generic string like "visited N nodes, completed M practices." The node names in `visited_nodes` are node_ids, not readable names, making the fallback summary unhelpful.
- **Files involved**: `backend/services/session_service.py:106,164-166`, `backend/agents/synthesizer.py`
- **Min fix**: Resolve node_ids to names from Neo4j before passing to fallback
- **Validation**: Complete session with AI disabled, verify summary shows node names
- **Score**: [user_leverage:4, core_capability:4, evidence:4, compounding:2, validation_ease:3, blast_radius:2]

### CANDIDATE-CC-001: Add misconception visualization to node detail
- **User problem**: Diagnoser identifies misconceptions but user never sees them during learning
- **User benefit**: Users can actively address identified misconceptions during study
- **Min entry point**: Show dynamic_misconceptions from node detail in the learning page
- **Files involved**: `backend/services/node_service.py:303-306`, `src/features/article-workspace/article-workspace-page.tsx`
- **Score**: [user_leverage:4, core_capability:5, evidence:4, compounding:3, validation_ease:3, blast_radius:2, total:21]

### CANDIDATE-CC-002: Implement evidence-based practice prompts
- **User problem**: Practice prompts don't incorporate user's past evidence
- **User benefit**: More personalized practice that targets actual weaknesses
- **Min entry point**: Fetch evidence nodes from Neo4j when generating practice prompts and include in Tutor context
- **Files involved**: `backend/services/practice_service.py:486-506`, `backend/agents/tutor.py`
- **Score**: [user_leverage:4, core_capability:5, evidence:4, compounding:3, validation_ease:3, blast_radius:2, total:21]

### CANDIDATE-CC-003: Add "auto-expand" after completing practice for a node
- **User problem**: After practicing a node, user must manually click expand to discover more nodes
- **User benefit**: Continuous learning flow without manual navigation
- **Min entry point**: After saving expression asset, auto-trigger expand_node for the current node
- **Files involved**: `src/routes/practice-page.tsx:655-708`
- **Score**: [user_leverage:4, core_capability:4, evidence:3, compounding:3, validation_ease:3, blast_radius:2, total:19]

### CANDIDATE-CC-004: Add friction-aware practice recommendations in session flow
- **User problem**: Session doesn't adapt to friction patterns emerging during the session
- **User benefit**: More targeted practice that responds to emerging weaknesses
- **Min entry point**: Aggregate friction_tags from all practices in current session, suggest practice types accordingly
- **Files involved**: `src/features/article-workspace/session-flow.ts`
- **Score**: [user_leverage:4, core_capability:4, evidence:3, compounding:3, validation_ease:3, blast_radius:2, total:19]

### CANDIDATE-CC-005: Implement mastery threshold customization per topic
- **User problem**: Mastery threshold is hardcoded at avg >= 70
- **User benefit**: Users studying harder topics can set higher thresholds
- **Min entry point**: Add `mastery_threshold` setting to Topic model and use in `_auto_transition_node_status`
- **Files involved**: `backend/services/review_service.py:229`, `backend/models/topic.py`
- **Score**: [user_leverage:3, core_capability:3, evidence:3, compounding:2, validation_ease:4, blast_radius:2, total:17]

### CANDIDATE-CC-006: Add practice difficulty ramping based on ability progression
- **User problem**: Practice difficulty doesn't increase as user gets better
- **User benefit**: Continuous challenge that prevents plateauing
- **Min entry point**: Use ability scores to set `difficulty` parameter in `generate_practice` calls
- **Files involved**: `backend/services/practice_service.py:497-506`
- **Score**: [user_leverage:3, core_capability:4, evidence:3, compounding:2, validation_ease:3, blast_radius:2, total:17]

### CANDIDATE-CC-007: Add learning intent impact to expand_node recommendations
- **User problem**: `fix_gap` intent should deprioritize applying/compress nodes in expansion
- **User benefit**: Expansion results better aligned with learning goals
- **Min entry point**: Weight expand_node suggestions by intent-relevant practice types
- **Files involved**: `backend/api/nodes.py:125-130`, `backend/graph/traversal.py`
- **Score**: [user_leverage:3, core_capability:4, evidence:3, compounding:2, validation_ease:3, blast_radius:2, total:17]

### CANDIDATE-CC-008: Implement cross-session learning signals
- **User problem**: Each session starts fresh without awareness of prior sessions
- **User benefit**: Smoother continuation across sessions
- **Min entry point**: Load last session's friction summary and ability gaps into new session context
- **Files involved**: `backend/services/session_service.py:18-38`
- **Score**: [user_leverage:3, core_capability:4, evidence:3, compounding:3, validation_ease:2, blast_radius:2, total:17]

### CANDIDATE-CC-009: Add concept confusion detection to practice flow
- **User problem**: User can practice contrast type but doesn't know which specific concepts they confuse
- **User benefit**: Targeted contrast practice for known confusions
- **Min entry point**: Query MISUNDERSTOOD_AS edges from Neo4j and suggest contrast practice for those nodes
- **Files involved**: `backend/services/practice_service.py:413-433`
- **Score**: [user_leverage:3, core_capability:4, evidence:4, compounding:3, validation_ease:3, blast_radius:2, total:19]

### CANDIDATE-CC-010: Implement teach_beginner practice with audience adaptation
- **User problem**: teach_beginner practice type doesn't adapt to different audience levels
- **User benefit**: More realistic expression training
- **Min entry point**: Add audience parameter (child/peer/expert) to teach_beginner prompts
- **Files involved**: `backend/agents/tutor.py:24,85-146`
- **Score**: [user_leverage:2, core_capability:3, evidence:3, compounding:2, validation_ease:3, blast_radius:1, total:14]

---

## Lens 3: Reliability (RL) — Stability and Recoverability

### ISSUE-RL-001: expand_node has 300+ lines of inline multi-database write logic without transaction
- **User scenario**: Neo4j write succeeds but LanceDB write fails midway, leaving inconsistent state
- **Impact degree**: High
- **Problem detail**: `nodes.py:136-337` writes to SQLite (session_nodes tracking), then Neo4j (batch node+edge creation), then LanceDB (vectors) in sequence without a single transaction. If Neo4j succeeds but LanceDB fails, the nodes exist in the graph but have no vector embeddings, and the system records a `record_sync_event` but never retries.
- **Files involved**: `backend/api/nodes.py:136-337`
- **Min fix**: Wrap the entire write sequence in a try/catch with compensating rollback actions for each stage
- **Validation**: Simulate LanceDB failure during expand, verify Neo4j nodes are cleaned up or flagged
- **Score**: [user_leverage:5, core_capability:5, evidence:5, compounding:5, validation_ease:2, blast_radius:5]

### ISSUE-RL-002: SQLite increment_topic_stats has no guard against negative learned_nodes
- **User scenario**: Node status toggles between mastered and practiced rapidly, learned_nodes goes negative
- **Impact degree**: Medium
- **Problem detail**: `review_service.py:268-270` calls `increment_topic_stats(db, topic_id, "learned_nodes", delta=-1)` with a guard `if (topic.get("learned_nodes") or 0) > 0`. But this reads the value at session start, not at the time of decrement. A concurrent session could have already decremented it. Additionally, `node_service.py:359` increments without the same guard, creating a TOCTOU race.
- **Files involved**: `backend/services/review_service.py:268-270`, `backend/services/node_service.py:348-361`
- **Min fix**: Use `MAX(0, ...)` SQL expression in the update: `SET learned_nodes = MAX(0, learned_nodes + ?)`
- **Validation**: Rapidly toggle node status between mastered/practiced, verify learned_nodes never goes below 0
- **Score**: [user_leverage:3, core_capability:4, evidence:4, compounding:3, validation_ease:4, blast_radius:3]

### ISSUE-RL-003: record_sync_event has no expiry or retry mechanism
- **User scenario**: Sync events accumulate indefinitely, never retried, filling up the sync_events table
- **Impact degree**: Medium
- **Problem detail**: `record_sync_event` inserts rows into the `sync_events` table with status "pending" but there is no background worker to process them. Over time, this table grows unboundedly with failed operations that are never retried.
- **Files involved**: `backend/repositories/sqlite_repo.py` (record_sync_event function)
- **Min fix**: Add a TTL-based cleanup that marks old pending events as "expired" after 24 hours
- **Validation**: Create multiple sync events, wait, verify they are marked expired
- **Score**: [user_leverage:3, core_capability:4, evidence:4, compounding:3, validation_ease:4, blast_radius:3]

### ISSUE-RL-004: AIClient global _ai_call_count and _ai_start_time are process-wide singletons
- **User scenario**: Multiple concurrent users share the same AI call counter, making logs confusing
- **Impact degree**: Low
- **Problem detail**: `base.py:18-19` uses module-level globals `_ai_call_count = 0` and `_ai_start_time = time.time()`. In a multi-user scenario (even single-user with concurrent requests), the counter and elapsed time are shared and meaningless for per-request tracing.
- **Files involved**: `backend/agents/base.py:18-19`
- **Min fix**: Make these per-instance or per-request, or use structured logging with request IDs
- **Validation**: Fire 2 concurrent AI requests, verify logs don't mix counters
- **Score**: [user_leverage:2, core_capability:3, evidence:5, compounding:2, validation_ease:4, blast_radius:2]

### ISSUE-RL-005: Neo4j UNWIND query uses string interpolation for relationship type
- **User scenario**: Malicious or corrupted edge type could inject Cypher
- **Impact degree**: Medium
- **Problem detail**: `nodes.py:265-270` uses f-string for relationship type: `f"""UNWIND $items AS item MATCH ... MERGE (src)-[r:\`{rel_type}\`]->(tgt) SET ..."""`. While `rel_type` comes from AI output filtered by `validate_and_filter_edges`, the edge validation in `graph/validator.py` uses a whitelist, so this is partially mitigated. But the f-string pattern itself is risky.
- **Files involved**: `backend/api/nodes.py:265-270`
- **Min fix**: Pre-validate all rel_types against the whitelist before the UNWIND query, not just filter
- **Validation**: Inject a rel_type with Cypher payload, verify it's rejected
- **Score**: [user_leverage:3, core_capability:3, evidence:4, compounding:3, validation_ease:3, blast_radius:4]

### ISSUE-RL-006: practice_service.py opens a separate SQLite connection for async friction update
- **User scenario**: Async friction update opens a second connection, potentially causing WAL lock contention
- **Impact degree**: Low
- **Problem detail**: `practice_service.py:177-178` creates a new `aiosqlite.connect()` in the async task. SQLite in WAL mode handles concurrent reads but only one writer at a time. If the main request is still writing (e.g., creating the practice attempt), the async task's write may timeout.
- **Files involved**: `backend/services/practice_service.py:171-264`
- **Min fix**: Queue friction writes and process them sequentially after the main response completes
- **Validation**: Submit practice while friction data is being written, verify no timeout
- **Score**: [user_leverage:2, core_capability:3, evidence:4, compounding:2, validation_ease:3, blast_radius:3]

### ISSUE-RL-007: Session claim_completion uses UPDATE but not within a transaction
- **User scenario**: Two concurrent complete_session calls both succeed, creating duplicate review items
- **Impact degree**: Medium
- **Problem detail**: `session_service.py:100` calls `claim_session_completion(db, session_id)` which presumably does an UPDATE. But the subsequent operations (synthesis, review generation) are not atomic. Two concurrent requests could both claim the session and generate duplicate review items.
- **Files involved**: `backend/services/session_service.py:100-104`, `backend/repositories/sqlite_repo.py` (claim_session_completion)
- **Min fix**: Use SQLite's BEGIN IMMEDIATE to serialize session completion
- **Validation**: Fire two concurrent complete_session requests, verify no duplicates
- **Score**: [user_leverage:3, core_capability:4, evidence:4, compounding:3, validation_ease:3, blast_radius:3]

### ISSUE-RL-008: No input sanitization on user_answer before Neo4j evidence write
- **User scenario**: User submits practice with very long answer (50000 chars), stored truncated in Neo4j
- **Impact degree**: Low
- **Problem detail**: `practice_service.py:238` truncates user_answer to 500 chars for evidence node: `"text": data.user_answer[:500]`. But the truncation is silent, and the full answer is already stored in SQLite. The 500 char limit is hardcoded with no rationale.
- **Files involved**: `backend/services/practice_service.py:238`
- **Min fix**: Document the truncation limit or make it configurable
- **Validation**: Submit 1000 char answer, verify evidence node has 500 char text
- **Score**: [user_leverage:2, core_capability:2, evidence:3, compounding:1, validation_ease:5, blast_radius:1]

### ISSUE-RL-009: Frontend error handling uses toast for all errors, no retry queue
- **User scenario**: Network transient error causes practice submission to fail, user must manually retry
- **Impact degree**: Medium
- **Problem detail**: Throughout the frontend (`practice-page.tsx:52,214`, `home-page.tsx:53,391`), errors are shown as toasts with no automatic retry. For transient errors (network blips), the user loses their answer draft if they navigate away.
- **Files involved**: `src/routes/practice-page.tsx:52,193-196`, `src/routes/home-page.tsx:52-53`
- **Min fix**: Add automatic retry with exponential backoff for mutation errors, or at minimum a "Retry" button in the error toast
- **Validation**: Disconnect network, submit practice, reconnect, verify auto-retry
- **Score**: [user_leverage:4, core_capability:2, evidence:4, compounding:3, validation_ease:4, blast_radius:2]

### ISSUE-RL-010: No rate limiting on expand_node or practice submit
- **User scenario**: User rapidly clicks expand or submit, firing multiple expensive AI calls
- **Impact degree**: Medium
- **Problem detail**: The frontend disables buttons while mutations are pending (`getPromptMutation.isPending`), but there is no server-side rate limiting. A user with a custom client could fire unlimited AI requests.
- **Files involved**: `backend/api/nodes.py:52-361`, `backend/api/practice.py`
- **Min fix**: Add per-topic rate limiting middleware for AI-heavy endpoints
- **Validation**: Fire 10 rapid expand requests, verify rate limiting kicks in
- **Score**: [user_leverage:3, core_capability:3, evidence:4, compounding:3, validation_ease:3, blast_radius:3]

### CANDIDATE-RL-001: Add sync event retry worker
- **User problem**: Failed sync events are never retried, leaving databases inconsistent
- **User benefit**: Automatic recovery from transient failures
- **Min entry point**: Add a background task that processes pending sync_events every 5 minutes
- **Files involved**: `backend/repositories/sqlite_repo.py`, new `backend/services/sync_service.py`
- **Score**: [user_leverage:5, core_capability:5, evidence:5, compounding:4, validation_ease:3, blast_radius:4, total:26]

### CANDIDATE-RL-002: Add database health check with self-healing
- **User problem**: Neo4j or LanceDB goes down, system degrades silently
- **User benefit**: Proactive detection and recovery
- **Min entry point**: Periodically check all three databases and attempt reconnection
- **Files involved**: `backend/api/system.py`
- **Score**: [user_leverage:4, core_capability:4, evidence:4, compounding:3, validation_ease:3, blast_radius:3, total:21]

### CANDIDATE-RL-003: Implement idempotency keys for all write operations
- **User problem**: Retrying a failed request creates duplicates
- **User benefit**: Safe retries without side effects
- **Min entry point**: Add idempotency_key to POST endpoints, check before processing
- **Files involved**: `backend/api/nodes.py`, `backend/api/practice.py`, `backend/api/sessions.py`
- **Score**: [user_leverage:4, core_capability:4, evidence:4, compounding:4, validation_ease:3, blast_radius:3, total:22]

### CANDIDATE-RL-004: Add write-ahead log for expand_node operations
- **User problem**: expand_node partial failure leaves inconsistent state across 3 databases
- **User benefit**: Guaranteed consistency or clean rollback
- **Min entry point**: Create a local WAL table, write intent before executing multi-DB operations
- **Files involved**: `backend/api/nodes.py:136-337`
- **Score**: [user_leverage:5, core_capability:5, evidence:5, compounding:4, validation_ease:2, blast_radius:4, total:25]

### CANDIDATE-RL-005: Add SQLite WAL checkpoint management
- **User problem**: Long-running app accumulates WAL file, slowing reads
- **User benefit**: Consistent read performance
- **Min entry point**: Periodically run PRAGMA wal_checkpoint
- **Files involved**: `backend/main.py`
- **Score**: [user_leverage:3, core_capability:3, evidence:4, compounding:3, validation_ease:4, blast_radius:2, total:19]

### CANDIDATE-RL-006: Add request-scoped logging correlation ID
- **User problem**: Logs from concurrent requests are interleaved and hard to trace
- **User benefit**: Debugging concurrent issues becomes feasible
- **Min entry point**: Add middleware that generates a request ID and adds it to all log statements
- **Files involved**: `backend/main.py`, `backend/agents/base.py`
- **Score**: [user_leverage:3, core_capability:3, evidence:4, compounding:3, validation_ease:4, blast_radius:2, total:19]

### CANDIDATE-RL-007: Implement graceful shutdown for in-progress AI calls
- **User problem**: User closes app during AI call, Neo4j may have partial writes
- **User benefit**: Clean shutdown without data corruption
- **Min entry point**: Add shutdown handler that waits for in-progress AI tasks to complete
- **Files involved**: `backend/main.py`
- **Score**: [user_leverage:3, core_capability:3, evidence:3, compounding:3, validation_ease:3, blast_radius:3, total:18]

### CANDIDATE-RL-008: Add database size monitoring and cleanup
- **User problem**: SQLite and LanceDB grow unboundedly over time
- **User benefit**: Prevent disk space exhaustion
- **Min entry point**: Add startup check for database sizes, warn if above threshold
- **Files involved**: `backend/api/system.py`
- **Score**: [user_leverage:3, core_capability:3, evidence:3, compounding:2, validation_ease:4, blast_radius:2, total:17]

### CANDIDATE-RL-009: Implement optimistic locking for ability record updates
- **User problem**: Two concurrent practice submissions on the same node overwrite each other's ability updates
- **User benefit**: No lost ability updates from race conditions
- **Min entry point**: Add version column to ability_records, check on update
- **Files involved**: `backend/repositories/sqlite_repo.py`, `backend/services/practice_service.py:306-319`
- **Score**: [user_leverage:4, core_capability:4, evidence:4, compounding:3, validation_ease:3, blast_radius:3, total:21]

### CANDIDATE-RL-010: Add frontend offline detection and queueing
- **User problem**: User loses unsaved work when backend becomes temporarily unavailable
- **User benefit**: Automatic retry when connectivity returns
- **Min entry point**: Use navigator.onLine to detect offline state, queue mutations
- **Files involved**: `src/hooks/use-mutations.ts`
- **Score**: [user_leverage:3, core_capability:2, evidence:3, compounding:3, validation_ease:3, blast_radius:2, total:16]

---

## Lens 4: Learning Quality (LQ) — Feedback Quality

### ISSUE-LQ-001: Review evaluation fallback uses answer length as quality proxy
- **User scenario**: User writes 200 chars of nonsense, gets "good" review result
- **Impact degree**: High
- **Problem detail**: `review_service.py:457-459` uses `if len(user_answer) > 100: "good"` as fallback when AI evaluation fails. This means any long-enough text, regardless of quality, gets a "good" rating, which incorrectly inflates ability scores and skips relearning.
- **Files involved**: `backend/services/review_service.py:454-469`
- **Min fix**: Use keyword matching against the node name/summary as a better heuristic, or return "medium" for all fallbacks
- **Validation**: Submit 150 chars of random text for review, verify not rated "good"
- **Score**: [user_leverage:5, core_capability:5, evidence:5, compounding:4, validation_ease:5, blast_radius:4]

### ISSUE-LQ-002: Practice feedback does not include per-dimension specific guidance
- **User scenario**: User gets "clarity: weak" but no specific suggestion on how to improve clarity
- **Impact degree**: Medium
- **Problem detail**: `tutor.py:47-65` _FEEDBACK_SCHEMA only has global `correctness`, `clarity`, `naturalness` scores plus generic `issues` and `suggestions` arrays. There is no per-dimension specific feedback (e.g., "to improve clarity, try using more concrete examples").
- **Files involved**: `backend/agents/tutor.py:47-65`
- **Min fix**: Add `dimension_feedback` object to the schema with specific guidance per weak dimension
- **Validation**: Submit practice with weak clarity, verify specific clarity improvement suggestion appears
- **Score**: [user_leverage:4, core_capability:5, evidence:4, compounding:3, validation_ease:3, blast_radius:3]

### ISSUE-LQ-003: Expression skeleton is not consistently generated
- **User scenario**: User saves expression asset without a skeleton, making it less useful for review
- **Impact degree**: Medium
- **Problem detail**: `tutor.py:62` includes `expression_skeleton` in the schema but it's not in the `required` fields (line 64). When AI omits it, `practice_service.py:607` shows an empty skeleton box. The static fallback at line 235 also returns empty skeleton.
- **Files involved**: `backend/agents/tutor.py:62-64`, `backend/services/practice_service.py:607`
- **Min fix**: Generate a skeleton from the recommended_answer if AI doesn't provide one
- **Validation**: Simulate AI returning no skeleton, verify a derived skeleton appears
- **Score**: [user_leverage:3, core_capability:4, evidence:4, compounding:3, validation_ease:4, blast_radius:2]

### ISSUE-LQ-004: Practice prompt cache doesn't consider learning intent changes
- **User scenario**: User changes topic learning intent from "build_system" to "fix_gap", but cached prompts from previous intent are served
- **Impact degree**: Medium
- **Problem detail**: `practice_service.py:447-457` caches prompts keyed by `(topic_id, node_id, practice_type)`. When the user changes the topic's learning intent, old cached prompts may not match the new intent's guidance (e.g., fix_gap should prioritize prerequisite practice but cached prompt doesn't).
- **Files involved**: `backend/services/practice_service.py:447-457`
- **Min fix**: Include learning_intent in the cache key, or invalidate cache on intent change
- **Validation**: Change learning intent, generate practice prompt, verify it reflects new intent
- **Score**: [user_leverage:3, core_capability:4, evidence:4, compounding:3, validation_ease:4, blast_radius:3]

### ISSUE-LQ-005: No minimum quality bar for AI-generated practice prompts
- **User scenario**: AI generates a practice prompt that is too vague or identical to a previous one
- **Impact degree**: Low
- **Problem detail**: `practice_service.py:497-522` uses the AI result directly without checking for quality. There's no check that the prompt is sufficiently different from the static fallback, or that it's specific to the node (not generic).
- **Files involved**: `backend/services/practice_service.py:510-522`
- **Min fix**: Compare AI prompt against static fallback using cosine similarity, regenerate if too similar
- **Validation**: Monitor practice prompt quality across multiple generations
- **Score**: [user_leverage:3, core_capability:3, evidence:3, compounding:2, validation_ease:3, blast_radius:2]

### ISSUE-LQ-006: Friction tag recommendations in practice page use hardcoded mapping
- **User scenario**: User has "weak_application" friction but recommended practice is "apply" which is correct, but the mapping is incomplete
- **Impact degree**: Low
- **Problem detail**: `practice-page.tsx:25-33` `FRICTION_LABELS` only maps 7 friction types. If Diagnoser returns a new friction type not in this mapping, it's displayed as raw string. Also, the mapping doesn't consider multiple simultaneous frictions.
- **Files involved**: `src/routes/practice-page.tsx:25-33`
- **Min fix**: Fetch friction tag metadata from the backend instead of hardcoding, and support compound recommendations
- **Validation**: Return a novel friction type, verify it's displayed meaningfully
- **Score**: [user_leverage:2, core_capability:3, evidence:3, compounding:2, validation_ease:4, blast_radius:2]

### ISSUE-LQ-007: Ability snapshot doesn't capture friction tags at time of snapshot
- **User scenario**: User looks at ability timeline but can't correlate ability changes with specific frictions
- **Impact degree**: Low
- **Problem detail**: `practice_service.py:322-341` captures `practice_type` and `feedback_correctness` in snapshots but not the friction_tags that were identified during that practice. This makes it impossible to understand why ability changed.
- **Files involved**: `backend/services/practice_service.py:325-341`
- **Min fix**: Add `friction_tags` field to ability snapshot
- **Validation**: Complete practice, check snapshot record for friction tags
- **Score**: [user_leverage:3, core_capability:3, evidence:4, compounding:3, validation_ease:4, blast_radius:2]

### ISSUE-LQ-008: Review type suggestion ignores practice history
- **User scenario**: User has done 5 "recall" reviews but keep getting "recall" suggested
- **Impact degree**: Low
- **Problem detail**: `review_service.py:35-48` `_suggest_review_type` looks at ability scores to find the weakest dimension but doesn't consider which review types have been done most frequently. A user who has done 5 "recall" reviews but still has weak recall would benefit more from a "contrast" or "explain" review for variety.
- **Files involved**: `backend/services/review_service.py:35-48`
- **Min fix**: Add a recency penalty for recently reviewed types
- **Validation**: Complete 5 recall reviews, verify next review suggests a different type
- **Score**: [user_leverage:2, core_capability:3, evidence:4, compounding:2, validation_ease:4, blast_radius:2]

### ISSUE-LQ-009: Practice difficulty "adaptive" mode only considers average ability
- **User scenario**: User has high understand (80) but low contrast (20), but adaptive difficulty shows "normal"
- **Impact degree**: Low
- **Problem detail**: `tutor.py:102-110` adaptive difficulty only checks average ability (`avg_ability > 70`). A user with imbalanced abilities (high in some, low in others) gets "normal difficulty" because the average is medium.
- **Files involved**: `backend/agents/tutor.py:102-110`
- **Min fix**: Consider the weakest dimension for difficulty adjustment, not the average
- **Validation**: Create imbalanced ability record, generate adaptive practice, verify difficulty
- **Score**: [user_leverage:2, core_capability:3, evidence:4, compounding:2, validation_ease:4, blast_radius:2]

### ISSUE-LQ-010: Misconception hints from Diagnoser are not shown to user during practice
- **User scenario**: Diagnoser identifies a misconception but user never sees it until next review
- **Impact degree**: Medium
- **Problem detail**: `practice_service.py:121-145` captures `misconception_hints` from Diagnoser but these are only persisted to Neo4j asynchronously (line 196-227). They are never returned to the user in the practice feedback. The user misses an opportunity to address the misconception immediately.
- **Files involved**: `backend/services/practice_service.py:121-145,357-365`
- **Min fix**: Include misconception_hints in the PracticeResult response
- **Validation**: Trigger a misconception diagnosis, verify it appears in practice feedback
- **Score**: [user_leverage:4, core_capability:4, evidence:5, compounding:3, validation_ease:4, blast_radius:3]

### CANDIDATE-LQ-001: Add practice prompt quality scoring
- **User problem**: Can't tell if AI-generated prompts are good enough
- **User benefit**: System self-monitors prompt quality and regenerates bad ones
- **Min entry point**: Score prompts on specificity, length, and topic relevance
- **Files involved**: `backend/services/practice_service.py:510-522`
- **Score**: [user_leverage:3, core_capability:4, evidence:3, compounding:2, validation_ease:3, blast_radius:2, total:16]

### CANDIDATE-LQ-002: Implement spaced repetition interval personalization
- **User problem**: Review intervals are fixed regardless of individual performance
- **User benefit**: Users who consistently perform well review less often
- **Min entry point**: Track per-node success rate and adjust intervals accordingly
- **Files involved**: `backend/services/review_service.py:52-54,146-156`
- **Score**: [user_leverage:4, core_capability:5, evidence:4, compounding:3, validation_ease:3, blast_radius:2, total:21]

### CANDIDATE-LQ-003: Add practice progress visualization per node
- **User problem**: User can't see which practice types they've completed for each node
- **User benefit**: Clear visualization of practice progress motivates completion
- **Min entry point**: Add a progress indicator showing completed practice types on node cards
- **Files involved**: `src/components/shared/ability-radar.tsx`, `src/routes/practice-page.tsx`
- **Score**: [user_leverage:3, core_capability:3, evidence:4, compounding:2, validation_ease:4, blast_radius:2, total:18]

### CANDIDATE-LQ-004: Add quality feedback loop — rate AI feedback quality
- **User problem**: Bad AI feedback is never corrected
- **User benefit**: System improves over time based on user corrections
- **Min entry point**: Add thumbs up/down on feedback, log for prompt improvement
- **Files involved**: `src/routes/practice-page.tsx:537-647`
- **Score**: [user_leverage:3, core_capability:4, evidence:3, compounding:3, validation_ease:3, blast_radius:2, total:18]

### CANDIDATE-LQ-005: Implement learning path deviation detection
- **User problem**: User's practice pattern doesn't follow the recommended sequence
- **User benefit**: Gentle nudges to follow optimal learning path
- **Min entry point**: Compare practice type order against PRACTICE_SEQUENCE, suggest next in sequence
- **Files involved**: `backend/services/practice_service.py:410-433`
- **Score**: [user_leverage:3, core_capability:4, evidence:3, compounding:2, validation_ease:3, blast_radius:2, total:17]

### CANDIDATE-LQ-006: Add expressiveness scoring beyond correctness/clarity/naturalness
- **User problem**: Current scoring doesn't capture nuance, specificity, or audience awareness
- **User benefit**: More accurate assessment of expression quality
- **Min entry point**: Add dimensions like specificity, conciseness, audience_match to feedback schema
- **Files involved**: `backend/agents/tutor.py:47-65`
- **Score**: [user_leverage:3, core_capability:5, evidence:4, compounding:3, validation_ease:2, blast_radius:2, total:19]

### CANDIDATE-LQ-007: Implement practice warm-up for new nodes
- **User problem**: First practice on a new node is intimidating with no context
- **User benefit**: Gradual difficulty ramp for new material
- **Min entry point**: When no practice history exists for a node, start with easier "define" type
- **Files involved**: `backend/services/practice_service.py:413-433`
- **Score**: [user_leverage:2, core_capability:3, evidence:3, compounding:2, validation_ease:4, blast_radius:1, total:15]

### CANDIDATE-LQ-008: Add time-boxed practice mode
- **User problem**: Users can spend too long on a single practice session
- **User benefit**: Focused, time-limited practice sessions
- **Min entry point**: Add a timer component that shows elapsed time and alerts at configurable intervals
- **Files involved**: `src/routes/practice-page.tsx`
- **Score**: [user_leverage:2, core_capability:2, evidence:3, compounding:1, validation_ease:4, blast_radius:1, total:13]

### CANDIDATE-LQ-009: Implement knowledge retention curve visualization
- **User problem**: User can't see how well they're retaining knowledge over time
- **User benefit**: Motivating visualization of learning progress
- **Min entry point**: Use ability snapshots to plot retention curves per node
- **Files involved**: `src/routes/stats-page.tsx:484-532`
- **Score**: [user_leverage:3, core_capability:4, evidence:4, compounding:3, validation_ease:3, blast_radius:2, total:19]

### CANDIDATE-LQ-010: Add comparative feedback — show user's answer vs recommended side by side
- **User problem**: User must scroll to compare their answer with the recommended one
- **User benefit**: Immediate visual comparison aids learning
- **Min entry point**: Render user answer and recommended answer in a side-by-side layout
- **Files involved**: `src/routes/practice-page.tsx:592-607`
- **Score**: [user_leverage:3, core_capability:3, evidence:4, compounding:2, validation_ease:4, blast_radius:1, total:17]

---

## Lens 5: Iteration Leverage (IL) — Making Future Changes Safer

### ISSUE-IL-001: sqlite_repo.py is 1715 lines with 8+ domain responsibilities
- **User scenario**: Developer modifies session-related code and accidentally breaks review-related code
- **Impact degree**: High
- **Problem detail**: `sqlite_repo.py` at 1715 lines contains CRUD for topics, sessions, session_nodes, ability_records, ability_snapshots, practice_attempts, expression_assets, friction_records, review_items, settings, articles, concept_candidates, sync_events, and deferred_nodes. Any change risks unintended side effects on unrelated domains.
- **Files involved**: `backend/repositories/sqlite_repo.py`
- **Min fix**: Extract into domain-specific repos: session_repo.py, ability_repo.py, practice_repo.py, review_repo.py (partially done — see existing files in repositories/)
- **Validation**: Count functions per file after split, verify each has single responsibility
- **Score**: [user_leverage:5, core_capability:3, evidence:5, compounding:5, validation_ease:3, blast_radius:4]

### ISSUE-IL-002: No API response type validation
- **User scenario**: Backend returns unexpected field type, frontend crashes silently
- **Impact degree**: Medium
- **Problem detail**: API responses use `success_response(data=...)` which wraps data in `{success, data, meta}` but there's no runtime validation that the response shape matches what the frontend expects. If a field name changes or type changes (e.g., `int` to `str`), the frontend has no guard.
- **Files involved**: `backend/core/response.py`, `src/hooks/use-queries.ts`
- **Min fix**: Add a response schema per endpoint and validate before sending
- **Validation**: Change a field type in backend, verify frontend gets a meaningful error
- **Score**: [user_leverage:4, core_capability:3, evidence:4, compounding:4, validation_ease:3, blast_radius:3]

### ISSUE-IL-003: Frontend test coverage does not cover API error handling
- **User scenario**: API returns unexpected error code, frontend shows generic error
- **Impact degree**: Medium
- **Problem detail**: Of 14 frontend test files, none test what happens when the API returns error responses with different error_codes. The tests mostly verify happy-path rendering.
- **Files involved**: `src/__tests__/` (all test files)
- **Min fix**: Add tests that mock error responses and verify ErrorState or toast rendering
- **Validation**: Add 5 error-handling tests, verify they pass
- **Score**: [user_leverage:4, core_capability:3, evidence:5, compounding:3, validation_ease:4, blast_radius:2]

### ISSUE-IL-004: No integration test for the full learn → practice → summary → review flow
- **User scenario**: A change to practice_service breaks the summary generation but no test catches it
- **Impact degree**: High
- **Problem detail**: The backend has 55 unit tests in `test_core.py` and 5 test files total. But there is no end-to-end test that creates a topic, starts a session, expands nodes, practices, completes the session, and generates reviews. This is the core user journey.
- **Files involved**: `backend/tests/`
- **Min fix**: Add a test in `test_core.py` that exercises the full flow with mocked AI
- **Validation**: Add test, verify it passes, break any step, verify test catches it
- **Score**: [user_leverage:5, core_capability:5, evidence:5, compounding:5, validation_ease:3, blast_radius:4]

### ISSUE-IL-005: Frontend types are manually aligned with backend, no code generation
- **User scenario**: Backend adds a new field to the API, frontend types are out of date
- **Impact degree**: Medium
- **Problem detail**: Per CLAUDE.md, frontend types use snake_case aligned with backend Pydantic models, but this alignment is manual. If a backend model adds a field, the frontend types silently become incomplete. The `types` directory has no automated sync mechanism.
- **Files involved**: `src/types/`, `backend/models/`
- **Min fix**: Generate frontend types from backend Pydantic models using a script (e.g., pydantic-to-ts)
- **Validation**: Add a field to a Pydantic model, run generation, verify types update
- **Score**: [user_leverage:4, core_capability:3, evidence:5, compounding:4, validation_ease:3, blast_radius:3]

### ISSUE-IL-006: No structured logging format — only plain text messages
- **User scenario**: Debugging production issues requires manual log parsing
- **Impact degree**: Low
- **Problem detail**: All backend logging uses `logger.warning(f"...")` with plain string messages. There's no structured logging (JSON format, request IDs, correlation IDs). This makes log analysis and monitoring harder.
- **Files involved**: All backend files using `logger`
- **Min fix**: Switch to structured logging with python-json-logger or similar
- **Validation**: Check log output format, verify JSON structure
- **Score**: [user_leverage:3, core_capability:2, evidence:5, compounding:3, validation_ease:4, blast_radius:3]

### ISSUE-IL-007: article-workspace-page.tsx is 1732 lines — too large for a single component
- **User scenario**: Developer needs to fix a sidebar issue but must understand the 1732-line page
- **Impact degree**: Medium
- **Problem detail**: `article-workspace-page.tsx` is a single component at 1732 lines that handles article rendering, concept navigation, session management, search, and workspace layout. This makes it difficult to understand, test, and modify any single concern.
- **Files involved**: `src/features/article-workspace/article-workspace-page.tsx`
- **Min fix**: Extract concerns into custom hooks: `useArticleNavigation`, `useSearch`, `useConceptDrawer`
- **Validation**: Component should be < 300 lines after extraction
- **Score**: [user_leverage:4, core_capability:2, evidence:5, compounding:4, validation_ease:3, blast_radius:3]

### ISSUE-IL-008: No lint or type-check configuration verification in CI
- **User scenario**: Developer pushes code with type errors, build breaks silently
- **Impact degree**: Medium
- **Problem detail**: The project has no CI configuration visible in the codebase. There's no evidence of automated type-checking (`tsc --noEmit`) or linting being enforced on push.
- **Files involved**: Project root (missing CI config)
- **Min fix**: Add a pre-push hook or CI pipeline that runs tsc and eslint
- **Validation**: Push code with a type error, verify it's rejected
- **Score**: [user_leverage:4, core_capability:2, evidence:5, compounding:4, validation_ease:4, blast_radius:3]

### ISSUE-IL-009: Test conftest.py may have fixture that doesn't match production schema
- **User scenario**: Test passes but production DB schema has diverged
- **Impact degree**: Low
- **Problem detail**: `backend/tests/conftest.py` creates test fixtures, but there's no mechanism to ensure the test schema matches production. If `sqlite_repo.py` SQL_INIT_TABLES changes, tests may pass against stale schema.
- **Files involved**: `backend/tests/conftest.py`, `backend/repositories/sqlite_repo.py:59-200`
- **Min fix**: Import SQL_INIT_TABLES in conftest to ensure test and production schema match
- **Validation**: Modify a table definition, verify test fails
- **Score**: [user_leverage:3, core_capability:3, evidence:4, compounding:3, validation_ease:4, blast_radius:2]

### ISSUE-IL-010: lib/utils.ts is only 6 lines, essentially unused
- **User scenario**: Developer looks for utility functions in utils.ts, finds nothing useful
- **Impact degree**: Low
- **Problem detail**: `src/lib/utils.ts` is only 6 lines and likely contains only the `cn` (classname merge) helper. Meanwhile, `src/lib/practice-constants.ts`, `src/lib/navigation-context.ts`, `src/lib/summary-display.ts`, and `src/lib/article-workspace.ts` contain significant logic that should arguably be in `utils.ts` or properly named modules.
- **Files involved**: `src/lib/utils.ts`
- **Min fix**: Either expand utils.ts with shared utilities or remove it if cn is the only export
- **Validation**: Code review
- **Score**: [user_leverage:1, core_capability:1, evidence:4, compounding:1, validation_ease:5, blast_radius:1]

### CANDIDATE-IL-001: Add API contract tests with snapshot testing
- **User problem**: API response changes are not caught by tests
- **User benefit**: Catch breaking changes automatically
- **Min entry point**: Use snapshot testing for API responses
- **Files involved**: `backend/tests/test_api.py`
- **Score**: [user_leverage:4, core_capability:3, evidence:4, compounding:4, validation_ease:4, blast_radius:3, total:22]

### CANDIDATE-IL-002: Add E2E test with Playwright for core flow
- **User problem**: No automated verification of the complete user journey
- **User benefit**: Catch regression issues before users encounter them
- **Min entry point**: Set up Playwright, write test for create → learn → practice → summary → review
- **Files involved**: New `e2e/` directory
- **Score**: [user_leverage:5, core_capability:4, evidence:5, compounding:5, validation_ease:2, blast_radius:4, total:25]

### CANDIDATE-IL-003: Generate frontend types from OpenAPI spec
- **User problem**: Manual type alignment between frontend and backend
- **User benefit**: Automatic type synchronization
- **Min entry point**: Add /docs endpoint, use openapi-typescript to generate types
- **Files involved**: `backend/main.py`, `src/types/`
- **Score**: [user_leverage:4, core_capability:3, evidence:4, compounding:4, validation_ease:3, blast_radius:3, total:21]

### CANDIDATE-IL-004: Add mutation testing for critical business logic
- **User problem**: Unit tests may not catch edge cases in ability delta calculation
- **User benefit**: Higher confidence in core algorithms
- **Min entry point**: Run mutation testing on ability.py and review_service.py
- **Files involved**: `backend/models/ability.py`, `backend/services/review_service.py`
- **Score**: [user_leverage:3, core_capability:4, evidence:4, compounding:3, validation_ease:2, blast_radius:2, total:18]

### CANDIDATE-IL-005: Extract article-workspace-page.tsx into smaller hooks and components
- **User problem**: 1732-line component is hard to maintain
- **User benefit**: Easier to modify individual features
- **Min entry point**: Extract useArticleNavigation, useConceptDrawer, useCommandPalette hooks
- **Files involved**: `src/features/article-workspace/article-workspace-page.tsx`
- **Score**: [user_leverage:4, core_capability:2, evidence:5, compounding:4, validation_ease:3, blast_radius:3, total:21]

### CANDIDATE-IL-006: Add pre-commit hooks for code quality
- **User problem**: Code with lint errors or type errors enters the codebase
- **User benefit**: Automatic quality gates before commit
- **Min entry point**: Add husky + lint-staged with tsc and eslint
- **Files involved**: Project root
- **Score**: [user_leverage:3, core_capability:2, evidence:4, compounding:3, validation_ease:5, blast_radius:2, total:19]

### CANDIDATE-IL-007: Add API versioning and migration framework
- **User problem**: Changing API responses breaks existing frontends
- **User benefit**: Safe API evolution
- **Min entry point**: Add /api/v2/ prefix, implement response versioning
- **Files involved**: `backend/api/`, `src/hooks/use-queries.ts`
- **Score**: [user_leverage:3, core_capability:3, evidence:3, compounding:4, validation_ease:3, blast_radius:3, total:19]

### CANDIDATE-IL-008: Extract sqlite_repo into domain-specific repository files
- **User problem**: 1715-line file is hard to navigate
- **User benefit**: Easier to find and modify domain-specific code
- **Min entry point**: Move session functions to session_repo.py, review functions to review_repo.py, etc.
- **Files involved**: `backend/repositories/sqlite_repo.py`
- **Score**: [user_leverage:5, core_capability:3, evidence:5, compounding:4, validation_ease:3, blast_radius:3, total:23]

### CANDIDATE-IL-009: Add property-based testing for ability clamping
- **User problem**: Edge cases in ability update rules (0-100 clamp, -5 to +10 delta) may not be covered
- **User benefit**: Higher confidence in core scoring algorithm
- **Min entry point**: Use hypothesis to generate random ability values and verify clamping
- **Files involved**: `backend/models/ability.py`
- **Score**: [user_leverage:3, core_capability:4, evidence:4, compounding:2, validation_ease:3, blast_radius:2, total:18]

### CANDIDATE-IL-010: Add structured error codes documentation
- **User problem**: Error codes are scattered across API files with no centralized documentation
- **User benefit**: Frontend developers can look up error handling per code
- **Min entry point**: Create docs/error-codes.md listing all codes and expected frontend behavior
- **Files involved**: `backend/api/*.py`
- **Score**: [user_leverage:3, core_capability:2, evidence:3, compounding:3, validation_ease:4, blast_radius:2, total:17]

---

## Lens 6: Architecture Drag (AD) — Obstacles to Value Delivery

### ISSUE-AD-001: expand_node in API layer contains 300 lines of business logic
- **User scenario**: N/A — developer experience issue that slows delivery
- **Impact degree**: High
- **Problem detail**: `nodes.py:53-361` expand_node endpoint contains 308 lines of inline business logic including AI calling, validation, multi-database writes, and error compensation. This violates the API → Service → Repository architecture specified in CLAUDE.md.
- **Files involved**: `backend/api/nodes.py:53-361`
- **Min fix**: Extract the entire function body to `node_service.expand_node()`
- **Validation**: After extraction, nodes.py should be < 50 lines for expand_node
- **Score**: [user_leverage:5, core_capability:4, evidence:5, compounding:5, validation_ease:3, blast_radius:4]

### ISSUE-AD-002: nodes.py imports sqlite_repo directly, breaking layer boundary
- **User scenario**: N/A — architectural violation
- **Impact degree**: Medium
- **Problem detail**: `nodes.py:12` has `from backend.repositories import sqlite_repo` which is used for `record_sync_event` calls at lines 166, 305, 323, 449. The API layer should only call service functions, not repository functions.
- **Files involved**: `backend/api/nodes.py:12`
- **Min fix**: Move sync event recording into the service layer
- **Validation**: Grep for sqlite_repo in all api/*.py files, verify only imports used for type hints
- **Score**: [user_leverage:4, core_capability:4, evidence:5, compounding:4, validation_ease:3, blast_radius:3]

### ISSUE-AD-003: nodes.py imports agents and graph modules at function scope
- **User scenario**: N/A — startup performance issue
- **Impact degree**: Low
- **Problem detail**: `nodes.py:84-87` has `from backend.repositories import neo4j_repo as graph`, `from backend.agents import explorer`, `from backend.graph.validator import ...`, `from backend.graph.traversal import ...` all inside the function body. While this avoids circular imports, it means these modules are imported on every request, adding latency.
- **Files involved**: `backend/api/nodes.py:84-87`
- **Min fix**: Move imports to module level with proper circular import handling
- **Validation**: Profile a request, verify no import overhead
- **Score**: [user_leverage:2, core_capability:2, evidence:5, compounding:2, validation_ease:4, blast_radius:2]

### ISSUE-AD-004: _neo4j_session_supports_run is a test-only hack leaked into production
- **User scenario**: N/A — code smell
- **Impact degree**: Low
- **Problem detail**: `nodes.py:19-22` defines `_neo4j_session_supports_run` which checks `callable(getattr(session, "run", None))`. This exists because test stubs don't implement the `run` method. This test accommodation has leaked into production code.
- **Files involved**: `backend/api/nodes.py:19-22`
- **Min fix**: Fix the test stubs to implement `run` instead
- **Validation**: Remove the check, verify tests still pass
- **Score**: [user_leverage:2, core_capability:2, evidence:5, compounding:2, validation_ease:4, blast_radius:2]

### ISSUE-AD-005: No shared error handling middleware — each endpoint has its own try/except
- **User scenario**: N/A — developer experience
- **Impact degree**: Medium
- **Problem detail**: Every API endpoint has its own try/except block with `logger.exception` and `error_response`. This leads to inconsistent error messages, missing error_codes in some endpoints, and difficulty adding cross-cutting concerns (e.g., logging all errors to a monitoring system).
- **Files involved**: All `backend/api/*.py` files
- **Min fix**: Add a global exception handler or decorator for consistent error handling
- **Validation**: Add a new endpoint without try/except, verify it still returns proper errors
- **Score**: [user_leverage:4, core_capability:3, evidence:5, compounding:4, validation_ease:3, blast_radius:3]

### ISSUE-AD-006: generate_article endpoint at line 394 also has inline logic
- **User scenario**: N/A — architectural consistency
- **Impact degree**: Medium
- **Problem detail**: `nodes.py:394-460` `generate_article` endpoint has 66 lines of inline logic including Neo4j queries, AI calling, and sync event recording. Like expand_node, this should be in the service layer.
- **Files involved**: `backend/api/nodes.py:394-460`
- **Min fix**: Move to `node_service.generate_article()` or `article_service.generate_article()`
- **Validation**: After extraction, verify the endpoint is < 20 lines
- **Score**: [user_leverage:4, core_capability:3, evidence:5, compounding:3, validation_easy:3, blast_radius:3]

### ISSUE-AD-007: Multiple agents define _load_prompt identically
- **User scenario**: N/A — DRY violation
- **Impact degree**: Low
- **Problem detail**: `explorer.py:134-139`, `tutor.py:68-73`, `diagnoser.py:59-64` all define identical `_load_prompt` functions that read a file from `backend/prompts/`. This is a DRY violation.
- **Files involved**: `backend/agents/explorer.py:134-139`, `backend/agents/tutor.py:68-73`, `backend/agents/diagnoser.py:59-64`
- **Min fix**: Move `_load_prompt` to `base.py` as a shared utility
- **Validation**: Move function, verify all agents still load prompts correctly
- **Score**: [user_leverage:2, core_capability:2, evidence:5, compounding:2, validation_ease:5, blast_radius:1]

### ISSUE-AD-008: No dependency injection — services import modules directly
- **User scenario**: N/A — testability issue
- **Impact degree**: Medium
- **Problem detail**: Services like `practice_service.py` directly import `from backend.agents import tutor_agent` and `from backend.agents import diagnoser_agent`. There's no dependency injection, making it impossible to swap implementations for testing without monkeypatching.
- **Files involved**: `backend/services/practice_service.py:17-18`, all service files
- **Min fix**: Accept agent instances as function parameters where needed
- **Validation**: Write a test that mocks agents at the service level
- **Score**: [user_leverage:3, core_capability:3, evidence:4, compounding:3, validation_ease:3, blast_radius:3]

### ISSUE-AD-009: Frontend lib/ directory has inconsistent file naming and responsibilities
- **User scenario**: N/A — developer navigation
- **Impact degree**: Low
- **Problem detail**: `src/lib/` contains `utils.ts` (6 lines), `practice-constants.ts` (constants + types), `navigation-context.ts` (routing helpers), `article-workspace.ts` (515 lines of workspace logic), `summary-display.ts` (presentation logic), `review-display.ts` (display helpers), `tauri.ts`, and `workspace-storage.ts`. The naming convention mixes purposes (constants, helpers, presentation, storage).
- **Files involved**: `src/lib/`
- **Min fix**: Reorganize into `src/lib/constants/`, `src/lib/routing/`, `src/lib/presentation/`
- **Validation**: Verify files are logically grouped
- **Score**: [user_leverage:2, core_capability:1, evidence:4, compounding:2, validation_ease:4, blast_radius:1]

### ISSUE-AD-010: No shared types directory — types are defined inline in files
- **User scenario**: Developer needs to find where a type is defined
- **Impact degree**: Low
- **Problem detail**: The `src/types/` directory presumably contains shared types, but many component-specific types (like `WorkspaceArticle`, `WorkspaceBreadcrumbItem`) are defined in `src/lib/article-workspace.ts` rather than in `src/types/`.
- **Files involved**: `src/lib/article-workspace.ts:84-91`, `src/types/`
- **Min fix**: Move all shared types to `src/types/`, keep file-local types inline
- **Validation**: Grep for type definitions outside src/types/
- **Score**: [user_leverage:2, core_capability:1, evidence:4, compounding:2, validation_ease:4, blast_radius:1]

### CANDIDATE-AD-001: Extract expand_node into node_service.expand_node()
- **User problem**: 300-line function in API layer makes changes risky
- **User benefit**: Isolated, testable business logic
- **Min entry point**: Move the function body to node_service.py, keep API as thin wrapper
- **Files involved**: `backend/api/nodes.py:53-361`, `backend/services/node_service.py`
- **Score**: [user_leverage:5, core_capability:4, evidence:5, compounding:5, validation_ease:3, blast_radius:4, total:26]

### CANDIDATE-AD-002: Add global error handling middleware
- **User problem**: Inconsistent error handling across API endpoints
- **User benefit**: Consistent error responses, easier to add cross-cutting concerns
- **Min entry point**: Create middleware that catches unhandled exceptions and formats them
- **Files involved**: `backend/main.py`, all `backend/api/*.py`
- **Score**: [user_leverage:4, core_capability:3, evidence:5, compounding:4, validation_ease:3, blast_radius:3, total:22]

### CANDIDATE-AD-003: Implement proper dependency injection
- **User problem**: Hard-coded imports make testing difficult
- **User benefit**: Easy mocking and swapping implementations
- **Min entry point**: Create a service container that wires dependencies
- **Files involved**: All `backend/services/*.py`
- **Score**: [user_leverage:3, core_capability:3, evidence:4, compounding:4, validation_ease:2, blast_radius:3, total:19]

### CANDIDATE-AD-004: Extract article-workspace-page.tsx into smaller components
- **User problem**: 1732-line component is a maintenance burden
- **User benefit**: Each concern can be modified independently
- **Min entry point**: Create ArticleContent.tsx, ConceptDrawer.tsx, SearchBar.tsx components
- **Files involved**: `src/features/article-workspace/article-workspace-page.tsx`
- **Score**: [user_leverage:4, core_capability:2, evidence:5, compounding:4, validation_ease:3, blast_radius:3, total:21]

### CANDIDATE-AD-005: Split sqlite_repo.py into domain repositories
- **User problem**: 1715-line file is difficult to navigate and maintain
- **User benefit**: Each domain can evolve independently
- **Min entry point**: Move session-related functions to session_repo.py, review to review_repo.py
- **Files involved**: `backend/repositories/sqlite_repo.py`
- **Score**: [user_leverage:5, core_capability:3, evidence:5, compounding:4, validation_ease:3, blast_radius:3, total:23]

### CANDIDATE-AD-006: Add API response schema validation middleware
- **User problem**: No runtime guarantee that API responses match expected shapes
- **User benefit**: Catch serialization bugs before they reach the frontend
- **Min entry point**: Add response_model to FastAPI routes, validate before sending
- **Files involved**: `backend/api/*.py`
- **Score**: [user_leverage:4, core_capability:3, evidence:4, compounding:4, validation_ease:3, blast_radius:3, total:21]

### CANDIDATE-AD-007: Centralize _load_prompt into shared utility
- **User problem**: 3 identical prompt loading functions across agents
- **User benefit**: Single place to modify prompt loading behavior
- **Min entry point**: Move to backend/agents/base.py or backend/prompts/loader.py
- **Files involved**: `backend/agents/explorer.py:134-139`, `backend/agents/tutor.py:68-73`, `backend/agents/diagnoser.py:59-64`
- **Score**: [user_leverage:2, core_capability:2, evidence:5, compounding:2, validation_ease:5, blast_radius:1, total:17]

### CANDIDATE-AD-008: Add architecture decision records (ADRs)
- **User problem**: No documentation of why certain architectural choices were made
- **User benefit**: Future developers understand the reasoning behind key decisions
- **Min entry point**: Create docs/adr/ directory with ADRs for major decisions
- **Files involved**: `docs/`
- **Score**: [user_leverage:3, core_capability:2, evidence:3, compounding:3, validation_ease:4, blast_radius:2, total:17]

### CANDIDATE-AD-009: Reorganize lib/ directory with clear naming conventions
- **User problem**: lib/ files have inconsistent naming and responsibilities
- **User benefit**: Easier to find utilities and understand code organization
- **Min entry point**: Create subdirectories for constants, routing, presentation, storage
- **Files involved**: `src/lib/`
- **Score**: [user_leverage:2, core_capability:1, evidence:4, compounding:2, validation_ease:5, blast_radius:1, total:15]

### CANDIDATE-AD-010: Move generate_article to article_service
- **User problem**: Article generation logic is in the API layer
- **User benefit**: Consistent layer separation
- **Min entry point**: Create or extend article_service.py with generate_article function
- **Files involved**: `backend/api/nodes.py:394-460`, `backend/services/article_service.py`
- **Score**: [user_leverage:4, core_capability:3, evidence:5, compounding:3, validation_ease:3, blast_radius:3, total:21]

---

## Summary

| Lens | Issues | Candidates | Total | Key Theme |
|-------|--------|-----------|-------|-----------|
| UJ (User Journey) | 10 | 10 | 20 | Frontend UX friction and missing interactions |
| CC (Core Capability) | 10 | 10 | 20 | AI role gaps, feedback quality, signal persistence |
| RL (Reliability) | 10 | 10 | 20 | Multi-DB consistency, race conditions, error recovery |
| LQ (Learning Quality) | 10 | 10 | 20 | Feedback specificity, scoring accuracy, prompt quality |
| IL (Iteration Leverage) | 10 | 10 | 20 | Test gaps, type safety, code organization |
| AD (Architecture Drag) | 10 | 10 | 20 | Layer violations, god files, DRY violations |
| **Total** | **60** | **60** | **120** | |

### Top 5 Highest-Impact Issues (by score sum)

1. **ISSUE-RL-001**: expand_node 300-line inline multi-DB write without transaction [34]
2. **ISSUE-CC-001**: Explorer silently truncates source content to 8000 chars [27]
3. **ISSUE-CC-002**: Diagnoser fallback breaks feedback loop with empty data [26]
4. **ISSUE-UJ-003**: No error boundary wrapping route components [26]
5. **ISSUE-CC-008**: Async friction update fire-and-forget with no completion guarantee [26]

### Top 5 Highest-Impact Candidates (by score total)

1. **CANDIDATE-RL-001**: Sync event retry worker [26]
2. **CANDIDATE-IL-002**: E2E test with Playwright [25]
3. **CANDIDATE-RL-004**: Write-ahead log for expand_node [25]
4. **CANDIDATE-AD-001**: Extract expand_node to service layer [26]
5. **CANDIDATE-IL-008**: Split sqlite_repo into domain repos [23]
