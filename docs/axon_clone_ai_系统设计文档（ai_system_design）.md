# AxonClone AI 系统设计文档（AI System Design）

## 一、文档目的

本文档用于定义 AxonClone 中 AI 能力的系统设计方式，包括 AI 在产品中的角色分工、任务链路、提示词结构、结构化输出设计、模型调用策略、上下文管理、质量约束、失败降级和演进路线，作为 AI 产品设计、后端编排、提示词工程和测试评估的统一依据。

AxonClone 的 AI 不只是“一个大模型回答问题”，而是一套围绕学习闭环设计的能力系统。AI 需要同时承担：
- 内容解析
- 知识节点生成
- 路径规划
- 卡点诊断
- 学习陪练
- 表达优化
- 收束总结
- 复习生成

因此，AI 层必须从一开始就按角色与任务拆分，而不是依赖一个大 prompt 承担所有职责。

---

## 二、AI 系统设计目标

### 2.1 产品目标映射
AI 系统必须直接服务以下三类产品价值：

1. 把输入内容转化为知识网络
2. 把理解转化为表达能力
3. 把学习过程转化为可追踪成长数据

### 2.2 技术目标映射
AI 系统必须满足：
- 结构化输出稳定
- 多任务职责边界清晰
- 上下文成本可控
- 失败可降级
- 后续支持多模态扩展

### 2.3 体验目标映射
用户应感知到系统：
- 不只是解释很多
- 而是知道该教什么
- 知道为什么推荐这些节点
- 知道用户卡在哪
- 知道什么时候该继续讲，什么时候该让用户练

---

## 三、AI 系统总体架构

建议将 AI 系统拆为四类角色：

1. Explorer：知识探索者
2. Diagnoser：学习诊断者
3. Tutor：学习陪练者
4. Synthesizer：收束总结者

在 MVP 阶段，这四类角色可以共享同一模型提供方，但必须使用不同 prompt、不同 schema 和不同业务入口。

---

## 四、AI 角色定义

## 4.1 Explorer（知识探索者）

### 作用
负责把输入内容或当前节点转化为结构化知识对象。

### 核心任务
- 从长文中抽取关键概念
- 判断主干与支线
- 为节点生成 summary / why_it_matters / applications
- 生成关系边
- 推荐起始节点与下一步节点

### 典型输入
- 用户输入的文章
- 当前 Topic 上下文
- 当前节点
- 学习意图
- 已有图谱摘要

### 典型输出
- Topic outline
- Node bundle
- Edge list
- Entry node recommendation
- Suggested next nodes

### 适用接口
- 创建 Topic
- 扩展节点
- 生成主干路径
- 推荐下一节点

---

## 4.2 Diagnoser（学习诊断者）

### 作用
负责分析用户作答、识别卡点、能力短板和误解模式。

### 核心任务
- 判断用户是定义不会、例子不会还是表达不清
- 标记 friction tags
- 判断是否需要补前置
- 生成诊断性建议
- 推动能力分数更新

### 典型输入
- 当前节点内容
- 当前练习题
- 用户回答
- 历史能力记录
- 历史卡点记录

### 典型输出
- friction tags
- ability deltas
- misconception hints
- suggested prerequisites
- recommended next action

---

## 4.3 Tutor（学习陪练者）

### 作用
负责围绕当前节点与用户目标进行 Socratic 式教学和表达训练。

### 核心任务
- 用适当深度解释概念
- 生成练习题
- 引导用户复述、举例、对比、应用
- 对用户表达进行反馈
- 生成更优表达版本与骨架

### 典型输入
- 当前节点结构化内容
- 用户学习意图
- 用户能力状态
- 当前练习类型
- 用户最近回答

### 典型输出
- 学习问题
- 表达练习题
- AI 反馈
- 推荐表达
- expression skeleton

---

## 4.4 Synthesizer（收束总结者）

### 作用
负责将一轮学习过程压缩为高价值收束内容。

### 核心任务
- 输出本轮主线总结
- 提炼新增关键节点
- 标记值得以后学的节点
- 生成复习候选
- 提炼用户新增表达资产

### 典型输入
- Session 访问路径
- 本轮练习结果
- 新增节点
- 用户能力变化

### 典型输出
- session summary
- key takeaways
- deferred suggestions
- review candidates
- asset highlights

---

## 五、AI 调用链设计

## 5.1 创建 Topic 时的调用链

### 目标
把用户输入转成可学习的 Topic 和起始路径。

### 调用顺序建议
1. Explorer：解析输入，生成 Topic outline
2. Explorer：生成 entry node + initial node bundle
3. 后端校验与写库
4. 如生成失败，进入简化模式返回最小学习卡

### 关键要求
- 不要在一次调用中展开整个大图
- 先生成主线、起始节点和有限初始节点

---

## 5.2 学习页扩展节点时的调用链

### 目标
围绕当前节点按当前意图做可控扩展。

### 调用顺序建议
1. 后端准备上下文摘要
2. Explorer 生成 3-5 个新关联节点
3. 后端做去重与关系约束校验
4. 返回推荐节点与 delta summary

### 关键要求
- 控制节点数量
- 保证关系类型合法
- 避免与已有节点重复

---

## 5.3 练习作答时的调用链

### 目标
生成题目并对用户表达做反馈。

### 调用顺序建议
1. Tutor：生成当前节点的练习题
2. 用户作答
3. Diagnoser：分析作答，输出能力变化和卡点标签
4. Tutor：生成更优表达版本与骨架
5. 后端更新 Ability / Friction / Expression Asset

---

## 5.4 收束总结时的调用链

### 目标
帮助用户结束一轮学习并明确下一步。

### 调用顺序建议
1. 后端汇总 session context
2. Synthesizer 生成本轮总结
3. Diagnoser 生成复习候选优先级
4. 后端写入 summary 与 review items

---

## 六、上下文设计原则

## 6.1 不把全部历史无脑塞进模型
AxonClone 不是聊天产品，不应简单依赖长对话上下文。建议始终使用“结构化上下文摘要”。

### 上下文来源建议
- 当前 Topic 摘要
- 当前节点结构化卡片
- 主干链摘要
- 最近 1-2 次练习结果
- 当前学习意图
- 当前能力弱项摘要

### 不建议直接全量传入的内容
- 所有历史对话原文
- 整个图谱所有节点详情
- 所有表达资产全文

---

## 6.2 上下文摘要结构建议

建议维护统一 Context Builder，按不同角色输出不同上下文结构。

### Explorer 上下文
- topic title
- learning intent
- current node
- mainline summary
- existing nodes digest
- max depth

### Diagnoser 上下文
- node summary
- practice prompt
- user answer
- recent ability record
- recent friction history

### Tutor 上下文
- node summary
- misconceptions
- examples
- user level hint
- current practice type

### Synthesizer 上下文
- visited nodes
- practice attempts summary
- ability changes
- deferred nodes
- suggested next nodes

---

## 七、结构化输出设计

## 7.1 结构化输出原则
- 每类任务一个独立 schema
- schema 越小越稳
- 字段命名与数据库对象一致
- 尽量让 AI 输出“对象”，而不是自由描述段落

---

## 7.2 Explorer 输出 schema 建议

### `NodeBundle`
字段建议：
- `current_node`
- `summary`
- `why_it_matters`
- `applications`
- `importance`
- `related`

### `RelatedNode`
字段建议：
- `name`
- `relation_type`
- `reason`
- `suggested_importance`

---

## 7.3 Diagnoser 输出 schema 建议

### `DiagnosticResult`
字段建议：
- `friction_tags`
- `severity`
- `ability_delta`
- `misconception_hints`
- `suggested_prerequisite_nodes`
- `recommended_practice_type`
- `short_feedback`

---

## 7.4 Tutor 输出 schema 建议

### `PracticePrompt`
字段建议：
- `practice_type`
- `prompt_text`
- `minimum_answer_hint`
- `evaluation_dimensions`

### `PracticeFeedback`
字段建议：
- `correctness`
- `clarity`
- `naturalness`
- `issues`
- `suggestions`
- `recommended_answer`
- `expression_skeleton`

---

## 7.5 Synthesizer 输出 schema 建议

### `SessionSummary`
字段建议：
- `mainline_summary`
- `key_takeaways`
- `new_key_nodes`
- `deferred_nodes`
- `next_recommendations`
- `review_candidates`
- `asset_highlights`

---

## 八、提示词设计原则

## 8.1 提示词不追求万能，追求单一职责
一个 prompt 不应同时做多个本质不同的任务，否则稳定性会迅速下降。

## 8.2 提示词必须显式绑定产品目标
例如 Tutor 不只是“解释知识”，而是“解释后必须推动用户输出”。

## 8.3 提示词必须显式限制扩展边界
Explorer 应明确：
- 只生成 3-5 个节点
- 优先主干
- 避免无限展开
- 不要引入与当前意图弱相关节点

## 8.4 提示词必须显式告诉模型“用户当前为什么来”
学习意图是路径合理性的关键。

---

## 九、各角色 Prompt 设计要点

## 9.1 Explorer Prompt 要点

必须明确：
- 当前输入类型（概念 / 问题 / 文章）
- 当前学习意图
- 当前 Topic 已有结构摘要
- 生成目标是学习路径，不是百科大全
- 关系类型白名单
- 节点数量限制

### Explorer 关键约束句建议
- 只输出与当前学习目标最相关的 3-5 个节点
- 优先返回主干知识，不要过度发散
- 若当前节点已有高相似概念，不生成同义重复节点
- 不输出无意义抽象概念

---

## 9.2 Diagnoser Prompt 要点

必须明确：
- 用户回答的目标是什么
- 当前节点核心知识点是什么
- 诊断重点是“用户卡在哪”，不是重新讲一遍正确答案
- 输出 friction tags 与 ability delta

### Diagnoser 关键约束句建议
- 判断用户问题更接近“不会”还是“不会表达”
- 优先识别前置缺失、概念混淆、缺例子、结构差等标签
- 输出简短、可行动的反馈，而不是长文批改

---

## 9.3 Tutor Prompt 要点

必须明确：
- 当前不是直接给答案，而是推动用户练
- 每次只做一个微任务
- 给用户留思考和表达空间
- 可根据能力状态调整难度

### Tutor 关键约束句建议
- 每次只问一个问题
- 先让用户用自己的话说，再提供优化版本
- 反馈中优先指出一个最关键改进点
- 语言要友好、简洁、口语化

---

## 9.4 Synthesizer Prompt 要点

必须明确：
- 不是重复整轮内容，而是帮助收束
- 总结要能告诉用户“这一轮学到了什么”和“接下来最值得做什么”
- 输出结构要简洁、清晰、可立即显示

### Synthesizer 关键约束句建议
- 不要罗列所有节点
- 优先总结主线和最值得记住的 3 个点
- 明确哪些节点可以稍后再学
- 给出 1-2 个高价值下一步建议

---

## 十、学习意图对 AI 的影响

学习意图必须进入每个 AI 角色的输入中。

## 10.1 不同意图下的行为差异

### 补基础（fix_gap）
- Explorer 优先 prerequisite
- Tutor 优先直觉解释与例子
- Diagnoser 优先看前置缺失

### 建立体系（build_system）
- Explorer 优先主干结构
- Synthesizer 强化主线总结
- 图谱推荐更完整

### 解决当前问题（solve_task）
- Explorer 优先最短路径
- Tutor 优先应用表达
- Synthesizer 强调“你现在已经能解决什么”

### 准备表达（prepare_expression）
- Tutor 提高表达练习密度
- Diagnoser 更关注结构、自然度与受众适配
- Expression asset 保存优先级更高

---

## 十一、能力图谱与 AI 的关系

AI 不只输出内容，还需要驱动能力图谱更新。

## 11.1 AI 输出能力变化的原则
- 不直接给大而假的总分
- 更适合输出分维度增量
- 分数变化必须有依据

### 示例
- 用户定义表达不错 → `understand +10, explain +8`
- 用户不会举例 → `example +0`
- 用户区分不清 → `contrast - 或保持低分`

## 11.2 AI 不应直接成为唯一评分权威
建议后端保留一定规则层：
- 同类练习重复成功后再累计增长
- 一次偶然失败不应大幅清零能力
- 复习失败应优先影响 recall / explain，而不是所有分数

---

## 十二、AI 驱动的复习生成逻辑

## 12.1 复习候选来源
- 高重要性节点
- 高混淆节点
- 用户 explain 分低的节点
- 最近复习失败节点
- 新学但尚未固化节点

## 12.2 AI 在复习中的职责
- 生成主动回忆题
- 判断回答是否真正掌握
- 决定是“继续复习”还是“回到学习页补基础”

### 复习题类型建议
- 一句话定义
- 举例
- 与相邻概念对比
- 放入具体问题解释
- 压缩复述

---

## 十三、失败降级设计

AI 系统必须具备失败可降级能力。

## 13.1 Explorer 失败时
### 降级策略
- 至少返回一个起始节点
- 只返回最小学习卡：名称 + summary + why_now
- 暂时不写入完整图谱

## 13.2 Diagnoser 失败时
### 降级策略
- 不更新 friction tags
- 仅返回通用反馈 + 不更新能力增量
- 前端提示“已使用简化反馈模式”

## 13.3 Tutor 失败时
### 降级策略
- 返回静态练习模板
- 前端允许用户继续记录表达

## 13.4 Synthesizer 失败时
### 降级策略
- 根据 session 记录做规则型总结
- 至少输出：访问节点数、练习次数、下一步建议

---

## 十四、质量控制与评估机制

## 14.1 AI 质量评估维度

### Explorer
- 节点相关性
- 主干合理性
- 关系合法性
- 重复率

### Diagnoser
- 卡点识别准确感
- 反馈可行动性
- 能力变化合理性

### Tutor
- 问题质量
- 反馈具体性
- 表达优化实用性
- 用户感知帮助度

### Synthesizer
- 收束感
- 主线清晰度
- 下一步建议有效性

---

## 14.2 评估样本建议
建立固定测试集：
- 文章输入样本
- 单概念输入样本
- 用户弱回答样本
- 用户较好回答样本
- 复习失败样本

用来回归测试各角色稳定性。

---

## 十五、模型与成本策略

## 15.1 模型使用建议
高价值场景优先用更强模型：
- Diagnoser
- Tutor 反馈
- Synthesizer

相对可简化场景可尝试轻量：
- Explorer 初始 outline
- 部分规则型总结
- 批量复习题生成

## 15.2 成本控制原则
- 避免把全历史传入
- 避免无上限扩图
- 能规则生成的字段不强依赖模型
- 可缓存的节点解释与题目尽量缓存

---

## 十六、MVP AI 落地范围

MVP 阶段建议先实现：
- Explorer：创建 Topic + 扩展节点
- Tutor：生成练习题 + 表达反馈
- Diagnoser：基础 friction tags + ability delta
- Synthesizer：session summary

MVP 阶段可不必实现：
- 复杂误解图谱推理
- 多模态证据理解
- 高级多 agent 自动协商
- 风格级个性化表达生成

---

## 十七、V1/V2 演进方向

## 17.1 V1
- 引入更细的卡点分类
- 误解图谱对象化
- 表达资产风格标签化
- 题型自适应

## 17.2 V2
- 多模态输入解析
- 证据片段绑定
- 更复杂的任务桥接
- 用户表达画像与风格迁移
- 局部 agent 自动规划

---

## 十八、最终结论

AxonClone 的 AI 系统必须从一开始就被设计成“学习操作系统中的能力层”，而不是“一个会回答问题的大模型”。

最合理的设计路径是：
- 用 **Explorer** 组织知识
- 用 **Diagnoser** 识别卡点
- 用 **Tutor** 训练表达
- 用 **Synthesizer** 帮助收束

并通过结构化输出、上下文摘要、分角色 prompt、能力更新与失败降级机制，把 AI 真正嵌入产品主流程中。

只有这样，AxonClone 才会从“生成很多内容”升级为“真正带着用户学、练、记、讲”的学习系统。

