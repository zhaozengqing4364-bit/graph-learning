# 边界情况与改进点

## 已实现的边界情况处理

| 边界情况 | 处理方式 | 实现文件 |
|----------|----------|----------|
| 第一天 loop → 第二天继续 | state.json 持久化，启动时读取 | `state.json` |
| 任务需要 > 3 分钟 | checkpoint + can_resume 机制 | `PROTOCOL.md` |
| 需要人工介入 | can_resume=false + 暂停状态 + 报告 | `PROTOCOL.md` |
| 任务执行中断 | checkpoint 保存 + 从断点恢复 | `PROTOCOL.md` |
| 任务清单被修改 | hash 校验 + 警告 | 待实现 |
| state.json 损坏 | 从 runs/ 备份恢复 | `axon-loop.sh restore` |
| 并发 loop 执行 | 文件锁机制 | `axon-loop-lock.sh` |
| 任务清单格式验证 | Dry run 验证 | `axon-loop-dryrun.sh` |

## 已实现的辅助功能

| 功能 | 脚本 |
|------|-------|
| 初始化 | `init-axon-loop.sh` |
| 状态管理 | `axon-loop.sh` |
| 文件锁 | `axon-loop-lock.sh` |
| Dry run 验证 | `axon-loop-dryrun.sh` |

---

## 待完善的边界情况

### 1. 并发 loop 执行

**问题**：用户可能同时启动两个 loop 命令

**方案**：文件锁
```bash
# 在 state.json 目录创建 .lock 文件
if ! mkdir "$LOOP_DIR/.lock" 2>/dev/null; then
    error "另一个 loop 正在执行"
    exit 1
fi
trap "rmdir '$LOOP_DIR/.lock'" EXIT
```

### 2. 定时自动暂停

**问题**：防止 loop 失控运行太久

**方案**：添加 max_execution_time 配置
```json
{
  "loop_session": {
    "max_execution_time": 30,
    "auto_pause_after_minutes": 25
  }
}
```

### 3. Dry Run 模式

**问题**：只想验证任务清单格式，不实际执行

**方案**：
```
/loop 3m --dry-run
[粘贴任务清单]
```

### 4. 自动 checkpoint

**问题**：即使任务未到中断点也想定期保存

**方案**：每 30 秒自动保存一次 checkpoint

### 5. Git 集成

**问题**：成功执行后想自动 commit

**方案**：添加 auto_commit 选项
```bash
./scripts/axon-loop.sh session "任务" --auto-commit
```

---

## 改进点

### 高优先级

| 改进点 | 描述 |
|--------|------|
| 文件锁 | 防止并发执行 |
| Dry run | 验证任务清单格式 |
| 进度百分比 | 更好的 UX |
| 任务依赖可视化 | 显示执行顺序图 |

### 中优先级

| 改进点 | 描述 |
|--------|------|
| 通知集成 | macOS 通知需要人工介入 |
| 自动 checkpoint | 每 30 秒保存 |
| Git 集成 | 成功后自动 commit |
| 定时暂停 | 防止失控运行 |

### 低优先级

| 改进点 | 描述 |
|--------|------|
| 多机器同步 | 通过 git 同步状态 |
| 任务超时 | 单任务超时控制 |
| 并行任务 | 可并行的任务同时执行 |
| Web UI | 可视化状态面板 |

---

## 通知集成方案

```bash
# macOS 通知
osascript -e 'display notification "Loop 需要人工介入" with title "Axon-Loop"'

# 或者使用 notifier 工具
brew install terminal-notifier
terminal-notifier -title "Axon-Loop" -message "任务 #3 需要确认"
```

---

## 文件锁实现

```bash
# acquire_lock
acquire_lock() {
    local lock_dir=".claude/loop/.lock"
    if ! mkdir "$lock_dir" 2>/dev/null; then
        echo "ERROR: 另一个 loop 正在执行"
        return 1
    fi
    trap "rmdir '$lock_dir'" EXIT
    return 0
}
```

---

## 后续可以添加的脚本

1. **`axon-loop-lock.sh`** - 文件锁管理
2. **`axon-loop-dryrun.sh`** - Dry run 验证
3. **`axon-loop-notify.sh`** - 通知集成
4. **`axon-loop-git.sh`** - Git 自动提交

---
