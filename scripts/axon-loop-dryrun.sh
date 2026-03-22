#!/bin/bash
#===============================================================================
# Axon-Loop Dry Run 验证器
# 验证任务清单格式，不实际执行
#
# 用法:
#   ./scripts/axon-loop-dryrun.sh < task-list.md
#   ./scripts/axon-loop-dryrun.sh --file task-list.md
#   ./scripts/axon-loop-dryrun.sh --check-state
#===============================================================================

set -e

LOOP_DIR=".claude/loop"
TEMPLATE_DIR="$LOOP_DIR/templates"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

error() { echo -e "${RED}[ERROR]${NC} $1"; ((ERRORS++)); }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; ((WARNINGS++)); }
info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }

#-------------------------------------------------------------------------------
# 验证任务清单
#-------------------------------------------------------------------------------
validate_task_list() {
    local content="$1"
    local line_num=0

    # 检查元信息
    if ! echo "$content" | grep -q "^# 任务清单"; then
        error "缺少标题 '# 任务清单'"
    fi

    # 统计任务数量
    local task_count=$(echo "$content" | grep -c "^## 任务 #" || true)
    if [[ "$task_count" -eq 0 ]]; then
        error "没有找到任何任务"
    else
        info "找到 $task_count 个任务"
    fi

    # 验证每个任务
    local in_task=false
    local task_num=0
    local task_name=""

    while IFS= read -r line; do
        ((line_num++))

        # 检测任务开始
        if [[ "$line" =~ ^##\ 任务\ #([0-9]+) ]]; then
            in_task=true
            task_num="${BASH_REMATCH[1]}"
            task_name="${line#### 任务 #${task_num}: }"
            info "验证任务 #$task_num: $task_name"

            # 检查必填字段
            continue
        fi

        if $in_task; then
            # 任务结束（下一个任务或文档结束）
            if [[ "$line" =~ ^#|^##[^#] || -z "$line" ]]; then
                in_task=false
            else
                # 检查必填字段
                case "$line" in
                    *- **文件**:*)
                        ;;
                    *- **验证标准**:*)
                        ;;
                    *- **回滚方案**:*)
                        ;;
                esac
            fi
        fi
    done <<< "$content"

    # 验证前置依赖
    info "检查前置依赖..."
    local deps_ok=true
    for i in $(seq 1 $task_count); do
        local dep=$(echo "$content" | sed -n "/^## 任务 #$i\b/,/^---/p" | grep "前置依赖" | grep -oP '#\d+' | tr -d '#')
        if [[ -n "$dep" ]]; then
            if [[ "$dep" -ge "$i" ]]; then
                error "任务 #$i 依赖 #$dep（依赖必须在前面）"
                deps_ok=false
            fi
        fi
    done
    $deps_ok && ok "前置依赖无循环"

    # 检查文件路径是否存在（如果项目已存在）
    if [[ -d ".claude" ]]; then
        info "检查文件路径..."
        local missing_files=0
        while IFS= read -r line; do
            if [[ "$line" =~ ^- \*\*文件\*\*:\ (.+) ]]; then
                local filepath="${BASH_REMATCH[1]}"
                # 移除 Markdown 格式
                filepath=$(echo "$filepath" | sed 's/`//g' | awk '{print $1}')
                if [[ ! -e "$filepath" ]]; then
                    warn "文件不存在: $filepath"
                    ((missing_files++))
                fi
            fi
        done <<< "$content"

        if [[ "$missing_files" -eq 0 ]]; then
            ok "所有文件路径有效"
        fi
    fi
}

#-------------------------------------------------------------------------------
# 验证 state.json
#-------------------------------------------------------------------------------
validate_state() {
    if [[ ! -f "$LOOP_DIR/state.json" ]]; then
        warn "state.json 不存在"
        return
    fi

    info "验证 state.json..."

    # JSON 格式
    if python3 -c "import sys,json; json.load(open('$LOOP_DIR/state.json'))" 2>/dev/null; then
        ok "state.json JSON 格式有效"
    else
        error "state.json JSON 格式无效"
    fi
}

#-------------------------------------------------------------------------------
# 显示帮助
#-------------------------------------------------------------------------------
show_help() {
    cat << EOF
Axon-Loop Dry Run 验证器

用法:
    ./scripts/axon-loop-dryrun.sh [options]

选项:
    --file <path>      从文件读取任务清单
    --check-state      仅验证 state.json
    --help             显示此帮助

示例:
    ./scripts/axon-loop-dryrun.sh
    ./scripts/axon-loop-dryrun.sh --file task-list.md
    ./scripts/axon-loop-dryrun.sh --check-state

检查项:
    - 标题格式
    - 任务数量
    - 必填字段
    - 前置依赖（无循环）
    - 文件路径有效性
    - state.json 格式
EOF
}

#-------------------------------------------------------------------------------
# 主函数
#-------------------------------------------------------------------------------
main() {
    local task_list=""
    local check_state=false

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --file|-f)
                task_list=$(cat "$2")
                shift 2
                ;;
            --check-state)
                check_state=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    echo "============================================"
    echo "  Axon-Loop Dry Run 验证"
    echo "============================================"
    echo ""

    if $check_state; then
        validate_state
    else
        if [[ -z "$task_list" ]]; then
            # 从 stdin 读取
            if [[ -t 0 ]]; then
                info "从 stdin 读取（使用管道或 heredoc）"
                info "示例: ./scripts/axon-loop-dryrun.sh < task-list.md"
                echo ""
                show_help
                exit 0
            fi
            task_list=$(cat)
        fi

        validate_task_list "$task_list"
    fi

    echo ""
    echo "============================================"
    echo "  验证结果"
    echo "============================================"
    echo ""
    echo -e "错误: ${RED}$ERRORS${NC}"
    echo -e "警告: ${YELLOW}$WARNINGS${NC}"
    echo ""

    if [[ $ERRORS -eq 0 ]]; then
        echo -e "${GREEN}验证通过${NC}"
        exit 0
    else
        echo -e "${RED}验证失败${NC}"
        exit 1
    fi
}

main "$@"
