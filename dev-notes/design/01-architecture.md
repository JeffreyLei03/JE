---
title: "01 — 架构设计 (Architecture)"
---

Je 保持可复用的 Agent 核心引擎与具体编码应用场景、交互界面之间的清晰解耦。

## 分层设计 (Layers)

### 1. `je_ai` (大模型交互层)
负责具体大模型供应商的流式请求与响应交互。将不同供应商（OpenAI、Anthropic、Ollama、DeepSeek 等）的异构响应协议转换为 Je 统一的无状态、平台中立事件流。

### 2. `je_agent` (核心智能体大脑)
拥有便携式智能体引擎的核心能力：消息体系（Messages）、工具接口（Tools）、事件协议（Events）、执行循环（Agent Loop）、AgentHarness 调度器及会话存储基元。
**该包绝不引入** CLI、Rich、Textual 或任何应用级资源加载逻辑。

### 3. `je_coding` (编码应用与环境)
承载具体的终端编程助理应用程序：CLI 命令集合、内置编码工具（文件读写/编辑/Shell 执行）、工作区指令规范（`AGENTS.md`、`.je/` 资源）、技能（Skills）、提示词模板、磁盘持久化会话以及 UI 适配层。

## 依赖关系与数据流向

```text
je_coding → je_agent
je_coding → je_ai → je_agent
```

终端与 UI 层作为事件观察者消费核心发出的事件，核心层不直接执行 UI 渲染。

## 概念边界

```text
AgentHarness  = 通用可复用大脑
CodingSession = 编码场景环境与上下文
TUI / CLI     = 前端消费与展示形态
```

代码导入方向由 `je_agent` 定义消息、事件、工具与 `ModelProvider` 契约，`je_ai` 实现该契约，`je_coding` 组装两者。运行时则由 Harness 调用注入的 Provider。核心运行时不依赖 UI；`je_agent.session` 同时提供可选的本地 JSONL 存储实现。
