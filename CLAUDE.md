# AxonClone — 项目级 Claude Code 规范

> 本文件是 Claude Code 在此项目中工作时必须遵守的规范。优先级高于全局 CLAUDE.md。

## 产品本质

AxonClone 不是聊天产品，不是知识库浏览器，而是**围绕"知识展开 + 表达训练 + 成长诊断"构建的桌面 AI 学习操作系统**。

核心价值链：**内容拆解 → 知识网络化 → 表达训练 → 能力诊断 → 长期资产沉淀 → 间隔复习**

一句话体验流程：**从内容进入、在节点聚焦、通过练习表达、以总结沉淀、靠复习巩固。**

## 技术栈（已确定，不可自行替换）

| 层         | 技术                                                       |
| ---------- | ---------------------------------------------------------- |
| 桌面壳     | **Tauri v2** + React + TypeScript + Vite                   |
| 前端 UI    | Tailwind CSS + Zustand（UI 状态）+ React Query（服务状态） |
| 图谱可视化 | **React Flow**                                             |
| 后端       | **FastAPI** + Python 3.12 + Pydantic                       |
| AI 调用    | **OpenAI Responses API**（结构化 JSON Schema 输出）         |
| 图存储     | **Neo4j**（节点、边、Topic-Node 组织关系）                 |
| 向量存储   | **LanceDB**（语义去重、相似节点推荐）                       |
| 业务状态   | **SQLite**（会话、设置、练习记录、表达资产、能力分数）      |
| 本地 Fallback | Ollama（可选，MVP 非必需）                                |

## 项目目录结构

```
project-root/
  src/              # React 前端（组件、页面、hooks、stores、services、types）
  src-tauri/        # Tauri 桌面壳与 sidecar 配置
  backend/          # FastAPI 后端
    api/            # 路由层
    services/       # 业务编排层
    agents/         # AI 角色逻辑（Explorer/Diagnoser/Tutor/Synthesizer）
    models/         # Pydantic 数据模型
    repositories/   # 数据库访问层
    graph/          # Neo4j 图谱操作
    vector/         # LanceDB 向量操作
    sessions/       # 学习会话与复习逻辑
    settings/       # 配置与模型切换
  docs/             # 项目文档（10份设计文档）
  scripts/          # 启动、初始化、打包脚本
  data/             # 本地运行数据（不入库）
    sqlite/
    lancedb/
    logs/
    exports/
    cache/
```

## 核心对象模型（全系统统一）

所有业务 ID 格式：`tp_xxx`（Topic）、`nd_xxx`（Node）、`eg_xxx`（Edge）、`ss_xxx`（Session）、`ea_xxx`（表达资产）、`rv_xxx`（复习）、`fr_xxx`（卡点）、`ab_xxx`（能力快照）

### 对象关系主线

```
Topic（学习主题容器）
 ├── Node（知识节点，基础学习单元）
 │     ├── Edge（关系边：prerequisite/contrast/variant/applies_in/extends/misunderstood_as）
 │     ├── AbilityRecord（8维能力评分：understand/example/contrast/apply/explain/recall/transfer）
 │     ├── ExpressionAsset（用户原文 + AI优化版 + 表达骨架）
 │     ├── MisconceptionRecord（误解记录）
 │     └── ReviewItem（复习任务）
 ├── Session（学习会话，一轮学习的时间容器）
 └── LearningIntent（学习意图：fix_gap/solve_task/build_system/prepare_expression/prepare_interview）
```

### 关键反哺闭环
- 练习结果 → 更新 AbilityRecord → 影响推荐节点
- 卡点 FrictionRecord → 影响复习优先级和路径推荐
- 表达资产 → 影响后续训练提示
- 误解记录 → 影响节点展示内容和对比题生成

## AI 四角色架构（严格职责分离）

| 角色           | 职责                               | 可读写对象                              |
| -------------- | ---------------------------------- | --------------------------------------- |
| **Explorer**   | 节点抽取、关系生成、路径建议       | Topic/Node/Edge（只生成，不评估）      |
| **Diagnoser**  | 卡点识别、能力短板、误解模式       | AbilityRecord/FrictionRecord（只评估） |
| **Tutor**      | 教学对话、出题、表达反馈           | ExpressionAsset（生成评估+优化）       |
| **Synthesizer** | 收束总结、复习任务生成            | Session/ReviewItem（总结+调度）        |

### 关键约束
- 每个角色对应独立 service 函数，**只允许读写自己负责的对象**
- Tutor 不得直接写 FrictionRecord，Diagnoser 不得直接写 ExpressionAsset
- AI 输出必须经过 schema 校验后才能写入数据库
- 每个 prompt 单一职责，不混搭任务

## 前端架构规则

### 路由设计
- `/` — 首页（创建 Topic + 恢复学习 + 待学入口）
- `/topic/:topicId/learn` — 学习页（聚焦当前节点）
- `/topic/:topicId/graph` — 图谱页（全局结构辅助视图，非默认主页）
- `/topic/:topicId/practice` — 练习页（表达训练）
- `/stats` — 统计页（成长与复习）
- `/reviews` — 复习页
- `/settings` — 设置页

### 状态管理边界
- **React Query** 管理所有服务端数据（Topic 列表、Node 详情、图谱、练习、复习队列、统计）
- **Zustand** 仅管理瞬时 UI 状态（当前 Topic/Node/Session ID、图谱视图状态、练习未提交文本、UI 开关）
- 不要在 Zustand 中复制 React Query 缓存的服务端数据

### 练习页状态机
```
idle → loading_prompt → answering → submitting → feedback_ready → saving_asset → completed
```

### 图谱页约束
- 默认只展示主干链，不一次性展开所有节点
- 当前节点最强高亮，支线弱化显示
- 误解边使用特殊视觉样式
- 单 Topic 最大节点数限制 30，超过强制折叠支线

## 后端架构规则

### API 基础
- Base URL: `http://127.0.0.1:8000/api/v1`
- 统一响应格式: `{ success, data, meta, error }`
- 接口围绕**学习动作**设计，不是 CRUD
- 错误信息必须可诊断（前端据此决定降级/重试/报错）

### 接口联调优先级
**P0 必先跑通**：
1. `POST /topics` — 创建主题
2. `GET /topics/{id}` — 获取主题详情
3. `GET /topics/{id}/nodes/{id}` — 节点详情
4. `POST /topics/{id}/sessions` — 开始会话
5. `POST /topics/{id}/nodes/{id}/practice` — 获取练习题
6. `POST /topics/{id}/nodes/{id}/practice/submit` — 提交练习
7. `POST /topics/{id}/sessions/{id}/complete` — 完成会话
8. `GET /topics/{id}/graph` — 获取图谱
9. `GET/PATCH /settings` — 设置

### 数据写入顺序
```
SQLite（元数据）→ Neo4j（图谱）→ LanceDB（向量）
```
失败时记录补偿任务或回滚标记，不静默丢失。

## 数据库规则

### 存储职责分离
- **Neo4j**: 知识图谱（Node/Edge/Topic-Node 组织关系、Misconception、Evidence、ReviewAnchor）
- **LanceDB**: 语义向量（concept_embeddings、topic_embeddings）
- **SQLite**: 用户业务状态（settings/topics/sessions/ability_records/expression_assets/practice_attempts/review_items/friction_records/deferred_nodes）

### 图谱写入校验（强制）
任何 AI 输出写入 Neo4j 前必须经过：
1. Schema 校验
2. 关系类型白名单校验（只有 PREREQUISITE/CONTRASTS/VARIANT_OF/APPLIES_IN/EXTENDS/MISUNDERSTOOD_AS）
3. LanceDB 语义去重（>=0.92 视为重复候选）
4. 字段完整性校验
5. Topic 上下文一致性校验

### 向量去重阈值
- `>=0.92`: 高概率重复
- `0.85-0.92`: 相似候选，需二次判断
- `<0.85`: 视为新节点

## 核心算法规则

### 知识图谱遍历
采用**主干优先的混合遍历**：主干 BFS + 高价值支点限深 DFS + 全局收束控制

### 节点扩展控制
- 每次扩展 3-5 个节点
- 单轮 session 新增不超过 8-12 个节点
- 深度上限默认 2-3

### 能力更新规则
- 一次练习只更新相关维度（define → understand/explain，contrast → contrast/explain）
- 单次增量不超过 +10，单次降量不超过 -5
- 一次失败不大幅清零
- 复习失败优先影响 recall/explain

### 复习优先级
```
ReviewPriority = Importance × ForgetRisk × ExplainGap × ConfusionRisk × TimeDueWeight
```

### 表达训练顺序（推荐）
define → example → contrast → apply → teach_beginner → compress

## 学习意图对 AI 行为的影响（关键控制变量）

| 意图              | Explorer 行为         | Tutor 行为              | Diagnoser 行为           |
| ----------------- | --------------------- | ----------------------- | ------------------------ |
| fix_gap          | 优先 prerequisite      | 优先直觉解释与例子       | 优先看前置缺失           |
| build_system     | 优先主干结构           | 正常流程                 | 正常流程                 |
| solve_task       | 优先最短路径（2-5节点） | 优先应用表达             | 正常流程                 |
| prepare_expression | 正常流程            | 提高表达练习密度         | 关注结构/自然度/受众适配 |
| prepare_interview | 正常流程            | 优先应用+对比            | 优先表达薄弱维度         |

## 失败降级策略

| 角色失败         | 降级行为                                                     |
| ---------------- | ------------------------------------------------------------ |
| Explorer 失败    | 至少返回一个起始节点（名称+summary+why_now），不写完整图谱  |
| Diagnoser 失败   | 不更新 friction tags，仅返回通用反馈                          |
| Tutor 失败       | 返回静态练习模板，前端允许用户继续记录表达                    |
| Synthesizer 失败 | 根据 session 记录做规则型总结（访问节点数+练习次数+下一步建议） |

## 环境变量（`.env`，后端专用）

```
OPENAI_API_KEY=
OPENAI_MODEL_DEFAULT=
OPENAI_EMBED_MODEL=
NEO4J_URI=
NEO4J_USER=
NEO4J_PASSWORD=
LANCEDB_PATH=
SQLITE_PATH=
OLLAMA_BASE_URL=
OLLAMA_ENABLED=false
APP_ENV=development
LOG_LEVEL=INFO
```

## 编码规范

### Python 后端
- 遵循项目已有风格，使用 Ruff/Black
- 所有对外接口用 Pydantic model 定义，不写裸 dict
- AI 输出 schema 与数据库 model 统一命名

### TypeScript 前端
- 遵循项目已有 ESLint/Prettier 配置
- 核心类型与后端 Pydantic model 对齐，使用 adapter 层做必要转换
- 不在前端自行派生多个不兼容结构

### 命名约定
- 后端返回字段用 snake_case
- 前端类型属性用 snake_case（与后端对齐，不做 camelCase 转换）
- 组件名用 PascalCase，文件名用 kebab-case

## MVP / V1 / V2 范围边界

### MVP（当前阶段）
输入解析、基础节点生成、节点学习页、基础图谱页、Study 表达训练、基础能力评分、收束总结、待学堆栈、统计页基础、设置页

### MVP 不做
多用户协作、云端部署、复杂移动端适配、企业组织管理、全自动大规模导入、高级多模态、误解图谱可视化

### V1 增强
卡点识别、误解图谱、表达资产库、待学堆栈增强、更强路径推荐

### V2 进阶
文章自动转课程、个性化表达画像、多模态输入、项目任务桥接、高级复习策略

## 开发顺序约束

1. **先定义对象，再写接口** — Pydantic model 先于 API route
2. **先保证主闭环，再做高级能力** — 跑通"输入→学习→练习→总结→状态保存"
3. **AI 与业务逻辑分层** — AI 只生成结构结果和反馈，不直接管理业务状态
4. **图谱写入必须有校验层** — AI 输出不可直接写入 Neo4j

## 关键设计文档索引

全部在 `docs/` 目录下：
- `axon_clone_详细prd（产品需求文档）.md` — 产品需求与验收标准
- `axon_clone_信息架构文档（ia）.md` — 核心对象与信息优先级
- `axon_clone_页面流文档（page_flow）.md` — 页面流转与异常兜底
- `axon_clone_ai_系统设计文档（ai_system_design）.md` — AI 四角色与 prompt 设计
- `axon_clone_前端实现与组件设计文档.md` — 前端组件与状态管理
- `axon_clone_后端接口文档（api_spec）.md` — 完整 API 定义
- `axon_clone_技术选型文档.md` — 技术选型决策与风险评估
- `axon_clone_数据库设计文档（db_design）.md` — 三库混合存储方案
- `axon_clone_测试与验收文档（qa_uat）.md` — 测试分层与发布门槛
- `axon_clone_算法与学习策略文档.md` — 图谱遍历/能力更新/复习调度算法
- `axon_clone_部署运维与开发环境文档.md` — 本地开发/打包/健康检查
 不使用docker！！！

任何实现决策与文档冲突时，**以文档为准**，并及时回写规范。
 不使用docker！！！
