"""Safe ZIP extraction.

Public API:
    extract_safe(archive, destination) -> list[str]

Validates every member of the archive *before* touching the filesystem, then
extracts file entries and returns the sorted relative POSIX paths of the
extracted files.
"""

from __future__ import annotations

import os
import re
import stat
import zipfile
from typing import List, Union

MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024  # 2 MiB

_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_S_IFMT = 0o170000
_S_IFLNK = 0o120000

Archive = Union[str, "os.PathLike[str]", zipfile.ZipFile]


class _ValidatedEntry:
    __slots__ = ("info", "rel", "is_dir")

    def __init__(self, info: zipfile.ZipInfo, rel: str, is_dir: bool) -> None:
        self.info = info
        self.rel = rel
        self.is_dir = is_dir


def _normalize_name(name: str) -> str:
    """Validate a member name and return its normalized POSIX relative path."""
    if not isinstance(name, str) or name == "":
        raise ValueError("archive member has an empty name")

    if "\\" in name:
        raise ValueError(f"backslash in member name: {name!r}")

    if name.startswith("/"):
        raise ValueError(f"absolute member path: {name!r}")

    if _DRIVE_RE.match(name):
        raise ValueError(f"Windows drive member path: {name!r}")

    segments = [part for part in name.split("/") if part not in ("", ".")]

    if any(part == ".." for part in segments):
        raise ValueError(f"'..' segment in member name: {name!r}")

    if not segments:
        raise ValueError(f"member name resolves to nothing: {name!r}")

    return "/".join(segments)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = info.external_attr >> 16
    return (mode & _S_IFMT) == _S_IFLNK


def _is_within(target: str, root: str) -> bool:
    return target == root or target.startswith(root + os.sep)


def extract_safe(archive: Archive, destination: Union[str, "os.PathLike[str]"]) -> List[str]:
    """Safely extract *archive* into *destination*.

    Every entry is validated before anything is created or written.  On any
    validation error a :class:`ValueError` is raised and the destination is
    left unchanged.
    """
    dest = os.fspath(destination)

    if isinstance(archive, zipfile.ZipFile):
        zf = archive
        close = False
    else:
        zf = zipfile.ZipFile(archive, "r")
        close = True

    try:
        dest_real = os.path.realpath(os.path.abspath(dest))
        total = 0
        seen: set[str] = set()
        validated: list[_ValidatedEntry] = []

        for info in zf.infolist():
            rel = _normalize_name(info.filename)
            is_dir = info.is_dir()

            if _is_symlink(info):
                raise ValueError(f"symlink member rejected: {info.filename!r}")

            if rel in seen:
                raise ValueError(f"duplicate normalized target: {rel!r}")
            seen.add(rel)

            total += info.file_size
            if total > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("total declared uncompressed size exceeds 2 MiB")

            target = os.path.join(dest_real, *rel.split("/"))
            if os.path.lexists(target):
                raise ValueError(f"target already exists: {rel!r}")

            if not _is_within(os.path.realpath(target), dest_real):
                raise ValueError(f"target escapes destination: {rel!r}")

            validated.append(_ValidatedEntry(info, rel, is_dir))

        # Validation passed: now it is safe to create/write.
        os.makedirs(dest_real, exist_ok=True)
        files: list[str] = []
        for entry in validated:
            target = os.path.join(dest_real, *entry.rel.split("/"))
            if entry.is_dir:
                os.makedirs(target, exist_ok=True)
                continue
            parent = os.path.dirname(target)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with zf.open(entry.info, "r") as src, open(target, "wb") as dst:
                while True:
                    chunk = src.read(65536)
                    if not chunk:
                        break
                    dst.write(chunk)
            files.append(entry.rel)

        return sorted(files)
    finally:
        if close:
            zf.close()
