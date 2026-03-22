# 任务清单 — H2 批次 1 (H2-001~005: 学习质量提升)

## 任务 #1：GROW-H2-001 — PRACTICE_DIMENSION_MAP 添加 recall 显式映射
## 任务 #2：GROW-H2-002 — 练习 prompt 包含节点关系上下文
## 任务 #3：GROW-H2-003 — apply 练习类型添加 few-shot 示例
## 任务 #4：GROW-H2-004 — Diagnoser prompt 要求 friction_tag 原因
## 任务 #5：GROW-H2-005 — Diagnoser friction_tags 白名单校验

全部修改: backend/ 目录下对应文件
验证: .venv/bin/python -m pytest backend/tests/test_core.py -q -x
