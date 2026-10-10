"""JE Autonomous Agent - 3 Long-Horizon Engineering Tasks Runner.

Executes 3 complex long-horizon engineering tasks on JE (DeepSeek-V4-Pro):
Task 1: Full-Feature Engineering (ContextCompactor & Budget Management)
Task 2: Bug Reproduction, Root-Cause Diagnosis & Regression Fix (Cross-platform CRLF & Shell Shim)
Task 3: System Benchmarking & Performance Suite (AgentBenchmarkHarness)
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

LONG_HORIZON_TASKS = [
    {
        "id": "LH-1",
        "category": "特性开发与端到端交付 (Full-Feature Engineering)",
        "title": "实现会话上下文智能压缩与预算管理引擎 (ContextCompactor)",
        "prompt": (
            "【长程任务 1：端到端特性研发】\n"
            "在长周期编码会话中，随着工具执行输出累积，上下文 token 快速暴增，容易超出模型窗口或导致成本激增。\n"
            "请在当前代码库中完整设计并实现一套会话上下文智能压缩与预算管理引擎：\n"
            "1. 在 `src/je_coding/context_compactor.py` 中实现 `ContextCompactor` 模块：\n"
            "   - 支持根据预设的 Token 预算（max_tokens）动态评估历史消息树中不同节点的重要性权重（保留关键代码 diff 与最新用户意图，智能折叠或合并超长终端输出与连续工具结果）；\n"
            "   - 生成符合项目规范的压缩节点（与 `CompactionSummaryMessage` 或 `je_agent.session` 契约兼容），维持上下文因果链连贯；\n"
            "   - 支持三种策略级别：'aggressive'（激进压缩，优先控制成本）、'balanced'（平衡模式）、'conservative'（保守模式，优先保留详细上下文）；\n"
            "2. 在 `src/je_coding/session.py` 或相关入口中支持该压缩器的配置与调用机制；\n"
            "3. 编写完整的单元测试套件 `tests/test_context_compactor.py`（覆盖：空会话处理、预算充足无需压缩、超预算按策略压缩、摘要完整性与因果链保持）；\n"
            "4. 运行 `uv run pytest tests/test_context_compactor.py` 确保全部测试通过，并使用 `uv run ruff check` 确保代码规范。"
        ),
        "target_tests": ["tests/test_context_compactor.py"],
    },
    {
        "id": "LH-2",
        "category": "复杂缺陷诊断与生态修复 (Debugging & Defect Remediation)",
        "title": "跨平台文件换行符保持与 Windows Shell 容错修复",
        "prompt": (
            "【长程任务 2：跨平台缺陷诊断与修复】\n"
            "在上一轮评测中，我们在 Windows 环境下发现了两个真实的底层工程痛点：\n"
            "A. 在 `src/je_coding/tools.py` 中，`edit` 和 `write` 工具写回文件时若直接使用 `Path.write_text`，Python 在 Windows 上会隐式将 LF 换行符转换为 CRLF，破坏了开源代码库原本以 LF 为主的换行风格；\n"
            "B. `bash` 工具在 Windows 平台直接调用宿主系统 Shell 时，若智能体习惯性发出含 `| tail -n 20`、`| grep` 或 `cat` 的 Unix 管道命令，会导致 `'tail' is not recognized` 异常退出。\n"
            "请完成以下端到端修复：\n"
            "1. 修复 A：重构 `src/je_coding/tools.py` 中的写入机制，写入时必须探测并严格保持原文件的主导行尾（dominant line ending），以 `newline=''` 或二进制方式写入，杜绝 Windows 默认的 CRLF 污染；\n"
            "2. 修复 B：在 `bash` 工具执行逻辑中，增加针对 Windows 平台的智能容错机制（例如：当在 Windows 上检测到类似 `tail`、`grep` 等常见管道关键字且执行失败时，提供自愈提示或尝试以跨平台兼容的方式执行）；\n"
            "3. 编写针对性的回归测试 `tests/test_cross_platform_tool_fixes.py`，完整覆盖上述两项修复，证明 CRLF 不会被错误引入且 Windows 管道容错生效；\n"
            "4. 运行 `uv run pytest tests/test_cross_platform_tool_fixes.py` 并保证已有工具单测 `tests/test_coding_tools.py` 依然通过。"
        ),
        "target_tests": ["tests/test_cross_platform_tool_fixes.py", "tests/test_coding_tools.py"],
    },
    {
        "id": "LH-3",
        "category": "系统测试体系与自动化基准构建 (System Tooling & Performance Suite)",
        "title": "构建智能体端到端性能、延迟与 Token 开销分析基准套件 (AgentBenchmarkHarness)",
        "prompt": (
            "【长程任务 3：系统级工具与性能评测套件构建】\n"
            "为了持续监控大模型在 Agent 场景下的真实表现，需要一套自动化的性能与开销分析基准工具：\n"
            "1. 在 `src/je_agent/benchmark.py` 中实现 `AgentBenchmarkHarness` 性能基准测试框架：\n"
            "   - 能够基于 `je_ai` 的 `FakeProvider` 或真实模型提供商，自动化模拟多轮并发对话任务；\n"
            "   - 精确采集并统计核心指标：首字延迟（TTFT）、Token 吞吐率（TPS / Tokens per Second）、工具调用往返耗时（RTT）、总消耗 Tokens 与成本估算；\n"
            "   - 支持并发压测模式（基于 asyncio 并发调度），计算并输出 P50、P90、P99 延迟分位数与均值；\n"
            "   - 自动生成结构化的 JSON 统计数据与排版优雅的 Markdown 性能报告；\n"
            "2. 编写单元测试 `tests/test_agent_benchmark.py`，利用 `FakeProvider` 验证基准框架的数据采集准确性、并发安全与统计计算逻辑；\n"
            "3. 在 `scripts/run_perf_benchmark.py` 中提供一个可直接运行的 CLI 脚本，支持通过命令行参数运行压测并打印性能看板；\n"
            "4. 运行 `uv run pytest tests/test_agent_benchmark.py` 与 `uv run python scripts/run_perf_benchmark.py --mock` 验证整套工具正常工作。"
        ),
        "target_tests": ["tests/test_agent_benchmark.py"],
    },
]


def run_long_horizon_tasks():
    project_root = Path("d:/projects/JE")
    output_dir = project_root / "benchmark_output"
    output_dir.mkdir(exist_ok=True)
    results_file = output_dir / "long_horizon_results.json"

    print("=" * 70)
    print(">>> JE-Agent (DeepSeek-V4-Pro) 3 Long-Horizon Engineering Tasks")
    print(f"Working Directory: {project_root}")
    print(f"Total Tasks: {len(LONG_HORIZON_TASKS)}")
    print("=" * 70)

    results = []

    for index, task in enumerate(LONG_HORIZON_TASKS, 1):
        task_id = task["id"]
        category = task["category"]
        title = task["title"]
        prompt = task["prompt"]
        target_tests = task.get("target_tests", [])

        print(f"\n[{index}/{len(LONG_HORIZON_TASKS)}] Starting {task_id}: {title}...")
        print(f"Category: {category}")

        start_time = time.time()
        process = subprocess.Popen(
            ["uv", "run", "je", "-p", prompt],
            cwd=str(project_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        stdout, stderr = process.communicate()
        elapsed = time.time() - start_time

        success = process.returncode == 0
        status_str = "SUCCESS" if success else f"FAILED (code {process.returncode})"
        print(f"-> Agent Loop Finished in {elapsed:.2f}s | Status: {status_str} | Output: {len(stdout)} chars")

        # Independent verification of target tests if any
        test_verification_results = {}
        for test_path in target_tests:
            full_test_path = project_root / test_path
            if full_test_path.exists():
                test_proc = subprocess.run(
                    ["uv", "run", "pytest", "-v", test_path],
                    cwd=str(project_root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                test_verification_results[test_path] = {
                    "passed": test_proc.returncode == 0,
                    "returncode": test_proc.returncode,
                    "stdout": test_proc.stdout[-1000:] if test_proc.stdout else "",
                }
                print(f"   [Verification] {test_path} -> {'PASSED' if test_proc.returncode == 0 else 'FAILED'}")
            else:
                test_verification_results[test_path] = {
                    "passed": False,
                    "returncode": -1,
                    "error": "File does not exist",
                }
                print(f"   [Verification] {test_path} -> NOT FOUND")

        task_result = {
            "id": task_id,
            "category": category,
            "title": title,
            "prompt": prompt,
            "status": "success" if success else "failed",
            "return_code": process.returncode,
            "elapsed_seconds": round(elapsed, 2),
            "stdout": stdout,
            "stderr": stderr,
            "test_verifications": test_verification_results,
        }
        results.append(task_result)

        # Write intermediate result
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f"All 3 Long-Horizon Tasks Finished! Saved to: {results_file}")
    print("=" * 70)


if __name__ == "__main__":
    run_long_horizon_tasks()
