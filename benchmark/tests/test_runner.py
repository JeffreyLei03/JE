"""Benchmark fixture reproducibility and isolation checks."""

import json
from pathlib import Path

import pytest
from benchmark import runner


def test_exactly_ten_unique_tasks_with_apis() -> None:
    tasks = runner.tasks()
    assert len(tasks) == 10
    assert len({task["id"] for task in tasks}) == 10
    assert all(task["api"] and task["spec"] for task in tasks)


def test_empty_or_unrun_groups_do_not_receive_completion_credit() -> None:
    assert runner.completion_percent({}) == 0
    groups = {str(i): {"passed": 0, "total": 0} for i in range(1, 5)}
    groups["4"] = {"passed": 0, "total": 1}
    assert runner.completion_percent(groups) == 0
    groups["1"] = {"passed": 3, "total": 3}
    assert runner.completion_percent(groups) == 25


def test_prepare_does_not_overwrite_prior_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = {"id": "01_csv", "spec": "Public specification", "api": ["summarize"]}
    (tmp_path / "tasks.json").write_text(json.dumps([task]))
    baseline = tmp_path / "baseline" / "01_csv"
    baseline.mkdir(parents=True)
    (baseline / "solution.py").write_text("# baseline\n")
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    runner.prepare()
    je = tmp_path / "runs" / "je" / "01_csv"
    assert (je / "TASK.md").read_text().strip() == task["spec"]
    assert not (je / "solution.py").read_text().startswith("# baseline")
    (je / "solution.py").write_text("precious generated result\n")
    with pytest.raises(FileExistsError):
        runner.prepare()
    assert (je / "solution.py").read_text() == "precious generated result\n"
