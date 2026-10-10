以下是三处目标的精准定位（相对路径均以 `d:/projects/je` 为基准）。

---

## 1. 工具调用生命周期 Hook（before_tool_call / after_tool_call）

### 类型定义
**文件：`src/je_agent/loop.py`**
```python
46  BeforeToolCall = Callable[[ToolCall], Awaitable[tuple[bool, str | None]]]
47  AfterToolCall = Callable[
48      [ToolCall, AgentToolResult, bool],
49      Awaitable[tuple[AgentToolResult, bool]],
50  ]
```
- `BeforeToolCall`：返回 `(blocked, block_reason)`。
- `AfterToolCall`：返回改写后的 `(result, is_error)`。

### 在 AgentLoop 中的触发调用点
**文件：`src/je_agent/loop.py`，函数 `_execute_tool_call`（定义于第 285 行）**
- before hook 触发：**第 302–303 行**
  ```python
  if before_tool_call is not None:
      blocked, block_reason = await before_tool_call(call)
  ```
- after hook 触发：**第 329–330 行**
  ```python
  if after_tool_call is not None:
      result, is_error = await after_tool_call(call, result, is_error)
  ```

调用链：
- `run_agent_loop` 的参数声明在第 67–68 行；主循环内对 `_execute_tool_call(...)` 的调用在 **第 159–166 行**（把 `before_tool_call`/`after_tool_call` 透传进去）。

### 配置装配点
**文件：`src/je_agent/harness.py`**
- 配置字段：第 47–48 行
- 注入 run_agent_loop：第 188–189 行

---

## 2. 终端命令超时熔断与取消级联

### 取消令牌协议定义
- 工具侧：**`src/je_agent/tools.py`**，`class ToolCancellationToken`，**第 15–18 行**（仅 `is_cancelled()`）。
- Provider 侧：**`src/je_agent/provider.py`**，`class CancellationToken`，**第 13–16 行**。
- 默认实现：**`src/je_agent/harness.py`**，`class SimpleCancellationToken`，**第 51 行**（`cancel()` 在第 55 行；Harness 持有当前信号在第 74 行，创建于第 165 行）。

### bash 工具执行与超时/取消实现
**文件：`src/je_coding/tools.py`，函数 `create_bash_tool_definition` 内的 `async def execute`（第 606 行起）**
- 前置取消检查：第 618–619 行
- POSIX 下 `start_new_session=True` 启动子进程：第 620–627 行
- 非 POSIX 回退：第 630–636 行
- 核心熔断/级联调用：**第 637–641 行**
  ```python
  output_bytes, _stderr, timed_out, cancelled = await _communicate_with_cancellation(
      process, timeout=timeout, signal=signal,
  )
  ```

### 底层执行器（真正的超时熔断与取消级联）
**文件：`src/je_coding/tools.py`**
- `async def _communicate_with_cancellation(...)`：**第 762 行**
  - 用 `asyncio.wait(..., timeout=timeout, FIRST_COMPLETED)` 同时监听 `process.communicate()` 与取消监视任务（第 771–779 行）
  - 超时或取消时调用 `_kill_process_tree(process)` 杀掉整个进程组（第 782 行）
  - 外层 `except asyncio.CancelledError` 同样触发 `_kill_process_tree` 并取消 communicate（第 793–798 行）
- `async def _wait_for_cancel(...)`：**第 805 行**（50ms 轮询 `signal.is_cancelled()`）
- `def _kill_process_tree(...)`：**第 1167 行**（POSIX 用 `os.killpg(process.pid, SIGKILL)` 杀进程组；Windows 回退 `process.kill()`）

---

## 3. 工作区信任机制（Project Trust）的鉴权判断入口函数

**文件：`src/je_coding/project_trust.py`**

### 核心鉴权入口
**`class ProjectTrustCoordinator`（第 483 行）→ `async def resolve(...)`（第 493 行）**
这是唯一的鉴权决策入口，按优先级判定 `trusted`：
1. override 强制（第 524–531 行）
2. 无受保护资源 → 直接信任（第 532–534 行）
3. 扩展 deciders（第 536–579 行，调用 `extension_deciders`）
4. 已保存记录 `store.nearest`（第 581–597 行）
5. 默认策略 `TrustDefault`（第 598–605 行）
6. 非交互 → 拒绝；交互 → `prompt(ProjectTrustRequest(...))` 询问用户（第 606–651 行）

返回 `(ProtectedResourceSummary, ProjectTrustResolution)`。

- 提交持久化：`ProjectTrustCoordinator.commit(...)`，第 634 行
- 路径规范化：`canonicalize_project_path(...)`，第 141 行
- 受保护资源探测：`class ProtectedResourceDetector`，第 170 行
- 信任存储：`class ProjectTrustStore`，第 284 行

### 上层调用入口（会话启动时触发鉴权）
**文件：`src/je_coding/session.py`，第 568–582 行**
```python
coordinator = config.project_trust_coordinator or ProjectTrustCoordinator(...)
summary, trust_resolution = await coordinator.resolve(
    config.cwd, override=..., default=..., interactive=...,
    prompt=..., extension_deciders=(extension_runtime.decide_project_trust,), ...
)
```
随后由 `resource_paths_with_project_trust(...)`（`src/je_coding/resources.py` 第 327 行）根据 `trusted` 结果过滤资源路径。

### 相关数据/API
- `ProjectTrustRequest`：`project_trust.py` 第 71 行
- `ProjectTrustResolution`：`project_trust.py` 第 87 行
- 扩展决策桥接：`src/je_coding/extensions/runtime.py`，`decide_project_trust(...)` 第 1173 行
- 扩展层只读视图：`src/je_coding/extensions/api.py`，`project_trusted` 第 977 行

---

### 汇总表

| 目标 | 文件 | 符号 | 行号 |
|---|---|---|---|
| Hook 类型 | `src/je_agent/loop.py` | `BeforeToolCall` / `AfterToolCall` | 46–50 |
| Hook 触发 | `src/je_agent/loop.py` | `_execute_tool_call` | before: 302–303；after: 329–330 |
| Hook 透传 | `src/je_agent/loop.py` | `run_agent_loop` | 67–68, 159–166 |
| Hook 装配 | `src/je_agent/harness.py` | `HarnessConfig` | 47–48, 188–189 |
| 取消令牌 | `src/je_agent/tools.py` / `provider.py` | `ToolCancellationToken` / `CancellationToken` | 15–18 / 13–16 |
| 超时熔断执行器 | `src/je_coding/tools.py` | `_communicate_with_cancellation` | 762–803 |
| 杀进程组 | `src/je_coding/tools.py` | `_kill_process_tree` | 1167–1181 |
| 取消轮询 | `src/je_coding/tools.py` | `_wait_for_cancel` | 805–807 |
| bash 执行入口 | `src/je_coding/tools.py` | `create_bash_tool_definition.execute` | 606–641 |
| 信任鉴权入口 | `src/je_coding/project_trust.py` | `ProjectTrustCoordinator.resolve` | 493–632 |
| 信任调用点 | `src/je_coding/session.py` | `CodingSession` 初始化 | 568–582 |
