import test from "node:test";
import assert from "node:assert/strict";
import { updateTools, toolsFromMessages } from "../src/events.ts";
test("Pi camelCase tool events preserve independent tool identities and partial output", () => {
  let tools = updateTools([], {
    type: "tool_execution_start",
    toolCallId: "read-1",
    toolName: "read",
    args: { path: "a.py" },
  });
  tools = updateTools(tools, {
    type: "tool_execution_start",
    toolCallId: "write-1",
    toolName: "write",
  });
  tools = updateTools(tools, {
    type: "tool_execution_update",
    toolCallId: "read-1",
    partialResult: { content: [{ type: "text", text: "partial" }] },
  });
  assert.equal(tools[0].output, "partial");
  assert.equal(tools[1].output, "");
  tools = updateTools(tools, {
    type: "tool_execution_end",
    toolCallId: "read-1",
    result: { content: [{ type: "text", text: "complete" }] },
    isError: false,
  });
  assert.equal(tools[0].name, "read");
  assert.equal(tools[0].status, "done");
  assert.equal(tools[0].output, "complete");
  assert.equal(tools[1].status, "running");
});
test("resumed sessions reconstruct completed and failed tool records", () => {
  const tools = toolsFromMessages([
    {
      role: "assistant",
      content: [
        {
          type: "toolCall",
          id: "a",
          name: "read",
          arguments: { path: "missing" },
        },
      ],
    },
    {
      role: "toolResult",
      toolCallId: "a",
      toolName: "read",
      isError: true,
      content: [{ type: "text", text: "Not found" }],
    },
  ]);
  assert.equal(tools[0].status, "error");
  assert.equal(tools[0].output, "Not found");
});
