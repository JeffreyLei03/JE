以下分析基于 JE 现有实现（`src/je_agent/tool_history.py`、调用点 `src/je_agent/loop.py:_provider_context` 与 `src/je_coding/session.py:_tool_history_repair_plan`），并附带一段我已在本地验证可运行、且幂等的独立演示代码。

---

## 1. 协议约束：缺失 ToolResult 为何是致命断链

JE 把消息抽象为供应商中立模型，再由 `je_ai` 适配到各协议。这两大协议的约束是**硬性的、结构性的**，不是建议。

### OpenAI（Chat Completions / Responses）
- assistant 消息携带 `tool_calls: [{id, type, function:{name, arguments}}]`，每个 `id` 唯一。
- 每个 `tool_call` 都必须由紧随其后的 `{"role":"tool","tool_call_id":<id>,"content":...}` 应答。
- 校验规则：**assistant 带 tool_calls 的那条消息之后，必须紧跟一组 tool 消息，覆盖其中每一个 id**。若 `call-2` 无应答，服务端直接返回 400，类似：
  > `An assistant message with 'tool_calls' must be followed by tool messages responding to each 'tool_call_id'. The following tool_call_ids did not have response messages: call-2`
- Responses API 同理：`function_call` 必须配对 `function_call_output`（`call_id` 对应），否则报 `No tool output found for function call ...`。

### Anthropic（Messages API）
- assistant content block 里是 `tool_use`（带 `id`），下一个 user 轮必须是 `tool_result`（带 `tool_use_id`）。
- 校验规则：**每个 `tool_use` 必须在紧接着的下一条 user 消息里有一个对应 `tool_result`**。缺一个就 400：
  > `tool_use ids were found without tool_result blocks immediately after: call-2. Each tool_use block must have a corresponding tool_result block in the next message.`
- 注意 Anthropic 的顺序语义比 OpenAI 更严：tool_result **只能**出现在紧邻的 user 轮，不能夹杂普通文本后再补。

### 后果（为什么必须修而不能不管）
1. **下一次请求直接 400/422 失败**：整个 ReAct 循环在下一轮就崩，重试也只是重复提交同样的坏历史 → 死循环或会话终止。
2. **隐性语义污染**：若某中间层"容错"地丢弃了 assistant 的 `tool_use`，模型会看到一个"要读 b.txt 却从未读"的空洞，于是**幻觉出结果**或**重复发起同一调用**，破坏 ReAct 的因果闭环。
3. **响应/思考签名与缓存失效**：Anthropic 的 thinking 块带 `signature`，与其 `tool_use` 强绑定；粗暴删 assistant 轮会连带丢掉推理链。同时 KV/前缀缓存因消息数组变化而失效，成本上升。
4. **孤儿结果同样非法**：只留 `call-1` 的结果、删掉 assistant 轮，会得到"没有前置 tool_call 的 tool 消息"，OpenAI 同样拒绝（`messages with role 'tool' must be a response to a preceding message with 'tool_calls'`）。

**结论**：唯一安全且不破坏因果语义的修复，是为每个缺失的调用**合成一条错误占位 `ToolResult`**（`is_error=True`），而不是删除调用或伪造成功结果。JE 正是这么做的。

---

## 2. JE 的标准状态机修复算法

JE 的 `repair_tool_history` 本质是一个**两阶段确定性状态机 + 规范化重建**。可形式化如下：

### 状态定义
- `GROUND`：当前没有未闭合的工具轮。
- `AWAIT_RESULTS(pending: 有序 map[id → ToolCall], filled: map[id → ToolResult])`：有一个 assistant 工具轮正在等待结果。

### 转移规则（流式视角）
| 当前状态 | 输入消息 | 动作 / 次态 |
|---|---|---|
| `GROUND` | `User`/`Assistant(无tool_calls)` | 原样保留，保持 `GROUND` |
| `GROUND` | `Assistant` 含 tool_calls | 保留 assistant，进入 `AWAIT_RESULTS`（pending 按 call 出现顺序） |
| `AWAIT_RESULTS` | `ToolResult`，id 在 pending 且未填 | 记录 `filled[id]`；若 pending 全部填满 → 按 call 顺序 flush 结果 → `GROUND` |
| `AWAIT_RESULTS` | `ToolResult`，id 不在 pending | **孤儿结果**：丢弃（参数不可重建），计数 `dropped_orphans` |
| `AWAIT_RESULTS` | `ToolResult`，id 已填 | **重复结果**：保留真实结果、优先于合成占位；计数 `dropped_duplicates` |
| `AWAIT_RESULTS` | 任意其它消息 | **闭轮**：为每个未填 pending 合成 `is_error` 占位（按 call 顺序插入到 assistant 之后），再处理该消息，回到 `GROUND` |
| EOF | — | 同"闭轮"处理 |

### 关键工程细节（这些是 JE 实现里踩过的坑）
1. **按位置而非仅按 id 配对**：相同 id 可能在多轮重复出现。JE 先"就近预留"已经合法的相邻配对（`id` 相同且位置正好在 assistant 之后），避免早轮调用抢走晚轮的合法结果。
2. **结果重排**：结果必须紧贴其 assistant 轮并**按 tool_calls 顺序**排列（Anthropic 要求紧邻；并行调用顺序一致性对模型更友好）。原历史里乱序/夹带其它消息的结果会被移到正确位置，计数 `reordered`。
3. **合成内容固定且可识别**：`"Tool call interrupted by user"`、`is_error=True`。因为可识别，才能实现规则 4。
4. **优先真实结果**：若同一 id 既有合成占位又有真实结果，用真实结果替换占位（保证重放历史修正后不残留假错误）。
5. **孤儿不臆造调用**：没有 tool_call 的结果直接丢弃——因为无法安全反推 `name/arguments`。
6. **幂等**：修复后再跑一次必须 `changed=False`（否则会在持久化时无限产生新分支）。JE 在写入会话树时把这次修复作为 `tau.session-history-repair` 的 `CustomEntry` 分支落盘，并记录 `synthesizedResults / droppedOrphanResults / droppedDuplicateResults / reorderedResults` 诊断计数。

调用时机：`je_agent/loop.py` 的 `_provider_context()` 在**每次真正发给 Provider 之前**对可重放历史做修复（同时剔除空失败的 error/aborted assistant 轮），保证落盘历史与发给模型的历史解耦；`je_coding/session.py` 则在会话层面把修复结果持久化。

---

## 3. Python 实现：检测并插入合成错误占位

下面代码与 JE 语义一致，可直接运行。我用你描述的场景（`call-1` 成功、`call-2` 因中断丢失结果）验证了输出，且验证了幂等性。

```python
"""确定性工具历史修复状态机（JE 语义的精简独立实现）。"""
from __future__ import annotations

from dataclasses import dataclass, field

INTERRUPTED = "Tool call interrupted: result was never recorded (host interrupt/crash)."


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class Assistant:
    tool_calls: list[ToolCall] = field(default_factory=list)
    text: str = ""


@dataclass(slots=True)
class ToolResult:
    tool_call_id: str
    tool_name: str
    content: str
    is_error: bool = False


@dataclass(slots=True)
class User:
    content: str


Message = User | Assistant | ToolResult


@dataclass(slots=True)
class RepairReport:
    synthesized: int = 0
    dropped_orphans: int = 0
    dropped_duplicates: int = 0
    reordered: int = 0
    changed: bool = False


def repair_tool_history(messages: list[Message]) -> tuple[list[Message], RepairReport]:
    report = RepairReport()

    # 索引每个调用，用 (assistant_index, offset) 作为稳定身份。
    occurrences: list[tuple[tuple[int, int], ToolCall, int]] = []
    for i, message in enumerate(messages):
        if isinstance(message, Assistant):
            for offset, call in enumerate(message.tool_calls, start=1):
                occurrences.append(((i, offset), call, i + offset))

    results_by_id: dict[str, list[tuple[int, ToolResult]]] = {}
    for i, message in enumerate(messages):
        if isinstance(message, ToolResult):
            results_by_id.setdefault(message.tool_call_id, []).append((i, message))

    # ── 选择阶段：每个调用有且仅有一个结果 ──
    selected: dict[tuple[int, int], tuple[int | None, ToolResult]] = {}
    used: set[int] = set()

    # 1) 先就近预留已经合法的相邻配对（保护重复 id 的多轮场景）。
    for occurrence, call, expected in occurrences:
        if expected < len(messages):
            candidate = messages[expected]
            if (
                isinstance(candidate, ToolResult)
                and candidate.tool_call_id == call.id
                and expected not in used
            ):
                selected[occurrence] = (expected, candidate)
                used.add(expected)

    # 2) 复用剩余真实结果；否则合成错误占位。
    for occurrence, call, _ in occurrences:
        if occurrence in selected:
            continue
        candidates = [c for c in results_by_id.get(call.id, []) if c[0] not in used]
        after = [c for c in candidates if c[0] > occurrence[0]]
        pool = after or candidates
        if pool:
            choice = next((c for c in pool if not _is_synthetic(c[1])), pool[0])
            selected[occurrence] = choice
            used.add(choice[0])
            continue
        selected[occurrence] = (
            None,
            ToolResult(call.id, call.name, INTERRUPTED, is_error=True),
        )
        report.synthesized += 1

    # ── 重建阶段：assistant 原地保留，其结果按调用顺序紧跟其后 ──
    repaired: list[Message] = []
    for i, message in enumerate(messages):
        if isinstance(message, ToolResult):
            continue  # 结果一律由 selected 重新注入，避免乱序/孤儿
        repaired.append(message)
        if not isinstance(message, Assistant):
            continue
        for offset, _ in enumerate(message.tool_calls, start=1):
            position, result = selected[(i, offset)]
            repaired.append(result)
            if position is not None and position != i + offset:
                report.reordered += 1

    # ── 诊断计数 ──
    call_ids = {call.id for _, call, _ in occurrences}
    for positions in results_by_id.values():
        for position, result in positions:
            if position in used:
                continue
            if result.tool_call_id in call_ids:
                report.dropped_duplicates += 1
            else:
                report.dropped_orphans += 1

    report.changed = repaired != messages
    return repaired, report


def _is_synthetic(result: ToolResult) -> bool:
    return result.is_error and result.content == INTERRUPTED


if __name__ == "__main__":
    history: list[Message] = [
        User("Please read a.txt and b.txt"),
        Assistant(
            tool_calls=[
                ToolCall("call-1", "read", {"path": "a.txt"}),
                ToolCall("call-2", "read", {"path": "b.txt"}),
            ]
        ),
        ToolResult("call-1", "read", "file a contents"),  # call-2 的结果在中断中丢失
    ]

    fixed, report = repair_tool_history(history)
    for message in fixed:
        print(message)
    print(report)

    fixed2, report2 = repair_tool_history(fixed)
    assert fixed2 == fixed and report2.changed is False  # 幂等
    print("idempotent OK")
```

实测输出：

```
User(content='Please read a.txt and b.txt')
Assistant(tool_calls=[ToolCall(id='call-1', ... a.txt), ToolCall(id='call-2', ... b.txt)], text='')
ToolResult(tool_call_id='call-1', tool_name='read', content='file a contents', is_error=False)
ToolResult(tool_call_id='call-2', tool_name='read', content='Tool call interrupted: result was never recorded (host interrupt/crash).', is_error=True)
RepairReport(synthesized=1, dropped_orphans=0, dropped_duplicates=0, reordered=0, changed=True)
idempotent OK
```

`call-2` 被合成为 `is_error=True` 的 ToolResult，紧跟在 assistant 之后、`call-1` 结果之后，顺序与 tool_calls 一致 —— 这正是 OpenAI 的 `role:"tool"` 序列与 Anthropic 的 `tool_result` 块所要求的合法形态，从而让下一轮推理可以继续进行，同时让模型明确知道该调用"失败了"，而不是幻觉出一个假结果。

---

### 三点补充（落地时容易忽略）
- **合成文本必须是固定、可识别的常量**：规则 4 的"真实结果替换占位"依赖它；否则重复修复会把真实结果误判为占位。
- **修复发生在 provider 边界，不能只改内存**：JE 在 `_provider_context` 做发送前修复，同时在 `je_coding` 用 `tau.session-history-repair` 分支持久化，避免每次重放都重算、以及落盘历史与发送历史分叉。
- **修复必须幂等**：`changed=False` 是安全落盘的前提，也是可以放心放到每次请求前的关键。
