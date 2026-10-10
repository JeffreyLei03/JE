"""Smoke tests for solution.extract_safe (standard library unittest only)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solution import MAX_UNCOMPRESSED_BYTES, extract_safe


def make_zip(path: Path, entries) -> None:
    """Write a zip. entries: list of (name, data, external_attr).

    data may be None to represent a directory entry.
    """
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data, attr in entries:
            info = zipfile.ZipInfo(name)
            info.external_attr = attr
            if data is None:
                info.external_attr |= 0o40755 << 16
                zf.writestr(info, b"")
            else:
                zf.writestr(info, data)


class ExtractSafeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _zip(self, entries, name="a.zip") -> Path:
        p = self.tmp / name
        make_zip(p, entries)
        return p

    def test_basic_nested(self) -> None:
        z = self._zip([("b.txt", b"B", 0), ("a/c.txt", b"C", 0)])
        dest = self.tmp / "out"
        result = extract_safe(z, dest)
        self.assertEqual(result, ["a/c.txt", "b.txt"])
        self.assertEqual((dest / "a" / "c.txt").read_bytes(), b"C")
        self.assertEqual((dest / "b.txt").read_bytes(), b"B")

    def test_empty_archive(self) -> None:
        z = self._zip([])
        dest = self.tmp / "out"
        self.assertEqual(extract_safe(z, dest), [])
        self.assertTrue(dest.is_dir())

    def test_directory_entries_omitted(self) -> None:
        z = self._zip([("a/", None, 0), ("a/b.txt", b"x", 0)])
        dest = self.tmp / "out"
        self.assertEqual(extract_safe(z, dest), ["a/b.txt"])
        self.assertTrue((dest / "a").is_dir())

    def test_absolute_path(self) -> None:
        z = self._zip([("/etc/passwd", b"x", 0)])
        dest = self.tmp / "out"
        with self.assertRaises(ValueError):
            extract_safe(z, dest)
        self.assertFalse(dest.exists())

    def test_windows_drive_path(self) -> None:
        z = self._zip([("C:/evil.txt", b"x", 0)])
        with self.assertRaises(ValueError):
            extract_safe(z, self.tmp / "out")

    def test_backslash(self) -> None:
        # zipfile normally rejects/rewrites backslashes; bypass that so the
        # archive member really keeps a backslash and exercise our check.
        from unittest import mock

        with mock.patch("zipfile._sanitize_filename", lambda n: n):
            z = self._zip([("a\\b.txt", b"x", 0)], name="backslash.zip")
            with self.assertRaises(ValueError):
                extract_safe(z, self.tmp / "out")

    def test_dotdot_segment(self) -> None:
        z = self._zip([("a/../../evil.txt", b"x", 0)])
        with self.assertRaises(ValueError):
            extract_safe(z, self.tmp / "out")

    def test_symlink_member(self) -> None:
        z = self._zip([("link", b"/etc/passwd", 0o120777 << 16)])
        dest = self.tmp / "out"
        with self.assertRaises(ValueError):
            extract_safe(z, dest)
        self.assertFalse(dest.exists())

    def test_duplicate_normalized(self) -> None:
        z = self._zip([("a/b.txt", b"1", 0), ("a//b.txt", b"2", 0)])
        with self.assertRaises(ValueError):
            extract_safe(z, self.tmp / "out")

    def test_existing_target(self) -> None:
        z = self._zip([("a.txt", b"x", 0)])
        dest = self.tmp / "out"
        dest.mkdir()
        (dest / "a.txt").write_bytes(b"old")
        with self.assertRaises(ValueError):
            extract_safe(z, dest)
        self.assertEqual((dest / "a.txt").read_bytes(), b"old")

    def test_size_limit(self) -> None:
        big = b"0" * (MAX_UNCOMPRESSED_BYTES + 1)
        z = self._zip([("big.bin", big, 0)])
        dest = self.tmp / "out"
        with self.assertRaises(ValueError):
            extract_safe(z, dest)
        self.assertFalse(dest.exists())

    def test_size_limit_at_boundary_ok(self) -> None:
        data = b"0" * MAX_UNCOMPRESSED_BYTES
        z = self._zip([("big.bin", data, 0)])
        dest = self.tmp / "out"
        self.assertEqual(extract_safe(z, dest), ["big.bin"])
        self.assertEqual((dest / "big.bin").stat().st_size, MAX_UNCOMPRESSED_BYTES)

    def test_validation_failure_leaves_destination_unchanged(self) -> None:
        z = self._zip(
            [
                ("good/f.txt", b"x", 0),
                ("/abs.txt", b"y", 0),
            ]
        )
        dest = self.tmp / "out"
        with self.assertRaises(ValueError):
            extract_safe(z, dest)
        self.assertFalse(dest.exists())

    def test_parent_symlink_escape(self) -> None:
        outside = self.tmp / "outside"
        outside.mkdir()
        dest = self.tmp / "out"
        dest.mkdir()
        link = dest / "link"
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:  # pragma: no cover
            self.skipTest(f"symlinks unavailable: {exc}")
        z = self._zip([("link/evil.txt", b"x", 0)])
        with self.assertRaises(ValueError):
            extract_safe(z, dest)
        self.assertFalse((outside / "evil.txt").exists())

    def test_realpath_escape_detected(self) -> None:
        # Simulate a preexisting parent symlink even where creating one is not
        # permitted (e.g. unprivileged Windows), by forcing realpath to report
        # that the target lives outside the destination.
        from unittest import mock

        outside = self.tmp / "outside"
        outside.mkdir()
        dest = self.tmp / "out"
        z = self._zip([("link/evil.txt", b"x", 0)])
        real_realpath = os.path.realpath

        def fake_realpath(path):
            if os.path.basename(path) == "evil.txt":
                return os.path.join(str(outside), "evil.txt")
            return real_realpath(path)

        with mock.patch("solution.os.path.realpath", side_effect=fake_realpath):
            with self.assertRaises(ValueError):
                extract_safe(z, dest)
        self.assertFalse(dest.exists())

    def test_utf8_names(self) -> None:
        z = self._zip([("caf\u00e9/\u4e2d\u6587.txt", b"hi", 0)])
        dest = self.tmp / "out"
        result = extract_safe(z, dest)
        self.assertEqual(result, ["caf\u00e9/\u4e2d\u6587.txt"])
        self.assertEqual((dest / "caf\u00e9" / "\u4e2d\u6587.txt").read_bytes(), b"hi")

    def test_accepts_open_zipfile(self) -> None:
        z = self._zip([("a.txt", b"x", 0)])
        dest = self.tmp / "out"
        with zipfile.ZipFile(z, "r") as zf:
            self.assertEqual(extract_safe(zf, dest), ["a.txt"])


if __name__ == "__main__":
    unittest.main()
