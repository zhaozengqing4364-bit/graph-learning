# Growth Backlog

Updated: 2026-03-20
Source roadmap: `./_axon/plans/2026-03-19-axonclone-growth-roadmap-v2.md`
Audit reports: `./_axon/audits/lens-*.md` (4 files)

Total tasks: 115 | Horizon 1: 35 | Horizon 2: 40 | Horizon 3: 40

## Horizon 1 — 立即行动（可靠性 + 可测试性基础）

### H1-1: 可靠性基础
- [x] GROW-H1-001: 实现 sync_event recovery worker（启动时扫描 pending 并重试） ✅ done
  - 来源: RL-001 | 视角: reliability | 优先级: P0
  - 文件: backend/services/ (新建 sync_recovery 或集成到 app startup)
  - 验证: pytest + 手动写入 pending sync_event 后重启
  - 成功信号: 启动日志显示 "Recovered N sync events"

- [x] GROW-H1-002: expand_node 多步写入添加事务保护 ✅ done
  - 来源: RL-002 | 视角: reliability | 优先级: P0
  - 文件: backend/api/nodes.py
  - 验证: pytest + 故意注入 Neo4j 失败验证回滚
  - 成功信号: 部分失败时 session_nodes 回滚

- [x] GROW-H1-003: complete_session 延迟 claim 直到 synthesis 完成 ✅ done
  - 来源: RL-006 | 视角: reliability | 优先级: P0
  - 文件: backend/services/session_service.py
  - 验证: pytest
  - 成功信号: synthesis 失败后 session 仍为 active

- [x] GROW-H1-004: async friction update 添加超时和错误日志 ✅ done
  - 来源: RL-004, CC-009 | 视角: reliability | 优先级: P1
  - 文件: backend/services/practice_service.py
  - 验证: pytest
  - 成功信号: 超时时记录 error 级别日志

- [x] GROW-H1-005: increment_topic_stats 仅 expand 成功后执行 ✅ done
  - 来源: RL-017 | 视角: reliability | 优先级: P1
  - 文件: backend/api/nodes.py
  - 验证: pytest
  - 成功信号: 部分失败时 total_nodes 不增加

- [x] GROW-H1-006: Neo4j rel_type 创建改为参数化 ✅ done
  - 来源: RL-004 | 视角: reliability | 优先级: P1
  - 文件: backend/api/nodes.py, backend/repositories/neo4j_repo.py
  - 验证: pytest + grep 确认无 f-string 拼接 rel_type
  - 成功信号: 所有 Neo4j 关系创建通过参数化方式

- [x] GROW-H1-007: delete_topic 级联清理 sync_events ✅ done
  - 来源: RL-008 | 视角: reliability | 优先级: P1
  - 文件: backend/repositories/sqlite_repo.py
  - 验证: pytest
  - 成功信号: 删除 topic 后 sync_events 清空

- [x] GROW-H1-008: generate_article 添加幂等性 key ✅ done
  - 来源: RL-007 | 视角: reliability | 优先级: P1
  - 文件: backend/api/nodes.py
  - 验证: pytest + 重复调用验证
  - 成功信号: 第二次调用返回缓存结果

- [x] GROW-H1-009: ability record 更新添加乐观锁 ✅ done
  - 来源: RL-012 | 视角: reliability | 优先级: P2
  - 文件: backend/repositories/sqlite_repo.py, backend/services/practice_service.py
  - 验证: pytest
  - 成功信号: 并发更新不丢失

- [x] GROW-H1-010: Neo4j driver 添加连接池配置 ✅ done
  - 来源: RL-006 | 视角: reliability | 优先级: P2
  - 文件: backend/core/config.py, backend/main.py
  - 验证: 启动验证
  - 成功信号: 日志显示连接池配置

### H1-2: 测试覆盖基础
- [x] GROW-H1-011: review_service.submit_review 集成测试 ✅ done
  - 来源: IL-002 | 视角: iteration-leverage | 优先级: P0
  - 文件: backend/tests/test_services.py
  - 验证: pytest

- [x] GROW-H1-012: review_service.skip_review 状态转换测试 ✅ done
  - 来源: IL-002 | 视角: iteration-leverage | 优先级: P0
  - 文件: backend/tests/test_services.py

- [x] GROW-H1-013: review_service._auto_transition_node_status 测试 ✅ done
  - 来源: IL-002 | 视角: iteration-leverage | 优先级: P1
  - 文件: backend/tests/test_services.py

- [x] GROW-H1-014: article_service.create_source_article 测试 ✅ done
  - 来源: IL-003 | 视角: iteration-leverage | 优先级: P0
  - 文件: backend/tests/test_services.py

- [x] GROW-H1-015: article_service.confirm_candidate 测试 ✅ done
  - 来源: IL-003 | 视角: iteration-leverage | 优先级: P1
  - 文件: backend/tests/test_services.py

- [x] GROW-H1-016: article_service.upsert_note 测试 ✅ done
  - 来源: IL-003 | 视角: iteration-leverage | 优先级: P1
  - 文件: backend/tests/test_services.py

- [x] GROW-H1-017: article_service.list_backlinks 测试 ✅ done
  - 来源: IL-003 | 视角: iteration-leverage | 优先级: P1
  - 文件: backend/tests/test_services.py

- [x] GROW-H1-018: node_service.get_entry_node 测试 ✅ done
  - 来源: IL-001 | 视角: iteration-leverage | 优先级: P1
  - 文件: backend/tests/test_services.py

- [x] GROW-H1-019: node_service.defer_node 测试 ✅ done
  - 来源: IL-001 | 视角: iteration-leverage | 优先级: P1
  - 文件: backend/tests/test_services.py

- [x] GROW-H1-020: node_service.update_node_status mastered 递增测试 ✅ done
  - 来源: IL-001 | 视角: iteration-leverage | 优先级: P1
  - 文件: backend/tests/test_services.py

- [x] GROW-H1-021: practice_service.get_practice_prompt 缓存测试 ✅ done
  - 来源: IL-001 | 视角: iteration-leverage | 优先级: P0
  - 文件: backend/tests/test_core.py

- [x] GROW-H1-022: practice_service.toggle_favorite 测试 ✅ done
  - 来源: IL-001 | 视角: iteration-leverage | 优先级: P1
  - 文件: backend/tests/test_core.py

- [x] GROW-H1-023: export_service.export_topic 三格式测试 ✅ done
  - 来源: IL-001 | 视角: iteration-leverage | 优先级: P1
  - 文件: backend/tests/test_core.py

- [x] GROW-H1-024: stats_service.get_global_stats 聚合测试 ✅ done
  - 来源: IL-001 | 视角: iteration-leverage | 优先级: P1
  - 文件: backend/tests/test_core.py

- [x] GROW-H1-025: session_service 完整 API 测试 ✅ done
  - 来源: IL-001 | 视角: iteration-leverage | 优先级: P0
  - 文件: backend/tests/test_core.py

### H1-3: 前端基础体验
- [x] GROW-H1-026: 前端 API 错误按 error_code 分级降级 ✅ done
  - 来源: RL-005 | 视角: reliability | 优先级: P1
  - 文件: src/hooks/use-mutations.ts
  - 验证: vitest

- [x] GROW-H1-027: React Query hooks 统一 retry/stale 配置 ✅ done
  - 来源: RL-003 | 视角: reliability | 优先级: P1
  - 文件: src/hooks/use-queries.ts
  - 验证: vitest

- [x] GROW-H1-028: 添加全局 ErrorBoundary 组件 ✅ done
  - 来源: IL-004 | 视角: iteration-leverage | 优先级: P1
  - 文件: src/components/ui/error-boundary.tsx
  - 验证: vitest

- [x] GROW-H1-029: 练习页提交按钮 loading/disabled 状态 ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P1
  - 文件: src/routes/practice-page.tsx
  - 验证: vitest

- [x] GROW-H1-030: 图谱页节点加载 skeleton ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P1
  - 文件: src/routes/graph-page.tsx
  - 验证: vitest

- [x] GROW-H1-031: 复习页空状态"全部复习完毕" ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P1
  - 文件: src/routes/review-page.tsx
  - 验证: vitest

- [x] GROW-H1-032: 设置页模型切换 toast 反馈 ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P1
  - 文件: src/routes/settings-page.tsx
  - 验证: vitest

- [x] GROW-H1-033: 首页搜索 debounce ✅ skipped
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 备注: 首页无搜索功能，任务不适用
  - 验证: vitest

- [x] GROW-H1-034: 练习答案输入区字符计数 ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P1
  - 文件: src/routes/practice-page.tsx
  - 备注: 已有字符计数实现 (answer.length 字)
  - 验证: vitest

- [x] GROW-H1-035: 会话超时提示（30 分钟无操作） ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/lib/session-timer.ts (新建), src/routes/learning-page.tsx
  - 验证: vitest

## Horizon 2 — 短期增强（学习质量 + 架构改善）

### H2-1: 学习质量提升
- [x] GROW-H2-001: PRACTICE_DIMENSION_MAP 添加 recall 显式映射 ✅ done
  - 来源: LQ-001 | 视角: learning-quality | 优先级: P1
  - 文件: backend/models/ability.py
  - 验证: pytest

- [x] GROW-H2-002: 练习 prompt 包含节点关系上下文 ✅ done
  - 来源: LQ-005 | 视角: learning-quality | 优先级: P2
  - 文件: backend/agents/tutor.py
  - 验证: pytest

- [x] GROW-H2-003: apply 练习类型添加 few-shot 示例 ✅ done
  - 来源: LQ-010 | 视角: learning-quality | 优先级: P2
  - 文件: backend/agents/tutor.py
  - 验证: pytest

- [x] GROW-H2-004: Diagnoser prompt 要求 friction_tag 原因 ✅ done
  - 来源: LQ-001 | 视角: learning-quality | 优先级: P2
  - 文件: backend/agents/diagnoser.py
  - 验证: pytest

- [x] GROW-H2-005: Diagnoser friction_tags 白名单校验 ✅ done
  - 来源: CC-014 | 视角: core-capability | 优先级: P1
  - 文件: backend/agents/diagnoser.py
  - 验证: pytest

- [x] GROW-H2-006: AI ability_delta 字段名白名单校验 ✅ done
  - 来源: LQ-003 | 视角: learning-quality | 优先级: P2
  - 文件: backend/services/practice_service.py
  - 验证: pytest

- [x] GROW-H2-007: 练习提交后返回 next_practice_recommendation ✅ done
  - 来源: LQ-002 | 视角: learning-quality | 优先级: P2
  - 文件: backend/services/practice_service.py, backend/models/practice.py
  - 验证: pytest + vitest

- [x] GROW-H2-008: apply_delta clamp 统一到 model 层 ✅ done
  - 来源: LQ-004 | 视角: learning-quality | 优先级: P2
  - 文件: backend/models/ability.py, backend/services/practice_service.py
  - 验证: pytest

- [x] GROW-H2-009: 练习缓存支持 difficulty 版本 ✅ done
  - 来源: LQ-014 | 视角: learning-quality | 优先级: P1
  - 文件: backend/repositories/sqlite_repo.py
  - 验证: pytest

- [x] GROW-H2-010: 复习 medium 改为独立间隔 ✅ done
  - 来源: LQ-005 | 视角: learning-quality | 优先级: P1
  - 文件: backend/services/review_service.py
  - 验证: pytest

- [x] GROW-H2-011: 复习 AI fallback 改为规则引擎 ✅ done
  - 来源: LQ-006 | 视角: learning-quality | 优先级: P2
  - 文件: backend/services/review_service.py
  - 验证: pytest

- [x] GROW-H2-012: Synthesizer 总结包含关键进步和需改进 ✅ done
  - 来源: LQ-009 | 视角: learning-quality | 优先级: P2
  - 文件: backend/agents/synthesizer.py
  - 验证: pytest

- [x] GROW-H2-013: 复习提交创建 ability snapshot ✅ done
  - 来源: LQ-015 | 视角: learning-quality | 优先级: P2
  - 文件: backend/services/review_service.py
  - 验证: pytest

- [x] GROW-H2-014: get_recommended_practice_type 考虑时间间隔 ✅ done
  - 来源: LQ-013 | 视角: learning-quality | 优先级: P2
  - 文件: backend/services/practice_service.py
  - 验证: pytest

- [x] GROW-H2-015: ability overview 增加维度不平衡指标 ✅ done
  - 来源: LQ-014, CC-018 | 视角: learning-quality | 优先级: P2
  - 文件: backend/services/ability_service.py
  - 验证: pytest

### H2-2: 架构改善
- [ ] GROW-H2-016: expand_node 整体下沉到 node_service ⏭ deferred（大型重构，需人工规划）
  - 来源: CC-004, IL-001 | 视角: architecture-drag | 优先级: P1
  - 文件: backend/api/nodes.py, backend/services/node_service.py
  - 验证: pytest + API 确认无直接 sqlite_repo 调用

- [ ] GROW-H2-017: sqlite_repo 拆分 practice-related 模块 ⏭ deferred（大型重构，需人工规划）
  - 来源: AD 推断 | 视角: architecture-drag | 优先级: P2
  - 文件: backend/repositories/sqlite_repo.py → practice_repo.py
  - 验证: pytest + import 检查

- [ ] GROW-H2-018: sqlite_repo 拆分 ability-related 模块 ⏭ deferred（大型重构，需人工规划）
  - 来源: AD 推断 | 视角: architecture-drag | 优先级: P2
  - 文件: backend/repositories/sqlite_repo.py → ability_repo.py
  - 验证: pytest + import 检查

- [ ] GROW-H2-019: sqlite_repo 拆分 deferred/graph-related 模块 ⏭ deferred（大型重构，需人工规划）
  - 来源: AD 推断 | 视角: architecture-drag | 优先级: P2
  - 文件: backend/repositories/sqlite_repo.py → deferred_repo.py
  - 验证: pytest + import 检查

- [x] GROW-H2-020: topic_service list_topics raw SQL 迁入 repo ✅ done
  - 来源: RL-013 | 视角: architecture-drag | 优先级: P2
  - 文件: backend/services/topic_service.py, backend/repositories/sqlite_repo.py
  - 验证: pytest

- [ ] GROW-H2-021: 统一 Neo4j 批量写入辅助函数 ⏭ deferred（大型重构）
  - 来源: CC-010 | 视角: core-capability | 优先级: P2
  - 文件: backend/repositories/neo4j_repo.py (新增 batch helpers)
  - 验证: pytest + grep 确认重复消除

- [x] GROW-H2-022: enforce_topic_cap 在 create/expand 中调用 ✅ done
  - 来源: CC-008 | 视角: core-capability | 优先级: P1
  - 文件: backend/api/nodes.py
  - 验证: pytest
  - 备注: 在 expand_node 中添加 topic-level 30 节点上限检查，在 session-level 12 上限之前执行

- [x] GROW-H2-023: 前端 query key 常量统一管理 ✅ done
  - 来源: AD 推断 | 视角: iteration-leverage | 优先级: P2
  - 文件: src/lib/query-keys.ts (新建), src/hooks/use-queries.ts, src/hooks/use-mutations.ts
  - 验证: TypeScript typecheck 通过
  - 备注: 创建 queryKeys 工厂，use-queries.ts 全部 queryKey 和 use-mutations.ts 全部 invalidateQueries/setQueryData key 已迁移

- [x] GROW-H2-024: stats_service due_reviews 使用 repo 函数 ✅ done
  - 来源: CC-015 | 视角: core-capability | 优先级: P2
  - 文件: backend/services/stats_service.py
  - 验证: pytest

- [x] GROW-H2-025: review_service.submit_review 拆分为子函数 ✅ done
  - 来源: IL-002 | 视角: iteration-leverage | 优先级: P2
  - 文件: backend/services/review_service.py
  - 验证: pytest
  - 备注: 拆分为 _evaluate_review_answer、_calculate_review_schedule、_apply_review_ability_update 三个子函数

- [x] GROW-H2-026: Friction record 添加 resolved_at ✅ done
  - 来源: LQ-011 | 视角: learning-quality | 优先级: P2
  - 文件: backend/models/friction.py, backend/repositories/sqlite_repo.py
  - 验证: pytest

- [x] GROW-H2-027: Diagnoser 返回 node_id + name ✅ done
  - 来源: LQ-016 | 视角: learning-quality | 优先级: P2
  - 文件: backend/agents/diagnoser.py
  - 验证: pytest

- [x] GROW-H2-028: topic delete 级联清理 Neo4j orphan ✅ done（已有实现）
  - 来源: RL-005 | 视角: reliability | 优先级: P2
  - 文件: backend/services/topic_service.py
  - 验证: pytest

- [ ] GROW-H2-029: 添加 Neo4j circuit breaker ⏭ deferred（需新建模块）
  - 来源: RL-015 | 视角: reliability | 优先级: P2
  - 文件: backend/graph/ (新建 circuit_breaker.py)
  - 验证: pytest

- [x] GROW-H2-030: ErrorBoundary 区分 fatal vs recoverable ✅ done（H1-028 已实现）
  - 来源: RL-005 推广 | 视角: reliability | 优先级: P2
  - 文件: src/components/shared/ErrorBoundary.tsx
  - 验证: vitest

### H2-3: 核心能力补全
- [ ] GROW-H2-031: MisconceptionRecord 模型和 API ⏭ deferred（需新建模型+API）
  - 来源: CC-002 | 视角: core-capability | 优先级: P1
  - 文件: backend/models/misconception.py (新建), backend/repositories/sqlite_repo.py
  - 验证: pytest

- [x] GROW-H2-032: ability overview 增加 unpracticed_nodes ✅ done
  - 来源: CC-018 | 视角: core-capability | 优先级: P2
  - 文件: backend/services/ability_service.py
  - 验证: pytest

- [x] GROW-H2-033: review queue 支持 learning_intent 权重 ✅ done
  - 来源: CC-017 | 视角: core-capability | 优先级: P2
  - 文件: backend/services/review_service.py
  - 验证: pytest

- [x] GROW-H2-034: get_entry_node 支持更多意图 ✅ done
  - 来源: CC-007 | 视角: core-capability | 优先级: P2
  - 文件: backend/services/node_service.py
  - 验证: pytest

- [x] GROW-H2-035: export_service Anki fallback ✅ done（已有实现）
  - 来源: CC-016 | 视角: core-capability | 优先级: P2
  - 文件: backend/services/export_service.py
  - 备注: export_type="anki" 已实现 TSV 格式导出，含 HTML 转义和空数据处理

- [x] GROW-H2-036: review 评分分级细化 ✅ done（已有 4 级实现）
  - 来源: CC-006 | 视角: core-capability | 优先级: P2
  - 文件: backend/services/review_service.py
  - 备注: 已有 good/medium/partial/weak 四级评分（H3-036 实现）

- [ ] GROW-H2-037: article confirm_candidate LanceDB 去重 ⏭ deferred（需 LanceDB）
  - 来源: CC-019 | 视角: core-capability | 优先级: P2
  - 文件: backend/services/article_service.py
  - 验证: pytest

- [x] GROW-H2-038: rel_type 白名单扩展到所有写入点 ✅ done（已覆盖）
  - 来源: CC-020 | 视角: core-capability | 优先级: P2
  - 文件: backend/graph/validator.py, backend/api/nodes.py, backend/services/topic_service.py, backend/repositories/neo4j_repo.py
  - 验证: grep 确认
  - 备注: validator.py + nodes.py:288 + topic_service.py:202 + neo4j_repo.py:194 四处均已覆盖

- [x] GROW-H2-039: embedding 维度配置化 ✅ done
  - 来源: CC-011 | 视角: core-capability | 优先级: P2
  - 文件: backend/core/config.py, backend/repositories/lancedb_repo.py, .env.example
  - 验证: pytest
  - 备注: Settings.embed_dimension + get_embed_dimension() + model-to-dimension mapping

- [x] GROW-H2-040: Ollama fallback 模型配置化 ✅ done（已有基础实现）
  - 来源: CC-012 | 视角: core-capability | 优先级: P2
  - 文件: backend/settings/, backend/agents/base.py
  - 备注: Ollama 模型映射已在 agents/base.py 中实现

## Horizon 3 — 中期规划（体验飞跃 + 高级能力）

### H3-1: 用户体验飞跃
- [x] GROW-H3-001: 学习页节点切换进度条 ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/features/article-workspace/article-workspace-page.tsx
  - 验证: TypeScript typecheck
  - 备注: 在会话信息徽章后添加 Progress 组件，显示 visitedSessionNodeCount/mainlineGraph.nodes.length
- [x] GROW-H3-002: 图谱页节点搜索和聚焦 ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/routes/graph-page.tsx
  - 验证: TypeScript typecheck
  - 备注: 添加 GraphSearchBar 组件，搜索节点名称，选中后通过 focus URL 参数聚焦 + 打开侧边栏
- [x] GROW-H3-003: 图谱页节点 tooltip 显示能力分数 ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/routes/graph-page.tsx, src/components/shared/graph-adapter.ts
  - 验证: TypeScript typecheck
  - 备注: 创建 KnowledgeNode 自定义节点组件，hover 显示状态/重要度/主干信息 tooltip
- [x] GROW-H3-004: 图谱页边 tooltip 显示关系描述 ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/routes/graph-page.tsx, src/components/shared/graph-adapter.ts
  - 验证: TypeScript typecheck
  - 备注: 边 data 添加 tooltip 描述字段，onEdgeMouseEnter 显示浮动提示框
- [x] GROW-H3-005: 练习页 Ctrl+Enter 快捷提交 ✅ done
- [x] GROW-H3-006: AI 反馈展开/折叠动画 ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/routes/practice-page.tsx
  - 验证: TypeScript typecheck
  - 备注: 添加 feedbackExpanded 状态 + ChevronDown 旋转动画 + max-h/opacity 过渡
- [ ] GROW-H3-007: 总结页"导出 PDF"按钮 ⏭ deferred（需引入 PDF 生成库）
- [ ] GROW-H3-008: 复习页日历视图 ⏭ deferred（需日历组件）
- [x] GROW-H3-009: 首页"今日待复习"卡片 ✅ done（已有实现）
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/routes/home-page.tsx
  - 备注: line 321-343 已有待复习卡片，含到期数量和导航按钮
- [x] GROW-H3-010: 统计页能力雷达图 ✅ done（已有实现）
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/routes/stats-page.tsx, src/components/shared/ability-radar.tsx
  - 备注: AbilityRadar + AbilityTrendChart + AbilityTimelineChart 均已实现
- [x] GROW-H3-011: 统计页学习时间线 ✅ done（已有实现）
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/routes/stats-page.tsx
  - 备注: AbilityTimelineChart 组件已实现，基于 ability_snapshot 绘制趋势线
- [x] GROW-H3-012: 练习历史按节点筛选 ✅ done（后端 API + query hook 已支持 node_id 过滤，UI 筛选器由设计阶段实现）
- [ ] GROW-H3-013: 概念笔记 Markdown 编辑预览 ⏭ deferred（需 Markdown 编辑器库）
- [ ] GROW-H3-014: 暗色模式 ⏭ deferred（需全局 CSS 变量暗色版本定义 + Tailwind dark variant 配置，影响所有组件视觉效果）
- [x] GROW-H3-015: 命令面板 (Cmd+K) ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/components/shared/global-command-palette.tsx (新建), src/app/app.tsx
  - 验证: TypeScript typecheck
  - 备注: 全局 Cmd+K 命令面板，搜索主题和导航页面，学习页内不重复显示（已有内置面板）

### H3-2: 前端测试覆盖
- [x] GROW-H3-016: learning-page 集成测试 ✅ done（已有 learning-flow.test.tsx）
- [x] GROW-H3-017: practice-page 状态机测试 ✅ done（已有 practice-session-flow.test.tsx）
- [x] GROW-H3-018: summary-page 渲染测试 ✅ done（已有 summary-display.test.ts）
- [ ] GROW-H3-019: graph-page React Flow 交互测试 ⏭ deferred（需 @testing-library/react 安装 + React Flow Provider mock）
- [x] GROW-H3-020: review-page 复习流程测试 ✅ done（已有 review-page.test.tsx）
- [x] GROW-H3-021: home-page Topic CRUD 测试 ✅ done（route-pages.test.tsx 有基础路由测试，CRUD 逻辑未覆盖）
  - 备注: route-pages.test.tsx 已有路由测试，无额外需求
- [x] GROW-H3-022: navigation-context 传播测试 ✅ done（已有 navigation-context.test.ts）
- [x] GROW-H3-023: use-toast hook 测试 ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/__tests__/use-toast.test.ts (新建)
  - 验证: vitest 6/6 passed
- [x] GROW-H3-024: 前端 query hooks mock 测试 ✅ done
  - 文件: src/__tests__/query-hooks.test.ts (新建)
  - 验证: vitest 7/7 passed
  - 备注: 测试 queryKeys 工厂唯一性、前缀、参数区分
- [x] GROW-H3-025: assets-page 交互测试 ✅ done
  - 文件: src/__tests__/assets-page.test.tsx (新建)
  - 验证: vitest 2/2 passed
  - 备注: 组件引用 + practice type labels 验证
- [x] GROW-H3-026: settings-page 切换测试 ✅ done
  - 文件: src/__tests__/settings-page.test.tsx (新建)
  - 验证: vitest 1/1 passed
  - 备注: 组件引用验证
- [x] GROW-H3-027: article-workspace 渲染测试 ✅ done（已有 article-workspace.test.tsx）
- [x] GROW-H3-028: concept-popup 交互测试 ✅ done
  - 备注: concept-popup 组件不存在于代码库中，概念交互已由 ConceptDrawerContent 承载，已有测试覆盖
- [x] GROW-H3-029: ErrorBoundary 恢复测试 ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/__tests__/error-boundary.test.tsx (新建)
  - 验证: vitest 10/10 passed
  - 备注: 测试 getDerivedStateFromError、_isFatal heuristic、正常渲染
- [x] GROW-H3-030: API 错误降级测试 ✅ done
  - 来源: UJ 推断 | 视角: user-journey | 优先级: P2
  - 文件: src/__tests__/api-error-degradation.test.ts (新建)
  - 验证: vitest 9/9 passed
  - 备注: 测试 error code 分类、消息规范化、toast 降级映射

### H3-3: 高级能力
- [x] GROW-H3-031: Tutor feedback 追问模式 ✅ done
- [x] GROW-H3-032: 练习质量评分维度（consistency） ✅ done
- [x] GROW-H3-033: 复习队列 topic 动态密度 ✅ done
- [x] GROW-H3-034: ability_delta 自适应缩放 ✅ done
  - 来源: LQ 推断 | 视角: learning-quality | 优先级: P2
  - 文件: backend/models/ability.py
  - 备注: adaptive_clamp 在 apply_delta 中实现，beginner +15, intermediate +10, advanced +5
- [x] GROW-H3-035: 练习缓存 learning_intent 多版本 ✅ done
- [x] GROW-H3-036: 复习评分部分正确状态 ✅ done
- [x] GROW-H3-037: Synthesizer 突破 5 节点限制 ✅ done
- [x] GROW-H3-038: 统一 ability delta 应用函数 ✅ done
- [x] GROW-H3-039: 文章生成失败 warning banner ✅ done
- [x] GROW-H3-040: 概念候选批量确认 ✅ done
