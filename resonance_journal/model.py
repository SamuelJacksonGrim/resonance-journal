"""Vocabulary of Resonance Journal: types, validators, errors, clock.

No I/O lives here. See architecture/Types.md.
"""

from __future__ import annotations

import enum
import re
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, Protocol

EntryId = int
Tag = str
Timestamp = str
Clock = Callable[[], Timestamp]

TITLE_MAX = 200
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_/-]{0,39}$")  # Contracts I1


class JournalError(Exception):
    """Base for every error the CLI reports with exit code 1."""


class ValidationError(JournalError):
    pass


class NotFoundError(JournalError):
    pass


class StorageError(JournalError):
    pass


class ExportError(JournalError):
    pass


class Visibility(enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    ALL = "all"


class ExportFormat(enum.Enum):
    MARKDOWN = "md"
    JSON = "json"


@dataclass(frozen=True)
class Link:
    source_id: EntryId
    target_id: EntryId
    note: str
    created_at: Timestamp
    other_title: str = ""
    other_archived: bool = False


@dataclass(frozen=True)
class Entry:
    id: EntryId
    title: str
    body: str
    tags: tuple[Tag, ...]
    created_at: Timestamp
    updated_at: Timestamp
    archived_at: Timestamp | None = None
    links: tuple[Link, ...] = ()
    backlinks: tuple[Link, ...] = ()

    @property
    def archived(self) -> bool:
        return self.archived_at is not None


@dataclass(frozen=True)
class EntryDraft:
    title: str
    body: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class SearchQuery:
    terms: tuple[str, ...] = ()
    tags: tuple[Tag, ...] = ()
    visibility: Visibility = Visibility.ACTIVE
    limit: int | None = None


def utcnow() -> Timestamp:
    """The single time source (Contracts, authority table)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_tag(raw: str) -> Tag:
    """Lowercase, trim, strip one leading '#'; then enforce I1."""
    tag = raw.strip().lower()
    if tag.startswith("#"):
        tag = tag[1:]
    if not TAG_RE.match(tag):
        raise ValidationError(
            f"invalid tag {raw!r}: use 1-40 of a-z 0-9 _ / - (starting with a letter or digit)"
        )
    return tag


def normalize_tags(raws: Iterable[str]) -> tuple[Tag, ...]:
    return tuple(sorted({normalize_tag(r) for r in raws}))


def validate_title(raw: str) -> str:
    """Contracts I4: 1-200 chars after trimming, single line."""
    title = raw.strip()
    if not title:
        raise ValidationError("title must not be empty")
    if "\n" in title or "\r" in title:
        raise ValidationError("title must be a single line")
    if len(title) > TITLE_MAX:
        raise ValidationError(f"title is longer than {TITLE_MAX} characters")
    return title


class JournalStore(Protocol):
    """Persistence behind the service. See architecture/Interfaces.md."""

    def transaction(self) -> AbstractContextManager[None]: ...
    def insert_entry(self, title: str, body: str, now: Timestamp) -> EntryId: ...
    def get_entry(self, entry_id: EntryId) -> Entry | None: ...
    def update_entry(self, entry_id: EntryId, title: str, body: str, now: Timestamp) -> None: ...
    def set_archived(self, entry_id: EntryId, archived_at: Timestamp | None) -> None: ...
    def add_tags(self, entry_id: EntryId, tags: Iterable[Tag]) -> None: ...
    def remove_tags(self, entry_id: EntryId, tags: Iterable[Tag]) -> None: ...
    def touch(self, entry_id: EntryId, now: Timestamp) -> None: ...
    def upsert_link(self, src: EntryId, dst: EntryId, note: str, now: Timestamp) -> None: ...
    def delete_link(self, src: EntryId, dst: EntryId) -> None: ...
    def find_entries(self, query: SearchQuery) -> list[Entry]: ...
    def tag_counts(self, visibility: Visibility) -> list[tuple[Tag, int]]: ...
    def close(self) -> None: ...
