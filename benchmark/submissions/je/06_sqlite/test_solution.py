"""Smoke tests for the users email migration."""

from __future__ import annotations

import sqlite3
import unittest

from solution import migrate


def make_legacy_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT NOT NULL)")
    return conn


class MigrateTests(unittest.TestCase):
    def tearDown(self) -> None:
        pass

    def test_normalizes_and_deduplicates_keeping_smallest_id(self) -> None:
        conn = make_legacy_conn()
        conn.executemany(
            "INSERT INTO users(id, email) VALUES(?, ?)",
            [
                (5, "  Alice@Example.COM "),
                (2, "alice@example.com"),
                (7, "BOB@X.COM"),
                (9, " bob@x.com"),
                (11, "carol@example.com"),
            ],
        )
        conn.commit()

        migrate(conn)

        rows = conn.execute("SELECT id, email FROM users ORDER BY id").fetchall()
        self.assertEqual(
            rows,
            [
                (2, "alice@example.com"),
                (7, "bob@x.com"),
                (11, "carol@example.com"),
            ],
        )
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
        conn.close()

    def test_unique_enforcement(self) -> None:
        conn = make_legacy_conn()
        conn.execute("INSERT INTO users(id, email) VALUES(1, 'a@x.com')")
        conn.commit()
        migrate(conn)

        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO users(email) VALUES('a@x.com')")
        conn.close()

    def test_rerun_is_idempotent(self) -> None:
        conn = make_legacy_conn()
        conn.executemany(
            "INSERT INTO users(id, email) VALUES(?, ?)",
            [(1, " A@x.com "), (2, "a@X.com")],
        )
        conn.commit()
        migrate(conn)
        before = conn.execute("SELECT id, email FROM users ORDER BY id").fetchall()

        migrate(conn)  # must not raise and must not change anything

        after = conn.execute("SELECT id, email FROM users ORDER BY id").fetchall()
        self.assertEqual(before, after)
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
        conn.close()

    def test_unsupported_version_raises(self) -> None:
        conn = make_legacy_conn()
        conn.execute("PRAGMA user_version = 2")
        conn.commit()
        with self.assertRaises(ValueError):
            migrate(conn)
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)
        conn.close()

    def test_active_transaction_raises_without_touching_it(self) -> None:
        conn = make_legacy_conn()
        conn.execute("INSERT INTO users(id, email) VALUES(1, ' A@x.com ')")
        # No commit: we are now inside a caller-owned transaction.
        self.assertTrue(conn.in_transaction)

        with self.assertRaises(ValueError):
            migrate(conn)

        self.assertTrue(conn.in_transaction)
        rows = conn.execute("SELECT id, email FROM users").fetchall()
        self.assertEqual(rows, [(1, " A@x.com ")])
        conn.rollback()
        conn.close()

    def test_empty_email_rolls_back_everything(self) -> None:
        conn = make_legacy_conn()
        conn.executemany(
            "INSERT INTO users(id, email) VALUES(?, ?)",
            [(1, " A@x.com "), (2, "   ")],
        )
        conn.commit()

        with self.assertRaises(ValueError):
            migrate(conn)

        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
        rows = conn.execute("SELECT id, email FROM users ORDER BY id").fetchall()
        self.assertEqual(rows, [(1, " A@x.com "), (2, "   ")])
        # No unique index was created.
        indexes = conn.execute("PRAGMA index_list('users')").fetchall()
        self.assertEqual(indexes, [])
        conn.close()

    def test_non_string_email_raises(self) -> None:
        conn = make_legacy_conn()
        conn.execute("INSERT INTO users(id, email) VALUES(1, ?)", (b"\x00\x01",))
        conn.commit()

        with self.assertRaises(ValueError):
            migrate(conn)

        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
        conn.close()

    def test_unrelated_tables_preserved(self) -> None:
        conn = make_legacy_conn()
        conn.execute("CREATE TABLE other(id INTEGER PRIMARY KEY, note TEXT)")
        conn.execute("INSERT INTO other(id, note) VALUES(1, 'keep me')")
        conn.execute("INSERT INTO users(id, email) VALUES(1, ' A@x.com ')")
        conn.commit()

        migrate(conn)

        self.assertEqual(
            conn.execute("SELECT id, note FROM other").fetchall(), [(1, "keep me")]
        )
        self.assertEqual(
            conn.execute("SELECT id, email FROM users").fetchall(),
            [(1, "a@x.com")],
        )
        conn.close()

    def test_partial_failure_is_atomic(self) -> None:
        conn = make_legacy_conn()
        conn.executemany(
            "INSERT INTO users(id, email) VALUES(?, ?)",
            [(1, " A@x.com "), (2, "a@X.COM"), (3, "")],
        )
        conn.commit()

        with self.assertRaises(ValueError):
            migrate(conn)

        # Nothing was normalized, deleted, indexed or versioned.
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
        rows = conn.execute("SELECT id, email FROM users ORDER BY id").fetchall()
        self.assertEqual(rows, [(1, " A@x.com "), (2, "a@X.COM"), (3, "")])
        self.assertEqual(conn.execute("PRAGMA index_list('users')").fetchall(), [])
        conn.close()

    def test_empty_table_migrates(self) -> None:
        conn = make_legacy_conn()
        conn.commit()
        migrate(conn)
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
        conn.close()


if __name__ == "__main__":
    unittest.main()
