#!/bin/bash
#===============================================================================
# Axon-Loop 初始化脚本
# 用法: ././_axon/scripts/init-axon-loop.sh [--force]
#
# 功能:
#   1. 创建 ./_axon/loop/ 目录结构
#   2. 初始化 state.json
#   3. 初始化 log.md
#   4. 复制模板文件
#   5. 设置权限
#
# 选项:
#   --force    强制重新初始化（会备份当前状态）
#   --help     显示帮助
#===============================================================================

set -e

LOOP_DIR="./_axon/loop"
TEMPLATE_DIR="./_axon/loop/templates"
RUNS_DIR="./_axon/loop/runs"
SCRIPTS_DIR="./_axon/scripts"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

#-------------------------------------------------------------------------------
# 帮助信息
#-------------------------------------------------------------------------------
show_help() {
    cat << EOF
Axon-Loop 初始化脚本

用法: ././_axon/scripts/init-axon-loop.sh [选项]

选项:
  --force    强制重新初始化（会备份当前状态到 runs/）
  --help     显示此帮助信息

示例:
  ././_axon/scripts/init-axon-loop.sh              # 首次初始化
  ././_axon/scripts/init-axon-loop.sh --force     # 重新初始化（备份当前）

更多信息:
  参见 ./_axon/loop/PROTOCOL.md
EOF
}

#-------------------------------------------------------------------------------
# 备份现有状态
#-------------------------------------------------------------------------------
backup_existing() {
    if [[ -f "$LOOP_DIR/state.json" ]]; then
        local timestamp=$(date +%Y-%m-%d-%H%M%S)
        local backup_dir="$RUNS_DIR/pre-init-$timestamp"
        mkdir -p "$backup_dir"
        info "备份现有状态到 $backup_dir"
        cp -r "$LOOP_DIR"/* "$backup_dir/" 2>/dev/null || true
    fi
}

#-------------------------------------------------------------------------------
# 创建目录结构
#-------------------------------------------------------------------------------
create_dirs() {
    info "创建目录结构..."
    mkdir -p "$LOOP_DIR/templates"
    mkdir -p "$LOOP_DIR/runs"
    mkdir -p "$SCRIPTS_DIR"
    info "  ✓ $LOOP_DIR/"
    info "  ✓ $LOOP_DIR/templates/"
    info "  ✓ $LOOP_DIR/runs/"
}

#-------------------------------------------------------------------------------
# 初始化 state.json
#-------------------------------------------------------------------------------
init_state() {
    local state_file="$LOOP_DIR/state.json"

    if [[ -f "$state_file" && "$1" != "--force" ]]; then
        info "state.json 已存在，跳过初始化"
        return
    fi

    info "初始化 state.json..."
    cat > "$state_file" << 'EOF'
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
EOF
}

#-------------------------------------------------------------------------------
# 初始化 log.md
#-------------------------------------------------------------------------------
init_log() {
    local log_file="$LOOP_DIR/log.md"

    if [[ -f "$log_file" && "$1" != "--force" ]]; then
        info "log.md 已存在，跳过初始化"
        return
    fi

    info "初始化 log.md..."
    cat > "$log_file" << 'EOF'
# Loop Execution Log

> 每轮追加记录，用于追踪执行历史和调试。

## 使用说明

- 每条记录包含：时间、会话ID、任务ID、状态、文件、验证结果
- 按时间倒序排列（最新在上）
- 手动编辑时保持格式一致

---

## 记录格式

```markdown
## YYYY-MM-DD HH:MM | session-id | status

### 会话信息
- 任务清单: [名称]
- 总任务数: N
- 开始时间: ISO8601

### 任务 #N | HH:MM | status
- **执行时间**: X 分钟
- **文件**: [文件列表]
- **验证**: [命令] → [结果]
- **摘要**: [描述]
```

---

## 状态说明

| 状态 | 含义 |
|------|------|
| `running` | 执行中 |
| `completed` | 全部完成 |
| `paused` | 暂停等待 |
| `aborted` | 手动终止 |

| 任务状态 | 含义 |
|----------|------|
| `✅` | 完成 |
| `❌` | 失败 |
| `⏸` | 暂停 |
| `⏭` | 跳过 |
| `⏳` | 进行中 |

---
EOF
}

#-------------------------------------------------------------------------------
# 复制模板文件
#-------------------------------------------------------------------------------
copy_templates() {
    info "复制模板文件..."

    # state-schema.json
    cat > "$TEMPLATE_DIR/state-schema.json" << 'EOF'
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Axon-Loop State",
  "type": "object",
  "properties": {
    "version": { "type": "string", "const": "1.0" },
    "loop_session": { "type": ["object", "null"] },
    "task_progress": {
      "type": "object",
      "properties": {
        "current_task": { "type": "integer" },
        "completed": { "type": "array", "items": { "type": "integer" } },
        "failed": { "type": "array", "items": { "type": "integer" } },
        "skipped": { "type": "array", "items": { "type": "integer" } },
        "in_progress": { "type": ["object", "null"] }
      }
    },
    "execution_stats": {
      "type": "object",
      "properties": {
        "completed": { "type": "integer" },
        "failed": { "type": "integer" },
        "skipped": { "type": "integer" },
        "total": { "type": "integer" }
      }
    },
    "last_updated": { "type": ["string", "null"] },
    "status": { "type": "string", "enum": ["idle", "running", "paused", "completed", "aborted"] }
  }
}
EOF

    # task-list-template.md
    cat > "$TEMPLATE_DIR/task-list-template.md" << 'EOF'
# 任务清单模板

> 由 axon-plan 生成的标准化任务清单格式

## 元信息
- **任务清单ID**: [uuid]
- **创建时间**: ISO8601
- **总任务数**: N
- **预计总耗时**: X-Y 分钟

---

## 任务 #N：[任务名称]

### 基本信息
- **文件**: [具体文件路径]
- **变更类型**: bugfix | feature | refactor | config | test
- **前置依赖**: #N | 无

### 设计与约束
- **验证标准**: [具体命令 + 预期输出]
- **风险提示**: [如果有]
- **回滚方案**: [如果失败，怎么回滚]
- **备选方案**: [方案A失败后的方案B]

### 执行设计（可中断）
- **预计耗时**: 5-15 分钟
- **可中断点**: [checkpoint 点]
- **状态保存**: [如何保存进度]
- **恢复方式**: [如何从断点继续]
- **人工介入条件**: [什么情况下需要暂停]
EOF

    info "  ✓ templates/state-schema.json"
    info "  ✓ templates/task-list-template.md"
}

#-------------------------------------------------------------------------------
# 设置权限
#-------------------------------------------------------------------------------
set_permissions() {
    info "设置权限..."

    # 模板文件只读
    chmod 444 "$TEMPLATE_DIR"/*.json 2>/dev/null || true
    chmod 444 "$TEMPLATE_DIR"/*.md 2>/dev/null || true

    # 数据文件读写
    chmod 644 "$LOOP_DIR/state.json" 2>/dev/null || true
    chmod 644 "$LOOP_DIR/log.md" 2>/dev/null || true

    # runs 目录可写
    chmod 755 "$RUNS_DIR"

    info "  ✓ templates/ 只读"
    info "  ✓ state.json, log.md 读写"
    info "  ✓ runs/ 可读写"
}

#-------------------------------------------------------------------------------
# 主函数
#-------------------------------------------------------------------------------
main() {
    echo "============================================"
    echo "  Axon-Loop 初始化"
    echo "============================================"
    echo ""

    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --force|-f)
            warn "强制模式：备份现有状态后重新初始化"
            backup_existing
            ;;
        "")
            # 默认模式：检查是否已初始化
            if [[ -f "$LOOP_DIR/state.json" ]]; then
                info "Axon-Loop 已初始化，可直接使用"
                info "使用 --force 重新初始化"
                exit 0
            fi
            ;;
        *)
            error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac

    create_dirs
    init_state "$@"
    init_log "$@"
    copy_templates
    set_permissions

    echo ""
    echo "============================================"
    echo -e "${GREEN}  Axon-Loop 初始化完成${NC}"
    echo "============================================"
    echo ""
    info "下一步："
    info "  1. 查看状态: cat $LOOP_DIR/state.json"
    info "  2. 使用 /loop 命令执行任务"
    info "  3. 参见 $LOOP_DIR/PROTOCOL.md"
}

main "$@"
