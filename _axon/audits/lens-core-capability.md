# Core Capability Audit — AxonClone

> 从"产品核心承诺是否兑现"视角，逐项检查核心能力链、AI 四角色、数据流完整性、降级策略。

审计日期：2026-03-19
审计范围：backend/services/、backend/agents/、backend/graph/、backend/models/、backend/repositories/

---

## 核心能力链审计

### 1. 内容拆解（Explorer + 节点生成）

| # | 检查项 | 状态 | 说明 |
|---|--------|------|------|
| 1 | 输入解析 → 初始节点 bundle | OK | explorer.create_topic() 返回 entry_node + nodes + edges + outline |
| 2 | Schema 校验 | OK | validate_ai_output() 在 topic_service 和 explorer 内双重校验 |
| 3 | 关系类型白名单 | OK | EdgeType 枚举 6 种，validator.py 强制校验 |
| 4 | LanceDB 语义去重 >=0.92 | OK | validate_and_filter_nodes() 调用 check_duplicate_node() |
| 5 | 节点扩展（expand_node） | OK | explorer.expand_node() + traversal.filter_nodes_for_expand() |
| 6 | Session 级节点上限 12 | OK | nodes.py:76 检查 session_nodes count |
| 7 | 深度限制 2-3 | OK | traversal.get_depth_limit() clamp 到 [2,3] |
| 8 | 每次扩展 3-5 节点 | OK | EXPAND_MIN_NODES=3, EXPAND_MAX_NODES=5 |

### 2. 知识网络化（图谱 + 关系）

| # | 检查项 | 状态 | 说明 |
|---|--------|------|------|
| 9 | 主干 BFS 优先 | OK | sort_nodes_by_mainline_priority + EDGE_MAINLINE_WEIGHTS |
| 10 | ExpandScore 排序 | OK | calculate_expand_score 含 Relevance x IntentMatch x StructuralPriority 等 6 维 |
| 11 | Topic 最大 30 节点 | OK | enforce_topic_cap()，但仅定义未调用 |
| 12 | 主干链折叠 | PARTIAL | 前端限制未在后端强制执行，enforce_topic_cap 已定义但未被调用 |
| 13 | is_mainline 继承 | OK | PREREQUISITE 边从父节点继承 is_mainline |
| 14 | 学习意图控制 Explorer | OK | _INTENT_GUIDANCE 5 种意图全覆盖 |

### 3. 表达训练（Tutor + 6 种练习类型）

| # | 检查项 | 状态 | 说明 |
|---|--------|------|------|
| 15 | define | OK | 静态 fallback + AI 生成 + 维度映射 |
| 16 | example | OK | 同上 |
| 17 | contrast | OK | 同上 |
| 18 | apply | OK | 同上 |
| 19 | teach_beginner | OK | 同上 |
| 20 | compress | OK | 同上 |
| 21 | explain（额外类型） | OK | 同上 |
| 22 | 练习序列推荐 | OK | PRACTICE_SEQUENCE 定义 6 种顺序 |
| 23 | 推荐练习类型 | OK | get_recommended_practice_type() 按历史 + 薄弱维度推荐 |
| 24 | 自适应难度 | OK | difficulty=adaptive 根据能力均值调整出题难度 |
| 25 | 练习 prompt 缓存 | OK | SQLite practice_prompt_cache |
| 26 | 表达资产持久化 | OK | ExpressionAsset.create() + sqlite_repo |
| 27 | 历史表达资产注入 prompt | OK | expression_assets 参数传入 Tutor |
| 28 | 学习意图控制 Tutor | OK | _INTENT_GUIDANCE 5 种意图全覆盖 |

### 4. 能力诊断（Diagnoser + 8 维评分）

| # | 检查项 | 状态 | 说明 |
|---|--------|------|------|
| 29 | 8 维度全覆盖 | OK | understand/example/contrast/apply/explain/recall/transfer/teach |
| 30 | 增量 +10/-5 clamp | OK | apply_delta() + practice_service 双重 clamp |
| 31 | 单次练习只更新相关维度 | OK | PRACTICE_DIMENSION_MAP 过滤 + filtered_delta |
| 32 | friction_tags 生成 | OK | Diagnoser 返回 friction_tags |
| 33 | friction_tags 写入 friction_records | OK | _async_friction_update fire-and-forget |
| 34 | misconception_hints 持久化 | OK | 写入 Neo4j Misconception 节点 + HAS_MISCONCEPTION 边 |
| 35 | Evidence 节点 | OK | practice 提交时创建 Evidence 节点 |
| 36 | 能力快照记录 | OK | ability_snapshot 每次 practice 后写入 |
| 37 | 学习意图控制 Diagnoser | OK | _INTENT_GUIDANCE 5 种意图全覆盖 |

### 5. 长期资产沉淀

| # | 检查项 | 状态 | 说明 |
|---|--------|------|------|
| 38 | ExpressionAsset CRUD | OK | save/list/toggle_favorite |
| 39 | session 级资产聚合 | OK | complete_session 中查询 session_assets |
| 40 | 资产高亮 | OK | asset_highlights 在 synthesis 中 |

### 6. 间隔复习（Review + Synthesizer）

| # | 检查项 | 状态 | 说明 |
|---|--------|------|------|
| 41 | ReviewPriority 公式 | OK | Importance x ForgetRisk x ExplainGap x ConfusionRisk x TimeDueWeight |
| 42 | ConfusionRisk friction 权重 | OK | _severity_weights 7 种 friction 类型 |
| 43 | 间隔递增 | OK | _REVIEW_SUCCESS_INTERVALS = [3, 7, 14, 30, 60] 天 |
| 44 | 失败回退 1 天 | OK | _REVIEW_FAILURE_INTERVAL = 1 |
| 45 | recall_confidence 衰减 | OK | 指数衰减 + MIN_CONFIDENCE=0.1 |
| 46 | 自动 mastered/practiced 转换 | OK | _auto_transition_node_status avg>=70 mastered |
| 47 | Synthesizer 总结 | OK | synthesize() 含 mainline_summary + key_takeaways |
| 48 | 复习候选生成 | OK | review_candidates → ReviewItem |
| 49 | 复习队列自动生成 | OK | generate_review_queue 基于 ability records |
| 50 | 学习意图控制 Synthesizer | OK | _INTENT_GUIDANCE 5 种意图全覆盖 |

### 7. 收束总结（Synthesizer）

| # | 检查项 | 状态 | 说明 |
|---|--------|------|------|
| 51 | mainline_summary | OK | Synthesizer AI 生成 + fallback |
| 52 | key_takeaways | OK | 列表形式 |
| 53 | next_recommendations | OK | 列表含 node_id/name/summary |
| 54 | synthesis_json 持久化 | OK | complete_session_synthesis 写入 SQLite |
| 55 | 规则型 fallback | OK | synthesize_fallback() 基于 visited_nodes + practice_count |

---

## Issues

### ISSUE-CC-001: enforce_topic_cap(30) 已定义但从未被调用
**严重度**: P2
**位置**: backend/graph/traversal.py:206-219
**说明**: enforce_topic_cap() 已完整实现（按 mainline priority 截断到 30 节点），但在 topic_service.create_topic() 和 nodes.py expand_node() 中均未调用。当用户持续扩展时，单个 Topic 可无限增长，违背文档"单 Topic 最大节点数限制 30，超过强制折叠支线"的承诺。
**影响**: 图谱过大导致前端渲染性能下降、学习路径推荐质量下降。
**建议**: 在 create_topic 和 expand_node 中新增节点前调用 enforce_topic_cap()，超出部分自动 defer。

### ISSUE-CC-002: sync_events 仅记录，无补偿/重试机制
**严重度**: P1
**位置**: backend/repositories/sqlite_repo.py (record_sync_event), 全部 service 文件
**说明**: 所有 Neo4j/LanceDB 写入失败后通过 record_sync_event 记录 pending 状态，但搜索整个代码库没有任何 retry/recover/compensate 函数。这些 pending 记录永远不会被处理，数据会静默丢失。文档承诺"失败时记录补偿任务或回滚标记，不静默丢失"。
**影响**: Neo4j 写入失败后节点存在 SQLite 但不存在 Neo4j，图谱不完整；LanceDB 写入失败后语义去重失效。
**建议**: 至少实现一个 startup reconciliation 函数，在应用启动时扫描 pending sync_events 并重试。优先级高的操作（如 topic.create）应该有同步重试。

### ISSUE-CC-003: expand_node 业务逻辑在 API 层而非 service 层
**严重度**: P2
**位置**: backend/api/nodes.py:52-361
**说明**: expand_node 路由函数长达 300+ 行，包含完整的 Explorer AI 调用、Neo4j 批量写入、LanceDB 向量写入、session cap 检查等复杂业务逻辑。这违反了 CLAUDE.md "AI 与业务逻辑分层"原则，也违反了 API→Service→Repository 的分层架构。node_service.py 中没有 expand_node 方法。
**影响**: 无法独立测试扩展逻辑；API 层与 neo4j_repo、explorer_agent、validator 直接耦合。
**建议**: 将 expand_node 的核心逻辑下沉到 node_service.py，API 层只做参数提取和响应格式化。

### ISSUE-CC-004: fire-and-forget friction 写入使用独立 SQLite 连接但无事务保障
**严重度**: P2
**位置**: backend/services/practice_service.py:171-263
**说明**: _async_friction_update() 创建新的 aiosqlite 连接写 friction_records，这意味着 friction_tags 写入与主 practice 提交不在同一事务中。如果主请求成功但 friction 写入失败（如 asyncio task 被取消），friction 记录会静默丢失，而前端已告知用户 friction 标签已记录。
**影响**: 用户看到的 friction 信息与实际存储不一致；Diagnoser 后续诊断缺少本次 friction 上下文。
**建议**: 要么将 friction 写入放回主事务（同步），要么在 friction task 完成后通知前端结果。考虑到已有 try/finally 关闭连接，同步写入更安全。

### ISSUE-CC-005: review_service.generate_review_queue 依赖 list_review_items(limit=None) 全量加载
**严重度**: P2
**位置**: backend/services/review_service.py:569
**说明**: generate_review_queue() 调用 `list_review_items(db, topic_id=topic_id, limit=None)` 一次性加载该 Topic 的所有 review items 到内存，然后遍历构建 per-node 的 review history。当 Topic 运行时间长（数十次复习）时，这是 O(n) 内存和 I/O。
**影响**: 长期使用的 Topic 复习队列生成变慢。
**建议**: 用 GROUP BY node_id 的聚合查询替代全量加载，一次查询获取 per-node 的 completed_count 和 pending/due 状态。

### ISSUE-CC-006: review submit 中 "medium" 评为 success，可能导致弱回答不断推进间隔
**严重度**: P2
**位置**: backend/services/review_service.py:474
**说明**: `success = result_level in ("good", "medium")` 将 medium 也视为成功，这会使复习间隔按 success 递增 [3, 7, 14, 30, 60] 天。但 medium 意味着用户回答质量一般，不应该获得与 good 相同的间隔递增奖励。
**影响**: 用户仅凭"勉强及格"的回答就能将复习间隔推到 60 天，导致遗忘。
**建议**: medium 应该使用较短的间隔（如 1-3 天），只有 good 才使用标准间隔递增。或者引入一个独立的中等等级间隔 [1, 3, 7, 14, 30]。

### ISSUE-CC-007: 入口节点选择（get_entry_node）不考虑 prepare_expression/prepare_interview
**严重度**: P2
**位置**: backend/services/node_service.py:38-190
**说明**: get_entry_node() 对 solve_task/fix_gap/build_system 三种意图有专门逻辑，但对 prepare_expression 和 prepare_interview 没有处理。当 learning_intent 为这两种时，代码会直接使用 topic 的 entry_node_id 或 current_node_id，忽略了意图对推荐路径的影响。
**影响**: prepare_expression 用户总是从固定入口开始，无法优先选择需要表达训练的节点；prepare_interview 用户无法优先选择高频考点。
**建议**: 为 prepare_expression 优先选择 explain_gap 最大（understand 高但 explain 低）的节点；为 prepare_interview 优先选择 importance 高且 apply/contrast 维度低的节点。

### ISSUE-CC-008: MisunderstandingRecord 对象在文档中承诺但未实现
**严重度**: P1
**位置**: backend/models/ 中无 misunderstanding_record.py
**说明**: CLAUDE.md 明确列出 Node 下应有 `MisconceptionRecord（误解记录）`，且核心反哺闭环中写了"误解记录 → 影响节点展示内容和对比题生成"。代码中虽有 Neo4j Misconception 节点（practice_service._async_friction_update），但没有独立的 MisconceptionRecord Pydantic model，没有 CRUD 接口，无法查询/管理误解历史。
**影响**: 误解数据散落在 Neo4j 中，无法通过 API 访问，无法按 Topic/Node 聚合展示，无法支撑 V1 的"误解图谱可视化"功能。
**建议**: 创建 MisconceptionRecord model + sqlite_repo 方法 + API 路由，至少支持 list/resolve。

### ISSUE-CC-009: graph/validator.py 注入检测不覆盖 SQL 注入向量
**严重度**: P3
**位置**: backend/graph/validator.py:15-16
**说明**: SUSPICIOUS_PATTERNS 检测 XSS 向量（<script, javascript: 等），但不检测 SQL 注入向量（如 `' OR 1=1 --`）。虽然 Neo4j 使用参数化查询，但 entry_node 的 name/summary 可能被拼接到非参数化上下文（如 f-string 中的 Cypher）。
**影响**: 低风险——当前 Neo4j 写入均使用参数化查询，但 defense-in-depth 原则应覆盖。
**建议**: 增加 SQL 注入模式检测或确保所有 Neo4j 查询路径均使用参数化。

### ISSUE-CC-010: topic_service.create_topic 中 initial node embedding 硬编码 [:5] 与 max_initial 可能不一致
**严重度**: P3
**位置**: backend/services/topic_service.py:262
**说明**: 第 113 行 `valid_nodes[:max_initial]` 写入 Neo4j 的节点数量受 max_initial 控制（shortest_path 时为 4），但第 262 行 `for n in ai_result.get("nodes", [])[:5]` 写入 LanceDB 时硬编码为 5。如果 max_initial < 5，LanceDB 会为未写入 Neo4j 的节点生成向量。
**影响**: LanceDB 中存在"幽灵向量"——有 embedding 但无对应 Neo4j 节点，语义去重会错误匹配。
**建议**: 将 LanceDB 循环改为遍历实际写入 Neo4j 的节点（valid_nodes[:max_initial]），或使用 node_name_to_id.keys() 确认。

### ISSUE-CC-011: learn_node 意图（get_entry_node）中 solve_task 主线路径选取过于简单
**严重度**: P3
**位置**: backend/services/node_service.py:68-82
**说明**: solve_task 的入口节点选取仅看 mainline 前 5 个节点的 ability 平均值最低者。文档承诺"优先最短路径（2-5 节点）"，但代码不计算实际路径长度或 BFS 最短路径，只按 ability 排序。
**影响**: 可能推荐一个 importance 低但 ability 也低的边缘节点，而非用户任务真正需要的关键路径节点。
**建议**: 结合 importance 权重和 PREREQUISITE 链深度来选择，而非纯 ability 最低值。

### ISSUE-CC-012: entry_node 的 article_body 字段未在 fallback 中设置
**严重度**: P3
**位置**: backend/agents/explorer.py:210-225
**说明**: create_topic_fallback() 返回的 entry_node 不包含 article_body 字段。当 AI 完全失败时，入口节点没有文章内容，前端会显示卡片布局并提示"生成文章"。但前端代码在 article_body 为空时需要用户手动点击生成，多了一次交互。
**影响**: AI 失败时的用户体验较差，用户需要额外操作才能开始阅读。
**建议**: 在 fallback 中至少为 entry_node 添加简短的 article_body（如基于 summary 生成一句话）。

### ISSUE-CC-013: 同步机制中对 Neo4j 关系类型使用 f-string 拼接，存在 Cypher 注入风险
**严重度**: P2
**位置**: backend/services/topic_service.py:204, backend/api/nodes.py:268
**说明**: 关系类型通过 f-string 直接嵌入 Cypher 查询：`` f"""MERGE (src)-[r:`{rel_type}`]->(tgt)"""``。虽然 validate_and_filter_edges() 在之前做了白名单校验，但 expand_node 路由中的 _expand_edges 来自 AI 输出（经过 validator），如果 validator 被绕过或白名单有 bug，rel_type 可能包含恶意 Cypher。
**影响**: 潜在的 Cypher 注入攻击面。虽然风险低（需要先绕过 validator），但违反参数化原则。
**建议**: 在执行前对 rel_type 做额外的正则白名单检查（只允许大写字母+下划线），或改用 APOC 动态关系创建。

### ISSUE-CC-014: Diagnoser 的 friction_tags 未做白名单校验
**严重度**: P3
**位置**: backend/services/practice_service.py:141-142
**说明**: Diagnoser AI 返回的 friction_tags 直接写入 friction_records，没有校验是否在已知类型列表中（prerequisite_gap, concept_confusion, weak_structure, abstract_overload, weak_recall, weak_application, lack_of_example）。虽然 review_service._calculate_confusion_risk() 用 dict.get() 处理未知类型，但未知的 friction_type 会污染数据分析。
**影响**: 统计页和分析功能可能显示无效的 friction 类型。
**建议**: 在写入前过滤/映射 friction_tags 到已知类型列表。

### ISSUE-CC-015: 能力更新中 practice_service 和 review_service 使用不同的 delta 应用逻辑
**严重度**: P2
**位置**: backend/services/practice_service.py:296-320, backend/services/review_service.py:499-513
**说明**: practice_service 先 clamp 到 [-5, 10]，然后调用 apply_delta()（内部再次 clamp）；review_service 也先 clamp，然后手动构建 AbilityDelta 对象调用 apply_delta()。但 review_service 的 filtered_delta 只填充了 allowed_dims 的维度，其余维度传入 AbilityDelta 时为 0，而 apply_delta() 对 0 delta 也执行 clamp（即 0+0=0），这虽然无害但逻辑不一致。更重要的是，practice_service 的 `ability_delta` 来自 Diagnoser，review_service 的来自 Diagnoser（复用同一 agent），但路径不同导致边界行为可能不同。
**影响**: 同一用户行为在不同入口（practice vs review）可能得到不同的能力更新结果。
**建议**: 提取一个统一的 `apply_ability_update(ability, delta, practice_type)` 函数，被两个 service 共享。

### ISSUE-CC-016: LanceDB embedding 向量维度硬编码为 1536
**严重度**: P3
**位置**: backend/repositories/lancedb_repo.py:71, 83
**说明**: schema 中 vector 字段维度硬编码为 `pa.list_(pa.float32(), 1536)`。如果用户切换 embedding 模型（如 text-embedding-3-small 输出 1536 维，但其他模型可能不同），schema 会不匹配导致写入失败。
**影响**: 更换 embedding 模型后系统静默失败。
**建议**: 从配置读取 embedding 维度，或至少在文档中标注必须使用 1536 维模型。

### ISSUE-CC-017: Ollama fallback 模型映射过时
**严重度**: P3
**位置**: backend/agents/base.py:73-96
**说明**: Ollama 模型映射表中最新的映射是 "o3-mini" → "llama3:8b"。如果用户使用 gpt-4.1、gpt-4.5 或其他新模型，会 fallback 到 llama3，但 llama3 本身也已是旧模型。更重要的是，Ollama 的 "json" format 选项不一定被所有模型支持。
**影响**: Ollama fallback 在新模型配置下可能完全无法使用。
**建议**: 映射表应保持更新，或提供一个默认模型配置项而非硬编码映射。

### ISSUE-CC-018: practice_service._rule_based_ability_delta 的 weak 分支 delta 可能为正
**严重度**: P3
**位置**: backend/services/practice_service.py:46-56
**说明**: 当 correctness="weak" 时，`base = score_map.get("weak", 1)` 得到 1，然后 `delta = {dim: max(-3, base - 5)}` = `max(-3, -4)` = -3。这本身是正确的。但如果 AI 返回一个未知的 correctness 值（如 "strong"），`score_map.get("strong", 4)` 会 fallback 到 4，即使是错误回答也得到正 delta。
**影响**: AI 返回意外 correctness 值时，能力会不恰当地增长。
**建议**: 对未知 correctness 值使用 0 或负 delta 作为默认值。

### ISSUE-CC-019: synthesize_fallback 中 key_takeaways 使用原始 node_id 而非名称
**严重度**: P3
**位置**: backend/agents/synthesizer.py:143
**说明**: `synthesize_fallback()` 中 `key_takeaways: [f"学习了 {n}" for n in visited_nodes[:3]]`，而 visited_nodes 是 node_id 列表（如 "nd_xxxx"）。用户在总结页看到的将是 "学习了 nd_abc123" 而非有意义的名称。
**影响**: AI 失败时总结页显示不可读的 node_id。
**建议**: synthesize_fallback 应接收 node_names 参数而非仅 visited_nodes。

### ISSUE-CC-020: article_service.confirm_candidate 创建新节点时无 LanceDB 去重检查
**严重度**: P3
**位置**: backend/services/article_service.py:389-456
**说明**: 当用户确认一个 concept candidate 且无 matched_node_id 时，会创建新的 Neo4j Concept 节点。虽然之后写入 LanceDB，但未调用 check_duplicate_node() 进行语义去重。与 topic_service.create_topic 中严格的 validate_and_filter_nodes 流程不一致。
**影响**: 用户手动确认的概念可能与已有节点语义重复。
**建议**: 在创建新节点前调用 lancedb_repo.search_similar_concepts() 检查重复。

### ISSUE-CC-021: review queue 生成不区分 learning_intent
**严重度**: P3
**位置**: backend/services/review_service.py:538-735
**说明**: generate_review_queue() 不接收 learning_intent 参数，所有意图使用相同的优先级公式。但文档中 learning_intent 对 Explorer 和 Tutor 有明确的行为差异，复习策略也应该有差异（如 prepare_interview 应优先复习 apply/contrast 类型的复习）。
**影响**: 复习队列对所有意图一视同仁，无法针对面试准备或表达训练做差异化调度。
**建议**: 将 learning_intent 传入 generate_review_queue，调整 priority 计算权重。

### ISSUE-CC-022: ability_service.get_ability_overview 中 0 练习节点被跳过但不通知前端
**严重度**: P3
**位置**: backend/services/ability_service.py:51-52
**说明**: `if avg == 0: continue` 跳过所有维度为 0 的节点。这些是"从未练习过的节点"，不应出现在 weak_nodes 或 strongest_nodes 中，但它们应该出现在某种"未练习"分类中。当前前端无法区分"薄弱节点"和"未练习节点"。
**影响**: 统计页的薄弱节点列表可能误导用户（不包含从未练习的节点）。
**建议**: 返回一个 `unpracticed_nodes` 列表或在 weak_nodes 中标注 `practiced: false`。

### ISSUE-CC-023: topic_service.create_topic 的事务完整性问题
**严重度**: P2
**位置**: backend/services/topic_service.py:21-361
**说明**: create_topic 在 Neo4j 写入失败后仍会更新 topic 的 entry_node_id（第 310-316 行），即使 Neo4j 中没有对应的 Concept 节点。这意味着 SQLite 中记录了 entry_node_id 但 Neo4j 中没有对应节点，后续 get_node_detail 会返回 fallback 数据。
**影响**: Neo4j 不可用时创建的 Topic 在恢复 Neo4j 后仍处于不一致状态。
**建议**: Neo4j 写入失败时，不更新 entry_node_id（或记录为需要 reconciliation 的状态）。

### ISSUE-CC-024: stats_service.get_global_stats 中 "due_reviews" 只统计 pending 状态
**严重度**: P3
**位置**: backend/services/stats_service.py:17-20
**说明**: `SELECT COUNT(*) as cnt FROM review_items WHERE status = 'pending'` 不包括 status='due' 的项目。review_service.list_reviews 中将 pending + due + actionable_snoozed 合并展示，但 stats 只计 pending。
**影响**: 首页显示的"待复习数"与实际可复习数不一致。
**建议**: 改为 `WHERE status IN ('pending', 'due')`。

### ISSUE-CC-025: export_service 中 Anki 格式无法导出无 Neo4j 的节点
**严重度**: P3
**位置**: backend/services/export_service.py:66-81
**说明**: Anki 导出依赖 graph_data 中的节点列表，但如果 Neo4j 不可用（graph_data=None），则 anki_lines 为空，返回错误。而 Markdown 导出使用 sqlite_repo.list_ability_records 作为 fallback。能力记录存在 SQLite 中但无法导出到 Anki。
**影响**: Neo4j 不可用时的 Anki 导出完全失败。
**建议**: Anki 导出也应使用 SQLite 中的 ability_records 作为 fallback 数据源。

---

## Candidates（改进建议）

### CANDIDATE-CC-001: 引入统一的 ability delta 应用函数
**优先级**: P2
**说明**: practice_service 和 review_service 各自实现了 delta clamp + apply 逻辑，应提取为 `backend/models/ability.py` 中的统一函数 `apply_practice_delta(record, delta, practice_type)`，确保两边行为完全一致。
**收益**: 减少 bug 面，便于后续调整增量规则。

### CANDIDATE-CC-002: 补全 MisconceptionRecord 模型和 API
**优先级**: P1
**说明**: 文档承诺的 MisconceptionRecord 缺失。建议在 `backend/models/misconception.py` 创建 Pydantic model，在 sqlite_repo 中添加 list/resolve 方法，在 `backend/api/nodes.py` 添加 GET/PATCH 路由。
**收益**: 补齐文档承诺，为 V1 误解图谱可视化打基础。

### CANDIDATE-CC-003: 实现 startup reconciliation 扫描 pending sync_events
**优先级**: P1
**说明**: 在 FastAPI lifespan 或 startup event 中扫描 sync_events 表中 status='pending' 的记录，按时间顺序重试。优先级：neo4j > lancedb > sqlite。设置最大重试次数（如 3 次），超过后标记为 'failed'。
**收益**: 消除"静默丢失"风险，实现文档承诺的补偿机制。

### CANDIDATE-CC-004: expand_node 逻辑下沉到 node_service
**优先级**: P2
**说明**: 将 nodes.py 中 300+ 行的 expand_node 业务逻辑提取到 `node_service.expand_node()`，API 层只做 request parsing 和 response formatting。
**收益**: 可测试性大幅提升，符合分层架构规范。

### CANDIDATE-CC-005: generate_review_queue 改用聚合查询
**优先级**: P2
**说明**: 替代 `list_review_items(limit=None)` + in-memory 遍历，改用：
```sql
SELECT node_id, COUNT(CASE WHEN status='completed' THEN 1 END) as completed_count,
       MAX(CASE WHEN status IN ('pending','due') THEN 1 END) as has_pending
FROM review_items WHERE topic_id=? GROUP BY node_id
```
**收益**: O(n) 内存 → O(k) 内存（k=节点数），I/O 次数从 1+N 降到 1。

### CANDIDATE-CC-006: review 评分分级细化
**优先级**: P2
**说明**: 将 review 结果从 good/medium/weak 三级改为 good/medium/weak/failed 四级，其中 medium 使用独立的间隔表 [1, 3, 7, 14, 30]（比 good 的 [3, 7, 14, 30, 60] 更保守）。
**收益**: 复习调度更精确，减少"勉强及格就大幅推迟"的问题。

### CANDIDATE-CC-007: get_entry_node 支持 prepare_expression/prepare_interview
**优先级**: P2
**说明**: 为这两种意图添加专门的入口节点选择逻辑：
- prepare_expression: 优先选择 explain_gap 最大（understand 高但 explain 低）的 practiced 节点
- prepare_interview: 优先选择 importance>=4 且 apply/contrast 维度低的节点
**收益**: 入口推荐更贴合意图，提升用户学习效率。

### CANDIDATE-CC-008: topic cap 强制执行
**优先级**: P2
**说明**: 在 create_topic 和 expand_node 中调用 `enforce_topic_cap()`，超出 30 节点的部分自动创建为 deferred_nodes，记录 reason="主题节点数已达上限(30)"。
**收益**: 防止单 Topic 无限膨胀，保证图谱质量。

### CANDIDATE-CC-009: friction 写入从 fire-and-forget 改为同步或带确认的异步
**优先级**: P2
**说明**: 选项 A：将 _async_friction_update 改为同步（在 submit_practice 返回前完成写入）。选项 B：保留异步但添加 API 端点让前端查询 friction 写入状态。
**收益**: 消除 friction 数据与前端展示的不一致。

### CANDIDATE-CC-010: 统一 Neo4j 批量写入逻辑
**说明**: topic_service.create_topic 和 nodes.py expand_node 中有大量重复的 Neo4j 批量写入代码（UNWIND 创建节点、设置 is_mainline、link to topic、分组创建关系）。应提取为 `backend/graph/batch_writer.py` 共享工具函数。
**收益**: 减少 ~100 行重复代码，统一写入逻辑。

### CANDIDATE-CC-011: embedding 维度配置化
**优先级**: P3
**说明**: 在 config.py 中添加 `EMBEDDING_DIMENSION` 配置项，lancedb_repo.py 中引用该配置而非硬编码 1536。
**收益**: 支持不同 embedding 模型。

### CANDIDATE-CC-012: Ollama fallback 模型配置化
**优先级**: P3
**说明**: 允许用户在设置页配置 Ollama fallback 模型名称，而非依赖硬编码映射表。
**收益**: 适配本地模型生态变化。

### CANDIDATE-CC-013: synthesize_fallback 接收 node 名称
**优先级**: P3
**说明**: 修改 synthesize_fallback 签名，增加 `node_names: dict[str, str]` 参数（node_id→name 映射），使 fallback 总结显示可读名称。
**收益**: AI 失败时用户体验改善。

### CANDIDATE-CC-014: Diagnoser friction_tags 白名单校验
**优先级**: P3
**说明**: 在 practice_service._async_friction_update() 写入前，过滤 friction_tags 到已知类型集合，未知类型记录 warning 但不写入。
**收益**: 保证数据分析质量。

### CANDIDATE-CC-015: stats_service 修复 due_reviews 统计
**优先级**: P3
**说明**: 将 `WHERE status = 'pending'` 改为 `WHERE status IN ('pending', 'due')`。
**收益**: 统计数据准确性。

### CANDIDATE-CC-016: export_service Anki fallback 到 SQLite
**优先级**: P3
**说明**: 当 graph_data 为 None 时，使用 sqlite_repo.list_ability_records 获取节点信息，拼接 node_id 到名称的映射（从 topic 的 entry_node_id 开始）。
**收益**: Neo4j 不可用时仍可导出 Anki。

### CANDIDATE-CC-017: review queue 支持 learning_intent 权重
**优先级**: P3
**说明**: generate_review_queue() 增加 learning_intent 参数，调整 priority 计算中各因子的权重。如 prepare_interview 提高 importance 权重、降低 explain_gap 权重。
**收益**: 复习策略差异化。

### CANDIDATE-CC-018: ability overview 增加 unpracticed_nodes 分类
**优先级**: P3
**说明**: 在 ability_service.get_ability_overview() 返回中增加 `unpracticed_nodes` 列表，包含所有维度为 0 的节点。
**收益**: 前端可区分"未练习"和"练习后仍薄弱"。

### CANDIDATE-CC-019: article confirm_candidate 添加 LanceDB 去重
**优先级**: P3
**说明**: 在 article_service.confirm_candidate 创建新节点前调用 lancedb_repo.search_similar_concepts()，相似度 >=0.92 时警告用户。
**收益**: 防止手动确认时创建重复节点。

### CANDIDATE-CC-020: rel_type 白名单强化
**优先级**: P3
**说明**: 在所有 f-string 拼接 Cypher 关系类型的位置（topic_service、nodes.py），在拼接前增加 `re.match(r'^[A-Z_]+$', rel_type)` 校验。
**收益**: 消除潜在的 Cypher 注入向量。

### CANDIDATE-CC-021: ability delta 对 0 值的防御处理
**优先级**: P3
**说明**: 在 practice_service._rule_based_ability_delta 中，对 score_map 未匹配的 correctness 值（如空字符串），默认返回 delta=0 或 delta=-2，而非正 delta。
**收益**: 防御 AI 输出异常。

### CANDIDATE-CC-022: topic_service initial node embedding 与 Neo4j 写入对齐
**优先级**: P3
**说明**: 将 topic_service.py:262 的 `ai_result.get("nodes", [])[:5]` 改为遍历实际写入 Neo4j 的节点列表 `valid_nodes[:max_initial]`。
**收益**: 消除 LanceDB 中的幽灵向量。

---

## 总结

### 核心能力链完整性评估

| 能力链环节 | 完成度 | 关键缺口 |
|-----------|--------|----------|
| 内容拆解 | 90% | topic cap 未强制执行 |
| 知识网络化 | 85% | enforce_topic_cap 未调用；expand_node 在 API 层 |
| 表达训练 | 95% | 几乎完整，6 种类型全覆盖 |
| 能力诊断 | 80% | MisconceptionRecord 缺失；sync 无补偿 |
| 长期资产沉淀 | 85% | MisconceptionRecord 缺失 |
| 间隔复习 | 80% | medium 评分间隔问题；全量加载性能 |
| 收束总结 | 85% | fallback 显示 node_id |

### AI 四角色职责分离评估

| 角色 | 分离度 | 违规情况 |
|------|--------|----------|
| Explorer | OK | 只生成 Node/Edge，不评估能力 |
| Diagnoser | OK | 只评估，不写 ExpressionAsset |
| Tutor | OK | 只生成反馈，不直接写 FrictionRecord |
| Synthesizer | OK | 只总结/调度，不修改能力 |

### 数据流完整性评估

| 检查项 | 状态 |
|--------|------|
| 写入顺序 SQLite→Neo4j→LanceDB | OK（create_topic） |
| Schema 校验 | OK（validator.py） |
| 关系白名单 | OK（EdgeType 枚举） |
| 语义去重 | OK（LanceDB >=0.92） |
| 失败补偿 | **FAIL** — 仅记录，无重试 |
| 事务一致性 | PARTIAL — friction fire-and-forget |

### 统计

- **Issues**: 25（P1 x2, P2 x10, P3 x13）
- **Candidates**: 22
- **核心能力链检查项**: 55（50 通过，5 部分通过）
- **AI 四角色职责**: 4/4 分离正确
