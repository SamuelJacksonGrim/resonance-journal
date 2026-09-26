---
artifact: Flows
status: complete
order: 2
fills: "behavioral blueprint — request, event, execution, error, state-update flows"
depends_on: [Architecture]
filled_by: both
last_decision: D-006
---

# Flows — Resonance Journal

## Request Flow (one per verb)

Every request goes: `rj <verb> ...` → cli parses → one `Journal` method →
render. Each step below is service behavior. The command form is in
parentheses.

| Verb | Command | Behavior |
|---|---|---|
| **create** | `rj new TITLE [--body T \| --body-file P\|-] [--tag X]...` | Validate the title. Normalize the tags. Insert the entry and its tags in one transaction. Return the new `Entry` with an `id`. If no body source is given, cli opens `$EDITOR` when stdin is a TTY and reads stdin otherwise. |
| **edit** | `rj edit ID [--title T] [--body T \| --body-file P\|-]` | Load the entry (it must exist). With no flags, cli opens `$EDITOR` on `title⏎⏎body` and parses the result. If nothing changed, it is a no-op and `updated_at` stays the same. Otherwise update the fields and set `updated_at = now`. Archived entries can be edited. |
| **tag** | `rj tag ID TAG...` / `rj untag ID TAG...` | Add or remove tags. Every token is normalized first. If any token is invalid, the whole command is rejected. Adding an existing tag or removing a missing one is a no-op. `updated_at` changes only if the tag set changed. Tags no entry uses any more are removed. |
| **link** | `rj link A B [--note N]` | Both entries must exist and A ≠ B. Store the directed link A→B. If it already exists, update the note and keep `created_at`. `rj unlink A B` removes it. |
| **search** | `rj search [TERMS...] [--tag X]... [--archived\|--all] [--limit N]` | Each term must appear as a literal, Unicode case-insensitive (`str.casefold`) substring of the title, body, or a tag. Each `--tag` must be present. Results are newest first. Archived entries are hidden unless `--archived` (archived only) or `--all` is given. With no terms and no tags, this is the same as `list`. |
| **view** | `rj show ID` | The full entry, plus outgoing links and backlinks (id, title, note, archived marker). `rj list` shows one line per entry, same visibility rules as search. `rj tags` shows the tag counts. |
| **archive** | `rj archive ID` / `rj unarchive ID` | Set or clear `archived_at`. Nothing else changes: not the body, not the links, not `updated_at`. Idempotent. |
| **export** | `rj export --format md\|json --out PATH [--all\|--archived] [--tag X]... [--force]` | Pick entries with the same filter rules as search. `json` writes one file. `md` writes a directory with one `NNNN-slug.md` per entry plus `index.md`. The target must not exist unless `--force` is given. Files are created 0600 and directories 0700. |

## Event Flow
There are no events or subscribers. Every state change is caused by a command
the user types and finishes inside that command (D-004).

## Execution Flow
```
main(argv)
  ├─ args = parser.parse_args(argv)      # usage error → exit 2
  ├─ path = --db | $RESONANCE_JOURNAL_DB | $XDG_DATA_HOME/resonance-journal/journal.db
  ├─ store = Store.open(path)            # creates dir 0700, file 0600, migrates
  ├─ journal = Journal(store)
  ├─ result = handler(journal, args)     # exactly one service call (+ export)
  ├─ print(render(result))
  └─ store.close(); return 0
```

## Error Flow
- `model.ValidationError` (bad title, bad tag, self-link, empty edit text) →
  stderr `error: ...`, exit 1. Nothing was written, because validation happens
  before the transaction starts.
- `model.NotFoundError` (unknown id) → exit 1, nothing written.
- `model.ExportError` (target exists, not writable) → exit 1. No partial export
  is left behind: files are written into a sibling temp path and then renamed
  into place.
- `sqlite3.Error` inside a transaction → rollback, then re-raised as
  `StorageError` → exit 1.
- DB file newer than this program (`user_version` > supported) → `StorageError`
  "database schema vN is newer than this program". The program refuses to
  touch it.
- `$EDITOR` exits non-zero or the buffer is left empty → `ValidationError`
  "aborted: empty entry". Nothing is written. The temp file is deleted in all
  cases.

## State-Update Flow
- State lives in `journal.db` only: tables `entries`, `tags`, `entry_tags`,
  `links` (see Types → Storage shape).
- `created_at` is set once. `updated_at` changes only when title, body, or the
  tag set really changes. `archived_at` is set or cleared only by
  archive/unarchive.
- Entries are never hard-deleted by any verb (D-005). Links and tags cascade
  only if a row is removed by hand outside the program.
- Timestamps are UTC ISO-8601 with seconds (`2026-09-26T19:40:00Z`), from one
  clock function `model.utcnow()`. Tests inject it.
