# Learning Quality Audit Report

> Lens: Learning Effect & Feedback Quality
> Date: 2026-03-19
> Scope: practice generation, diagnosis feedback, ability scoring, review scheduling, cross-session persistence, prompt templates

---

## Issues (ISSUE-LQ-NNN)

### ISSUE-LQ-001: `PRACTICE_DIMENSION_MAP` 缺少 `recall` 类型的映射
**File**: `backend/models/ability.py:12-20`
**Severity**: Medium
**Description**: `PRACTICE_DIMENSION_MAP` 定义了 7 种练习类型的维度映射（define/example/contrast/apply/teach_beginner/compress/explain），但复习场景使用 `review_type="recall"` 映射到 `practice_type_for_eval="recall"`（`review_service.py:411`）。`PRACTICE_DIMENSION_MAP` 中没有 `"recall"` 键。当 `review_service.py:503` 查找 `PRACTICE_DIMENSION_MAP.get("recall", ["recall", "explain"])` 时，使用的是 fallback 默认值 `["recall", "explain"]`，这在功能上碰巧正确，但属于隐式依赖——如果有人修改 fallback 默认值或 PRACTICE_DIMENSION_MAP 增加了 `"recall"` 键但映射不同，就会产生不一致。
**Impact**: 复习提交的能力维度映射依赖硬编码 fallback，而非显式声明。
**Fix**: 在 `PRACTICE_DIMENSION_MAP` 中显式添加 `"recall": ["recall", "understand"]`。

### ISSUE-LQ-002: `_friction_practice_map` 引用了不存在的 friction_type `vague_expression`
**File**: `backend/services/practice_service.py:160-166`
**Severity**: Medium
**Description**: `_friction_practice_map` 包含 `"vague_expression": ["example", "apply"]`，但 `FrictionType.ALL`（`backend/models/friction.py:21-24`）只有 7 种类型：`prerequisite_gap`, `concept_confusion`, `lack_of_example`, `weak_structure`, `abstract_overload`, `weak_recall`, `weak_application`。`vague_expression` 不在白名单中。虽然 AI Diagnoser 不太可能生成这个 tag（prompt 中未列出），但如果有旧数据或手动写入包含 `vague_expression`，`_friction_practice_map.get(tag, [])` 会返回空列表而非抛错，只是静默忽略。不过更重要的是 `FrictionRecord.create()` 会将未知类型替换为 `weak_structure`（`friction.py:53-57`），所以这个 map entry 永远不会被触发——属于死代码。
**Impact**: 死代码，误导维护者以为 `vague_expression` 是有效的 friction_type。如果未来添加该类型，还需要同步更新 `FrictionType.ALL`。
**Fix**: 删除 `vague_expression` 条目，或在 `FrictionType.ALL` 中添加该类型并更新 Diagnoser prompt。

### ISSUE-LQ-003: AI Diagnoser 返回的 `ability_delta` 未经过 friction_type 白名单校验
**File**: `backend/services/practice_service.py:143-144`, `backend/agents/diagnoser.py:19-56`
**Severity**: Low
**Description**: Diagnoser AI 返回的 `friction_tags` 在写入 `FrictionRecord` 时会通过 `FrictionRecord.create()` 做白名单校验（未知类型替换为 `weak_structure`），但 `ability_delta` 没有任何校验。AI 可能返回 `"understanding": 5`（非标准字段名）或 `"understand": 15`（超范围值），前者在 `practice_service.py:299` 的维度过滤时被忽略，后者在 `practice_service.py:304` 被 clamp 到 10。这虽然不会崩溃，但 AI 返回的非标准维度名会静默丢失。
**Impact**: AI 输出维度名拼写错误时静默丢弃，不生成任何日志提示。
**Fix**: 在 Diagnoser 的 `validate_ai_output` 或 `practice_service` 中添加 ability_delta 字段名白名单校验，对非标准字段记录 warning。

### ISSUE-LQ-004: `apply_delta` 双重 clamp 但语义不同步
**File**: `backend/models/ability.py:95-119`, `backend/services/practice_service.py:304`
**Severity**: Low
**Description**: `apply_delta` 内部有 `clamp()`（增量 clamp 到 ±10/±5 再 clamp 到 0-100 范围）。`practice_service.py:304` 在调用 `apply_delta` 前先做了一次 `ability_delta = {k: max(-5, min(10, v)) for k, v in ability_delta.items()}`。这是双重 clamp，语义正确但冗余。`review_service.py:505` 也有类似的显式 clamp。如果未来修改 clamp 规则（比如允许 +15），需要在多处同步修改。
**Impact**: 代码冗余，未来维护可能不同步。
**Fix**: 将 clamp 逻辑统一到 `apply_delta` 内部，service 层不再重复 clamp。

### ISSUE-LQ-005: 复习提交时 `medium` 被视为 `success`（`review_service.py:474`）
**File**: `backend/services/review_service.py:474`
**Severity**: Medium
**Description**: `success = result_level in ("good", "medium")`，意味着 `medium` 评分也算"成功"，会触发更长的复习间隔（`_REVIEW_SUCCESS_INTERVALS`）。但 `medium` 通常表示"一般"，用户对内容的掌握并不充分。将 `medium` 归为 `success` 会导致遗忘间隔过早拉长，用户还没真正掌握就被推到 3 天后再复习。这与间隔重复的最佳实践不一致。
**Impact**: 复习间隔增长过快，用户可能在未充分掌握时就被推入长间隔，降低复习效果。
**Fix**: 改为 `success = result_level == "good"`，或将 `medium` 映射到短间隔（如 1 天）。

### ISSUE-LQ-006: 复习时 AI 评估 fallback 使用字符长度作为质量代理
**File**: `backend/services/review_service.py:457-462`
**Severity**: Medium
**Description**: 当 AI 评估失败时，fallback 逻辑是 `len(user_answer) > 100 → good`，`len(user_answer) > 30 → medium`，否则 `weak`。这个启发式非常粗糙——用户可以写 200 字的废话得到 `good`，也可以写 20 字的精确回答得到 `weak`。更关键的是，这个 fallback 会直接影响能力分数更新（因为它决定 `success`），间接影响复习间隔。
**Impact**: AI 不可用时，复习评估完全不可靠，可能给用户错误的能力反馈。
**Fix**: 改为默认 `medium` + 明确告知用户"AI 评估不可用，本次不更新能力分数"，或至少不基于长度做能力更新。

### ISSUE-LQ-007: Friction record 异步写入使用独立 DB 连接，存在最终一致性风险
**File**: `backend/services/practice_service.py:171-264`
**Severity**: Low
**Description**: `_async_friction_update()` 创建独立 SQLite 连接写入 friction records。这是 fire-and-forget 模式，如果主请求后续读取 friction（如 `get_frictions`），可能看不到刚提交的 friction records。对于练习提交场景影响不大（用户不会立刻查看 frictions），但如果其他业务流程依赖同步读取 friction，就会出现数据不一致。
**Impact**: 边界情况下用户在练习提交后立刻查看卡点列表，可能看不到最新记录。
**Fix**: 文档化这个行为为"最终一致"，或在前端做延迟加载。

### ISSUE-LQ-008: `get_recommended_practice_type` 不考虑练习质量（只看是否完成过）
**File**: `backend/services/practice_service.py:413-433`
**Severity**: Medium
**Description**: `get_recommended_practice_type` 只检查 `completed_types` 集合（基于 `practice_type` 是否在历史记录中出现过），不考虑该类型练习的评分。比如用户做过一次 `define` 但得了 `weak`，系统仍然会跳过 `define` 推荐下一个类型。这意味着用户没有机会在同一类型上改进。
**Impact**: 用户每次练习都被推到新类型，即使之前类型表现不佳，无法在同类型上迭代改进。
**Fix**: 加入"弱类型优先重练"逻辑：如果某类型最近一次评分是 `weak`，优先重练而非推到下一个类型。

### ISSUE-LQ-009: Synthesizer 的 `ability_summary` 只取前 5 个节点
**File**: `backend/services/session_service.py:121-125`
**Severity**: Medium
**Description**: `ability_summary` 构建时 `records[:5]`，只取前 5 个 ability records。当 topic 有超过 5 个节点时，Synthesizer 无法看到后续节点的能力情况，可能导致总结中遗漏重要信息。且 `records` 的排序未显式指定，可能是按 `node_id` 或插入顺序，而非按重要性或访问顺序。
**Impact**: Synthesizer 总结的质量在节点数 > 5 时下降，可能遗漏薄弱节点。
**Fix**: 按最弱维度或最近访问排序后取前 5-10 个，或在 prompt 中传入聚合摘要（平均分、最弱节点等）而非原始记录。

### ISSUE-LQ-010: `_suggest_review_type` 只考虑 3 个维度，忽略其他 5 个
**File**: `backend/services/review_service.py:35-48`
**Severity**: Low
**Description**: `_suggest_review_type` 只看 `recall`, `contrast`, `explain` 三个维度选择复习类型。`apply`, `transfer`, `teach`, `understand`, `example` 五个维度完全不在复习类型选择范围内。如果用户 `apply` 维度最弱（分数为 5），但 `recall` 是 40，系统不会推荐 `apply` 类型的复习。
**Impact**: 部分能力维度的薄弱不会被复习系统覆盖。
**Fix**: 扩展 `_suggest_review_type` 以覆盖更多维度，或在 `_REVIEW_TYPE_PRACTICE_MAP` 中增加更多映射（如 `"apply"` → `"apply"`）。

### ISSUE-LQ-011: `review_service.py` 中 `ReviewItem.status` 有 `"due"` 状态但无自动转换逻辑
**File**: `backend/services/review_service.py`, `backend/models/review.py:32`
**Severity**: Low
**Description**: `ReviewItem.status` 支持 `pending|due|completed|failed|skipped|snoozed|cancelled`。`generate_review_queue` 创建时 status 为 `pending`，但没有定时任务将 `pending` 转换为 `due`（当 `due_at` 到期时）。`list_reviews` 在查询 `status="pending"` 时会同时拉取 `pending`/`due`/`snoozed` 并做日期过滤（`review_service.py:307-313`），所以功能上不受影响。但 `due` 状态从未被设置，属于死状态。
**Impact**: `due` 状态从未被写入，数据库中不存在 status="due" 的记录，`list_reviews` 中对 `due` 的查询是无效的。
**Fix**: 要么删除 `due` 状态并简化 `list_reviews` 逻辑，要么添加状态转换逻辑（定时任务或查询时标记）。

### ISSUE-LQ-012: 复习队列生成不考虑 `recall_confidence` 字段
**File**: `backend/services/review_service.py:538-735`
**Severity**: Low
**Description**: `generate_review_queue` 使用 `calculate_review_priority` 公式计算优先级，但该公式不包含 `recall_confidence`。`recall_confidence` 在 `submit_review` 中更新（`review_service.py:517-522`），但从未被优先级计算使用。这意味着一个 `recall_confidence=0.1`（即将遗忘）的节点和一个 `recall_confidence=0.9`（记忆牢固）的节点，如果其他参数相同，会得到相同的优先级。
**Impact**: `recall_confidence` 的衰减模型被精心实现但未被使用，浪费了计算资源。
**Fix**: 在 `calculate_review_priority` 中引入 `recall_confidence` 作为 ForgetRisk 的补充因子。

### ISSUE-LQ-013: Tutor feedback prompt 缺少 `learning_intent` 在 user prompt 中的使用
**File**: `backend/agents/tutor.py:149-169`
**Severity**: Low
**Description**: `generate_feedback_prompt` 将 `learning_intent` 注入 system prompt（`tutor_feedback.md` 中的 `{learning_intent}`），这是正确的。但 user prompt 只包含题目和用户回答，没有传入 `ability_record` 或 `friction_history`。相比 Diagnoser 的 `diagnose_prompt` 会传入 `ability_record` 和 `friction_history`，Tutor 的反馈生成无法参考用户历史能力水平和过去卡点，可能导致反馈不够个性化。
**Impact**: Tutor 反馈缺乏历史上下文，可能给出与用户实际水平不匹配的建议。
**Fix**: 在 `generate_feedback_prompt` 中传入 `ability_record` 摘要，让 Tutor 了解用户当前水平。

### ISSUE-LQ-014: Practice prompt 缓存不区分 `difficulty` 和 `learning_intent`
**File**: `backend/services/practice_service.py:446-457`, `backend/repositories/sqlite_repo.py`
**Severity**: Medium
**Description**: `get_cached_practice_prompt` 使用 `(topic_id, node_id, practice_type)` 作为复合键（`MEMORY.md` 提到）。但同一个 node 对同一个 practice_type，在不同 `difficulty` 或 `learning_intent` 下应该生成不同题目。缓存键不包含 `difficulty` 和 `learning_intent`，导致用户修改难度或意图后，仍然拿到旧的缓存题目。`regenerate=True` 可以绕过，但用户通常不知道需要重新生成。
**Impact**: 用户切换学习意图或难度后，练习题目不会自动更新。
**Fix**: 缓存键加入 `difficulty`，或在缓存命中后检查 `difficulty`/`learning_intent` 是否匹配。

### ISSUE-LQ-015: `_calculate_forget_risk` 当 `history_count > 5` 时固定返回 0.1
**File**: `backend/services/review_service.py:57-68`
**Severity**: Low
**Description**: `_FORGET_RISK_INTERVALS = [1, 3, 7, 14, 30]`，当 `history_count >= 5` 时 `idx = min(history_count, 4)` 固定为 4，interval=30，ForgetRisk=3/30=0.1。这意味着复习 5 次后，ForgetRisk 永远是 0.1，不再下降。这在设计上是合理的（不能无限降低到 0），但意味着高频复习的节点最终会收敛到相同的低风险值，丧失区分度。
**Impact**: 长期复习的节点在优先级排序中区分度不足。
**Fix**: 可以在 5 次后使用渐进衰减公式而非固定值，或接受当前设计为合理的下限。

### ISSUE-LQ-016: Diagnoser few-shot 示例中 `ability_delta` 与 `PRACTICE_DIMENSION_MAP` 不一致
**File**: `backend/prompts/diagnose.md:47-48`
**Severity**: Low
**Description**: 示例 1（概念混淆）中，练习类型是 `contrast`，AI 输出 `ability_delta: {"contrast": -3, "explain": -2}`。根据 `PRACTICE_DIMENSION_MAP`，`contrast` 应该只影响 `["contrast", "explain"]`，这里是一致的。示例 2（表达结构弱）中，类型是 `explain`，输出 `{"explain": -2, "understand": -1}`，也一致。示例 3（优秀回答）中，类型是 `define`，输出 `{"understand": 5, "explain": 4}`，一致。few-shot 整体正确。
**Impact**: 无直接影响。但 few-shot 中未展示 `apply`, `teach_beginner`, `compress` 类型的 ability_delta 模式，AI 对这些类型的维度映射可能不够准确。
**Fix**: 补充 `apply` 和 `teach_beginner` 的 few-shot 示例。

### ISSUE-LQ-017: `_auto_transition_node_status` 的 mastered 阈值 70 与 `_should_reschedule_future_review` 的 mastered 判断不联动
**File**: `backend/services/review_service.py:200-271`, `backend/services/review_service.py:622`
**Severity**: Low
**Description**: `_auto_transition_node_status` 在 avg >= 70 时设为 `mastered` 并取消 pending review items。但 `generate_review_queue` 中的过滤条件是 `avg < 70 and max_score > 0`（`review_service.py:622`），这意味着 avg 正好 70 的节点不会被生成复习项。两个阈值一致（70），但 `generate_review_queue` 的 `max_score > 0` 条件意味着如果某节点只有 1 个维度有微小正分（如 understand=1），avg 可能是 0.125，会被纳入复习队列。这是合理的但可能导致大量微弱练习记录触发复习。
**Impact**: 微小练习记录（如只做了一次 define 得了 1 分）也会触发复习生成。
**Fix**: 加入最低练习次数门槛（如至少完成 2 次练习才纳入复习队列）。

### ISSUE-LQ-018: `submit_practice` 中 `ability_delta` 为空 dict 时不创建 snapshot
**File**: `backend/services/practice_service.py:297-340`
**Severity**: Low
**Description**: 当 AI Diagnoser 返回 `ability_delta: {}` 时（如诊断完全失败但未走 fallback 路径），`practice_service.py:297-304` 会尝试过滤 delta，得到空 `filtered_delta`，然后调用 `_rule_based_ability_delta` 生成基于 feedback 的 delta。但如果 `feedback` 也是 `None`（极端情况），则 `ability_delta` 保持为空 dict，`updated_ability` 为 `None`，不创建 ability snapshot（`practice_service.py:324`）。这意味着该次练习没有任何记录。
**Impact**: 极端情况下练习记录丢失（无 ability 更新、无 snapshot），但 practice_attempt 仍然被创建。
**Fix**: 确保即使 AI 全部失败，也至少用 rule-based delta 创建一个最小 snapshot。

### ISSUE-LQ-019: `generate_review_queue` 的 `due_at` 回填逻辑可能在首次生成时产生不合理的 `due_at`
**File**: `backend/services/review_service.py:630`
**Severity**: Medium
**Description**: `due_at = node_due_from_history.get(node_id, now).isoformat()`，首次生成复习队列时（无历史 review），使用 `now` 作为 due_at。这意味着所有新复习项的到期时间都是"现在"，用户打开复习列表时会看到大量"已到期"的项。这虽然在功能上正确（新复习项应该尽快做），但用户体验不佳——用户刚完成一轮学习就被催促复习所有节点。
**Impact**: 用户体验差，可能产生"学习焦虑"。
**Fix**: 首次生成时使用 `now + _FORGET_RISK_INTERVALS[0]` 天（即 1 天后）作为 due_at，给用户缓冲时间。

### ISSUE-LQ-020: Tutor `static_practice_fallback` 的 `prompt_text` 是练习类型描述而非实际问题
**File**: `backend/agents/tutor.py:216-223`
**Severity**: Low
**Description**: `static_practice_fallback` 返回 `"prompt_text": _PRACTICE_TYPE_MAP.get(practice_type, "请用自己的话解释这个概念。")`。`_PRACTICE_TYPE_MAP` 中的值是描述性文本（如 `"定义表达：用自己的话定义或解释概念"`），而非实际可回答的问题。这导致用户看到的是类型描述而非具体题目。`practice_service.py` 中的静态 fallback（`practice_service.py:525-533`）使用了更好的格式（如 `"请用自己的话定义或解释这个概念。"`），但 `tutor_agent.static_practice_fallback()` 和 `practice_service` 的静态 fallback 是两套不同的逻辑。
**Impact**: AI 失败时，`tutor_agent.static_practice_fallback()` 返回的 prompt 文本质量低于 `practice_service` 的静态 fallback，但 `practice_service` 只在 `tutor_agent.generate_practice()` 返回 None 时才走到自己的静态 fallback（`practice_service.py:524-540`），不会使用 `tutor_agent.static_practice_fallback()`。不过如果其他地方直接调用 `static_practice_fallback()`，就会有问题。
**Fix**: 统一两套静态 fallback 逻辑，或删除 `tutor_agent.static_practice_fallback()`。

### ISSUE-LQ-021: `practice_service.py` 中 `_recommended_practice_types` 计算结果未被返回给前端
**File**: `backend/services/practice_service.py:157-169`
**Severity**: Low
**Description**: `_recommended_practice_types` 在 `submit_practice` 内部基于 friction_tags 计算，但没有被包含在 `PracticeResult` 返回值中（`practice_service.py:357-365`）。前端无法知道 friction 诊断后推荐的下一步练习类型。`get_recommended_practice_type` 是单独的 API，需要前端额外调用。
**Impact**: 前端需要额外 API 调用才能获取基于诊断结果的推荐练习类型，增加延迟。
**Fix**: 将 `_recommended_practice_types` 加入 `PracticeResult` 返回。

### ISSUE-LQ-022: Synthesizer prompt 中 `asset_highlights` 的 `correctness` 类型不一致
**File**: `backend/agents/synthesizer.py:69`
**Severity**: Low
**Description**: `_SUMMARY_SCHEMA` 中 `asset_highlights[].correctness` 定义为 `"type": "number"`，但实际 `expression_assets` 中的 `correctness` 是字符串 `"good"/"medium"/"weak"`（来自 Tutor feedback）。这会导致 AI 输出的 `correctness` 可能是数字或字符串，取决于模型对 schema 的理解。在 `session_service.py:139` 中直接取 `a.get("correctness", "")` 传入 synthesis，类型不一致。
**Impact**: Synthesizer AI 输出的 `correctness` 类型不确定，可能导致前端渲染异常。
**Fix**: 将 `_SUMMARY_SCHEMA` 中 `correctness` 改为 `{"type": "string"}` 与实际数据对齐。

---

## Candidates (CANDIDATE-LQ-NNN)

### CANDIDATE-LQ-001: Diagnoser prompt 应要求 AI 对每个 friction_tag 提供简要原因
**File**: `backend/prompts/diagnose.md`
**Rationale**: 当前 Diagnoser 只输出 friction_tags 列表，没有要求附带判断依据。用户看到 "concept_confusion" 但不知道 AI 为什么这样判断。如果要求 AI 对每个 tag 附带 1-2 句原因，可以显著提高反馈的可操作性和可信度。
**Effort**: Low (prompt 修改 + schema 更新)

### CANDIDATE-LQ-002: 在练习提交后返回 `next_practice_recommendation`
**File**: `backend/services/practice_service.py:357-365`
**Rationale**: 当前练习提交后，前端需要单独调用 `get_recommended_practice_type` 获取下一步推荐。可以在 `PracticeResult` 中直接包含推荐，减少一次 API round-trip，也使推荐能基于本次诊断结果更精准。
**Effort**: Low (已在 ISSUE-LQ-021 分析)

### CANDIDATE-LQ-003: 引入"练习质量评分"维度：consistency（多次练习的一致性）
**File**: `backend/models/ability.py`
**Rationale**: 当前 8 个维度都是绝对能力，缺少"稳定性"维度。一个每次都随机波动的用户和一个稳定进步的用户可能得到相同的总分。引入 `consistency` 维度可以更精准地反映真实掌握程度。
**Effort**: High (需要新维度 + 历史数据计算 + UI 更新)

### CANDIDATE-LQ-004: 复习评估应支持"部分正确"的中间状态
**File**: `backend/services/review_service.py:457-462`
**Rationale**: 当前 AI fallback 只有 good/medium/weak 三档。可以引入更细粒度的评分（如 1-5 分），配合不同的复习间隔策略。比如 3/5 分对应 1 天后复习，4/5 分对应 3 天后。
**Effort**: Medium (需要修改 schema + 间隔映射)

### CANDIDATE-LQ-005: Practice prompt 应包含节点间关系上下文
**File**: `backend/agents/tutor.py:76-146`
**Rationale**: 当前练习题只基于单个节点的 name + summary 出题，不包含与其他节点的关系（如 prerequisite、contrasts_with）。如果题目能引用关联节点（如 "请说明 Dropout 和 BatchNorm 在训练效果上的区别"），可以更好地测试用户的对比能力。
**Effort**: Medium (需要 Neo4j 查询 + prompt 模板更新)

### CANDIDATE-LQ-006: `ability_delta` 应基于当前分数做自适应缩放
**File**: `backend/services/practice_service.py:304`
**Rationale**: 当前 clamp 是绝对的（+10/-5），不区分用户当前水平。一个从 0 分开始进步到 10 分的用户，和一个从 80 分进步到 90 分的用户，增量都是 +10。但后者显然更难。可以根据当前分数做缩放：低分段给更大增量，高分段给更小增量。
**Effort**: Medium (需要修改 apply_delta + 测试)

### CANDIDATE-LQ-007: Tutor feedback 应支持"追问"模式
**File**: `backend/agents/tutor.py`
**Rationale**: 当 Tutor 识别到用户回答有明确的知识缺口时（如缺少某个关键点），可以生成一个简短追问而非只给反馈。例如用户解释 Dropout 但没提到"防止共适应"，Tutor 可以追问"Dropout 为什么能减少过拟合？"。这比被动等用户做下一轮练习更高效。
**Effort**: Medium (需要新 prompt + 前端追问 UI)

### CANDIDATE-LQ-008: 复习队列应按 topic 进度动态调整复习密度
**File**: `backend/services/review_service.py:538-735`
**Rationale**: 当前复习队列生成不考虑 topic 的整体进度。一个刚开始学的 topic（只有 2 个节点）和一个深入学习的 topic（20 个节点），复习队列的密度应该不同。可以引入"复习密度系数"：节点少时减少并发复习数，节点多时允许更多并发。
**Effort**: Low (在 generate_review_queue 中加入并发控制)

### CANDIDATE-LQ-009: Synthesizer 应在总结中包含"本轮最关键的进步"和"最需改进的点"
**File**: `backend/agents/synthesizer.py`, `backend/prompts/synthesize.md`
**Rationale**: 当前总结中的 `key_takeaways` 是知识层面的收获，缺少"能力进步"层面的反馈（如"你在对比表达上有明显进步"）。加入能力进步反馈可以增强用户的学习成就感和方向感。
**Effort**: Low (prompt 修改)

### CANDIDATE-LQ-010: 为 `apply` 练习类型增加 few-shot 示例
**File**: `backend/prompts/tutor_prompt.md`
**Rationale**: 当前 tutor_prompt.md 有 define/contrast/apply/teach_beginner/compress 五种示例，但 tutor_feedback.md 只有 explain 和 define 两种示例，diagnose.md 有 contrast/explain/define 三种。反馈和诊断 prompt 的 few-shot 覆盖不够全面，尤其缺少 `apply` 和 `teach_beginner` 的诊断示例。
**Effort**: Low (添加 few-shot 示例)

### CANDIDATE-LQ-011: Friction record 应支持 `resolved_at` 字段表示卡点是否已解决
**File**: `backend/models/friction.py`
**Rationale**: 当前 friction_records 只有 `created_at`，没有解决标记。用户可能在后续练习中解决了某个卡点，但旧 friction 记录永远存在，影响 `_calculate_confusion_risk`。增加 `resolved_at` 字段，在相关练习达到 good 评分时自动标记已解决。
**Effort**: Medium (schema + service + migration)

### CANDIDATE-LQ-012: 练习缓存应支持基于 `learning_intent` 的多版本
**File**: `backend/services/practice_service.py:446-457`
**Rationale**: (与 ISSUE-LQ-014 关联) 同一个节点在不同学习意图下应该有不同题目。缓存应支持 intent 维度，确保 fix_gap 模式下不会拿到 build_system 的题目。
**Effort**: Low (扩展缓存键 + 可能的 migration)

### CANDIDATE-LQ-013: `get_recommended_practice_type` 应考虑时间间隔
**File**: `backend/services/practice_service.py:413-433`
**Rationale**: 当前推荐只看历史记录是否存在，不考虑时间。如果用户 3 周前做过 define（得了 good），现在推荐重做 define 可能比推到新类型更有价值（遗忘效应）。
**Effort**: Low (加入时间衰减因子)

### CANDIDATE-LQ-014: Ability overview 应包含维度不平衡指标
**File**: `backend/services/ability_service.py:23-70`
**Rationale**: 当前 overview 返回各维度平均值，但不计算维度间的方差或不平衡度。一个 understand=80 但 contrast=10 的节点，应该比 understand=45 contrast=45 的节点获得更高的"需要改进"优先级。可以引入"维度不平衡度"指标。
**Effort**: Low (计算逻辑修改)

### CANDIDATE-LQ-015: 复习提交应创建 ability snapshot（与练习提交一致）
**File**: `backend/services/review_service.py:345-535`
**Rationale**: `submit_practice` 在每次练习后创建 ability snapshot（`practice_service.py:322-354`），但 `submit_review` 不创建。这意味着复习导致的能力变化无法在时间线上追踪，用户无法看到"复习前 vs 复习后"的能力变化。
**Effort**: Low (复用 snapshot 创建逻辑)

### CANDIDATE-LQ-016: Diagnoser 的 `suggested_prerequisite_nodes` 返回 node_id 但前端无法直接使用
**File**: `backend/agents/diagnoser.py:48-51`
**Rationale**: `_DIAGNOSE_SCHEMA` 中 `suggested_prerequisite_nodes` 是字符串数组，但未指定是 node_id 还是 node_name。AI 可能返回名称而非 ID，前端无法直接跳转。应在 prompt 中明确要求返回 node_id，或增加 name→ID 的解析步骤。
**Effort**: Low (prompt 明确化)

---

## Summary

| Category | Count |
|----------|-------|
| Issues | 22 |
| Candidates | 16 |
| Critical | 0 |
| Medium | 6 |
| Low | 16 |

### Top Priority Issues
1. **ISSUE-LQ-005**: 复习 medium 算 success 导致间隔增长过快 — 直接影响复习效果
2. **ISSUE-LQ-006**: AI fallback 用字符长度评估质量 — 影响降级场景下的用户体验
3. **ISSUE-LQ-008**: 推荐练习不考虑质量只看完成 — 影响练习迭代效果
4. **ISSUE-LQ-014**: 缓存不区分 difficulty/intent — 影响个性化练习体验
5. **ISSUE-LQ-019**: 首次复习队列 due_at=now — 影响学习体验
6. **ISSUE-LQ-009**: Synthesizer 只看 5 个节点 — 影响总结质量

### Prompt Quality Assessment
- **tutor_prompt.md**: 质量良好，有 5 个类型的 few-shot，难度控制清晰，支持历史表达和误解上下文。
- **tutor_feedback.md**: 质量中等，只有 2 个示例（explain + define），缺少 apply/teach_beginner/compress/contrast 的反馈示例。
- **diagnose.md**: 质量良好，有 3 个示例（含优秀回答），friction_type 白名单清晰。缺少 apply/teach_beginner 类型示例。
- **synthesize.md**: 质量良好，有 2 个示例（正常 + 待改进），输出结构合理。
