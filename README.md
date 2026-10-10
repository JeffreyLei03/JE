# Je ⚡

> **An autonomous AI coding agent that lives in your terminal.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

Je is a lightweight, extensible terminal coding assistant. You type requests like *"explain this repo"*, *"add tests"*, or *"refactor this module"*; Je reads files, plans changes, edits code, executes shell commands, and preserves durable session histories while streaming everything in real time.

---

## 🏗 Architecture

Je is built on a clean three-layer architecture with strict separation of concerns:

```text
je_coding  →  je_agent  →  je_ai
```

- **`je_ai`**: LLM abstraction and streaming layer. Translates multiple model providers (Anthropic, OpenAI, OpenRouter, Ollama, Hugging Face, etc.) into provider-neutral event streams.
- **`je_agent`**: Core agent harness and event engine. Implements the portable agent loop, tool execution, session management, and state transitions without UI dependencies.
- **`je_coding`**: Coding-agent environment. Implements the terminal application: Textual interactive TUI, headless print mode (`je -p`), workspace context, project rules (`AGENTS.md`), skills, and session persistence.

```text
AgentHarness  = Reusable Brain
CodingSession = Coding-Agent Environment
TUI / CLI     = Frontend Consumers
```

---

## 🚀 Quickstart

### Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) (recommended)

### Installation & Run

Clone the repository and run with `uv`:

```bash
git clone https://github.com/JeffreyLei03/je.git
cd je
uv sync --dev
```

Launch the interactive terminal UI:

```bash
uv run je
```

Or run headlessly in one-shot print mode:

```bash
uv run je -p "Summarize the architecture of this project"
```

To install globally as an editable CLI tool:

```bash
uv tool install --editable .
je --help
```

---

## 🛠 Features

- **Interactive TUI & Headless CLI**: Modern Textual-powered terminal user interface and scriptable one-shot CLI mode.
- **Full Coding Toolset**: Built-in `read`, `write`, `edit`, and `bash` tools for deep repository interaction.
- **Durable Sessions**: JSONL session history saved under `~/.je/sessions/` with instant resume and session branching.
- **Rich Context Management**: Automatic loading of project rules (`AGENTS.md`, `.je/` resources), user skills, and intelligent context compaction.
- **Extensible Extensions & Skills**: Support for custom user extensions, prompt templates, and custom TUI themes (`je-dark`, `je-light`).
- **Multiple Providers**: Seamless integration with OpenAI, Anthropic, Ollama, OpenRouter, and custom OpenAI-compatible endpoints.

---

## 📦 Using Je as a Library

Because `je_agent` is decoupled from terminal UI libraries, you can embed the harness directly into your own applications:

```python
from je_agent import AgentHarness, AgentHarnessConfig

harness = AgentHarness(
    AgentHarnessConfig(
        provider=provider,
        model="gpt-4o",
        system="You are an autonomous software engineer.",
        tools=tools,
    )
)

async for event in harness.prompt("Explain this codebase"):
    print(event)
```

---

## 🧪 Testing & Verification

Run the full test suite with:

```bash
uv run pytest
uv run ruff check .
uv run mypy
```

---

## 📄 License & Acknowledgments

This project is licensed under the [MIT License](LICENSE).

**Acknowledgments**:
The architectural design of Je is inspired by and evolved from the Pi and Tau agent harness architectures.
