"""SQLite migration for the legacy ``users`` table.

The migration:

* normalizes every ``email`` with ``str.strip().casefold()``;
* deduplicates normalized emails, keeping the row with the smallest ``id``;
* enforces uniqueness of ``email`` through a unique index;
* sets ``PRAGMA user_version = 1``.

The whole operation runs inside a single explicit transaction so that a
validation failure (empty/non-string email) leaves both the data and the
schema/version untouched.  Only the standard library is used.
"""

from __future__ import annotations

import sqlite3

__all__ = ["migrate"]

_UNIQUE_INDEX_NAME = "idx_users_email_unique"


def _normalize_email(email: object) -> str:
    """Return the canonical form of ``email`` or raise ``ValueError``."""
    if not isinstance(email, str):
        raise ValueError("users.email must be a string")
    normalized = email.strip().casefold()
    if not normalized:
        raise ValueError("users.email must not be empty")
    return normalized


def migrate(conn: sqlite3.Connection) -> None:
    """Migrate ``conn`` from schema version 0 to version 1.

    Raises:
        ValueError: if the connection already has an active transaction, if
            the stored ``user_version`` is greater than 1, or if any email is
            invalid (empty or not a string).
    """
    # Precondition: never touch a caller-owned transaction.
    if conn.in_transaction:
        raise ValueError("connection has an active transaction at entry")

    version: int = conn.execute("PRAGMA user_version").fetchone()[0]
    if version == 1:
        # Already migrated: rerunning is a no-op.
        return
    if version > 1:
        raise ValueError(f"unsupported schema version: {version}")

    # Validate and plan the whole migration before mutating anything.  This
    # way an invalid email aborts cleanly without any partial work.
    rows = conn.execute("SELECT id, email FROM users ORDER BY id").fetchall()

    planned_updates: list[tuple[int, str]] = []
    duplicate_ids: list[int] = []
    seen: dict[str, int] = {}
    for row_id, email in rows:
        normalized = _normalize_email(email)
        if normalized in seen:
            duplicate_ids.append(row_id)
        else:
            seen[normalized] = row_id
            planned_updates.append((row_id, normalized))

    # Use an explicit transaction while suppressing sqlite3's implicit
    # transaction management so BEGIN/COMMIT/ROLLBACK are fully under our
    # control.  The previous isolation level is restored afterwards.
    old_isolation_level = conn.isolation_level
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        try:
            for row_id, normalized in planned_updates:
                conn.execute(
                    "UPDATE users SET email = ? WHERE id = ?",
                    (normalized, row_id),
                )
            for row_id in duplicate_ids:
                conn.execute("DELETE FROM users WHERE id = ?", (row_id,))
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                f"{_UNIQUE_INDEX_NAME} ON users(email)"
            )
            conn.execute("PRAGMA user_version = 1")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")
    finally:
        conn.isolation_level = old_isolation_level
