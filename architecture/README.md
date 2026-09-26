---
artifact: README
status: complete
order: 10
fills: "front door — what/why/problem/components for the instantiated system"
depends_on: [Architecture, Flows, Contracts]
filled_by: both
last_decision: D-007
---

# Resonance Journal: design

## What is this?
The design record for Resonance Journal. It is a local-first journal you run
from the terminal, one SQLite file on your machine, and a CLI to create, edit,
tag, link, search, view, archive, and export entries.

## Why does it exist?
Journals hold private thoughts. Most journal apps put those thoughts on
someone else's server. This one keeps them in one file you own, and it lets
you connect entries ("this resonates with that") so the journal becomes a web
of thoughts and not just a stack of them.

## What problem does it solve?
- Writing and finding entries without a network, account, or install step.
- Getting your journal out in open formats (Markdown, JSON) at any time. Export
  never silently overwrites anything.
- Seeing how thoughts connect: links and backlinks on every entry.

## Major components
From [Modules](Modules.md):

| Module | Role |
|---|---|
| `cli` | command grammar, text input (flags, file, stdin, `$EDITOR`), rendering |
| `service` | use cases; single authority on domain rules |
| `store` | SQLite schema and queries; the only code that opens the DB |
| `export` | Markdown and JSON output; atomic, private, never overwrites without `--force` |
| `model` | types, validators, errors, clock |

Start with [INTENT](../INTENT.md), then [Architecture](Architecture.md) →
[Flows](Flows.md) → [Contracts](Contracts.md). The *why* is in
[DecisionLog](DecisionLog.md).

## Artifact status
Depth: **standard** (escalated from thin because of private data; see
[INTENT](../INTENT.md) and D-003).

| Artifact | Status |
|----------|--------|
| Architecture | complete |
| Flows | complete |
| Contracts | complete |
| Types | complete |
| Schemas | partial (allowed at standard) |
| Interfaces | complete |
| Modules | complete |
| Dependencies | complete (beyond standard; D-003) |
| DecisionLog | complete |
| README | complete |

## Evidence
- `python3 -m unittest discover -s tests -t .`: 51 tests covering model,
  service, store, export, CLI end to end, and the import boundaries
  (Dependencies and G1 are checked against the source).
- `scripts/smoke.sh`: the main path as a user types it, against a throwaway
  journal.
- Mutation check during the build: nine deliberate breakages (tag
  normalization, self-link guard, no-op `updated_at`, rollback, casefold
  search, export marker guard, DB, export and editor-temp file privacy) each
  made the suite fail.
