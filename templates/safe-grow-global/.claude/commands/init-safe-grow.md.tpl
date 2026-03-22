---
argument-hint: [project-name]
description: 为当前项目初始化 safe-grow 单点安全增长工作流
---

你正在为当前项目初始化 `safe-grow` 工作流。

执行步骤：

1. 将当前工作目录视为目标项目根目录；如果 `$ARGUMENTS` 非空，把它作为项目展示名称，否则使用当前目录名。

2. 运行以下命令，把本地工作流文件安装到当前项目：

- 如果 `$ARGUMENTS` 为空：

```bash
python3 {{SAFE_GROW_KIT_PATH}}/bin/init_safe_grow.py .
```

- 如果 `$ARGUMENTS` 非空：

```bash
python3 {{SAFE_GROW_KIT_PATH}}/bin/init_safe_grow.py . --project-name "$ARGUMENTS"
```

3. 安装完成后，读取这些文件：
   - `CLAUDE.md`（如果存在）
   - `README.md`、`README-frontend.md` 或其他项目说明（如果存在）
   - `.claude/loop/PROJECT_GROWTH.md`

4. 基于现有文档先补全 `.claude/loop/PROJECT_GROWTH.md`：
   - 项目本质
   - 核心用户
   - 主价值闭环
   - 北极星
   - 优先增长方向
   - 反目标
   - 成功指标
   只把能从真实文档和代码推断出来的内容写进去；不确定的地方明确标注为假设。

5. 如果关键信息仍缺失，再用最少的问题向用户确认，不要一开始就连发很多问题。

6. 最后告诉用户：
   - 先把审计结果填入 `.claude/loop/GLM_AUDIT.md`
   - 然后执行 `/safe-grow`
   - 如果想定时推进，再执行 `/loop 10m /safe-grow`
