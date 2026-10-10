"""Je 内部说明文档与示例路径定义。"""

from __future__ import annotations

from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
_DATA_ROOT = _PACKAGE_ROOT / "data"


def je_readme_path() -> Path:
    """Return the installed overview document for Tau-aware tasks."""
    return _DATA_ROOT / "docs" / "README.md"


def je_docs_path() -> Path:
    """Return the installed Tau self-documentation directory."""
    return _DATA_ROOT / "docs"


def je_examples_path() -> Path:
    """Return the installed Tau example directory."""
    return _DATA_ROOT / "examples"


tau_readme_path = je_readme_path
tau_docs_path = je_docs_path
tau_examples_path = je_examples_path
