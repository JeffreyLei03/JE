---
title: "02 — 智能体主执行循环 (Agent Loop)"
---

Agent Loop 是轻量且高度可复用的核心执行引擎，负责协调上下文消息、工具执行与大模型流式响应，驱动整个 Agent 状态向前演进。

## 核心职责 (Responsibilities)

1. 接收当前的系统提示词（System Prompt）、会话记录（Transcript）、工具集合（Tools）与模型配置。
2. 请求大模型提供商开启流式响应。
3. 随着文本生成与工具调用到达，实时派发细粒度事件。
4. 汇总组装完整的 Assistant 响应消息。
5. 执行大模型请求调用的本地工具。
6. 将工具执行结果作为消息追加至上下文。
7. 重复上述流转，直至模型完成思考与操作、不再请求调用工具为止。

## 非核心职责边界 (Non-responsibilities)

Agent Loop 严禁感知 CLI 参数解析、Textual 终端组件、会话落盘存储位置或本地工程规则。这些属于上层 `je_coding` 的职责。

## 事件驱动优先 (Event-first Design)

执行过程中的每一个关键步骤均通过类型化事件（Events）对外暴露，使无头 Print 模式、Rich 控制台渲染与 Textual 全交互 TUI 能够无缝复用同一个执行核心。
