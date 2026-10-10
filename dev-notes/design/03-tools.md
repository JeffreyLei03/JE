---
title: "03 — 工具体系 (Tools)"
---

工具（Tools）允许智能体通过结构化调用检查和修改用户的工作区与操作系统环境。

Je 将工具的抽象与具体的前端界面解耦：
- `je_agent`：定义供应商中立的工具类型标准，并负责执行具体的工具调用。
- `je_coding`：提供具体的本地文件操作和 Shell 执行工具。
- 前端（CLI / TUI）：决定在会话中向 Agent 暴露哪些工具。

## 核心模型 (Core Model)

一个 `AgentTool` 包含：
- `name`：工具名称，例如 `read` 或 `bash`
- `description`：用户/模型可读的描述
- `label`：前端显示名称
- `parameters`：JSON Schema 入参定义（`input_schema` 是只读兼容属性）
- `execute_fn`：异步执行器，接收 `tool_call_id`、`arguments`、可选取消信号和 `on_update` 回调

执行完成后返回 `AgentToolResult`：
- `content`：文本或图片内容块列表
- `details`：供 UI 和日志使用的 JSON 元数据
- `added_tool_names` / `terminate`：可选运行时信息

成功与失败通过 `ToolExecutionEndEvent.is_error` 和 `ToolResultMessage.is_error` 表示，结果对象没有 `ok` 或 `error` 字段。执行器异常由循环转换为错误结果；通过 `on_update(AgentToolResult(...))` 主动报告的进度在工具完成前派发。

## 内置编码工具 (Built-in Coding Tools)

`je_coding` 提供了四大核心内置工具：

1. **`read` (文件读取)**：
   - 智能识别文本与常见图片（JPEG、PNG、GIF、WebP）。
   - 支持分页读取（`offset` 和 `limit`），单次输出超过 2,000 行或 50KB 时自动截断并给出续读提示。
2. **`write` (文件写入)**：
   - 完整创建或覆盖单个 UTF-8 文本文件。
   - 自动创建缺失的各级父目录。
   - 进程内同路径写操作自动串行化，防止并发写冲突。
3. **`edit` (精确局部编辑)**：
   - 对现有 UTF-8 文件应用精确文本块替换。
   - 严格要求原文本（`oldText`）在文件中唯一且精确匹配。
   - 具备原子回滚机制：若任一匹配校验失败，保持原文件完全不变。
   - 自动保留文件的换行符风格（CRLF/LF）与 UTF-8 BOM。
4. **`bash` (终端命令执行)**：
   - 在当前工作区执行 Shell 命令行。
   - 支持自定义超时控制（`timeout`）。
   - 合并 stdout 与 stderr，发生超长输出时截取尾部并保存完整日志至临时文件。
