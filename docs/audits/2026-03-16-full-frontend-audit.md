# Full Frontend Audit Report

## 1. Audit Summary
- 模式：full-surface
- 环境地址：
  `http://127.0.0.1:5173`
- 审测范围：
  首页、文章工作台、图谱、练习、复习、统计、设置、导出、资产空态、移动端工作台。
- 不在范围内：
  Tauri 桌面壳、Summary 页正向流程、删除/归档主题、设置保存/重置、复习详情提交、练习提交答案与保存资产、404 页。

## 2. Coverage Summary
- 已覆盖页面 / 模块：
  `/`
  `/topic/:topicId/learn`
  `/topic/:topicId/graph`
  `/topic/:topicId/practice`
  `/topic/:topicId/assets`
  `/stats`
  `/reviews`
  `/settings`
- 已覆盖控件数量或类别：
  主题创建、当前主题快捷导航、文章切换、命令面板、源文章创建与编辑、候选概念确认、专文生成与打开、图谱视图和关系筛选、练习起题、设置导出、移动端文章库切换。
- 被阻塞项：
  无硬阻塞，但 review/detail、summary、asset 非空态、practice 提交与 asset 保存依赖额外业务数据，本轮未覆盖。
- 跳过项及原因：
  删除/归档主题：属于破坏性动作，本轮不执行。
  设置保存/重置：会改用户真实配置，本轮不执行。
  练习提交答案与保存资产：不属于本轮分支改动核心，且会产生额外 AI 写入。
  Summary 正向页：需要完整 session summary 数据或路由 state。

## 3. Wave Results
- Wave:
  首页与全局入口
- Scope:
  创建主题、最近学习、当前主题快捷导航
- Pages covered:
  `/`
- Controls covered:
  标题输入、内容输入、创建主题、最近主题卡片、继续学习、当前主题快捷入口。
- Key states covered:
  首页正常态、创建成功跳转。
- Findings:
  发现“当前主题 > 学习”快捷入口会带着失效 `nodeId` 进入坏状态。
- Evidence:
  浏览器实际打开了 `/topic/tp_11768sfd/learn?nodeId=nd_fake`，阅读区标题和面包屑直接出现 `nd_fake`。
- Console / Network:
  `POST /api/v1/topics` 200，创建主题后实际跳转到新主题工作台。

- Wave:
  文章工作台主路径
- Scope:
  导读、概念专文、命令面板、源文章编辑、候选概念确认、后台生成、打开专文、移动端
- Pages covered:
  `/topic/tp_11768sfd/learn`
  `/topic/tp_qzlktp1f/learn`
- Controls covered:
  切换概念专文、搜索按钮、命令面板输入、创建源文章、编辑、保存并重新分析、候选概念确认、打开专文、移动端文章库切换。
- Key states covered:
  guide/source/concept 三种文章态、candidate -> confirmed -> generating -> ready、移动端文章库展开/收起。
- Findings:
  发现旧主题导读文案出现 `undefined`，根因是同一 `entry-node` 接口返回了两种结构。
- Evidence:
  旧主题 `tp_11768sfd` 的导读 banner 显示“从 undefined 出发”，正文显示“从 undefined 开始”；同一接口对新主题返回扁平结构，对旧主题返回 `{ node: ... }` 包裹结构。
- Console / Network:
  `GET /api/v1/topics/tp_11768sfd/entry-node` 与 `GET /api/v1/topics/tp_qzlktp1f/entry-node` 响应形状不一致。

- Wave:
  图谱
- Scope:
  视图切换、深度 slider、关系类型筛选、React Flow 画布
- Pages covered:
  `/topic/tp_11768sfd/graph`
- Controls covered:
  主干 / 全图 / 前置 / 误解、深度 slider、关系类型弹层。
- Key states covered:
  正常态、关系类型弹层展开。
- Findings:
  图谱页出现 React key 警告，说明边渲染存在不稳定 identity。
- Evidence:
  浏览器控制台报错：`Each child in a list should have a unique "key" prop ... child from EdgeRenderer`。
- Console / Network:
  页面功能可用，但控制台有 1 条 error。

- Wave:
  次级页面
- Scope:
  练习、复习空态、统计、设置、导出、资产空态
- Pages covered:
  `/topic/tp_11768sfd/practice?nodeId=nd_rfdrmvzt`
  `/reviews`
  `/stats`
  `/settings`
  `/topic/tp_11768sfd/assets`
- Controls covered:
  开始定义练习、复习空态、统计概览、设置页导出、资产空态“前往练习”。
- Key states covered:
  practice 起题成功、review empty、stats no-ability、assets empty、settings export success。
- Findings:
  无新增功能性缺陷。
- Evidence:
  练习页成功生成题目；设置页导出成功下载 `图神经网络入门.md`。
- Console / Network:
  设置页导出请求成功；无新的前端报错。

## 4. Findings
- Severity:
  High
- Title:
  “当前主题 > 学习”快捷入口会带入失效 `nodeId`，把用户送进损坏的阅读状态
- Area:
  全局侧栏 / 文章工作台入口
- Repro:
  1. 打开任意带全局壳层的页面，例如 `/stats`。
  2. 点击侧栏 `当前主题 > 学习`。
  3. 观察地址栏与阅读区。
- Expected:
  应进入当前主题的有效文章入口，至少应回到 guide 或最近有效 article，而不是使用未校验的失效节点。
- Actual:
  实际进入 `/topic/tp_11768sfd/learn?nodeId=nd_fake`，面包屑和文章标题显示 `nd_fake`，正文为空。
- Evidence:
  浏览器快照显示 `nd_fake` 出现在 breadcrumb 和 H1；侧栏链接本身也渲染为 `/topic/tp_11768sfd/learn?nodeId=nd_fake`。
  代码上 [app-layout.tsx](/Users/zhaozengqing/Downloads/图学习/src/app/app-layout.tsx#L67) 直接拼接 `current_node_id`，而 [app-store.ts](/Users/zhaozengqing/Downloads/图学习/src/stores/app-store.ts#L61) 将其持久化且没有任何校验或失效清理。

- Severity:
  Medium
- Title:
  旧主题导读会把 `undefined` 渲染进正文和标题
- Area:
  文章工作台导读拼装
- Repro:
  1. 打开 `/topic/tp_11768sfd/learn`。
  2. 停留在 guide 文章。
  3. 查看 banner 和正文首段。
- Expected:
  导读应使用有效入口概念，或在入口概念不可用时退回到不引用概念名的兜底文案。
- Actual:
  页面显示“从 undefined 出发”“从 undefined 开始 undefined 是这条阅读路径的入口概念。”
- Evidence:
  浏览器快照直接出现上述文案。
  网络上同一接口对旧主题返回 `data.node.name`，对新主题返回 `data.name`，而前端服务层 [index.ts](/Users/zhaozengqing/Downloads/图学习/src/services/index.ts#L71) 和类型 [index.ts](/Users/zhaozengqing/Downloads/图学习/src/types/index.ts#L84) 只接受扁平 `EntryNode`。
  后端入口接口 [nodes.py](/Users/zhaozengqing/Downloads/图学习/backend/api/nodes.py#L16) 返回 `node_service.get_entry_node()` 的结果；该服务在 `current_node_id` 存在时会直接返回完整 node detail，而在正常 entry-node 分支返回扁平对象，见 [node_service.py](/Users/zhaozengqing/Downloads/图学习/backend/services/node_service.py#L32) 和 [node_service.py](/Users/zhaozengqing/Downloads/图学习/backend/services/node_service.py#L63)。
  前端导读拼装在 [article-workspace.ts](/Users/zhaozengqing/Downloads/图学习/src/lib/article-workspace.ts#L145) 对 `entryNode.name` 和 `entryNode.summary` 没有做结构兜底。

- Severity:
  Low
- Title:
  图谱页渲染存在 React key 警告
- Area:
  React Flow 图谱渲染
- Repro:
  1. 打开 `/topic/tp_11768sfd/graph`。
  2. 等待画布渲染。
  3. 查看浏览器控制台。
- Expected:
  图谱渲染不应产生 React key 警告。
- Actual:
  控制台报错：`Each child in a list should have a unique "key" prop. Check the render method of div. It was passed a child from EdgeRenderer.`
- Evidence:
  Playwright 控制台抓到上述错误。
  前端边数据直接使用后端 `edge_id` 作为 React Flow edge id，见 [graph-adapter.ts](/Users/zhaozengqing/Downloads/图学习/src/components/shared/graph-adapter.ts#L54)。当前需要继续确认是否是后端 edge_id 冲突，或前端在筛边/折叠后生成了重复子元素。

## 5. Coverage Gaps
- 未覆盖页面 / 模块：
  `summary` 正向页，review detail 正向页，assets 非空态。
- 未覆盖控件：
  删除主题、归档主题、设置保存、设置重置、练习提交答案、保存表达资产、review 提交/跳过/稍后提醒。
- 原因：
  这些路径要么是破坏性操作，要么依赖额外业务数据，要么会写入用户真实配置；本轮按审计优先级跳过。

## 6. Automation Handoff
- 建议新增 / 更新的测试文件：
  暂不进入自动化补测阶段。
- 推荐优先覆盖的路径：
  先修复 Findings 里的三个问题，再补 E2E。
- 推荐关键断言：
  修复后再定义。
- 依赖的稳定选择器：
  修复后再定义。
- 需要补的 testability patch：
  目前不建议继续加测试性补丁，先处理已确认缺陷。
