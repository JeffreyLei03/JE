我已经通读了三个包的核心源码、契约与设计文档。下面按你的三个问题给出深入分析，并在开头澄清一个文档与实际代码不一致的关键点。

---

# 0. 先澄清：真实的单向依赖方向

项目里存在两处描述不一致：

- `AGENTS.md`：`je_coding → je_ai → je_agent`
- 网站 `website/content/internals/architecture.md`：`je_coding → je_agent → je_ai`

**以源码为准，实际方向是 `je_coding → je_ai → je_agent`。** 我用 grep 验证过：

- `src/je_ai/*.py` 大量 `from je_agent.messages/tools/types/provider_events import ...`（例如 `je_ai/anthropic.py:11`、`je_ai/stream.py:7`、`je_ai/provider.py:3`）。
- `src/je_agent/*.py` **不导入** `je_ai`、`je_coding`，也不导入 `rich`/`textual`/`typer`（只有 `from __future__ import annotations` 这种巧合命中）。

这其实是正确的架构选择，符合**依赖倒置 / 端口-适配器**：

```text
        定义契约（端口）                实现契约（适配器）        组装+应用
je_agent ───────────────►  je_ai  ───────────────►  je_coding
   ▲                                                    │
   └────────────────────────────────────────────────────┘
              （je_coding 同时直接消费 je_agent）
```

`je_agent.provider.ModelProvider`、`je_agent.messages`、`je_agent.provider_events` 是**供应商中立的契约**，由内核拥有；`je_ai` 是这些契约的具体实现（OpenAI/Anthropic/Google/…），所以**实现依赖契约，而非核心依赖具体供应商**。网站那行图把箭头方向写反了，语义上想表达的只是“三层解耦”，但代码事实是 `je_ai → je_agent`。

---

# 1. 三层职责、边界与调用关系

## 1.1 `je_agent` — 可移植的 Agent 内核（契约拥有者）

**职责**：消息模型、类型化工具抽象、类型化事件流、执行主循环、有状态调度器、会话存储基元。

关键文件：
- `src/je_agent/messages.py`：`AgentMessage`（User/Assistant/ToolResult/Custom…）、`AssistantMessage` 的有序 content blocks（Text/Thinking/ToolCall）。
- `src/je_agent/tools.py`：`AgentTool`（name/description/schema/async executor）、`AgentToolResult`、`ToolExecutionMode`、更新回调。
- `src/je_agent/provider.py`：**只定义** `ModelProvider` 协议与 `CancellationToken`。
- `src/je_agent/provider_events.py`：供应商中立流事件（`AssistantStartEvent`/`TextDeltaEvent`/`ThinkingDeltaEvent`/`ToolCallDeltaEvent`/`AssistantDoneEvent`/`AssistantErrorEvent`…）。
- `src/je_agent/events.py`：核心 `AgentEvent` 判别联合（见第 2 节）。
- `src/je_agent/loop.py`：`run_agent_loop` 纯异步生成器。
- `src/je_agent/harness.py`：`AgentHarness` 有状态封装。
- `src/je_agent/session/`：只追加条目模型、JSONL 序列化、存储后端、重放/树遍历。
- `src/je_agent/tool_history.py`：provider 安全的工具历史修复。

**边界约束（硬性）**：不得依赖 CLI、Rich/Textual、`~/.je` 等资源路径、具体供应商。它是可脱离终端嵌入的内核。

## 1.2 `je_ai` — 统一的模型流式适配层

**职责**：把各家 API 的流式协议，统一转换为 `je_agent.provider_events` 的类型化事件；实现 `ModelProvider`。

关键文件：
- `src/je_ai/provider.py`：仅重导出 `je_agent` 的 `CancellationToken`/`ModelProvider`（契约来自内核，实现方不重新定义）。
- 各供应商适配器：`openai_compatible.py`、`anthropic.py`、`google.py`、`mistral.py`、`openai_codex.py`。
- `src/je_ai/stream.py`：`canonicalize_provider_stream`，把解析器内部的 `ProviderEvent`（含 `ProviderRetryEvent` 等）规范化为统一的 `AssistantMessageEvent`，并处理**内容块顺序**与**独立通道**（Chat Completions 的 text/thinking 独立频道）。
- `src/je_ai/fake.py`：确定性 Fake Provider，供高确定性单测。
- `src/je_ai/retry.py`、`http*.py`、`model_limits.py`、`model_catalog.py` 等传输/重试/限额细节。

**边界约束**：纯协议转换，不含业务逻辑，不感知应用状态；可复用 `je_agent` 的消息/工具/契约，但核心不反向依赖它。

## 1.3 `je_coding` — 终端编码助手应用层（组装根 / Composition Root）

**职责**：CLI、Textual TUI、无头 print 模式、内置工具、技能/提示词/`AGENTS.md` 资源、扩展机制、provider 配置与动态注册、磁盘会话管理与索引、渲染、RPC 等。

关键文件：
- `src/je_coding/session.py`：`CodingSession`（约 5260 行），把 `je_agent.AgentHarness` 组装进编码场景，并实现 **push 持久化**、分支导航、压缩、模型切换等。
- `src/je_coding/session_manager.py`：会话索引/归档（`index.jsonl`）——**可重建的缓存，不是事实来源**。
- `src/je_coding/provider_runtime.py`、`provider_config.py`、`extensions/`：构造具体 `je_ai` Provider，动态源/层/generation 感知。
- `src/je_coding/tools.py`、`skills.py`、`system_prompt.py`、`context.py`。
- `src/je_coding/tui/`、`rendering/`：事件消费者，只渲染事件。
- `src/je_coding/events.py`：`CodingSessionEvent = AgentEvent | SessionOwnEvent`（扩展内核事件，增加 `agent_settled`、`entry_appended`、`compaction_*`、`auto_retry_*` 等）。

**边界约束**：只消费内核事件、驱动交互；绝不把 Textual/Rich 依赖下沉到 `je_agent`。

## 1.4 单向依赖与"事件作为唯一契约"

```text
je_coding ──► je_ai ──► je_agent      （契约倒置：实现依赖端口）
    │                        ▲
    └────────────────────────┘        （直接消费 AgentEvent / 会话基元）
```

- 内核定义 `ModelProvider` 端口 → `je_ai` 实现 → 运行时由 Harness 注入。
- 内核抛出 `AgentEvent` 事件流 → `je_coding` 的 TUI/print/RPC 订阅渲染。
- TUI 仅"发送 prompt、消费事件流、绘制"，因此同一内核可驱动 print 模式、Textual、或自建前端。

---

# 2. ReAct 主循环：基于 `AsyncIterator[AgentEvent]` 的细粒度事件流

## 2.1 两层的分工

- `run_agent_loop(...) -> AsyncGenerator[AgentEvent, None]`：**纯函数式、无状态**的循环（`je_agent/loop.py`）。
- `AgentHarness`：**有状态**封装（消息列表、steering/follow-up 队列、监听器、取消 token、修复），把循环包成可反复调用的 `prompt()`/`continue_()`，返回 `AsyncIterator[AgentEvent]`。

## 2.2 事件模型（判别联合）

`je_agent/events.py` 用 Pydantic 判别联合表达生命周期：

```python
type AgentEvent = Annotated[
    AgentStartEvent | AgentEndEvent
    | TurnStartEvent | TurnEndEvent
    | MessageStartEvent | MessageUpdateEvent | MessageEndEvent
    | ToolExecutionStartEvent | ToolExecutionUpdateEvent | ToolExecutionEndEvent,
    Field(discriminator="type"),
]
```

- `AgentStart/End`：一次运行。
- `TurnStart/End`：一次助手响应 + 其工具结果。
- `MessageStart/Update/End`：一条消息生命周期；流式细节**嵌套**在 `MessageUpdateEvent.assistant_message_event`（即 `AssistantMessageEvent`）。
- `ToolExecutionStart/Update/End`：工具执行过程及部分结果。

**最终 `AssistantMessage` 是权威**：它把 text/thinking/tool_calls 持久化为有序内容块；嵌套 update 仅用于响应式渲染。这保证了"渲染用增量、落盘/回放用终态"。

## 2.3 循环结构（`run_agent_loop`）

```text
yield AgentStart
yield TurnStart
（prelude_messages：修复产生的合成消息，先发 start/end）
（prompts：新用户消息，发 start/end）

while True:                                  # 外层：follow-up
    while has_more_tools or pending:         # 内层：ReAct 迭代
        if not first_turn: yield TurnStart
        （注入 steering 消息 → start/end）
        （max_turns 检查 → error 消息）
        async for event in _assistant_events(...):   # 助手流
            yield event
            （捕获 MessageEndEvent 的 AssistantMessage）
        append assistant
        if stop_reason in {error, aborted}: yield TurnEnd; yield AgentEnd; return
        for call in calls:                   # 工具执行
            async with aclosing(_execute_tool_call(...)) as execution:
                async for event in execution:
                    yield event
                    （捕获 ToolResultMessage 并 append）
        yield TurnEnd(message=assistant, tool_results=...)
        turn += 1
        pending = get_steering_messages()
    follow_ups = get_follow_up_messages()
    if follow_ups: pending = follow_ups; continue
    break
yield AgentEnd(messages=new_messages)
```

这就是 ReAct 循环本质：**模型流式输出 → 若含 tool_calls 则执行 → 结果回填消息 → 再次请求模型**，直到无工具调用。

## 2.4 助手子生成器：把 Provider 流映射为内核事件

`_assistant_events`（`loop.py`）把 `provider.stream_response(...) -> AsyncIterator[AssistantMessageEvent]` 映射为 `AgentEvent`：

- 手动 `await anext(source_iterator)` 而不是 `async for`，用于**逐次累计等待时间**（`monotonic_ns`）计算 `ResponseTiming`（TTFT / total）。
- `AssistantStartEvent` → `MessageStartEvent`
- `AssistantDoneEvent` / `AssistantErrorEvent` → `MessageEndEvent`（附带 timing）
- 其余 delta（Text/Thinking/ToolCall）→ `MessageUpdateEvent`

**关键异步细节**：创建生成器时不会执行任何代码；只有消费者 `async for` 拉动才会推进。因此**背压天然存在**，前端渲染慢会自动反压到 provider 流。

## 2.5 工具执行：回调式更新 → 异步生成器

`_execute_tool_call` 产出 `ToolExecutionStart → (Update*) → End`，再接 `MessageStart/End(ToolResultMessage)`，保证落盘时工具结果与调用相邻。

难点是工具 API 用**同步回调** `on_update(partial)` 上报部分结果，而循环需要 `yield`。`_run_tool` 用一个 `asyncio.Queue` + `asyncio.create_task` 桥接：

```python
def on_update(partial):
    if accepting: updates.put_nowait(partial.model_copy(deep=True))

async def execute():
    try: updates.put_nowait((await tool.execute(...), False))
    except CancelledError: raise
    except Exception as exc: updates.put_nowait((_error_result(str(exc)), True))  # 隔离边界
    finally: accepting = False; updates.put_nowait(None)

task = asyncio.create_task(execute())
while (update := await updates.get()) is not None: yield update
await task
```

工具异常被收敛成 `is_error=True` 的结果，作为**隔离边界**，绝不让单个工具异常炸掉整个循环。`finally` 里 `accepting=False` 阻止尾部回调、必要时 `task.cancel()`，并用 `suppress(CancelledError)` 等待清理。

## 2.6 取消、修复与生成器终结

- 每次运行创建 `SimpleCancellationToken`；`provider.stream_response(..., signal=...)` 与工具都检查 `signal.is_cancelled()`。
- 用 `contextlib.aclosing(...)` 包裹子生成器，确保异常/取消时 `aclose()` 被调用，触发其 `finally`，不泄漏任务。
- **工具历史修复**：`_append_interrupted_tool_results` 在运行开始时补齐"有 tool_call 却无 tool_result"的悬挂调用；取消的 `finally` 中再次补齐，并通过监听器推送给订阅者。`_provider_context` 过滤掉空的 error/aborted 助手消息（不可重放的失败），再经 `repair_tool_history` 修复发送给 provider 的上下文，保证 provider 不会因 `tool_use` 缺少 `tool_result` 而 400。

## 2.7 Harness 的 push 通知与事件消费解耦

`AgentHarness._run` 的核心：

```python
async for event in stream:
    await self._notify(event)   # 先推给所有订阅者（持久化、扩展）
    yield event                 # 再交给消费者（TUI/print）
```

这是一个**极其重要的设计**：持久化是**订阅者（push）**而非**消费者（pull）**。TUI 中断时会取消消费 worker，若持久化依赖消费，尾部的合成修复消息会丢失（这正是 `dev-notes/push-based-persistence.md` 记录的 bug）。改为订阅后：

- `message_end` 是持久化边界，写入发生在事件到达前端**之前**。
- 运行开始/取消时的修复通过 `_notify` 推送，UI 拆解也无法丢失。
- 监听器异常被 `suppress(Exception)` 包裹，但**取消不被吞掉**（`CancelledError` 会继续传播），避免清理掩盖取消。

---

# 3. 树状持久化：`SessionTree` / `JsonlSessionStorage` 原理与可恢复性

## 3.1 数据模型：只追加的条目树

`je_agent/session/entries.py`：

```python
class BaseSessionEntry(BaseModel):
    id: str = Field(default_factory=new_entry_id)      # uuid4 hex
    parent_id: str | None = None                       # 树的边
    timestamp: float = ...

type SessionEntry = Annotated[MessageEntry | CustomMessageEntry | ModelChangeEntry
    | ThinkingLevelChangeEntry | CompactionEntry | BranchSummaryEntry
    | LabelEntry | LeafEntry | SessionInfoEntry | CustomEntry,
    Field(discriminator="type")]
```

- 每个条目通过 `parent_id` 形成**树**；`message` 是唯一进入模型上下文的条目，其余是元数据/控制条目。
- 没有"原地修改"：模型切换、thinking 级别、压缩、打标、分支摘要都是**追加新条目**。
- 序列化：一行一个 JSON 对象（JSONL），用 `TypeAdapter(SessionEntry)` + `dump_json(exclude_none=True)`。

## 3.2 树遍历与分支重建

`session/tree.py`：

- `entries_by_id`：建索引，**重复 id 直接报错**（`SessionTreeError`）。
- `path_to_entry(entries, leaf_id)`：从 leaf 沿 `parent_id` 回溯到根，**检测环**（`seen` 集合）与**缺失父节点**，再 reverse 成 root→leaf 路径。

`session/memory.py::SessionState.from_entries(entries, leaf_id=...)`：

- 默认 leaf = 文件序最后一个非 `leaf` 条目；显式传 `leaf_id` 用于**内存中的树导航**。
- **只重放 active root→leaf 路径**，兄弟分支不会泄漏进当前 transcript。
- 沿途处理：`message`/`custom_message` 收集消息；`model_change`/`thinking_level_change` 记录当前设置；`label` 全局解析（分支外的书签也可见）；`compaction` 通过 `_apply_compaction` 把旧消息替换为摘要（兼容旧的 `replaces_entry_ids` 与新的 `first_kept_entry_id` 两种语义）；`branch_summary` 转成用户上下文摘要消息。
- 输出 `SessionState`，含 `messages`、`context_entry_ids`、`active_leaf_id` 等。

`LeafEntry` 仅用于反序列化旧格式，**永不作为 tip 选择器**（`_last_non_leaf_id` 跳过它），避免历史 leaf 指针干扰。

## 3.3 `JsonlSessionStorage`：只追加 + 原子批提交

`session/storage.py` 的 `SessionStorage` 协议规定 `append` / `append_batch` / `read_all`，并声明 **`append_batch` 是持久化事务边界：整批可见或旧 transcript 不变**。

### 单条追加（真正的字节级只追加）

```python
with self._locked(exclusive=True):
    self._remove_incomplete_temp()
    with self.path.open("ab") as file:      # 追加二进制
        file.write(entry_to_json_line(entry).encode())
        file.flush(); os.fsync(file.fileno())
```

每条记录写完即 `fsync`，崩溃最多丢失最后一条未 fsync 的记录，不会产生半行（整行一次 write + fsync，且独占锁串行化）。

### 批量追加（逻辑只追加，物理原子替换）

```python
with self._locked(exclusive=True):
    self._remove_incomplete_temp()
    previous = self.path.read_bytes() if exists else b""
    data = previous + encoded
    self._atomic_replace(data)
```

`_atomic_replace`：同目录 `mkstemp` → 写临时文件 → `fsync` → `os.replace`（原子）→ **目录 fsync**（持久化目录项）。因此批提交是"读旧 + 拼接 + 原子替换"，**内容只增不减**，但物理上是整文件重写。

### 为什么只追加仍然安全

- `previous + encoded` 保证内容集合单调增长；历史条目对象不被修改。
- 替换是原子的：读者要么看到旧文件、要么看到新文件，绝不会看到半截。
- 目录 fsync 保证 rename 本身在断电后可恢复。

### 跨进程并发

`_locked(exclusive=...)` 使用独立锁文件 `.{name}.lock`：
- POSIX：`fcntl.flock` 的 `LOCK_SH`（读）/`LOCK_EX`（写）。
- Windows：`msvcrt.locking`（无共享锁，读也退化为独占锁），提供跨进程串行化。
- 锁文件独立于 transcript，避免锁与数据耦合。

> 注意：读路径上若存在稳定标记 `.{name}.tmp`，会升级为独占锁清理它——这个标记**永远不是提交文件**。

## 3.4 故障可恢复性

| 故障场景 | 恢复机制 |
|---|---|
| 追加时进程崩溃 | 最后一次 `fsync` 前丢失末尾记录；不会产生半行（整行 write+fsync+独占锁） |
| 批替换中途崩溃 | 提交是 `os.replace` 原子操作；旧文件或新文件二选一。遗留的 `.tmp` / `.{name}.*.tmp` 在下次读/写时被清理 |
| 目录项未落盘 | `_fsync_directory` 对目录 fsync |
| 多进程并发写 | 独立锁文件 + 每次写前重读当前文件 |
| 格式演进 | `jsonl.py::_migrate_session_entry` 在**读取边界**迁移旧 v1 记录（label 无 target、custom_type 大小写、旧 message 形状、tool→toolResult 等），磁盘原文件不改 |
| 索引损坏 | `SessionManager.index.jsonl` 是可重建缓存；索引失败只记诊断，不影响 transcript（`_record_session_index_diagnostic`） |

## 3.5 应用层 push 持久化：幂等与补偿

`je_coding/session.py` 把持久化实现为 Harness **订阅者**：

```python
def _attach_persistence_listener(self):
    self._persistence_unsubscribe = self._harness.subscribe(self._persist_on_message_end)

async def _persist_on_message_end(self, event):
    if isinstance(event, MessageEndEvent):
        self._ended_message_ids.add(id(event.message))
        await self._persist_message(event.message)
```

`_persist_message` 的幂等设计：

1. **稳定 entry id**：第一次为消息生成 `_PendingMessageWrite(message, entry)` 并缓存；重试复用同一 `entry.id`。
2. **只有重试才读盘**：`durable_ids` 仅在 `is_retry` 时读取，检查 `pending.entry.id` 是否已落盘，避免重复追加。首次尝试的新 id 不可能已在磁盘，省掉读。
3. 追加成功后更新 `_last_parent_id`（新条目以当前 tip 为父），刷新 `SessionState`，记录已持久化消息 id。
4. `_reconcile_run_persistence` 在 `prompt()`/`continue_()` 的 `finally` 里，按**消息身份**（`id(message)`）而非计数，重试 `message_end` 已触发但写失败的持久化。用计数会因"循环在 append 到 transcript 之前就发出 message_end"而双写。
5. `_flush_pending_message_writes` 在下一个 prompt / 压缩 / 上下文相关终端命令前冲刷残留写。

这解决了"取消后尾部合成消息丢失"的经典 bug：合成修复在 Harness 内部生成并通过 `_notify` 推送，消费被撤销也不会丢。

## 3.6 分支的"内存导航 vs 持久变更"

`branch_to_entry`（`session.py`）：

- 先 `_flush_pending_message_writes`。
- `summarize=True`：对被放弃路径上的消息调用模型生成摘要，**追加** `BranchSummaryEntry`（这是唯一写），它成为新的持久 tip。
- 否则**纯内存导航**：只改 `_last_parent_id` 与 `SessionState.from_entries(..., leaf_id=target)`，并用 `harness.replace_messages(...)` 替换运行时消息；**不写盘**。
- 若 `harness.replace_messages(...)` 被历史修复分支取代（`_persist_active_tool_history_repairs` 非 None），则走修复路径：把 provider 安全的修复分支作为**新分支追加**，保留原始条目不动，并附诊断。

因此：普通导航不落盘（退出后按文件序最后一个非 leaf 条目恢复），下一次消息或状态变更以所选目标为父追加，从而**使分支持久化**——完美体现"移动即结构变更，而非编辑 transcript"。

## 3.7 工具历史修复：会话层的故障可恢复性

`tool_history.py` 的 `repair_tool_history` 与 `CodingSession._persist_active_tool_history_repairs` 处理旧会话中 `assistant(tool_use)` 后缺 `tool_result` 的悬挂调用：

- 在加载/`/tree` 时校验活跃历史，发现异常则**追加**一个 provider 安全的修复分支 + 持久诊断，**原条目保留**。
- 循环侧 `_provider_context` 在最终请求前也做内存修复作为兜底。
- 这是"只追加 + 可恢复"哲学在**协议有效性**维度的延伸：宁可追加修复分支，也不重写历史。

---

# 总结

1. **三层与依赖**：真实方向是 `je_coding → je_ai → je_agent`（契约倒置）。`je_agent` 拥有消息/工具/provider 协议/事件/会话基元；`je_ai` 实现 `ModelProvider`；`je_coding` 组装并消费事件。内核零 UI 依赖。
2. **ReAct 循环**：`run_agent_loop` 是纯异步生成器，用 `AgentStart/TurnStart/Message*/ToolExecution*/TurnEnd/AgentEnd` 细粒度事件驱动；流式细节嵌套在 `MessageUpdateEvent`；`_assistant_events` 桥接 provider 流并计时，`_run_tool` 用队列桥接回调与生成器，`aclosing`/取消 token/工具历史修复保证终结与可恢复；Harness 通过 `subscribe` 让持久化成为 push 订阅者而非 pull 消费者。
3. **树状持久化**：`parent_id` 构树、`path_to_entry` 沿根路径重放、`leaf_id` 支持分支；`JsonlSessionStorage` 单条追加 `O_APPEND`+`fsync`，批量用同目录临时文件 + `os.replace` + 目录 fsync 原子提交；独立锁文件跨进程串行化，读时清理遗留临时文件；读取边界做格式迁移；`CodingSession` 用稳定 entry id 实现幂等重试与 finally 补偿，分支导航默认仅内存、写操作才追加，从而在**只追加语义**下实现分支、压缩、摘要与故障可恢复。
