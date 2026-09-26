---
artifact: Schemas
status: partial
order: 5
fills: "conceptual ontology — Entity→State→Event→Evaluation→Decision→Action"
depends_on: [Types]
filled_by: both
last_decision: null
---

# Schemas — Resonance Journal

> `partial` on purpose. At `standard` depth this artifact may stay open. The
> mapping below is enough to compare this system with others. Nothing here
> is needed to build or change it.

## Core Transformation Chain
| Ontology | Resonance Journal |
|---|---|
| Entity | `Entry` (plus its `Tag`s and `Link`s) |
| State | active / archived; its tag set; its link neighborhood |
| Event | a user command (`new`, `edit`, `tag`, `link`, `archive`, ...) |
| Evaluation | service validation (I1–I4) and filter matching (`search`) |
| Decision | accept and write in one transaction, or reject with `JournalError` |
| Action | row write, rendered output, or export files |

## Cognitive Schemas
Not applicable. The system holds no beliefs or goals of its own.

## Information Schemas
Raw text (argv, stdin, or editor) becomes an `EntryDraft` or edit fields. The
service validates and normalizes them into rows. The store reads rows back as
an `Entry`, which is rendered as terminal text, Markdown, or JSON.

## Transformation Schemas
Not yet written: formal rules for round-tripping Markdown export back into an
import. There is no import verb yet. See D-006.
