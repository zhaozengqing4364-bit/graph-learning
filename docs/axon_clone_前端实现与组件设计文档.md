# AxonClone 前端实现与组件设计文档

## 一、文档目的

本文档用于定义 AxonClone 桌面端前端实现方案、页面级组件拆分、状态管理策略、模块边界、交互响应规则、与后端接口协作方式以及开发落地建议，作为前端开发、交互设计与联调实现的统一依据。

AxonClone 的前端并不是普通内容展示页面，而是一个高状态密度、强交互、强上下文、强流程引导的学习界面系统。因此，前端设计必须优先围绕“当前学习动作”构建，而不是围绕功能堆砌构建。

---

## 二、前端实现目标

### 2.1 产品体验目标
- 首页能快速开始或恢复学习
- 学习页能聚焦当前节点，不让用户迷路
- 图谱页能提供全局结构感，但不造成信息过载
- 练习页能高效承载表达训练与反馈
- 统计页能展示真实成长与复习任务

### 2.2 工程目标
- 组件边界清晰
- 页面状态可预测
- 与后端接口耦合度可控
- 支持本地桌面运行与后续扩展
- 对复杂对象（Topic / Node / Practice / Review）具备良好类型约束

---

## 三、前端技术栈

### 推荐组合
- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Zustand
- React Query
- React Flow

### 职责说明
- React：页面和组件组织
- TypeScript：对象类型约束
- Vite：开发与构建
- Tailwind：快速布局与视觉一致性
- React Router：页面路由管理
- Zustand：本地 UI 状态管理
- React Query：服务请求与缓存
- React Flow：图谱可视化

---

## 四、前端架构分层建议

建议拆成以下层：

1. App Shell 层
2. Route Page 层
3. Domain Module 层
4. Shared UI 层
5. Store 层
6. Query / API 层
7. Type 层

---

## 4.1 App Shell 层

负责：
- 全局布局
- 侧边导航
- 顶部状态条
- 路由出口
- 全局提示与错误展示

建议组件：
- `AppLayout`
- `SidebarNav`
- `Topbar`
- `GlobalToast`
- `GlobalLoadingMask`

---

## 4.2 Route Page 层

页面级路由建议：
- `HomePage`
- `LearningPage`
- `GraphPage`
- `PracticePage`
- `StatsPage`
- `ReviewPage`
- `SettingsPage`

每个页面只负责：
- 组装 domain modules
- 处理路由参数
- 触发页面初始化逻辑

---

## 4.3 Domain Module 层

按产品域拆分：
- `topic`
- `node`
- `graph`
- `practice`
- `review`
- `stats`
- `settings`

每个域包含：
- hooks
- services
- local components
- types（若需局部扩展）

---

## 4.4 Shared UI 层

放通用组件：
- 按钮、输入框、弹窗
- 标签、徽标、卡片
- 空状态、加载态、错误态
- 分页/列表组件
- 能力条 / 进度条 / 小图表

---

## 4.5 Store 层

Zustand 主要管理：
- 当前 Topic
- 当前 Node
- 当前 Session
- 当前图谱视图状态
- 待学堆栈本地交互态
- 练习流程中的瞬时状态

### 不建议放入 store 的内容
- 可通过 React Query 管理的接口数据缓存
- 所有服务端对象的完整持久数据

---

## 4.6 Query / API 层

建议统一放：
- request client
- 各业务 API 调用函数
- React Query hooks

例如：
- `useTopicListQuery`
- `useTopicDetailQuery`
- `useNodeDetailQuery`
- `useGraphQuery`
- `usePracticeMutation`
- `useReviewQueueQuery`

---

## 五、路由设计建议

### 一级路由
- `/`
- `/topic/:topicId/learn`
- `/topic/:topicId/graph`
- `/topic/:topicId/practice`
- `/stats`
- `/reviews`
- `/settings`

### 推荐补充参数
- `nodeId`
- `sessionId`
- `view`
- `practiceType`

### 示例
- `/topic/tp_001/learn?nodeId=nd_101`
- `/topic/tp_001/graph?view=mainline`
- `/topic/tp_001/practice?nodeId=nd_101&practiceType=contrast`

---

## 六、核心页面实现拆解

## 6.1 首页 HomePage

### 页面目标
统一入口，快速开始或恢复学习。

### 主要模块
- `NewTopicInputPanel`
- `RecentTopicsPanel`
- `DeferredNodesPanel`
- `ContinueLearningPanel`
- `RecentPracticePanel`

### 推荐状态
- 初始空状态
- 有历史主题状态
- 有待学节点状态

### 关键交互
- 输入内容创建 Topic
- 点击继续学习进入 LearningPage
- 点击待学节点恢复到对应主题

---

## 6.2 学习页 LearningPage

### 页面目标
围绕当前节点提供最高密度的有效学习信息。

### 页面模块建议
- `TopicHeader`
- `LearningPathBreadcrumb`
- `CurrentNodeCard`
- `NodeRelationsPanel`
- `SuggestedNextNodesPanel`
- `LearningActionsBar`

### CurrentNodeCard 内容建议
- 节点名称
- 一句话定义
- 为什么现在学它
- 重要性
- 当前能力摘要
- 一个例子
- 常见误解

### NodeRelationsPanel 选项卡建议
- 前置
- 对比
- 应用
- 误解
- 相关

### LearningActionsBar 按钮建议
- 进入练习
- 继续扩展
- 稍后再学
- 查看图谱
- 完成本轮

---

## 6.3 图谱页 GraphPage

### 页面目标
让用户获得全局结构感。

### 页面模块建议
- `GraphToolbar`
- `GraphCanvas`
- `GraphSidebar`

### GraphToolbar 功能建议
- 视图切换：主干 / 全图 / 前置 / 误解
- 深度切换
- 关系筛选
- 聚焦当前节点

### GraphSidebar 内容建议
- 当前选中节点
- 一句话定义
- 关键关系
- 进入学习 / 进入练习按钮

### 关键注意
默认不要把全部节点一次展开，优先主干视图。

---

## 6.4 练习页 PracticePage

### 页面目标
承载表达训练与反馈。

### 页面模块建议
- `PracticeHeader`
- `PracticePromptCard`
- `PracticeAnswerInput`
- `PracticeFeedbackPanel`
- `ExpressionAssetPanel`
- `PracticeActionsFooter`

### PracticeFeedbackPanel 内容建议
- 正确性
- 清晰度
- 自然度
- 最关键问题
- 一条优化建议
- 推荐表达版本
- 表达骨架

### PracticeActionsFooter 按钮建议
- 保存表达资产
- 下一题
- 返回学习页
- 结束练习

---

## 6.5 统计页 StatsPage

### 页面目标
展示用户成长与待处理事项。

### 页面模块建议
- `StatsOverviewCards`
- `AbilityRadarPanel`
- `FrictionDistributionPanel`
- `ReviewQueuePreview`
- `ExpressionAssetsSummary`
- `WeakNodesList`

---

## 6.6 复习页 ReviewPage

### 页面目标
以主动回忆与再表达为核心完成复习。

### 模块建议
- `ReviewQueueHeader`
- `ReviewTaskCard`
- `ReviewAnswerInput`
- `ReviewFeedbackPanel`
- `ReviewActionsFooter`

---

## 6.7 设置页 SettingsPage

### 页面模块建议
- `ModelSettingsSection`
- `LearningSettingsSection`
- `GraphSettingsSection`
- `PracticeSettingsSection`
- `DataSettingsSection`

---

## 七、组件分层与命名建议

## 7.1 页面级组件
以页面整体布局与域模块组装为主。

## 7.2 业务组件
如：
- `NodeCard`
- `PracticePromptCard`
- `AbilityRadar`
- `DeferredNodeList`

## 7.3 通用组件
如：
- `Button`
- `Dialog`
- `Tabs`
- `Badge`
- `Card`
- `Input`
- `Textarea`
- `EmptyState`

---

## 八、状态管理策略

## 8.1 React Query 管理的数据
适合放到 query 层：
- Topic 列表
- Topic 详情
- Node 详情
- 图谱数据
- 练习题结果
- 复习队列
- 统计数据

## 8.2 Zustand 管理的数据
适合放到本地 store：
- 当前 Topic ID
- 当前 Node ID
- 当前 Session ID
- 当前 Graph 视图状态
- 练习输入中的未提交文本
- 局部 UI 开关
- 当前临时筛选条件

## 8.3 本地持久化建议
可对以下状态做 local persistence：
- 最后访问的 Topic
- 图谱视图偏好
- 侧边栏折叠状态
- 草稿型练习文本（短期）

---

## 九、前端类型系统建议

建议定义统一 TypeScript 类型，与后端 schema 对齐：
- `Topic`
- `Node`
- `Edge`
- `AbilityRecord`
- `PracticePrompt`
- `PracticeFeedback`
- `SessionSummary`
- `ReviewItem`
- `ExpressionAsset`
- `FrictionRecord`

### 原则
- 不在前端自行派生多个不兼容结构
- 使用 adapter 层做必要转换

---

## 十、与后端协作模式

## 10.1 请求风格
前端不直接拼接复杂业务逻辑，应调用明确服务函数：
- `createTopic()`
- `getNodeDetail()`
- `expandNode()`
- `startSession()`
- `submitPractice()`
- `completeSession()`
- `getReviewQueue()`

## 10.2 页面初始化模式

### 首页
- 拉取 recent topics
- 拉取 deferred nodes
- 拉取 review preview

### 学习页
- 拉取 topic detail
- 拉取 node detail
- 若无 session，则自动 start session

### 练习页
- 拉取或创建 practice prompt
- 提交答案后更新能力摘要

---

## 十一、加载态与空状态设计

## 11.1 加载态原则
- 页面级加载尽量少
- 优先模块级 skeleton
- 学习页当前节点卡片应优先可见
- 图谱页画布与侧栏可分开加载

## 11.2 空状态设计
- 首页空状态：引导创建第一个 Topic
- 图谱空状态：提示先完成初始解析
- 表达资产空状态：提示先做一次练习
- 复习空状态：提示当前没有到期复习任务

---

## 十二、错误态与降级设计

## 12.1 页面级错误处理原则
- 错误不要直接挡住全部学习流程
- 优先降级展示简化结果

### 示例
- 图谱拉取失败：仍保留学习页
- 练习反馈失败：保留用户输入，允许重试
- Topic 创建部分失败：若 entry node 可用，则允许进入简化学习页

## 12.2 通用错误边界建议
- `PageErrorState`
- `ModuleErrorState`
- `RetryActionButton`
- `FallbackHint`

---

## 十三、图谱前端实现建议

## 13.1 React Flow 数据适配层
建议建立独立 adapter：
- 后端 `nodes/edges` → React Flow `nodes/edges`
- 状态颜色 / 类型 / 高亮规则统一由 adapter 处理

## 13.2 图谱视觉层次建议
- 当前节点：最强高亮
- 主干链：高亮线
- 支线：弱化显示
- 误解边：特殊视觉样式
- 折叠分支：聚合提示点

## 13.3 图谱性能建议
- 默认只渲染当前 Topic 的局部图
- 大图优先按主干渲染
- 侧边详情与图分离更新

---

## 十四、练习交互实现建议

## 14.1 练习流状态机建议
建议用清晰状态驱动：
- idle
- loading_prompt
- answering
- submitting
- feedback_ready
- saving_asset
- completed

### 好处
- 减少复杂条件渲染混乱
- 便于控制按钮禁用与提示文案

## 14.2 输入区体验建议
- 保留草稿
- 支持最小示例提示
- 支持字数不足时提示
- 不要一开始展示标准答案

---

## 十五、统计与可视化组件建议

### 推荐组件
- `AbilityRadarChart`
- `FrictionBarChart`
- `ReviewPriorityList`
- `WeakNodeTable`
- `ExpressionTypeBreakdown`

### 注意事项
- 统计页重点是帮助决策，不是做 BI 大盘
- 图表数量适中，优先解释性强的展示

---

## 十六、Tauri 侧前端协作建议

## 16.1 前端与 Tauri 的边界
前端只处理 UI 和调用本地后端，不直接承担：
- 模型调用
- 图数据库写入
- 复杂文件解析

## 16.2 可由 Tauri 提供的能力
- 打开本地文件
- 选择导入内容
- 触发导出文件保存
- 管理 sidecar 进程状态

---

## 十七、开发优先级建议

## P0
- AppLayout
- HomePage
- LearningPage
- PracticePage
- Topic/Node/Practice 基础 hooks
- GraphPage 最小可用版

## P1
- StatsPage
- ReviewPage
- DeferredNodesPanel
- ExpressionAssetPanel
- Graph filters

## P2
- 更高级图谱交互
- 复杂拖拽布局
- 表达资产高级检索
- 导出中心

---

## 十八、前端目录建议

```text
src/
  app/
  routes/
  modules/
    topic/
    node/
    graph/
    practice/
    review/
    stats/
    settings/
  components/
    ui/
    shared/
  stores/
  services/
  hooks/
  types/
  utils/
  styles/
```

---

## 十九、最终结论

AxonClone 前端实现的关键，不在于页面多，而在于每个页面都必须围绕“当前最该做的学习动作”组织信息与按钮。

最核心的实现原则是：
- 首页负责开始与恢复
- 学习页负责聚焦当前节点
- 练习页负责推动表达输出
- 图谱页负责提供结构感
- 统计页负责建立成长感

在工程上，应坚持：
- 页面轻、业务模块清晰
- React Query 管服务数据，Zustand 管瞬时状态
- 统一类型定义
- 错误可降级
- 图谱视图不喧宾夺主

只要前端实现守住这些原则，AxonClone 的学习体验就会非常清晰，而不会变成一个信息很多但不好用的桌面工具。

