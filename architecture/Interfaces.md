---
artifact: Interfaces
status: complete
order: 6
fills: "plug points — the contracts between modules that make them swappable"
depends_on: [Types, Contracts]
filled_by: both
last_decision: D-007
---

# Interfaces — Resonance Journal

> `depends_on` differs from the template (`[Schemas]`). See D-007.

## Interface List

### JournalStore (`model.JournalStore`, a `typing.Protocol`)
- **Purpose:** persistence behind the service. You can swap SQLite for
  in-memory SQLite (tests) or another engine without touching the service.
- **Inputs → Outputs:**
  - `transaction() -> ContextManager[None]`: commit on normal exit, roll back
    on any exception. Nesting is allowed and joins the outer transaction.
  - `insert_entry(title, body, now) -> EntryId`
  - `get_entry(id) -> Entry | None` (with tags, links, and backlinks filled)
  - `update_entry(id, title, body, now) -> None`
  - `set_archived(id, archived_at: Timestamp | None) -> None`
  - `add_tags(id, tags) -> None` / `remove_tags(id, tags) -> None`
  - `touch(id, now) -> None` (bumps `updated_at` only)
  - `upsert_link(src, dst, note, now) -> None` / `delete_link(src, dst) -> None`
  - `find_entries(query: SearchQuery) -> list[Entry]`
  - `tag_counts(visibility) -> list[tuple[Tag, int]]`
  - `close() -> None`
- **Upholds:** G2 (transactions), I2 (the schema `CHECK` and FKs are a second
  line of defense), I5, C-P1.
- **Implemented by:** `store.Store`.
- **Consumed by:** `service.Journal`.
- The store does **no** domain validation. It trusts normalized input and
  enforces only integrity constraints.

### Journal API (`service.Journal`)
- **Purpose:** the use cases. Any front end (today cli, later maybe a TUI) goes
  through this.
- **Inputs → Outputs:**
  - `create(draft: EntryDraft) -> Entry`
  - `edit(id, title: str | None = None, body: str | None = None) -> Entry`
  - `tag(id, add=(), remove=()) -> Entry`
  - `link(src, dst, note="") -> Entry` (returns the source) / `unlink(src, dst) -> Entry`
  - `archive(id) -> Entry` / `unarchive(id) -> Entry`
  - `get(id) -> Entry` (raises `NotFoundError`)
  - `search(query: SearchQuery) -> list[Entry]`
  - `tags(visibility) -> list[tuple[Tag, int]]`
- **Upholds:** I1–I4, the "look optional" invariants, and the authority table.
- **Implemented by:** `service.Journal(store, clock=model.utcnow)`.
- **Consumed by:** `cli`.

### Exporter (`export.export_entries`)
- **Purpose:** turn entries into files. You can add a format without touching
  service or store.
- **Inputs → Outputs:** `export_entries(entries: Sequence[Entry], fmt:
  ExportFormat, out: Path, now: Timestamp, force: bool = False) -> Path`.
  Returns the path it wrote.
- **Upholds:** G4, C-P2, atomic write (temp sibling + rename), the
  marker-guarded `--force`.
- **Implemented by:** `export`.
- **Consumed by:** `cli`.

### TextSource (`cli.edit_in_editor`)
- **Purpose:** get free text from the user. Tests replace it with a function.
- **Inputs → Outputs:** `edit_in_editor(initial: str) -> str`.
- **Upholds:** C-P3.
- **Implemented by:** `cli` (`$VISUAL`, then `$EDITOR`, then `vi`).
- **Consumed by:** `cli` handlers for `new` and `edit`.

### Clock (`Callable[[], Timestamp]`)
- **Purpose:** the only time source (authority table). Tests inject a fixed
  sequence.
- **Implemented by:** `model.utcnow`.
- **Consumed by:** `service.Journal`, `cli` (export timestamp).
