"""SQLite repository. The only module that opens the journal file.

Implements model.JournalStore. See architecture/Interfaces.md and Contracts
(G2 atomic commands, I5 schema version, C-P1 file permissions).
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

from .model import (
    Entry,
    EntryId,
    Link,
    SearchQuery,
    StorageError,
    Tag,
    Timestamp,
    Visibility,
)

SCHEMA_VERSION = 1

_SCHEMA_V1 = """
CREATE TABLE entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    archived_at TEXT
);
CREATE TABLE tags (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE entry_tags (
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    tag_id   INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, tag_id)
);
CREATE TABLE links (
    source_id  INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    target_id  INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    note       TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    PRIMARY KEY (source_id, target_id),
    CHECK (source_id <> target_id)
);
CREATE INDEX links_target ON links(target_id);
CREATE INDEX entries_created ON entries(created_at, id);
"""

_VISIBILITY_SQL = {
    Visibility.ACTIVE: "e.archived_at IS NULL",
    Visibility.ARCHIVED: "e.archived_at IS NOT NULL",
    Visibility.ALL: "1",
}


def _contains(haystack: str | None, needle: str) -> int:
    # Literal, Unicode-aware, case-insensitive substring match. Used instead of
    # LIKE, which is ASCII-only case-insensitive and treats % and _ as wildcards.
    return int(haystack is not None and needle in haystack.casefold())


class Store:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._depth = 0

    @classmethod
    def open(cls, path: str | os.PathLike[str]) -> "Store":
        """Open (creating if needed) and migrate the journal at `path`.

        ':memory:' gives a throwaway in-memory journal (tests).
        """
        target = str(path)
        if target != ":memory:":
            p = Path(target)
            if not p.parent.exists():
                p.parent.mkdir(parents=True, mode=0o700)
            if not p.exists():
                # C-P1: create the file 0600 before SQLite touches it.
                fd = os.open(p, os.O_CREAT | os.O_WRONLY, 0o600)
                os.close(fd)
        try:
            conn = sqlite3.connect(target, timeout=5.0, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.create_function("rj_contains", 2, _contains, deterministic=True)
        except sqlite3.Error as exc:
            raise StorageError(f"cannot open journal at {target}: {exc}") from exc
        store = cls(conn)
        store._migrate(target)
        return store

    def _migrate(self, target: str) -> None:
        try:
            version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        except sqlite3.DatabaseError as exc:
            raise StorageError(f"{target} is not a Resonance Journal database: {exc}") from exc
        if version > SCHEMA_VERSION:
            raise StorageError(
                f"database schema v{version} is newer than this program (v{SCHEMA_VERSION})"
            )
        if version == 0:
            with self.transaction():
                for stmt in _SCHEMA_V1.split(";"):
                    if stmt.strip():
                        self._conn.execute(stmt)
                self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Contracts G2. Nested calls join the outermost transaction."""
        if self._depth == 0:
            self._exec("BEGIN IMMEDIATE")  # waits up to `timeout` for another writer
        self._depth += 1
        try:
            yield
        except BaseException:
            self._depth -= 1
            if self._depth == 0:
                self._conn.execute("ROLLBACK")
            raise
        else:
            self._depth -= 1
            if self._depth == 0:
                self._exec("COMMIT")

    def _exec(self, sql: str, params: Iterable[object] = ()) -> sqlite3.Cursor:
        try:
            return self._conn.execute(sql, tuple(params))
        except sqlite3.Error as exc:
            raise StorageError(f"storage error: {exc}") from exc

    # --- entries -----------------------------------------------------------

    def insert_entry(self, title: str, body: str, now: Timestamp) -> EntryId:
        cur = self._exec(
            "INSERT INTO entries (title, body, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (title, body, now, now),
        )
        return int(cur.lastrowid)

    def get_entry(self, entry_id: EntryId) -> Entry | None:
        row = self._exec("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        return self._hydrate(row) if row else None

    def update_entry(self, entry_id: EntryId, title: str, body: str, now: Timestamp) -> None:
        self._exec(
            "UPDATE entries SET title = ?, body = ?, updated_at = ? WHERE id = ?",
            (title, body, now, entry_id),
        )

    def set_archived(self, entry_id: EntryId, archived_at: Timestamp | None) -> None:
        self._exec("UPDATE entries SET archived_at = ? WHERE id = ?", (archived_at, entry_id))

    def touch(self, entry_id: EntryId, now: Timestamp) -> None:
        self._exec("UPDATE entries SET updated_at = ? WHERE id = ?", (now, entry_id))

    # --- tags --------------------------------------------------------------

    def add_tags(self, entry_id: EntryId, tags: Iterable[Tag]) -> None:
        for tag in tags:
            self._exec("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            self._exec(
                "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) "
                "SELECT ?, id FROM tags WHERE name = ?",
                (entry_id, tag),
            )

    def remove_tags(self, entry_id: EntryId, tags: Iterable[Tag]) -> None:
        for tag in tags:
            self._exec(
                "DELETE FROM entry_tags WHERE entry_id = ? "
                "AND tag_id = (SELECT id FROM tags WHERE name = ?)",
                (entry_id, tag),
            )
        self._exec("DELETE FROM tags WHERE id NOT IN (SELECT tag_id FROM entry_tags)")

    def tag_counts(self, visibility: Visibility) -> list[tuple[Tag, int]]:
        rows = self._exec(
            "SELECT t.name, COUNT(*) AS n FROM tags t "
            "JOIN entry_tags et ON et.tag_id = t.id "
            "JOIN entries e ON e.id = et.entry_id "
            f"WHERE {_VISIBILITY_SQL[visibility]} "
            "GROUP BY t.name ORDER BY n DESC, t.name"
        ).fetchall()
        return [(r["name"], r["n"]) for r in rows]

    # --- links -------------------------------------------------------------

    def upsert_link(self, src: EntryId, dst: EntryId, note: str, now: Timestamp) -> None:
        self._exec(
            "INSERT INTO links (source_id, target_id, note, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (source_id, target_id) DO UPDATE SET note = excluded.note",
            (src, dst, note, now),
        )

    def delete_link(self, src: EntryId, dst: EntryId) -> None:
        self._exec("DELETE FROM links WHERE source_id = ? AND target_id = ?", (src, dst))

    # --- search ------------------------------------------------------------

    def find_entries(self, query: SearchQuery) -> list[Entry]:
        where = [_VISIBILITY_SQL[query.visibility]]
        params: list[object] = []
        for term in query.terms:
            needle = term.casefold()
            where.append(
                "(rj_contains(e.title, ?) OR rj_contains(e.body, ?) OR EXISTS ("
                " SELECT 1 FROM entry_tags et JOIN tags t ON t.id = et.tag_id"
                " WHERE et.entry_id = e.id AND rj_contains(t.name, ?)))"
            )
            params += [needle, needle, needle]
        for tag in query.tags:
            where.append(
                "EXISTS (SELECT 1 FROM entry_tags et JOIN tags t ON t.id = et.tag_id"
                " WHERE et.entry_id = e.id AND t.name = ?)"
            )
            params.append(tag)
        sql = (
            "SELECT e.* FROM entries e WHERE "
            + " AND ".join(where)
            + " ORDER BY e.created_at DESC, e.id DESC"
        )
        if query.limit is not None:
            sql += " LIMIT ?"
            params.append(query.limit)
        return [self._hydrate(r) for r in self._exec(sql, params).fetchall()]

    # --- helpers -----------------------------------------------------------

    def _hydrate(self, row: sqlite3.Row) -> Entry:
        entry_id = row["id"]
        tags = tuple(
            r["name"]
            for r in self._exec(
                "SELECT t.name FROM tags t JOIN entry_tags et ON et.tag_id = t.id "
                "WHERE et.entry_id = ? ORDER BY t.name",
                (entry_id,),
            )
        )
        links = tuple(
            Link(r["source_id"], r["target_id"], r["note"], r["created_at"],
                 r["title"], r["archived_at"] is not None)
            for r in self._exec(
                "SELECT l.*, e.title, e.archived_at FROM links l "
                "JOIN entries e ON e.id = l.target_id WHERE l.source_id = ? ORDER BY l.target_id",
                (entry_id,),
            )
        )
        backlinks = tuple(
            Link(r["source_id"], r["target_id"], r["note"], r["created_at"],
                 r["title"], r["archived_at"] is not None)
            for r in self._exec(
                "SELECT l.*, e.title, e.archived_at FROM links l "
                "JOIN entries e ON e.id = l.source_id WHERE l.target_id = ? ORDER BY l.source_id",
                (entry_id,),
            )
        )
        return Entry(
            id=entry_id,
            title=row["title"],
            body=row["body"],
            tags=tags,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            archived_at=row["archived_at"],
            links=links,
            backlinks=backlinks,
        )
