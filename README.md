# Resonance Journal

[![License: AGPL-3.0-only](https://img.shields.io/badge/license-AGPL--3.0--only-blue)](LICENSE)
[![dual-license](https://img.shields.io/badge/dual--license-AGPL--3.0--only%20or%20commercial-blueviolet)](LICENSING.md)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](pyproject.toml)
[![built with](https://img.shields.io/badge/built%20with-Architecture--Blueprints--Frameworks-orange)](https://github.com/SamuelJacksonGrim/Architecture-Blueprints-Frameworks)

## Case study: testing a build framework with one-shot AI builds

*A two-minute read. This repo is the first build in a series of controlled
trials I ran to test and improve my
[Architecture-Blueprints-Frameworks](https://github.com/SamuelJacksonGrim/Architecture-Blueprints-Frameworks), a method any AI can follow to
design and build software from a plain request.*

**How I work:** I state the intent. The AI builds the whole thing without
asking permission at each step. Then I inspect the result, decide what's wrong,
and direct the fix. Every step below is a public commit or PR.

1. **Trial 1: this repo.** Claude built this journal in one pass from a short
   request. It worked, and it was tested. But I judged that it did only the
   literal verbs: no delete, no import, no date search, no multi-hop links. The
   framework never asked what a user would expect without saying it.
   ([scored history](evals/journal-rubric.md))
2. **Fixing the method, not the app.** I directed changes to the framework
   itself:
   - implied features ("export" means "import" too);
   - clear rules for when to ask the human and when to just build;
   - definitions of the escalation triggers;
   - a portable validator.

   Fresh AI agents that had never seen the discussion ran the new intake on
   different requests. Their confusion drove a second round of fixes.
   ([PR #11](https://github.com/SamuelJacksonGrim/Architecture-Blueprints-Frameworks/pull/11), [PR #12](https://github.com/SamuelJacksonGrim/Architecture-Blueprints-Frameworks/pull/12))
3. **Trial 2: a contaminated re-run.** A fresh session rebuilt the journal, but
   it found the grading rubric inside the framework and said so. I ruled that
   answer keys can't live in the system under test and removed them.
   ([PR #13](https://github.com/SamuelJacksonGrim/Architecture-Blueprints-Frameworks/pull/13),
   [re-run repo](https://github.com/SamuelJacksonGrim/resonance-journal-rerun))
4. **Trial 3: blind.** I wrote a deliberately vague, one-shot prompt the
   framework had never seen: *"Build me something that weighs semantic
   relationships between words for storage that makes accessing them easy for
   an AI to pull when relevant."* The result: a local semantic memory with
   multi-hop recall that explains why each result was pulled, bounded storage,
   an MCP server, and 28 passing tests. It came with no model downloads or API
   calls, and with its own list of expected-but-unstated features.
   ([blind repo](https://github.com/SamuelJacksonGrim/resonance-journal-blind))
5. **Carrying it back.** Reviewing that build surfaced an accent-matching bug
   ("zurich" vs "Zürich"). I had it fixed there, then found the same class of
   bug in my main project's fallback search and fixed that too, with tests.
   ([blind fix](https://github.com/SamuelJacksonGrim/resonance-journal-blind/commit/11643c9),
   [resonance-memory #40](https://github.com/SamuelJacksonGrim/resonance-memory/pull/40))
6. **Tightening the loop.** Finally I pressure-tested the method's own rules.
   What does "complete" mean? What should an improvement round do when a check
   fails? I settled both.
   ([PR #18](https://github.com/SamuelJacksonGrim/Architecture-Blueprints-Frameworks/pull/18))

**What it shows:** the AI does the construction, and I do the judging. The
judging is where I spend my time:
- deciding which gaps matter;
- designing tests that can't be gamed;
- ruling on contamination;
- knowing when an AI's own finding is wrong.

## License

This project is dual-licensed under **AGPL-3.0-only** OR a commercial license.

- [LICENSE](LICENSE): GNU AGPL-3.0-only (the free track)
- [LICENSING.md](LICENSING.md): how the two tracks work
- [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md): the commercial agreement
- [NOTICE](NOTICE): copyright, SPDX identifier, and provenance
- [legal/AUTHORSHIP.md](legal/AUTHORSHIP.md): how this work was made

A small, local-first journal for the terminal. Your entries live in one SQLite
file on your machine. Nothing is sent anywhere.

Create, edit, tag, link, search, view, archive, and export entries. Links show
up on both ends as backlinks, so you can follow how one thought resonates with
another.

- **No dependencies.** Python 3.10+ standard library only (tested on 3.10–3.13).
- **Private by default.** The journal file is `0600`, exports are `0600`, and
  the program has no network code (a test enforces this).
- **Nothing is lost silently.** There is no delete; `archive` hides an entry
  and can be undone. Export never overwrites without `--force`.

## Run it

```sh
# no install needed
python3 -m resonance_journal --help

# or install the `rj` command
pip install .
rj --help
```

The journal lives at `$RESONANCE_JOURNAL_DB`. If that is not set, it is
`$XDG_DATA_HOME/resonance-journal/journal.db` (default
`~/.local/share/resonance-journal/journal.db`). `--db PATH` overrides both.

## Use it

```sh
rj new "Low tide" --body "Walked out past the sandbar." -t sea -t walks
rj new "Night swim"                  # opens $VISUAL / $EDITOR (title line, blank line, body)
echo "Cold water." | rj new "Swim"   # body from stdin
rj edit 2                            # edit title+body in $EDITOR
rj edit 2 --title "Night swim, July" --body-file notes.txt

rj tag 2 sea moon                    # tags are normalized: "#Moon" == "moon"
rj untag 1 walks
rj tags                              # tag counts

rj link 2 1 --note "same beach"      # 2 → 1; 1 shows it as a backlink
rj unlink 2 1

rj show 1                            # full entry + links + backlinks
rj list                              # newest first (active entries)
rj search sandbar moon --tag sea     # every term must match (title, body, or tag)
rj list --archived                   # or --all

rj archive 1                         # hidden from list/search/export; reversible
rj unarchive 1

rj export --out journal-md                        # Markdown dir: index.md + one file per entry
rj export --all --format json --out journal.json  # lossless JSON (resonance-journal/v1)
rj export --out journal-md --force                # replace a previous export
```

Exit codes: `0` ok, `1` journal error (message on stderr), `2` usage error.

## Verify it

```sh
python3 -m unittest discover -s tests -t .   # 51 tests
./scripts/smoke.sh                           # end-to-end main path
```

## How it was built

This project was designed and built with the
[Architecture-Blueprints-Frameworks](https://github.com/SamuelJacksonGrim/Architecture-Blueprints-Frameworks)
method. Intent → construction pass → evidence → human decision.

- [`INTENT.md`](INTENT.md): what was asked, class `ui`, depth `standard`, and why
- [`architecture/`](architecture/): the ten artifacts. Start at
  [`architecture/README.md`](architecture/README.md)
- [`architecture/DecisionLog.md`](architecture/DecisionLog.md): why it is shaped
  this way (stack, no delete, export safety, ...)

```
resonance_journal/
  model.py     types, validators, errors, clock
  store.py     SQLite: the only code that opens the journal file
  service.py   use cases: the only authority on domain rules
  export.py    Markdown / JSON export: atomic, private, no silent overwrite
  cli.py       argument parsing, $EDITOR, rendering
tests/         unit, end-to-end, and import-boundary tests
scripts/smoke.sh
```

## The two license tracks

**Dual-licensed.** You pick one. If the AGPL works for you, you owe nothing.

1. **[AGPL-3.0](LICENSE)** is free. You can use, run, modify, fork, and
   redistribute this software at no charge. The copyleft catch is AGPL §13: if
   you *modify* it and let other people interact with it over a network (SaaS,
   an API, a hosted service), you must make the complete corresponding source of
   your modified version available to those users under the AGPL-3.0.
2. **A [paid commercial license](LICENSING.md)** covers closed-source,
   proprietary, or hosted use without the AGPL's source-disclosure obligations.
   Contact Samuel Jackson Grim, `samgrim97@gmail.com`, subject
   `Commercial license — Resonance Journal`.

This README is not a contract. The binding terms are [`LICENSE`](LICENSE) and a
signed commercial agreement, if you buy one. Contributing:
[`CONTRIBUTING.md`](CONTRIBUTING.md).
