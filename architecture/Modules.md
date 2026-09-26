---
artifact: Modules
status: complete
order: 7
fills: "module list, ownership, responsibilities, boundaries"
depends_on: [Interfaces]
filled_by: both
last_decision: D-004
---

# Modules — Resonance Journal

| Module | Responsibility | Owns (boundary) | Implements interface |
|--------|----------------|-----------------|----------------------|
| `resonance_journal/model.py` | Types, validators (`normalize_tag`, `validate_title`), errors, clock | the vocabulary; tag and title rules | JournalStore (declares it), Clock |
| `resonance_journal/store.py` | SQLite schema, migrations, queries, transactions | the DB file and every SQL string | JournalStore |
| `resonance_journal/service.py` | Use cases and domain rules | when a change is valid; `updated_at` semantics | Journal API |
| `resonance_journal/export.py` | Markdown and JSON rendering, safe file writing | export layout, overwrite policy | Exporter |
| `resonance_journal/cli.py` | argv parsing, text gathering, terminal rendering, exit codes | the user-facing command grammar | TextSource |
| `resonance_journal/__main__.py` | `python -m resonance_journal` entry point | nothing | — |
| `tests/` | unit tests per module, boundary test, CLI end-to-end test | evidence | — |
| `scripts/smoke.sh` | the main path as a user would type it | smoke evidence | — |

Size target: about 1,000 lines of package code (1,015 at this pass, counting
blank lines and docstrings). The whole program should fit
in one reader's head.
