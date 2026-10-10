"""Validate complete ZIP manifest before any filesystem mutation."""

import re
import stat
import zipfile
from pathlib import Path, PurePosixPath


def extract_safe(archive, destination) -> list[str]:
    root = Path(destination).resolve()
    targets = []
    seen = set()
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        if sum(entry.file_size for entry in entries) > 2 * 1024 * 1024:
            raise ValueError("Archive too large")
        for entry in entries:
            name = entry.orig_filename
            path = PurePosixPath(name)
            if (
                not name
                or path.is_absolute()
                or "\\" in name
                or ".." in path.parts
                or re.match(r"^[A-Za-z]:", name)
                or stat.S_ISLNK(entry.external_attr >> 16)
            ):
                raise ValueError("Unsafe member")
            target = root.joinpath(*path.parts)
            if not target.resolve().is_relative_to(root) or target.exists() or target.is_symlink():
                raise ValueError("Unsafe target")
            if target in seen:
                raise ValueError("Duplicate target")
            seen.add(target)
            targets.append((entry, target, path.as_posix()))
        # Detect file-as-parent conflicts before writing.
        files = {target for entry, target, _ in targets if not entry.is_dir()}
        for _, target, _ in targets:
            if any(
                parent in files or (parent.exists() and not parent.is_dir())
                for parent in target.parents
                if parent.is_relative_to(root)
            ):
                raise ValueError("Invalid parent")
        result = []
        for entry, target, name in targets:
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.read(entry))
                result.append(name)
    return sorted(result)
