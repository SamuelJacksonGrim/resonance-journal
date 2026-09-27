---
artifact: DecisionLog
status: complete
order: 99
fills: "architectural memory — consequential decisions, not every change"
depends_on: []
filled_by: both
last_decision: D-008
---

# DecisionLog — Resonance Journal

> Why the architecture became what it is. Git records what changed.
> Scope: continuous and selective (Architecture-Blueprints-Frameworks `SCHEMA.md`).

## Habits
- **Append-only. Supersede, never rewrite.**
- **Title the question, not the verdict.**
- **Skip ordinary work.**

## Status values
`active` · `superseded by D-NNN` · `reversed by D-NNN`

---

### D-001 — Build order: Flows before Contracts?
- **Date:** 2026-09-26
- **Decided by:** both (inherited)
- **Status:** active
- **Decision:** Build order is Architecture → Flows → Contracts.
- **Alternatives:** Contracts before Flows (rejected).
- **Reason:** A contract constrains a behavior, so the behavior has to be
  described first. Inherited from `PIPELINE.md`.
- **Affects:** Flows, Contracts.

### D-002 — Which stack, when the human named none?
- **Date:** 2026-09-26
- **Decided by:** AI (stack rule: smallest that can smoke-test; logged, shown)
- **Status:** active
- **Decision:** Python ≥ 3.10, standard library only. `sqlite3` for storage,
  `argparse` for the CLI, `unittest` for tests. Packaged with a
  `pyproject.toml` that declares a console script `rj`. It also runs with no
  install via `python -m resonance_journal`.
- **Alternatives:** Node + a web UI (rejected: a local HTTP server is a network
  boundary, which is a SELECTOR escalation, and adds a dependency tree).
  A JSON file store (rejected: no atomic multi-row updates, and the whole
  journal is rewritten on every change). SQLite FTS5 search (rejected for now:
  not every Python build ships it, and a linear substring scan is fast
  enough at personal-journal scale. Measured on 10,000 entries of ~1 KB each,
  in memory on the build container: a no-hit term search takes 0.03 s and
  listing everything takes 0.23 s).
- **Reason:** Zero install. It is "self-contained and reasonably small", SQLite
  gives G2 for free, and the smoke test is a shell script.
- **Affects:** all modules, Dependencies (stdlib-only rule).

### D-003 — Is `standard` enough when a module boundary carries privacy?
- **Date:** 2026-09-26
- **Decided by:** AI
- **Status:** active
- **Decision:** Depth is `standard`, which is the private-data escalation from
  `thin`. The forbidden import edges (only `store` touches the DB, and export
  never queries) are stated in Contracts and Dependencies and enforced by
  `tests/test_boundaries.py`. Dependencies is completed beyond what standard
  requires. Schemas stays `partial`.
- **Alternatives:** `full` (rejected: the only thing it would add is a finished
  Schemas ontology, and no decision in this system depends on it). `thin`
  (rejected: private data needs explicit module ownership).
- **Reason:** SELECTOR governing test: use the thinnest depth that can express
  every decision that cannot safely stay implicit.
- **Affects:** INTENT, Dependencies, Schemas, tests.

### D-004 — Integer ids, string timestamps, and no background process?
- **Date:** 2026-09-26
- **Decided by:** AI
- **Status:** active
- **Decision:** Entries use autoincrement integer ids. Timestamps are UTC
  ISO-8601 strings with second precision. Each command is one short process,
  with no daemon and no events.
- **Alternatives:** UUIDs (rejected: painful to type in a CLI, and there is no
  multi-device merge to justify them). Epoch integers (rejected: unreadable in
  the DB and in exports).
- **Reason:** Local-first for a single device. If sync is added later, UUIDs
  and a network boundary come together, and that would reopen INTENT.
- **Affects:** Types, store schema, export format, cli grammar.

### D-005 — Should entries be deletable?
- **Date:** 2026-09-26
- **Decided by:** AI. The human may reverse this.
- **Status:** active
- **Decision:** No delete verb. `archive` hides an entry from list, search, and
  export by default, and can be undone.
- **Alternatives:** A hard `delete` with a confirmation prompt (rejected for
  now: irreversible, not asked for, and it would orphan backlinks).
- **Reason:** The intent lists "archive", not "delete". Deletion is an
  irreversible action on private data, so it waits for a human decision.
- **Affects:** Flows, Contracts (G3, guardrails).

### D-006 — What does export promise, and is there an import?
- **Date:** 2026-09-26
- **Decided by:** AI
- **Status:** active
- **Decision:** Two formats. `json` is one machine-readable file, versioned
  `resonance-journal/v1`, and is lossless for entries, tags, and outgoing
  links. `md` is a human-readable directory with front matter. Both are written
  atomically and never overwrite without `--force`. `--force` on a directory
  requires the `.resonance-export` marker. No import verb in this pass.
- **Alternatives:** Always overwrite (rejected: a single mistyped path could
  destroy a directory). One big Markdown file (rejected: harder to browse and
  diff).
- **Reason:** Export is the user's way out and their backup. It must be
  complete, and it must never become the thing that loses data.
- **Affects:** Flows (export), Contracts (G4, C-P2), export module, Schemas.

### D-007 — Interfaces depends on Schemas, but standard leaves Schemas optional?
- **Date:** 2026-09-26
- **Decided by:** AI
- **Status:** active
- **Decision:** In this instance, `Interfaces.depends_on` is `[Types,
  Contracts]`, not the template's `[Schemas]`.
- **Alternatives:** Keep `[Schemas]` and force Schemas to be complete
  (rejected: that is `full` depth in all but name).
- **Reason:** SCHEMA.md depth self-consistency says an artifact that standard
  requires complete may only depend on artifacts standard also requires
  complete. The template's edge breaks that rule at standard. The interfaces
  here are built from Types and Contracts. This gap belongs to the
  methodology, and it is reported upstream in the handover.
- **Affects:** Interfaces frontmatter.

### D-008 — Under what terms is this released?
- **Date:** 2026-09-27
- **Decided by:** human (the AI applied it)
- **Status:** active
- **Decision:** Dual license, AGPL-3.0-only OR commercial, mirroring
  resonance-memory: LICENSE, LICENSING.md, COMMERCIAL-LICENSE.md, NOTICE,
  CONTRIBUTING.md, legal/, SPDX headers on source files, README badges, and
  license metadata in pyproject.toml. legal/AUTHORSHIP.md records the one-shot
  process as it actually happened, together with the author's position that
  the work is protected through the methodology and the templates it was
  instantiated from.
- **Alternatives:** Copy resonance-memory's authorship record word for word
  (rejected: its multi-model account is false for this project).
- **Affects:** repository root, legal/, source file headers.
