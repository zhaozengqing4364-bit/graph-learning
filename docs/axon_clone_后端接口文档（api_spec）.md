# AxonClone 后端接口文档（API Spec）

## 一、文档目的

本文档用于定义 AxonClone 本地后端服务的接口结构、资源模型、请求响应格式、状态码规范、核心业务 API、错误处理策略与版本演进原则，作为前后端联调、服务开发、测试验收和后续扩展的统一依据。

本文档假设当前后端采用 FastAPI 作为本地服务，桌面客户端通过 HTTP 调用本地 API。接口设计以单机单用户为前提，但对象结构应预留未来多用户/多工作区扩展能力。

---

## 二、接口设计原则

### 2.1 以业务动作驱动，而不是纯 CRUD 驱动
AxonClone 不是后台管理系统，不应只围绕“增删改查”设计接口，而应围绕学习动作设计：
- 创建主题
- 生成节点 bundle
- 开始学习会话
- 提交练习
- 更新能力
- 生成总结
- 生成复习队列

### 2.2 结构化返回优先
所有核心接口都应返回明确结构对象，而不是未约束的自由文本。

### 2.3 支持渐进增强
MVP 阶段先保证主链路接口稳定；V1 再增强误解图谱、表达资产检索、复习调度等高级接口。

### 2.4 接口与对象统一命名
后端返回字段命名要与数据库和前端类型保持一致，避免 Topic / Node / Edge / Session / Ability 等对象多套命名。

### 2.5 错误信息可诊断
接口出错时，要能帮助前端决定是展示兜底内容、提示重试，还是回退到简化模式。

---

## 三、接口分层

建议将接口按资源域拆成八类：

1. 系统接口
2. Topic 接口
3. Node 接口
4. Graph 接口
5. Session 接口
6. Practice 接口
7. Review 接口
8. Settings 接口

---

## 四、基础规范

## 4.1 Base URL

本地桌面端默认：
`http://127.0.0.1:8000/api/v1`

## 4.2 通用响应格式

### 成功响应
```json
{
  "success": true,
  "data": {},
  "meta": {},
  "error": null
}
```

### 失败响应
```json
{
  "success": false,
  "data": null,
  "meta": {},
  "error": {
    "code": "NODE_GENERATION_FAILED",
    "message": "Failed to generate node bundle",
    "details": {}
  }
}
```

## 4.3 通用 meta 字段建议
- `request_id`
- `timestamp`
- `version`
- `fallback_used`
- `partial`

## 4.4 状态码建议
- `200`：请求成功
- `201`：资源创建成功
- `400`：请求参数错误
- `404`：资源不存在
- `409`：冲突（重复 Topic / 重复节点 / 状态冲突）
- `422`：结构校验失败
- `500`：系统错误
- `503`：模型服务不可用或本地依赖未就绪

---

## 五、系统接口

## 5.1 健康检查

### `GET /health`

#### 作用
检查本地服务、数据库和模型依赖是否正常。

#### 返回示例
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "services": {
      "api": true,
      "sqlite": true,
      "neo4j": true,
      "lancedb": true,
      "model_provider": true,
      "ollama": false
    }
  },
  "meta": {},
  "error": null
}
```

---

## 5.2 获取系统能力

### `GET /system/capabilities`

#### 作用
返回当前启用的能力，用于前端判断入口和降级展示。

#### 返回字段建议
- `supports_multimodal`
- `supports_local_fallback`
- `supports_export`
- `supports_review`
- `supports_expression_assets`

---

## 六、Topic 接口

## 6.1 创建学习主题

### `POST /topics`

#### 作用
根据概念、问题、文章或长文本创建 Topic，并触发初始解析。

#### 请求体
```json
{
  "title": "Tokenizer 学习主题",
  "source_type": "article",
  "source_content": "...长文本内容...",
  "learning_intent": "build_system",
  "mode": "full_system"
}
```

#### 字段说明
- `source_type`：`concept | question | article | notes | mixed`
- `learning_intent`：`build_system | fix_gap | solve_task | prepare_expression | prepare_interview`
- `mode`：`shortest_path | full_system`

#### 响应体
```json
{
  "success": true,
  "data": {
    "topic": {
      "topic_id": "tp_001",
      "title": "Tokenizer 学习主题",
      "learning_intent": "build_system",
      "mode": "full_system",
      "status": "active"
    },
    "entry_node": {
      "node_id": "nd_101",
      "name": "Tokenizer",
      "summary": "Tokenizer 是把文本转成模型可处理单元的过程。"
    },
    "outline": {
      "mainline": ["Tokenizer", "Token", "BPE"],
      "suggested_nodes": 5
    }
  },
  "meta": {
    "fallback_used": false,
    "partial": false
  },
  "error": null
}
```

---

## 6.2 获取 Topic 列表

### `GET /topics`

#### 查询参数建议
- `status`
- `limit`
- `offset`
- `q`

#### 返回内容
- 最近学习主题
- 主题状态
- 当前节点
- 最近更新时间

---

## 6.3 获取 Topic 详情

### `GET /topics/{topic_id}`

#### 作用
返回 Topic 基础信息与当前学习进度概览。

#### 返回字段建议
- topic 基础信息
- current_node_id
- last_session_id
- total_nodes
- mastered_nodes
- due_review_count
- deferred_count

---

## 6.4 更新 Topic

### `PATCH /topics/{topic_id}`

#### 作用
更新 Topic 的标题、学习意图、模式、状态等。

#### 可更新字段
- `title`
- `learning_intent`
- `mode`
- `status`

---

## 6.5 删除 / 归档 Topic

### `POST /topics/{topic_id}/archive`
### `DELETE /topics/{topic_id}`

#### 建议
MVP 阶段前端优先调用 archive，而不是直接硬删除。

---

## 七、Node 接口

## 7.1 获取当前 Topic 推荐起始节点

### `GET /topics/{topic_id}/entry-node`

#### 作用
在恢复 Topic 时返回推荐继续学习的节点。

---

## 7.2 获取节点详情

### `GET /topics/{topic_id}/nodes/{node_id}`

#### 作用
返回当前节点学习页所需的全部核心数据。

#### 返回字段建议
```json
{
  "success": true,
  "data": {
    "node": {
      "node_id": "nd_101",
      "name": "Tokenizer",
      "summary": "...",
      "why_it_matters": "...",
      "importance": 5,
      "status": "learning"
    },
    "examples": ["..."],
    "misconceptions": ["..."],
    "prerequisites": [{"node_id": "nd_102", "name": "Token"}],
    "contrasts": [{"node_id": "nd_103", "name": "Embedding"}],
    "applications": [{"node_id": "nd_104", "name": "Prompt token 计算"}],
    "related": [{"node_id": "nd_105", "name": "BPE"}],
    "ability": {
      "understand_score": 40,
      "example_score": 20,
      "contrast_score": 15,
      "apply_score": 10,
      "explain_score": 10,
      "recall_score": 0,
      "transfer_score": 0
    },
    "why_now": "这是当前主题的核心主干节点，也是后续 BPE 的前置。"
  },
  "meta": {},
  "error": null
}
```

---

## 7.3 扩展节点 bundle

### `POST /topics/{topic_id}/nodes/{node_id}/expand`

#### 作用
围绕当前节点生成下一批知识节点与关系。

#### 请求体
```json
{
  "depth_limit": 2,
  "intent": "build_system",
  "strategy": "balanced"
}
```

#### strategy 可选值
- `mainline_first`
- `balanced`
- `deep_dive`

#### 返回字段建议
- `new_nodes`
- `new_edges`
- `suggested_next_nodes`
- `summary_delta`

---

## 7.4 节点加入待学堆栈

### `POST /topics/{topic_id}/nodes/{node_id}/defer`

#### 请求体
```json
{
  "source_node_id": "nd_101",
  "reason": "当前先不展开，后续统一学习 tokenizer 分支"
}
```

---

## 7.5 节点标记状态

### `PATCH /topics/{topic_id}/nodes/{node_id}/status`

#### 可更新状态
- `unseen`
- `browsed`
- `learning`
- `practiced`
- `review_due`
- `mastered`

---

## 八、Graph 接口

## 8.1 获取 Topic 图谱

### `GET /topics/{topic_id}/graph`

#### 查询参数建议
- `view=mainline|full|prerequisite|misconception`
- `max_depth`
- `focus_node_id`
- `collapsed=true|false`

#### 返回结构建议
```json
{
  "success": true,
  "data": {
    "nodes": [...],
    "edges": [...],
    "meta": {
      "view": "mainline",
      "collapsed": true,
      "current_node_id": "nd_101"
    }
  },
  "meta": {},
  "error": null
}
```

---

## 8.2 获取主干路径

### `GET /topics/{topic_id}/graph/mainline`

#### 作用
用于学习页和收束页展示当前主干结构。

---

## 8.3 获取节点邻域

### `GET /topics/{topic_id}/graph/neighborhood/{node_id}`

#### 查询参数建议
- `radius`
- `relation_types`

#### 作用
用于图谱页侧边详情和学习页局部推荐。

---

## 九、Session 接口

## 9.1 开始学习会话

### `POST /topics/{topic_id}/sessions`

#### 请求体
```json
{
  "entry_node_id": "nd_101"
}
```

#### 返回内容
- `session_id`
- `entry_node`
- `restored` 是否为恢复会话

---

## 9.2 获取会话详情

### `GET /topics/{topic_id}/sessions/{session_id}`

#### 返回字段建议
- entry node
- visited nodes
- practice count
- current summary
- current status

---

## 9.3 记录节点访问

### `POST /topics/{topic_id}/sessions/{session_id}/visit`

#### 请求体
```json
{
  "node_id": "nd_101",
  "action_type": "open_node"
}
```

#### 作用
用于重建用户学习路径。

---

## 9.4 结束会话并生成总结

### `POST /topics/{topic_id}/sessions/{session_id}/complete`

#### 请求体
```json
{
  "generate_summary": true,
  "generate_review_items": true
}
```

#### 返回字段建议
- `session_summary`
- `next_recommendations`
- `review_candidates`
- `new_assets_count`

---

## 十、Practice 接口

## 10.1 获取练习任务

### `POST /topics/{topic_id}/nodes/{node_id}/practice`

#### 作用
根据节点与当前能力状态生成练习任务。

#### 请求体
```json
{
  "practice_type": "explain",
  "difficulty": "adaptive"
}
```

#### practice_type 建议
- `define`
- `example`
- `contrast`
- `apply`
- `teach_beginner`
- `compress`

#### 返回内容
- 题目
- 作答要求
- 评分维度
- 最小作答提示

---

## 10.2 提交练习答案

### `POST /topics/{topic_id}/nodes/{node_id}/practice/submit`

#### 请求体
```json
{
  "session_id": "ss_001",
  "practice_type": "explain",
  "prompt_text": "请用一句话解释 Tokenizer",
  "user_answer": "Tokenizer 就是把文本切成模型能处理的 token。"
}
```

#### 返回内容建议
```json
{
  "success": true,
  "data": {
    "attempt_id": "pa_001",
    "feedback": {
      "correctness": "good",
      "clarity": "good",
      "naturalness": "medium",
      "issues": ["表达还可以更具体"],
      "suggestions": ["补一句为什么要做这一步"]
    },
    "recommended_answer": "Tokenizer 是把原始文本切分成模型可处理 token 的过程，它决定了文本如何进入模型。",
    "expression_skeleton": "X 是把 A 转成 B 的过程，它决定了 C。",
    "ability_update": {
      "understand_score": 60,
      "explain_score": 45
    },
    "friction_tags": ["weak_structure"]
  },
  "meta": {},
  "error": null
}
```

---

## 10.3 保存表达资产

### `POST /topics/{topic_id}/nodes/{node_id}/expression-assets`

#### 请求体
```json
{
  "attempt_id": "pa_001",
  "expression_type": "define",
  "user_expression": "...",
  "ai_rewrite": "...",
  "skeleton": "...",
  "quality_tags": ["clear", "reusable"]
}
```

---

## 10.4 获取表达资产列表

### `GET /topics/{topic_id}/expression-assets`

#### 查询参数
- `node_id`
- `expression_type`
- `favorited`
- `limit`

---

## 十一、Ability / Diagnostics 接口

## 11.1 获取节点能力记录

### `GET /topics/{topic_id}/nodes/{node_id}/ability`

#### 返回
当前最新能力分数与最近一次变化。

---

## 11.2 获取 Topic 能力概览

### `GET /topics/{topic_id}/abilities/overview`

#### 返回字段建议
- ability averages
- weak nodes
- strongest nodes
- explain gap nodes

---

## 11.3 获取卡点记录

### `GET /topics/{topic_id}/frictions`

#### 查询参数
- `node_id`
- `friction_type`
- `limit`

---

## 11.4 生成节点诊断建议

### `POST /topics/{topic_id}/nodes/{node_id}/diagnose`

#### 作用
在用户反馈“学不会”“讲不清”时，单独生成诊断报告。

#### 返回字段建议
- `friction_tags`
- `reasoning_summary`
- `suggested_prerequisites`
- `recommended_practice_types`

---

## 十二、Review 接口

## 12.1 获取待复习列表

### `GET /reviews`

#### 查询参数建议
- `status`
- `limit`
- `topic_id`
- `due_before`

#### 返回字段建议
- 节点名称
- 复习类型
- 优先级
- 到期时间
- 推荐原因

---

## 12.2 获取复习任务详情

### `GET /reviews/{review_id}`

#### 返回
- 节点信息
- 复习题目
- 复习类型
- 历史结果

---

## 12.3 提交复习答案

### `POST /reviews/{review_id}/submit`

#### 请求体
```json
{
  "user_answer": "...",
  "session_id": "ss_002"
}
```

#### 返回字段建议
- `result`
- `feedback`
- `ability_update`
- `next_due_time`
- `needs_relearn`

---

## 12.4 生成 Topic 复习队列

### `POST /topics/{topic_id}/reviews/generate`

#### 作用
手动触发某个 Topic 的复习队列生成。

---

## 十三、Settings 接口

## 13.1 获取设置

### `GET /settings`

#### 返回字段建议
- `default_model`
- `default_learning_intent`
- `default_mode`
- `max_graph_depth`
- `auto_start_practice`
- `auto_generate_summary`
- `ollama_enabled`

---

## 13.2 更新设置

### `PATCH /settings`

#### 请求体示例
```json
{
  "default_model": "gpt-5.4-thinking",
  "max_graph_depth": 3,
  "auto_start_practice": true
}
```

---

## 十四、Export 接口（预留）

## 14.1 导出 Topic

### `POST /topics/{topic_id}/export`

#### 请求体建议
```json
{
  "export_type": "markdown"
}
```

#### export_type 预留
- `markdown`
- `json`
- `anki`

---

## 十五、错误码规范

建议维护统一错误码字典。

### 通用错误码示例
- `INVALID_REQUEST`
- `RESOURCE_NOT_FOUND`
- `MODEL_PROVIDER_UNAVAILABLE`
- `NODE_GENERATION_FAILED`
- `GRAPH_WRITE_FAILED`
- `VECTOR_INDEX_FAILED`
- `PRACTICE_EVALUATION_FAILED`
- `REVIEW_GENERATION_FAILED`
- `SETTINGS_UPDATE_FAILED`

### 前端建议处理方式
- 可重试错误：提示重试
- 可降级错误：展示简化版本
- 数据错误：提示刷新或返回首页
- 模型错误：允许切换本地 fallback

---

## 十六、接口版本管理

### 当前版本
`/api/v1`

### 建议原则
- 破坏性变更进入 `v2`
- 字段追加优先兼容旧前端
- 返回结构尽量稳定，避免频繁改 key

---

## 十七、接口联调优先级建议

## P0 必联调接口
- `POST /topics`
- `GET /topics/{topic_id}`
- `GET /topics/{topic_id}/nodes/{node_id}`
- `POST /topics/{topic_id}/sessions`
- `POST /topics/{topic_id}/nodes/{node_id}/practice`
- `POST /topics/{topic_id}/nodes/{node_id}/practice/submit`
- `POST /topics/{topic_id}/sessions/{session_id}/complete`
- `GET /topics/{topic_id}/graph`
- `GET /settings`
- `PATCH /settings`

## P1 接口
- `POST /topics/{topic_id}/nodes/{node_id}/expand`
- `POST /topics/{topic_id}/nodes/{node_id}/defer`
- `GET /reviews`
- `POST /reviews/{review_id}/submit`
- `GET /topics/{topic_id}/expression-assets`
- `GET /topics/{topic_id}/frictions`

---

## 十八、接口安全与边界

单机本地服务无需复杂鉴权，但仍建议：
- 仅监听 `127.0.0.1`
- 禁止无关跨域来源
- 对导入内容和导出路径做基础校验
- 对删除类接口做二次确认

---

## 十九、最终结论

AxonClone 的后端接口不应被设计成普通管理后台式 API，而应围绕学习动作构建：

- 创建 Topic
- 获取节点学习上下文
- 生成图谱与扩展节点
- 启动和完成会话
- 发起与提交练习
- 更新能力与卡点
- 生成复习任务与总结
- 管理设置与资产

只要接口保持“业务动作清晰、对象结构统一、错误可诊断、字段可扩展”这四个原则，前后端联调和后续架构演进都会顺很多。

