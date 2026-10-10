"""Desktop adapter: the existing coding session and JSONL RPC, without a TUI."""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from pathlib import Path

import anyio

from je_agent.messages import AgentMessage, AssistantMessage
from je_agent.provider import CancellationToken
from je_agent.provider_events import AssistantErrorEvent, AssistantMessageEvent
from je_agent.session import JsonlSessionStorage
from je_agent.tools import AgentTool
from je_coding.credentials import FileCredentialStore
from je_coding.provider_catalog import builtin_provider_entry
from je_coding.provider_config import (
    load_provider_settings,
    provider_config_from_catalog_entry,
    resolve_provider_selection,
    upsert_saved_provider,
)
from je_coding.provider_runtime import create_model_provider
from je_coding.rpc import RpcServer
from je_coding.session import CodingSession, CodingSessionConfig
from je_coding.session_manager import SessionManager


class LoginNeededProvider:
    """Keep file browsing and sessions available before a model is connected."""

    async def aclose(self) -> None:
        """No external connection to close."""

    def stream_response(
        self,
        *,
        model: str,
        system: str,
        messages: list[AgentMessage],
        tools: list[AgentTool],
        signal: CancellationToken | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[AssistantMessageEvent]:
        async def stream() -> AsyncIterator[AssistantMessageEvent]:
            yield AssistantErrorEvent(
                reason="error",
                error=AssistantMessage(
                    model=model,
                    stop_reason="error",
                    error_message="请先在模型设置中连接 API key。",
                ),
            )

        return stream()


class DesktopRpcServer(RpcServer):
    """Add desktop resource discovery and API-key login to the existing RPC."""

    def __init__(self, session: CodingSession, *, connected: bool = True) -> None:
        super().__init__(session)
        self.coding_session = session
        self.connected = connected

    async def _dispatch(self, command: dict[str, object], tasks: anyio.abc.TaskGroup) -> None:
        kind, request_id = command.get("type"), command.get("id")
        session = self.coding_session
        try:
            if kind == "desktop_info":
                manager = session.session_manager
                await self._response(
                    request_id,
                    "desktop_info",
                    {
                        "connected": self.connected,
                        "cwd": str(session.cwd),
                        "skills": [
                            {"name": s.name, "description": s.description, "path": str(s.path)}
                            for s in session.skills
                        ],
                        "prompts": [
                            {"name": p.name, "description": p.description, "path": str(p.path)}
                            for p in session.prompt_templates
                        ],
                        "context": [str(p.path) for p in session.context_files],
                        "tools": [t.name for t in session.tools],
                        "sessions": [
                            {"id": r.id, "title": r.title, "updatedAt": r.updated_at}
                            for r in manager.list_sessions(session.cwd)
                        ]
                        if manager
                        else [],
                    },
                )
                return
            if kind == "desktop_login":
                provider, key = command.get("provider"), command.get("key")
                if not isinstance(provider, str) or not isinstance(key, str) or not key.strip():
                    raise ValueError("Provider and API key are required")
                entry = builtin_provider_entry(provider)
                if entry is None or entry.credential_name is None:
                    raise ValueError("This provider requires login through the JE terminal")
                # Reuse JE's credential store; never return a credential over RPC.
                FileCredentialStore().set_api_key(entry.credential_name, key)
                upsert_saved_provider(
                    provider_config_from_catalog_entry(provider), set_default=False
                )
                session.reload_provider_settings()
                session.set_provider(provider, persist_default=False)
                self.connected = True
                await self._response(request_id, "desktop_login")
                return
            if kind == "desktop_reload":
                await session.reload()
                await self._response(request_id, "desktop_reload")
                return
        except Exception as exc:
            await self._error(request_id, str(kind), str(exc))
            return
        await super()._dispatch(command, tasks)


async def serve(cwd: Path, trusted: bool = False) -> None:
    """Prepare the same engine used by JE CLI and serve one desktop workspace."""
    settings = load_provider_settings()
    selection = resolve_provider_selection(settings)
    connected = True
    try:
        provider = create_model_provider(selection.provider, model=selection.model)
    except RuntimeError:
        provider = LoginNeededProvider()
        connected = False
    manager = SessionManager()
    record = manager.prepare_session(
        cwd=cwd, model=selection.model, provider_name=selection.provider.name
    )
    session = await CodingSession.load(
        CodingSessionConfig(
            provider=provider,
            owns_initial_provider=True,
            model=selection.model,
            storage=JsonlSessionStorage(record.path),
            cwd=cwd,
            session_id=record.id,
            session_manager=manager,
            index_on_first_persist=True,
            provider_name=selection.provider.name,
            provider_settings=settings,
            runtime_provider_config=selection.provider if connected else None,
            extensions_enabled=False,
            trust_default="always" if trusted else "never",
            trust_override="approve" if trusted else "decline",
        )
    )
    await DesktopRpcServer(session, connected=connected).run()


def main() -> None:
    """Start the desktop's stdio backend with a selected workspace."""
    parser = argparse.ArgumentParser(description="JE Desktop JSONL backend")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--trusted", action="store_true")
    args = parser.parse_args()
    anyio.run(serve, args.cwd.resolve(), args.trusted)


if __name__ == "__main__":
    main()
