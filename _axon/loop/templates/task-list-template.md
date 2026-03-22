# 任务清单模板

> 由 axon-plan 生成的标准化任务清单格式

```markdown
# 任务清单 — [目标简述]

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

---
```

## 填充说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `文件` | 精确路径 | `backend/services/node_service.py` |
| `变更类型` | 单一类型 | `bugfix` |
| `验证标准` | 命令+输出 | `pytest tests/x.py -v → PASSED` |
| `预计耗时` | 合理估算 | `5-10 分钟` |
| `可中断点` | 原子步骤 | `函数A完成` |
| `人工介入条件` | 触发条件 | `API 行为与预期不符` |

## 示例

```markdown
## 任务 #3：修复 expand_score 算法

### 基本信息
- **文件**: `backend/services/node_service.py`
- **变更类型**: bugfix
- **前置依赖**: #1

### 设计与约束
- **验证标准**: `python -c "from services.node_service import calculate_expand_score; print(calculate_expand_score({'importance': 0.8, 'friction': 0.2}, 'solve_task'))"` → 输出接近 0.6
- **风险提示**: 无
- **回滚方案**: `git checkout -- backend/services/node_service.py`
- **备选方案**: 使用固定的 0.5 作为 fallback

### 执行设计
- **预计耗时**: 3-5 分钟
- **可中断点**: 函数定位完成 | 算法修改完成 | 验证通过
- **状态保存**: 记录已修改的函数名和行号
- **恢复方式**: 从 state.json 读取已完成的 checkpoint
- **人工介入条件**: 计算结果与预期偏差 > 20%
```
