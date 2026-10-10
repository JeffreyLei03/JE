# Je 开发者指南与开发规范 (Agent Instructions)

Je 是一个面向终端的现代化自主 AI 编码助手框架。本项目致力于提供高内聚、低耦合、极度清晰的代码架构，兼顾终端交互体验与底层 Agent 引擎的可复用性。

---

## 架构核心原则 (Architecture Principles)

Je 严格遵循三层分层解耦架构，保证底层核心引擎与上层终端界面的完全独立：

```text
je_coding → je_agent
je_coding → je_ai → je_agent
```

```text
AgentHarness  = 可复用的通用 Agent 大脑引擎
CodingSession = 面向实际工程的编码助理环境
TUI / CLI     = 前端消费层（事件流驱动）
```

### 1. `je_ai`：统一模型流式层
- **职责**：抽象和适配各类 LLM 提供商（OpenAI、Anthropic、Ollama、DeepSeek、Hugging Face 等），将其流式协议统一转换为框架中立的类型化事件。
- **边界约束**：纯协议转换，不包含业务逻辑，依赖 je_agent 的供应商中立消息、工具及 Provider 契约，不依赖应用层状态。

### 2. `je_agent`：便携式通用 Agent 引擎
- **职责**：Agent 的“核心大脑”，包含消息管理（Messages）、类型化工具抽象（Tools）、事件流定义（Events）、执行主循环（Agent Loop）、状态调度（AgentHarness）以及基础会话存储。
- **边界约束**：**绝对不可**依赖 CLI（Typer）、终端渲染（Rich/Textual）、特定文件存储路径或本地配置加载。它是纯粹的、可脱离终端嵌入其他应用的可移植内核。

### 3. `je_coding`：终端智能助理环境与应用层
- **职责**：为开发者打造的终端编程助理全功能应用。提供交互式 TUI、无头 Print 模式、内置文件与命令操作工具、项目级上下文规范（`AGENTS.md`、`.je/` 资源）、自定义技能（Skills）、扩展机制（Extensions）以及磁盘会话管理。
- **边界约束**：作为前端和环境胶水层，消费 `je_agent` 发出的事件并驱动交互。

---

## 终端与界面架构 (UI Direction)

- 交互式 TUI 采用 Textual 构建，但必须严格置于适配器边界之后（Adapter Pattern）。
- Agent 核心引擎只负责触发并抛出类型化事件（Events），UI 层仅作为事件观察者（Event Consumer）进行订阅渲染。
- 永远不要让 Textual 或 Rich 成为核心 `je_agent` 的依赖。

---

## 项目路径与配置规范 (Filesystem Layout)

Je 规范化使用 `.je` 作为配置与资源目录：

- **用户级全局配置与会话**：存储于 `~/.je/`（支持通过 `JE_HOME` 环境变量自定义）。
  - `~/.je/sessions/`：历史会话持久化存储
  - `~/.je/skills/`：全局自定义技能
  - `~/.je/prompts/`：全局提示词模板
  - `~/.je/extensions/`：用户级扩展
- **项目级本地配置与上下文**：存储于当前工程根目录的 `.je/`。
  - `.je/skills/`：工程专属技能
  - `.je/SYSTEM.md`：工程专属系统提示词覆盖
  - `.je/APPEND_SYSTEM.md`：工程专属系统提示词追加

---

## 开发工作流与规范 (Development Workflow)

- **环境与依赖**：本项目统一使用 [`uv`](https://docs.astral.sh/uv/) 管理虚拟环境与依赖。
  - 运行测试：`uv run pytest`
  - 代码格式化与检查：`uv run ruff check .`
  - 类型检查：`uv run mypy`
  - 启动测试应用：`uv run je`
- **渐进式迭代**：每次迭代必须包含完整且语义明确的类型注解、测试用例与设计文档。
- **原子化提交 (Atomic Commits)**：遵循 Conventional Commits 规范（`feat:`、`fix:`、`refactor:`、`docs:`、`test:` 等），每个 commit 只做一件完整且清晰的事。
- **Python 编码标准**：
  - 目标版本为 Python 3.12+。
  - 核心消息、事件、配置均推荐使用强类型 `dataclass(slots=True)` 或 Pydantic 模型。
  - 显式管理异步（`async`/`await`）边界，避免阻塞操作混入异步循环。
  - 测试驱动：优先使用 Fake Provider 和 Fake Tools 编写高确定性的单元测试。

代码导入方向由 `je_agent` 定义消息、事件、工具与 `ModelProvider` 契约，`je_ai` 实现该契约，`je_coding` 组装两者。运行时则由 Harness 调用注入的 Provider。核心运行时不依赖 UI；`je_agent.session` 同时提供可选的本地 JSONL 存储实现。
