---
artifact: Architecture
status: complete
order: 1
fills: "structural blueprint — subsystems, boundaries, data & control flow"
depends_on: []
filled_by: both
last_decision: D-004
---

# Architecture — Resonance Journal

## Purpose
Resonance Journal is one process on the user's machine. It runs as a
command-line program, `rj` or `python -m resonance_journal`. Each run parses
one command, does it against one SQLite file, prints the result, and exits.
There is no daemon, server, or network. It links entries to each other, so a
reader can follow a thought to where it "resonates" with another entry.

## Major Subsystems
- **cli** (`cli.py`): parses argv, collects text (flags, file, stdin, or
  `$EDITOR`), calls the service, and prints results. It holds no domain rules
  and no SQL.
- **service** (`service.py`): the journal use cases: create, edit, tag, link,
  search, show, archive, and list. It is the **only authority on domain
  rules**: tag normalization, no self-links, what counts as a valid edit, and
  the archive semantics.
- **store** (`store.py`): the SQLite repository. It is the **only code that
  opens the database file.** It owns the schema, migrations (`PRAGMA
  user_version`), transactions, and file permissions.
- **export** (`export.py`): turns entries into Markdown files or one JSON
  document and writes them under a target path. It is the **only code that
  writes journal content outside the DB**. It refuses to overwrite by default.
- **model** (`model.py`): value types (`Entry`, `EntryDraft`, `SearchQuery`,
  `ExportFormat`), validation helpers, and the error hierarchy. It has no I/O.

## Boundaries
- **Trust and privacy boundary:** the user's filesystem. Journal text crosses
  it in two places only. The DB file (store) and an explicit export (export).
  An `$EDITOR` round-trip uses a private temp file that is deleted afterwards
  (cli). Nothing crosses a network. The package imports no networking module,
  and a test enforces that.
- **Process boundary:** none. One process, one command, one short-lived
  connection.
- **Human boundary:** the terminal. Every change comes from an explicit command
  the user typed. Nothing runs in the background.

## Data Flow
```
argv / stdin / $EDITOR ─► cli ─► service ─► store ─► journal.db (0600)
                            ▲        │
                            │        └─► Entry objects ─► cli (render to terminal)
                            │                         └─► export ─► *.md / .json (0600)
                          stdout
```
Entries always travel as `model.Entry` values. Neither cli nor export sees a
row, cursor, or SQL string.

## Control Flow
`cli.main(argv)` → build `Store(path)` → `Journal(store)` → one service call →
render → `store.close()` → exit code (0 ok, 1 domain error, 2 usage error).
The service calls the store inside one transaction per command. Export is
called by cli with entries it got from the service. Export never calls the
store.

## High-Level Diagram
See [`diagrams/architecture_graph.md`](diagrams/architecture_graph.md) and
[`diagrams/system_flow.md`](diagrams/system_flow.md).
