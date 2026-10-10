"""Transactional normalization and unique schema migration."""

import sqlite3


def migrate(conn: sqlite3.Connection) -> None:
    if conn.in_transaction:
        raise ValueError("Active caller transaction")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > 1:
        raise ValueError("Unsupported version")
    if version == 1:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        rows = conn.execute("SELECT id,email FROM users ORDER BY id").fetchall()
        unique = {}
        for user_id, email in rows:
            if not isinstance(email, str) or not email.strip():
                raise ValueError("Invalid email")
            unique.setdefault(email.strip().casefold(), user_id)
        conn.execute(
            "CREATE TABLE users_je_migration(id INTEGER PRIMARY KEY,email TEXT NOT NULL UNIQUE)"
        )
        conn.executemany(
            "INSERT INTO users_je_migration(id,email) VALUES (?,?)",
            [(user_id, email) for email, user_id in unique.items()],
        )
        conn.execute("DROP TABLE users")
        conn.execute("ALTER TABLE users_je_migration RENAME TO users")
        conn.execute("PRAGMA user_version=1")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
