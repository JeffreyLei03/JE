"""Verify scoring cannot reward missing, incorrect or deceptively fast submissions."""

from pathlib import Path

import pytest
from benchmark.evaluator import evaluate
from benchmark.runner import tasks

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("identifier", [task["id"] for task in tasks()])
def test_codex_baseline_passes_independent_checks(identifier: str) -> None:
    result = evaluate(identifier, ROOT / "baseline" / identifier)
    assert result["passed"] == result["total"], result["failures"]
    assert all(group["total"] > 0 for group in result["groups"].values())
    assert result["runtime_ms"] is not None


def test_missing_solution_is_not_complete(tmp_path: Path) -> None:
    result = evaluate("02_intervals", tmp_path)
    assert result["passed"] == 0
    assert result["total"] > 0
    assert result["runtime_ms"] is None


def test_trivial_fast_solution_gets_no_performance_measurement(tmp_path: Path) -> None:
    (tmp_path / "solution.py").write_text("def normalize(intervals): return []\n")
    result = evaluate("02_intervals", tmp_path)
    assert 0 < result["passed"] < result["total"]
    assert result["runtime_ms"] is None
    assert any("nested" in failure for failure in result["failures"])


def test_original_buggy_starter_fails_merge_and_nonmutation(tmp_path: Path) -> None:
    task = next(task for task in tasks() if task["id"] == "02_intervals")
    (tmp_path / "solution.py").write_text(task["starter"])
    result = evaluate("02_intervals", tmp_path)
    assert result["passed"] < result["total"]
    assert any("nonmutation" in failure for failure in result["failures"])
    assert any("nested" in failure for failure in result["failures"])


def test_syntax_error_does_not_abort_suite(tmp_path: Path) -> None:
    (tmp_path / "solution.py").write_text("invalid ! syntax")
    result = evaluate("01_csv", tmp_path)
    assert result["passed"] == 0
    assert "SyntaxError" in result["failures"][0]


def test_functional_mode_preserves_accuracy_without_workload() -> None:
    result = evaluate("04_cache", ROOT / "baseline" / "04_cache", run_workload=False)
    assert result["passed"] == result["total"]
    assert result["runtime_ms"] is None
