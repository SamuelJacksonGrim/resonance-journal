> **History note.** This rubric was locked in the framework repo at
> `Architecture-Blueprints-Frameworks@d2dc69d`, before the changes it measured.
> It was removed from there by D-023 after the re-run
> (`resonance-journal-rerun`) found and read it. That makes the re-run's score
> *contaminated*, not blind. The journal prompt is now burned as a blind test,
> because the framework's DecisionLog describes its expected result. Blind
> tests now use unseen prompts, judged by the framework's PIPELINE Done list.

# Eval — Resonance Journal one-shot (locked rubric)

Regression check for this framework, not for the app. Locked **before** any
framework change that it measures, so the change cannot shape its own grade.

## Protocol

1. Fresh session. It must not have seen the conversation that produced this file.
2. Empty repository. The prompt below, verbatim. No hints.
3. When the run finishes, a reviewer reads the produced repo and scores it here.
   Score only what is listed. New observations go under "Notes". They are not
   added to the score.

### Prompt (verbatim)

> Build a small local-first journal application called Resonance Journal.
>
> It should allow a user to create, edit, tag, link, search, view, archive, and
> export journal entries.
>
> Keep it self-contained and reasonably small.
>
> Use the Architecture-Blueprints-Frameworks repository as the methodology for
> designing and constructing the application.
>
> Start with this blank repository and take the project from intent through a
> working, verified implementation.

## Scored — product (implied counterparts and category norms)

| # | Item | Pass when |
|---|---|---|
| B1 | Delete | An entry can be permanently removed, with a guard: a confirmation, or a separate verb from archive. |
| B2 | Import | Export output can be loaded back in. A round-trip is verified by a test. |
| B3 | Edit keeps the previous text | Prior text is recoverable after an edit. Storage is **bounded**: unbounded full-copy history is only a partial pass. |
| B4 | Navigable export links | Links between entries are clickable or followable in the exported files. |
| B5 | Date search | Filter or search by date or date range. |
| B6 | Multi-hop links | You can traverse the link graph beyond one step (depth ≥ 2, or a path or neighborhood view). |

## Scored — process

| # | Item | Pass when |
|---|---|---|
| P1 | Implied counterparts surfaced | The Intent Card lists the expected-but-unstated features, each marked include or exclude with a reason. |
| P2 | No needless questions | This prompt fills every consequential Intent field (single local user, no network, no money), so the run proceeds without a pre-plan. |
| P3 | Evidence | Tests and a smoke test ran, and the result is disclosed. |
| P4 | Artifacts valid | The framework validator (if present) passes on the produced artifacts. |
| P5 | Growth bounded | Every feature that grows storage without limit states a bound or retention rule. |

## Not scored (by the human's decision)

Web or TUI interface, sync or multiple devices, encryption at rest, CI, license
file, Windows test run, schema-upgrade test. A run that adds these is neither
rewarded nor penalized. Summarization / TL;DR is a bonus note only.

## Baseline — run 1 (2026-09-26, `SamuelJacksonGrim/resonance-journal@a930173`)

| B1 | B2 | B3 | B4 | B5 | B6 | P1 | P2 | P3 | P4 | P5 |
|---|---|---|---|---|---|---|---|---|---|---|
| fail | fail | fail | fail | fail | fail | fail | pass | pass | n/a | n/a |

**Product 0/6 · Process 2/3 applicable.**

## Run 2 — re-run (contaminated, not blind)

`SamuelJacksonGrim/resonance-journal-rerun@2c8acb9`, against framework
`@bab6361`. The builder said up front that it had found and read this rubric,
so the score shows what the framework plus the answer key produces. It is not
evidence of what the framework produces alone.

| B1 | B2 | B3 | B4 | B5 | B6 | P1 | P2 | P3 | P4 | P5 |
|---|---|---|---|---|---|---|---|---|---|---|
| pass | pass | pass | pass | pass | pass | pass | pass | pass | pass | pass |

**Product 6/6 · Process 5/5 (contaminated).**

Notes: delete guarded by `--yes`, revisions capped at 20 per entry, `graph`
depth 1–5 plus `path`, Markdown export with relative links and backlinks,
`--from`/`--to` date filters, and an idempotent JSON import keyed by UUID.
Depth `thin`, and the validator passes. Tests pass (reviewer re-ran them).

## Run 3 — blind (unseen prompt, no rubric)

`SamuelJacksonGrim/resonance-journal-blind@ffabeb3`. The prompt was *"Build me
something that weighs semantic relationships between words for storage that
makes accessing them easy for an AI to pull when relevant."* It was judged only
against its own Intent Card and PIPELINE's Done list.

- It surfaced 12 implied counterparts with reasons (forget/unrelate, export and
  import with links intact, multi-hop recall, a "why" path for each result,
  date filters, and exclusions for embeddings and reinforcement).
- Every include was built and tested: 28 tests pass, and the reviewer ran the
  main path by hand.
- Growth is bounded (`max_pairs`, fan-out caps). The live boundary held: no
  model download, no API calls.
- Depth `standard` (the MCP server is a second process). The validator passes.
- **Framework defect found:** it applied the one-shot rule because "no human
  was present to answer". The human never said one-shot and was reachable.
  SELECTOR had no rule for runs where the builder cannot tell whether anyone
  will answer.
