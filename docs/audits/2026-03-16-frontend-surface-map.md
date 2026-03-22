# Frontend Surface Map

## 1. System Summary
- 当前系统是做什么的：
  以“文章优先”的方式组织学习。用户先创建主题，再在文章工作台中连续阅读、编辑源文章、确认候选概念、生成概念专文，并把结果沉淀到图谱、练习、复习、统计与表达资产中。
- 主要用户角色：
  单一学习者，没有显式多角色权限系统。
- 主要前端模块：
  首页与主题创建、文章工作台、图谱、表达练习、复习队列、学习总结、表达资产、统计、设置。

## 2. Route / Page Inventory
- 页面 / 路由：
  `/` 首页。
  `/topic/:topicId/learn` 文章优先工作台。
  `/topic/:topicId/graph` 图谱页。
  `/topic/:topicId/practice` 表达练习页。
  `/topic/:topicId/summary` 学习总结页。
  `/topic/:topicId/assets` 表达资产页。
  `/stats` 统计页。
  `/reviews` 复习页。
  `/settings` 设置页。
  `*` 404。
- 入口方式：
  首页创建主题、最近学习、继续学习、全局侧栏“当前主题”、工作台内跳转、图谱/统计/设置/复习导航。
- 访问前置条件：
  `learn/graph/practice/assets/summary` 需要有效 `topicId`。
  `practice` 还需要有效 `nodeId`。
  `summary` 依赖 `sessionId` 或路由 state。
- 关联接口 / 状态：
  全站依赖 React Query + `/api/v1/*`。
  关键状态还受 Zustand 持久化的 `current_topic_id/current_node_id/current_session_id` 影响。

## 3. Feature Modules
- 模块名称：
  首页。
- 主要能力：
  创建主题、继续学习、查看最近主题、归档/删除主题、进入复习。
- 关键用户动作：
  填表创建主题、点击最近主题卡片、归档、删除。
- 高风险点：
  创建成功后的跳转、当前主题同步、持久化状态污染。

- 模块名称：
  文章工作台。
- 主要能力：
  导读文章、源文章编辑、概念专文阅读、命令面板搜索、候选概念确认、后台生成专文、知识地图、回退路径。
- 关键用户动作：
  切文章、开搜索、建源文章、编辑保存、点击概念、确认/忽略候选、打开专文。
- 高风险点：
  URL 参数与持久化状态恢复、候选概念生命周期、导读拼装、移动端抽屉。

- 模块名称：
  图谱。
- 主要能力：
  视图切换、深度调节、关系筛选、当前节点聚焦、节点侧栏。
- 关键用户动作：
  切换主干/全图/前置/误解、拖动画布、筛边、点击节点。
- 高风险点：
  React Flow 渲染稳定性、边 ID 唯一性、节点过多时折叠。

- 模块名称：
  练习 / 复习 / 总结。
- 主要能力：
  生成题目、提交答案、结果反馈、进入复习、展示本轮总结。
- 关键用户动作：
  开始练习、重新生成、提交答案、跳过/稍后提醒、继续下一个。
- 高风险点：
  AI 依赖、空态与结果态切换、依赖真实会话数据。

- 模块名称：
  资产 / 统计 / 设置。
- 主要能力：
  搜索和收藏表达资产、查看统计、导出主题、配置 AI 与图谱设置。
- 关键用户动作：
  搜索筛选、收藏、导出、保存设置、重置。
- 高风险点：
  空态、导出下载、服务健康面板、避免误改用户配置。

## 4. Actionable Control Inventory
- Control:
  创建学习主题
- Type:
  表单提交按钮
- Page / Route:
  `/`
- Purpose:
  创建新主题并跳转到文章工作台
- Preconditions:
  标题和内容非空
- Risk:
  高

- Control:
  最近主题卡片 / 继续学习
- Type:
  卡片点击 / 按钮
- Page / Route:
  `/`
- Purpose:
  返回已有主题
- Preconditions:
  至少 1 个 active topic
- Risk:
  高

- Control:
  当前主题 > 学习 / 图谱 / 资产
- Type:
  全局侧栏快捷导航
- Page / Route:
  全局壳层页面
- Purpose:
  从任意页面回到主题
- Preconditions:
  Zustand 中存在 `current_topic_id`
- Risk:
  高

- Control:
  搜索 / 新建源文章 / 标记完成
- Type:
  顶部动作按钮
- Page / Route:
  `/topic/:topicId/learn`
- Purpose:
  打开命令面板、创建源文章、推进阅读状态
- Preconditions:
  有效 topic
- Risk:
  高

- Control:
  源文章编辑 / 保存并重新分析
- Type:
  双态按钮 + 文本编辑区
- Page / Route:
  `/topic/:topicId/learn`
- Purpose:
  写文章并触发概念分析
- Preconditions:
  当前文章是 source article
- Risk:
  高

- Control:
  候选概念确认 / 忽略 / 打开专文
- Type:
  抽屉按钮
- Page / Route:
  `/topic/:topicId/learn`
- Purpose:
  推进 candidate -> confirmed -> article
- Preconditions:
  源文章中出现候选概念
- Risk:
  高

- Control:
  图谱视图切换 / 深度 / 关系类型
- Type:
  切换按钮 / slider / 复选框弹层
- Page / Route:
  `/topic/:topicId/graph`
- Purpose:
  控制图谱可视范围
- Preconditions:
  图谱数据存在
- Risk:
  中

- Control:
  开始定义练习 / 重新生成 / 提交答案
- Type:
  按钮 + 文本域
- Page / Route:
  `/topic/:topicId/practice`
- Purpose:
  完成一次练习
- Preconditions:
  有效 nodeId，AI 提供商可用
- Risk:
  中

- Control:
  导出当前主题
- Type:
  下拉框 + 下载按钮
- Page / Route:
  `/settings`
- Purpose:
  导出当前主题资料
- Preconditions:
  `current_topic_id` 有值
- Risk:
  中

## 5. Key States
- Loading:
  首页主题列表、工作台 bundle、图谱、练习题目、设置、统计、复习都依赖远端加载。
- Empty:
  首页无主题、资产空态、复习空态、图谱空态、统计无能力数据。
- Error:
  各页面大多有 `ErrorState` 或等价重试分支；图谱和设置属于高价值错误面。
- Success:
  创建主题成功跳到 learn，候选概念确认后静默生成专文，设置导出触发下载。
- Destructive confirm:
  首页删除主题使用确认框；本轮未执行删除。
- Responsive breakpoints:
  learn 页移动端切为顶部动作栏 + 可收起文章库；其他页面走普通响应式栅格。

## 6. Dependencies / Preconditions
- 登录态 / 账号：
  无显式登录。
- 测试数据：
  需要至少 1 个 active topic；若要覆盖 review/practice/assets/stats 的正向内容，还需要 practice attempts、review items、expression assets、ability snapshots。
- Feature flags：
  无显式 feature flag；AI provider 和服务健康状态会改变 UI 分支。
- 外部服务 / 第三方回调：
  FastAPI 后端、SQLite、Neo4j、LanceDB、AI provider；前端通过 Vite 代理访问 `/api/v1`。

## 7. Audit Waves
- Wave:
  首页与全局入口
- Scope:
  主题创建、最近学习、当前主题快捷导航
- Priority:
  P0
- Blocking risks:
  持久化状态污染入口 URL

- Wave:
  文章工作台主路径
- Scope:
  导读、概念专文、源文章编辑、候选概念确认、后台生成、命令面板、移动端
- Priority:
  P0
- Blocking risks:
  entry-node 数据形状不一致、URL 参数恢复、异步生成链路

- Wave:
  图谱
- Scope:
  视图按钮、关系筛选、控制面板、控制台错误
- Priority:
  P1
- Blocking risks:
  React Flow 边渲染稳定性

- Wave:
  次级页面
- Scope:
  练习、复习空态、统计、设置、导出、资产空态
- Priority:
  P1
- Blocking risks:
  真实数据不足导致部分正向流程不可达
