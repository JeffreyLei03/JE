"""Desktop discovery preserves JE session resources without exposing credentials."""

from io import StringIO
from pathlib import Path

import anyio
import pytest

from je_agent.session import JsonlSessionStorage
from je_coding.desktop import DesktopRpcServer, LoginNeededProvider
from je_coding.session import CodingSession, CodingSessionConfig


@pytest.mark.anyio
async def test_desktop_discovery_works_before_model_login(tmp_path: Path) -> None:
    session = await CodingSession.load(
        CodingSessionConfig(
            provider=LoginNeededProvider(),
            model="test",
            cwd=tmp_path,
            storage=JsonlSessionStorage(tmp_path / "session.jsonl"),
            extensions_enabled=False,
            trust_default="never",
        )
    )
    server = DesktopRpcServer(session, connected=False)
    output = StringIO()
    server._stdout = output
    try:
        async with anyio.create_task_group() as tasks:
            await server._dispatch({"id": "info", "type": "desktop_info"}, tasks)
        import json

        result = json.loads(output.getvalue())
        assert result["success"] is True
        assert result["data"]["connected"] is False
        assert Path(result["data"]["cwd"]) == tmp_path
        assert "read" in result["data"]["tools"]
        assert "key" not in result["data"]
        assert result["data"]["skills"] == []
    finally:
        await session.aclose()


@pytest.mark.anyio
async def test_desktop_rejects_empty_credentials_without_saving(tmp_path: Path) -> None:
    session = await CodingSession.load(
        CodingSessionConfig(
            provider=LoginNeededProvider(),
            model="test",
            cwd=tmp_path,
            storage=JsonlSessionStorage(tmp_path / "session.jsonl"),
            extensions_enabled=False,
        )
    )
    server = DesktopRpcServer(session, connected=False)
    output = StringIO()
    server._stdout = output
    try:
        async with anyio.create_task_group() as tasks:
            await server._dispatch(
                {"id": "login", "type": "desktop_login", "provider": "deepseek", "key": ""}, tasks
            )
        assert '"success":false' in output.getvalue()
        assert server.connected is False
    finally:
        await session.aclose()
