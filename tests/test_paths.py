from pathlib import Path

import pytest

from je_coding.paths import JePaths, TauPaths


def test_je_paths_user_locations(tmp_path: Path) -> None:
    paths = JePaths(home=tmp_path / ".je", agents_home=tmp_path / ".agents")

    assert paths.sessions_dir == tmp_path / ".je" / "sessions"
    assert paths.user_skills_dir == tmp_path / ".je" / "skills"
    assert paths.user_prompts_dir == tmp_path / ".je" / "prompts"
    assert paths.user_agents_skills_dir == tmp_path / ".agents" / "skills"
    assert paths.user_agents_prompts_dir == tmp_path / ".agents" / "prompts"


def test_je_paths_project_locations(tmp_path: Path) -> None:
    paths = JePaths(home=tmp_path / "home", agents_home=tmp_path / "agents")
    cwd = tmp_path / "project"

    assert paths.project_je_dir(cwd) == cwd / ".je"
    assert paths.project_tau_dir(cwd) == cwd / ".je"
    assert paths.project_agents_dir(cwd) == cwd / ".agents"
    assert paths.project_skills_dir(cwd) == cwd / ".je" / "skills"
    assert paths.project_prompts_dir(cwd) == cwd / ".je" / "prompts"
    assert paths.project_agents_skills_dir(cwd) == cwd / ".agents" / "skills"
    assert paths.project_agents_prompts_dir(cwd) == cwd / ".agents" / "prompts"


def test_default_session_path_uses_home_sessions_and_readable_project_path(
    tmp_path: Path,
) -> None:
    paths = JePaths(home=tmp_path / "home", agents_home=tmp_path / "agents")
    cwd = tmp_path / "repos" / "exploration" / "je"
    cwd.mkdir(parents=True)

    session_path = paths.default_session_path(cwd)

    assert session_path.name == "default.jsonl"
    assert session_path.parent.parent == tmp_path / "home" / "sessions"
    assert "repos-exploration-je-" in session_path.parent.name
    assert len(session_path.parent.name.rsplit("-", maxsplit=1)[-1]) == 6
    assert session_path.parent.exists()


def test_je_home_defaults_to_dot_je(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JE_HOME", raising=False)
    monkeypatch.delenv("TAU_HOME", raising=False)

    assert JePaths().home == Path.home() / ".je"


def test_empty_je_home_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JE_HOME", "")

    assert JePaths().home == Path.home() / ".je"


def test_je_home_environment_override_is_read_for_each_instance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first_home = tmp_path / "je-first"
    second_home = tmp_path / "je-second"

    monkeypatch.setenv("JE_HOME", str(first_home))
    first = JePaths()
    monkeypatch.setenv("JE_HOME", str(second_home))
    second = JePaths()

    assert first.home == first_home
    assert first.sessions_dir == first_home / "sessions"
    assert first.user_extensions_dir == first_home / "extensions"
    assert second.home == second_home
    assert second.models_store_path == second_home / "models-store.json"
    assert second.llama_cpp_state_path == second_home / "state" / "extensions" / "llama.cpp.json"
    assert first.agents_home == second.agents_home == Path.home() / ".agents"


def test_je_home_expands_current_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JE_HOME", "~/.je-personal")

    assert JePaths().home == Path.home() / ".je-personal"


def test_je_home_must_be_absolute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JE_HOME", ".je-personal")

    with pytest.raises(ValueError, match="JE_HOME must be an absolute path"):
        JePaths()


def test_explicit_je_home_ignores_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    explicit_home = tmp_path / "explicit"
    monkeypatch.setenv("JE_HOME", str(tmp_path / "environment"))

    assert JePaths(home=explicit_home).home == explicit_home
