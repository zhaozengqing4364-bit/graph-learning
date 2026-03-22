# AxonClone 数据库设计文档（DB Design）

## 一、文档目的

本文档用于定义 AxonClone 的数据存储方案、核心数据对象、数据库职责划分、表结构/图结构设计、索引策略、关系约束、读写路径、数据生命周期与演进原则，作为后端开发、数据层实现、接口设计、图谱写入逻辑和后续扩展的统一依据。

AxonClone 不是单一数据库即可完成所有需求的产品。它同时包含：
- 知识节点与关系网络
- 语义相似检索与去重
- 用户学习会话
- 能力记录与卡点记录
- 表达资产与复习任务
- 系统配置与本地状态

因此推荐采用 **图数据库 + 向量数据库 + 轻量关系型存储** 的混合架构。

---

## 二、数据库总体架构

## 2.1 存储层职责划分

### 1）Neo4j
用于存储知识网络与图关系，承载：
- Topic 与 Node 的组织关系
- Node 与 Node 的 prerequisite / contrast / applies_in / extends 等关系
- Topic 内主干链与支线链组织
- 节点与误解、证据、复习对象的图式关联

### 2）LanceDB
用于存储向量索引，承载：
- 节点语义向量
- 相似节点查重
- 相似概念推荐
- 输入内容与已有主题/节点的相似匹配

### 3）SQLite
用于存储用户本地业务状态，承载：
- 用户设置
- 学习会话记录
- 表达资产
- 能力分数快照
- 卡点记录
- 复习任务
- 页面状态缓存
- 导出记录

---

## 三、数据库设计原则

### 3.1 一类数据只放在最合适的存储层
不要把所有数据都压进 Neo4j，也不要把图关系扁平写进 SQLite。

### 3.2 图谱写入必须经过校验层
任何 AI 输出都不能直接写入图数据库，必须经过：
- schema 校验
- 关系类型白名单校验
- 相似节点去重校验
- 字段完整性校验
- Topic 上下文一致性校验

### 3.3 用户状态与知识结构适度解耦
知识结构是产品公共底层，用户学习状态是用户私有演进层。两者应通过稳定 ID 关联，而不是混在一起。

### 3.4 数据模型必须支持未来扩展
当前是单机单用户版本，但对象设计要预留：
- user_id
- workspace_id
- source_type
- version
- status
- confidence

### 3.5 优先支持“可恢复”“可追溯”“可重建”
学习产品的数据层不只要会存，还要支持：
- 从上次会话恢复
- 回看某一轮学习过程
- 重建某个 Topic 的主干路径
- 追踪能力变化与误解修正过程

---

## 四、统一对象标识设计

建议所有核心对象采用统一 ID 规则。

### 4.1 ID 建议
- `topic_id`：`tp_xxx`
- `node_id`：`nd_xxx`
- `edge_id`：`eg_xxx`
- `session_id`：`ss_xxx`
- `asset_id`：`ea_xxx`
- `review_id`：`rv_xxx`
- `friction_id`：`fr_xxx`
- `ability_snapshot_id`：`ab_xxx`

### 4.2 命名原则
- 使用字符串 ID，而不是数据库自增 ID 暴露到业务层
- 前后端、AI、数据库统一使用同一业务 ID
- 图数据库与 SQLite 使用同一业务 ID 关联

---

## 五、Neo4j 图模型设计

## 5.1 节点类型定义

建议定义以下主要 Label：

### 1）Topic
表示学习主题容器。

字段建议：
- `topic_id`
- `title`
- `source_type`
- `source_content_digest`
- `learning_intent`
- `mode`
- `status`
- `created_at`
- `updated_at`

### 2）Concept
表示知识节点。

字段建议：
- `node_id`
- `name`
- `summary`
- `why_it_matters`
- `importance`
- `status`
- `confidence`
- `topic_id`
- `created_at`
- `updated_at`

### 3）Misconception
表示误解对象。

字段建议：
- `misconception_id`
- `text`
- `severity`
- `topic_id`
- `created_at`

### 4）Evidence
表示证据对象，用于后续多模态或来源绑定。

字段建议：
- `evidence_id`
- `source_type`
- `source_ref`
- `excerpt`
- `topic_id`

### 5）ReviewAnchor
表示图谱视角下的复习锚点。

字段建议：
- `review_anchor_id`
- `node_id`
- `priority`
- `topic_id`

---

## 5.2 关系类型定义

关系类型应保持严格收敛，建议第一阶段仅开放以下几类：

- `HAS_NODE`：`(Topic)-[:HAS_NODE]->(Concept)`
- `PREREQUISITE`：`(Concept)-[:PREREQUISITE]->(Concept)`
- `CONTRASTS`：`(Concept)-[:CONTRASTS]->(Concept)`
- `VARIANT_OF`：`(Concept)-[:VARIANT_OF]->(Concept)`
- `APPLIES_IN`：`(Concept)-[:APPLIES_IN]->(Concept)`
- `EXTENDS`：`(Concept)-[:EXTENDS]->(Concept)`
- `MISUNDERSTOOD_AS`：`(Concept)-[:MISUNDERSTOOD_AS]->(Concept)`
- `HAS_MISCONCEPTION`：`(Concept)-[:HAS_MISCONCEPTION]->(Misconception)`
- `EVIDENCED_BY`：`(Concept)-[:EVIDENCED_BY]->(Evidence)`
- `HAS_REVIEW_ANCHOR`：`(Concept)-[:HAS_REVIEW_ANCHOR]->(ReviewAnchor)`

每条边建议包含属性：
- `edge_id`
- `reason`
- `weight`
- `confidence`
- `created_at`

---

## 5.3 Topic 与 Concept 组织关系

每个 Topic 内部应形成一张局部知识图谱，因此同名节点在不同 Topic 中建议优先复用语义层，但图谱实例层仍需绑定 Topic。

### 推荐策略
- 语义实体以 `canonical_name` 为基础
- Topic 内部实例以 `topic_id + node_id` 管理
- MVP 阶段可简化为每个 Topic 内使用独立 `node_id`
- V2 阶段再引入全局 canonical concept 层

---

## 5.4 Neo4j 约束与索引建议

### 唯一约束
- Topic.topic_id 唯一
- Concept.node_id 唯一
- Misconception.misconception_id 唯一
- Evidence.evidence_id 唯一

### 索引建议
- Topic.title
- Topic.learning_intent
- Concept.name
- Concept.topic_id
- Concept.importance
- Concept.status
- Misconception.topic_id

---

## 六、LanceDB 向量表设计

## 6.1 表用途

向量层不作为权威知识结构来源，而作为语义辅助层，主要承担：
- 新节点与已有节点的语义去重
- 相似节点推荐
- 输入内容与已有主题的相似匹配
- 后续文档片段与节点的轻量检索

---

## 6.2 表一：`concept_embeddings`

### 字段建议
- `id`：对应 `node_id`
- `topic_id`
- `name`
- `summary`
- `text_for_embedding`
- `vector`
- `importance`
- `updated_at`

### embedding 文本拼接建议
建议拼接：
- name
- summary
- why_it_matters
- top misconceptions
- top applications

这样相似度更接近真实知识语义，而不只是短 summary。

---

## 6.3 表二：`topic_embeddings`

### 字段建议
- `id`：对应 `topic_id`
- `title`
- `source_digest`
- `learning_intent`
- `topic_summary`
- `vector`
- `updated_at`

### 作用
用于：
- 查找相似学习主题
- 首页推荐继续学习
- 防止用户重复创建极其相似的 Topic

---

## 6.4 相似度阈值建议

MVP 阶段建议保守：
- `>=0.92`：高概率重复候选
- `0.85-0.92`：相似候选，人工/规则二次判断
- `<0.85`：通常视为新节点

实际阈值需通过样本调参。

---

## 七、SQLite 表结构设计

SQLite 负责本地业务状态，是产品可恢复、可统计、可复习的关键。

## 7.1 `app_settings`

### 用途
存储全局设置。

### 字段建议
- `key` TEXT PRIMARY KEY
- `value` TEXT
- `updated_at` TEXT

### 示例 key
- `default_model`
- `default_learning_intent`
- `default_topic_mode`
- `auto_start_practice`
- `auto_generate_summary`
- `max_graph_depth`
- `ollama_enabled`

---

## 7.2 `topics`

### 用途
存储 Topic 元数据与本地业务属性。

### 字段建议
- `topic_id` TEXT PRIMARY KEY
- `title` TEXT
- `source_type` TEXT
- `source_content` TEXT
- `learning_intent` TEXT
- `mode` TEXT
- `status` TEXT
- `current_node_id` TEXT
- `last_session_id` TEXT
- `created_at` TEXT
- `updated_at` TEXT
- `archived_at` TEXT NULL

---

## 7.3 `sessions`

### 用途
记录每轮学习会话。

### 字段建议
- `session_id` TEXT PRIMARY KEY
- `topic_id` TEXT
- `entry_node_id` TEXT
- `start_time` TEXT
- `end_time` TEXT NULL
- `status` TEXT
- `summary_json` TEXT NULL
- `visited_count` INTEGER DEFAULT 0
- `practice_count` INTEGER DEFAULT 0

### 索引建议
- `topic_id`
- `status`
- `start_time`

---

## 7.4 `session_nodes`

### 用途
记录某次会话中访问过哪些节点。

### 字段建议
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `session_id` TEXT
- `node_id` TEXT
- `visit_order` INTEGER
- `entered_at` TEXT
- `left_at` TEXT NULL
- `action_type` TEXT

### 说明
便于重建学习路径、统计用户浏览主干还是支线。

---

## 7.5 `ability_records`

### 用途
存储每个用户在每个节点上的最新能力状态。

### 字段建议
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `topic_id` TEXT
- `node_id` TEXT
- `understand_score` INTEGER
- `example_score` INTEGER
- `contrast_score` INTEGER
- `apply_score` INTEGER
- `explain_score` INTEGER
- `recall_score` INTEGER
- `transfer_score` INTEGER
- `updated_at` TEXT

### 唯一约束建议
- `(topic_id, node_id)`

---

## 7.6 `ability_snapshots`

### 用途
存储能力变化历史，用于趋势分析。

### 字段建议
- `ability_snapshot_id` TEXT PRIMARY KEY
- `topic_id` TEXT
- `node_id` TEXT
- `session_id` TEXT
- `understand_score` INTEGER
- `example_score` INTEGER
- `contrast_score` INTEGER
- `apply_score` INTEGER
- `explain_score` INTEGER
- `recall_score` INTEGER
- `transfer_score` INTEGER
- `source` TEXT
- `created_at` TEXT

---

## 7.7 `friction_records`

### 用途
记录卡点标签与诊断结果。

### 字段建议
- `friction_id` TEXT PRIMARY KEY
- `topic_id` TEXT
- `node_id` TEXT
- `session_id` TEXT
- `friction_type` TEXT
- `severity` INTEGER
- `evidence_text` TEXT
- `suggested_next_node_id` TEXT NULL
- `created_at` TEXT

### friction_type 枚举建议
- prerequisite_gap
- concept_confusion
- lack_of_example
- weak_structure
- abstract_overload
- weak_recall
- weak_application

---

## 7.8 `expression_assets`

### 用途
存储用户表达资产。

### 字段建议
- `asset_id` TEXT PRIMARY KEY
- `topic_id` TEXT
- `node_id` TEXT
- `session_id` TEXT NULL
- `expression_type` TEXT
- `user_expression` TEXT
- `ai_rewrite` TEXT
- `skeleton` TEXT
- `quality_tags` TEXT
- `created_at` TEXT
- `favorited` INTEGER DEFAULT 0

### 索引建议
- `topic_id`
- `node_id`
- `expression_type`
- `favorited`

---

## 7.9 `practice_attempts`

### 用途
记录每次练习作答与 AI 反馈。

### 字段建议
- `attempt_id` TEXT PRIMARY KEY
- `topic_id` TEXT
- `node_id` TEXT
- `session_id` TEXT
- `practice_type` TEXT
- `prompt_text` TEXT
- `user_answer` TEXT
- `ai_feedback` TEXT
- `ai_score_json` TEXT
- `created_at` TEXT

---

## 7.10 `review_items`

### 用途
存储复习任务。

### 字段建议
- `review_id` TEXT PRIMARY KEY
- `topic_id` TEXT
- `node_id` TEXT
- `review_type` TEXT
- `priority` INTEGER
- `due_time` TEXT
- `status` TEXT
- `last_result` TEXT NULL
- `created_at` TEXT
- `updated_at` TEXT

### status 枚举建议
- pending
- due
- completed
- failed
- snoozed

---

## 7.11 `deferred_nodes`

### 用途
存储“稍后再学”的待学堆栈。

### 字段建议
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `topic_id` TEXT
- `node_id` TEXT
- `source_node_id` TEXT NULL
- `reason` TEXT
- `created_at` TEXT
- `resolved_at` TEXT NULL

---

## 7.12 `exports`

### 用途
存储导出记录，如后续 Anki / Markdown / JSON 导出。

### 字段建议
- `export_id` TEXT PRIMARY KEY
- `topic_id` TEXT
- `export_type` TEXT
- `file_path` TEXT
- `created_at` TEXT

---

## 八、跨库关系映射设计

## 8.1 统一主键关联

不同存储之间统一使用业务 ID：
- Neo4j Concept.node_id
- LanceDB concept_embeddings.id
- SQLite expression_assets.node_id
- SQLite ability_records.node_id

这样可避免后期跨存储对齐困难。

## 8.2 权威来源约定

建议定义：
- 图结构权威来源：Neo4j
- 语义相似权威来源：LanceDB
- 用户学习状态权威来源：SQLite

不能出现同一类核心信息在多处互相覆盖。

---

## 九、典型读写路径

## 9.1 创建 Topic

### 写入流程
1. 前端提交原始输入
2. 后端创建 topic_id
3. SQLite 写入 `topics`
4. AI 生成节点 bundle
5. 去重校验
6. Neo4j 写入 Topic、Concept、Edge
7. LanceDB 写入 concept_embeddings / topic_embeddings
8. 返回推荐起始节点

---

## 9.2 节点学习后更新能力

### 写入流程
1. 用户完成练习
2. AI 输出能力分数与卡点标签
3. SQLite 更新 `ability_records`
4. SQLite 写入 `ability_snapshots`
5. SQLite 写入 `friction_records`
6. 按需生成或更新 `review_items`

---

## 9.3 保存表达资产

### 写入流程
1. 用户提交表达
2. AI 返回优化版与骨架
3. SQLite 写入 `expression_assets`
4. 统计页和后续练习页可检索该资产

---

## 9.4 稍后再学

### 写入流程
1. 用户点击“稍后再学”
2. SQLite 写入 `deferred_nodes`
3. 首页展示待学入口

---

## 十、数据生命周期设计

## 10.1 可长期保存数据
- Topic
- Node
- Edge
- Ability snapshots
- Expression assets
- Review history
- Friction history

## 10.2 可归档但不建议删除数据
- Sessions
- Practice attempts
- Deferred nodes

## 10.3 可定期清理数据
- 中间缓存
- 临时导出记录
- AI 原始调试日志（若存在）

---

## 十一、删除与归档策略

### 11.1 Topic 删除策略
建议分两级：
- 软删除：标记 archived
- 硬删除：级联清理 SQLite 相关状态，并按 topic_id 清理 Neo4j/LanceDB 记录

### 11.2 节点删除策略
MVP 阶段不建议开放自由删除节点，而应开放：
- 标记无效
- 合并节点
- 隐藏节点

因为图谱删除容易破坏已有学习历史。

---

## 十二、数据一致性策略

## 12.1 事务边界建议

跨 Neo4j / LanceDB / SQLite 无法天然强事务，因此应采用“主流程 + 补偿”机制：
- 先写 SQLite Topic 元数据
- 再写 Neo4j 图谱
- 再写 LanceDB 向量
- 失败时记录补偿任务或回滚标记

## 12.2 一致性优先级
- Topic 与 Session 元数据必须稳定
- 图谱写入失败时不能导致应用崩溃
- 向量层失败时允许降级，但需标记未建索引状态

---

## 十三、索引与性能建议

## 13.1 SQLite 索引重点
- topics(status, updated_at)
- sessions(topic_id, start_time)
- ability_records(topic_id, node_id)
- friction_records(topic_id, node_id)
- review_items(status, due_time, priority)
- expression_assets(topic_id, node_id, expression_type)

## 13.2 Neo4j 查询优化重点
- 当前 Topic 下的主干链查询
- 某节点前置链查询
- 某节点高混淆邻居查询
- Topic 内高重要性节点查询

## 13.3 LanceDB 查询优化重点
- 新节点写入前相似查重
- 输入文本创建 Topic 前相似主题检索
- 练习完成后相关节点推荐

---

## 十四、版本演进建议

## 14.1 MVP 阶段
优先落地：
- Topic / Node / Edge
- sessions
- ability_records
- practice_attempts
- expression_assets
- review_items
- deferred_nodes

## 14.2 V1 阶段
增强：
- ability_snapshots
- friction_records
- misconception records
- evidence refs
- 更细的 review 结构

## 14.3 V2 阶段
扩展：
- 全局 canonical concept 层
- 多模态证据对象
- 团队 / workspace 支持
- 更复杂的用户画像与风格资产

---

## 十五、数据库实施建议

### 15.1 先建统一 schema，再写接口
不要先写 API 再倒推表结构，否则后面会反复返工。

### 15.2 先跑通单 Topic 主流程
先验证：
创建 Topic → 写入图谱 → 做一轮练习 → 更新能力 → 生成复习

### 15.3 图谱写入必须做幂等
重复创建同一个 Topic 或重复生成相似节点时，不能无限复制脏数据。

### 15.4 预留 migration 机制
SQLite 和 Neo4j schema 都要有版本管理策略，避免后续升级困难。

---

## 十六、最终结论

AxonClone 的数据库设计不应追求“一个库解决所有问题”，而应围绕产品的真实数据结构建立混合存储体系：

- **Neo4j** 负责知识图谱与关系网络
- **LanceDB** 负责语义查重与向量检索
- **SQLite** 负责用户学习状态、表达资产、复习任务与设置持久化

这套设计既能支撑 MVP 快速落地，也能为后续能力图谱、误解图谱、多模态证据和长期成长系统提供稳定的数据底座。

