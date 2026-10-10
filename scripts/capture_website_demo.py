"""Capture the real Textual UI with a live DeepSeek model in an isolated fixture.

The API key is read without echo and never enters screenshots or metadata.
Run from the repository root: .venv/Scripts/python scripts/capture_website_demo.py
"""

from __future__ import annotations

import asyncio
import getpass
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

from smoke_openai import runtime_config

from je_agent.messages import AssistantMessage, ToolCall
from je_agent.session import JsonlSessionStorage
from je_ai.openai_compatible import OpenAICompatibleProvider
from je_coding.resources import TauResourcePaths
from je_coding.session import CodingSession, CodingSessionConfig
from je_coding.tui.app import JeTuiApp, PromptInput

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "website/static/images/demo"
WORKSPACE = ROOT.parent / "tmp/je-portfolio-demo"
MODEL = "deepseek-v4-flash"
PROMPT = (
    "Read greeting.py. Change greet to accept a name with default 'world' and return "
    "'Hello, <name>!'. Write test_greeting.py with assertions for greet() and greet('Ada'). "
    "Read both files to verify. Use read, edit and write tools. Reply with a short summary."
)


async def capture(key: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    home = WORKSPACE / ".je"
    os.environ["JE_HOME"] = str(home)
    os.environ["JE_NO_UPDATE_CHECK"] = "1"
    os.environ["JE_OFFLINE"] = "1"
    (WORKSPACE / "greeting.py").write_text('def greet():\n    return "Hello!"\n', encoding="utf-8")
    provider = OpenAICompatibleProvider(runtime_config(key, MODEL, "deepseek"))
    session = await CodingSession.load(
        CodingSessionConfig(
            provider=provider,
            model=MODEL,
            provider_name="deepseek",
            storage=JsonlSessionStorage(WORKSPACE / f"demo-{uuid4().hex}.jsonl"),
            cwd=WORKSPACE,
            resource_paths=TauResourcePaths(root=home, cwd=WORKSPACE, agents_root=None),
            allowed_tool_names=frozenset({"read", "edit", "write"}),
            extensions_enabled=False,
            skills_enabled=False,
            trust_default="always",
            thinking_level="low",
            system="You are Je, a concise coding assistant. Only edit the requested demo files.",
        )
    )
    app = JeTuiApp(session)
    try:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            prompt = app.query_one("#prompt", PromptInput)
            prompt.value = PROMPT
            await pilot.pause()
            app.save_screenshot("01-prompt.svg", path=str(OUTPUT))
            await pilot.press("enter")
            worker = app._prompt_worker
            if worker is not None:
                await asyncio.wait_for(worker.wait(), timeout=90)
            await pilot.pause()
            final = session.messages[-1]
            assert isinstance(final, AssistantMessage) and final.stop_reason != "error"
            assert (WORKSPACE / "test_greeting.py").exists()
            subprocess.run(
                [sys.executable, str(WORKSPACE / "test_greeting.py")],
                cwd=WORKSPACE,
                check=True,
                timeout=10,
                capture_output=True,
            )
            calls = [
                block.name
                for message in session.messages
                if isinstance(message, AssistantMessage)
                for block in message.content
                if isinstance(block, ToolCall)
            ]
            assert {"read", "edit", "write"}.issubset(calls), calls
            app.save_screenshot("02-result.svg", path=str(OUTPUT))
            await pilot.press("ctrl+o")
            await pilot.pause()
            app.save_screenshot("03-tools.svg", path=str(OUTPUT))
            metadata = {
                "captured_at": date.today().isoformat(),
                "provider": "DeepSeek",
                "model": MODEL,
                "renderer": "Textual App.save_screenshot",
                "environment": "headless real TUI, isolated demo workspace",
                "terminal_size": [120, 40],
                "prompt": PROMPT,
                "tools": calls,
                "screenshots": ["01-prompt.svg", "02-result.svg", "03-tools.svg"],
                "validation": "greet() and greet('Ada') assertions passed",
            }
            (OUTPUT / "capture.json").write_text(
                json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
            )
            print(f"Captured 3 real TUI frames; live tool calls: {calls}")
    finally:
        await session.aclose()
        await provider.aclose()


if __name__ == "__main__":
    asyncio.run(capture(getpass.getpass("DeepSeek API key (hidden): ")))
