# Axon-Loop 系统设计

> 跨会话状态持久化 + 可中断任务执行框架

---

## 核心问题

| 问题 | 解决方案 |
|------|----------|
| 第一天 loop → 第二天继续 | state.json 持久化 + 启动时读取 |
| 任务需要 > 3 分钟 | in_progress 状态 + can_resume 标记 |
| 需要人工介入 | 暂停机制 + can_resume=false + 报告等待 |
| 任务执行中断 | checkpoint 保存 + 从断点恢复 |
| 任务清单被修改 | hash 校验 + 警告 |

---

## 目录结构

```
.claude/loop/
├── state.json              # 当前状态（核心）
├── log.md                 # 操作日志（追加）
├── runs/                  # 历史运行快照
│   └── YYYY-MM-DD-HHMMSS-session-id/
│       ├── state.json.bak
│       ├── task-list.md
│       └── log.md
└── templates/              # 模板文件
    ├── task-list-template.md
    └── state-schema.json
```

---

## state.json 结构

```json
{
  "version": "1.0",
  "loop_session": {
    "session_id": "uuid-v4",
    "session_name": "用户给定的任务名称",
    "started_at": "ISO8601",
    "task_list_hash": "sha256(task-list)",
    "total_tasks": 10
  },
  "task_progress": {
    "current_task": 3,
    "completed": [1, 2],
    "failed": [],
    "skipped": [],
    "in_progress": {
      "task_id": 3,
      "started_at": "ISO8601",
      "last_checkpoint": "函数A完成，等待函数B",
      "can_resume": true,
      "checkpoints": [
        { "at": "步骤1完成", "saved_state": {} }
      ]
    }
  },
  "execution_stats": {
    "completed": 2,
    "failed": 0,
    "skipped": 0,
    "total": 10
  },
  "last_updated": "ISO8601",
  "status": "running | paused | completed | aborted"
}
```

---

## 运行状态

```
┌─────────────────────────────────────────────────────────┐
│                    loop 会话生命周期                       │
└─────────────────────────────────────────────────────────┘

start → running → [paused] → completed
                  ↘ [running] → aborted

状态说明：
- running: 正在执行
- paused: 暂停等待人工介入
- completed: 全部任务完成
- aborted: 手动终止
```

---

## 3 分钟检查逻辑

```
┌─────────────────────────────────────────────┐
│            每 3 分钟检查点                   │
└─────────────────────────────────────────────┘

检查 in_progress 状态：

├── in_progress == null
│   └── 读取 current_task → 开始执行
│
├── in_progress.can_resume == true
│   └── 继续执行 → 更新 checkpoint
│
├── in_progress.can_resume == false
│   └── 暂停 → 报告等待原因 → 等待指令
│
└── task 验证失败
    └── 标记 failed → 尝试备选 → 还失败标记跳过

检查 current_task：

├── current_task > total_tasks
│   └── 全部完成 → status=completed → 生成报告
│
└── 执行当前任务 → 完成后 current_task++
```

---

## 任务设计要求

每个任务必须设计为"可中断 + 可恢复"：

```markdown
## 任务 #N：[任务名称]
- **文件**: [具体文件路径]
- **预计耗时**: 5-15 分钟
- **可中断点**: [checkpoint 点]
- **状态保存**: [如何保存进度]
- **恢复方式**: [如何从断点继续]
- **人工介入条件**: [什么情况下需要暂停]
```

---

## 日志格式

```markdown
# Loop Execution Log

## 2026-03-18 | session-abc123 | running

### 会话信息
- 任务清单: [名称]
- 总任务数: 10
- 开始时间: 2026-03-18T10:00:00

---

## 任务 #1 | 2026-03-18T10:00:05 | ✅ 完成

- **执行时间**: 2 分钟
- **文件**: `backend/services/x.py`
- **验证**: `pytest tests/test_x.py -v` → PASSED
- **摘要**: 修复空指针问题

---

## 任务 #3 | 2026-03-18T10:15:00 | ⏸ 暂停

- **暂停原因**: 需要人工确认 API 行为
- **当前进度**: 函数A完成，函数B需要调试
- **可恢复**: 是
- **等待**: 用户确认后继续
```

---

## 边界情况处理

| 情况 | 处理方式 |
|------|----------|
| 任务 #5 进行中，#3 失败 | 先尝试备选方案 #3，还失败则标记跳过继续 #5 |
| 用户修改了任务清单 | 检测 hash 变化，警告用户，确认后重置状态 |
| state.json 损坏 | 从最近 runs/ 备份恢复 |
| 连续 3 次同一任务失败 | 暂停，报告，需要明确决策 |
| 所有任务完成 | status=completed，生成最终报告 |
| 用户强制终止 | status=aborted，保存当前状态 |

---

## 初始化状态

```json
{
  "version": "1.0",
  "loop_session": null,
  "task_progress": {
    "current_task": 0,
    "completed": [],
    "failed": [],
    "skipped": [],
    "in_progress": null
  },
  "execution_stats": {
    "completed": 0,
    "failed": 0,
    "skipped": 0,
    "total": 0
  },
  "last_updated": null,
  "status": "idle"
}
```

---

## 快速参考

```bash
# 初始化新项目
./scripts/init-axon-loop.sh

# 查看当前状态
cat .claude/loop/state.json

# 手动备份
./scripts/axon-loop.sh backup

# 恢复备份
./scripts/axon-loop.sh restore runs/2026-03-18-100000-session-id/
```
