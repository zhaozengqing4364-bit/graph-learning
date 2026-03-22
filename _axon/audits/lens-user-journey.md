# 用户旅程审计报告 (User Journey Audit)

> 审计日期: 2026-03-19
> 审计范围: AxonClone 前端全链路 (src/routes, src/features, src/components, src/stores, src/hooks)
> 审计视角: 用户从打开应用到完成学习的完整路径

---

## 用户旅程总览

```
首页(创建/恢复主题) → 学习页(文章阅读/概念展开) → 练习页(表达训练) → 总结页(收束) → 复习页(间隔复习)
                              ↕
                        图谱页(结构浏览)
                              ↕
                        资产页(表达回顾)
                              ↕
                        统计页(成长诊断)
```

---

## 问题列表 (ISSUES)

### ISSUE-UJ-001: 首页创建主题时缺少内容长度提示
- **用户场景**: 用户粘贴了一篇很长的文章，不知道是否超限
- **影响程度**: 低
- **问题详情**: textarea 有 maxLength=500000 但没有字符计数，用户无法知道已输入多少内容。创建时 AI 分析可能需要 10-30 秒，但没有任何进度指示（仅文字提示）
- **涉及文件**: `src/routes/home-page.tsx:103-117`
- **当前表现**: textarea 无字符计数，创建按钮旁有提示文字但无进度条
- **理想表现**: 显示字符计数（如 "1,234 / 500,000"），创建时显示进度或更详细的等待状态
- **最小修复方案**: 在 textarea 下方添加字符计数，使用与 practice-page 类似的 `{content.length} 字` 显示
- **修复文件**: `src/routes/home-page.tsx`
- **验证方式**: 粘贴文本后观察字符计数是否显示
- **成功信号**: 用户能看到输入了多少字符
- **影响半径**: 无
- **得分**: user_leverage:2, core_capability:1, evidence:5, compounding:1, validation_ease:5, blast_radius:1

### ISSUE-UJ-002: 首页"继续学习"仅展示第一个主题
- **用户场景**: 用户有多个活跃主题，想快速切换到非最近的一个
- **影响程度**: 中
- **问题详情**: "继续学习"面板始终指向 `recentTopics[0]`，无法选择其他主题继续
- **涉及文件**: `src/routes/home-page.tsx:278-298`
- **当前表现**: 固定显示第一个主题的卡片，只有一个"继续"按钮
- **理想表现**: 支持选择最近 2-3 个主题，或直接使用列表卡片的箭头入口
- **最小修复方案**: 移除单独的"继续学习"面板（与列表卡片功能重复），或在面板中添加下拉选择器
- **修复文件**: `src/routes/home-page.tsx`
- **验证方式**: 有多个主题时查看"继续学习"面板是否支持选择
- **成功信号**: 用户能快速选择要继续的主题
- **影响半径**: 无
- **得分**: user_leverage:3, core_capability:1, evidence:5, compounding:2, validation_ease:4, blast_radius:1

### ISSUE-UJ-003: 首页待学堆栈和最近练习无链接到 topicId
- **用户场景**: 用户在首页看到"待学堆栈"或"最近练习"，点击后可能导航到错误的主题
- **影响程度**: 中
- **问题详情**: 这两个面板使用 `currentTopicId`（即 recentTopics[0].topic_id）来构建链接。如果用户在首页看到的是另一个主题的待学节点，但实际 topicId 是第一个主题的，导致导航错误
- **涉及文件**: `src/routes/home-page.tsx:64-66, 346-379`
- **当前表现**: `useDeferredNodesQuery(currentTopicId)` 和 `usePracticeAttemptsQuery(currentTopicId)` 总是使用第一个主题
- **理想表现**: 只显示当前活跃主题的待学和练习，或支持切换主题查看
- **最小修复方案**: 在面板标题旁显示所属主题名称，或合并到主题卡片中
- **修复文件**: `src/routes/home-page.tsx`
- **验证方式**: 创建两个主题，在两个主题都有待学节点时查看首页面板
- **成功信号**: 用户能识别待学节点属于哪个主题
- **影响半径**: 无
- **得分**: user_leverage:3, core_capability:1, evidence:4, compounding:1, validation_ease:3, blast_radius:1

### ISSUE-UJ-004: 学习页加载状态信息不足
- **用户场景**: 用户从首页创建主题后跳转到学习页，看到一个"正在展开文章工作台..."的纯文字
- **影响程度**: 中
- **问题详情**: 学习页加载时仅显示一个居中文字提示，没有 skeleton 加载骨架、没有进度指示、没有超时处理。如果 API 慢或超时，用户不知道是在加载还是已经卡死
- **涉及文件**: `src/features/article-workspace/article-workspace-page.tsx:1374-1382`
- **当前表现**: 一个圆角卡片中显示"正在展开文章工作台…"，无其他反馈
- **理想表现**: 使用 LoadingSkeleton + 文字提示 + 超时自动重试/刷新按钮
- **最小修复方案**: 添加 skeleton 骨架或 spinner 动画，超过 10 秒显示刷新按钮
- **修复文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **验证方式**: 创建新主题后观察加载态
- **成功信号**: 用户能感知系统在工作，且在长时间无响应时有刷新选项
- **影响半径**: 无
- **得分**: user_leverage:4, core_capability:1, evidence:5, compounding:2, validation_ease:4, blast_radius:1

### ISSUE-UJ-005: 学习页错误状态无法区分主题不存在和网络错误
- **用户场景**: 用户直接访问一个无效的 topicId URL
- **影响程度**: 低
- **问题详情**: 错误状态只显示 "加载失败" + 错误消息，没有引导用户返回首页或重新创建
- **涉及文件**: `src/features/article-workspace/article-workspace-page.tsx:1384-1403`
- **当前表现**: 显示错误消息 + "清理本地状态"和"重试"两个按钮
- **理想表现**: 区分 404 和网络错误，404 时提供"返回首页"按钮，网络错误时提供重试
- **最小修复方案**: 添加"返回首页"按钮，区分错误类型
- **修复文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **验证方式**: 手动修改 URL topicId 为无效值，观察错误页面
- **成功信号**: 用户能快速回到正常流程
- **影响半径**: 无
- **得分**: user_leverage:2, core_capability:1, evidence:3, compounding:1, validation_ease:4, blast_radius:1

### ISSUE-UJ-006: 学习页没有全局 ErrorBoundary
- **用户场景**: 学习页渲染过程中发生 JS 错误（如 API 返回异常数据格式）
- **影响程度**: 高
- **问题详情**: 虽然有顶层 ErrorBoundary（app.tsx），但学习页是一个 ~1700 行的巨型组件，任何子组件错误都会导致整个学习页崩溃。没有页面级别的 ErrorBoundary 来隔离故障
- **涉及文件**: `src/app/app.tsx:26-53`, `src/features/article-workspace/article-workspace-page.tsx`
- **当前表现**: 任何 JS 错误都会显示全局 ErrorBoundary 的 "页面出现了意外错误"
- **理想表现**: 学习页有自己的 ErrorBoundary，崩溃时保留侧边栏和导航
- **最小修复方案**: 在 ArticleWorkspacePage 外层包一个 ErrorBoundary，fallback 提供回到首页的链接
- **修复文件**: `src/routes/learning-page.tsx`
- **验证方式**: 在组件中模拟 throw new Error() 观察崩溃表现
- **成功信号**: 学习页崩溃后用户仍能看到侧边栏导航，能返回首页
- **影响半径**: 学习页
- **得分**: user_leverage:4, core_capability:2, evidence:4, compounding:3, validation_ease:5, blast_radius:2

### ISSUE-UJ-007: 文章工作区概念专文无 article_body 时的体验断裂
- **用户场景**: 用户点击一个还没有生成专文的概念节点
- **影响程度**: 高
- **问题详情**: 当概念的 article_body 为空时，系统自动触发 AI 生成，但没有明确的"生成中"UI 反馈。用户看到的是：摘要区域显示 summary，但 article renderer 因为 body 为空直接返回 null（ArticleRenderer:283 `if (!body) return null`），页面下半部分突然空白
- **涉及文件**: `src/components/shared/article-renderer.tsx:283`, `src/features/article-workspace/article-workspace-page.tsx:959-989`
- **当前表现**: 文章区域空白，没有加载指示器。用户不知道文章正在生成
- **理想表现**: 显示"文章正在生成中..."的 skeleton 或 spinner，生成完成后自动替换
- **最小修复方案**: 在 ArticleRenderer 中添加 body 为空时的 loading 占位，或在 workspace-page 中检测生成状态并显示占位
- **修复文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **验证方式**: 点击一个新概念节点，观察空白区域
- **成功信号**: 用户能看到"正在生成专文"的明确反馈
- **影响半径**: 学习页概念浏览
- **得分**: user_leverage:5, core_capability:3, evidence:5, compounding:4, validation_ease:4, blast_radius:2

### ISSUE-UJ-008: 文章工作区"标记完成"行为不透明
- **用户场景**: 用户阅读完一篇文章后点击"标记完成"
- **影响程度**: 中
- **问题详情**: 点击"标记完成"后，如果设置了 auto_start_practice，会自动跳转到练习页。用户可能不理解为什么突然跳转。如果没有设置，则什么都不发生（只是 toast），没有引导用户去下一篇
- **涉及文件**: `src/features/article-workspace/article-workspace-page.tsx:1095-1142`
- **当前表现**: toast 提示"已标记为完成"，然后可能自动跳转或无后续动作
- **理想表现**: "标记完成"后显示下一步选项：去下一篇/去练习/返回首页，而不是自动执行
- **最小修复方案**: 在标记完成后的 toast 中包含"点击查看下一篇"的链接，或禁用自动跳转改为提示
- **修复文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **验证方式**: 开启 auto_start_practice 后点击"标记完成"
- **成功信号**: 用户理解为什么跳转到练习页，或能看到下一步选择
- **影响半径**: 学习→练习转换
- **得分**: user_leverage:4, core_capability:2, evidence:5, compounding:3, validation_ease:3, blast_radius:2

### ISSUE-UJ-009: 练习页从学习页跳转后 nodeId 参数缺失
- **用户场景**: 用户在学习页点击"去练习"按钮
- **影响程度**: 低
- **问题详情**: 如果当前没有选中具体的概念节点（例如在 guide 页面或 source 文章页面），`practiceRoute` 会是 null（`src/features/article-workspace/article-workspace-page.tsx:1416-1418`），"去练习"按钮不会渲染。用户可能不理解为什么没有练习入口
- **涉及文件**: `src/features/article-workspace/article-workspace-page.tsx:1416-1418, 1476-1481`
- **当前表现**: 没有 nodeId 时不显示"去练习"按钮
- **理想表现**: 显示但禁用，或引导用户先选择一个概念节点
- **最小修复方案**: 始终显示"去练习"按钮，没有 nodeId 时禁用并显示 tooltip 提示"请先选择一个概念节点"
- **修复文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **验证方式**: 在 guide 页面查看工具栏
- **成功信号**: 用户能看到练习入口并理解为什么不可用
- **影响半径**: 无
- **得分**: user_leverage:2, core_capability:1, evidence:4, compounding:1, validation_ease:5, blast_radius:1

### ISSUE-UJ-010: 练习页答案草稿不跨会话持久化
- **用户场景**: 用户在练习页写了很长的回答，不小心刷新页面
- **影响程度**: 高
- **问题详情**: 练习页的答案草稿存储在 Zustand 的 `practice_draft` 中，但 `partialize` 仅持久化 `sidebar_collapsed` 和 `graph_view`（`src/stores/app-store.ts:111-114`）。刷新页面后草稿丢失
- **涉及文件**: `src/stores/app-store.ts:111-114`, `src/routes/practice-page.tsx:92-97`
- **当前表现**: 刷新页面后已写的回答消失
- **理想表现**: 答案草稿应持久化到 localStorage（类似 review-page 的实现，`src/routes/review-page.tsx:35-48`）
- **最小修复方案**: 将 `practice_draft` 加入 `partialize`，或在 practice-page 中使用 localStorage 直接读写（与 review-page 保持一致）
- **修复文件**: `src/stores/app-store.ts` 或 `src/routes/practice-page.tsx`
- **验证方式**: 在练习页输入文字后刷新页面
- **成功信号**: 刷新后文字仍然存在
- **影响半径**: 练习页
- **得分**: user_leverage:5, core_capability:2, evidence:5, compounding:3, validation_ease:5, blast_radius:1

### ISSUE-UJ-011: 练习页"提交失败"后答案可能丢失
- **用户场景**: 用户写了长回答后提交，网络错误导致提交失败
- **影响程度**: 中
- **问题详情**: 提交失败时 `setPracticeState('answering')` 回到回答状态，但 `answer` 变量仍然保持，所以答案不会丢失。但如果用户在 submitting 状态下刷新页面，答案会丢失（同 ISSUE-UJ-010）
- **涉及文件**: `src/routes/practice-page.tsx:172-197`
- **当前表现**: 提交失败后回到 answering 状态，答案保留。但 submitting 期间刷新页面会丢失
- **理想表现**: submitting 期间也应保存草稿
- **最小修复方案**: 同 ISSUE-UJ-010 的修复
- **修复文件**: 同上
- **验证方式**: 同上
- **成功信号**: 同上
- **影响半径**: 同上
- **得分**: user_leverage:4, core_capability:2, evidence:4, compounding:3, validation_ease:5, blast_radius:1

### ISSUE-UJ-012: 练习页从 completed 状态无路返回查看反馈
- **用户场景**: 用户保存表达资产后（completed 状态），想回看刚才的反馈
- **影响程度**: 低
- **问题详情**: completed 状态显示"表达资产已保存"卡片，有"继续练习"和"返回学习"按钮，但没有"查看反馈"按钮。如果用户想复习刚才的反馈内容，需要重新做一题
- **涉及文件**: `src/routes/practice-page.tsx:655-708`
- **当前表现**: completed 状态只有继续练习和返回学习两个选项
- **理想表现**: 添加"查看反馈"按钮，点击后回到 feedback_ready 状态
- **最小修复方案**: 在 completed 状态添加一个"查看反馈"按钮，设置 `setPracticeState('feedback_ready')` 和恢复 feedback 状态
- **修复文件**: `src/routes/practice-page.tsx`
- **验证方式**: 完成一次练习并保存资产后，尝试查看反馈
- **成功信号**: 用户能回到反馈页面回顾
- **影响半径**: 练习页
- **得分**: user_leverage:2, core_capability:1, evidence:4, compounding:1, validation_ease:5, blast_radius:1

### ISSUE-UJ-013: 练习页 completed 后自动跳转总结页可能令人困惑
- **用户场景**: 用户想继续做多道练习，但系统自动跳转到总结页
- **影响程度**: 中
- **问题详情**: 当 `practice_state === 'completed'` 且 `sessionCompletionIntent.type === 'summary'` 时，自动触发 `handleCompleteSession`。用户保存一次资产后就被迫跳转总结，无法继续练习
- **涉及文件**: `src/routes/practice-page.tsx:253-259`
- **当前表现**: 保存资产后自动跳转总结页
- **理想表现**: 自动跳转改为可选，或在跳转前显示提示"是否结束本轮？"
- **最小修复方案**: 添加延迟或显示确认对话框，而非立即自动跳转
- **修复文件**: `src/routes/practice-page.tsx`
- **验证方式**: 保存资产后观察是否自动跳转
- **成功信号**: 用户有选择是否结束本轮的权利
- **影响半径**: 练习→总结转换
- **得分**: user_leverage:4, core_capability:2, evidence:5, compounding:3, validation_ease:4, blast_radius:2

### ISSUE-UJ-014: 练习页没有显示当前练习的进度
- **用户场景**: 用户想了解自己在推荐练习序列中的位置
- **影响程度**: 低
- **问题详情**: 练习页顶部显示推荐顺序（define → example → contrast → apply → teach_beginner → compress），但没有标注已完成哪些类型。`practiceAttempts` 数据已经可用但没有用于高亮已完成步骤
- **涉及文件**: `src/routes/practice-page.tsx:418-432`
- **当前表现**: 推荐顺序中只有当前类型加粗，已完成类型没有标记
- **理想表现**: 已完成类型显示绿色对勾
- **最小修复方案**: 使用 practiceAttempts 数据在推荐顺序中标记已完成类型
- **修复文件**: `src/routes/practice-page.tsx`
- **验证方式**: 完成多道练习后查看推荐顺序
- **成功信号**: 已完成类型有视觉标记
- **影响半径**: 无
- **得分**: user_leverage:2, core_capability:1, evidence:4, compounding:1, validation_ease:5, blast_radius:1

### ISSUE-UJ-015: 练习页 textarea 无自动高度计算导致体验差
- **用户场景**: 用户在练习页输入较长的回答
- **影响程度**: 低
- **问题详情**: textarea 有 onInput 自动高度（`src/routes/practice-page.tsx:478-481`），但初始 rows=5 对于长回答来说太小，且没有最大高度限制，长回答时 textarea 会无限增长
- **涉及文件**: `src/routes/practice-page.tsx:473-487`
- **当前表现**: textarea 从 5 行开始，随内容增长但无上限
- **理想表现**: 设置 min-height 和 max-height，使 textarea 在合理范围内自适应
- **最小修复方案**: 添加 `max-h-[50vh] overflow-y-auto` 到 textarea className
- **修复文件**: `src/routes/practice-page.tsx`
- **验证方式**: 输入超长文字，观察 textarea 是否有最大高度限制
- **成功信号**: 长回答时 textarea 不超过视口一半高度，超出部分可滚动
- **影响半径**: 无
- **得分**: user_leverage:2, core_capability:1, evidence:3, compounding:1, validation_ease:5, blast_radius:1

### ISSUE-UJ-016: 图谱页双击节点跳转学习页时丢失 sessionId
- **用户场景**: 用户在图谱页双击一个节点，想从当前会话继续学习
- **影响程度**: 中
- **问题详情**: 双击节点跳转到 `/topic/${topicId}/learn?nodeId=${node.id}`（`src/routes/graph-page.tsx:183`），没有携带 sessionId。用户会丢失会话上下文，练习追踪和收束总结可能中断
- **涉及文件**: `src/routes/graph-page.tsx:182-184`
- **当前表现**: 双击跳转后 sessionId 丢失
- **理想表现**: 双击跳转时应携带当前 URL 的 sessionId 参数
- **最小修复方案**: 从 searchParams 或 appStore 中获取当前 sessionId，拼接在跳转 URL 中
- **修复文件**: `src/routes/graph-page.tsx`
- **验证方式**: 在有 sessionId 的会话中从图谱页双击节点
- **成功信号**: 跳转后 URL 中仍包含 sessionId
- **影响半径**: 图谱→学习转换，会话追踪
- **得分**: user_leverage:4, core_capability:3, evidence:5, compounding:3, validation_ease:5, blast_radius:2

### ISSUE-UJ-017: 图谱页侧边栏"稍后学"按钮 deferFrom 参数可能无效
- **用户场景**: 用户在图谱页点击"稍后学"
- **影响程度**: 低
- **问题详情**: deferFrom 参数构建为 `focusNodeId || currentNodeId || graph_selected_node_id`（`src/routes/graph-page.tsx:432`），但 nodeId 参数是 `graph_selected_node_id`（`src/routes/graph-page.tsx:433`），两个参数可能指向同一个节点
- **涉及文件**: `src/routes/graph-page.tsx:431-433`
- **当前表现**: deferFrom 和 nodeId 可能相同
- **理想表现**: deferFrom 应该是当前正在学习的节点（currentNodeId），nodeId 是要推迟的节点
- **最小修复方案**: 确保顺序为 `currentNodeId || focusNodeId || graph_selected_node_id`
- **修复文件**: `src/routes/graph-page.tsx`
- **验证方式**: 选择一个非当前节点的节点，点击"稍后学"
- **成功信号**: 推迟操作正确关联到当前学习节点
- **影响半径**: 图谱→待学堆栈
- **得分**: user_leverage:2, core_capability:2, evidence:3, compounding:1, validation_ease:4, blast_radius:1

### ISSUE-UJ-018: 图谱页没有节点数量变化的动画过渡
- **用户场景**: 用户切换图谱视图（主干/全图/前置/误解）时
- **影响程度**: 低
- **问题详情**: 切换视图时节点和边瞬间重新渲染，没有过渡动画，用户难以理解视图变化
- **涉及文件**: `src/routes/graph-page.tsx:358-375`
- **当前表现**: 切换视图后画面闪烁
- **理想表现**: React Flow 提供了 `animate` 属性或 `transition` 配置，应启用
- **最小修复方案**: 在 ReactFlow 上添加 `animationOnViewportChange` 或使用 `fitView` 的 transition 选项
- **修复文件**: `src/routes/graph-page.tsx`
- **验证方式**: 切换不同视图观察过渡效果
- **成功信号**: 切换视图时有平滑过渡
- **影响半径**: 图谱页
- **得分**: user_leverage:2, core_capability:1, evidence:3, compounding:1, validation_ease:3, blast_radius:1

### ISSUE-UJ-019: 总结页完全依赖 location.state 传递数据
- **用户场景**: 用户完成会话后跳转到总结页，刷新总结页
- **影响程度**: 高
- **问题详情**: 总结页优先使用 `location.state?.summary`（`src/routes/summary-page.tsx:53`），如果没有 state 则尝试从 API 获取（`useSessionSummaryQuery`）。但如果用户在总结页刷新，location.state 会丢失。虽然代码有 API fallback，但 `useSessionSummaryQuery` 需要 sessionId（`src/routes/summary-page.tsx:51`），而 sessionId 来自 URL 的 searchParams。如果 URL 中没有 sessionId 参数（例如从 practice-page 跳转时没有带），则 API fallback 也不会触发
- **涉及文件**: `src/routes/summary-page.tsx:45-53`, `src/routes/practice-page.tsx:236-238`
- **当前表现**: 刷新总结页时如果没有 sessionId 参数，显示"没有找到本轮总结"
- **理想表现**: 跳转总结页时始终在 URL 中包含 sessionId 参数
- **最小修复方案**: 在 practice-page 的 `navigate(summaryRoute)` 中确保 URL 包含 sessionId
- **修复文件**: `src/routes/practice-page.tsx`, `src/lib/navigation-context.ts`
- **验证方式**: 完成会话到达总结页后刷新页面
- **成功信号**: 刷新后总结页仍能正确显示
- **影响半径**: 练习→总结转换
- **得分**: user_leverage:4, core_capability:3, evidence:5, compounding:4, validation_ease:4, blast_radius:2

### ISSUE-UJ-020: 总结页"资产亮点"显示 node_id 而非节点名称
- **用户场景**: 用户在总结页查看"本轮表达资产亮点"
- **影响程度**: 低
- **问题详情**: 资产亮点中显示 `{asset.node_id}`（`src/routes/summary-page.tsx:222`），用户看到的是如 "nd_xxx" 的内部 ID，而非可读的节点名称
- **涉及文件**: `src/routes/summary-page.tsx:222`
- **当前表现**: 亮点列表显示不友好的 node_id
- **理想表现**: 显示节点名称而非 ID
- **最小修复方案**: 在 buildSummaryPresentation 中或在 summary-page 中查找 node_id 对应的 name
- **修复文件**: `src/lib/summary-display.ts` 或 `src/routes/summary-page.tsx`
- **验证方式**: 查看总结页的资产亮点区域
- **成功信号**: 显示可读的节点名称
- **影响半径**: 总结页
- **得分**: user_leverage:3, core_capability:1, evidence:5, compounding:1, validation_ease:4, blast_radius:1

### ISSUE-UJ-021: 复习页无批量操作
- **用户场景**: 用户有 10+ 待复习项，想快速处理
- **影响程度**: 低
- **问题详情**: 复习队列一次只能处理一个，用户必须逐个点击、回答、提交、下一个。没有批量跳过或批量延后的功能
- **涉及文件**: `src/routes/review-page.tsx:129-132`
- **当前表现**: 只有一个一个处理
- **理想表现**: 至少支持批量跳过低优先级项
- **最小修复方案**: 在列表模式添加"批量跳过低优先级"按钮
- **修复文件**: `src/routes/review-page.tsx`
- **验证方式**: 有多个待复习项时查看是否有批量操作
- **成功信号**: 用户能快速清理低优先级复习
- **影响半径**: 复习页
- **得分**: user_leverage:3, core_capability:1, evidence:3, compounding:2, validation_ease:3, blast_radius:1

### ISSUE-UJ-022: 复习页提交后无能力更新反馈
- **用户场景**: 用户提交复习答案后，看到 "回忆良好" 但不知道自己的能力分数变化
- **影响程度**: 中
- **问题详情**: 复习页提交后只显示 correctness/clarity/naturalness 三维评分和 issues/suggestions，但没有像练习页那样显示 AbilityBars 能力变化
- **涉及文件**: `src/routes/review-page.tsx:212-270`
- **当前表现**: 无能力变化展示
- **理想表现**: 复习后也显示能力雷达或能力条的变化
- **最小修复方案**: 在复习结果中添加 AbilityBars 组件
- **修复文件**: `src/routes/review-page.tsx`
- **验证方式**: 完成一次复习提交
- **成功信号**: 用户能看到能力变化
- **影响半径**: 复习页
- **得分**: user_leverage:3, core_capability:2, evidence:4, compounding:2, validation_ease:3, blast_radius:1

### ISSUE-UJ-023: 统计页重复的 loading 检查
- **用户场景**: 统计页加载时可能闪烁
- **影响程度**: 低
- **问题详情**: stats-page.tsx 在第 42-52 行和第 76-91 行有两个重复的 `if (topicsLoading)` 检查。第二个永远不会触发因为如果 topicsLoading 为 true，第一个已经 return 了
- **涉及文件**: `src/routes/stats-page.tsx:76-78`
- **当前表现**: 无视觉问题，但代码冗余
- **理想表现**: 只有一个 loading 检查
- **最小修复方案**: 删除第二个重复的检查
- **修复文件**: `src/routes/stats-page.tsx`
- **验证方式**: 代码审查
- **成功信号**: 无重复代码
- **影响半径**: 无
- **得分**: user_leverage:1, core_capability:1, evidence:5, compounding:1, validation_ease:5, blast_radius:1

### ISSUE-UJ-024: 统计页的"空数据"状态可能和数据正常共存
- **用户场景**: 主题有数据但某个具体查询（如 abilityOverview）为空
- **影响程度**: 低
- **问题详情**: "空数据"状态检查 `!topics || topics.length === 0`（`src/routes/stats-page.tsx:410`）在组件最底部，但如果 topics 有数据但其他查询为空，页面仍然渲染了一些卡片（能力雷达、近期卡点等），然后最底部又显示"暂无学习数据"的 EmptyState
- **涉及文件**: `src/routes/stats-page.tsx:410-422`
- **当前表现**: 可能同时显示数据和空状态
- **理想表现**: "空数据"状态应在 return 最前面，作为早退出
- **最小修复方案**: 将空状态检查移到组件开头，紧跟 loading/error 之后
- **修复文件**: `src/routes/stats-page.tsx`
- **验证方式**: 有数据时查看页面底部是否出现空状态提示
- **成功信号**: 有数据时不显示空状态
- **影响半径**: 无
- **得分**: user_leverage:2, core_capability:1, evidence:4, compounding:1, validation_ease:5, blast_radius:1

### ISSUE-UJ-025: 统计页无导出功能
- **用户场景**: 用户想导出统计数据用于外部分析
- **影响程度**: 低
- **问题详情**: 设置页有主题导出功能，但统计页没有单独的数据导出入口
- **涉及文件**: `src/routes/stats-page.tsx`
- **当前表现**: 无导出功能
- **理想表现**: 提供导出能力概览或能力趋势的选项
- **最小修复方案**: 在统计页顶部添加"导出报告"按钮
- **修复文件**: `src/routes/stats-page.tsx`
- **验证方式**: 查看统计页是否有导出入口
- **成功信号**: 用户能导出统计数据
- **影响半径**: 统计页
- **得分**: user_leverage:2, core_capability:1, evidence:3, compounding:1, validation_ease:4, blast_radius:1

### ISSUE-UJ-026: 设置页未保存的更改数提示不够醒目
- **用户场景**: 用户修改了多个设置项，准备离开设置页
- **影响程度**: 中
- **问题详情**: 设置页的"未保存"提示仅在"保存设置"按钮旁（`src/routes/settings-page.tsx:389-393`），是一个小 badge。如果用户不点击保存就导航到其他页面，没有离开确认
- **涉及文件**: `src/routes/settings-page.tsx:385-399`
- **当前表现**: 只在按钮旁显示 "N 项未保存" badge
- **理想表现**: 导航离开设置页时如果有未保存更改，应提示确认
- **最小修复方案**: 使用 react-router 的 `useBlocker` 在有未保存更改时阻止导航并显示确认
- **修复文件**: `src/routes/settings-page.tsx`
- **验证方式**: 修改设置后导航到其他页面
- **成功信号**: 弹出确认对话框
- **影响半径**: 设置页
- **得分**: user_leverage:3, core_capability:1, evidence:4, compounding:2, validation_ease:4, blast_radius:1

### ISSUE-UJ-027: 设置页 Ollama 回退开关缺少连接测试
- **用户场景**: 用户启用 Ollama 后想确认是否能连接
- **影响程度**: 低
- **问题详情**: 设置页有"启用 Ollama 本地回退"开关，但没有提供测试连接的按钮。用户无法在设置页确认 Ollama 是否正在运行
- **涉及文件**: `src/routes/settings-page.tsx:306-312`
- **当前表现**: 只有开关，没有连接测试
- **理想表现**: 添加"测试连接"按钮，显示连接状态
- **最小修复方案**: 在 Ollama 开关旁添加测试按钮，调用 health API 的 ollama 状态
- **修复文件**: `src/routes/settings-page.tsx`
- **验证方式**: 启用 Ollama 后点击测试按钮
- **成功信号**: 显示连接成功/失败状态
- **影响半径**: 设置页
- **得分**: user_leverage:2, core_capability:1, evidence:3, compounding:1, validation_ease:4, blast_radius:1

### ISSUE-UJ-028: 侧边栏学习/图谱/资产链接缺少 sessionId
- **用户场景**: 用户在会话中从侧边栏导航到学习或图谱页
- **影响程度**: 中
- **问题详情**: 侧边栏的"学习"链接使用 `buildLearnRoute(currentTopicId, { nodeId: currentNodeId, sessionId })`（`src/app/app-layout.tsx:70`），但 `currentNodeId` 和 `sessionId` 来自 `useResolvedTopicContext`，而 Zustand 的 `partialize` 没有持久化 session 相关字段（`src/stores/app-store.ts:111-114`）。刷新页面后 sessionId 丢失，侧边栏链接不带 sessionId
- **涉及文件**: `src/stores/app-store.ts:111-114`, `src/app/app-layout.tsx:20-21`
- **当前表现**: 刷新页面后侧边栏链接不带 sessionId
- **理想表现**: sessionId 应从 URL 的 searchParams 中获取，而非仅依赖 Zustand
- **最小修复方案**: 修改 `useResolvedTopicContext` 优先从当前 URL 解析 sessionId
- **修复文件**: `src/hooks/use-resolved-topic-context.ts`
- **验证方式**: 在会话中刷新页面，检查侧边栏链接是否包含 sessionId
- **成功信号**: 侧边栏链接始终包含 sessionId（当 URL 中有时）
- **影响半径**: 全局导航
- **得分**: user_leverage:4, core_capability:3, evidence:5, compounding:4, validation_ease:4, blast_radius:3

### ISSUE-UJ-029: 学习页全屏模式无侧边栏返回路径
- **用户场景**: 用户在学习页（全屏模式，无侧边栏）想回到首页
- **影响程度**: 中
- **问题详情**: 学习页是全屏渲染的（`src/app/app-layout.tsx:22-24` 匹配 `/topic/:topicId/learn` 时直接 `<Outlet />` 无侧边栏）。学习页本身没有返回首页的按钮，如果用户刷新页面且 URL 中没有 searchParams 中的 sessionId，`useResolvedTopicContext` 返回空，侧边栏"学习"链接消失
- **涉及文件**: `src/app/app-layout.tsx:22-24`
- **当前表现**: 全屏模式下无侧边栏，学习页也没有回到首页的明显入口
- **理想表现**: 学习页顶部应有品牌 logo 或返回首页的入口
- **最小修复方案**: 在学习页顶部栏添加 AxonClone logo 链接回首页
- **修复文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **验证方式**: 直接访问学习页 URL，寻找回到首页的入口
- **成功信号**: 能找到回到首页的路径
- **影响半径**: 学习页
- **得分**: user_leverage:3, core_capability:1, evidence:5, compounding:3, validation_ease:4, blast_radius:2

### ISSUE-UJ-030: 404 页面没有动画或品牌元素
- **用户场景**: 用户访问不存在的 URL
- **影响程度**: 低
- **问题详情**: 404 页面只是一个静态的 "404" 大字 + "页面不存在" + "返回首页" 链接（`src/app/app.tsx:41-47`），风格与品牌不一致
- **涉及文件**: `src/app/app.tsx:41-47`
- **当前表现**: 简单的 404 文字
- **理想表现**: 添加品牌 logo 和更友好的提示
- **最小修复方案**: 在 404 页面添加 AxonClone logo
- **修复文件**: `src/app/app.tsx`
- **验证方式**: 访问不存在的 URL
- **成功信号**: 404 页面有品牌标识
- **影响半径**: 无
- **得分**: user_leverage:1, core_capability:1, evidence:3, compounding:1, validation_ease:5, blast_radius:1

### ISSUE-UJ-031: 资产页的"再练一次"链接不带 sessionId
- **用户场景**: 用户在资产页点击"再练一次"
- **影响程度**: 低
- **问题详情**: "再练一次"使用 `buildPracticeRoute(topicId!, asset.node_id)`（`src/routes/assets-page.tsx:165`），没有 sessionId 参数。练习后无法收束到当前会话
- **涉及文件**: `src/routes/assets-page.tsx:165`
- **当前表现**: 跳转后的练习不带 sessionId
- **理想表现**: 如果当前有活跃 sessionId，应传递到练习页
- **最小修复方案**: 从 URL searchParams 或 context 中获取 sessionId 并传递
- **修复文件**: `src/routes/assets-page.tsx`
- **验证方式**: 在资产页点击"再练一次"
- **成功信号**: 练习页 URL 中包含 sessionId
- **影响半径**: 资产→练习转换
- **得分**: user_leverage:3, core_capability:2, evidence:4, compounding:2, validation_ease:5, blast_radius:1

### ISSUE-UJ-032: 所有 textarea 缺少 ARIA label
- **用户场景**: 屏幕阅读器用户使用页面
- **影响程度**: 低
- **问题详情**: 首页内容 textarea（home-page.tsx:103）和复习页 textarea（review-page.tsx:171）没有关联的 label，也没有 aria-label
- **涉及文件**: `src/routes/home-page.tsx:103-117`, `src/routes/review-page.tsx:171-183`
- **当前表现**: textarea 有 label 元素但通过 id 关联，某些屏幕阅读器可能不识别
- **理想表现**: 所有 textarea 都有明确的 aria-label
- **最小修复方案**: 添加 aria-label 属性
- **修复文件**: `src/routes/home-page.tsx`, `src/routes/review-page.tsx`
- **验证方式**: 使用 Lighthouse 审计
- **成功信号**: 无 ARIA 相关的 accessibility 警告
- **影响半径**: 无
- **得分**: user_leverage:1, core_capability:1, evidence:4, compounding:1, validation_ease:5, blast_radius:1

### ISSUE-UJ-033: 键盘快捷键 Cmd+K 的命令面板无 discoverability
- **用户场景**: 用户不知道有命令面板功能
- **影响程度**: 低
- **问题详情**: 命令面板通过 Cmd+K 打开（`src/features/article-workspace/article-workspace-page.tsx:948-957`），但没有任何 UI 提示告诉用户这个快捷键存在。工具栏的"搜索"按钮没有显示快捷键提示
- **涉及文件**: `src/features/article-workspace/article-workspace-page.tsx:1482-1485`
- **当前表现**: "搜索"按钮没有显示 Cmd+K 提示
- **理想表现**: 搜索按钮旁显示 "⌘K" 快捷键标签
- **最小修复方案**: 在搜索按钮旁添加 keyboard shortcut 标签
- **修复文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **验证方式**: 查看学习页工具栏搜索按钮
- **成功信号**: 用户能看到 Cmd+K 快捷键提示
- **影响半径**: 无
- **得分**: user_leverage:2, core_capability:1, evidence:4, compounding:1, validation_ease:5, blast_radius:1

### ISSUE-UJ-034: 练习页提交等待时无取消按钮
- **用户场景**: 用户提交答案后改变主意想取消
- **影响程度**: 低
- **问题详情**: 练习页 submitting 状态只显示 LoadingSkeleton + "正在评估你的回答..."（`src/routes/practice-page.tsx:529-534`），没有取消按钮。如果 AI 评估耗时较长，用户只能等待
- **涉及文件**: `src/routes/practice-page.tsx:529-534`
- **当前表现**: 只有等待动画，无取消选项
- **理想表现**: 添加取消按钮（AbortController）
- **最小修复方案**: 添加取消按钮，使用 mutation 的 reset() 方法
- **修复文件**: `src/routes/practice-page.tsx`
- **验证方式**: 提交答案后立即点击取消
- **成功信号**: 能取消正在进行的评估
- **影响半径**: 练习页
- **得分**: user_leverage:2, core_capability:1, evidence:3, compounding:1, validation_ease:3, blast_radius:1

### ISSUE-UJ-035: 学习页"新建源文章"无确认对话框
- **用户场景**: 用户误点"新建源文章"按钮
- **影响程度**: 低
- **问题详情**: 点击"新建源文章"会立即调用 `createSourceArticleMutation` 创建一个空文章并进入编辑模式。如果用户误点，会创建一个无用的空文章
- **涉及文件**: `src/features/article-workspace/article-workspace-page.tsx:1024-1039`
- **当前表现**: 直接创建空文章
- **理想表现**: 至少在创建后提供一个"删除"或"取消"选项
- **最小修复方案**: 空文章创建后编辑区域提供"放弃编辑"按钮
- **修复文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **验证方式**: 点击"新建源文章"后立即想取消
- **成功信号**: 能取消创建或删除空文章
- **影响半径**: 学习页
- **得分**: user_leverage:2, core_capability:1, evidence:3, compounding:1, validation_ease:4, blast_radius:1

---

## 候选改进列表 (CANDIDATES)

### CANDIDATE-UJ-001: 学习路径引导气泡
- **用户问题**: 新用户不知道应该先做什么（阅读→练习→总结→复习的循环）
- **用户收益**: 减少新用户困惑，加快上手速度
- **系统能力收益**: 提升新用户激活率
- **最小切入点**: 在学习页空白区域添加首次使用引导提示
- **涉及文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **得分**: user_leverage:4, core_capability:2, evidence:3, compounding:4, validation_ease:3, blast_radius:2, total:18

### CANDIDATE-UJ-002: 练习页键盘快捷键（Ctrl+Enter 提交）
- **用户问题**: 用户在练习页输入答案后需要鼠标点击"提交答案"按钮
- **用户收益**: 提高练习效率
- **系统能力收益**: 减少练习页操作摩擦
- **最小切入点**: 添加 onKeyDown 事件，Ctrl/Cmd+Enter 触发提交
- **涉及文件**: `src/routes/practice-page.tsx`
- **得分**: user_leverage:4, core_capability:1, evidence:4, compounding:2, validation_ease:5, blast_radius:1, total:17

### CANDIDATE-UJ-003: 练习推荐类型高亮卡片
- **用户问题**: 用户不知道 AI 推荐的下一个练习类型是什么
- **用户收益**: 更有目的地练习，减少盲目选择
- **系统能力收益**: 提升练习针对性
- **最小切入点**: 在练习类型选择区域高亮推荐类型
- **涉及文件**: `src/routes/practice-page.tsx`
- **得分**: user_leverage:3, core_capability:2, evidence:3, compounding:3, validation_ease:4, blast_radius:1, total:16

### CANDIDATE-UJ-004: 复习页间隔时间显示
- **用户问题**: 用户不知道复习项距离上次复习间隔了多久
- **用户收益**: 了解遗忘曲线对个人的影响
- **系统能力收益**: 增强复习策略透明度
- **最小切入点**: 在 ReviewCard 中显示上次复习时间
- **涉及文件**: `src/routes/review-page.tsx`
- **得分**: user_leverage:3, core_capability:2, evidence:3, compounding:2, validation_ease:4, blast_radius:1, total:15

### CANDIDATE-UJ-005: 图谱页节点右键菜单
- **用户问题**: 用户需要先点击节点再在侧边栏操作，步骤多
- **用户收益**: 减少图谱交互步骤
- **系统能力收益**: 提升图谱操作效率
- **最小切入点**: 添加右键菜单提供"学习/练习/稍后学"快捷操作
- **涉及文件**: `src/routes/graph-page.tsx`
- **得分**: user_leverage:3, core_capability:1, evidence:3, compounding:2, validation_ease:3, blast_radius:2, total:14

### CANDIDATE-UJ-006: 学习进度百分比显示
- **用户问题**: 用户在首页看到 "2/5 已掌握" 但不确定整体进度
- **用户收益**: 更直观的学习进度感知
- **系统能力收益**: 提升学习动力
- **最小切入点**: 在首页和 topbar 显示整体完成百分比
- **涉及文件**: `src/routes/home-page.tsx`, `src/components/shared/topbar.tsx`
- **得分**: user_leverage:3, core_capability:1, evidence:3, compounding:2, validation_ease:4, blast_radius:1, total:14

### CANDIDATE-UJ-007: 概念面板中添加"前往练习"按钮
- **用户问题**: 用户在概念面板查看详情后想直接去练习，需要先关闭面板再点"去练习"
- **用户收益**: 减少概念探索到练习的步骤
- **系统能力收益**: 缩短学习→练习转化路径
- **最小切入点**: 在概念面板底部添加"前往练习"按钮
- **涉及文件**: `src/features/article-workspace/concept-drawer-content.tsx`
- **得分**: user_leverage:4, core_capability:2, evidence:3, compounding:3, validation_ease:4, blast_radius:1, total:17

### CANDIDATE-UJ-008: 表达资产收藏列表筛选
- **用户问题**: 用户在资产页收藏了多个资产，但想只看收藏的
- **用户收益**: 快速找到优质表达
- **系统能力收益**: 提升资产检索效率
- **最小切入点**: 资产页已有收藏筛选（showFavoritedOnly），但首页统计页没有
- **涉及文件**: 已实现，可扩展到统计页
- **得分**: user_leverage:2, core_capability:1, evidence:2, compounding:1, validation_ease:5, blast_radius:1, total:12

### CANDIDATE-UJ-009: 会话计时器显示
- **用户问题**: 用户不知道自己在当前会话中学习了多久
- **用户收益**: 时间管理意识
- **系统能力收益**: 增强学习节奏感
- **最小切入点**: 学习页已有 sessionElapsed 计时器但显示不明显（`article-workspace-page.tsx:1466-1469`）
- **涉及文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **得分**: user_leverage:3, core_capability:1, evidence:3, compounding:2, validation_ease:4, blast_radius:1, total:14

### CANDIDATE-UJ-010: 总结页分享功能
- **用户问题**: 用户想分享学习总结给同学或导师
- **用户收益**: 社交化和外部反馈
- **系统能力收益**: 增强产品传播
- **最小切入点**: 在总结页添加"复制总结到剪贴板"按钮
- **涉及文件**: `src/routes/summary-page.tsx`
- **得分**: user_leverage:3, core_capability:1, evidence:2, compounding:3, validation_ease:4, blast_radius:1, total:14

### CANDIDATE-UJ-011: 概念文章生成进度条
- **用户问题**: 用户等待概念专文生成时不知道还要多久
- **用户收益**: 减少等待焦虑
- **系统能力收益**: 提升生成过程的透明度
- **最小切入点**: 使用 mutation 的 isPending 状态显示 skeleton 加载动画
- **涉及文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **得分**: user_leverage:4, core_capability:2, evidence:4, compounding:3, validation_ease:4, blast_radius:1, total:18

### CANDIDATE-UJ-012: 源文章编辑时自动保存
- **用户问题**: 用户编辑源文章时忘记点保存，切换到其他文章后丢失修改
- **用户收益**: 防止编辑内容丢失
- **系统能力收益**: 减少内容丢失投诉
- **最小切入点**: 在编辑模式的 onBlur 或定时自动调用保存
- **涉及文件**: `src/features/article-workspace/article-workspace-page.tsx`
- **得分**: user_leverage:4, core_capability:1, evidence:4, compounding:3, validation_ease:3, blast_radius:1, total:16

### CANDIDATE-UJ-013: 练习页历史记录展开
- **用户问题**: 用户想回顾之前的练习记录但需要点击展开
- **用户收益**: 快速回顾练习历史
- **系统能力收益**: 增强学习反思
- **最小切入点**: 默认展开历史记录（已部分实现 `showHistory` state）
- **涉及文件**: `src/routes/practice-page.tsx`
- **得分**: user_leverage:2, core_capability:1, evidence:3, compounding:1, validation_ease:5, blast_radius:1, total:13

### CANDIDATE-UJ-014: 图谱页当前节点高亮动画
- **用户问题**: 用户在图谱页难以找到当前正在学习的节点
- **用户收益**: 快速定位当前节点
- **系统能力收益**: 增强图谱导航效率
- **最小切入点**: 当前节点添加脉冲动画或特殊边框颜色
- **涉及文件**: `src/routes/graph-page.tsx`
- **得分**: user_leverage:4, core_capability:2, evidence:3, compounding:3, validation_ease:4, blast_radius:2, total:18

### CANDIDATE-UJ-015: 复习队列智能排序
- **用户问题**: 复习队列中的顺序不直观
- **用户收益**: 按优先级和到期时间排序更合理
- **系统能力收益**: 优化复习效果
- **最小切入点**: 在 review-page 中按 priority 降序和 due_at 升序排序
- **涉及文件**: `src/routes/review-page.tsx`
- **得分**: user_leverage:3, core_capability:2, evidence:3, compounding:3, validation_ease:4, blast_radius:1, total:16

### CANDIDATE-UJ-016: 首页主题卡片添加最后学习时间
- **用户问题**: 用户看到多个主题卡片但不知道哪个最近更新
- **用户收益**: 更好地决定继续学习哪个主题
- **系统能力收益**: 提升主题切换效率
- **最小切入点**: 在主题卡片中显示 `updated_at` 或 `last_session_at`
- **涉及文件**: `src/routes/home-page.tsx`
- **得分**: user_leverage:3, core_capability:1, evidence:3, compounding:2, validation_ease:4, blast_radius:1, total:14

### CANDIDATE-UJ-017: 练习页答案字数统计增强
- **用户问题**: 用户不知道自己的回答长度是否足够
- **用户收益**: 更有目的地组织回答
- **系统能力收益**: 提升回答质量
- **最小切入点**: 在字数旁添加"推荐 100-300 字"提示
- **涉及文件**: `src/routes/practice-page.tsx`
- **得分**: user_leverage:2, core_capability:1, evidence:3, compounding:2, validation_ease:5, blast_radius:1, total:14

### CANDIDATE-UJ-018: 学习页面包屑导航增强
- **用户问题**: 面包屑太长时溢出，用户无法看到全部浏览历史
- **用户收益**: 更好的导航体验
- **系统能力收益**: 提升文章导航效率
- **最小切入点**: 添加 max-width 和 overflow scroll 到面包屑容器
- **涉及文件**: `src/features/article-workspace/article-workspace-page.tsx:1510-1523`
- **得分**: user_leverage:3, core_capability:1, evidence:3, compounding:2, validation_ease:5, blast_radius:1, total:15

### CANDIDATE-UJ-019: 练习页"采纳"按钮行为优化
- **用户问题**: 用户点击"采纳"推荐表达后，答案变为推荐表达，但可能想在此基础上修改
- **用户收益**: 更灵活的表达编辑
- **系统能力收益**: 提升表达训练质量
- **最小切入点**: 采纳后 focus textarea，方便用户微调
- **涉及文件**: `src/routes/practice-page.tsx:596-604`
- **得分**: user_leverage:3, core_capability:1, evidence:3, compounding:2, validation_ease:4, blast_radius:1, total:14

### CANDIDATE-UJ-020: 主题创建成功后跳转带动画
- **用户问题**: 创建主题后跳转到学习页比较突兀
- **用户收益**: 更平滑的过渡体验
- **系统能力收益**: 提升首印象
- **最小切入点**: 跳转前显示"主题创建成功！正在展开知识图谱..."的全屏过渡
- **涉及文件**: `src/routes/home-page.tsx`
- **得分**: user_leverage:2, core_capability:1, evidence:2, compounding:2, validation_ease:3, blast_radius:1, total:11

---

## 审计总结

### 按严重程度分布
- **高**: 5 个（ISSUE-UJ-006, 007, 010, 019, 028）
- **中**: 11 个
- **低**: 19 个

### 按用户旅程阶段分布
| 阶段 | 问题数 |
|------|--------|
| 首页/创建 | 5 |
| 学习页 | 11 |
| 练习页 | 9 |
| 图谱页 | 4 |
| 总结页 | 3 |
| 复习页 | 3 |
| 统计页 | 3 |
| 设置页 | 3 |
| 全局/导航 | 5 |

### 高优先修复建议（按投入产出比排序）
1. **ISSUE-UJ-010** (练习草稿持久化) - 最高 user_leverage，修复简单
2. **ISSUE-UJ-007** (概念专文空白状态) - 严重影响学习体验
3. **ISSUE-UJ-019** (总结页刷新丢失) - 数据丢失风险
4. **ISSUE-UJ-028** (全局 sessionId 丢失) - 影响会话追踪
5. **ISSUE-UJ-016** (图谱跳转丢失 sessionId) - 修复简单，影响大
6. **ISSUE-UJ-006** (学习页 ErrorBoundary) - 防止全页崩溃
7. **ISSUE-UJ-013** (自动跳转总结页) - 影响练习连贯性

### 总计
- **问题 (ISSUES)**: 35 个
- **候选改进 (CANDIDATES)**: 20 个
