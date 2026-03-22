# 增长路线图 — AxonClone v2

> 生成时间：2026-03-19
> 分析方式：4/6 Agent Teams 并行审计（user-journey、architecture-drag 超时，由主进程补充）
> 审计来源：lens-core-capability (25 issues), lens-reliability (23 issues), lens-learning-quality (22 issues), lens-iteration-leverage (20 issues)

## 当前判断
- 项目阶段：MVP 功能基本完整，核心循环可用但可靠性不足
- 最关键问题：sync_event 补偿机制未实现（CLAUDE.md 承诺但代码未兑现）、expand_node 300 行 API 层 inline 逻辑、测试覆盖率严重不足
- 主要矛盾：功能已基本完整，但可靠性（写入一致性）和可测试性（让未来改动更安全）成为主要瓶颈

## 保留项
- AI 四角色职责分离架构（Explorer/Diagnoser/Tutor/Synthesizer）
- 三库写入顺序 SQLite → Neo4j → LanceDB
- 练习类型序列 define → example → contrast → apply → teach_beginner → compress
- 能力 8 维评分增量规则
- API/Service/Repository 三层分离
- React Query vs Zustand 状态管理边界

## 审计发现汇总

| 视角 | 问题数 | 候选数 | 最高优先级 |
|------|--------|--------|-----------|
| 核心能力 | 25 | 22 | enforce_topic_cap 未调用、MisconceptionRecord 缺失 |
| 可靠性 | 23 | 18 | sync_event 无消费者（P0）、expand_node 无事务（P0）|
| 学习质量 | 22 | 16 | 复习 medium 算 success、练习缓存不分 difficulty |
| 迭代杠杆 | 20 | 0 | expand_node 300行单体、review_service 几乎零测试 |

## 路线图

### Horizon 1 — 立即行动（可靠性 + 可测试性基础）

影响最大、验证最快、风险最小的改动。

#### H1-1: 可靠性基础（10 个任务）
- [ ] GROW-H1-001: 实现 sync_event recovery worker — 启动时扫描 pending sync_events 并重试
- [ ] GROW-H1-002: expand_node 多步写入添加事务保护 — SQLite 部分用 BEGIN/COMMIT
- [ ] GROW-H1-003: complete_session 延迟 claim 直到 synthesis 完成
- [ ] GROW-H1-004: async friction update 添加超时和错误日志
- [ ] GROW-H1-005: increment_topic_stats 在 expand 中仅成功后执行
- [ ] GROW-H1-006: Neo4j rel_type 创建改为参数化（消除 f-string 拼接风险）
- [ ] GROW-H1-007: delete_topic 级联清理 sync_events 表
- [ ] GROW-H1-008: generate_article 添加幂等性 key
- [ ] GROW-H1-009: ability record 更新添加乐观锁
- [ ] GROW-H1-010: Neo4j driver 添加连接池配置

#### H1-2: 测试覆盖基础（15 个任务）
- [ ] GROW-H1-011: review_service.submit_review 集成测试
- [ ] GROW-H1-012: review_service.skip_review 状态转换测试
- [ ] GROW-H1-013: review_service._auto_transition_node_status 测试
- [ ] GROW-H1-014: article_service.create_source_article 测试
- [ ] GROW-H1-015: article_service.confirm_candidate 测试
- [ ] GROW-H1-016: article_service.upsert_note 测试
- [ ] GROW-H1-017: article_service.list_backlinks 测试
- [ ] GROW-H1-018: node_service.get_entry_node 测试
- [ ] GROW-H1-019: node_service.defer_node 测试
- [ ] GROW-H1-020: node_service.update_node_status mastered 递增测试
- [ ] GROW-H1-021: practice_service.get_practice_prompt 缓存命中/未命中测试
- [ ] GROW-H1-022: practice_service.toggle_favorite 测试
- [ ] GROW-H1-023: export_service.export_topic markdown/json/anki 三格式测试
- [ ] GROW-H1-024: stats_service.get_global_stats 聚合测试
- [ ] GROW-H1-025: session_service API 层完整测试（create/complete/claim）

#### H1-3: 前端基础体验（10 个任务）
- [ ] GROW-H1-026: 前端 API 错误处理按 error_code 分级降级
- [ ] GROW-H1-027: React Query hooks 添加统一的 retry/stale 配置
- [ ] GROW-H1-028: 添加全局 ErrorBoundary 组件
- [ ] GROW-H1-029: 练习页提交按钮添加 loading/disabled 状态
- [ ] GROW-H1-030: 图谱页添加节点加载 skeleton
- [ ] GROW-H1-031: 复习页空状态添加"全部复习完毕"插图
- [ ] GROW-H1-032: 设置页模型切换后 toast 反馈确认
- [ ] GROW-H1-033: 首页搜索 debounce 优化
- [ ] GROW-H1-034: 练习页答案输入区添加字符计数
- [ ] GROW-H1-035: 会话超时提示（30 分钟无操作）

### Horizon 2 — 短期增强（学习质量 + 架构改善）

#### H2-1: 学习质量提升（15 个任务）
- [ ] GROW-H2-001: PRACTICE_DIMENSION_MAP 显式添加 recall 映射
- [ ] GROW-H2-002: 练习 prompt 包含节点关系上下文（前驱/对比/应用）
- [ ] GROW-H2-003: apply 练习类型添加 few-shot 示例
- [ ] GROW-H2-004: Diagnoser prompt 要求对每个 friction_tag 提供原因
- [ ] GROW-H2-005: Diagnoser friction_tags 白名单校验
- [ ] GROW-H2-006: AI ability_delta 字段名白名单校验 + warning 日志
- [ ] GROW-H2-007: 练习提交后返回 next_practice_recommendation
- [ ] GROW-H2-008: apply_delta clamp 逻辑统一到 model 层
- [ ] GROW-H2-009: 练习缓存支持 difficulty 参数版本
- [ ] GROW-H2-010: 复习 medium 改为独立间隔（不视为 success）
- [ ] GROW-H2-011: 复习 AI fallback 改为规则引擎（替代字符长度）
- [ ] GROW-H2-012: Synthesizer 总结包含"最关键进步"和"最需改进"
- [ ] GROW-H2-013: 复习提交创建 ability snapshot
- [ ] GROW-H2-014: get_recommended_practice_type 考虑时间间隔
- [ ] GROW-H2-015: ability overview 增加维度不平衡指标

#### H2-2: 架构改善（15 个任务）
- [ ] GROW-H2-016: expand_node 300 行逻辑整体下沉到 node_service
- [ ] GROW-H2-017: sqlite_repo 继续拆分（practice-related 模块）
- [ ] GROW-H2-018: sqlite_repo 继续拆分（ability-related 模块）
- [ ] GROW-H2-019: sqlite_repo 继续拆分（deferred/graph-related 模块）
- [ ] GROW-H2-020: topic_service.list_topics 中的 raw SQL 迁入 repo 层
- [ ] GROW-H2-021: 统一 Neo4j 批量写入辅助函数（消除重复 UNWIND 代码）
- [ ] GROW-H2-022: enforce_topic_cap 在 create_topic 和 expand_node 中调用
- [ ] GROW-H2-023: 前端 query key 常量统一管理
- [ ] GROW-H2-024: stats_service due_reviews 使用 repo 层函数
- [ ] GROW-H2-025: review_service.submit_review 拆分为更小的子函数
- [ ] GROW-H2-026: Friction record 添加 resolved_at 字段
- [ ] GROW-H2-027: Diagnoser suggested_prerequisite_nodes 返回 node_id + name
- [ ] GROW-H2-028: topic delete 级联清理 Neo4j orphan 检测
- [ ] GROW-H2-029: 添加 Neo4j circuit breaker 模式
- [ ] GROW-H2-030: 前端 ErrorBoundary 区分 fatal vs recoverable

#### H2-3: 核心能力补全（10 个任务）
- [ ] GROW-H2-031: MisconceptionRecord 模型和 API 实现
- [ ] GROW-H2-032: ability overview 增加 unpracticed_nodes 分类
- [ ] GROW-H2-033: review queue 支持 learning_intent 权重
- [ ] GROW-H2-034: get_entry_node 支持 prepare_expression/prepare_interview 意图
- [ ] GROW-H2-035: export_service Anki fallback 到 SQLite 数据
- [ ] GROW-H2-036: review 评分分级细化（good/medium/weak 三级间隔）
- [ ] GROW-H2-037: article confirm_candidate 添加 LanceDB 去重
- [ ] GROW-H2-038: rel_type 白名单从 validator 扩展到所有写入点
- [ ] GROW-H2-039: embedding 维度配置化（settings API）
- [ ] GROW-H2-040: Ollama fallback 模型配置化

### Horizon 3 — 中期规划（体验飞跃 + 高级能力）

#### H3-1: 用户体验飞跃（15 个任务）
- [ ] GROW-H3-001: 学习页添加节点切换进度条（已学习 N/total）
- [ ] GROW-H3-002: 图谱页支持节点搜索和聚焦
- [ ] GROW-H3-003: 图谱页节点 tooltip 显示能力分数
- [ ] GROW-H3-004: 图谱页边关系 tooltip 显示关系描述
- [ ] GROW-H3-005: 练习页支持快捷键提交（Ctrl+Enter）
- [ ] GROW-H3-006: 练习页添加 AI 反馈的展开/折叠动画
- [ ] GROW-H3-007: 总结页添加"导出为 PDF"按钮
- [ ] GROW-H3-008: 复习页添加日历视图
- [ ] GROW-H3-009: 首页添加"今日待复习"卡片
- [ ] GROW-H3-010: 统计页添加能力雷达图
- [ ] GROW-H3-011: 统计页添加学习时间线
- [ ] GROW-H3-012: 练习历史页面支持按节点筛选
- [ ] GROW-H3-013: 概念笔记支持 Markdown 编辑和预览
- [ ] GROW-H3-014: 暗色模式支持（跟随系统）
- [ ] GROW-H3-015: 键盘快捷键系统（Cmd+K 命令面板）

#### H3-2: 前端测试覆盖（15 个任务）
- [ ] GROW-H3-016: learning-page 集成测试
- [ ] GROW-H3-017: practice-page 状态机测试
- [ ] GROW-H3-018: summary-page 渲染测试
- [ ] GROW-H3-019: graph-page React Flow 交互测试
- [ ] GROW-H3-020: review-page 复习流程测试
- [ ] GROW-H3-021: home-page Topic CRUD 测试
- [ ] GROW-H3-022: navigation-context sessionId 传播测试
- [ ] GROW-H3-023: use-toast hook 测试
- [ ] GROW-H3-024: 前端 query hooks 端到端 mock 测试
- [ ] GROW-H3-025: assets-page 收藏/删除交互测试
- [ ] GROW-H3-026: settings-page 模型切换测试
- [ ] GROW-H3-027: article-workspace 文章渲染测试
- [ ] GROW-H3-028: concept-popup 弹出交互测试
- [ ] GROW-H3-029: ErrorBoundary 触发和恢复测试
- [ ] GROW-H3-030: 前端 API 错误降级统一测试

#### H3-3: 高级能力（10 个任务）
- [ ] GROW-H3-031: Tutor feedback 支持"追问"模式（连续对话）
- [ ] GROW-H3-032: 引入"练习质量评分"维度（consistency）
- [ ] GROW-H3-033: 复习队列按 topic 进度动态调整密度
- [ ] GROW-H3-034: ability_delta 基于当前分数自适应缩放
- [ ] GROW-H3-035: 练习缓存支持 learning_intent 多版本
- [ ] GROW-H3-036: review 评分支持"部分正确"中间状态
- [ ] GROW-H3-037: Synthesizer 突破前 5 节点限制
- [ ] GROW-H3-038: 统一 ability delta 应用函数（消除双重 clamp）
- [ROW-H3-039: 节点文章生成失败时显示 warning banner
- [ ] GROW-H3-040: 概念候选批量确认功能

## 下一批 safe-grow 候选（Top 10）

| # | 候选 | 来源 | 涉及文件 |
|---|------|------|----------|
| 1 | sync_event recovery worker | RL-001 | backend/services/ |
| 2 | expand_node 事务保护 | RL-002 | backend/api/nodes.py |
| 3 | complete_session 延迟 claim | RL-006 | backend/services/session_service.py |
| 4 | expand_node 下沉到 service | CC-004, IL-001 | backend/api/nodes.py, node_service.py |
| 5 | PRACTICE_DIMENSION_MAP 添加 recall | LQ-001 | backend/models/ability.py |
| 6 | 复习 medium 改独立间隔 | LQ-005 | backend/services/review_service.py |
| 7 | 前端 error_code 分级降级 | RL-005 | src/lib/ |
| 8 | review_service.submit_review 测试 | IL-002 | backend/tests/ |
| 9 | Neo4j rel_type 参数化 | RL-004 | backend/api/nodes.py |
| 10 | 练习缓存支持 difficulty | LQ-014 | backend/services/practice_service.py |

## 反目标

- 不要做"为了整洁"的纯重构（除非直接影响核心价值交付）
- 不要引入新的数据库或消息队列（在 SQLite/Neo4j/LanceDB 范围内解决）
- 不要重写 AI prompt 模板（在现有基础上增量改进）
- 不要添加多用户/云端功能（MVP 不做）
- 不要过度工程化 retry/circuit-breaker（优先简单可靠方案）

## 落地方式
- 路线图文件：./_axon/plans/2026-03-19-axonclone-growth-roadmap-v2.md
- 详细审计：./_axon/audits/lens-*.md（4 份）
- 执行方式：`/axsafe` 或 `/loop 3m /axsafe`
- 规划新任务：`axon-plan` → `/loop 3m /axon`
