---
artifact: Contracts
status: complete
order: 3
fills: "guarantees, assumptions, invariants, pre/post-conditions"
depends_on: [Architecture, Flows]
filled_by: both
last_decision: D-006
---

# Contracts — Resonance Journal

## Guarantees
- **G1 Local only.** No code path opens a socket. The package imports none of
  `socket`, `http`, `urllib`, `ssl`, `smtplib`, `ftplib`.
  `tests/test_boundaries.py` enforces this.
- **G2 Atomic commands.** Each command's writes happen in one SQLite
  transaction. After any error the DB is exactly as it was before the command.
- **G3 No silent loss.** No verb deletes an entry. `edit` replaces text only
  with text the user gave explicitly. An empty editor buffer aborts the edit.
  It is never saved as an empty body.
- **G4 Faithful export.** Export contains every selected entry with its title,
  body (byte-for-byte), tags, timestamps, archive state, and outgoing links.
  JSON export round-trips: `json.loads` gives the same fields as `Entry`.

## Privacy contracts
- **C-P1** On POSIX, the DB file is created with mode `0600` and its directory
  with `0700`. Existing permissions are left alone. The user may have chosen
  them.
- **C-P2** Export files are created `0600` and export directories `0700`.
- **C-P3** `$EDITOR` temp files are created with `tempfile.mkstemp` (0600) and
  deleted in a `finally` block, even when the editor fails.
- **C-P4** Journal text is never written to logs or stderr. Error messages name
  ids and paths, not content.

## Assumptions
- One user and one process at a time. SQLite's file lock serializes two
  processes running at once. The second one waits up to 5 s (`timeout=5.0`)
  and then gets `StorageError`.
- The local clock is roughly right. Ordering uses `created_at` with `id` as the
  tie-break, so clock skew only affects display order.
- The terminal encoding is UTF-8. Text is stored as SQLite TEXT (UTF-8) either
  way.

## Invariants
- **I1** Every stored tag matches `^[a-z0-9][a-z0-9_/-]{0,39}$`.
- **I2** A link has `source_id ≠ target_id`, and both ids exist. There is at
  most one link per ordered pair.
- **I3** `archived_at` is NULL or ≥ `created_at`. `updated_at` ≥ `created_at`.
- **I4** The title is 1–200 characters after trimming, with no newline.
- **I5** `PRAGMA user_version` = `SCHEMA_VERSION` (1) after `Store.open`.

## Invariants that look optional but aren't
- **Tags are normalized before storage and before lookup** (lowercase, trim,
  strip a leading `#`). *Why:* without this, `Work`, `work`, and `#work`
  become three tags. `search --tag work` then silently misses entries and
  `rj tags` over-counts. This fails quietly, without an error.
- **`updated_at` moves only on real change.** *Why:* the list is sorted by
  creation time, but `show` and exports report `updated_at` as "last edited".
  A no-op `edit`, `tag`, or `archive` that bumps it makes that record wrong.
- **Archive never touches `updated_at` or links.** *Why:* archive is about
  visibility, not content. If archiving cut links, unarchiving could not bring
  back the graph, and backlinks on live entries would vanish when a neighbor
  was archived.
- **Search terms are matched literally with `casefold`, not with SQL `LIKE`.**
  The store registers `rj_contains()` for this. *Why:* `LIKE` treats `%` and
  `_` as wildcards, so `100%` or `snake_case` would match unrelated entries.
  It also folds case for ASCII only, so `ÉTÉ` would miss `été`. Both failures
  return plausible-looking results, so nobody notices.
- **Export writes to a temp sibling, then renames.** *Why:* a crash halfway
  through would otherwise leave a truncated export that looks complete. The
  user may treat that export as their backup.
- **`--force` on a Markdown export replaces only a directory that holds
  `.resonance-export`.** *Why:* without the marker, `--out ~/Documents --force`
  would replace a directory the user cares about.

## Guardrails — do NOT
- Don't write SQL outside `store.py`. Add a method to `Store` and call it from
  the service.
- Don't normalize tags or check links in cli or store. Call
  `model.normalize_tag`. The service is where tags are applied.
- Don't add a `delete` verb that removes rows. Use `archive`, which hides an
  entry and can be undone. Permanent deletion needs a human decision recorded
  in DecisionLog first (D-005).
- Don't print entry bodies in error messages. Name the id.
- Don't add sync, HTTP, or a web UI inside this package. That is a SELECTOR
  escalation (network boundary). Revisit INTENT and the depth first.

## Authority hierarchy (single source of truth)
| Decision | Authority | Others |
|---|---|---|
| Is this title, tag, or link valid? | `service` (using `model` validators) | cli only passes input through |
| What's in the DB, schema version, transactions | `store` | service asks. It never opens the file. |
| Which entries a filter selects (search/list/export) | `service.search` | export receives entries. It never re-queries. |
| File layout and overwrite policy of exports | `export` | cli passes `--force` through |
| Current time | `model.utcnow` (injectable) | nobody calls `datetime.now()` directly |

## Pre/Post-Conditions
| Operation | Pre | Post |
|---|---|---|
| `create(draft)` | title valid (I4), tags valid (I1) | new row, `created_at = updated_at`, `archived_at` NULL |
| `edit(id, title?, body?)` | entry exists, at least one field given | fields replaced; `updated_at` bumped iff changed |
| `set_tags(id, add, remove)` | entry exists, all tokens valid | tag set = (old ∪ add) − remove |
| `link(a, b, note)` | both exist, a ≠ b | exactly one link a→b with that note |
| `unlink(a, b)` | both exist | no link a→b (idempotent) |
| `archive(id)` / `unarchive(id)` | entry exists | `archived_at` set/cleared; nothing else changed |
| `search(q)` | limit ≥ 1 | entries matching every term and tag; newest first |
| `export(entries, fmt, out, force)` | out absent, or force with a valid target | complete export at `out`, or nothing new on disk |
