#!/bin/bash
#===============================================================================
# Axon-Loop 状态管理脚本
# 用法: ./scripts/axon-loop.sh <command> [options]
#
# 命令:
#   status          显示当前状态
#   backup          手动备份当前状态
#   restore <path>  从备份恢复
#   init            初始化（调用 init-axon-loop.sh）
#   validate        验证 state.json 格式
#   clean <days>    清理 N 天前的备份
#
# 示例:
#   ./scripts/axon-loop.sh status
#   ./scripts/axon-loop.sh backup
#   ./scripts/axon-loop.sh restore .claude/loop/runs/2026-03-18-100000/
#   ./scripts/axon-loop.sh clean 7
#===============================================================================

set -e

LOOP_DIR=".claude/loop"
STATE_FILE="$LOOP_DIR/state.json"
LOG_FILE="$LOOP_DIR/log.md"
RUNS_DIR="$LOOP_DIR/runs"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
title() { echo -e "${CYAN}==>${NC} ${BLUE}$1${NC}"; }

#-------------------------------------------------------------------------------
# 显示帮助
#-------------------------------------------------------------------------------
show_help() {
    cat << EOF
Axon-Loop 状态管理脚本

用法: ./scripts/axon-loop.sh <command> [options]

命令:
  status              显示当前状态
  backup              手动备份当前状态到 runs/
  restore <path>      从备份恢复
  init                初始化（调用 init-axon-loop.sh）
  validate            验证 state.json 格式
  clean <days>        清理 N 天前的备份
  session <name>      开始新的任务清单会话

示例:
  ./scripts/axon-loop.sh status              # 查看状态
  ./scripts/axon-loop.sh backup             # 备份
  ./scripts/axon-loop.sh restore runs/xxx/   # 恢复
  ./scripts/axon-loop.sh clean 7            # 删除 7 天前备份

详细文档: .claude/loop/PROTOCOL.md
EOF
}

#-------------------------------------------------------------------------------
# 显示当前状态
#-------------------------------------------------------------------------------
cmd_status() {
    if [[ ! -f "$STATE_FILE" ]]; then
        error "state.json 不存在，请先运行 init"
        exit 1
    fi

    title "Axon-Loop 当前状态"

    # 读取并格式化 JSON
    local status=$(cat "$STATE_FILE")

    local session_name=$(echo "$status" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('loop_session'); print(s.get('session_name','N/A') if s else 'N/A')" 2>/dev/null || echo "N/A")
    local session_id=$(echo "$status" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('loop_session'); print(s.get('session_id','N/A')[:8] if s else 'N/A')" 2>/dev/null || echo "N/A")
    local total=$(echo "$status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('execution_stats',{}).get('total',0))" 2>/dev/null || echo "0")
    local completed=$(echo "$status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('execution_stats',{}).get('completed',0))" 2>/dev/null || echo "0")
    local failed=$(echo "$status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('execution_stats',{}).get('failed',0))" 2>/dev/null || echo "0")
    local current=$(echo "$status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('task_progress',{}).get('current_task',0))" 2>/dev/null || echo "0")
    local loop_status=$(echo "$status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")
    local last_updated=$(echo "$status" | python3 -c "import sys,json; d=json.load(sys.stdin); u=d.get('last_updated'); print(u if u else '从未')" 2>/dev/null || echo "N/A")

    # 状态颜色
    local status_color="$NC"
    case "$loop_status" in
        running)  status_color="$GREEN" ;;
        paused)   status_color="$YELLOW" ;;
        completed) status_color="$GREEN" ;;
        aborted)  status_color="$RED" ;;
        idle)     status_color="$BLUE" ;;
    esac

    echo ""
    echo -e "  会话名称: ${CYAN}$session_name${NC}"
    echo -e "  会话 ID:   ${CYAN}$session_id${NC}..."
    echo -e "  状态:     ${status_color}$loop_status${NC}"
    echo -e "  上次更新: ${BLUE}$last_updated${NC}"
    echo ""
    echo -e "  进度:     ${GREEN}$completed${NC} / $total 完成"
    echo -e "          当前任务: $current"
    echo -e "          失败: ${RED}$failed${NC}"

    # 显示已完成和失败的任务
    local done_list=$(echo "$status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(','.join(map(str,d.get('task_progress',{}).get('completed',[]))))" 2>/dev/null || echo "")
    local fail_list=$(echo "$status" | python3 -c "import sys,json; d=json.load(sys.stdin); print(','.join(map(str,d.get('task_progress',{}).get('failed',[]))))" 2>/dev/null || echo "")

    if [[ -n "$done_list" ]]; then
        echo -e "  已完成:   ${GREEN}$done_list${NC}"
    fi
    if [[ -n "$fail_list" ]]; then
        echo -e "  失败:     ${RED}$fail_list${NC}"
    fi

    echo ""
}

#-------------------------------------------------------------------------------
# 手动备份
#-------------------------------------------------------------------------------
cmd_backup() {
    if [[ ! -f "$STATE_FILE" ]]; then
        error "state.json 不存在"
        exit 1
    fi

    local timestamp=$(date +%Y-%m-%d-%H%M%S)
    local session_id=$(cat "$STATE_FILE" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('loop_session'); print(s.get('session_id','')[:8] if s else 'no-session')" 2>/dev/null || echo "no-session")
    local backup_dir="$RUNS_DIR/$timestamp-$session_id"

    mkdir -p "$backup_dir"

    info "备份到: $backup_dir"
    cp "$STATE_FILE" "$backup_dir/state.json.bak"
    cp "$LOG_FILE" "$backup_dir/log.md.bak" 2>/dev/null || true

    # 如果有任务清单备份
    if [[ -f "$LOOP_DIR/task-list.md" ]]; then
        cp "$LOOP_DIR/task-list.md" "$backup_dir/task-list.md"
    fi

    echo ""
    info "备份完成"
    ls -la "$backup_dir"
}

#-------------------------------------------------------------------------------
# 恢复备份
#-------------------------------------------------------------------------------
cmd_restore() {
    local backup_path="$1"

    if [[ -z "$backup_path" ]]; then
        error "请指定备份路径"
        echo "用法: $0 restore <backup-path>"
        exit 1
    fi

    if [[ ! -d "$backup_path" ]]; then
        error "备份目录不存在: $backup_path"
        exit 1
    fi

    if [[ ! -f "$backup_path/state.json.bak" ]]; then
        error "不是有效的备份目录（缺少 state.json.bak）"
        exit 1
    fi

    warn "即将从备份恢复..."
    warn "  备份位置: $backup_path"
    echo ""

    read -p "确认恢复? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "取消恢复"
        exit 0
    fi

    # 备份当前状态
    cmd_backup

    info "恢复状态..."
    cp "$backup_path/state.json.bak" "$STATE_FILE"
    if [[ -f "$backup_path/log.md.bak" ]]; then
        cp "$backup_path/log.md.bak" "$LOG_FILE"
    fi

    info "恢复完成"
    cmd_status
}

#-------------------------------------------------------------------------------
# 初始化
#-------------------------------------------------------------------------------
cmd_init() {
    if [[ -x "./scripts/init-axon-loop.sh" ]]; then
        ./scripts/init-axon-loop.sh "$@"
    else
        error "init-axon-loop.sh 不存在或不可执行"
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# 验证 state.json
#-------------------------------------------------------------------------------
cmd_validate() {
    if [[ ! -f "$STATE_FILE" ]]; then
        error "state.json 不存在"
        exit 1
    fi

    # 使用 python 验证 JSON
    if python3 -c "import sys,json; json.load(open('$STATE_FILE'))" 2>/dev/null; then
        info "state.json 格式有效"
    else
        error "state.json 格式无效"
        exit 1
    fi

    # 验证必填字段
    local required_fields=("version" "loop_session" "task_progress" "execution_stats" "last_updated" "status")
    for field in "${required_fields[@]}"; do
        if python3 -c "import sys,json; d=json.load(open('$STATE_FILE')); exit(0 if '$field' in d else 1)" 2>/dev/null; then
            echo -e "  ✓ $field"
        else
            error "缺少必填字段: $field"
            exit 1
        fi
    done

    info "所有必填字段存在"
}

#-------------------------------------------------------------------------------
# 清理旧备份
#-------------------------------------------------------------------------------
cmd_clean() {
    local days="${1:-7}"

    if [[ ! -d "$RUNS_DIR" ]]; then
        info "没有需要清理的备份"
        exit 0
    fi

    info "清理 ${days} 天前的备份..."

    local count=$(find "$RUNS_DIR" -maxdepth 1 -type d -mtime "+$days" | wc -l)
    if [[ "$count" -eq 0 ]]; then
        info "没有找到需要清理的备份"
        exit 0
    fi

    warn "将删除 $count 个旧备份"
    read -p "确认? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "取消清理"
        exit 0
    fi

    find "$RUNS_DIR" -maxdepth 1 -type d -mtime "+$days" -exec rm -rf {} \;
    info "清理完成"
}

#-------------------------------------------------------------------------------
# 开始新会话
#-------------------------------------------------------------------------------
cmd_session() {
    local session_name="${1:-unnamed}"

    if [[ ! -f "$STATE_FILE" ]]; then
        error "state.json 不存在，请先运行 init"
        exit 1
    fi

    # 生成 session ID
    local session_id=$(python3 -c "import uuid; print(str(uuid.uuid4()))")

    info "开始新会话: $session_name"
    info "Session ID: $session_id"

    # 更新 state.json
    python3 << EOF
import json
from datetime import datetime

with open('$STATE_FILE', 'r') as f:
    state = json.load(f)

state['loop_session'] = {
    'session_id': '$session_id',
    'session_name': '$session_name',
    'started_at': datetime.now().isoformat(),
    'task_list_hash': '',
    'total_tasks': 0
}
state['task_progress'] = {
    'current_task': 0,
    'completed': [],
    'failed': [],
    'skipped': [],
    'in_progress': None
}
state['execution_stats'] = {
    'completed': 0,
    'failed': 0,
    'skipped': 0,
    'total': 0
}
state['status'] = 'idle'
state['last_updated'] = datetime.now().isoformat()

with open('$STATE_FILE', 'w') as f:
    json.dump(state, f, indent=2)
EOF

    info "状态已重置，可以开始新的 loop"
}

#-------------------------------------------------------------------------------
# 主函数
#-------------------------------------------------------------------------------
main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi

    local command="$1"
    shift

    case "$command" in
        status|s)
            cmd_status
            ;;
        backup|b)
            cmd_backup
            ;;
        restore|r)
            cmd_restore "$@"
            ;;
        init|i)
            cmd_init "$@"
            ;;
        validate|v)
            cmd_validate
            ;;
        clean|c)
            cmd_clean "$@"
            ;;
        session|session)
            cmd_session "$@"
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
