# Je 开发设计笔记与架构日志 (Dev Notes)

这里是 **Je** 项目内部的开发日志、架构决策记录（ADR）与核心系统设计文档。
这些文档旨在帮助中文开发者与贡献者清晰理解系统的构建全貌与设计细节。

---

## 目录索引 (Contents)

- **`design/` — 核心系统高层设计文档**：
  - `00-roadmap.md` — 分阶段迭代路线图
  - `01-architecture.md` — 三层分层解耦架构设计
  - `02-agent-loop.md` — Agent 执行循环与状态机职责
  - `03-tools.md` — 内置编码工具体系设计
  - `04-sessions.md` — 会话树、分支及持久化机制
  - `05-core-types-and-events.md` — 供应商中立的类型与事件契约
  - `project-trust.md` — 工作区受信任机制设计
- **`architecture/` — 具体实现与演进笔记**：
  - 各阶段功能落地的详细笔记与演进记录（`phase-1` … `phase-24`）。
- **`adr/` — 架构决策记录 (Architecture Decision Records)**：
  - 核心选型考量与技术架构决策。
