---
title: Print mode & scripting
description: Run Je non-interactively for a single prompt — ideal for scripts, pipes, and CI.
---

Print mode runs a single prompt without the interactive UI and writes the result
to the terminal. It's the right choice for scripts, pipelines, and one-off
questions.

## Basic use

```bash
je -p "summarize the changes in the last commit"
```

The `-p` / `--print` flag switches Je into print mode; the prompt itself is a
plain positional argument, the same as an initial prompt for the TUI. Print
mode still uses the full coding-session environment — the same tools, project
context, and session storage as the TUI — so its turns are saved under
`~/.je/sessions/` too.

Put flags **before** the prompt. Je accepts multi-word prompts without
quoting, so anything after the last recognized flag — including tokens that
look like other flags — is treated as prompt text:

```bash
je -p --mode json "list the public functions in src/app.py"
```

## Output formats

Choose how results are written with `--mode`. Passing `--mode` on its own also
switches Je into non-interactive mode, so `-p` is optional once `--mode` is set:

```bash
je -p --mode text "list the public functions in src/app.py"        # default, human-readable
je --mode json "list the public functions in src/app.py"           # JSON, for parsing
je -p --mode transcript "list the public functions in src/app.py"  # structured transcript
```

- **text** — plain text with ANSI styling, for reading.
- **json** — machine-readable, for piping into other tools.
- **transcript** — a structured record of the turn.

Piped stdin is merged into the prompt, so you can feed file contents in:

```bash
cat README.md | je -p "Summarize this text"
```

A piped body can also be the entire prompt — `je -p` with no positional text
and piped stdin is valid:

```bash
cat README.md | je -p
```

## Choosing provider, model, and directory

The same selection flags work in print mode:

```bash
je -m gpt-5.5 -p "explain this module"
je --provider local -p "explain this module"
je --cwd ./services/api -p "audit for secrets"
```

## Resume a conversation

Pass an existing session id to run a follow-up turn non-interactively:

```bash
je --print --session <session-id> "Follow-up message"
```

Je appends the turn to the existing transcript and sends its active conversation
history to the model. It also uses the session's saved working directory,
provider, and model unless explicit selection flags override them. This works
with every output mode and keeps stdout dedicated to that mode. Unknown ids fail
without creating a session. `--session` cannot be combined with `--new-session`
or `--session-id`.

Use `tau sessions` to find session ids.

## Recording the session id

Automation can choose the exact id of a new print-mode session with
`--session-id`. This keeps stdout dedicated to the selected output format and
avoids scanning `~/.je/sessions/`:

```bash
worker_session_id="$(python -c 'import uuid; print(uuid.uuid4().hex)')"
je --print --new-session \
  --session-id "$worker_session_id" \
  --cwd /path/to/project \
  "review the current changes"
printf 'Je session: %s\n' "$worker_session_id"
```

Ids may contain letters, numbers, `.`, `_`, and `-`, must start and end with a
letter or number, and may be at most 128 bytes. `default` and `index` are
reserved. Use a unique id for each worker. Je atomically reserves the transcript
and exits with an error rather than opening or overwriting an existing session,
even if an unindexed transcript already uses that id or two workers start at the
same time. The option applies to text, JSON, and transcript modes without adding
metadata to their stdout output.

## Exit status

Print mode exits non-zero if the run fails, so you can use it in scripts:

```bash
if je --mode text -p "do the tests pass? answer yes or no" | grep -qi yes; then
  echo "looks good"
fi
```

> [!TIP]
> For interactive work, start the [TUI](/guides/tui/) instead — you get streaming,
> steering, pickers, and session branching.
