---
artifact: Types
status: complete
order: 4
fills: "core domain types, primitives, enums, identifiers, structural schemas"
depends_on: [Contracts]
filled_by: both
last_decision: D-004
---

# Types — Resonance Journal

All of these live in `resonance_journal/model.py`. They are frozen dataclasses
unless stated otherwise.

## Core Domain Types
- **`Entry`**: `id: EntryId`, `title: str`, `body: str`, `tags: tuple[Tag, ...]`
  (sorted), `created_at: Timestamp`, `updated_at: Timestamp`,
  `archived_at: Timestamp | None`, `links: tuple[Link, ...]` (outgoing),
  `backlinks: tuple[Link, ...]` (incoming). The property `archived` is
  `archived_at is not None`.
- **`Link`**: `source_id: EntryId`, `target_id: EntryId`, `note: str`,
  `created_at: Timestamp`, `other_title: str`, `other_archived: bool`. The
  `other_*` fields describe the entry at the far end. They are filled in by the
  store so a view needs no extra query.
- **`EntryDraft`**: `title: str`, `body: str`, `tags: tuple[str, ...]` (raw,
  not yet normalized). This is the input to `create`.

## Primitives & Identifiers
- **`EntryId`** = `int`. It is SQLite `INTEGER PRIMARY KEY AUTOINCREMENT`, so
  ids are never reused after a row is removed by hand. Short numbers are easy
  to type in a CLI (D-004).
- **`Tag`** = `str` matching I1. Made by `normalize_tag(raw) -> Tag`, which
  raises `ValidationError`.
- **`Timestamp`** = `str`, UTC ISO-8601 `YYYY-MM-DDTHH:MM:SSZ`. It sorts
  lexically in time order, and that is why it is a string (D-004). Made only by
  `utcnow()`.

## Enums
- **`Visibility`**: `ACTIVE` (default), `ARCHIVED`, `ALL`. Used by search,
  list, and export.
- **`ExportFormat`**: `MARKDOWN = "md"`, `JSON = "json"`.

## Error hierarchy
`JournalError` → `ValidationError`, `NotFoundError`, `StorageError`,
`ExportError`. cli turns any `JournalError` into exit code 1.

## Structural Schemas
- **`SearchQuery`**: `terms: tuple[str, ...]`, `tags: tuple[Tag, ...]`,
  `visibility: Visibility = ACTIVE`, `limit: int | None = None`.
- **JSON export document**:
  ```json
  {"format": "resonance-journal/v1", "exported_at": "<Timestamp>",
   "entries": [{"id": 1, "title": "...", "body": "...", "tags": ["a"],
                "created_at": "...", "updated_at": "...", "archived_at": null,
                "links": [{"target_id": 2, "note": "..."}]}]}
  ```
- **Markdown export file** `NNNN-slug.md`:
  ```
  ---
  id: 1
  title: "..."            # JSON-quoted, so any title is safe YAML
  tags: [a, b]
  created_at: ...
  updated_at: ...
  archived_at: null
  links: [2, 5]
  ---

  <body verbatim>
  ```
  and `index.md` lists `[title](NNNN-slug.md)` and tags for each entry. An
  empty `.resonance-export` marker file sits next to them.
- **Storage shape** (store-private, schema v1):
  `entries(id PK, title, body, created_at, updated_at, archived_at)`,
  `tags(id PK, name UNIQUE)`,
  `entry_tags(entry_id FK→entries ON DELETE CASCADE, tag_id FK→tags, PK(entry_id, tag_id))`,
  `links(source_id FK, target_id FK, note, created_at, PK(source_id, target_id), CHECK(source_id <> target_id))`.
