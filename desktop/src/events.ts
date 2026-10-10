import type { Event, Message } from "./types.ts";
export interface Tool {
  id: string;
  name: string;
  args: Record<string, unknown>;
  output: string;
  status: "running" | "done" | "error";
}
export function updateTools(current: Tool[], event: Event): Tool[] {
  if (!event.toolCallId) return current;
  if (event.type === "tool_execution_start")
    return [
      ...current.filter((t) => t.id !== event.toolCallId),
      {
        id: event.toolCallId,
        name: event.toolName ?? "tool",
        args: event.args ?? {},
        output: "",
        status: "running",
      },
    ];
  if (!["tool_execution_update", "tool_execution_end"].includes(event.type))
    return current;
  const result = event.result ?? event.partialResult;
  return current.map((tool) =>
    tool.id === event.toolCallId
      ? {
          ...tool,
          output:
            result?.content?.map((b) => b.text ?? "").join("\n") ?? tool.output,
          status:
            event.type === "tool_execution_end"
              ? event.isError
                ? "error"
                : "done"
              : "running",
        }
      : tool,
  );
}
export function toolsFromMessages(messages: Message[]): Tool[] {
  const tools: Tool[] = [];
  for (const message of messages) {
    if (message.role === "assistant" && Array.isArray(message.content))
      for (const block of message.content) {
        if (block.type === "toolCall" && block.id)
          tools.push({
            id: block.id,
            name: block.name ?? "tool",
            args: block.arguments ?? {},
            output: "",
            status: "running",
          });
      }
    if (message.role === "toolResult") {
      const tool = tools.find((t) => t.id === message.toolCallId);
      if (tool) {
        tool.status = message.isError ? "error" : "done";
        tool.output =
          typeof message.content === "string"
            ? message.content
            : (message.content ?? []).map((b) => b.text ?? "").join("\n");
      }
    }
  }
  return tools;
}
