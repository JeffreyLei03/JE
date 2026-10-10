---
title: "05 — 核心类型与事件体系 (Core Types and Events)"
---

核心类型体系定义了跨越供应商层、Agent 引擎、会话及 UI 层流转的统一数据模型与契约。

## 设计目的

各个系统层级绝不直接暴露特定 LLM 供应商的原始响应对象，而是统一基于 Je 的类型化事件与消息模型进行交互。

## 消息体系 (Messages)

位于 `je_agent.messages`：
- `UserMessage`：记录用户输入
- `AssistantMessage`：记录助手生成内容及工具调用请求（ToolCall）
- `ToolResultMessage`：记录特定工具调用的执行返回结果
- `AgentMessage`：所有消息类型的联合类型（Union Type）

## 工具类型 (Tools)

`ToolCall` 定义在 `je_agent.messages`，并由 `je_agent.tools` 兼容导出：
- `ToolCall`：模型发出的结构化工具调用请求
- `AgentTool`：工具元数据声明（名称、描述、JSON Schema、异步执行器）
- `AgentToolResult`：工具执行的标准结构化响应

## 事件流体系 (Events)

位于 `je_agent.events`，描述 Agent 生命周期中的所有实时进度：
- 周期事件：`agent_start` / `agent_end`、`turn_start` / `turn_end`
- 消息流：`message_start`、`message_update`、`message_end`
- 增量内容：`message_update.assistant_message_event` 包含 `text_delta`、`thinking_delta` 或工具调用增量；思考内容仅限供应商实际返回的内容，不保证提供完整思维链
- 工具执行流：`tool_execution_start`、`tool_execution_update`、`tool_execution_end`
- 模型错误：通过消息中的 `stop_reason` / `error_message` 表达，没有顶层 `error` 事件

`je_coding.events` 扩展会话事件：`queue_update`、`agent_settled`、`auto_retry_start/end`、`compaction_start/end` 等。`AgentHarness` 与 `CodingSession` 的事件范围不同，消费者应按所用接口处理。

无头命令行（Print Mode）、JSON 流模式以及 Textual 交互式终端统一订阅消费此事件流。
