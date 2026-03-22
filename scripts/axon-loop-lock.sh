#!/bin/bash
#===============================================================================
# Axon-Loop 文件锁管理
# 防止并发执行
#
# 用法:
#   ./scripts/axon-loop-lock.sh acquire    获取锁
#   ./scripts/axon-loop-lock.sh release   释放锁
#   ./scripts/axon-loop-lock.sh status    查看锁状态
#===============================================================================

set -e

LOOP_DIR=".claude/loop"
LOCK_DIR="$LOOP_DIR/.lock"
LOCK_FILE="$LOCK_DIR/pid"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

#-------------------------------------------------------------------------------
# 获取锁
#-------------------------------------------------------------------------------
acquire() {
    if [[ -d "$LOCK_DIR" ]]; then
        local pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            echo -e "${RED}[ERROR]${NC} 另一个 loop 正在执行 (PID: $pid)"
            echo "如确认没有其他 loop 运行，删除 .claude/loop/.lock 目录"
            return 1
        else
            echo -e "${YELLOW}[WARN]${NC} 发现残留锁文件，清理中..."
            cleanup
        fi
    fi

    mkdir -p "$LOCK_DIR"
    echo $$ > "$LOCK_FILE"

    # 设置退出时自动释放
    trap 'release 2>/dev/null' EXIT

    echo -e "${GREEN}[OK]${NC} 锁已获取 (PID: $$)"
    return 0
}

#-------------------------------------------------------------------------------
# 释放锁
#-------------------------------------------------------------------------------
release() {
    if [[ -d "$LOCK_DIR" ]]; then
        local pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [[ "$pid" == "$$" ]]; then
            rm -rf "$LOCK_DIR"
            echo -e "${GREEN}[OK]${NC} 锁已释放"
        fi
    fi
}

#-------------------------------------------------------------------------------
# 清理残留锁
#-------------------------------------------------------------------------------
cleanup() {
    rm -rf "$LOCK_DIR"
    echo -e "${YELLOW}[INFO]${NC} 锁已清理"
}

#-------------------------------------------------------------------------------
# 查看锁状态
#-------------------------------------------------------------------------------
status() {
    if [[ -d "$LOCK_DIR" ]]; then
        local pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "unknown")
        echo -e "${RED}[LOCKED]${NC} 锁被占用"
        echo "  PID: $pid"
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "  状态: ${GREEN}运行中${NC}"
        else
            echo -e "  状态: ${YELLOW}已结束（残留）${NC}"
            echo "  运行 'rm -rf $LOCK_DIR' 清理"
        fi
    else
        echo -e "${GREEN}[UNLOCKED]${NC} 未加锁"
    fi
}

#-------------------------------------------------------------------------------
# 主函数
#-------------------------------------------------------------------------------
case "${1:-}" in
    acquire|a)
        acquire
        ;;
    release|r)
        release
        ;;
    status|s)
        status
        ;;
    cleanup|c)
        cleanup
        ;;
    *)
        echo "用法: $0 {acquire|release|status|cleanup}"
        exit 1
        ;;
esac
