---
artifact: Intent
status: complete
order: 0
fills: "human intent plus the inspectable class/depth decision"
depends_on: []
filled_by: both
last_decision: D-003
---

# Intent Card — Resonance Journal

- **Want:** a small, local-first journal application. A user can create, edit,
  tag, link, search, view, archive, and export journal entries.
- **Must not:** send journal content anywhere (no network, no telemetry, no
  sync). Must not silently destroy entries. Must not need anything beyond the
  runtime itself to install or run.
- **Who it's for:** one person keeping a private journal on their own machine.
- **Runs where:** the user's machine. One process started from a terminal. Data
  lives in one local SQLite file.
- **Done when:** all eight verbs work end to end from the CLI, a unit test suite
  and a scripted smoke test pass, and the design artifacts match the code.
- **Secrets / private data / irreversible actions:** **private data.** Journal
  text is personal. The DB file and every export are private. The one
  irreversible act a user could trigger (overwriting a file on export) is
  refused by default. There is no hard-delete verb. See Contracts C-P1..C-P4.
- **Language / host (only if the human named one):** not named. Chosen:
  Python 3.10+ standard library only (`sqlite3`, `argparse`, `unittest`).
  Logged as D-002.

## Selector decision

```yaml
class: ui            # a CLI front end over a local store. No agent loop, no
                     # event bus, no dispatch. Nearest skeleton: none, so templates/.
depth: standard
reasons:
  - private_data: journal entries are personal. That is a SELECTOR escalation
    trigger, so depth goes up one step, from thin to standard.
  - The privacy posture is carried by module boundaries. Only store touches
    the file. Only export writes outside it. Those boundaries have to be
    explicit, so Types, Interfaces, and Modules must be complete.
  - Persistent local state alone would not escalate (SELECTOR). It is noted
    here because the other trigger applies.
  - No second process, no network boundary, no secrets, no money. Not reused
    as a skeleton. So not full.
escalate_if:        # SELECTOR Step C triggers, instantiated
  - a second process, or any network boundary (e.g. adding sync or a web UI)
  - secrets, money, private data, or irreversible actions (private data: already applied)
  - modules that must not import each other (present: only `store` may open the
    DB. Written into Contracts and enforced by a test. Dependencies is
    completed even though standard does not require it. See D-003.)
  - the intent to reuse this design as a skeleton
```
