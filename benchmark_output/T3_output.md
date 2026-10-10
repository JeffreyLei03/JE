完成了。实现位于 `src/je_agent/rate_limit.py`，配套测试在 `tests/test_rate_limit.py`。

## 设计要点

**复合双闸门**：一次放行必须同时通过两道闸门
- **滑动日志（Sliding Log）**：`deque[(timestamp, tokens)]` 精确记录，任意 `window_seconds` 内放行总量 ≤ `burst_capacity`，杜绝固定窗口的边界双倍突发；用缓存的 `_used` 做 O(1) 增量维护。
- **令牌桶（Token Bucket）**：容量 `ceil(limit * burst_ratio)`，补充速率 `limit / window_seconds`，提供突发平滑。

**关键参数语义**
- `limit` 基准配额；`window_seconds` 窗口秒数；`burst_ratio ≥ 1.0` 动态突发容忍度
- `burst_capacity = ceil(limit * burst_ratio)`，初始桶为满（允许冷启动突发）

**并发无死锁**
- 全部状态变更在 `asyncio.Condition` 保护下串行化
- 等待者按“最早可放行时刻”`asyncio.wait_for(condition.wait(), wait)` 精确休眠，非轮询忙等；超时/唤醒后循环重评估
- 成功放行后 `notify_all()`，避免其他等待者依赖失效假设继续休眠
- 等待时间取两闸门较大值（安全下界，不会乐观提前放行），并用 `_MIN_WAIT_SECONDS` 防浮点零等待忙等

**边界与异常**
- 构造参数校验（类型、正数、有限值、`burst_ratio ≥ 1`）
- `tokens ≤ 0` 或 `> burst_capacity`（永远无法满足）抛 `ValueError`；`timeout` 负数/NaN/Inf 抛错
- `timeout=0` 只做一次即时尝试并返回 `False`；超时返回 `False` 且不消耗任何令牌
- `asyncio.CancelledError` 原样传播不吞信号

**可观测性**：`snapshot()` 返回 `RateLimitSnapshot`（含 `window_headroom` / `bucket_headroom`）。

## 验证结果
- `ruff check src tests` ✅
- `ruff format --check` ✅
- `uv run mypy`（strict，125 files）✅
- `uv run pytest tests/test_rate_limit.py` → **12 passed**
- 全量测试 2069 passed，另有 2 个**与本次改动无关的** Windows 环境失败：`test_coding_tools.py` 的 bash 子进程取消、`test_tui_app.py` 的 model picker 取消（均为既有/环境性 flaky，我的改动只新增文件，不可能影响它们）。

另外提醒：`scripts/benchmark_runner.py` 存在 31 处既有 ruff 报错（未在 `src`/`tests` 范围内，我未改动）。
