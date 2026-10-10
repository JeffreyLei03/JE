"""External independent functional checks and deterministic workload timings."""

from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import os
import sqlite3
import stat
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from types import ModuleType
from typing import Any


class Checks:
    def __init__(self) -> None:
        self.groups = {str(i): {"passed": 0, "total": 0} for i in range(1, 5)}
        self.failures: list[str] = []

    def check(self, group: int, name: str, action: Callable[[], Any], expected: Any) -> None:
        bucket = self.groups[str(group)]
        bucket["total"] += 1
        try:
            actual = action()
            if actual != expected:
                raise AssertionError(f"expected {expected!r}, got {actual!r}")
        except Exception as exc:
            self.failures.append(f"{name}: {type(exc).__name__}: {exc}"[:240])
        else:
            bucket["passed"] += 1

    def rejects(
        self,
        group: int,
        name: str,
        action: Callable[[], Any],
        exception: type[BaseException] = ValueError,
    ) -> None:
        def run() -> bool:
            try:
                action()
            except exception:
                return True
            return False

        self.check(group, name, run, True)


def csv_checks(m: ModuleType, c: Checks) -> Callable[[], Any]:
    header = "customer,currency,amount\n"
    c.check(1, "empty", lambda: m.summarize(""), [])
    c.check(1, "header", lambda: m.summarize(header), [])
    c.check(
        1,
        "basic",
        lambda: m.summarize(header + "Ada,usd,1.25\nAda,USD,2.25\n"),
        [{"customer": "Ada", "currency": "USD", "total": "3.50", "count": 2}],
    )
    c.check(
        2,
        "round after sum",
        lambda: m.summarize(header + "a,EUR,0.005\na,EUR,0.005\n"),
        [{"customer": "a", "currency": "EUR", "total": "0.01", "count": 2}],
    )
    c.check(
        2,
        "signed rounding",
        lambda: m.summarize(header + "a,EUR,-1.235\n"),
        [{"customer": "a", "currency": "EUR", "total": "-1.24", "count": 1}],
    )
    c.check(
        2,
        "strip and sort",
        lambda: m.summarize(header + " z , usd ,1\na,EUR,2\n"),
        [
            {"customer": "a", "currency": "EUR", "total": "2.00", "count": 1},
            {"customer": "z", "currency": "USD", "total": "1.00", "count": 1},
        ],
    )
    for value in ("NaN", "Infinity", "bad", ""):
        c.rejects(3, f"amount {value}", lambda v=value: m.summarize(header + f"a,USD,{v}\n"))
    for line in (",USD,1", "a,US,1", "a,€UR,1", "a,USD", "a,USD,1,extra"):
        c.rejects(3, f"row {line}", lambda line=line: m.summarize(header + line + "\n"))
    c.rejects(4, "missing header", lambda: m.summarize("customer,amount\na,1\n"))
    c.check(
        4,
        "quoted customer",
        lambda: m.summarize(header + '"a,b",USD,3\n'),
        [{"customer": "a,b", "currency": "USD", "total": "3.00", "count": 1}],
    )
    c.check(
        4,
        "extra header",
        lambda: m.summarize("customer,currency,amount,note\na,USD,1,x\n"),
        [{"customer": "a", "currency": "USD", "total": "1.00", "count": 1}],
    )
    return lambda: m.summarize(header + "a,USD,0.01\n" * 40000)


def interval_checks(m: ModuleType, c: Checks) -> Callable[[], Any]:
    for name, values, expected in (
        ("empty", [], []),
        ("touch", [(4, 7), (1, 4)], [(1, 7)]),
        ("nested", [(1, 10), (2, 3), (5, 8)], [(1, 10)]),
        ("disjoint", [(9, 10), (-3, -1)], [(-3, -1), (9, 10)]),
        ("duplicates", [(1, 3), (1, 3)], [(1, 3)]),
        ("generator", iter([(2, 5), (1, 4)]), [(1, 5)]),
    ):
        c.check(
            1 if name in {"empty", "touch", "disjoint"} else 2,
            name,
            lambda values=values: m.normalize(values),
            expected,
        )
    for values in ([(1, 1)], [(3, 2)], [(False, 3)], [(1.0, 3)], [(1,)], [(1, 10), (5, 4)]):
        c.rejects(3, f"invalid {values}", lambda v=values: m.normalize(v))

    def immutable() -> bool:
        values = [[5, 8], [1, 4]]
        m.normalize(values)
        return values == [[5, 8], [1, 4]]

    c.check(4, "nonmutation", immutable, True)
    c.check(4, "large integer", lambda: m.normalize([(10**40, 10**40 + 2)]), [(10**40, 10**40 + 2)])
    return lambda: m.normalize([(i, i + 2) for i in range(60000, 0, -1)])


def dag_checks(m: ModuleType, c: Checks) -> Callable[[], Any]:
    c.check(1, "empty", lambda: m.plan({}), [])
    c.check(1, "independent", lambda: m.plan({"b": [], "a": []}), ["a", "b"])
    c.check(1, "chain", lambda: m.plan({"a": ["b"], "b": []}), ["b", "a"])
    c.check(2, "ready heap", lambda: m.plan({"a": ["b"], "b": [], "c": []}), ["b", "a", "c"])
    c.check(2, "duplicate dependencies", lambda: m.plan({"a": ["b", "b"], "b": []}), ["b", "a"])
    for graph in (
        {"a": ["x"]},
        {"a": ["a"]},
        {"a": ["b"], "b": ["a"]},
        {"z": [], "a": ["b"], "b": ["a"]},
    ):
        c.rejects(3, f"invalid {graph}", lambda graph=graph: m.plan(graph))

    def immutable() -> bool:
        graph = {"a": ["b", "b"], "b": []}
        m.plan(graph)
        return graph == {"a": ["b", "b"], "b": []}

    c.check(4, "nonmutation", immutable, True)
    graph = {f"n{i:05}": [f"n{i - 1:05}"] if i else [] for i in range(10000)}
    c.check(4, "deep chain", lambda: m.plan(graph), sorted(graph))
    return lambda: m.plan(graph)


def cache_checks(m: ModuleType, c: Checks) -> Callable[[], Any]:
    def scenario(which: str) -> Any:
        now = [0.0]
        cache = m.Cache(2, lambda: now[0])
        cache.put("a", 1, 10)
        cache.put("b", None, 2)
        if which == "basic":
            return cache.get("a"), cache.get("b", "miss"), cache.get("x", "miss"), len(cache)
        if which == "lru":
            cache.get("a")
            cache.put("c", 3, 10)
            return cache.get("b", "miss"), cache.get("a"), cache.get("c")
        if which == "expiry":
            now[0] = 2
            return cache.get("b", "miss"), len(cache)
        if which == "expire before eviction":
            cache.get("b")
            now[0] = 2
            cache.put("c", 3, 10)
            return cache.get("a"), cache.get("c"), len(cache)
        if which == "update":
            cache.put("b", 4, 20)
            now[0] = 3
            return cache.get("b"), len(cache)
        cache.put("a", 5, 0)
        return cache.get("a", "miss"), len(cache)

    for group, name, expected in (
        (1, "basic", (1, None, "miss", 2)),
        (1, "lru", ("miss", 1, 3)),
        (2, "expiry", ("miss", 1)),
        (2, "expire before eviction", (1, 3, 2)),
        (3, "update", (4, 2)),
        (3, "remove", ("miss", 1)),
    ):
        c.check(group, name, lambda n=name: scenario(n), expected)
    for capacity in (0, -1, True, 1.5):
        c.rejects(4, f"capacity {capacity}", lambda n=capacity: m.Cache(n, lambda: 0))

    def arbitrary() -> bool:
        cache = m.Cache(2, lambda: 0)
        cache.put((1, "a"), 7, 10)
        cache.put(5, 9, 10)
        return cache.get((1, "a")) == 7 and cache.get(5) == 9

    c.check(4, "hashable keys", arbitrary, True)

    def refreshed_expiry() -> bool:
        now = [0.0]
        cache = m.Cache(2, lambda: now[0])
        cache.put("a", 1, 2)
        cache.put("a", 2, 10)
        now[0] = 2
        live = cache.get("a") == 2
        now[0] = 10
        expired = cache.get("a", "missing") == "missing" and len(cache) == 0
        cache.put("b", 3, 10)
        cache.put("b", 4, -1)
        return live and expired and len(cache) == 0

    c.check(3, "refresh expiry and negative TTL", refreshed_expiry, True)

    def workload() -> None:
        cache = m.Cache(20000, lambda: 0)
        for i in range(20000):
            cache.put(i, i, 100)
        for i in range(40000):
            if cache.get(i % 20000) != i % 20000:
                raise AssertionError("Workload cache result")

    return workload


def async_checks(m: ModuleType, c: Checks) -> Callable[[], Any]:
    async def identity(value: int) -> int:
        return value * 2

    c.check(1, "empty", lambda: asyncio.run(m.bounded_map(identity, [], 2)), [])
    c.check(
        1,
        "generator",
        lambda: asyncio.run(m.bounded_map(identity, iter(range(5)), 2)),
        [0, 2, 4, 6, 8],
    )

    async def bounded() -> bool:
        active = 0
        peak = 0

        async def operation(value: int) -> int:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                await asyncio.sleep((5 - value) * 0.001)
                return value
            finally:
                active -= 1

        results = await m.bounded_map(operation, range(5), 2)
        return results == list(range(5)) and 1 < peak <= 2 and active == 0

    c.check(2, "order and concurrency", lambda: asyncio.run(bounded()), True)
    for limit in (0, -1, True, 1.5):
        c.rejects(2, f"limit {limit}", lambda n=limit: asyncio.run(m.bounded_map(identity, [], n)))

    async def cleanup(cancel: bool) -> bool:
        active = 0
        entered = asyncio.Event()

        async def operation(value: int) -> None:
            nonlocal active
            active += 1
            entered.set()
            try:
                if value == 0 and not cancel:
                    await asyncio.sleep(0.005)
                    raise RuntimeError("original")
                await asyncio.sleep(10)
            finally:
                active -= 1

        task = asyncio.create_task(m.bounded_map(operation, range(8), 3))
        await entered.wait()
        if cancel:
            task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            if not cancel:
                raise
        except RuntimeError as exc:
            if cancel or str(exc) != "original":
                raise
        else:
            return False
        await asyncio.sleep(0)
        return active == 0 and not [
            t for t in asyncio.all_tasks() if t is not asyncio.current_task() and not t.done()
        ]

    c.check(3, "error cleanup", lambda: asyncio.run(cleanup(False)), True)
    c.check(4, "caller cancellation cleanup", lambda: asyncio.run(cleanup(True)), True)
    return lambda: asyncio.run(m.bounded_map(identity, range(30000), 16))


def sqlite_checks(m: ModuleType, c: Checks) -> Callable[[], Any]:
    def scenario(mode: str) -> Any:
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT NOT NULL)")
            conn.execute("CREATE TABLE notes(value TEXT)")
            conn.execute("INSERT INTO notes VALUES ('safe')")
            rows = [(3, " ADA@X "), (1, "ada@x"), (2, "B@Y")]
            if mode == "invalid":
                rows.append((4, "  "))
            conn.executemany("INSERT INTO users VALUES (?,?)", rows)
            conn.commit()
            if mode == "future":
                conn.execute("PRAGMA user_version=2")
            if mode == "transaction":
                conn.execute("BEGIN")
            if mode in {"invalid", "future", "transaction"}:
                try:
                    m.migrate(conn)
                except ValueError:
                    version = conn.execute("PRAGMA user_version").fetchone()[0]
                    actual = conn.execute("SELECT id,email FROM users ORDER BY id").fetchall()
                    return (
                        actual == sorted(rows)
                        and version == (2 if mode == "future" else 0)
                        and conn.in_transaction == (mode == "transaction")
                    )
                return False
            m.migrate(conn)
            if mode == "rerun":
                m.migrate(conn)
            if mode == "unique":
                try:
                    conn.execute("INSERT INTO users VALUES (7,'ada@x')")
                except sqlite3.IntegrityError:
                    return True
                return False
            return (
                conn.execute("SELECT id,email FROM users ORDER BY id").fetchall(),
                conn.execute("PRAGMA user_version").fetchone()[0],
                conn.execute("SELECT value FROM notes").fetchall(),
                conn.in_transaction,
            )
        finally:
            conn.close()

    expected = ([(1, "ada@x"), (2, "b@y")], 1, [("safe",)], False)
    c.check(1, "normalize and deduplicate", lambda: scenario("basic"), expected)
    c.check(2, "unique enforcement", lambda: scenario("unique"), True)
    c.check(2, "idempotency", lambda: scenario("rerun"), expected)
    c.check(3, "atomic rollback", lambda: scenario("invalid"), True)
    c.check(4, "future schema", lambda: scenario("future"), True)
    c.check(4, "caller transaction preserved", lambda: scenario("transaction"), True)

    def workload() -> None:
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT NOT NULL)")
            conn.executemany(
                "INSERT INTO users VALUES (?,?)", [(i, f" a{i % 10000}@x ") for i in range(30000)]
            )
            conn.commit()
            m.migrate(conn)
            assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 10000
        finally:
            conn.close()

    return workload


class LinesOnly(io.StringIO):
    def read(self, *args: Any, **kwargs: Any) -> str:
        raise AssertionError("read() is forbidden")

    def readlines(self, *args: Any, **kwargs: Any) -> list[str]:
        raise AssertionError("readlines() is forbidden")


def jsonl_checks(m: ModuleType, c: Checks) -> Callable[[], Any]:
    valid = '{"type":"sale","customer":" 阿达 ","amount":3}\n'

    def run(text: str) -> tuple[dict, list]:
        sink = io.StringIO()
        stats = m.process(LinesOnly(text), sink)
        return stats, [json.loads(line) for line in sink.getvalue().splitlines()]

    c.check(
        1,
        "basic unicode",
        lambda: run(valid * 2),
        (
            {"accepted": 2, "invalid": 0, "ignored": 0},
            [{"customer": "阿达", "total": 6, "count": 2}],
        ),
    )
    c.check(1, "empty", lambda: run(""), ({"accepted": 0, "invalid": 0, "ignored": 0}, []))
    invalid = (
        "bad\n[]\nnull\n"
        + "\n".join(
            json.dumps(x)
            for x in (
                {"type": "sale", "customer": "a", "amount": True},
                {"type": "sale", "customer": "a", "amount": -1},
                {"type": "sale", "customer": " ", "amount": 1},
                {"type": "sale", "amount": 1},
            )
        )
        + "\n"
    )
    c.check(
        2, "validation", lambda: run(invalid), ({"accepted": 0, "invalid": 7, "ignored": 0}, [])
    )
    c.check(
        2,
        "ignored lines",
        lambda: run('\n {}\n{"type":"other"}\n'),
        ({"accepted": 0, "invalid": 0, "ignored": 3}, []),
    )
    c.check(
        3,
        "sorted results",
        lambda: run(valid + '{"type":"sale","customer":"a","amount":0}\n'),
        (
            {"accepted": 2, "invalid": 0, "ignored": 0},
            [
                {"customer": "a", "total": 0, "count": 1},
                {"customer": "阿达", "total": 3, "count": 1},
            ],
        ),
    )

    def cli(same: bool) -> bool:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "input.jsonl"
            output = source if same else Path(temporary) / "out.jsonl"
            source.write_text(valid, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, m.__file__, str(source), str(output)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=5,
            )
            if same:
                return result.returncode != 0 and source.read_text(encoding="utf-8") == valid
            return (
                result.returncode == 0
                and json.loads(result.stdout)["accepted"] == 1
                and json.loads(output.read_text(encoding="utf-8"))["customer"] == "阿达"
            )

    c.check(4, "CLI UTF8", lambda: cli(False), True)
    c.check(4, "CLI same file rejection", lambda: cli(True), True)
    return lambda: run(valid * 40000)


def zip_checks(m: ModuleType, c: Checks) -> Callable[[], Any]:
    def scenario(
        entries: list[tuple[Any, bytes]], reject: bool = False, existing: bool = False
    ) -> Any:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            archive = directory / "fixture.zip"
            destination = directory / "out"
            with zipfile.ZipFile(archive, "w") as bundle:
                for name, value in entries:
                    bundle.writestr(name, value)
            # ZipInfo normalizes Windows separators when constructing fixtures.
            # Patch equal-length local/central names to exercise an actual raw ZIP name.
            for name, _ in entries:
                if isinstance(name, str) and "\\" in name:
                    archive.write_bytes(
                        archive.read_bytes().replace(
                            name.replace("\\", "/").encode(), name.encode()
                        )
                    )
            if existing:
                destination.mkdir()
                (destination / "a.txt").write_text("original")
            before = {
                p.relative_to(directory).as_posix(): p.read_bytes()
                for p in directory.rglob("*")
                if p.is_file()
            }
            if reject:
                try:
                    m.extract_safe(archive, destination)
                except ValueError:
                    after = {
                        p.relative_to(directory).as_posix(): p.read_bytes()
                        for p in directory.rglob("*")
                        if p.is_file()
                    }
                    return before == after and (existing or not destination.exists())
                return False
            result = m.extract_safe(archive, destination)
            return result, {
                p.relative_to(destination).as_posix(): p.read_bytes()
                for p in destination.rglob("*")
                if p.is_file()
            }

    c.check(1, "empty", lambda: scenario([]), ([], {}))
    c.check(
        1,
        "valid nested",
        lambda: scenario([("dir/", b""), ("dir/文.txt", b"yes")]),
        (["dir/文.txt"], {"dir/文.txt": b"yes"}),
    )
    for unsafe in ("../bad", "/absolute", "C:/drive", "x\\bad", "a/../../bad"):
        c.check(
            2,
            f"unsafe {unsafe}",
            lambda n=unsafe: scenario([("ok.txt", b"ok"), (n, b"bad")], True),
            True,
        )
    symlink = zipfile.ZipInfo("link")
    symlink.create_system = 3
    symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
    c.check(3, "symlink member", lambda: scenario([(symlink, b"target")], True), True)
    c.check(
        3,
        "duplicate normalized",
        lambda: scenario([("a.txt", b"a"), ("./a.txt", b"b")], True),
        True,
    )
    c.check(4, "no overwrite", lambda: scenario([("a.txt", b"new")], True, True), True)
    c.check(
        4, "zip bomb limit", lambda: scenario([("big", b"x" * (2 * 1024 * 1024 + 1))], True), True
    )
    c.check(4, "parent file conflict", lambda: scenario([("a", b"x"), ("a/b", b"y")], True), True)

    def parent_link() -> bool:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            destination = root / "destination"
            outside.mkdir()
            destination.mkdir()
            link = destination / "link"
            if os.name == "nt":
                created = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                    capture_output=True,
                    timeout=5,
                )
                if created.returncode:
                    raise RuntimeError("Cannot prepare parent junction fixture")
            else:
                link.symlink_to(outside, target_is_directory=True)
            archive = root / "fixture.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("link/evil.txt", b"bad")
            try:
                m.extract_safe(archive, destination)
            except ValueError:
                return not list(outside.iterdir()) and not (destination / "evil.txt").exists()
            return False

    c.check(4, "existing parent symlink/junction", parent_link, True)
    return lambda: scenario([(f"d/f{i}.txt", b"x" * 16) for i in range(500)])


def search_checks(m: ModuleType, c: Checks) -> Callable[[], Any]:
    docs = {"z": "red blue red", "a": "red blue blue", "x": "red"}
    c.check(1, "AND score order", lambda: m.rank("red blue", docs), [("a", 3), ("z", 3)])
    c.check(1, "no match", lambda: m.rank("green", docs), [])
    c.check(1, "limit", lambda: m.rank("red blue", docs, 1), [("a", 3)])
    c.check(2, "deduplicate query", lambda: m.rank("RED red", docs), [("z", 2), ("a", 1), ("x", 1)])
    c.check(2, "unicode casefold", lambda: m.rank("STRASSE", {"a": "Straße straße"}), [("a", 2)])
    c.check(2, "underscore delimiter", lambda: m.rank("red_blue", {"a": "red blue"}), [("a", 2)])
    for query in ("", " !!! ", "___"):
        c.check(3, f"empty query {query}", lambda q=query: m.rank(q, docs), [])
    c.check(3, "zero limit", lambda: m.rank("red", docs, 0), [])
    for limit in (-1, True, 1.2):
        c.rejects(4, f"invalid limit {limit}", lambda n=limit: m.rank("", docs, n))

    def immutable() -> bool:
        m.rank("red", docs)
        return docs == {"z": "red blue red", "a": "red blue blue", "x": "red"}

    c.check(4, "nonmutation", immutable, True)
    c.check(3, "whole tokens", lambda: m.rank("red", {"a": "redder", "b": "red!"}), [("b", 1)])
    return lambda: m.rank("red blue", {f"d{i:05}": "red blue green " * 5 for i in range(20000)})


def retry_checks(m: ModuleType, c: Checks) -> Callable[[], Any]:
    c.check(
        1,
        "empty",
        lambda: m.run_jobs([], lambda *_: None, 2),
        {"results": {}, "attempts": {}, "failed": {}},
    )
    c.check(
        1,
        "None success",
        lambda: m.run_jobs(iter(["a"]), lambda *_: None, 1),
        {"results": {"a": None}, "attempts": {"a": 1}, "failed": {}},
    )

    def scenario() -> tuple[dict, list]:
        calls = []

        def handler(job: str, attempt: int) -> str:
            calls.append((job, attempt))
            if job == "b":
                raise ValueError("permanent")
            if job == "c" or attempt == 1:
                raise RuntimeError("retry")
            return "ok"

        result = m.run_jobs(["a", "b", "c"], handler, 3)
        return result, calls

    c.check(
        2,
        "round robin retries",
        scenario,
        (
            {
                "results": {"a": "ok"},
                "attempts": {"a": 2, "b": 1, "c": 3},
                "failed": {"b": "ValueError", "c": "RuntimeError"},
            },
            [("a", 1), ("b", 1), ("c", 1), ("a", 2), ("c", 2), ("c", 3)],
        ),
    )
    for jobs in (["a", "a"], ["a", 5], ["a", []]):

        def invalid(jobs=jobs) -> bool:
            calls = []
            try:
                m.run_jobs(jobs, lambda *args: calls.append(args), 2)
            except ValueError:
                return not calls
            return False

        c.check(3, f"invalid jobs {jobs}", invalid, True)
    for attempts in (0, -1, True, 1.5):
        c.rejects(4, f"attempts {attempts}", lambda n=attempts: m.run_jobs([], lambda *_: 0, n))

    def fatal(*_: Any) -> None:
        raise KeyboardInterrupt()

    c.rejects(
        4, "BaseException propagation", lambda: m.run_jobs(["a"], fatal, 2), KeyboardInterrupt
    )
    return lambda: m.run_jobs((str(i) for i in range(40000)), lambda *_: 1, 3)


CHECKERS = dict(
    zip(
        [
            "01_csv",
            "02_intervals",
            "03_dag",
            "04_cache",
            "05_async",
            "06_sqlite",
            "07_jsonl",
            "08_zip",
            "09_search",
            "10_retry",
        ],
        [
            csv_checks,
            interval_checks,
            dag_checks,
            cache_checks,
            async_checks,
            sqlite_checks,
            jsonl_checks,
            zip_checks,
            search_checks,
            retry_checks,
        ],
        strict=True,
    )
)


def evaluate(identifier: str, workspace: Path, *, run_workload: bool = True) -> dict[str, Any]:
    checks = Checks()
    runtime = None
    try:
        spec = importlib.util.spec_from_file_location("submission", workspace / "solution.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules["submission"] = module
        spec.loader.exec_module(module)
        workload = CHECKERS[identifier](module, checks)
        if run_workload and not checks.failures:
            start = perf_counter()
            workload()
            runtime = round((perf_counter() - start) * 1000, 4)
    except Exception as exc:
        checks.failures.append(f"evaluation: {type(exc).__name__}: {exc}"[:300])
        # Import/setup/workload failures must not accidentally receive perfect accuracy.
        checks.groups["4"]["total"] += 1
    return {
        "passed": sum(group["passed"] for group in checks.groups.values()),
        "total": sum(group["total"] for group in checks.groups.values()),
        "groups": checks.groups,
        "failures": checks.failures,
        "runtime_ms": runtime,
    }


if __name__ == "__main__":
    print(
        json.dumps(
            evaluate(sys.argv[1], Path(sys.argv[2]), run_workload="--functional" not in sys.argv),
            ensure_ascii=False,
        )
    )
