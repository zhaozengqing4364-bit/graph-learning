---
argument-hint: [focus or horizon]
description: 深度分析当前项目并生成未来增长路线图，优先提升用户使用效果与系统主能力
---

使用 `.claude/skills/growth-architect/SKILL.md` 作为本命令的工作流真源，并严格遵守项目 `CLAUDE.md`。

执行规则：

1. 先读取以下文件：
   - `CLAUDE.md`
   - `.claude/skills/growth-architect/SKILL.md`
   - `.claude/roadmap/PROJECT_FUTURE.md`
   - `.claude/loop/PROJECT_GROWTH.md`
   - `.claude/loop/GLM_AUDIT.md`
   - `.claude/loop/GROWTH_BACKLOG.md`
   - `.claude/loop/state.json`
   - `task_plan.md`
   - `findings.md`
   - `progress.md`
   - 最新的 `docs/audits/` 与 `docs/plans/` 相关文档

2. 真实扫描代码与系统表面，而不是只复述文档：
   - `src/`
   - `backend/`
   - `src-tauri/`
   - `scripts/`
   - tests

3. 每个候选方向必须至少明确：
   - 用户问题
   - 用户收益
   - 系统能力收益
   - 证据来源
   - 可能涉及文件
   - 最小可行切入点
   - 依赖关系
   - 验证方式
   - 成功信号
   - 为什么现在不应该做成大重构

4. 输出结果写入：
   - `docs/plans/YYYY-MM-DD-<project-name>-growth-roadmap.md`

5. 如果当前 `.claude/loop/GROWTH_BACKLOG.md` 候选质量不足，允许基于路线图回补 3-5 个新的高价值增长项，但不要直接开始改业务代码。
