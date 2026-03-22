# AxonClone -- Iteration Leverage Audit

> "What single change would make all future changes safer?"

Audit date: 2026-03-19
Auditor: iteration-leverage agent
Scope: test coverage, API contracts, observability, error boundaries, module coupling

---

## ISSUE-IL-001: nodes.py expand_node 仍是 300 行的单体函数，直接操作三库

**File:** `backend/api/nodes.py:55-360`

expand_node 在 API 层直接编排 Neo4j session、LanceDB 向量写入、SQLite session_nodes 追踪，绕过了 service 层。这是后端最大的单体函数，也是唯一一个在 API 层直接操作三库的端点。

- API 层内含 5 处 `sqlite_repo` 直接调用
- API 层内含 4 处原始 SQL（`db.execute`、`db.execute_fetchall`、`db.commit`）
- 函数体 ~300 行，深度嵌套 4 层 try/except

**Impact:** 任何节点扩展逻辑变更都必须修改 API 层，无法被 service 层测试覆盖，且绕过了 service 层的统一错误处理模式。

---

## ISSUE-IL-002: review_service.py 735 行，仅 5 个测试覆盖辅助函数

**File:** `backend/services/review_service.py`

review_service 包含 13 个函数（5 个纯计算 + 8 个 async DB 操作），是最大的 service 文件。现有测试仅覆盖：
- `calculate_review_priority`（精确值测试）
- `_calculate_forget_risk`（边界值）
- `_calculate_explain_gap`（边界值）
- `_get_next_review_interval`（间隔值）
- `generate_review_queue`（集成测试）

**未测试的关键函数：**
- `submit_review`（345 行，包含能力更新、复习调度、状态转换）
- `list_reviews`（分页 + due_before 过滤）
- `skip_review` / `snooze_review`（状态转换）
- `_auto_transition_node_status`（72 行，复杂的节点状态机）
- `_should_reschedule_future_review`（18 行，逻辑分支）

---

## ISSUE-IL-003: article_service.py 552 行，几乎零测试覆盖

**File:** `backend/services/article_service.py`

19 个 async 函数中，仅 `confirm_candidate` 通过 resilience 测试间接覆盖。以下核心函数完全没有测试：

- `analyze_article`（147 行，含 `[[wiki-link]]` 解析、候选生成、重绑定）
- `update_source_article`（含 mention 删除和候选状态回退）
- `search_workspace`（全文搜索）
- `_ensure_candidate`（去重逻辑）
- `create_candidate` / `ignore_candidate` / `list_backlinks_for_concept`

API 层 `test_articles_api.py` 测试了 HTTP 端点行为，但 service 层的内部逻辑分支（如 mention 签名计算、候选去重）无覆盖。

---

## ISSUE-IL-004: 前端 ErrorBoundary 仅包裹根节点，路由页面无独立降级

**Files:** `src/app/app.tsx:28`, `src/components/ui/error-boundary.tsx`

ErrorBoundary 只在 App 组件顶层包裹了一次。所有路由页面共享同一个 ErrorBoundary——如果某个页面（如 learning-page、graph-page）抛出渲染错误，整个应用白屏。

没有任何路由页面级别的 ErrorBoundary 包裹。对于一个有 9 个路由页面的桌面应用，这意味着一个组件的 bug 会杀死整个应用。

---

## ISSUE-IL-005: 前端 query key 散落在 use-queries.ts 字符串字面量中，无集中定义

**File:** `src/hooks/use-queries.ts`

所有 34 个 query key 都是硬编码的字符串字面量（如 `['topic', topicId, 'graph', params]`），无集中常量定义。`use-mutations.ts` 中的 60+ 个 `invalidateQueries` 调用也是手工匹配的。

存在不一致：
- queries 中用 `'abilities-overview'`，mutations 中用 `'abilities-overview'`（OK）
- 但 `'abilities-snapshots'` 在 queries 中使用，mutations 中却用 `'topic', topicId, 'abilities-snapshots'`（不存在于 queries 中）——导致 `submitPractice` 的 `invalidateQueries` 对 abilities-snapshots 无效

**Impact:** 如果 query key 命名不统一，mutation 后的数据刷新静默失败，用户看到过期数据而不自知。

---

## ISSUE-IL-006: AbilityRecord Pydantic model 无字段级验证约束

**File:** `backend/models/ability.py:23-37`

`AbilityRecord` 的 8 个能力维度字段（`understand`, `example` 等）定义为 `int = 0`，没有 `ge=0, le=100` 约束。`AbilityDelta` 同样缺少约束。

虽然 `apply_delta()` 函数内做了 clamp，但任何直接构造 `AbilityRecord` 的代码（如 service 层从 DB dict 构造）都可以绕过校验：

```python
record = AbilityRecord(topic_id="x", node_id="y", understand=999)
# Pydantic 不报错，但数据非法
```

---

## ISSUE-IL-007: FrictionRecord.friction_type 使用运行时 warning 替代 Pydantic 验证

**File:** `backend/models/friction.py:50-57`

`FrictionRecord.create()` 中对非法 `friction_type` 只是 `logging.warning()` 然后静默替换为 `'weak_structure'`。Pydantic model 层面没有 `Literal` 或 `pattern` 约束：

```python
class FrictionRecord(BaseModel):
    friction_type: str  # 无约束，任意字符串都能通过
```

AI 输出的 friction_type 如果拼写错误，会被静默吞掉而不会报错。

---

## ISSUE-IL-008: PracticeResult.ability_update 类型为 `dict | None`，无结构约束

**File:** `backend/models/practice.py:87`

```python
ability_update: dict | None = None
```

`PracticeResult.ability_update` 是 AI 生成的关键数据，但类型只是裸 `dict`。没有定义它应该包含哪些 key、值范围是多少。如果 AI 输出格式变化，下游代码不会在构造时就报错。

---

## ISSUE-IL-009: sqlite_repo.py 1715 行，部分函数无测试

**File:** `backend/repositories/sqlite_repo.py`

57 个 async 函数中，通过 API 层间接测试的约 30 个。以下函数无任何测试覆盖：

- `resolve_sync_event`（同步事件处理）
- `cleanup_old_sync_events`（定时清理）
- `batch_create_friction_records`（批量创建卡点）
- `delete_article_generated_candidates`（文章候选清理）
- `rebind_mentions_to_concept`（mention 重绑定）
- `search_topics`（主题搜索）
- `increment_topic_stats`（统计自增，在 nodes.py 直接调用）

---

## ISSUE-IL-010: node_service.py diagnose 函数无测试

**File:** `backend/services/ability_service.py:84-145`

`diagnose()` 和 `diagnose_full()` 是 Diagnoser 角色的核心输出函数，但没有任何测试。`test_core.py` 只测试了 `diagnoser_fallback`（agent 层 fallback），不覆盖 service 层的诊断编排逻辑。

---

## ISSUE-IL-011: 前端 use-mobile.ts hook 无测试

**File:** `src/hooks/use-mobile.ts`

`use-mobile.ts` 是断言式 hook（检测屏幕宽度），但无测试。前端测试文件列表中不包含此 hook 的测试。

---

## ISSUE-IL-012: 前端 use-resolved-topic-context.ts 无测试

**File:** `src/hooks/use-resolved-topic-context.ts`

此 hook 封装了 topic 解析逻辑，是 learning-flow 的关键依赖，但无独立测试。

---

## ISSUE-IL-013: 前端 64 个测试中无 hooks 测试

所有 64 个前端测试分布在 14 个 describe 块中，覆盖：
- 纯函数（article-renderer、review-display、summary-display、navigation-context、workspace-storage、workspace-ui）
- 组件（route-pages、learning-flow、practice-session-flow、review-page、stats-page、article-workspace）
- 核心逻辑（core-logic：extractConceptRefs、graph-adapter、类型一致性）

**完全没有测试的：**
- `use-queries.ts`（34 个 query hooks）
- `use-mutations.ts`（24 个 mutation hooks）
- `use-resolved-topic-context.ts`
- `use-mobile.ts`
- `api-client.ts`（guardUrl、unwrapEnvelope、ApiError）
- `app-store.ts`（Zustand store）

---

## ISSUE-IL-014: api-client.ts 错误处理路径无测试

**File:** `src/services/api-client.ts`

`api-client.ts` 是所有 API 调用的唯一出口，包含：
- `guardUrl()` 路径遍历防护
- `unwrapEnvelope()` 响应格式校验
- `ApiError` 自定义错误类
- 网络错误拦截器（超时、断连）

这些关键路径无任何测试。如果 `unwrapEnvelope` 的 `success` 判断逻辑出错，所有 API 调用都会静默失败。

---

## ISSUE-IL-015: 前端 mutation 错误处理统一使用 toast，无法区分错误类型

**File:** `src/hooks/use-mutations.ts:51`

```typescript
const _onError = () => showToast('操作失败，请重试', 'error')
```

所有 24 个 mutation 共享同一个错误处理函数，无论错误是网络超时、权限拒绝还是数据校验失败，都显示相同的 "操作失败" 提示。用户无法根据错误类型采取不同行动。

---

## ISSUE-IL-016: 后端日志使用标准 logging 模块，无结构化输出

**Files:** 所有 `backend/` 下的 Python 文件

整个后端使用 Python 标准 `logging.getLogger(__name__)`，没有结构化日志（如 structlog 或 JSON 格式）。在生产环境下：
- 无法按 topic_id / session_id / node_id 过滤日志
- 日志格式不一致（有些用 f-string，有些用 % 格式化）
- nodes.py expand_node 中混合使用 `logger.warning(f"...")` 和 `logger.warning("...")`

---

## ISSUE-IL-017: 前端 route pages 内有散落的 query key 直接引用

**File:** `src/routes/review-page.tsx:82`

review-page.tsx 中直接调用 `qc.invalidateQueries({ queryKey: ['reviews'] })`，绕过了 hooks 层。这破坏了 "所有数据操作通过 hooks 层" 的架构约束。

---

## ISSUE-IL-018: topic_service.py create_topic 依赖顺序不可验证

**File:** `backend/services/topic_service.py:21-363`

`create_topic` 函数体内有 "SQLite -> Neo4j -> LanceDB" 的写入顺序，但这个顺序只在代码中隐式保证。如果未来有人在中间插入新的写入步骤，没有机制防止顺序错误或遗漏补偿记录。

---

## ISSUE-IL-019: stats_service.py 仅 42 行但无任何测试

**File:** `backend/services/stats_service.py`

`get_global_stats()` 和 `get_topic_stats()` 虽然简单，但涉及多个表的聚合查询（topics、sessions、ability_records、review_items），且 API 测试只验证 HTTP 200 + `success: true`，不验证数值正确性。

---

## ISSUE-IL-020: export_service.py 导出格式逻辑无单元测试

**File:** `backend/services/export_service.py:15-141`

`_sanitize_filename()` 和 `export_topic()` 中的 Markdown/JSON/Anki 生成逻辑，仅通过 API 层的 happy-path 测试覆盖。`test_services.py` 中的 `test_export_markdown_structure` 和 `test_export_anki_format` 测试了部分输出格式，但不覆盖：
- 中文文件名清理
- 空数据的导出行为
- 大量节点的导出性能

---

## ISSUE-IL-021: 后端无集成测试覆盖 "AI 失败降级 -> 继续使用 fallback" 的完整链路

**File:** `backend/tests/test_core.py`

`test_core.py` 测试了各个 agent 的 fallback 返回值，但不测试 "agent 调用失败 -> service 层降级 -> API 返回 fallback 数据" 的端到端链路。例如：
- Explorer 失败 -> 至少返回一个 entry node（已测试，但用 mock）
- Tutor 失败 -> 返回静态练习模板（仅在 practice_service 代码中处理，无测试）
- Synthesizer 失败 -> 规则型总结（无测试）

---

## ISSUE-IL-022: 前端无 `queryOptions` 工厂函数，staleTime 配置分散

**File:** `src/hooks/use-queries.ts`

staleTime 配置分散在各处：
- settings: `5 * 60_000`
- health: `30_000`
- system-capabilities: `60_000`
- deferred-nodes: `2 * 60_000`
- practice-attempts: `60_000`
- recommended-practice: `2 * 60_000`
- concept-summary: `5 * 60_000`
- session-summary: `5 * 60_000`
- global stats: `30_000`
- topic stats: `30_000`
- ability-snapshots: `60_000`

没有统一的 staleTime 策略文档或工厂函数。如果需要调整某个类别的缓存策略，需要逐个修改。

---

## ISSUE-IL-023: Zustand store persist partialize 只持久化 sidebar_collapsed 和 graph_view

**File:** `src/stores/app-store.ts:111-114`

Zustand store 定义了 15+ 个状态字段，但 `partialize` 只持久化 2 个。这意味着用户刷新页面后，graph_selected_node_id、graph_edge_filters 等状态全部丢失。这是有意设计（session-scoped 状态不持久化），但缺乏文档说明。

---

## ISSUE-IL-024: practice_service.py submit_practice 的异步诊断是 fire-and-forget

**File:** `backend/services/practice_service.py:59, 82-367`

`submit_practice` 中通过 `asyncio.create_task()` 启动异步诊断任务，然后在 `_log_friction_update_result` 中处理结果。如果诊断任务异常，只有 `logger.warning` 记录，用户无感知。

测试中（`test_submit_practice_updates_ability_record`）用 mock 覆盖了异步诊断，但 fire-and-forget 模式本身的行为未被测试。

---

## ISSUE-IL-025: 前端 services/index.ts 与 types 存在循环引用风险

**Files:** `src/services/index.ts`, `src/types/index.ts`

services/index.ts import 了 30+ 类型从 `../types`，types 中可能引用 service 层的常量。虽然当前无循环引用，但随着类型增长，这个双向依赖可能导致构建问题。

---

## ISSUE-IL-026: Pydantic model 中 `PracticeFeedback` 所有字段为可选，无约束

**File:** `backend/models/practice.py:39-47`

`PracticeFeedback` 的所有字段都有默认值（空字符串或空列表），没有 min_length 约束。AI 返回的 feedback 如果全部为空，下游代码会显示空白反馈而不是错误。

---

## ISSUE-IL-027: test_services.py 存在测试 ID 重复定义

**Files:** `backend/tests/test_services.py:18`, `backend/tests/test_session_review_regressions.py`

两个测试文件都定义了 `test_complete_session_closes_open_session_nodes`。pytest 会运行两者，但如果它们的断言期望不同（例如一个用 mock，一个用真实 DB），可能产生假阴性。

---

## ISSUE-IL-028: practice_service.py _rule_based_ability_delta 与 apply_delta 逻辑重复

**File:** `backend/services/practice_service.py:46-57`

`_rule_based_ability_delta()` 是 Tutor 失败时的规则型降级函数，内部有自己的 clamp 逻辑。`apply_delta()` 也有 clamp。两者独立维护，如果 clamp 规则变化，需要同步修改两处。

---

## ISSUE-IL-029: 后端 API 层 nodes.py 中 Neo4j Cypher 查询包含字符串拼接

**File:** `backend/api/nodes.py:266-270`

```python
await session.run(
    f"""UNWIND $items AS item
       MATCH ...
       MERGE (src)-[r:`{rel_type}`]->(tgt)
       SET r.reason = item.reason""",
    {"items": rel_items},
)
```

`rel_type` 通过 f-string 拼接到 Cypher 查询中。虽然 `rel_type` 来自 `validate_and_filter_edges` 的白名单校验，但这个模式本身是危险的——如果白名单校验被绕过，就存在 Cypher 注入风险。

---

## ISSUE-IL-030: 前端无 loading skeleton 的统一组件

**Files:** `src/components/shared/`, `src/app/app.tsx`

`app.tsx` 引入了 `LoadingSkeleton`，但各页面是否有统一的 loading 状态未审计。如果某个页面在数据加载期间渲染了不完整的 UI，可能导致闪烁或布局偏移。

---

## CANDIDATE-IL-001: 将 expand_node 从 API 层提取到 node_service

**Effort:** Medium | **Leverage:** High

将 `nodes.py:expand_node` 的 300 行逻辑拆分为 `node_service.expand_node()`。这会让：
- 节点扩展逻辑可被单元测试覆盖
- 三库写入顺序统一在 service 层保证
- API 层仅负责请求解析和响应格式化

**Depends on:** 无

---

## CANDIDATE-IL-002: 建立 query key 常量工厂

**Effort:** Small | **Leverage:** High

创建 `src/lib/query-keys.ts`，集中定义所有 query key：

```typescript
export const keys = {
  topics: (params?) => ['topics', params],
  topic: (id) => ['topic', id],
  topicGraph: (id, params?) => ['topic', id, 'graph', params],
  // ...
}
```

这会让 mutations 的 `invalidateQueries` 和 queries 的 `queryKey` 自动保持一致，消除 ISSUE-IL-005。

**Depends on:** 无

---

## CANDIDATE-IL-003: 为 Pydantic model 添加字段级验证

**Effort:** Small | **Leverage:** High

- `AbilityRecord`: 8 个维度加 `ge=0, le=100`
- `FrictionRecord.friction_type`: 改为 `Literal["prerequisite_gap", "concept_confusion", ...]`
- `PracticeResult.ability_update`: 定义为 typed model
- `PracticeFeedback`: 加 `min_length` 约束

这能让非法数据在构造时就报错，而不是在运行时静默传播。

**Depends on:** 无

---

## CANDIDATE-IL-004: 为每个路由页面添加独立 ErrorBoundary

**Effort:** Small | **Leverage:** Medium

在 `app.tsx` 中为每个 lazy 路由组件包裹独立的 ErrorBoundary：

```tsx
<Route element={<AppLayout />}>
  <Route index element={<ErrorBoundary><Suspense><HomePage /></Suspense></ErrorBoundary>} />
  ...
</Route>
```

这样单个页面崩溃不会影响其他页面。

**Depends on:** 无

---

## CANDIDATE-IL-005: 补充 review_service 的 submit_review 测试

**Effort:** Medium | **Leverage:** High

`submit_review` 是 345 行的核心函数，覆盖：
- 正常提交 + 能力更新 + 复习调度
- 空能力记录的 bootstrap
- future review 的 reschedule 决策
- 状态转换（pending -> reviewing -> completed）

**Depends on:** 无

---

## CANDIDATE-IL-006: 补充 article_service 核心函数测试

**Effort:** Medium | **Leverage:** High

重点覆盖：
- `analyze_article` 的 `[[wiki-link]]` 解析和候选去重
- `update_source_article` 的 mention 删除和候选回退
- `confirm_candidate` 的图写入 + 向量写入

**Depends on:** 无

---

## CANDIDATE-IL-007: 为 api-client.ts 添加单元测试

**Effort:** Small | **Leverage:** Medium

测试 `guardUrl`、`unwrapEnvelope`、`ApiError` 类和网络错误拦截器。这是所有前端数据流的唯一出口，其正确性直接影响所有页面。

**Depends on:** 无

---

## CANDIDATE-IL-008: 为 ability_service diagnose 添加测试

**Effort:** Medium | **Leverage:** Medium

覆盖 `diagnose()` 和 `diagnose_full()` 在各种能力维度组合下的诊断输出。

**Depends on:** 无

---

## CANDIDATE-IL-009: 统一 mutation 错误处理策略

**Effort:** Small | **Leverage:** Medium

将 `_onError` 从固定字符串改为根据 `ApiError.code` 映射不同提示：
- `NETWORK_ERROR` -> "网络连接失败"
- `SESSION_NOT_ACTIVE` -> "会话已结束"
- `PRACTICE_SUBMIT_INVALID` -> "提交内容不满足要求"
- fallback -> "操作失败，请重试"

**Depends on:** CANDIDATE-IL-007

---

## CANDIDATE-IL-010: 引入 structlog 替换标准 logging

**Effort:** Medium | **Leverage:** Medium

统一日志格式为 JSON，自动注入 topic_id / session_id / request_id。这对生产环境调试至关重要。

**Depends on:** 无

---

## CANDIDATE-IL-011: 合并 _rule_based_ability_delta 到 apply_delta

**Effort:** Small | **Leverage:** Small

将 `practice_service._rule_based_ability_delta()` 的逻辑统一到 `ability.apply_delta()` 中，消除重复的 clamp 逻辑。

**Depends on:** 无

---

## CANDIDATE-IL-012: 将 nodes.py 中的 f-string Cypher 改为参数化查询

**Effort:** Small | **Leverage:** High

```python
# Before (危险):
f"""MERGE (src)-[r:`{rel_type}`]->(tgt)"""

# After (安全):
"""MERGE (src)-[r]->(tgt) SET r:` + rel_type + ` = true"""
# 或使用 APOC 动态关系
```

消除 Cypher 注入风险。

**Depends on:** 无

---

## CANDIDATE-IL-013: 为 stats_service 添加数值正确性测试

**Effort:** Small | **Leverage:** Small

在测试中插入已知数据（topics、sessions、ability_records），验证 `get_global_stats()` 和 `get_topic_stats()` 返回的聚合值精确匹配。

**Depends on:** 无

---

## CANDIDATE-IL-014: 建立 query staleTime 策略文档

**Effort:** Small | **Leverage:** Small

文档化 staleTime 策略：
- 实时数据（health）：30s
- 用户操作数据（topics、sessions）：0s（默认）
- 参考数据（settings）：5min
- 历史数据（stats、snapshots）：60s

**Depends on:** CANDIDATE-IL-002

---

## CANDIDATE-IL-015: 为前端 hooks 编写基础测试

**Effort:** Medium | **Leverage:** Medium

优先测试：
- `use-mutations.ts` 的 `invalidateQueries` key 一致性
- `use-resolved-topic-context.ts` 的 topic 解析逻辑
- `use-mobile.ts` 的断点逻辑

使用 `renderHook` from `@testing-library/react`。

**Depends on:** 无

---

## CANDIDATE-IL-016: 将 resolve_sync_event 和 cleanup_old_sync_events 加入测试

**Effort:** Small | **Leverage:** Medium

sync_events 是多库一致性补偿的关键机制，但核心处理函数 `resolve_sync_event` 无测试。

**Depends on:** 无

---

## CANDIDATE-IL-017: 消除 review-page.tsx 中的直接 query key 引用

**Effort:** Small | **Leverage:** Small

将 `review-page.tsx:82` 的 `qc.invalidateQueries({ queryKey: ['reviews'] })` 改为调用 hooks 层导出的 mutation hook 或创建专用的 `useInvalidateReviews` hook。

**Depends on:** CANDIDATE-IL-002

---

## CANDIDATE-IL-018: 为 create_topic 的写入顺序添加集成测试

**Effort:** Medium | **Leverage:** Medium

测试 SQLite 写入成功但 Neo4j/LanceDB 失败时的补偿事件记录。已有 resilience 测试覆盖部分场景，但缺少完整的事务性验证（如 SQLite 回滚测试）。

**Depends on:** CANDIDATE-IL-001

---

## CANDIDATE-IL-019: 为前端 app-store 编写测试

**Effort:** Small | **Leverage:** Small

测试 Zustand store 的：
- 初始状态
- persist partialize 行为
- Set 操作（toggle、clear）
- migration 逻辑（v0 -> v1）

**Depends on:** 无

---

## CANDIDATE-IL-020: 统一后端 f-string 和 % 格式化的日志风格

**Effort:** Small | **Leverage:** Small

当前代码混合使用 `logger.warning(f"...")` 和 `logger.warning("...", var)`。统一为 % 格式化（Python logging 最佳实践），避免 f-string 在日志级别未启用时的性能开销。

**Depends on:** 无

---

## CANDIDATE-IL-021: 将 test_services.py 中重复的测试函数名去重

**Effort:** Small | **Leverage:** Small

`test_complete_session_closes_open_session_nodes` 在 `test_services.py` 和 `test_session_review_regressions.py` 中都有定义，应合并或重命名。

**Depends on:** 无

---

## CANDIDATE-IL-022: 为 AI 失败降级链路编写端到端测试

**Effort:** Medium | **Leverage:** High

使用 mock 的 AI agent，测试：
1. Tutor 失败 -> submit_practice 返回规则型评估
2. Synthesizer 失败 -> complete_session 返回规则型总结
3. Explorer 失败 -> expand_node 降级到 Neo4j 邻居

这些测试应该在 API 层（httpx AsyncClient）运行，验证完整的请求-响应链路。

**Depends on:** 无

---

## CANDIDATE-IL-023: 建立前端 ErrorBoundary 测试

**Effort:** Small | **Leverage:** Small

测试 ErrorBoundary 的：
- 子组件抛错时显示 fallback UI
- "重试渲染" 按钮重置 state
- "刷新页面" 按钮触发 reload
- 自定义 fallback 渲染

**Depends on:** CANDIDATE-IL-004

---

## CANDIDATE-IL-024: 将 API 层剩余的原始 SQL 移入 service/repo 层

**Effort:** Small | **Leverage:** Medium

`nodes.py` 中的 4 处原始 SQL：
- `db.execute("SELECT COUNT(*) ...")` -> `session_service.count_session_nodes()`
- `db.execute_fetchall("SELECT title, ...")` -> `topic_service.get_topic_meta()`
- `db.execute("INSERT OR IGNORE INTO session_nodes ...")` -> 已在 CANDIDATE-IL-001 中处理
- `articles.py:db.execute("SELECT 1 FROM topics ...")` -> `topic_service.topic_exists()`

**Depends on:** CANDIDATE-IL-001

---

## CANDIDATE-IL-025: 为 PracticeFeedback 添加非空校验或 fallback 值

**Effort:** Small | **Leverage:** Small

当 AI 返回空 feedback 时，前端应显示 "AI 评估暂不可用" 而不是空白。可以在 PracticeFeedback model 的 validator 中添加 `model_validator(mode='after')` 检查。

**Depends on:** CANDIDATE-IL-003

---

## Summary Statistics

| Category | Issues | Candidates |
|----------|--------|------------|
| Test Coverage | 13 | 14 |
| API Contracts / Pydantic | 4 | 2 |
| Error Boundaries / Resilience | 4 | 3 |
| Observability / Logging | 2 | 2 |
| Module Coupling | 3 | 2 |
| Frontend State / Query Keys | 2 | 2 |
| **Total** | **30** | **25** |

## Priority Matrix (Effort x Leverage)

### High Leverage + Low Effort (Do First)
1. **CANDIDATE-IL-002**: query key 常量工厂 -- 消除 key 不一致
2. **CANDIDATE-IL-003**: Pydantic 字段级验证 -- 构造时捕获非法数据
3. **CANDIDATE-IL-012**: 消除 Cypher f-string 注入风险
4. **CANDIDATE-IL-007**: api-client.ts 测试 -- 覆盖唯一数据出口
5. **CANDIDATE-IL-004**: 路由级 ErrorBoundary -- 防止单页崩溃

### High Leverage + Medium Effort (Do Next)
6. **CANDIDATE-IL-001**: expand_node 提取到 service 层 -- 最大单体函数
7. **CANDIDATE-IL-005**: review submit 测试 -- 最大未测核心函数
8. **CANDIDATE-IL-006**: article_service 测试 -- 第二大未测 service
9. **CANDIDATE-IL-022**: AI 降级链路端到端测试 -- 覆盖关键 fallback
