---
artifact: Dependencies
status: complete
order: 8
fills: "allowed/forbidden dependency directions, hierarchy, import rules"
depends_on: [Modules, Interfaces]
filled_by: both
last_decision: D-003
---

# Dependencies — Resonance Journal

> Not required at `standard`. Completed because the privacy boundary depends
> on a forbidden edge (D-003). `tests/test_boundaries.py` enforces it.

## Module Hierarchy
```
cli                 (top: depends on others)
 ├── service
 │    └── store
 ├── export
 └── model          (bottom: depends on nothing in the package)
```

## Allowed Directions
- `cli → service, export, model, store` (store only to construct `Store` in
  `main`, and only through `Store.open`)
- `service → model` (it receives the store through the `JournalStore`
  protocol and does not import `store`)
- `store → model`
- `export → model`

## Forbidden Directions
- `service → store` (import). The service gets its store injected. That is what
  makes in-memory tests and a swapped backend possible.
- `export → store` and `export → service`. Export renders what it is given.
  If it re-queried, it would become a second authority on "which entries".
- `model → anything` in the package.
- Any module → `socket`, `http`, `urllib`, `ssl`, `smtplib`, `ftplib` (G1).
- Third-party imports anywhere. Stdlib only (D-002).

## Import Rules
- No cycles.
- Only `store.py` may contain `import sqlite3`. Everyone else sees `Entry`.
- `cli.py` may call `Store.open` and `close`, and nothing else on `Store`.
  The test checks this by rejecting any other attribute access on the store.
