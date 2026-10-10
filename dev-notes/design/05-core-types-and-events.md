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

位于 `je_agent.tools`：
- `ToolCall`：模型发出的结构化工具调用请求
- `AgentTool`：工具元数据声明（名称、描述、JSON Schema、异步执行器）
- `AgentToolResult`：工具执行的标准结构化响应

## 事件流体系 (Events)

位于 `je_agent.events`，描述 Agent 生命周期中的所有实时进度：
- 周期事件：`agent_start` / `agent_end`、`turn_start` / `turn_end`
- 消息流：`message_start`、`message_delta`、`message_end`
- 深度思考：`thinking_delta`（捕获大模型思维链流式内容）
- 工具执行流：`tool_execution_start`、`tool_execution_update`、`tool_execution_end`
- 状态与异常：`queue_update`、`retry`、`error`

无头命令行（Print Mode）、JSON 流模式以及 Textual 交互式终端统一订阅消费此事件流。
