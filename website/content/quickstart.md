---
title: Quickstart
description: Install Je, connect a model, and run your first coding session.
type: doc
---

This page takes you from nothing to your first Je session. It should take a few
minutes.

## 1. Install Je

Je is a Python tool requiring Python 3.12 or newer. Its installer uses
[`uv`](https://docs.astral.sh/uv/) to create an isolated environment and installs
`uv` first when it is not already available.

On macOS or Linux, run:

```bash
curl -LsSf https://raw.githubusercontent.com/JeffreyLei03/JE/main/website/static/install.sh | sh
```

On Windows, run in PowerShell:

```powershell
irm https://raw.githubusercontent.com/JeffreyLei03/JE/main/website/static/install.ps1 | iex
```

The installer announces before installing `uv`, never uses `sudo`, verifies the
installed `je` command, and tells you if you need to restart your shell for a
`PATH` update. To review code before executing it, download and inspect
[`install.sh`](/install.sh) or [`install.ps1`](/install.ps1) first.

Check it worked:

```bash
je --version
```

> [!TIP] Already have a package manager?
> Install Je directly with `uv tool install git+https://github.com/JeffreyLei03/JE.git`, `pipx install git+https://github.com/JeffreyLei03/JE.git`, or
> `python -m pip install git+https://github.com/JeffreyLei03/JE.git`.

### Upgrade Je

The installer currently uses this repository as a Git source. Git is required.
To update that installation, run:

```bash
uv tool install --force git+https://github.com/JeffreyLei03/JE.git
```

For an editable checkout, pull changes and reinstall with
`uv tool install --editable --force .`. `je update` supports published PyPI
installations and intentionally refuses to replace a direct-source installation.

## 2. Connect a model

Je needs an AI model to talk to. A **provider** is the service that hosts the
model (OpenAI, Anthropic, …). Start Je and use `/login` to connect one:

```bash
je
```

Then run one of these inside Je:

```text
/login              # choose a provider
/login openai       # save an OpenAI API key
/login openai-codex # authenticate a Codex/ChatGPT subscription
```

Je ships with built-in entries for OpenAI, Anthropic, OpenAI Codex,
OpenRouter, and Hugging Face. See [Providers & models](/guides/providers-and-models/)
for switching models or adding a custom/local OpenAI-compatible endpoint.

## 3. Start a session

Run Je from inside the project you want to work on:

```bash
cd my-project
je
```

This opens the interactive terminal UI. Type a request and press **Enter**:

```text
explain what this project does
```

Je streams its response, and when it needs to, it reads files and runs commands
to answer you. Try something that changes code:

```text
add a docstring to every function in src/utils.py
```

You'll see each tool call (read, edit, bash) as it happens.

> [!TIP] Useful first keys
> **Enter** submits · **Esc** cancels the current run · **Ctrl+K** opens the
> command palette · **Ctrl+D** quits. Full list in
> [Keyboard shortcuts](/reference/keybindings/).

## 4. Come back later

Je saves every session. List them:

```bash
je sessions
```

Resume the most recent one for this directory, or pick from a list:

```bash
je --session <session-id>
```

…or open the picker inside the TUI with `/resume`. See
[Sessions](/guides/sessions/) for resuming, branching, and exporting.

## One-shot mode

Don't need the UI? Run a single prompt and get the result on stdout — handy for
scripts and pipes:

```bash
je -p "summarize the changes in the last commit"
```

More in [Print mode & scripting](/guides/print-mode/).

## Where to go next

- **[Core concepts](/concepts/)** — understand what's actually happening.
- **[The interactive session](/guides/tui/)** — get fluent in the TUI.
- **[Providers & models](/guides/providers-and-models/)** — switch models,
  add providers, use local models.
