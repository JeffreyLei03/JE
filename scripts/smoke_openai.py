"""Opt-in OpenAI/DeepSeek smoke test; credentials are never written to the report."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import replace
from pathlib import Path
from time import monotonic
from uuid import uuid4

from je_agent.harness import AgentHarness, AgentHarnessConfig
from je_agent.messages import AssistantMessage, UserMessage
from je_agent.session import JsonlSessionStorage, MessageEntry
from je_ai.env import OpenAICompatibleConfig
from je_ai.openai_compatible import OpenAICompatibleProvider
from je_coding.provider_config import (
    OpenAICompatibleProviderConfig,
    openai_compatible_config_from_provider,
    provider_config_from_catalog_entry,
)
from je_coding.tools import create_coding_tools


def runtime_config(key: str, model: str, provider_name: str) -> OpenAICompatibleConfig:
    if provider_name == "deepseek":
        provider = provider_config_from_catalog_entry("deepseek")
        assert isinstance(provider, OpenAICompatibleProviderConfig)
        config = openai_compatible_config_from_provider(
            provider, credential_reader={"deepseek": key}, model=model, thinking_level="low"
        )
        return replace(config, max_tokens=4096, max_retries=0, timeout_seconds=45)
    return OpenAICompatibleConfig(
        api_key=key,
        base_url="https://api.openai.com/v1",
        max_tokens=512,
        max_retries=0,
        timeout_seconds=30,
        infer_api_from_model=False,
    )


async def stream_text(
    key: str, model: str, api: str, provider_name: str = "openai"
) -> dict[str, object]:
    provider = OpenAICompatibleProvider(replace(runtime_config(key, model, provider_name), api=api))
    try:
        events = [
            event
            async for event in provider.stream_response(
                model=model,
                system="Follow the user's instruction exactly.",
                messages=[UserMessage(content="Reply exactly JE_STREAM_OK.")],
                tools=[],
            )
        ]
        errors = [event for event in events if event.type == "error"]
        if errors:
            raise RuntimeError(errors[0].error.error_message)
        done = next(event for event in events if event.type == "done")
        assert done.message.text.strip() == "JE_STREAM_OK", "Unexpected stream result"
        deltas = sum(event.type == "text_delta" for event in events)
        assert deltas > 0, "Provider did not stream text deltas"
        return {
            "status": "passed",
            "text_deltas": deltas,
            "input_tokens": done.message.usage.input,
            "output_tokens": done.message.usage.output,
        }
    finally:
        await provider.aclose()


async def file_tools(
    key: str, model: str, directory: Path, provider_name: str = "openai"
) -> dict[str, object]:
    nonce = "JE_" + uuid4().hex
    (directory / "fixture.txt").write_text(nonce, encoding="utf-8")
    provider = OpenAICompatibleProvider(runtime_config(key, model, provider_name))
    harness = AgentHarness(
        AgentHarnessConfig(
            provider=provider,
            model=model,
            max_turns=5,
            system="Use only the supplied file tools. Follow all requested steps.",
            tools=[
                tool
                for tool in create_coding_tools(cwd=directory)
                if tool.name in {"read", "write", "edit"}
            ],
        )
    )
    try:
        events = [
            event
            async for event in harness.prompt(
                "Read fixture.txt with read. Write its exact contents to output.txt with write. "
                "Then edit output.txt to append _VERIFIED to that token. "
                "Finally reply with the exact complete contents of output.txt."
            )
        ]
        expected = nonce + "_VERIFIED"
        assert (directory / "output.txt").read_text(encoding="utf-8").strip() == expected
        final = harness.messages[-1]
        assert isinstance(final, AssistantMessage) and final.stop_reason != "error"
        assert expected in final.text, "Final answer did not use the tool result"
        calls = [event.tool_name for event in events if event.type == "tool_execution_start"]
        assert {"read", "write", "edit"}.issubset(calls), "Missing requested tool call"
        assert not any(event.is_error for event in events if event.type == "tool_execution_end")
        storage = JsonlSessionStorage(directory / "session.jsonl")
        entries = []
        parent = None
        for message in harness.messages:
            entry = MessageEntry(message=message, parent_id=parent)
            entries.append(entry)
            parent = entry.id
        await storage.append_batch(entries)
        restored = await storage.read_all()
        assert restored == entries, "Session round-trip changed transcript"
        resumed = AgentHarness(harness.config, messages=[entry.message for entry in entries])
        resumed_events = [
            event
            async for event in resumed.prompt(
                "Without using tools, repeat the exact verified token from our previous turn."
            )
        ]
        recovered = resumed.messages[-1]
        assert isinstance(recovered, AssistantMessage) and expected in recovered.text
        return {
            "status": "passed",
            "tools": calls,
            "session_entries": len(restored),
            "resume_events": len(resumed_events),
        }
    finally:
        await provider.aclose()


def cli_test(
    key: str, model: str, directory: Path, provider_name: str = "openai"
) -> dict[str, object]:
    env = os.environ.copy()
    env.update(
        {
            ("DEEPSEEK_API_KEY" if provider_name == "deepseek" else "OPENAI_API_KEY"): key,
            "JE_HOME": str(directory / "home"),
            "HOME": str(directory),
            "USERPROFILE": str(directory),
            "JE_OFFLINE": "1",
            "JE_NO_UPDATE_CHECK": "1",
        }
    )
    env.pop("TAU_HOME", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from je_coding.cli import app; app()",
            "--provider",
            provider_name,
            "--model",
            model,
            "--cwd",
            str(directory),
            "-p",
            "Reply exactly JE_CLI_OK. Do not use tools.",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).replace(key, "[REDACTED]")[-1000:])
    assert "JE_CLI_OK" in result.stdout, "CLI did not return the expected response"
    return {"status": "passed", "exit_code": result.returncode}


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("openai", "deepseek"), default="openai")
    parser.add_argument("--model")
    parser.add_argument("--key-stdin", action="store_true")
    parser.add_argument("--key-prompt", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    args.model = args.model or (
        "deepseek-v4-flash" if args.provider == "deepseek" else "gpt-4.1-mini"
    )
    key_env = "DEEPSEEK_API_KEY" if args.provider == "deepseek" else "OPENAI_API_KEY"
    print("Waiting for ephemeral API credential", flush=True)
    if args.key_prompt:
        key = getpass.getpass(f"{args.provider} API key (hidden): ").strip()
    elif args.key_stdin:
        key = sys.stdin.readline().strip()
    else:
        key = os.environ.get(key_env, "")
    if not key:
        parser.error(f"Set {key_env} or supply --key-stdin")
    report: dict[str, object] = {"provider": args.provider, "model": args.model, "tests": {}}
    tests = report["tests"]
    assert isinstance(tests, dict)
    with tempfile.TemporaryDirectory(
        prefix=f"je-{args.provider}-", dir=args.report.parent
    ) as temporary:
        directory = Path(temporary)
        cases: dict[str, Callable[[], Awaitable[dict[str, object]]]] = {
            "chat_completions_stream": lambda: stream_text(
                key, args.model, "openai-completions", args.provider
            ),
        }
        if args.provider == "openai":
            cases["responses_stream"] = lambda: stream_text(key, args.model, "openai-responses")
        cases["file_tools_and_session_resume"] = lambda: file_tools(
            key, args.model, directory, args.provider
        )
        cases["cli_print"] = lambda: asyncio.to_thread(
            cli_test, key, args.model, directory, args.provider
        )
        for name, run in cases.items():
            started = monotonic()
            try:
                outcome = await asyncio.wait_for(run(), timeout=120)
            except Exception as exc:
                outcome = {"status": "failed", "error": str(exc).replace(key, "[REDACTED]")[:1000]}
            outcome["seconds"] = round(monotonic() - started, 2)
            tests[name] = outcome
            print(json.dumps({name: outcome}, ensure_ascii=False), flush=True)
            args.report.write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            if outcome["status"] == "failed":
                break
    return (
        0
        if len(tests) == len(cases) and all(item["status"] == "passed" for item in tests.values())
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
