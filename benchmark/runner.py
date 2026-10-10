"""Prepare isolated fixtures, run real JE sessions, and produce scored reports."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import shutil
import statistics
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
MODEL = "deepseek-flash"


def tasks() -> list[dict[str, Any]]:
    return json.loads((ROOT / "tasks.json").read_text(encoding="utf-8"))


def save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def completion_percent(groups: dict[str, dict[str, int]]) -> float:
    return (
        100
        * sum(group["total"] > 0 and group["passed"] == group["total"] for group in groups.values())
        / 4
    )


def prepare() -> None:
    for task in tasks():
        for actor in ("je", "codex"):
            directory = ROOT / "runs" / actor / task["id"]
            if directory.exists():
                raise FileExistsError(
                    f"Existing run: {directory}; archive it before preparing again"
                )
            directory.mkdir(parents=True)
            (directory / "TASK.md").write_text(task["spec"] + "\n", encoding="utf-8")
            starter = task.get("starter", "# Implement the public TASK.md specification here.\n")
            (directory / "solution.py").write_text(starter, encoding="utf-8")
            (directory / "AGENTS.md").write_text(
                "Only modify files in this task workspace. Standard library only. "
                "Implement solution.py and write test_solution.py with unittest smoke tests. "
                "Do not access parent folders or other benchmark files.\n",
                encoding="utf-8",
            )
            if actor == "codex":
                shutil.copy2(
                    ROOT / "baseline" / task["id"] / "solution.py", directory / "solution.py"
                )
    print("Prepared 10 tasks x 2 actors", flush=True)


async def run_je(key: str) -> None:
    import httpx

    from je_agent.messages import AssistantMessage, sum_usage
    from je_agent.session import JsonlSessionStorage
    from je_ai.env import OpenAICompatibleConfig
    from je_ai.openai_compatible import OpenAICompatibleProvider
    from je_coding.resources import TauResourcePaths
    from je_coding.session import CodingSession, CodingSessionConfig

    # Keep credentials out of child tool environments.
    for name in list(os.environ):
        if "API_KEY" in name or name in {"OPENAI_TOKEN", "ANTHROPIC_AUTH_TOKEN"}:
            os.environ.pop(name, None)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://api.deepseek.com/models", headers={"Authorization": f"Bearer {key}"}
        )
        response.raise_for_status()
        available = sorted(item["id"] for item in response.json()["data"])
    save(
        ROOT / "reports" / "model-verification.json",
        {
            "requested_version": "DeepSeek-V4.1-Flash",
            "api_model": MODEL,
            "available_models": available,
            "verified_at": datetime.now(UTC).isoformat(),
            "source": "https://deepseek.com/news/deepseek-v4-1-flash/",
        },
    )
    if MODEL not in available:
        raise RuntimeError(f"Requested model unavailable; API returned {available}")
    print(f"Verified model: {MODEL}", flush=True)
    for task in tasks():
        identifier = task["id"]
        directory = ROOT / "runs" / "je" / identifier
        meta_path = ROOT / "runs" / "metadata" / f"{identifier}.json"
        if meta_path.exists():
            print(f"Skipping recorded task {identifier}", flush=True)
            continue
        home = ROOT / "runs" / "homes" / identifier
        home.mkdir(parents=True, exist_ok=True)
        os.environ.update(JE_HOME=str(home), JE_OFFLINE="1", JE_NO_UPDATE_CHECK="1")
        provider = OpenAICompatibleProvider(
            OpenAICompatibleConfig(
                api_key=key,
                base_url="https://api.deepseek.com",
                max_tokens=8192,
                timeout_seconds=120,
                max_retries=0,
                provider_name="deepseek",
                thinking_format="deepseek",
                reasoning_effort="low",
                infer_api_from_model=False,
            )
        )
        session = await CodingSession.load(
            CodingSessionConfig(
                provider=provider,
                model=MODEL,
                provider_name="deepseek",
                cwd=directory,
                storage=JsonlSessionStorage(home / "session.jsonl"),
                resource_paths=TauResourcePaths(root=home, cwd=directory, agents_root=None),
                extensions_enabled=False,
                skills_enabled=False,
                trust_default="always",
                thinking_level="low",
                auto_compact_enabled=False,
                allowed_tool_names=frozenset({"read", "write", "edit", "bash"}),
            )
        )
        start = perf_counter()
        tool_calls = 0
        tool_errors = 0
        turns = 0
        status = "completed"
        error = None
        print(f"START {identifier}", flush=True)
        try:
            async with asyncio.timeout(480):
                prompt = (
                    f"{task['spec']}\n\nImplement this task in solution.py in the current "
                    "workspace. Read the starter first. Write test_solution.py with unittest "
                    "tests and run them. Use read/write/edit/bash tools, not just a text answer. "
                    "Do not access parent directories or other benchmark files. "
                    "Standard library only. Windows command shell: avoid Unix shell syntax. "
                    f'Run Python using the quoted executable "{sys.executable}". '
                    "End with a brief implementation and verification summary."
                )
                async for event in session.prompt(prompt):
                    if event.type == "turn_start":
                        turns += 1
                        if turns > 24:
                            raise RuntimeError("Model turn limit reached")
                    elif event.type == "tool_execution_start":
                        tool_calls += 1
                    elif event.type == "tool_execution_end" and event.is_error:
                        tool_errors += 1
        except Exception as exc:
            status = "error"
            error = f"{type(exc).__name__}: {exc}".replace(key, "[REDACTED]")[:500]
        finally:
            assistants = [m for m in session.messages if isinstance(m, AssistantMessage)]
            usage = sum_usage(m.usage for m in assistants)
            if any(m.stop_reason == "error" for m in assistants):
                status = "provider_error"
                error = next(m.error_message for m in assistants if m.stop_reason == "error")
                error = (error or "Unknown provider error").replace(key, "[REDACTED]")[:500]
            await session.aclose()
            await provider.aclose()
        metadata = {
            "id": identifier,
            "model": MODEL,
            "status": status,
            "error": error,
            "wall_seconds": round(perf_counter() - start, 3),
            "turns": turns,
            "tool_calls": tool_calls,
            "tool_errors": tool_errors,
            "requests": len(assistants),
            "usage": usage.model_dump(),
            "response_models": sorted({m.model for m in assistants if m.model}),
        }
        save(meta_path, metadata)
        print(
            f"END {identifier}: {status}, {metadata['wall_seconds']}s, {tool_calls} tools",
            flush=True,
        )


def score() -> None:
    rows = []
    process_env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    for task in tasks():
        for actor in ("codex", "je"):
            workspace = ROOT / "runs" / actor / task["id"]
            if not workspace.exists():
                workspace = (
                    ROOT / "baseline" / task["id"]
                    if actor == "codex"
                    else ROOT / "submissions" / "je" / task["id"]
                )
            measurements = []
            for _ in range(3):
                functional = None
                try:
                    base_command = [
                        sys.executable,
                        str(ROOT / "evaluator.py"),
                        task["id"],
                        str(workspace),
                    ]
                    functional_result = subprocess.run(
                        [*base_command, "--functional"],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        timeout=45,
                        cwd=workspace,
                        env=process_env,
                    )
                    if functional_result.returncode:
                        raise RuntimeError(functional_result.stderr[-500:])
                    functional = json.loads(functional_result.stdout)
                    result = subprocess.run(
                        base_command,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        timeout=45,
                        cwd=workspace,
                        env=process_env,
                    )
                    if result.returncode:
                        raise RuntimeError(result.stderr[-500:])
                    measurements.append(json.loads(result.stdout))
                except Exception as exc:
                    if functional is not None:
                        functional["runtime_ms"] = None
                        functional["failures"].append(f"Performance run: {type(exc).__name__}")
                        measurements.append(functional)
                    else:
                        measurements.append(
                            {
                                "passed": 0,
                                "total": 1,
                                "groups": {},
                                "failures": [str(exc)[:300]],
                                "runtime_ms": None,
                            }
                        )
            first = min(measurements, key=lambda item: item["passed"] / item["total"])
            all_correct = all(m["passed"] == m["total"] for m in measurements)
            times = [m["runtime_ms"] for m in measurements if m["runtime_ms"] is not None]
            runtime = statistics.median(times) if len(times) == 3 else None
            completion = min(completion_percent(item["groups"]) for item in measurements)
            row = {
                "id": task["id"],
                "title": task["title"],
                "actor": actor,
                "completion": completion,
                "accuracy": round(100 * min(m["passed"] / m["total"] for m in measurements), 2),
                "performance": 100
                if all_correct and runtime is not None and runtime <= 2000
                else 0,
                "runtime_ms": runtime,
                "checks": first,
                "measurement_runtime_ms": times,
            }
            if actor == "je":
                path = ROOT / "runs" / "metadata" / f"{task['id']}.json"
                if not path.exists():
                    path = ROOT / "submissions" / "metadata" / f"{task['id']}.json"
                row["execution"] = json.loads(path.read_text()) if path.exists() else None
            rows.append(row)
    write_report(rows)


def write_report(rows: list[dict[str, Any]]) -> None:
    summary = {
        actor: {
            metric: round(statistics.mean(r[metric] for r in rows if r["actor"] == actor), 2)
            for metric in ("completion", "accuracy", "performance")
        }
        for actor in ("codex", "je")
    }
    git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip()
    save(
        ROOT / "reports" / "results.json",
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "je_git_sha": git_sha,
            "python": sys.version,
            "model": MODEL,
            "summary": summary,
            "tasks": rows,
        },
    )
    lines = [
        "# JE 与 Codex 编码任务实测",
        "",
        f"JE 源码提交：`{git_sha}`。",
        "",
        "每题一次编码运行、三次外部验证/计时。性能预算每题 2000 ms，正确性全通过才得分。",
        "",
        "| 执行者 | 完成度 | 准确率 | 性能达标率 |",
        "|---|---:|---:|---:|",
    ]
    for actor, values in summary.items():
        lines.append(
            f"| {actor} | {values['completion']}% | {values['accuracy']}% | "
            f"{values['performance']}% |"
        )
    lines += [
        "",
        "| 任务 | 执行者 | 完成度 | 准确率 | 性能 | 代码耗时 ms | JE执行秒 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        elapsed = (row.get("execution") or {}).get("wall_seconds", "N/A")
        runtime = f"{row['runtime_ms']:.3f}" if row["runtime_ms"] is not None else "N/A"
        lines.append(
            f"| {row['title']} | {row['actor']} | {row['completion']} | "
            f"{row['accuracy']} | {row['performance']} | {runtime} | {elapsed} |"
        )
    lines += ["", "## 验证失败", ""]
    for row in rows:
        if row["checks"]["failures"]:
            lines.append(f"- {row['actor']} / {row['id']}: " + "; ".join(row["checks"]["failures"]))
    execution = [row["execution"] for row in rows if row.get("execution")]
    seconds = sum(item["wall_seconds"] for item in execution)
    requests = sum(item["requests"] for item in execution)
    calls = sum(item["tool_calls"] for item in execution)
    tokens = sum(item["usage"]["totalTokens"] for item in execution)
    passed = sum(row["checks"]["passed"] for row in rows if row["actor"] == "je")
    total = sum(row["checks"]["total"] for row in rows if row["actor"] == "je")
    lines += [
        "",
        "## 运行统计",
        "",
        f"JE 总执行耗时 {seconds:.3f} 秒，{requests} 次请求、{calls} 次工具调用、"
        f"{tokens} reported tokens（含缓存）。实际通过 {passed}/{total} 个检查；"
        "表格准确率为题目等权平均。",
        "账单金额不可观测；Usage.cost 的 0 是未配置价格的默认值，不代表免费。",
    ]
    lines += [
        "",
        "## 解释范围",
        "",
        "Codex 基线由当前助手亲自实现，且助手知道规格与验证器，存在作者优势。",
        "Codex 在验证后改进了 DAG 查询并修复 ZIP 原始路径检查；JE 为首轮运行结果，未修补答案。",
        "没有把 Codex 的推理时间/token 伪装成可观测数据。JE 的完整请求/token/工具统计见 JSON。",
        "这不是盲测排名；单次小样本适合诊断 JE 工作流。没有修补生产 JE 源码来适应测试。",
    ]
    (ROOT / "reports" / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "je", "score"])
    parser.add_argument("--key-stdin", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command == "score":
        score()
    else:
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            if args.key_stdin:
                print("Awaiting credential on private stdin", flush=True)
                key = sys.stdin.readline().strip()
            else:
                key = getpass.getpass("DeepSeek API key (hidden): ")
        asyncio.run(run_je(key))


if __name__ == "__main__":
    main()
