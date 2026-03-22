# AxonClone 部署运维与开发环境文档

## 一、文档目的

本文档用于定义 AxonClone 的本地开发环境、项目启动方式、依赖服务管理、桌面端打包发布、日志与故障排查、版本管理和运行时运维建议，作为研发搭建环境、联调运行、打包发布与后续维护的统一依据。

AxonClone 当前定位为单机桌面产品，因此“部署运维”不等同于云服务 DevOps，而更偏向：
- 本地开发环境可稳定搭建
- 桌面客户端可一键启动
- 本地 sidecar 服务可管理
- 依赖服务可健康检查
- 本地数据可定位与恢复
- 打包发布流程清晰可重复

---

## 二、环境角色划分

AxonClone 运行包含四类环境：

1. 本地开发环境
2. 本地联调环境
3. 打包测试环境
4. 发布运行环境

---

## 三、本地开发环境要求

## 3.1 基础运行环境

建议开发机安装：
- Node.js LTS
- npm 或 pnpm
- Rust toolchain
- Python 3.12
- Neo4j 本地实例
- Git

可选：
- Docker（仅用于本地数据库或工具辅助）
- Ollama（若测试本地 fallback）

---

## 3.2 前端环境

### 必需项
- Node.js
- 包管理器
- 浏览器内核调试环境

### 启动方式
- `npm install`
- `npm run dev`
- Tauri 与前端联动时通过 `cargo tauri dev`

---

## 3.3 Rust / Tauri 环境

### 必需项
- Rust stable toolchain
- 对应平台的编译依赖

### 作用
- 启动 Tauri 容器
- 管理桌面壳与 sidecar
- 打包产物

---

## 3.4 Python / FastAPI 环境

### 必需项
- Python 3.12
- 虚拟环境工具（venv / uv / poetry 任选其一）
- requirements 或 pyproject 管理

### 作用
- 启动本地 API 服务
- 承载 AI 调用编排
- 处理图谱写入与数据存储

---

## 四、开发目录与职责建议

推荐目录：

```text
project-root/
  src/              # React 前端
  src-tauri/        # Tauri 壳与配置
  backend/          # FastAPI 后端
  docs/             # 项目文档
  scripts/          # 启动、初始化、打包脚本
  data/             # 本地运行数据（可忽略入库）
```

### 子目录职责
- `src/`：页面与组件
- `src-tauri/`：桌面壳、sidecar 管理、打包配置
- `backend/`：服务逻辑、AI 编排、数据库访问
- `scripts/`：初始化数据库、健康检查、导出辅助脚本

---

## 五、本地服务启动架构

## 5.1 启动链路建议

开发与运行时建议采用：
- Tauri 启动前端
- Tauri sidecar 启动 FastAPI
- FastAPI 连接 Neo4j / LanceDB / SQLite
- 前端调用 `127.0.0.1:8000`

---

## 5.2 启动顺序建议

### 开发模式
1. 检查 Node / Python / Rust 环境
2. 启动 Neo4j
3. 启动 FastAPI
4. 启动 Tauri + React

### 发布模式
1. 用户打开桌面应用
2. Tauri 启动本地 sidecar
3. sidecar 做健康检查
4. 前端就绪

---

## 六、环境变量建议

建议统一使用 `.env` 管理后端环境变量。

### 建议变量
- `OPENAI_API_KEY`
- `OPENAI_MODEL_DEFAULT`
- `OPENAI_EMBED_MODEL`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `LANCEDB_PATH`
- `SQLITE_PATH`
- `OLLAMA_BASE_URL`
- `OLLAMA_ENABLED`
- `APP_ENV`
- `LOG_LEVEL`

### 说明
- 开发、测试、发布环境应分开配置
- 客户端不应直接暴露密钥逻辑到前端层

---

## 七、数据库初始化与迁移建议

## 7.1 SQLite 初始化

建议通过脚本自动创建：
- settings
- topics
- sessions
- ability_records
- practice_attempts
- review_items
- expression_assets
- friction_records
- deferred_nodes

## 7.2 Neo4j 初始化

建议通过初始化脚本创建：
- 唯一约束
- 索引
- 基础 Label 约定

## 7.3 LanceDB 初始化

建议启动时检查：
- 数据目录存在
- `concept_embeddings` 表存在
- `topic_embeddings` 表存在

---

## 八、本地数据目录建议

建议统一本地数据目录，避免多处散落。

### 目录建议
- `data/sqlite/`
- `data/lancedb/`
- `data/logs/`
- `data/exports/`
- `data/cache/`

### 原则
- 用户可定位
- 发布版可自动创建
- 日志、数据库、导出分目录

---

## 九、日志设计建议

## 9.1 日志分层

### 前端日志
- 页面切换错误
- 请求失败
- 关键状态异常

### 后端日志
- API 请求摘要
- AI 调用结果状态
- 图谱写入状态
- 数据库错误
- 会话完成结果

### 系统日志
- sidecar 启动/关闭
- 健康检查结果
- 环境依赖异常

---

## 9.2 日志级别建议
- `DEBUG`：开发调试
- `INFO`：常规业务日志
- `WARNING`：可恢复异常
- `ERROR`：接口失败或核心逻辑失败

## 9.3 日志注意事项
- 不要记录完整用户密钥
- 避免直接记录全部用户长文输入
- 练习作答日志建议可配置脱敏

---

## 十、健康检查与可观察性

## 10.1 启动时健康检查
建议在应用启动时检查：
- FastAPI 是否可访问
- SQLite 是否可读写
- Neo4j 是否连接成功
- LanceDB 是否可用
- 模型提供方是否可用
- Ollama（若启用）是否可用

## 10.2 前端健康提示建议
若健康检查失败，应明确提示：
- 哪个依赖不可用
- 当前是否可降级使用
- 用户可以做什么

---

## 十一、打包发布建议

## 11.1 打包目标
- macOS `.dmg`
- Windows `.exe` / 安装包
- Linux AppImage

## 11.2 打包前检查清单
- 前端构建通过
- 后端依赖锁定
- sidecar 路径正确
- 环境变量模板齐全
- 日志路径正常
- 本地数据库初始化脚本包含

## 11.3 发布包内容建议
- 主应用
- sidecar 后端
- 默认配置模板
- 必要初始化资源
- 用户说明文档（后续）

---

## 十二、Sidecar 管理建议

## 12.1 Sidecar 职责
- 启动 FastAPI 服务
- 监听退出信号
- 管理端口占用
- 可输出健康状态

## 12.2 启动失败处理
若 sidecar 启动失败，前端应：
- 阻止进入核心学习流程
- 显示明确错误信息
- 提供重试入口

## 12.3 退出时清理建议
- 结束未完成会话状态写入
- 关闭 sidecar
- 刷新本地缓存落盘

---

## 十三、开发运行脚本建议

建议提供脚本：
- `dev:frontend`
- `dev:backend`
- `dev:tauri`
- `dev:all`
- `init:db`
- `check:health`
- `build:desktop`
- `test:all`

### 示例职责
- `dev:all`：一键启动开发环境
- `init:db`：初始化 SQLite / Neo4j / LanceDB
- `check:health`：检查依赖是否就绪

---

## 十四、版本管理建议

## 14.1 前后端版本对齐
建议维护：
- app version
- api version
- schema version

## 14.2 数据库版本迁移
SQLite 与 Neo4j schema 变更时，应记录 migration 版本号与执行记录。

## 14.3 发布节奏建议
- 内部开发版
- 可测试 beta 版
- 稳定发布版

---

## 十五、故障排查指南建议

建议后续补充 FAQ / Troubleshooting 文档，至少覆盖：
- 应用打不开
- sidecar 启动失败
- Neo4j 无法连接
- 图谱加载失败
- AI 反馈一直失败
- 本地模型不可用
- 导出失败

---

## 十六、备份与恢复建议

## 16.1 本地数据备份
建议允许用户备份：
- SQLite 数据文件
- LanceDB 数据目录
- 导出资产目录

## 16.2 恢复策略
若应用重装，可通过导入本地数据目录恢复：
- Topic
- 表达资产
- 复习记录
- 设置

### 注意
Neo4j 若嵌入式部署复杂，可考虑通过导出图谱 JSON 做恢复辅助。

---

## 十七、发布运行风险与建议

## 17.1 风险一：用户本地环境差异
应尽量减少用户手工配置成本。

## 17.2 风险二：依赖多导致启动失败
MVP 应尽量减少强依赖数量，对 Ollama 等做可选化处理。

## 17.3 风险三：本地数据库损坏
应提供导出 / 备份路径，并减少异常退出导致的写损坏风险。

---

## 十八、开发团队协作建议

### 前端
主要关注页面、交互和本地状态。

### 后端
主要关注业务编排、AI 调用、数据库写入。

### AI / Prompt
主要关注结构化输出、练习反馈、诊断准确性。

### 测试
主要关注主流程、异常流和环境稳定性。

### 所有角色共同关注
- schema 一致性
- 版本一致性
- 本地环境可复现性

---

## 十九、MVP 部署建议

MVP 阶段建议采用最小可运行方案：
- Tauri 壳
- FastAPI sidecar
- SQLite 本地文件
- LanceDB 本地目录
- Neo4j 本地单实例
- 云端模型主路径
- Ollama 可选

目标不是极致自动化，而是：
- 研发团队可以稳定跑通
- 测试人员可以快速装起来
- 后续用户版可以逐步收敛依赖

---

## 二十、最终结论

AxonClone 的部署运维重点不是云端大规模运维，而是：
- 本地开发环境可复现
- 本地 sidecar 可管理
- 本地依赖可检查
- 本地数据可保存与恢复
- 打包发布流程稳定

因此，应以“桌面应用工程化”思路管理：
- 清晰目录
- 清晰脚本
- 清晰健康检查
- 清晰日志
- 清晰打包流程

只要把这套底座搭稳，AxonClone 的研发、联调、测试和后续发布都会顺很多。

