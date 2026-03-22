# Findings

## Requirements
- 用户要求对当前仓库做“全量检测 / 全量审计”。
- 需要开启 Agent Team，使用并行子代理覆盖不同维度。
- 输出不只包含 bug，还要包含缺少的功能、未完善的内容、架构或测试空缺。

## Research Findings
- 仓库是一个桌面学习系统原型：Tauri v2 + React + TypeScript + Vite + FastAPI。
- 项目级 `CLAUDE.md` 明确定义了目标产品不是聊天工具，而是围绕知识展开、表达训练、成长诊断和复习闭环的学习操作系统。
- 根目录现有 `task_plan.md` / `findings.md` / `progress.md` 是 2026-03-16 的 article-first workspace 实施记录，不等于本轮全量审计结果。
- 仓库内已有一次前端审计产物：`docs/audits/2026-03-16-frontend-surface-map.md` 和 `docs/audits/2026-03-16-full-frontend-audit.md`，可以作为基线，但不能直接替代本轮结论。
- 前端静态质量当前是绿的：`eslint` 通过，Vitest 10 个文件 51 个测试通过，后端 Pytest 101 个测试通过，前端生产构建成功。
- 会话能力在前后端“定义存在、接线不足”：前端定义了 `useStartSessionMutation` / `useVisitNodeMutation` / `useCompleteSessionMutation`，但当前主流程代码没有实际消费这些 hooks，练习页只是在 `sessionId` 查询参数存在时才给出总结入口。
- `settings` 中的 `auto_start_practice` / `auto_generate_summary` 目前只体现在表单里，未看到主流程消费逻辑。
- 后端复习和多存储可靠性存在结构性缺口：review 间隔调度没有真正闭环，SQLite/Neo4j/LanceDB 写入没有补偿或回滚标记，部分 graph/node 接口返回数据形状正确但语义不完全符合文档契约。
- `entry-node` 接口仍有响应形状不一致风险：当 topic 已有 `current_node_id` 时，后端直接返回完整 node detail，而文章导读拼装仍按扁平 `EntryNode` 消费。
- Tauri 壳层已经提供 sidecar IPC 封装，但前端没有实际调用这些桥接方法，桌面模式后端生命周期仍偏手工。
- 本地健康检查显示 Neo4j 当前不可连接，因此图谱增强、关系查询和部分推荐能力在当前环境只能依赖降级路径。
- 仓库扫描未发现 `.github/workflows`、Playwright/Cypress 配置或其它 E2E 自动化入口；现有自动化主要停留在单元、纯函数和 API 层。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 审计分为产品能力、前端面覆盖、后端实现、测试运维四条线 | 便于并行且覆盖用户要求的“全都告诉我” |
| 浏览器审计基于代码面映射后进行 | 避免遗漏路由和关键交互 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| 项目没有更深层 AGENTS.md | 以用户提供的全局约束和仓库级 `CLAUDE.md` 作为审计基线 |
| `spawn_agent` 可用线程数达到上限 | 保留已启动子代理，剩余审计由主线程补齐 |

## Resources
- `/Users/zhaozengqing/Downloads/图学习/CLAUDE.md`
- `/Users/zhaozengqing/Downloads/图学习/docs/audits/2026-03-16-frontend-surface-map.md`
- `/Users/zhaozengqing/Downloads/图学习/docs/audits/2026-03-16-full-frontend-audit.md`
- `/Users/zhaozengqing/Downloads/图学习/src/hooks/use-mutations.ts`
- `/Users/zhaozengqing/Downloads/图学习/src/routes/practice-page.tsx`
- `/Users/zhaozengqing/Downloads/图学习/src/routes/settings-page.tsx`
- `/Users/zhaozengqing/Downloads/图学习/src/lib/article-workspace.ts`
- `/Users/zhaozengqing/Downloads/图学习/src/lib/tauri.ts`
- `/Users/zhaozengqing/Downloads/图学习/backend/services/topic_service.py`
- `/Users/zhaozengqing/Downloads/图学习/backend/services/node_service.py`
- `/Users/zhaozengqing/Downloads/图学习/backend/services/session_service.py`
- `/Users/zhaozengqing/Downloads/图学习/backend/services/review_service.py`
- `/Users/zhaozengqing/Downloads/图学习/src-tauri/src/main.rs`
- `/Users/zhaozengqing/Downloads/图学习/src-tauri/sidecar/axon-server.sh`

## Visual/Browser Findings
- 计划做浏览器验证，但当前内置 Playwright / Chrome MCP 受现有 Chrome 持久化会话冲突影响，尚未形成可靠浏览器证据；本轮结论目前以代码、测试和子代理审阅为主。
